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
#[cfg(any(windows, test))]
use std::{collections::BTreeSet, time::Instant};

const MAX_BYTES: usize = 128 * 1024 * 1024;
const MAX_FILES: usize = 20000;
pub(crate) const KIND: &str = "docker-readonly-source-v1";
pub(crate) fn missing_declaration_recovery() -> Value {
    json!({"kind":"capability-gap","cause":"missing-executor-declaration","human_answer_allowed":false,
        "runtime_checks":"not-performed",
        "configuration":{"reference":".agentic-workspace/verification/manifest.toml","section":"execution",
            "kind":KIND,"required_fields":["kind","inputs"]},
        "next_action":{"kind":"configure-executor","reselect_request":"verification/execute-selected/v1"},
        "detail":"Declare [execution] in .agentic-workspace/verification/manifest.toml with kind = \"docker-readonly-source-v1\" and explicit bounded inputs for the selected command, then configure an immutable image and reselect verification/execute-selected/v1. Local [proof_execution].image only overrides an already declared executor; it does not enable one. Docker/runtime checks were not performed. Source protection remains enforced; human approval cannot supply the execution boundary."})
}
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

struct SourceFile {
    bytes: Vec<u8>,
    executable: bool,
}

fn input_paths(config: &Value) -> Result<Vec<&str>, CoreError> {
    config["inputs"]
        .as_array()
        .filter(|v| !v.is_empty() && v.len() <= 128)
        .ok_or_else(|| err("proof-executor-inputs-required"))?
        .iter()
        .map(|input| {
            input
                .as_str()
                .filter(|p| relative(p) && p.split('/').count() <= 64)
                .ok_or_else(|| err("proof-executor-input-invalid"))
        })
        .collect()
}

// Windows has no dependable checkout execute bit. Git's stage-zero regular-file
// mode is its bounded authority; untracked inputs are conservatively non-executable.
// Conflicted/non-regular index entries cannot silently acquire a regular mode.
#[cfg(any(windows, test))]
fn indexed_modes(
    target: &Path,
    config: &Value,
) -> Result<BTreeMap<String, Option<bool>>, CoreError> {
    let inputs = input_paths(config)?;
    let mut queries = vec![
        inputs
            .iter()
            .map(|p| format!(":(literal){p}"))
            .collect::<Vec<_>>(),
    ];
    let mut ancestors: BTreeMap<usize, BTreeSet<String>> = BTreeMap::new();
    for input in &inputs {
        let mut parent = Path::new(input).parent();
        while let Some(parent_path) = parent.filter(|p| !p.as_os_str().is_empty()) {
            let path = parent_path.to_str().unwrap().replace('\\', "/");
            if !inputs
                .iter()
                .any(|input| path == *input || path.starts_with(&format!("{input}/")))
            {
                ancestors
                    .entry(path.split('/').count())
                    .or_default()
                    .insert(path.clone());
            }
            parent = parent_path.parent();
        }
    }
    // Exact ancestors can carry a gitlink or conflict above an otherwise
    // untracked file. Query one depth at a time and exclude descendants, so
    // observing an ancestor never imports its unrelated directory contents.
    for paths in ancestors.values() {
        let mut specs = Vec::new();
        for path in paths {
            specs.push(format!(":(literal){path}"));
            let escaped: String = path
                .chars()
                .flat_map(|c| {
                    if matches!(c, '*' | '?' | '[' | ']' | '\\') {
                        vec!['\\', c]
                    } else {
                        vec![c]
                    }
                })
                .collect();
            specs.push(format!(":(exclude,glob){escaped}/**"));
        }
        queries.push(specs);
    }
    let deadline = Instant::now() + Duration::from_secs(5);
    let mut modes = BTreeMap::new();
    for specs in queries {
        let remaining = deadline.saturating_duration_since(Instant::now());
        if remaining.is_zero() {
            return Err(err("proof-snapshot-index-mode-observation-timed-out"));
        }
        let mut command = Command::new("git");
        command
            .arg("-C")
            .arg(target)
            .args([
                "-c",
                "core.fsmonitor=false",
                "ls-files",
                "--stage",
                "-z",
                "--",
            ])
            .args(specs)
            .env("GIT_OPTIONAL_LOCKS", "0")
            .env("GIT_LITERAL_PATHSPECS", "0")
            .env("GIT_GLOB_PATHSPECS", "0")
            .env("GIT_NOGLOB_PATHSPECS", "0")
            .env("GIT_ICASE_PATHSPECS", "0");
        let (status, bytes) = crate::native_verification::bounded_git_output_with_limit(
            &mut command,
            remaining,
            8 * 1024 * 1024,
        )
        .map_err(err)?;
        if !status.success() {
            return Err(err(
                "proof-snapshot-index-mode-unavailable: Windows requires an observable Git index; preserve source and restore Git access",
            ));
        }
        let mut observed = BTreeMap::new();
        for entry in bytes
            .split(|byte| *byte == 0)
            .filter(|entry| !entry.is_empty())
        {
            let entry = std::str::from_utf8(entry)
                .map_err(|_| err("proof-snapshot-index-path-unsupported"))?;
            let (header, path) = entry
                .split_once('\t')
                .ok_or_else(|| err("proof-snapshot-index-entry-invalid"))?;
            let fields: Vec<_> = header.split(' ').collect();
            if fields.len() != 3 || !relative(path) {
                return Err(err("proof-snapshot-index-entry-invalid"));
            }
            let executable = match (fields[0], fields[2]) {
                ("100644", "0") => Some(false),
                ("100755", "0") => Some(true),
                _ => None,
            };
            let prior = observed.insert(path.to_owned(), executable);
            if prior.is_some() {
                observed.insert(path.to_owned(), None);
            }
        }
        modes.extend(observed);
    }
    Ok(modes)
}

