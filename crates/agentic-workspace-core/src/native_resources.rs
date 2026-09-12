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
    collections::BTreeMap,
    fs,
    io::Write,
    path::{Path, PathBuf},
    process::Command,
    time::Duration,
};
const LOCAL: &str = ".agentic-workspace/local";
const SCRATCH: &str = ".agentic-workspace/local/scratch";
const MARKER: &str = ".aw-scratch.json";

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
    path: Option<String>,
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
fn policy(target: &Path, changed: &[String]) -> Result<Value, CoreError> {
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
    let instructions = crate::native_instructions::resolve(
        target,
        changed,
        &Value::Null,
        config["admissions"]["instruction_revision"]
            .as_str()
            .unwrap_or(""),
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
        include_str!("../../../src/agentic_workspace/_payload/.agentic-workspace/OWNERSHIP.toml")
            .to_owned()
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
fn scratch_snapshot(target: &Path, relative: &str) -> Result<(Value, Vec<String>), CoreError> {
    let path = target.join(relative);
    unlinked(&path)?;
    if !path.exists() {
        return Ok((json!({"status":"absent"}), vec![]));
    }
    let dir = Dir::open_ambient_dir(&path, ambient_authority()).map_err(err)?;
    unlinked(&path.join(MARKER))?;
    if path.join(MARKER).exists() && fs::metadata(path.join(MARKER)).map_err(err)?.len() > 16384 {
        return Err(err("oversized scratch marker preserved"));
    }
    let marker_bytes = match dir.read(MARKER) {
        Ok(bytes) => bytes,
        Err(e)
            if e.kind() == std::io::ErrorKind::NotFound
                && dir.entries().map_err(err)?.next().is_none() =>
        {
            return Ok((json!({"status":"empty-interrupted"}), vec![]));
        }
        Err(e) => return Err(err(e)),
    };
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
    fn walk(
        dir: &Dir,
        prefix: &str,
        out: &mut BTreeMap<String, Value>,
        files: &mut Vec<String>,
        bytes: &mut usize,
    ) -> Result<(), CoreError> {
        for entry in dir.entries().map_err(err)? {
            if out.len() >= 2048 {
                return Err(err(
                    "scratch exceeds bounded cleanup; preserve and split explicit material",
                ));
            }
            let entry = entry.map_err(err)?;
            let name = entry.file_name().to_string_lossy().into_owned();
            let path = if prefix.is_empty() {
                name.clone()
            } else {
                format!("{prefix}/{name}")
            };
            let meta = entry.metadata().map_err(err)?;
            if entry.file_type().map_err(err)?.is_symlink() {
                return Err(err("linked scratch material must be preserved"));
            }
            #[cfg(windows)]
            {
                use cap_std::fs::MetadataExt;
                if meta.file_attributes() & 0x400 != 0 {
                    return Err(err("linked scratch material must be preserved"));
                }
            }
            if meta.is_dir() {
                out.insert(path.clone(), json!({"directory":true}));
                walk(&dir.open_dir(&name).map_err(err)?, &path, out, files, bytes)?;
            } else if meta.is_file() {
                *bytes += meta.len() as usize;
                if *bytes > 16_777_216 {
                    return Err(err(
                        "scratch exceeds bounded cleanup bytes; do not treat build caches as task scratch",
                    ));
                }
                out.insert(
                    path.clone(),
                    json!({"revision":digest(&json!(dir.read(&name).map_err(err)?))?}),
                );
                files.push(path);
            } else {
                return Err(err("nonregular scratch material must be preserved"));
            }
        }
        Ok(())
    }
    let mut entries = BTreeMap::new();
    let mut files = Vec::new();
    walk(&dir, "", &mut entries, &mut files, &mut 0)?;
    Ok((
        json!({"status":"present","marker":marker,"entries":entries}),
        files,
    ))
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
/// Read-only proposal first; effects require the exact freshly rederived revision.
/// No generic cache, session or resource registry is created.
pub fn view(value: Value) -> Result<Value, CoreError> {
    let input: Input = serde_json::from_value(value).map_err(err)?;
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
    let mut scope = input.changed.clone();
    scope.push(if request.operation.starts_with("scratch") {
        format!("{SCRATCH}/**")
    } else {
        ".git/worktrees/**".to_owned()
    });
    let policy = policy(&target, &scope)?;
    let policy_revision = digest(&policy)?;
    let task_id = digest(&json!({"target":target,"task":input.task}))?;
    let id = task_id.trim_start_matches("sha256:");
    let scratch = format!("{SCRATCH}/{id}");
    let relative = request.path.as_deref().unwrap_or(&scratch);
    let mut snapshot;
    let mut files = vec![];
    let mut blockers = vec![];
    let path: PathBuf;
    let mut registration = Value::Null;
    let mut seed = String::new();
    let mut outputs = vec![];
    match request.operation.as_str() {
        "scratch-create" | "scratch-remove" | "scratch-retain" | "scratch-release" => {
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
            (snapshot, files) = scratch_snapshot(&target, relative)?;
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
            if request.operation == "scratch-remove" && snapshot["marker"]["retain"] == true {
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
    let writes = if request.operation.starts_with("scratch") {
        vec![format!("{relative}/**")]
    } else {
        vec![".git/worktrees/**".to_owned()]
    };
    for source in policy["instructions"].as_array().into_iter().flatten() {
        if source["applicable"] == true
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
            blockers.push("current structured instruction protects this resource destination");
        }
    }
    if (request.operation == "scratch-remove" && snapshot["status"] == "present")
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
            "independent_owners",
        ]
        .iter()
        .any(|key| referenced(&current[*key], relative))
        {
            blockers.push("current owner references this resource material; reconcile that owner before cleanup");
        }
    }
    static PRODUCER: std::sync::LazyLock<String> =
        std::sync::LazyLock::new(|| digest(&json!(include_str!("native_resources.rs"))).unwrap());
    let revision = digest(
        &json!({"semantics":&*PRODUCER,"target":target,"task":input.task,"operation":request.operation,"path":path,"snapshot":snapshot,"policy":policy,"need":request.need,"reason":request.reason,"disposable_outputs":outputs}),
    )?;
    let mut next = request.clone();
    next.path = Some(if request.operation.starts_with("scratch") {
        relative.to_owned()
    } else {
        path.to_string_lossy().into_owned()
    });
    next.expected_revision = Some(revision.clone());
    let mut result = json!({"kind":"agentic-workspace/resource-proposal/v1","operation":request.operation,"path":path,"revision":revision,"policy":policy,"policy_revision":policy_revision,"blockers":blockers,"snapshot":snapshot,"effect_outcome":"not-invoked","recovery":"Reobserve this exact path from a fresh process; never create a replacement merely to clean up."});
    if request.operation.starts_with("worktree") {
        result["disposable_outputs"] = json!(outputs);
        result["build_environment"] = build_environment(&path, &outputs);
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
        "operation_id":operation,"operation_revision":&*PRODUCER,"idempotency_key":revision,
        "arguments":result["action"],"effects":["task-resource"],"expected_dependency_revision":revision});
    crate::admit_invocation_value(
        json!({"decision":{"ready_actions":[invocation]},"invocation":invocation}),
    )?;
    unlinked(&path)?;
    if request.operation.starts_with("scratch")
        && scratch_snapshot(&target, relative)?.0 != snapshot
    {
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
        "scratch-remove" if snapshot["status"] == "empty-interrupted" => {
            fs::remove_dir(&path).map_err(err)?;
        }
        "scratch-remove" if snapshot["status"] == "present" => {
            let root = Dir::open_ambient_dir(&target, ambient_authority()).map_err(err)?;
            let dir = root.open_dir(relative).map_err(err)?;
            // Delete marker last; interrupted cleanup remains recognizable and re-observable.
            for file in files.into_iter().filter(|p| p != MARKER) {
                unlinked(&path.join(&file))?;
                if digest(&json!(dir.read(&file).map_err(err)?))?
                    != snapshot["entries"][&file]["revision"]
                {
                    return Err(err(
                        "scratch changed at deletion barrier; preserve remaining material and reobserve",
                    ));
                }
                dir.remove_file(file).map_err(err)?;
            }
            let mut dirs: Vec<_> = snapshot["entries"]
                .as_object()
                .unwrap()
                .iter()
                .filter(|(_, v)| v["directory"] == true)
                .map(|(k, _)| k.clone())
                .collect();
            dirs.sort_by_key(|p| std::cmp::Reverse(p.len()));
            for directory in dirs {
                dir.remove_dir(directory).map_err(err)?;
            }
            if digest(&json!(dir.read(MARKER).map_err(err)?))?
                != snapshot["entries"][MARKER]["revision"]
            {
                return Err(err(
                    "scratch retention changed during cleanup; preserve marker and reobserve",
                ));
            }
            dir.remove_file(MARKER).map_err(err)?;
            drop(dir);
            root.remove_dir(relative).map_err(err)?;
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
