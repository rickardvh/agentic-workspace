//! Bounded scratch and Git worktree resources. No policy store or session registry.
//! Git owns worktree registrations; the existing ownership ledger classifies local state.
use crate::{CoreError, digest};
use cap_std::{
    ambient_authority,
    fs::{Dir, OpenOptions},
};
use serde::Deserialize;
use serde_json::{Value, json};
use std::{
    fs,
    io::{Read, Write},
    path::{Path, PathBuf},
    process::Command,
    time::Duration,
};
const LOCAL: &str = ".agentic-workspace/local";
const SCRATCH: &str = ".agentic-workspace/local/scratch";
const MARKER: &str = ".aw-scratch.json";
const REMOVAL_LOCK: &str = ".agentic-workspace/local/effects/resources.lock";

#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct RemovalCustody {
    attempt: crate::attempt_store::Evidence,
    committed: Option<Value>,
}

fn producer() -> &'static str {
    static PRODUCER: std::sync::LazyLock<String> =
        std::sync::LazyLock::new(|| digest(&json!(include_str!("native_resources.rs"))).unwrap());
    &PRODUCER
}

fn removal_path(relative: &str) -> Result<String, CoreError> {
    let id = relative
        .strip_prefix(&format!("{SCRATCH}/"))
        .filter(|id| id.len() == 64 && id.bytes().all(|b| b.is_ascii_hexdigit()))
        .ok_or_else(|| {
            err("scratch operation requires one exact task container below local/scratch")
        })?;
    Ok(format!(
        ".agentic-workspace/local/effects/scratch-{id}.prepared.json"
    ))
}

fn container_identity(path: &Path) -> Result<Value, CoreError> {
    unlinked(path)?;
    let metadata = fs::metadata(path).map_err(err)?;
    if !metadata.is_dir() {
        return Err(err("scratch container is not a directory; preserve"));
    }
    let created = metadata.created().ok();
    #[cfg(windows)]
    if created.is_none() {
        return Err(err("scratch creation identity unavailable; preserve"));
    }
    let mut identity = json!({"created":created});
    #[cfg(unix)]
    {
        use std::os::unix::fs::MetadataExt;
        identity["device"] = json!(metadata.dev());
        identity["inode"] = json!(metadata.ino());
    }
    Ok(identity.take())
}

fn resource_lock(target: &Path, root: &Dir) -> Result<std::fs::File, CoreError> {
    unlinked(&target.join(REMOVAL_LOCK))?;
    root.create_dir_all(".agentic-workspace/local/effects")
        .map_err(err)?;
    let file = root
        .open_with(
            REMOVAL_LOCK,
            OpenOptions::new().read(true).write(true).create(true),
        )
        .map_err(err)?
        .into_std();
    if file.metadata().map_err(err)?.len() != 0 {
        return Err(err("unrecognized resource lock preserved"));
    }
    file.try_lock().map_err(err)?;
    Ok(file)
}

fn removal_record(target: &Path, relative: &str) -> Result<Option<Value>, CoreError> {
    let path = removal_path(relative)?;
    unlinked(&target.join(&path))?;
    let root = Dir::open_ambient_dir(target, ambient_authority()).map_err(err)?;
    let Some(record) = crate::current_projection::read(&root, &path)? else {
        return Ok(None);
    };
    let custody: RemovalCustody = serde_json::from_value(record["custody"].clone()).map_err(err)?;
    let attempt = crate::attempt_store::read_source(target.to_str().unwrap(), &custody.attempt)?;
    let invocation = &record["invocation"];
    let paths = crate::attempt_store::write_paths(invocation)?;
    if record != json!({"invocation":invocation,"custody":record["custody"]})
        || attempt["invocation"] != *invocation
        || record["custody"]["attempt"]["path"] != paths[0]
        || custody.committed.is_some()
        || invocation["source_owner"] != "workspace-resources"
        || invocation["operation_id"] != "workspace.resources.scratch-remove"
        || invocation["operation_revision"] != producer()
        || invocation["arguments"]["target"] != json!(target)
        || invocation["arguments"]["request"]["path"] != relative
        || invocation["arguments"]["request"]["operation"] != "scratch-remove"
        || invocation["arguments"]["request"]["expected_revision"] != invocation["idempotency_key"]
        || invocation["arguments"]["removal"]["snapshot"]["status"] != "present"
        || invocation["arguments"]["removal"]["snapshot"]["marker"]["retain"] != false
    {
        return Err(err(
            "scratch removal lacks exact owner attempt custody; preserve",
        ));
    }
    Ok(Some(record))
}

fn removal_snapshot(
    target: &Path,
    relative: &str,
    task: &str,
    changed: &[String],
    policy_revision: &str,
) -> Result<(Value, Option<Value>), CoreError> {
    let record = removal_record(target, relative)?;
    let Some(record) = record else {
        return Ok((scratch_snapshot(target, relative, None)?, None));
    };
    let arguments = &record["invocation"]["arguments"];
    if arguments["task"] != task
        || arguments["changed"] != json!(changed)
        || arguments["removal"]["policy_revision"] != policy_revision
    {
        return Err(err(
            "scratch removal task/path or current policy changed; preserve",
        ));
    }
    let path = target.join(relative);
    unlinked(&path)?;
    let mut snapshot = if path.exists() {
        if container_identity(&path)? != arguments["removal"]["container_identity"] {
            return Err(err("scratch removal container identity changed; preserve"));
        }
        unlinked(&path.join(MARKER))?;
        if path.join(MARKER).exists()
            && scratch_snapshot(target, relative, None)? != arguments["removal"]["snapshot"]
        {
            return Err(err(
                "scratch removal custody or retention changed; preserve",
            ));
        }
        arguments["removal"]["snapshot"].clone()
    } else {
        json!({"status":"absent"})
    };
    snapshot["removal_attempt"] = json!(digest(&record)?);
    Ok((snapshot, Some(record)))
}