/// Read confined regular sources and their executable property. No source script
/// runs; Windows reads bounded Git index metadata without mutating the checkout.
fn snapshot(target: &Path, config: &Value) -> Result<BTreeMap<String, SourceFile>, CoreError> {
    #[cfg(windows)]
    let modes = Some(indexed_modes(target, config)?);
    #[cfg(not(windows))]
    let modes = None;
    snapshot_with_modes(target, config, modes.as_ref())
}
fn snapshot_with_modes(
    target: &Path,
    config: &Value,
    modes: Option<&BTreeMap<String, Option<bool>>>,
) -> Result<BTreeMap<String, SourceFile>, CoreError> {
    fn visit(
        root: &Dir,
        path: &str,
        files: &mut BTreeMap<String, SourceFile>,
        total: &mut usize,
        visited: &mut usize,
        modes: Option<&BTreeMap<String, Option<bool>>>,
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
                visit(root, &child, files, total, visited, modes)?;
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
            let executable = if let Some(modes) = modes {
                match modes.get(path) {
                    Some(Some(executable)) => *executable,
                    Some(None) => {
                        return Err(err(format!("proof-snapshot-index-mode-ambiguous:{path}")));
                    }
                    None => {
                        if modes.iter().any(|(parent, mode)| {
                            mode.is_none() && path.starts_with(&format!("{parent}/"))
                        }) {
                            return Err(err(format!("proof-snapshot-index-mode-ambiguous:{path}")));
                        }
                        false
                    }
                }
            } else {
                #[cfg(unix)]
                {
                    use cap_std::fs::PermissionsExt;
                    metadata.permissions().mode() & 0o111 != 0
                }
                #[cfg(not(unix))]
                {
                    return Err(err("proof-snapshot-executable-authority-unavailable"));
                }
            };
            files.insert(path.into(), SourceFile { bytes, executable });
        } else {
            return Err(err("proof-snapshot-special-file-unsupported"));
        }
        Ok(())
    }
    let root = Dir::open_ambient_dir(target, ambient_authority()).map_err(err)?;
    let inputs = input_paths(config)?;
    let mut files = BTreeMap::new();
    let mut total = 0;
    let mut visited = 0;
    for input in inputs {
        let path = input;
        // Check ancestors as well: a confined link is still not snapshot custody.
        let mut parent = Path::new(path);
        while !parent.as_os_str().is_empty() {
            if linked(&root.symlink_metadata(parent).map_err(err)?) {
                return Err(err("proof-snapshot-link-unsupported"));
            }
            parent = parent.parent().unwrap_or(Path::new(""));
        }
        visit(&root, path, &mut files, &mut total, &mut visited, modes)?;
    }
    Ok(files)
}
fn identity(files: &BTreeMap<String, SourceFile>) -> Result<String, CoreError> {
    use sha2::{Digest, Sha256};
    let entries: BTreeMap<_, _> = files
        .iter()
        .map(|(name, file)| (name, json!({"sha256":format!("{:x}", Sha256::digest(&file.bytes)),"executable":file.executable})))
        .collect();
    digest(&json!(entries))
}

