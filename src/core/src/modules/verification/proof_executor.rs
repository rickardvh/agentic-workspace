//! A narrow selected-proof executor. Only regular source bytes cross into Docker;
//! the proof gets no host mounts, socket, credentials, network, or writable source.
//! Repository policy declares the image and inputs; native code owns the boundary.
use crate::{CoreError, digest};
use cap_std::{ambient_authority, fs::Dir};
use serde_json::{Value, json};
use std::{
    collections::BTreeMap,
    io::Read,
    path::{Component, Path, PathBuf},
    process::Command,
    time::Duration,
};

const MAX_BYTES: usize = 128 * 1024 * 1024;
const MAX_FILES: usize = 20000;
pub(crate) const KIND: &str = "docker-readonly-source-v1";
pub(crate) fn configuration(target: &Path) -> Result<Value, CoreError> {
    let root = Dir::open_ambient_dir(target, ambient_authority()).map_err(err)?;
    let mut schema: Value =
        serde_json::from_str(include_str!("contracts/manifest.schema.json")).map_err(err)?;
    schema["properties"]["assurance"] =
        serde_json::from_str(include_str!("contracts/assurance.schema.json")).map_err(err)?;
    let manifest = crate::native_config::load(
        &root,
        ".agentic-workspace/verification/manifest.toml",
        &serde_json::to_string(&schema).map_err(err)?,
    )
    .map_err(err)?
    .map(|v| v.0)
    .unwrap_or(Value::Null);
    let mut execution = manifest["execution"].clone();
    if execution.is_null() {
        return Ok(execution);
    }
    let local = crate::native_config::load(
        &root,
        ".agentic-workspace/config.local.toml",
        include_str!("../../../contracts/schemas/workspace_local_override.schema.json"),
    )
    .map_err(err)?
    .map(|v| v.0)
    .unwrap_or(Value::Null);
    if !local["proof_execution"]["image"].is_null() {
        execution["image"] = local["proof_execution"]["image"].clone();
    }
    Ok(execution)
}
fn err(e: impl std::fmt::Display) -> CoreError {
    CoreError::new(e.to_string())
}

fn docker() -> Result<PathBuf, CoreError> {
    let name = if cfg!(windows) {
        "docker.exe"
    } else {
        "docker"
    };
    std::env::split_paths(&std::env::var_os("PATH").unwrap_or_default())
        .map(|p| p.join(name))
        .find(|p| p.is_file())
        .ok_or_else(|| err("proof-executor-unavailable: Docker executable required"))
}
fn run(args: &[&str], budget: Duration) -> Result<Value, CoreError> {
    let mut command = Command::new(docker()?);
    command.args(args);
    crate::process_execution::run(command, None, budget)
}
fn checked(args: &[&str]) -> Result<String, CoreError> {
    let result = run(args, Duration::from_secs(30))?;
    if result["status"] != "passed" {
        return Err(err(format!(
            "proof-executor-unavailable: {}",
            result["output"]["stderr"]
        )));
    }
    result["output"]["stdout"]["tail"]
        .as_str()
        .map(|s| s.trim().to_owned())
        .ok_or_else(|| err("proof-executor-invalid-response"))
}
fn relative(path: &str) -> bool {
    !path.is_empty()
        && path.len() <= 4096
        && !path.contains(['\\', ':'])
        && Path::new(path)
            .components()
            .all(|c| matches!(c, Component::Normal(_)))
}

fn linked(metadata: &cap_std::fs::Metadata) -> bool {
    #[cfg(windows)]
    {
        use cap_std::fs::MetadataExt;
        metadata.file_attributes() & 0x400 != 0
    }
    #[cfg(not(windows))]
    {
        metadata.file_type().is_symlink()
    }
}