fn remove_scratch(
    target: &Path,
    relative: &str,
    invocation: &Value,
    snapshot: &Value,
    policy_revision: &str,
    previous: Option<&Value>,
    observe: &mut dyn FnMut(&str) -> Result<(), CoreError>,
) -> Result<(), CoreError> {
    let root = Dir::open_ambient_dir(target, ambient_authority()).map_err(err)?;
    let record = if let Some(record) = previous {
        record.clone()
    } else {
        let mut invocation = invocation.clone();
        invocation["arguments"]["removal"] = json!({"snapshot":snapshot,"policy_revision":policy_revision,
            "container_identity":container_identity(&target.join(relative))?});
        let admission = crate::attempt_store::admit(json!({"target":target,
            "decision":{"ready_actions":[invocation]},"invocation":invocation}))?;
        let record = json!({"invocation":invocation,"custody":admission["custody"]});
        crate::current_projection::write(&root, &removal_path(relative)?, &record)?;
        record
    };
    observe("custody-retained")?;
    if target.join(relative).exists() {
        // The external exact attempt survives loss of the in-tree marker.
        root.remove_dir_all(relative).map_err(err)?;
    }
    match root.symlink_metadata(relative) {
        Err(error) if error.kind() == std::io::ErrorKind::NotFound => (),
        Err(error) => return Err(err(error)),
        Ok(_) => return Err(err("scratch removal absence not confirmed")),
    }
    observe("container-absent")?;
    // This short-lived owner projection and its immutable admission serve only
    // the pending removal. No scratch history or independent registry survives.
    let evidence = serde_json::from_value(record["custody"]["attempt"].clone()).map_err(err)?;
    crate::attempt_store::read_source(target.to_str().unwrap(), &evidence)?;
    root.remove_file(removal_path(relative)?).map_err(err)?;
    root.remove_file(record["custody"]["attempt"]["path"].as_str().unwrap())
        .map_err(err)?;
    Ok(())
}