fn scratch_paths(
    config: &Value,
    files: &BTreeMap<String, SourceFile>,
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

fn source_prerequisites(
    files: &BTreeMap<String, SourceFile>,
    subject: &Value,
) -> Result<(), CoreError> {
    for declaration in subject["requirements"].as_array().into_iter().flatten() {
        for input in declaration["source_inputs"]
            .as_array()
            .into_iter()
            .flatten()
        {
            let path = input
                .as_str()
                .filter(|p| relative(p))
                .ok_or_else(|| err("proof-prerequisite-source-invalid"))?;
            if !files.contains_key(path) {
                return Err(err(format!("proof-prerequisite-source-missing:{path}")));
            }
        }
    }
    Ok(())
}

fn image_path(value: &Value) -> Result<&str, CoreError> {
    value
        .as_str()
        .filter(|p| p.strip_prefix('/').is_some_and(relative))
        .ok_or_else(|| err("proof-prerequisite-image-path-invalid"))
}

// Only fixed, cheap capability checks run here. No source code or selected
// command executes, and no host/source mounts or writable image are supplied.
fn image_prerequisites(image: &str, subject: &Value) -> Result<(), CoreError> {
    let prefix = [
        "create",
        "--pull=never",
        "--network=none",
        "--read-only",
        "--cap-drop=ALL",
        "--security-opt=no-new-privileges",
        "--pids-limit=32",
        "--memory=64m",
        "--cpus=1",
        "--user=10001:10001",
    ];
    for declaration in subject["requirements"].as_array().into_iter().flatten() {
        let executables: Vec<&str> = declaration["image_executables"]
            .as_array()
            .into_iter()
            .flatten()
            .map(image_path)
            .collect::<Result<_, _>>()?;
        if !executables.is_empty() {
            let mut args = prefix.to_vec();
            args.extend(["--entrypoint=/bin/sh", image, "-ec",
                "for p do test -f \"$p\" && test -x \"$p\" || { printf '%s\\n' \"$p\"; exit 61; }; done", "prerequisites"]);
            args.extend(executables);
            let result = capability_probe(&args)?;
            if result["status"] != "passed" {
                return Err(err(format!(
                    "proof-prerequisite-image-executable-missing:{}",
                    result["output"]["stdout"]["tail"]
                )));
            }
        }
        let git = &declaration["git_subject"];
        if !git.is_null() {
            let path = image_path(&git["path"])?;
            let revision = git["revision"]
                .as_str()
                .filter(|r| r.len() == 40 && r.bytes().all(|b| b.is_ascii_hexdigit()))
                .ok_or_else(|| err("proof-prerequisite-git-revision-invalid"))?;
            let safe = format!("safe.directory={path}");
            let mut args = prefix.to_vec();
            args.extend([
                "--entrypoint=/usr/bin/git",
                image,
                "-c",
                &safe,
                "-C",
                path,
                "rev-parse",
                "--verify",
                "HEAD",
            ]);
            let result = capability_probe(&args)?;
            if result["status"] != "passed"
                || result["output"]["stdout"]["tail"].as_str().map(str::trim) != Some(revision)
            {
                return Err(err(format!(
                    "proof-prerequisite-git-subject-unavailable:{path}@{revision}"
                )));
            }
        }
    }
    Ok(())
}

fn capability_probe(args: &[&str]) -> Result<Value, CoreError> {
    let id = checked(args)?;
    let mut resources = Resources {
        containers: vec![id.clone()],
        volume: None,
    };
    let result = run(&["start", "--attach", &id], Duration::from_secs(10))?;
    resources.cleanup()?;
    Ok(result)
}

pub(crate) fn observe(target: &Path, config: &Value, subject: &Value) -> Result<Value, CoreError> {
    if config["kind"] != KIND {
        return Err(err("proof-executor-kind-unsupported"));
    }
    let files = snapshot(target, config)?;
    source_prerequisites(&files, subject)?;
    let scratch = scratch_paths(config, &files)?;
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
    image_prerequisites(
        details["Id"]
            .as_str()
            .ok_or_else(|| err("proof-executor-image-id-missing"))?,
        subject,
    )?;
    Ok(
        json!({"kind":KIND,"transport":crate::native_proof::binary(&docker()?)?,"image":details["Id"],"daemon":daemon["ID"],"source_revision":identity(&files)?,
        "configuration":config,"constructibility_subject":subject,"host_mounts":false,"network":"none","source_access":"read-only",
        "source_mode_authority":if cfg!(windows) {"git-index-stage-zero; untracked inputs non-executable; ambiguous inputs blocked"} else {"checkout executable bits"},
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
    let subject = &observed["constructibility_subject"];
    if subject["command"] != command || observe(target, config, subject)? != *observed {
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
    for (path, file) in files {
        let mut header = tar::Header::new_gnu();
        header.set_size(file.bytes.len() as u64);
        header.set_mode(if file.executable { 0o555 } else { 0o444 });
        header.set_uid(0);
        header.set_gid(0);
        header.set_mtime(0);
        header.set_cksum();
        tar.append_data(&mut header, path, file.bytes.as_slice())
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
        #[cfg(windows)]
        {
            assert!(
                Command::new("git")
                    .args(["init", "-q"])
                    .arg(&path)
                    .status()
                    .unwrap()
                    .success()
            );
        }
        let files = snapshot(&path, &json!({"inputs":["source"]})).unwrap();
        assert_eq!(files["source/input"].bytes, b"current");
        let subject = json!({"requirements":[{"source_inputs":["source/input"]}]});
        assert!(source_prerequisites(&files, &subject).is_ok());
        for missing in ["source/omitted", "../outside"] {
            assert!(
                source_prerequisites(
                    &files,
                    &json!({"requirements":[{"source_inputs":[missing]}]})
                )
                .is_err()
            );
        }
        assert!(image_path(&json!("/usr/bin/git")).is_ok());
        assert!(image_path(&json!("/usr/../outside")).is_err());
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

    #[test]
    fn indexed_executable_authority_is_explicit_and_binds_mode_only_changes() {
        let path = std::env::temp_dir().join(format!(
            "aw-proof-modes-{}-{}",
            std::process::id(),
            std::time::SystemTime::now()
                .duration_since(std::time::UNIX_EPOCH)
                .unwrap()
                .as_nanos()
        ));
        std::fs::create_dir_all(path.join("source")).unwrap();
        let git = |args: &[&str]| {
            let result = Command::new("git")
                .arg("-C")
                .arg(&path)
                .args(args)
                .output()
                .unwrap();
            assert!(
                result.status.success(),
                "{}",
                String::from_utf8_lossy(&result.stderr)
            );
        };
        git(&["init", "-q"]);
        for name in ["module.py", "run.sh", "untracked"] {
            std::fs::write(path.join("source").join(name), "same bytes").unwrap();
        }
        git(&["add", "source/module.py", "source/run.sh"]);
        git(&["update-index", "--chmod=+x", "source/run.sh"]);
        git(&["update-index", "--chmod=-x", "source/module.py"]);
        let config = json!({"inputs":["source"]});
        let modes = indexed_modes(&path, &config).unwrap();
        let first = snapshot_with_modes(&path, &config, Some(&modes)).unwrap();
        #[cfg(windows)]
        assert_eq!(
            identity(&snapshot(&path, &config).unwrap()).unwrap(),
            identity(&first).unwrap()
        );
        assert!(!first["source/module.py"].executable);
        assert!(
            first["source/run.sh"].executable,
            "tracked Git intent does not depend on POSIX checkout bits"
        );
        assert!(
            !first["source/untracked"].executable,
            "explicit conservative untracked policy"
        );
        git(&["update-index", "--chmod=-x", "source/run.sh"]);
        let current_modes = indexed_modes(&path, &config).unwrap();
        let changed = snapshot_with_modes(&path, &config, Some(&current_modes)).unwrap();
        #[cfg(windows)]
        assert_eq!(
            identity(&snapshot(&path, &config).unwrap()).unwrap(),
            identity(&changed).unwrap()
        );
        assert_eq!(first["source/run.sh"].bytes, changed["source/run.sh"].bytes);
        assert_ne!(identity(&first).unwrap(), identity(&changed).unwrap());
        let hash = Command::new("git")
            .arg("-C")
            .arg(&path)
            .args(["hash-object", "-w", "source/run.sh"])
            .output()
            .unwrap();
        assert!(hash.status.success());
        let hash = std::str::from_utf8(&hash.stdout).unwrap().trim();
        git(&["update-index", "--force-remove", "source/run.sh"]);
        let mut child = Command::new("git")
            .arg("-C")
            .arg(&path)
            .args(["update-index", "--index-info"])
            .stdin(std::process::Stdio::piped())
            .spawn()
            .unwrap();
        use std::io::Write;
        writeln!(
            child.stdin.take().unwrap(),
            "100644 {hash} 1\tsource/run.sh"
        )
        .unwrap();
        assert!(child.wait().unwrap().success());
        let ambiguous = indexed_modes(&path, &config).unwrap();
        assert_eq!(ambiguous["source/run.sh"], None);
        assert!(snapshot_with_modes(&path, &config, Some(&ambiguous)).is_err());
        #[cfg(windows)]
        assert!(snapshot(&path, &config).is_err());
        #[cfg(unix)]
        {
            use std::os::unix::fs::PermissionsExt;
            let ordinary = snapshot(&path, &config).unwrap();
            std::fs::set_permissions(
                path.join("source/run.sh"),
                std::fs::Permissions::from_mode(0o755),
            )
            .unwrap();
            let executable = snapshot(&path, &config).unwrap();
            assert_ne!(identity(&ordinary).unwrap(), identity(&executable).unwrap());
        }
        // Unrelated staged paths must not consume a tiny proof's mode budget.
        // These entries need no working-tree files, including on Windows.
        let mut child = Command::new("git")
            .arg("-C")
            .arg(&path)
            .args(["update-index", "--index-info"])
            .stdin(std::process::Stdio::piped())
            .spawn()
            .unwrap();
        let prefix = format!("unrelated/{}", format!("{}/", "x".repeat(200)).repeat(16));
        let mut input = child.stdin.take().unwrap();
        for n in 0..2700 {
            writeln!(input, "100644 {hash}\t{prefix}{n:04}").unwrap();
        }
        drop(input);
        assert!(child.wait().unwrap().success());
        let listing = Command::new("git")
            .arg("-C")
            .arg(&path)
            .args(["ls-files", "--stage", "-z"])
            .output()
            .unwrap();
        assert!(listing.status.success());
        assert!(listing.stdout.len() > 8 * 1024 * 1024);
        let tiny = json!({"inputs":["source/module.py"]});
        let scoped = indexed_modes(&path, &tiny).unwrap();
        let tiny_files = snapshot_with_modes(&path, &tiny, Some(&scoped)).unwrap();
        assert_eq!(tiny_files.len(), 1);
        assert!(!tiny_files["source/module.py"].executable);
        assert_eq!(
            scoped.len(),
            1,
            "unrelated index entries remain outside mode observation"
        );
        #[cfg(windows)]
        assert_eq!(
            identity(&snapshot(&path, &tiny).unwrap()).unwrap(),
            identity(&tiny_files).unwrap()
        );
        git(&["update-index", "--chmod=+x", "source/module.py"]);
        let scoped = indexed_modes(&path, &tiny).unwrap();
        let changed = snapshot_with_modes(&path, &tiny, Some(&scoped)).unwrap();
        assert_eq!(
            tiny_files["source/module.py"].bytes,
            changed["source/module.py"].bytes
        );
        assert_ne!(identity(&tiny_files).unwrap(), identity(&changed).unwrap());
        #[cfg(windows)]
        assert_eq!(
            identity(&snapshot(&path, &tiny).unwrap()).unwrap(),
            identity(&changed).unwrap()
        );
        std::fs::create_dir_all(path.join("source/分组")).unwrap();
        std::fs::write(path.join("source/分组/input"), "untracked within gitlink").unwrap();
        git(&[
            "update-index",
            "--add",
            "--cacheinfo",
            &format!("160000,{hash},source/分组"),
        ]);
        let nested = json!({"inputs":["source/分组/input"]});
        let nested_modes = indexed_modes(&path, &nested).unwrap();
        assert_eq!(nested_modes["source/分组"], None);
        assert_eq!(nested_modes.len(), 1);
        assert!(snapshot_with_modes(&path, &nested, Some(&nested_modes)).is_err());
        #[cfg(windows)]
        assert!(snapshot(&path, &nested).is_err());
        std::fs::remove_dir_all(path).unwrap();
    }
}