/// Read through a confined directory, reject links/special files at every level,
/// and hash the actual bytes later transferred. No Git command or source script
/// runs while constructing a snapshot.
fn snapshot(target: &Path, config: &Value) -> Result<BTreeMap<String, Vec<u8>>, CoreError> {
    fn visit(
        root: &Dir,
        path: &str,
        files: &mut BTreeMap<String, Vec<u8>>,
        total: &mut usize,
        visited: &mut usize,
    ) -> Result<(), CoreError> {
        if files.contains_key(path) {
            return Ok(());
        }
        *visited += 1;
        if *visited > MAX_FILES || path.split('/').count() > 64 {
            return Err(err("proof-snapshot-capacity-exceeded"));
        }
        let metadata = root.symlink_metadata(path).map_err(err)?;
        if linked(&metadata) {
            return Err(err("proof-snapshot-link-unsupported"));
        }
        if metadata.is_dir() {
            for entry in root.read_dir(path).map_err(err)? {
                let name = entry
                    .map_err(err)?
                    .file_name()
                    .into_string()
                    .map_err(|_| err("proof-snapshot-path-unsupported"))?;
                let child = format!("{path}/{name}");
                if !relative(&child) {
                    return Err(err("proof-snapshot-path-unsupported"));
                }
                visit(root, &child, files, total, visited)?;
            }
        } else if metadata.is_file() {
            if files.len() >= MAX_FILES || metadata.len() > (MAX_BYTES - *total) as u64 {
                return Err(err("proof-snapshot-capacity-exceeded"));
            }
            let mut bytes = Vec::new();
            root.open(path)
                .map_err(err)?
                .take((MAX_BYTES - *total + 1) as u64)
                .read_to_end(&mut bytes)
                .map_err(err)?;
            *total += bytes.len();
            if *total > MAX_BYTES {
                return Err(err("proof-snapshot-capacity-exceeded"));
            }
            files.insert(path.into(), bytes);
        } else {
            return Err(err("proof-snapshot-special-file-unsupported"));
        }
        Ok(())
    }
    let root = Dir::open_ambient_dir(target, ambient_authority()).map_err(err)?;
    let inputs = config["inputs"]
        .as_array()
        .filter(|v| !v.is_empty() && v.len() <= 128)
        .ok_or_else(|| err("proof-executor-inputs-required"))?;
    let mut files = BTreeMap::new();
    let mut total = 0;
    let mut visited = 0;
    for input in inputs {
        let path = input
            .as_str()
            .filter(|p| relative(p))
            .ok_or_else(|| err("proof-executor-input-invalid"))?;
        // Check ancestors as well: a confined link is still not snapshot custody.
        let mut parent = Path::new(path);
        while !parent.as_os_str().is_empty() {
            if linked(&root.symlink_metadata(parent).map_err(err)?) {
                return Err(err("proof-snapshot-link-unsupported"));
            }
            parent = parent.parent().unwrap_or(Path::new(""));
        }
        visit(&root, path, &mut files, &mut total, &mut visited)?;
    }
    Ok(files)
}
fn identity(files: &BTreeMap<String, Vec<u8>>) -> Result<String, CoreError> {
    use sha2::{Digest, Sha256};
    let entries: BTreeMap<_, _> = files
        .iter()
        .map(|(name, bytes)| (name, format!("{:x}", Sha256::digest(bytes))))
        .collect();
    digest(&json!(entries))
}

fn scratch_paths(
    config: &Value,
    files: &BTreeMap<String, Vec<u8>>,
) -> Result<Vec<String>, CoreError> {
    let mut paths = Vec::new();
    for value in config["scratch_paths"].as_array().into_iter().flatten() {
        let path = value
            .as_str()
            .filter(|p| relative(p))
            .ok_or_else(|| err("proof-scratch-path-invalid"))?;
        if paths.len() >= 2
            || files.keys().any(|file| {
                file == path
                    || file.starts_with(&format!("{path}/"))
                    || path.starts_with(&format!("{file}/"))
            })
            || paths.iter().any(|old: &String| {
                old == path
                    || old.starts_with(&format!("{path}/"))
                    || path.starts_with(&format!("{old}/"))
            })
        {
            return Err(err("proof-scratch-path-overlaps-source"));
        }
        paths.push(path.to_owned());
    }
    Ok(paths)
}