fn err(e: impl ToString) -> CoreError {
    CoreError::new(e.to_string())
}
#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct Input {
    target: String,
    #[serde(default)]
    task: String,
    #[serde(default)]
    changed: Vec<String>,
    request: Request,
}
#[derive(Clone, Deserialize, serde::Serialize)]
#[serde(deny_unknown_fields)]
struct Request {
    operation: String,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    route_request: Option<Value>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    planning_request: Option<Value>,
    path: Option<String>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    selection: Option<String>,
    need: Option<String>,
    base: Option<String>,
    reason: Option<String>,
    policy_revision: Option<String>,
    policy_answer: Option<String>,
    expected_revision: Option<String>,
    #[serde(default)]
    disposable_outputs: Vec<String>,
}
fn linked(meta: &fs::Metadata) -> bool {
    if meta.file_type().is_symlink() {
        return true;
    }
    #[cfg(windows)]
    {
        use std::os::windows::fs::MetadataExt;
        if meta.file_attributes() & 0x400 != 0 {
            return true;
        }
    }
    false
}
fn unlinked(path: &Path) -> Result<(), CoreError> {
    for part in path.ancestors() {
        match fs::symlink_metadata(part) {
            Ok(m) if linked(&m) => {
                return Err(err(
                    "resource path contains a link; preserve and reconcile exact path",
                ));
            }
            Ok(_) => (),
            Err(e) if e.kind() == std::io::ErrorKind::NotFound => (),
            Err(e) => return Err(err(e)),
        }
    }
    Ok(())
}
fn git(target: &Path, args: &[&str]) -> Result<String, CoreError> {
    let mut command = Command::new("git");
    command.arg("-C").arg(target).args(args);
    let result = crate::process_execution::run(command, None, Duration::from_secs(30))?;
    if result["status"] != "passed" {
        return Err(err(format!(
            "Git resource operation did not complete: {result}; inspect the exact resource before retrying"
        )));
    }
    if result["output"]["stdout"]["truncated"] == true {
        return Err(err(
            "Git resource observation exceeded bounded output; preserve state",
        ));
    }
    Ok(result["output"]["stdout"]["tail"]
        .as_str()
        .unwrap_or("")
        .to_owned())
}
fn policy(
    target: &Path,
    changed: &[String],
    targets: &[String],
    route: &Value,
) -> Result<Value, CoreError> {
    let config = crate::native_config::view(target)?;
    if config["sources"]
        .as_array()
        .into_iter()
        .flatten()
        .any(|s| s["status"] == "invalid")
    {
        return Err(err(
            "current configuration is invalid; preserve resources and reconcile its owner",
        ));
    }
    let instructions = crate::native_instructions::resolve_with_targets(
        target,
        changed,
        route,
        config["admissions"]["instruction_revision"]
            .as_str()
            .unwrap_or(""),
        targets,
    )?;
    if instructions["sources"]
        .as_array()
        .into_iter()
        .flatten()
        .any(|s| s["valid"] != true)
    {
        return Err(err(
            "current instruction source is invalid; reconcile through its owner before resource effects",
        ));
    }
    let startup = if let Some(reference) = config["agent_instructions_file"].as_str() {
        crate::decision_source::relative(reference)?;
        let root = Dir::open_ambient_dir(target, ambient_authority()).map_err(err)?;
        crate::native_planning::read(&root, reference)?.map(|bytes| json!({"reference":reference,"text":String::from_utf8_lossy(&bytes),"revision":digest(&json!(bytes)).unwrap()}))
    } else {
        None
    };
    Ok(
        json!({"configuration_revision":config["revision"],"startup":startup,"instructions":instructions["sources"]}),
    )
}
fn audit(target: &Path) -> Result<Value, CoreError> {
    let path = target.join(LOCAL);
    unlinked(&path)?;
    let ledger_path = target.join(".agentic-workspace/OWNERSHIP.toml");
    unlinked(&ledger_path)?;
    let text = if ledger_path.exists() {
        fs::read_to_string(&ledger_path).map_err(err)?
    } else {
        include_str!("../payload/.agentic-workspace/OWNERSHIP.toml").to_owned()
    };
    let ledger: toml::Value = toml::from_str(&text).map_err(err)?;
    let mut rows = Vec::new();
    if path.exists() {
        for entry in fs::read_dir(path).map_err(err)? {
            if rows.len() >= 1024 {
                return Err(err(
                    "local root exceeds bounded hygiene inventory; preserve residue and inspect exact entries",
                ));
            }
            let entry = entry.map_err(err)?;
            let name = entry.file_name().to_string_lossy().into_owned();
            let reference = format!("{LOCAL}/{name}");
            let owner = ledger
                .get("managed_surfaces")
                .and_then(toml::Value::as_array)
                .into_iter()
                .flatten()
                .find(|s| {
                    s.get("path")
                        .and_then(toml::Value::as_str)
                        .is_some_and(|p| p.trim_end_matches('/') == reference)
                })
                .and_then(|s| s.get("module"))
                .and_then(toml::Value::as_str);
            rows.push(json!({"path":reference,"class":if name=="scratch" {"disposable-task-containers"} else if owner.is_some() {"structured-owner-state"} else {"unowned-residue"},"owner":owner,
                "recovery":if owner.is_some(){"preserve; use current owner"}else{"preserve existing bytes; identify current references/owner, then explicitly relocate disposable material into task scratch"}}));
        }
    }
    rows.sort_by_key(|r| r["path"].as_str().unwrap().to_owned());
    Ok(
        json!({"kind":"agentic-workspace/local-hygiene/v1","entries":rows,"authority":"classification-only; ignored is not disposable","source_revision":digest(&json!(text))?}),
    )
}
// The custody marker authenticates the disposable container. Contents are not
// an inventory, a revision dependency, or a source of deletion authority.
fn scratch_snapshot(
    target: &Path,
    relative: &str,
    selection: Option<&str>,
) -> Result<Value, CoreError> {
    let path = target.join(relative);
    unlinked(&path)?;
    if !path.exists() {
        return Ok(json!({"status":"absent"}));
    }
    let dir = Dir::open_ambient_dir(&path, ambient_authority()).map_err(err)?;
    unlinked(&path.join(MARKER))?;
    let file = match dir.open(MARKER) {
        Ok(file) => file,
        Err(e)
            if e.kind() == std::io::ErrorKind::NotFound
                && dir.entries().map_err(err)?.next().is_none() =>
        {
            // A crash after mkdir may leave this exact empty directory. Only
            // creation may finish publishing custody; emptiness never grants
            // authority to remove an unauthenticated container.
            return Ok(json!({"status":"empty-interrupted"}));
        }
        Err(e) => return Err(err(e)),
    };
    let metadata = file.metadata().map_err(err)?;
    if !metadata.is_file() || metadata.len() > 16384 {
        return Err(err("invalid or oversized scratch marker preserved"));
    }
    let mut marker_bytes = Vec::new();
    file.take(16385)
        .read_to_end(&mut marker_bytes)
        .map_err(err)?;
    if marker_bytes.len() > 16384 {
        return Err(err("oversized scratch marker preserved"));
    }
    let marker: Value = serde_json::from_slice(&marker_bytes).map_err(err)?;
    if marker["kind"] != "agentic-workspace/task-scratch/v1"
        || marker["path"] != relative
        || marker["target"] != json!(target)
        || !marker["retain"].is_boolean()
        || !marker["task"].is_string()
        || relative
            != format!(
                "{SCRATCH}/{}",
                digest(&json!({"target":target,"task":marker["task"]}))?
                    .trim_start_matches("sha256:")
            )
    {
        return Err(err(
            "scratch custody differs; preserve contents and reconcile exact owner",
        ));
    }
    // Marker currentness is bounded. Directory modification time is excluded:
    // adding disposable contents must not invalidate container ownership.
    let marker_metadata = fs::metadata(path.join(MARKER)).map_err(err)?;
    let mut identity = json!({
        "created":marker_metadata.created().ok(),
        "modified":marker_metadata.modified().map_err(err)?,
        "container_created":fs::metadata(&path).map_err(err)?.created().ok()
    });
    #[cfg(unix)]
    {
        use std::os::unix::fs::MetadataExt;
        identity["device"] = json!(marker_metadata.dev());
        identity["inode"] = json!(marker_metadata.ino());
    }
    identity["marker_revision"] = json!(digest(&json!(marker_bytes))?);
    let mut snapshot = json!({"status":"present","marker":marker,"custody":identity});
    // Deprecated 1.x compatibility only. Ordinary container removal never
    // observes temporary contents or inherits this selected-file bound.
    if let Some(selected) = selection {
        crate::decision_source::relative(selected)?;
        if selected == MARKER {
            return Err(err("scratch marker is not a disposable selection"));
        }
        unlinked(&path.join(selected))?;
        let metadata = dir.symlink_metadata(selected).map_err(err)?;
        if !metadata.is_file() || metadata.len() > 16_777_216 {
            return Err(err(
                "selected scratch material must be one bounded regular file; preserve",
            ));
        }
        let mut bytes = Vec::new();
        dir.open(selected)
            .map_err(err)?
            .take(16_777_217)
            .read_to_end(&mut bytes)
            .map_err(err)?;
        if bytes.len() > 16_777_216 {
            return Err(err(
                "selected scratch material must be one bounded regular file; preserve",
            ));
        }
        snapshot["selection"] = json!({"path":selected,"revision":digest(&json!(bytes))?});
    }
    Ok(snapshot)
}
fn normalized_path(path: &Path) -> String {
    let text = path
        .to_string_lossy()
        .trim_start_matches(r"\\?\")
        .replace('\\', "/");
    #[cfg(windows)]
    let text = text.to_lowercase();
    text
}
fn worktrees(target: &Path, selected: &Path) -> Result<Vec<Value>, CoreError> {
    let text = git(target, &["worktree", "list", "--porcelain", "-z"])?;
    let mut rows: Vec<Value> = text
        .split("\0\0")
        .filter(|r| !r.is_empty())
        .map(|record| {
            let mut row = json!({});
            for line in record.split('\0').filter(|s| !s.is_empty()) {
                let (key, value) = line.split_once(' ').unwrap_or((line, ""));
                row[key] = json!(value);
            }
            row
        })
        .collect();
    let Some(row) = rows.iter_mut().find(|row| {
        normalized_path(Path::new(row["worktree"].as_str().unwrap_or("")))
            == normalized_path(selected)
    }) else {
        return Ok(rows);
    };
    let common = PathBuf::from(git(target, &["rev-parse", "--git-common-dir"])?.trim());
    let admin = if common.is_absolute() {
        common
    } else {
        target.join(common)
    }
    .join("worktrees");
    unlinked(&admin)?;
    if admin.exists() {
        for (index, entry) in fs::read_dir(&admin).map_err(err)?.enumerate() {
            if index >= 1024 {
                return Err(err("worktree registration set exceeds bounded recovery"));
            }
            let directory = entry.map_err(err)?.path();
            unlinked(&directory)?;
            let gitdir = directory.join("gitdir");
            unlinked(&gitdir)?;
            // Only the selected Git registration's resource data participates.
            if !gitdir.is_file()
                || normalized_path(Path::new(fs::read_to_string(&gitdir).map_err(err)?.trim()))
                    != normalized_path(&selected.join(".git"))
            {
                continue;
            }
            let marker = directory.join("aw-resource.json");
            unlinked(&marker)?;
            if marker.is_file() {
                if fs::metadata(&marker).map_err(err)?.len() > 16384 {
                    return Err(err("oversized resource custody preserved"));
                }
                let receipt: Value =
                    serde_json::from_slice(&fs::read(&marker).map_err(err)?).map_err(err)?;
                if receipt["kind"] != "agentic-workspace/worktree-resource/v1"
                    || receipt["origin"] != normalized_path(target)
                    || receipt["path"] != normalized_path(selected)
                {
                    return Err(err(
                        "worktree recovery custody differs; preserve exact registration",
                    ));
                }
                row["resource_custody"] = receipt;
            }
            break;
        }
    }
    Ok(rows)
}
// These are leases of empty tool-output roots, never a classification of arbitrary ignored files.
fn output_roots(value: &Value) -> Result<Vec<String>, CoreError> {
    let roots: Vec<String> = if value.is_null() {
        vec![]
    } else {
        serde_json::from_value(value.clone()).map_err(err)?
    };
    let mut seen = std::collections::BTreeSet::new();
    for root in &roots {
        if !matches!(root.as_str(), "target" | ".pytest_cache" | ".venv") || !seen.insert(root) {
            return Err(err(
                "disposable output must be a distinct supported tool root: target, .pytest_cache or .venv",
            ));
        }
    }
    Ok(roots)
}
fn worktree_status(path: &Path, outputs: &[String]) -> Result<String, CoreError> {
    let mut args = vec![
        "status",
        "--porcelain=v1",
        "-z",
        "--untracked-files=all",
        "--ignored=matching",
        "--",
        ".",
    ];
    let exclusions: Vec<_> = outputs
        .iter()
        .map(|root| format!(":(exclude){root}"))
        .collect();
    for root in outputs {
        unlinked(&path.join(root))?;
        // A subsequent commit cannot silently turn a leased output root into deletable source.
        if !git(path, &["ls-files", "--", root])?.trim().is_empty() {
            return Err(err(
                "tracked material occupies a disposable output root; preserve resource",
            ));
        }
    }
    args.extend(exclusions.iter().map(String::as_str));
    let raw = git(path, &args)?;
    // Git still reports explicitly ignored directories with --ignored=matching
    // even when pathspecs exclude them. Filter only untracked/ignored entries
    // inside the exact creation leases; NUL records avoid quoted-path ambiguity.
    Ok(raw
        .split('\0')
        .filter(|record| !record.is_empty())
        .filter(|record| {
            let candidate = record
                .strip_prefix("!! ")
                .or_else(|| record.strip_prefix("?? "));
            !candidate.is_some_and(|name| {
                outputs
                    .iter()
                    .any(|root| name == root || name.starts_with(&format!("{root}/")))
            })
        })
        .map(|record| format!("{record}\0"))
        .collect())
}
fn build_environment(path: &Path, outputs: &[String]) -> Value {
    let mut env = json!({});
    if outputs.iter().any(|s| s == "target") {
        env["CARGO_TARGET_DIR"] = json!(path.join("target"));
        env["PYTHONPYCACHEPREFIX"] = json!(path.join("target/python-cache"));
    } else {
        env["PYTHONDONTWRITEBYTECODE"] = json!("1");
    }
    if outputs.iter().any(|s| s == ".venv") {
        env["UV_PROJECT_ENVIRONMENT"] = json!(path.join(".venv"));
    }
    env
}
fn planning_continuity(input: &Input, target: &Path, seed: &str) -> Result<Value, CoreError> {
    if let Some(request) = &input.request.planning_request {
        let requests = request
            .as_array()
            .map(Vec::as_slice)
            .unwrap_or(std::slice::from_ref(request));
        if requests.iter().any(|r| {
            r["owner"] != "planning"
                || !matches!(
                    r["request_kind"].as_str(),
                    Some(
                        "planning/continuation/v1"
                            | "planning/posture/v1"
                            | "planning/select-owner/v1"
                    )
                )
        }) {
            return Err(err(
                "planning_request accepts only current Planning relation/posture requests",
            ));
        }
    }
    let current = crate::native_public::start(json!({"target":target,"task":input.task,
        "changed":input.changed,"request":input.request.planning_request}))?;
    let planning = &current["planning"];
    let mut result = json!({"planning":planning,"seed":seed,"status":"admitted"});
    if planning["task_relation"] == "unresolved"
        || matches!(
            planning["status"].as_str(),
            Some("stale" | "custody-required" | "independent")
        )
    {
        result["status"] = json!("relation-required");
    } else if planning["task_relation"] == "continues" {
        let owner = &planning["selected_owner"];
        let reference = owner["ref"]
            .as_str()
            .ok_or_else(|| err("continuing Planning owner reference missing"))?;
        crate::decision_source::relative(reference)?;
        result["required_owner"] = owner.clone();
        // Read the immutable seed, never copy local selectors or fabricate owner
        // custody in the destination. JSON equality permits Git EOL conversion.
        let entry = git(target, &["ls-tree", "--name-only", seed, "--", reference])?;
        if entry.trim().is_empty() {
            result["status"] = json!("owner-missing-from-seed");
        } else {
            let seed_text = git(target, &["show", &format!("{seed}:{reference}")])?;
            let seed_owner: Value = serde_json::from_str(&seed_text).map_err(err)?;
            let root = Dir::open_ambient_dir(target, ambient_authority()).map_err(err)?;
            let bytes = crate::native_planning::read(&root, reference)?
                .ok_or_else(|| err("continuing Planning owner disappeared"))?;
            let source_owner: Value = serde_json::from_slice(&bytes).map_err(err)?;
            result["seed_owner_revision"] = json!(digest(&seed_owner)?);
            if seed_owner != source_owner || seed_owner["id"] != owner["id"] {
                result["status"] = json!("owner-differs-at-seed");
            }
        }
    }
    Ok(result)
}

/// Read-only proposal first; effects require the exact freshly rederived revision.
/// No generic cache, session or resource registry is created.
pub fn view(value: Value) -> Result<Value, CoreError> {
    view_checked(value, &mut |_| Ok(()))
}

fn view_checked(
    value: Value,
    observe: &mut dyn FnMut(&str) -> Result<(), CoreError>,
) -> Result<Value, CoreError> {
    let input: Input = serde_json::from_value(value.clone()).map_err(err)?;
    let target = fs::canonicalize(&input.target).map_err(err)?;
    let request = &input.request;
    let requested_outputs = output_roots(&json!(request.disposable_outputs))?;
    if !requested_outputs.is_empty() && request.operation != "worktree-create" {
        return Err(err(
            "disposable outputs must be reserved at worktree creation, never adopted during cleanup",
        ));
    }
    if request.operation.ends_with("-create") && input.task.trim().is_empty() {
        return Err(err("resource creation requires explicit current work"));
    }
    if request.operation == "audit" {
        return audit(&target);
    }
    let mut changed = input.changed.clone();
    for path in &changed {
        crate::decision_source::relative(path)?;
    }
    changed.sort();
    changed.dedup();
    let work = json!({"kind":"current-work","id":digest(&json!({"target":target,"task":input.task,"changed":changed}))?});
    let catalogue = crate::native_routes::source(&target)?;
    let (route_source, _) = crate::native_routes::former_selection(&target, &catalogue)?;
    let routes = crate::semantic_routes::view(
        json!({"current_work":work,"source":route_source,"request":request.route_request}),
    )?;
    let task_id = digest(&json!({"target":target,"task":input.task}))?;
    let id = task_id.trim_start_matches("sha256:");
    let scratch = format!("{SCRATCH}/{id}");
    let relative = request.path.as_deref().unwrap_or(&scratch);
    let mut targets = if request.operation.starts_with("scratch") {
        vec![relative.to_owned(), format!("{relative}/**")]
    } else {
        vec![".git/worktrees/**".to_owned()]
    };
    if request.operation.starts_with("scratch") {
        targets.push(REMOVAL_LOCK.into());
    }
    if request.operation == "scratch-remove" {
        targets.push(removal_path(relative)?);
        targets.push(".agentic-workspace/local/effects/*.attempt.json".into());
    }
    let policy = policy(
        &target,
        &changed,
        &targets,
        &routes["decision"]["semantic_task_routes"],
    )?;
    let policy_revision = digest(&policy)?;
    let mut snapshot;
    let mut blockers = vec![];
    let path: PathBuf;
    let mut registration = Value::Null;
    let mut seed = String::new();
    let mut outputs = vec![];
    let mut removal = None;
    match request.operation.as_str() {
        "scratch-create" | "scratch-remove" | "scratch-prune" | "scratch-retain"
        | "scratch-release" => {
            crate::decision_source::relative(relative)?;
            if relative
                .strip_prefix(&format!("{SCRATCH}/"))
                .is_none_or(|s| s.is_empty() || s.contains('/'))
            {
                return Err(err(
                    "scratch operation requires one exact task container below local/scratch",
                ));
            }
            path = target.join(relative);
            if request.operation == "scratch-create" && relative != scratch {
                return Err(err(
                    "new scratch path must be derived from the explicit current work",
                ));
            }
            if (request.operation == "scratch-prune") != request.selection.is_some() {
                return Err(err(
                    "scratch-prune requires one explicit selection; other operations accept none",
                ));
            }
            if request.operation == "scratch-remove" {
                (snapshot, removal) =
                    removal_snapshot(&target, relative, &input.task, &changed, &policy_revision)?;
            } else {
                if removal_record(&target, relative)?.is_some() {
                    return Err(err(
                        "scratch has an interrupted removal; recover that exact scratch-remove before other operations",
                    ));
                }
                snapshot = scratch_snapshot(&target, relative, request.selection.as_deref())?;
            }
            if matches!(
                request.operation.as_str(),
                "scratch-remove" | "scratch-prune"
            ) && snapshot["status"] == "empty-interrupted"
            {
                blockers.push("missing scratch custody; preserve and recover exact task creation");
            }
            if matches!(
                request.operation.as_str(),
                "scratch-retain" | "scratch-release"
            ) && (snapshot["status"] != "present"
                || request
                    .reason
                    .as_deref()
                    .is_none_or(|s| s.trim().is_empty()))
            {
                blockers.push("retention disposition requires an existing task container and an explicit reason");
            }
            if matches!(
                request.operation.as_str(),
                "scratch-remove" | "scratch-prune"
            ) && snapshot["marker"]["retain"] == true
            {
                blockers.push("retained recovery material requires current owner disposition");
            }
        }
        "worktree-create" | "worktree-remove" => {
            let default = target
                .parent()
                .ok_or_else(|| err("repository has no parent"))?
                .join(".aw-worktrees")
                .join(id);
            let requested_path = request.path.as_ref().map(PathBuf::from).unwrap_or(default);
            // Git cannot create worktrees using Windows verbatim path syntax.
            // Keep display/effect spelling intact; normalized_path is comparison-only.
            let text = requested_path.to_string_lossy();
            let text = text.strip_prefix(r"\\?\").unwrap_or(&text);
            path = if let Some(unc) = text.strip_prefix(r"UNC\") {
                PathBuf::from(format!(r"\\{unc}"))
            } else {
                PathBuf::from(text)
            };
            if !path.is_absolute()
                || normalized_path(&path) == normalized_path(&target)
                || normalized_path(&path).starts_with(&format!("{}/", normalized_path(&target)))
                || path.to_string_lossy().chars().any(char::is_control)
                || path.components().any(|p| {
                    matches!(
                        p,
                        std::path::Component::ParentDir | std::path::Component::CurDir
                    )
                })
                || path
                    .components()
                    .any(|p| p.as_os_str() == ".agentic-workspace")
            {
                return Err(err(
                    "worktree must be an absolute external resource outside repository/AW state",
                ));
            }
            unlinked(&path)?;
            let parent = path.parent().ok_or_else(|| err("invalid worktree path"))?;
            if parent.exists() && fs::canonicalize(parent).map_err(err)?.starts_with(&target) {
                return Err(err("worktree parent resolves inside repository"));
            }
            let rows = worktrees(&target, &path)?;
            registration = rows
                .into_iter()
                .find(|r| {
                    normalized_path(Path::new(r["worktree"].as_str().unwrap_or("")))
                        == normalized_path(&path)
                })
                .unwrap_or(Value::Null);
            seed = git(
                &target,
                &[
                    "rev-parse",
                    "--verify",
                    "--end-of-options",
                    &format!("{}^{{commit}}", request.base.as_deref().unwrap_or("HEAD")),
                ],
            )?
            .trim()
            .to_owned();
            snapshot =
                json!({"registration":registration,"exists":path.exists(),"origin_head":seed});
            if request.operation == "worktree-create" {
                snapshot["continuity"] = planning_continuity(&input, &target, &seed)?;
                match snapshot["continuity"]["status"].as_str() {
                    Some("relation-required") => blockers.push("resolve the current Planning relation/posture or custody before isolating this work; carry the returned Planning request as planning_request"),
                    Some("owner-missing-from-seed" | "owner-differs-at-seed") => blockers.push("requested seed cannot represent the exact current Planning owner; use a commit containing that owner or establish independent work through Planning in the source checkout"),
                    _ => (),
                }
                outputs = requested_outputs;
                for output in &outputs {
                    if !git(&target, &["ls-tree", "--name-only", &seed, "--", output])?
                        .trim()
                        .is_empty()
                    {
                        blockers.push("source tree already owns a requested disposable output root; preserve it");
                    }
                }
                if !registration.is_null() || path.exists() {
                    blockers.push("destination already exists; inspect/recover it without creating another worktree");
                }
                if !matches!(
                    request.need.as_deref(),
                    Some(
                        "conflicting-checkout"
                            | "transport-requires-isolation"
                            | "destructive-validation"
                    )
                ) || request
                    .reason
                    .as_deref()
                    .is_none_or(|s| s.trim().is_empty())
                {
                    blockers.push("no concrete isolation need; use the existing checkout");
                }
                if request.policy_revision.as_deref() != Some(&policy_revision)
                    || request.policy_answer.as_deref() != Some("permits-isolation")
                {
                    blockers.push("current instruction consequence requires explicit scoped isolation judgment");
                }
            } else if !registration.is_null() {
                outputs = output_roots(&registration["resource_custody"]["disposable_outputs"])?;
                let lock = registration["locked"].as_str().unwrap_or("");
                let prefix = format!("aw-resource:{}:", digest(&json!(target))?);
                if !lock.starts_with(&prefix)
                    && registration["resource_custody"]["kind"]
                        != "agentic-workspace/worktree-resource/v1"
                {
                    blockers
                        .push("registration is not owned by this supported lifecycle; preserve it");
                }
                if path.exists() {
                    let status = worktree_status(&path, &outputs)?;
                    snapshot["status"] = json!(status);
                    if !status.trim().is_empty() {
                        blockers.push("dirty/untracked/ignored material must be preserved or explicitly reconciled before teardown");
                    }
                }
                let head = if path.exists() {
                    git(&path, &["rev-parse", "HEAD"])?
                } else {
                    registration["HEAD"].as_str().unwrap_or("").to_owned()
                };
                if head.trim().is_empty() {
                    return Err(err("worktree registration has no current commit; preserve"));
                }
                let retained = git(
                    &target,
                    &[
                        "for-each-ref",
                        "--contains",
                        head.trim(),
                        "--format=%(refname)",
                        "refs/heads",
                        "refs/remotes",
                        "refs/tags",
                    ],
                )?;
                snapshot["head"] = json!(head);
                snapshot["retained_refs"] = json!(retained);
                if retained.trim().is_empty() {
                    blockers.push("unique commits require retained integration before teardown");
                }
            } else if path.exists() {
                blockers.push("unregistered directory is not a disposable worktree");
            }
        }
        _ => {
            return Err(err(
                "unknown resource operation; use audit, scratch-create/remove or worktree-create/remove",
            ));
        }
    }
    let mut writes = if request.operation.starts_with("scratch") {
        vec![format!("{relative}/**")]
    } else {
        vec![".git/worktrees/**".to_owned()]
    };
    if request.operation == "scratch-remove" {
        writes.push(removal_path(relative)?);
        writes.push(".agentic-workspace/local/effects/*.attempt.json".into());
    }
    if request.operation.starts_with("scratch") {
        writes.push(REMOVAL_LOCK.into());
    }
    let mut route_unresolved = false;
    for source in policy["instructions"].as_array().into_iter().flatten() {
        if (source["applicable"] == true || source["applicability"]["status"] == "unresolved")
            && source["metadata"]["protect"]
                .as_array()
                .into_iter()
                .flatten()
                .filter_map(Value::as_str)
                .any(|pattern| {
                    writes.iter().any(|path| {
                        crate::instruction_applicability::patterns_overlap(pattern, path)
                    })
                })
        {
            route_unresolved |= source["applicability"]["status"] == "unresolved";
            blockers.push(if source["applicability"]["status"] == "unresolved" {
                "current instruction applicability is unresolved for this resource destination"
            } else {
                "current structured instruction protects this resource destination"
            });
        }
    }
    if (matches!(
        request.operation.as_str(),
        "scratch-remove" | "scratch-prune"
    ) && (snapshot["status"] == "present" || removal.is_some()))
        || (request.operation == "worktree-remove" && !registration.is_null())
    {
        let current = crate::native_public::start(
            json!({"target":target,"task":input.task,"changed":input.changed}),
        )?;
        fn referenced(value: &Value, reference: &str) -> bool {
            match value {
                Value::String(s) => {
                    s.contains(reference)
                        || normalized_path(Path::new(s))
                            .contains(&normalized_path(Path::new(reference)))
                }
                Value::Array(v) => v.iter().any(|x| referenced(x, reference)),
                Value::Object(v) => v.values().any(|x| referenced(x, reference)),
                _ => false,
            }
        }
        if [
            "planning",
            "memory",
            "verification",
            "decision_sources",
            "instructions",
            "assignment",
            "task_requirements",
            "independent_owners",
        ]
        .iter()
        .any(|key| referenced(&current[*key], relative))
        {
            blockers.push("current owner references this resource material; reconcile that owner before cleanup");
        }
    }
    let producer = producer();
    let revision = digest(
        &json!({"semantics":producer,"target":target,"task":input.task,"changed":input.changed,"operation":request.operation,"path":path,"snapshot":snapshot,"policy":policy,"need":request.need,"reason":request.reason,"disposable_outputs":outputs}),
    )?;
    let mut next = request.clone();
    next.path = Some(if request.operation.starts_with("scratch") {
        relative.to_owned()
    } else {
        path.to_string_lossy().into_owned()
    });
    next.expected_revision = Some(revision.clone());
    let mut result = json!({"kind":"agentic-workspace/resource-proposal/v1","operation":request.operation,"path":path,"revision":revision,"policy":policy,"policy_revision":policy_revision,"blockers":blockers,"snapshot":snapshot,"effect_outcome":"not-invoked","recovery":"Reobserve this exact path from a fresh process; never create a replacement merely to clean up."});
    if route_unresolved {
        result["route_requests"] = routes["requests"].clone();
    }
    if request.operation.starts_with("worktree") {
        result["disposable_outputs"] = json!(outputs);
        result["build_environment"] = build_environment(&path, &outputs);
    }
    if request.operation == "worktree-create" {
        result["planning"] = snapshot["continuity"]["planning"].clone();
        result["continuity"] = snapshot["continuity"].clone();
    }
    if !blockers.is_empty() {
        return Ok(result);
    }
    result["action"] =
        json!({"target":target,"task":input.task,"changed":input.changed,"request":next});
    let Some(expected) = &request.expected_revision else {
        return Ok(result);
    };
    if expected != &revision {
        return Err(err(
            "resource source/policy changed; reobserve exact path before effect",
        ));
    }
    let operation = format!("workspace.resources.{}", request.operation);
    let invocation = json!({"kind":"agentic-workspace/operation-invocation/v1","source_owner":"workspace-resources",
        "operation_id":operation,"operation_revision":producer,"idempotency_key":revision,
        "arguments":result["action"],"effects":["task-resource"],"expected_dependency_revision":revision});
    crate::admit_invocation_value(
        json!({"decision":{"ready_actions":[invocation]},"invocation":invocation}),
    )?;
    let root = Dir::open_ambient_dir(&target, ambient_authority()).map_err(err)?;
    let _lock = if request.operation.starts_with("scratch") {
        Some(resource_lock(&target, &root)?)
    } else {
        None
    };
    if request.operation.starts_with("scratch") {
        let mut fresh = value.clone();
        fresh["request"]["expected_revision"] = Value::Null;
        let observed = view(fresh)?;
        if observed["revision"] != revision
            || observed["blockers"]
                .as_array()
                .is_none_or(|b| !b.is_empty())
        {
            return Err(err(
                "resource sources changed at locked effect barrier; preserve and reobserve",
            ));
        }
    }
    unlinked(&path)?;
    let current_snapshot = if request.operation == "scratch-remove" {
        removal_snapshot(&target, relative, &input.task, &changed, &policy_revision)?.0
    } else if request.operation.starts_with("scratch") {
        if removal_record(&target, relative)?.is_some() {
            return Err(err("scratch removal appeared at effect barrier; preserve"));
        }
        scratch_snapshot(&target, relative, request.selection.as_deref())?
    } else {
        snapshot.clone()
    };
    if current_snapshot != snapshot {
        return Err(err(
            "scratch changed at effect barrier; preserve and reobserve",
        ));
    }
    let effected = match request.operation.as_str() {
        "scratch-create" => snapshot["status"] != "present",
        "scratch-remove" => snapshot["status"] != "absent",
        "worktree-remove" => !registration.is_null(),
        _ => true,
    };
    match request.operation.as_str() {
        "scratch-create" if snapshot["status"] != "present" => {
            let root = Dir::open_ambient_dir(&target, ambient_authority()).map_err(err)?;
            root.create_dir_all(SCRATCH).map_err(err)?;
            if snapshot["status"] == "absent" {
                root.create_dir(relative).map_err(err)?;
            }
            let marker = json!({"kind":"agentic-workspace/task-scratch/v1","target":target,"task":input.task,"path":relative,"retain":false});
            let mut file = root
                .open_with(
                    format!("{relative}/{MARKER}"),
                    OpenOptions::new().write(true).create_new(true),
                )
                .map_err(err)?;
            file.write_all(&serde_json::to_vec(&marker).map_err(err)?)
                .map_err(err)?;
            file.sync_all().map_err(err)?;
        }
        "scratch-remove" if snapshot["status"] == "present" || removal.is_some() => {
            remove_scratch(
                &target,
                relative,
                &invocation,
                &snapshot,
                &policy_revision,
                removal.as_ref(),
                observe,
            )?;
        }
        "scratch-prune" if snapshot["status"] == "present" => {
            let dir = Dir::open_ambient_dir(&path, ambient_authority()).map_err(err)?;
            // Same custody, policy, retention and owner-reference gates as removal,
            // but dispose only the exact bounded selection for existing 1.x clients.
            if scratch_snapshot(&target, relative, request.selection.as_deref())? != snapshot {
                return Err(err(
                    "scratch changed at deletion barrier; preserve and reobserve",
                ));
            }
            dir.remove_file(request.selection.as_deref().unwrap())
                .map_err(err)?;
        }
        "scratch-retain" | "scratch-release" => {
            let mut marker = snapshot["marker"].clone();
            marker["retain"] = json!(request.operation == "scratch-retain");
            marker["retention_reason"] = json!(request.reason);
            let dir = Dir::open_ambient_dir(&path, ambient_authority()).map_err(err)?;
            dir.write(MARKER, serde_json::to_vec(&marker).map_err(err)?)
                .map_err(err)?;
        }
        "worktree-create" => {
            if planning_continuity(&input, &target, &seed)? != snapshot["continuity"] {
                return Err(err(
                    "Planning continuity changed at worktree creation barrier; reobserve before effect",
                ));
            }
            fs::create_dir_all(path.parent().unwrap()).map_err(err)?;
            let reason = format!("aw-resource:{}:{seed}", digest(&json!(target))?);
            git(
                &target,
                &[
                    "worktree",
                    "add",
                    "--detach",
                    "--lock",
                    "--reason",
                    &reason,
                    path.to_str().ok_or_else(|| err("non-UTF8 path"))?,
                    &seed,
                ],
            )?;
            let admin = PathBuf::from(git(&path, &["rev-parse", "--absolute-git-dir"])?.trim());
            unlinked(&admin)?;
            let worktree = Dir::open_ambient_dir(&path, ambient_authority()).map_err(err)?;
            for output in &outputs {
                worktree.create_dir(output).map_err(err)?;
            }
            fs::write(admin.join("aw-resource.json"), serde_json::to_vec(&json!({
                "kind":"agentic-workspace/worktree-resource/v1", "origin":normalized_path(&target),
                "path":normalized_path(&path),"baseline":seed,"task":input.task,"need":request.need,"reason":request.reason,"disposable_outputs":outputs
            })).map_err(err)?).map_err(err)?;
        }
        "worktree-remove" if !registration.is_null() => {
            let p = path.to_str().ok_or_else(|| err("non-UTF8 path"))?;
            if path.exists() {
                let status = worktree_status(&path, &outputs)?;
                let head = git(&path, &["rev-parse", "HEAD"])?;
                if snapshot["status"] != status || snapshot["head"] != head {
                    return Err(err(
                        "worktree changed at teardown barrier; preserve exact resource and reobserve",
                    ));
                }
            }
            if path.exists() {
                let worktree = Dir::open_ambient_dir(&path, ambient_authority()).map_err(err)?;
                for output in &outputs {
                    unlinked(&path.join(output))?;
                    // Confined removal of only creation-leased reproducible output, regardless of byte volume.
                    if path.join(output).exists() {
                        worktree.remove_dir_all(output).map_err(err)?;
                    }
                }
                if !worktree_status(&path, &[])?.trim().is_empty() {
                    return Err(err(
                        "new material appeared during output cleanup; preserve checkout and reobserve",
                    ));
                }
            }
            if registration.get("locked").is_some() {
                git(&target, &["worktree", "unlock", p])?;
            }
            let removal = if path.exists() {
                git(&target, &["worktree", "remove", p])
            } else {
                git(&target, &["worktree", "remove", "--force", p])
            };
            if let Err(e) = removal {
                let _ = git(
                    &target,
                    &[
                        "worktree",
                        "lock",
                        "--reason",
                        registration["locked"].as_str().unwrap_or(""),
                        p,
                    ],
                );
                return Err(e);
            }
        }
        _ => (),
    }
    result["operation_result"] = crate::operation_result_value(json!({"invocation":invocation,
        "outcome":{"status":if effected {"applied"} else {"unchanged"},"effects":if effected {json!(["task-resource"])} else {json!([])},"value":{"operation":request.operation,"path":path}},"decision":null}))?;
    result["effect_outcome"] = json!("committed");
    result["retry_effect"] = json!(false);
    result.as_object_mut().unwrap().remove("action");
    Ok(result)
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::time::{SystemTime, UNIX_EPOCH};

    struct Repo(PathBuf);
    impl Repo {
        fn new() -> Self {
            let path = std::env::temp_dir().join(format!(
                "aw-scratch-recovery-{}-{}",
                std::process::id(),
                SystemTime::now()
                    .duration_since(UNIX_EPOCH)
                    .unwrap()
                    .as_nanos()
            ));
            fs::create_dir(&path).unwrap();
            Self(path)
        }
        fn intent(&self, operation: &str) -> Value {
            json!({"target":self.0,"task":"Exact scratch lifecycle","request":{"operation":operation}})
        }
        fn create(&self) -> (PathBuf, String) {
            let proposal = view(self.intent("scratch-create")).unwrap();
            let relative = proposal["action"]["request"]["path"]
                .as_str()
                .unwrap()
                .to_owned();
            view(proposal["action"].clone()).unwrap();
            let path = self.0.join(&relative);
            fs::write(path.join("residue.txt"), "owned temporary material").unwrap();
            (path, relative)
        }
        fn interrupt(&self, path: &Path, stage: &str) {
            let proposal = view(self.intent("scratch-remove")).unwrap();
            let result = view_checked(proposal["action"].clone(), &mut |phase| {
                if phase == stage {
                    if stage == "custody-retained" {
                        fs::remove_file(path.join(MARKER)).unwrap();
                    }
                    return Err(err("deterministic removal interruption"));
                }
                Ok(())
            });
            assert!(
                result
                    .unwrap_err()
                    .to_string()
                    .contains("deterministic removal interruption")
            );
        }
    }
    impl Drop for Repo {
        fn drop(&mut self) {
            fs::remove_dir_all(&self.0).unwrap();
        }
    }

    #[test]
    fn recovery_child() {
        let Ok(input) = std::env::var("AW_TEST_SCRATCH_RECOVERY") else {
            return;
        };
        let proposal = view(serde_json::from_str(&input).unwrap()).unwrap();
        assert_eq!(
            view(proposal["action"].clone()).unwrap()["effect_outcome"],
            "committed"
        );
    }

    #[test]
    fn exact_removal_recovers_in_fresh_process_after_marker_loss_or_absence() {
        for stage in ["custody-retained", "container-absent"] {
            let repo = Repo::new();
            let (path, relative) = repo.create();
            let sibling = repo.0.join(SCRATCH).join("unowned-sibling");
            fs::create_dir(&sibling).unwrap();
            fs::write(sibling.join("keep.txt"), "preserve").unwrap();
            repo.interrupt(&path, stage);
            assert!(repo.0.join(removal_path(&relative).unwrap()).exists());
            assert!(!path.join(MARKER).exists());
            let child = Command::new(std::env::current_exe().unwrap())
                .args([
                    "--exact",
                    "native_resources::tests::recovery_child",
                    "--nocapture",
                ])
                .env(
                    "AW_TEST_SCRATCH_RECOVERY",
                    repo.intent("scratch-remove").to_string(),
                )
                .output()
                .unwrap();
            assert!(
                child.status.success(),
                "{}{}",
                String::from_utf8_lossy(&child.stdout),
                String::from_utf8_lossy(&child.stderr)
            );
            assert!(!path.exists());
            assert!(!repo.0.join(removal_path(&relative).unwrap()).exists());
            assert_eq!(
                fs::read_to_string(sibling.join("keep.txt")).unwrap(),
                "preserve"
            );
            let root = Dir::open_ambient_dir(&repo.0, ambient_authority()).unwrap();
            assert!(
                root.read_dir(".agentic-workspace/local/effects")
                    .unwrap()
                    .all(|e| { e.unwrap().file_name() == "resources.lock" })
            );
        }
    }

    #[test]
    fn recovery_preserves_changed_task_policy_custody_and_replaced_container() {
        for change in [
            "task",
            "policy",
            "record",
            "attempt",
            "container",
            "retention",
        ] {
            let repo = Repo::new();
            let (path, relative) = repo.create();
            let original_marker = fs::read(path.join(MARKER)).unwrap();
            repo.interrupt(&path, "custody-retained");
            let record_path = repo.0.join(removal_path(&relative).unwrap());
            let mut record: Value =
                serde_json::from_slice(&fs::read(&record_path).unwrap()).unwrap();
            let mut intent = repo.intent("scratch-remove");
            intent["request"]["path"] = json!(relative);
            match change {
                "task" => intent["task"] = json!("Other task"),
                "policy" => fs::write(
                    repo.0.join(".agentic-workspace/config.toml"),
                    "[workspace]\nenabled=true\n",
                )
                .unwrap(),
                "record" => {
                    record["invocation"]["arguments"]["task"] = json!("Forged subject");
                    fs::write(&record_path, record.to_string()).unwrap();
                }
                "attempt" => fs::write(
                    repo.0
                        .join(record["custody"]["attempt"]["path"].as_str().unwrap()),
                    "{}",
                )
                .unwrap(),
                "container" => {
                    fs::rename(&path, repo.0.join("preserved-container")).unwrap();
                    fs::create_dir(&path).unwrap();
                    fs::write(path.join("unowned.txt"), "preserve").unwrap();
                }
                "retention" => {
                    let mut marker: Value = serde_json::from_slice(&original_marker).unwrap();
                    marker["retain"] = json!(true);
                    fs::write(path.join(MARKER), marker.to_string()).unwrap();
                }
                _ => unreachable!(),
            }
            assert!(view(intent).is_err(), "{change}");
            assert!(path.exists(), "{change}");
            assert!(record_path.exists(), "{change}");
            assert!(view(repo.intent("scratch-create")).is_err());
        }
    }

    #[test]
    fn markerless_unowned_material_cannot_acquire_removal_custody() {
        let repo = Repo::new();
        let (path, relative) = repo.create();
        fs::remove_file(path.join(MARKER)).unwrap();
        assert!(view(repo.intent("scratch-remove")).is_err());
        assert!(!repo.0.join(removal_path(&relative).unwrap()).exists());
        assert!(path.join("residue.txt").exists());
    }
}