pub(crate) fn observe(target: &Path, config: &Value) -> Result<Value, CoreError> {
    if config["kind"] != KIND {
        return Err(err("proof-executor-kind-unsupported"));
    }
    let image = config["image"]
        .as_str()
        .ok_or_else(|| err("proof-executor-image-required"))?;
    let hash = image
        .strip_prefix("sha256:")
        .or_else(|| image.rsplit_once("@sha256:").map(|(_, h)| h));
    if !hash.is_some_and(|h| h.len() == 64 && h.bytes().all(|b| b.is_ascii_hexdigit())) {
        return Err(err("proof-executor-immutable-image-required"));
    }
    let details: Value =
        serde_json::from_str(&checked(&["image", "inspect", image])?).map_err(err)?;
    let details = &details[0];
    if details["Os"] != "linux"
        || details["Config"]["Volumes"]
            .as_object()
            .is_some_and(|v| !v.is_empty())
    {
        return Err(err("proof-executor-image-boundary-unsupported"));
    }
    let daemon: Value =
        serde_json::from_str(&checked(&["info", "--format", "{{json .}}"])?).map_err(err)?;
    if daemon["OSType"] != "linux" {
        return Err(err("proof-executor-linux-required"));
    }
    let files = snapshot(target, config)?;
    let scratch = scratch_paths(config, &files)?;
    Ok(
        json!({"kind":KIND,"transport":crate::native_proof::binary(&docker()?)?,"image":details["Id"],"daemon":daemon["ID"],"source_revision":identity(&files)?,
        "configuration":config,"host_mounts":false,"network":"none","source_access":"read-only",
        "temporary_storage_bytes":536870912_u64 + scratch.len() as u64 * 2147483648_u64,"max_processes":128}),
    )
}

/// Docker resource IDs are obtained from successful creates, never adopted from
/// a name supplied by a caller. Cleanup failure leaves the attempt uncertain.
struct Resources {
    containers: Vec<String>,
    volume: Option<String>,
}
impl Resources {
    fn cleanup(&mut self) -> Result<(), CoreError> {
        for id in self.containers.iter().rev() {
            checked(&["rm", "--force", id])?;
        }
        self.containers.clear();
        if let Some(volume) = &self.volume {
            checked(&["volume", "rm", volume])?;
        }
        self.volume = None;
        Ok(())
    }
}
impl Drop for Resources {
    fn drop(&mut self) {
        let _ = self.cleanup();
    }
}

pub(crate) fn execute(
    target: &Path,
    invocation: &Value,
    command: &str,
    seconds: u64,
) -> Result<Value, CoreError> {
    let observed = &invocation["arguments"]["selection"]["proof_subject"]["runtime"]["executor"];
    let config = &observed["configuration"];
    if observe(target, config)? != *observed {
        return Err(err("proof-executor-changed-before-launch"));
    }
    let files = snapshot(target, config)?;
    if identity(&files)? != observed["source_revision"] {
        return Err(err("proof-snapshot-changed-before-launch"));
    }
    // Transfer the bytes just observed directly. A mutable on-disk archive would
    // create another unadmitted input between snapshot identity and execution.
    let mut tar = tar::Builder::new(Vec::new());
    let scratch = scratch_paths(config, &files)?;
    for path in &scratch {
        let mut header = tar::Header::new_gnu();
        header.set_entry_type(tar::EntryType::Directory);
        header.set_size(0);
        header.set_mode(0o777);
        header.set_uid(0);
        header.set_gid(0);
        header.set_mtime(0);
        header.set_cksum();
        tar.append_data(&mut header, path, std::io::empty())
            .map_err(err)?;
    }
    for (path, bytes) in files {
        let mut header = tar::Header::new_gnu();
        header.set_size(bytes.len() as u64);
        header.set_mode(0o555);
        header.set_uid(0);
        header.set_gid(0);
        header.set_mtime(0);
        header.set_cksum();
        tar.append_data(&mut header, path, bytes.as_slice())
            .map_err(err)?;
        if tar.get_ref().len() > 160 * 1024 * 1024 - 1024 {
            return Err(err("proof-snapshot-transfer-capacity-exceeded"));
        }
    }
    let bytes = tar.into_inner().map_err(err)?;
    let image = observed["image"]
        .as_str()
        .ok_or_else(|| err("proof-executor-image-missing"))?;
    let label = format!("aw.proof.attempt={}", digest(invocation)?);
    let mut resources = Resources {
        containers: Vec::new(),
        volume: None,
    };
    let volume = checked(&["volume", "create", "--label", &label])?;
    resources.volume = Some(volume.clone());
    let writable = format!("type=volume,source={volume},target=/workspace,volume-nocopy");
    // This staging container is never started. Docker copies regular tar entries
    // into a new private volume; no repository process runs with write access.
    let staging = checked(&[
        "create",
        "--label",
        &label,
        "--network",
        "none",
        "--read-only",
        "--mount",
        &writable,
        "--entrypoint",
        "/bin/true",
        image,
    ])?;
    resources.containers.push(staging.clone());
    let mut copy = Command::new(docker()?);
    copy.args(["cp", "-", &format!("{staging}:/workspace")]);
    let copied = crate::process_execution::run_with_input_limit(
        copy,
        Some(bytes),
        Duration::from_secs(60),
        160 * 1024 * 1024,
    )?;
    if copied["status"] != "passed" {
        return Err(err("proof-snapshot-transfer-failed"));
    }
    let readonly = format!("{writable},readonly");
    let deadline = seconds.to_string();
    // Root supervises the deadline. The proof drops UID, groups and all caps,
    // so it cannot stop its supervisor to outlive an interrupted native caller.
    let mut args = vec![
        "create",
        "--label",
        &label,
        "--network",
        "none",
        "--read-only",
        "--mount",
        &readonly,
        "--tmpfs",
        "/tmp:rw,exec,nosuid,nodev,size=536870912,mode=1777",
        "--cap-drop=ALL",
        "--cap-add=SETUID",
        "--cap-add=SETGID",
        "--cap-add=SETPCAP",
        "--cap-add=KILL",
        "--security-opt=no-new-privileges",
        "--pids-limit=128",
        "--memory=4g",
        "--cpus=2",
        "--user=0:0",
        "--workdir=/workspace",
        "--entrypoint=/usr/bin/timeout",
    ];
    let mounts: Vec<String> = scratch
        .iter()
        .map(|path| format!("/workspace/{path}:rw,exec,nosuid,nodev,size=2147483648,mode=1777"))
        .collect();
    for mount in &mounts {
        args.extend(["--tmpfs", mount]);
    }
    args.extend([
        image,
        "--signal=KILL",
        &deadline,
        "/usr/bin/setpriv",
        "--reuid=10001",
        "--regid=10001",
        "--clear-groups",
        "--bounding-set=-all",
        "--inh-caps=-all",
        "--ambient-caps=-all",
        "--no-new-privs",
        "/usr/bin/env",
    ]);
    // Source environment applies only after dropping privileges. It cannot
    // preload code into, or otherwise reconfigure, the root deadline supervisor.
    let environment: Vec<String> = config["environment"]
        .as_object()
        .into_iter()
        .flatten()
        .map(|(key, value)| format!("{key}={}", value.as_str().unwrap()))
        .collect();
    args.extend(environment.iter().map(String::as_str));
    args.extend(["/bin/sh", "-ec", command]);
    let worker = checked(&args)?;
    resources.containers.push(worker.clone());
    let mut result = run(
        &["start", "--attach", &worker],
        Duration::from_secs(seconds + 10),
    )?;
    resources.cleanup()?;
    result["execution_kind"] = json!(KIND);
    Ok(result)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn source_transfer_rejects_escape_links_special_files_and_scratch_masks() {
        let path = std::env::temp_dir().join(format!(
            "aw-proof-inputs-{}-{}",
            std::process::id(),
            std::time::SystemTime::now()
                .duration_since(std::time::UNIX_EPOCH)
                .unwrap()
                .as_nanos()
        ));
        std::fs::create_dir(&path).unwrap();
        std::fs::create_dir(path.join("source")).unwrap();
        std::fs::write(path.join("source/input"), "current").unwrap();
        let files = snapshot(&path, &json!({"inputs":["source"]})).unwrap();
        assert_eq!(files["source/input"], b"current");
        assert!(snapshot(&path, &json!({"inputs":["../outside"]})).is_err());
        assert!(scratch_paths(&json!({"scratch_paths":["source"]}), &files).is_err());
        assert!(scratch_paths(&json!({"scratch_paths":["source/input/child"]}), &files).is_err());
        assert!(scratch_paths(&json!({"scratch_paths":["build"]}), &files).is_ok());
        #[cfg(unix)]
        {
            std::os::unix::fs::symlink("source", path.join("link")).unwrap();
            let _socket = std::os::unix::net::UnixListener::bind(path.join("socket")).unwrap();
            assert!(snapshot(&path, &json!({"inputs":["socket"]})).is_err());
        }
        #[cfg(windows)]
        junction::create(path.join("source"), path.join("link")).unwrap();
        assert!(snapshot(&path, &json!({"inputs":["link/input"]})).is_err());
        assert!(snapshot(&path, &json!({"inputs":["link"]})).is_err());
        #[cfg(windows)]
        junction::delete(path.join("link")).unwrap();
        std::fs::remove_dir_all(path).unwrap();
    }
}
