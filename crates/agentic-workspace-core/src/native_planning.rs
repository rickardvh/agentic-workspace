//! Read current Planning selection through its owner contract. Public requests
//! express applicability only; source evidence is derived from confined reads.
use crate::{CoreError, decision_source, digest, prepare_request_value};
use cap_std::{ambient_authority, fs::Dir};
use serde_json::{Value, json};
use sha2::{Digest, Sha256};
use std::path::{Path, PathBuf};

const SELECTION: &str = ".agentic-workspace/local/planning/owner-selection.json";
const THREADS: &str = ".agentic-workspace/local/work-threads/index.json";
const STATE: &str = ".agentic-workspace/planning/state.toml";
const RETAINED: &str = "reconciliation";
/// Footprint of this owner's already normalized pending action. Patterned
/// temporary names stay bounded to the exact selected-owner carrier directory.
/// The public host uses these paths only to intersect current restrictions.
pub(crate) fn write_scope(pending_action: &Value) -> Result<Vec<String>, CoreError> {
    if pending_action["source_owner"] != "planning"
        || pending_action["operation_id"] != "planning.reconcile"
    {
        return Err(error(
            "write scope",
            "requires the current normalized Planning reconciliation action",
        ));
    }
    let effect = pending_action["logical_effect_id"]
        .as_str()
        .filter(|value| !value.is_empty())
        .ok_or_else(|| error("write scope", "normalized logical effect identity missing"))?;
    let mut paths = vec![
        SELECTION.to_owned(),
        ".agentic-workspace/local/planning/owner-selection.lock".to_owned(),
        ".agentic-workspace/local/planning/owner-selection.*.*.tmp".to_owned(),
    ];
    paths.extend(crate::attempt_store::write_paths(
        &json!({"idempotency_key":effect}),
    )?);
    Ok(paths)
}
fn validate_retained(value: &Value) -> Result<(), CoreError> {
    let schema: Value = serde_json::from_str(include_str!(
        "../../../src/agentic_workspace/contracts/schemas/planning_reconciliation.schema.json"
    ))
    .expect("checked schema");
    let mut shape = schema["$defs"]["retained_reconciliation"].clone();
    shape["$schema"] = schema["$schema"].clone();
    shape["$defs"] = schema["$defs"].clone();
    crate::schema_validator(&shape, "Planning retained custody")?
        .validate(value)
        .map_err(|e| {
            error(
                SELECTION,
                format!("invalid reconciliation custody at {}", e.instance_path()),
            )
        })
}
fn error(path: &str, reason: impl std::fmt::Display) -> CoreError {
    CoreError::new(format!(
        "Planning source {path}: {reason}; reconcile the current Planning owner"
    ))
}
fn read(root: &Dir, path: &str) -> Result<Option<Vec<u8>>, CoreError> {
    decision_source::relative(path)?;
    let mut current = PathBuf::new();
    for part in path.split('/') {
        current.push(part);
        match root.symlink_metadata(&current) {
            Ok(metadata) => {
                #[cfg(windows)]
                let linked = {
                    use cap_std::fs::MetadataExt;
                    metadata.file_attributes() & 0x400 != 0
                };
                #[cfg(not(windows))]
                let linked = metadata.is_symlink();
                if linked {
                    return Err(error(path, "linked source is not admitted"));
                }
            }
            Err(e) if e.kind() == std::io::ErrorKind::NotFound => return Ok(None),
            Err(e) => return Err(error(path, e)),
        }
    }
    decision_source::read(root, path)
        .map(Some)
        .map_err(|e| error(path, e))
}
fn parsed(path: &str, bytes: &[u8]) -> Result<Value, CoreError> {
    let text = std::str::from_utf8(bytes)
        .map_err(|e| error(path, e))?
        .trim_start_matches('\u{feff}');
    let value: Value = if path.ends_with(".toml") {
        let value: toml::Value = toml::from_str(text).map_err(|e| error(path, e))?;
        serde_json::to_value(value).map_err(|e| error(path, e))?
    } else {
        serde_json::from_str(text).map_err(|e| error(path, e))?
    };
    if !value.is_object() {
        return Err(error(path, "expected object"));
    }
    Ok(value)
}
fn text(value: &Value) -> String {
    value.as_str().map(str::to_owned).unwrap_or_else(|| {
        if value.is_number() {
            value.to_string()
        } else {
            String::new()
        }
    })
}
fn owner(
    root: &Dir,
    target: &Path,
    selected: &Value,
    provenance: &str,
) -> Result<Value, CoreError> {
    let path = selected["ref"]
        .as_str()
        .ok_or_else(|| error(provenance, "owner ref missing"))?;
    let id = selected["id"]
        .as_str()
        .filter(|s| !s.is_empty())
        .ok_or_else(|| error(provenance, "owner id missing"))?;
    if !path.starts_with(".agentic-workspace/planning/execplans/") || !path.ends_with(".json") {
        return Err(error(provenance, "owner ref outside canonical execplans"));
    }
    let bytes = read(root, path)?.ok_or_else(|| error(path, "selected owner missing"))?;
    let body = parsed(path, &bytes)?;
    if body["id"] != id {
        return Err(error(path, "owner identity mismatch"));
    }
    if !matches!(body["lifecycle"].as_str(), Some("live" | "planned"))
        || matches!(
            body["phase"].as_str(),
            Some("complete" | "completed" | "closeout" | "closed" | "archived")
        )
    {
        return Err(error(path, "selected owner is not live"));
    }
    let expected = text(&selected["revision"]);
    if !expected.is_empty() && expected != text(&body["revision"]) {
        return Err(error(path, "owner revision mismatch"));
    }
    // These legacy authority tuples require their own current owner projection.
    // Do not treat caller or record assertions as a current native admission.
    for field in [
        "planning_revision",
        "planning_revision_id",
        "target_authority_revision",
        "authority",
        "authority_envelope",
        "assignment_target_identity_ref",
        "assignment_revision",
        "evaluation_result_identity",
        "proof_obligation_revision",
        "mutation_baseline_id",
        "integration_revision",
    ] {
        if body.get(field).is_some_and(|v| !v.is_null() && v != "") {
            return Err(error(
                path,
                format!("{field} current authority projection is not yet natively admitted"),
            ));
        }
    }
    Ok(
        json!({"id":id,"ref":path,"selection_source":provenance,"source":{
        "target":target,"path":path,"owner":"planning","revision":format!("sha256:{:x}",Sha256::digest(&bytes))}}),
    )
}

/// Returns read-only public request detail and, only after current explicit
/// continuation, an internally admitted input for the existing Planning reducer.
/// No stored effect is adopted, no owner records are written, no claims granted.
pub(crate) fn resolve(
    target: &Path,
    current_work: &Value,
    request: Option<&Value>,
) -> Result<Value, CoreError> {
    resolve_with_contract(target, current_work, request, None)
}

pub(crate) fn resolve_with_contract(
    target: &Path,
    current_work: &Value,
    request: Option<&Value>,
    current_full_contract: Option<&Value>,
) -> Result<Value, CoreError> {
    let target = std::fs::canonicalize(target).map_err(|e| error("target", e))?;
    let root =
        Dir::open_ambient_dir(&target, ambient_authority()).map_err(|e| error("target", e))?;
    let mut sources = Vec::new();
    let mut load = |path: &str| -> Result<Option<Value>, CoreError> {
        let bytes = read(&root, path)?;
        let value = bytes.as_ref().map(|b| parsed(path, b)).transpose()?;
        let revision = if path == SELECTION {
            value
                .as_ref()
                .map(|value| {
                    let mut value = value.clone();
                    if let Some(retained) = value.get(RETAINED) {
                        validate_retained(retained)?;
                    }
                    value.as_object_mut().unwrap().remove(RETAINED);
                    digest(&value)
                })
                .transpose()?
        } else {
            bytes
                .as_ref()
                .map(|b| format!("sha256:{:x}", Sha256::digest(b)))
        };
        sources.push(json!({"path":path,"revision":revision}));
        Ok(value)
    };
    let threads = load(THREADS)?.unwrap_or(json!({}));
    let work_id = threads["selected_thread_id"]
        .as_str()
        .filter(|s| !s.is_empty())
        .unwrap_or("default");
    let selection = load(SELECTION)?;
    let retained = selection
        .as_ref()
        .map(|s| s[RETAINED].clone())
        .unwrap_or(Value::Null);
    let mut selected = Value::Null;
    if let Some(selection) = selection {
        if selection["kind"] != "agentic-planning/owner-selection/v1"
            || selection["mode"].as_str().unwrap_or("local") != "local"
        {
            return Err(error(SELECTION, "unsupported selection kind or mode"));
        }
        if selection["current_work_id"]
            .as_str()
            .filter(|s| !s.is_empty())
            .unwrap_or("default")
            != work_id
        {
            return Err(error(SELECTION, "local selection current-work mismatch"));
        }
        for field in ["target_root", "repo_root", "worktree"] {
            if let Some(path) = selection[field].as_str().filter(|s| !s.is_empty())
                && std::fs::canonicalize(path).map_err(|e| error(SELECTION, e))? != target
            {
                return Err(error(SELECTION, "local selection target mismatch"));
            }
        }
        selected = owner(&root, &target, &selection["selected_owner"], SELECTION)?;
    } else if let Some(state) = load(STATE)? {
        let mut candidates = Vec::new();
        for (field, entries) in [
            ("todo.active_items", &state["todo"]["active_items"]),
            ("active.execplans", &state["active"]["execplans"]),
        ] {
            if entries.is_null() {
                continue;
            }
            let entries = entries
                .as_array()
                .ok_or_else(|| error(STATE, format!("{field} must be an array")))?;
            for entry in entries {
                if matches!(
                    entry["status"].as_str().or(entry["maturity"].as_str()),
                    Some("closed" | "complete" | "completed" | "archived" | "done")
                ) {
                    continue;
                }
                let reference = entry
                    .get("surface")
                    .or_else(|| entry.get("path"))
                    .cloned()
                    .unwrap_or(Value::Null);
                if reference.is_null() {
                    return Err(error(STATE, format!("{field} live owner ref missing")));
                }
                let candidate =
                    json!({"id":entry["id"],"ref":reference,"revision":entry["revision"]});
                if !candidates
                    .iter()
                    .any(|c: &Value| c["ref"] == candidate["ref"])
                {
                    candidates.push(candidate);
                }
            }
        }
        // Preserve the canonical owner's declared order, not directory order or
        // task keywords. Multiple references remain visible in source revision.
        if let Some(candidate) = candidates.first() {
            selected = owner(&root, &target, candidate, STATE)?;
        }
    }
    let revision = digest(&json!({"sources":sources,"selected":selected}))?;
    let schema: Value = serde_json::from_str(include_str!(
        "../../../src/agentic_workspace/contracts/schemas/planning_reconciliation.schema.json"
    ))
    .expect("checked schema");
    let mut shape = schema["$defs"]["continuation_request"].clone();
    shape["$schema"] = schema["$schema"].clone();
    let declaration = json!({"kind":"planning/continuation/v1","result_kind":"agentic-workspace/planning-continuation-result/v1","input_schema":shape});
    let owner_revision = digest(&declaration)?;
    let mut contract = json!({"kind":"agentic-workspace/capability-contract/v1","revision":"pending","owners":[{"owner":"planning","revision":owner_revision,"requests":[declaration]}],"restriction_authorities":[{"owner":"planning","affects":["task"]}]});
    if !selected.is_null() {
        contract["owners"][0]["effects"] = json!([{"id":"planning-state","domain":"planning"}]);
        contract["owners"][0]["domains"] = json!(["planning"]);
        let mut arguments = schema["$defs"]["operation_arguments"].clone();
        arguments["$schema"] = schema["$schema"].clone();
        arguments["$defs"] = schema["$defs"].clone();
        contract["owners"][0]["operations"] = json!([{"id":"planning.reconcile","semantic_revision":"planning-reconciliation-v1","input_schema":arguments,"result_kind":"agentic-planning/reconciliation-result/v1","effects":["planning-state"],"reads":["planning"]}]);
    }
    contract["revision"] = json!(digest(&contract)?);
    let validation_contract = current_full_contract.unwrap_or(&contract);
    let template = json!({"kind":"agentic-workspace/public-request/v1","id":"planning/continuation/v1","owner":"planning","owner_revision":owner_revision,"source_revision":revision,"capability_revision":validation_contract["revision"],"task_identity":current_work,"request_kind":"planning/continuation/v1","arguments":{"answer":"continue-selected"}});
    let mut status = if selected.is_null() {
        "direct"
    } else {
        "unresolved"
    };
    let mut planning_input = Value::Null;
    if !selected.is_null()
        && retained["kind"] == "agentic-planning/reconciliation-custody/v1"
        && retained["current_work"] == *current_work
        && retained["source"] == selected["source"]
    {
        status = "current";
        planning_input = json!({"target":target,"relevant":true,"source":selected["source"],"intent":{"current_work":current_work},"custody":retained["custody"]});
    }
    if let Some(request) = request {
        prepare_request_value(
            json!({"request":request,"current_work":current_work,"capability_contract":validation_contract}),
        )?;
        if request["owner"] != "planning" {
            return Err(error("request", "another owner requested"));
        }
        if request["source_revision"] != revision {
            status = "stale";
            planning_input = Value::Null;
        } else if request["arguments"]["answer"] == "unrelated-direct" {
            status = "direct";
            planning_input = Value::Null;
        } else if selected.is_null() {
            return Err(error("request", "no currently selected owner to continue"));
        } else {
            status = "current";
            if planning_input.is_null() {
                planning_input = json!({"target":target,"relevant":true,"source":selected["source"],"intent":{"current_work":current_work}});
            }
            // Explicit continuation may change task wording without changing
            // the selected semantic owner. Reuse only its already retained,
            // source-current custody; a fresh unrelated task never gets this.
            if retained["source"] == selected["source"] && !retained.is_null() {
                planning_input["custody"] = retained["custody"].clone();
            }
        }
    }
    let custody_required =
        status == "current" && selected["selection_source"] == SELECTION && retained.is_null();
    if custody_required {
        status = "custody-required";
        planning_input = Value::Null;
    }
    let blockers = if custody_required {
        json!([{"code":"planning-selection-custody-required", "message":"The existing local Planning selection is readable source evidence, but has no retained producer custody for mutation. Preserve it and obtain authority-correct ownership transfer through its current owner; native transfer is not yet available.", "affects":["task"]}])
    } else {
        json!([])
    };
    let decisions = if matches!(status, "unresolved" | "stale") {
        json!([{"id":"planning-continuation","question":"Does the current task continue the selected Planning owner?","response_request":{"request_kind":"planning/continuation/v1","arguments":{}},"choices":[{"id":"continue-selected","label":"Continue the selected Planning owner"},{"id":"unrelated-direct","label":"Unrelated bounded direct work"}],"affects":["task"]}])
    } else {
        json!([])
    };
    let contribution = json!({"owner":"planning","revision":revision,"facts":{"continuation":status,"selected_owner":selected},"decisions":decisions,"blockers":blockers,"settled":status=="direct"});
    Ok(
        json!({"status":status,"source_revision":revision,"current_work_id":work_id,"selected_owner":selected,"requests":if selected.is_null(){json!([])}else{json!([template])},"capability_contract":contract,"contribution":contribution,"planning_input":planning_input,"custody_status":"not-admitted"}),
    )
}

/// Execute only after the public host has admitted this invocation against its
/// full composed decision (including configuration restrictions). Re-derive
/// source ownership under the selected owner's lock; public fields never supply
/// source or producer custody.
pub(crate) fn resolve_for_execution(
    target: &Path,
    current_work: &Value,
    current_full_contract: &Value,
) -> Result<Value, CoreError> {
    let mut view = resolve_with_contract(target, current_work, None, Some(current_full_contract))?;
    if view["selected_owner"].is_null() {
        return Err(error(
            SELECTION,
            "current source-selected owner required for reconciliation execution",
        ));
    }
    if view["planning_input"].is_null() {
        view["planning_input"] = json!({"target":std::fs::canonicalize(target).map_err(|e|error("target",e))?,"relevant":true,"source":view["selected_owner"]["source"],"intent":{"current_work":current_work}});
    }
    let target = std::fs::canonicalize(target).map_err(|e| error("target", e))?;
    let root =
        Dir::open_ambient_dir(&target, ambient_authority()).map_err(|e| error("target", e))?;
    let selection = read(&root, SELECTION)?
        .map(|bytes| parsed(SELECTION, &bytes))
        .transpose()?;
    if let Some(retained) = selection.as_ref().and_then(|value| value.get(RETAINED)) {
        validate_retained(retained)?;
        if retained["source"] == view["selected_owner"]["source"] {
            view["planning_input"]["custody"] = retained["custody"].clone();
        }
    }
    view["planning_input"]["capability_contract"] = current_full_contract.clone();
    // The invocation is an execution intention, not a fabricated public answer.
    // Exact operation and all final composed restrictions are admitted by the
    // caller before any handler effect is permitted.
    Ok(view)
}

#[cfg(test)]
pub(crate) fn execute(
    target: &Path,
    current_work: &Value,
    invocation: &Value,
    current_full_contract: &Value,
) -> Result<Value, CoreError> {
    execute_observing(
        target,
        current_work,
        invocation,
        current_full_contract,
        |_| Ok(()),
    )
}

#[cfg(test)]
fn execute_observing(
    target: &Path,
    current_work: &Value,
    invocation: &Value,
    current_full_contract: &Value,
    after_retention: impl FnMut(&Value) -> Result<(), CoreError>,
) -> Result<Value, CoreError> {
    execute_checked(
        target,
        current_work,
        invocation,
        current_full_contract,
        after_retention,
        || Ok(()),
    )
}

/// Public host hook: re-derive and admit the exact invocation against current
/// global restrictions immediately before commit. The callback must remain
/// read-only (resolve/compose/admit); it must not recursively execute Planning.
pub(crate) fn execute_revalidating(
    target: &Path,
    current_work: &Value,
    invocation: &Value,
    current_full_contract: &Value,
    revalidate: impl FnMut() -> Result<(), CoreError>,
) -> Result<Value, CoreError> {
    execute_checked(
        target,
        current_work,
        invocation,
        current_full_contract,
        |_| Ok(()),
        revalidate,
    )
}

fn execute_checked(
    target: &Path,
    current_work: &Value,
    invocation: &Value,
    current_full_contract: &Value,
    mut after_retention: impl FnMut(&Value) -> Result<(), CoreError>,
    revalidate: impl FnMut() -> Result<(), CoreError>,
) -> Result<Value, CoreError> {
    use cap_std::fs::OpenOptions;
    use std::io::Write;
    let target = std::fs::canonicalize(target).map_err(|e| error("target", e))?;
    let root =
        Dir::open_ambient_dir(&target, ambient_authority()).map_err(|e| error("target", e))?;
    // Exact continuation/invocation permits acquiring the absent local carrier.
    // Read-only discovery never creates it, and recognizable content cannot be
    // acquired through this absent-only path.
    let mut expected = read(&root, SELECTION)?;
    if let Some(bytes) = &expected {
        let value = parsed(SELECTION, bytes)?;
        let retained = value.get(RETAINED).ok_or_else(|| {
            error(
                SELECTION,
                "existing local selection requires producer custody before mutation; preserved",
            )
        })?;
        validate_retained(retained)?;
    }

    root.create_dir_all(".agentic-workspace/local/planning")
        .map_err(|e| error(SELECTION, e))?;
    // Recheck confinement and absence after creating the bounded parents.
    if read(&root, SELECTION)? != expected {
        return Err(error(SELECTION, "selection changed before lock admission"));
    }
    let lock_path = ".agentic-workspace/local/planning/owner-selection.lock";
    if let Ok(metadata) = root.symlink_metadata(lock_path) {
        #[cfg(windows)]
        let linked = {
            use cap_std::fs::MetadataExt;
            metadata.file_attributes() & 0x400 != 0
        };
        #[cfg(not(windows))]
        let linked = metadata.is_symlink();
        if linked {
            return Err(error(lock_path, "linked lock is not admitted"));
        }
    }
    let lock = root
        .open_with(
            lock_path,
            OpenOptions::new().read(true).write(true).create(true),
        )
        .map_err(|e| error(lock_path, e))?
        .into_std();
    if lock.metadata().map_err(|e| error(lock_path, e))?.len() != 0 {
        return Err(error(lock_path, "unrecognized nonempty lock preserved"));
    }
    lock.try_lock()
        .map_err(|e| error(lock_path, format!("selected owner is busy: {e}")))?;
    if read(&root, SELECTION)? != expected {
        return Err(error(SELECTION, "selection changed before lock admission"));
    }
    let view = resolve_for_execution(&target, current_work, current_full_contract)?;
    let initial_selection = json!({
        "kind":"agentic-planning/owner-selection/v1", "mode":"local",
        "current_work_id":view["current_work_id"],
        "selected_owner":{"id":view["selected_owner"]["id"],"ref":view["selected_owner"]["ref"]}
    });
    let source = view["selected_owner"]["source"].clone();
    let mut input = json!({"target":target,"relevant":true,"source":source,"intent":{"current_work":current_work},"capability_contract":current_full_contract,"invocation":invocation});
    if !view["planning_input"]["custody"].is_null() {
        input["custody"] = view["planning_input"]["custody"].clone();
    }
    crate::planning::reconcile_retaining_checked(
        input,
        |custody| {
            // Re-read both the exact selection and its selected semantic source
            // before each bounded write. Preserve unfamiliar state on any drift.
            if read(&root, SELECTION)? != expected {
                return Err(error(
                    SELECTION,
                    "selection changed during reconciliation; retained files preserved",
                ));
            }
            let fresh =
                resolve_with_contract(&target, current_work, None, Some(current_full_contract))?;
            if fresh["selected_owner"]["source"] != source {
                return Err(error(
                    SELECTION,
                    "selected semantic source changed during reconciliation",
                ));
            }
            let mut selection = expected
                .as_ref()
                .map(|bytes| parsed(SELECTION, bytes))
                .transpose()?
                .unwrap_or_else(|| initial_selection.clone());
            let retained = json!({"kind":"agentic-planning/reconciliation-custody/v1","current_work":current_work,"source":source,"invocation":invocation,"custody":custody});
            validate_retained(&retained)?;
            selection[RETAINED] = retained;
            let bytes = serde_json::to_vec_pretty(&selection).map_err(|e| error(SELECTION, e))?;
            if expected.as_ref() != Some(&bytes) {
                if expected.is_none() {
                    // Persist returned attempt custody in the newly acquired
                    // carrier before any committed outcome can be produced.
                    let mut file = root
                        .open_with(SELECTION, OpenOptions::new().write(true).create_new(true))
                        .map_err(|e| {
                            error(
                                SELECTION,
                                format!(
                                    "selection acquisition failed; existing content preserved: {e}"
                                ),
                            )
                        })?;
                    file.write_all(&bytes).map_err(|e| error(SELECTION, e))?;
                    file.sync_all().map_err(|e| error(SELECTION, e))?;
                    expected = Some(bytes);
                    return after_retention(custody);
                }
                let nonce = std::time::SystemTime::now()
                    .duration_since(std::time::UNIX_EPOCH)
                    .map_err(|e| error(SELECTION, e))?
                    .as_nanos();
                let temporary = format!(
                    ".agentic-workspace/local/planning/owner-selection.{}.{nonce}.tmp",
                    std::process::id()
                );
                let mut file = root
                    .open_with(&temporary, OpenOptions::new().write(true).create_new(true))
                    .map_err(|e| error(&temporary, e))?;
                file.write_all(&bytes).map_err(|e| error(&temporary, e))?;
                file.sync_all().map_err(|e| error(&temporary, e))?;
                drop(file);
                if read(&root, SELECTION)? != expected {
                    return Err(error(
                        SELECTION,
                        "selection changed before atomic replacement; temporary preserved",
                    ));
                }
                root.rename(&temporary, &root, SELECTION)
                    .map_err(|e| error(SELECTION, e))?;
                expected = Some(bytes);
            }
            after_retention(custody)
        },
        revalidate,
    )
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::{
        fs,
        time::{SystemTime, UNIX_EPOCH},
    };
    const PLAN: &str = ".agentic-workspace/planning/execplans/delegation-lane-sweep.plan.json";
    struct Target(PathBuf);
    impl Target {
        fn new() -> Self {
            let path = std::env::temp_dir().join(format!(
                "aw-native-planning-{}-{}",
                std::process::id(),
                SystemTime::now()
                    .duration_since(UNIX_EPOCH)
                    .unwrap()
                    .as_nanos()
            ));
            fs::create_dir(&path).unwrap();
            Self(path)
        }
        fn write(&self, path: &str, value: &str) {
            let path = self.0.join(path);
            fs::create_dir_all(path.parent().unwrap()).unwrap();
            fs::write(path, value).unwrap();
        }
        fn plan(&self) -> Value {
            let value: Value = serde_json::from_str(include_str!(
                "../../../.agentic-workspace/planning/execplans/delegation-lane-sweep.plan.json"
            ))
            .unwrap();
            self.write(PLAN, &value.to_string());
            value
        }
        fn share(&self) {
            self.write(STATE, &format!("[[active.execplans]]\nid = \"delegation-lane-sweep\"\nsurface = \"{PLAN}\"\nstatus = \"active\"\n"));
        }
        fn select(&self) {
            self.write(SELECTION,&json!({"kind":"agentic-planning/owner-selection/v1","mode":"local","current_work_id":"default","selected_owner":{"id":"delegation-lane-sweep","ref":PLAN}}).to_string());
        }
    }
    impl Drop for Target {
        fn drop(&mut self) {
            fs::remove_dir_all(&self.0).unwrap();
        }
    }
    fn work() -> Value {
        json!({"kind":"current-work","id":"ordinary-task"})
    }
    fn continued(target: &Target) -> Value {
        let initial = resolve(&target.0, &work(), None).unwrap();
        resolve(&target.0, &work(), Some(&initial["requests"][0])).unwrap()
    }
    fn action(target: &Target) -> (Value, Value) {
        let view = continued(target);
        let contract = view["capability_contract"].clone();
        let mut input = view["planning_input"].clone();
        input["capability_contract"] = contract.clone();
        let (input, _) = crate::planning::compose_input(input).unwrap();
        let decision = crate::compile_value(input).unwrap();
        (decision["primary_action"].clone(), contract)
    }
    fn fresh_current(target: &Target) -> bool {
        let view = resolve(&target.0, &work(), None).unwrap();
        let mut input = view["planning_input"].clone();
        input["capability_contract"] = view["capability_contract"].clone();
        crate::planning::compose_input(input).unwrap().1["current"] == true
    }
    fn shared_target() -> Target {
        let target = Target::new();
        target.plan();
        target.write(STATE, &format!("[[active.execplans]]\nid = \"delegation-lane-sweep\"\nsurface = \"{PLAN}\"\nstatus = \"active\"\n"));
        target
    }
    #[test]
    fn native_planning_shared_continuation_acquires_selection_in_one_reconciliation() {
        let target = shared_target();
        let original = fs::read(target.0.join(PLAN)).unwrap();
        let initial = resolve(&target.0, &work(), None).unwrap();
        assert_eq!(initial["status"], "unresolved");
        assert!(!target.0.join(".agentic-workspace/local").exists());
        let mut unrelated = initial["requests"][0].clone();
        unrelated["arguments"]["answer"] = json!("unrelated-direct");
        assert_eq!(
            resolve(&target.0, &work(), Some(&unrelated)).unwrap()["status"],
            "direct"
        );
        assert!(!target.0.join(".agentic-workspace/local").exists());
        let (invocation, contract) = action(&target);
        assert_eq!(invocation["operation_id"], "planning.reconcile");
        let outcome = execute(&target.0, &work(), &invocation, &contract).unwrap();
        assert!(fresh_current(&target));
        let selection: Value =
            serde_json::from_slice(&fs::read(target.0.join(SELECTION)).unwrap()).unwrap();
        assert_eq!(selection["selected_owner"]["ref"], PLAN);
        assert_eq!(selection[RETAINED]["custody"], outcome["custody"]);
        let before = fs::read(target.0.join(SELECTION)).unwrap();
        let replay = execute(&target.0, &work(), &invocation, &contract).unwrap();
        assert_eq!(replay["value"], outcome["value"]);
        assert_eq!(fs::read(target.0.join(SELECTION)).unwrap(), before);
        assert_eq!(fs::read(target.0.join(PLAN)).unwrap(), original);
    }
    #[test]
    fn native_planning_shared_acquisition_retains_attempt_before_interruption() {
        let target = shared_target();
        let (invocation, contract) = action(&target);
        let failed = execute_observing(&target.0, &work(), &invocation, &contract, |_| {
            Err(error(
                "test",
                "injected stop after absent carrier acquisition",
            ))
        });
        assert!(failed.is_err());
        let selection: Value =
            serde_json::from_slice(&fs::read(target.0.join(SELECTION)).unwrap()).unwrap();
        assert!(selection[RETAINED]["custody"]["committed"].is_null());
        let result = execute(&target.0, &work(), &invocation, &contract).unwrap();
        assert_eq!(
            result["custody"]["attempt"],
            selection[RETAINED]["custody"]["attempt"]
        );
        assert!(fresh_current(&target));
    }
    #[test]
    fn native_planning_recognized_unowned_selection_is_source_only() {
        let target = shared_target();
        let (invocation, contract) = action(&target);
        target.select();
        let original = fs::read(target.0.join(SELECTION)).unwrap();
        let view = continued(&target);
        assert_eq!(view["status"], "custody-required");
        assert!(view["planning_input"].is_null());
        assert_eq!(
            view["contribution"]["blockers"][0]["code"],
            "planning-selection-custody-required"
        );
        assert!(
            execute(&target.0, &work(), &invocation, &contract)
                .unwrap_err()
                .to_string()
                .contains("requires producer custody")
        );
        assert_eq!(fs::read(target.0.join(SELECTION)).unwrap(), original);
        assert!(!target.0.join(".agentic-workspace/local/effects").exists());
        assert!(
            !target
                .0
                .join(".agentic-workspace/local/planning/owner-selection.lock")
                .exists()
        );
    }
    #[test]
    fn native_planning_shared_acquisition_preserves_intervening_unknown_selection() {
        let target = shared_target();
        let (invocation, contract) = action(&target);
        target.write(SELECTION, "{\"kind\":\"unknown\"}");
        let before = fs::read(target.0.join(SELECTION)).unwrap();
        assert!(execute(&target.0, &work(), &invocation, &contract).is_err());
        assert_eq!(fs::read(target.0.join(SELECTION)).unwrap(), before);
        assert!(!target.0.join(".agentic-workspace/local/effects").exists());
    }
    #[test]
    fn native_planning_retains_current_custody_across_fresh_reads() {
        let target = Target::new();
        target.plan();
        target.share();
        let before = resolve(&target.0, &work(), None).unwrap();
        let (invocation, contract) = action(&target);
        let result = execute(&target.0, &work(), &invocation, &contract).unwrap();
        assert!(!result["custody"]["committed"].is_null());
        assert!(fresh_current(&target));
        let after = resolve(&target.0, &work(), None).unwrap();
        assert_eq!(
            before["selected_owner"]["source"],
            after["selected_owner"]["source"]
        );
        let selection: Value =
            serde_json::from_slice(&fs::read(target.0.join(SELECTION)).unwrap()).unwrap();
        assert_eq!(
            selection["selected_owner"],
            json!({"id":"delegation-lane-sweep","ref":PLAN})
        );
        assert_eq!(selection[RETAINED]["custody"], result["custody"]);
    }
    #[test]
    fn native_planning_write_scope_matches_actual_producer_custody() {
        let target = Target::new();
        target.plan();
        target.share();
        let view = continued(&target);
        let contract = view["capability_contract"].clone();
        let mut input = view["planning_input"].clone();
        input["capability_contract"] = contract.clone();
        let (input, _) = crate::planning::compose_input(input).unwrap();
        let decision = crate::compile_value(input).unwrap();
        let pending = &decision["pending_consequences"]["actions"][0];
        let paths = write_scope(pending).unwrap();
        assert_eq!(paths.len(), 5);
        assert!(!target.0.join(".agentic-workspace/local/effects").exists());
        let result = execute(&target.0, &work(), &decision["primary_action"], &contract).unwrap();
        for field in ["attempt", "committed"] {
            assert!(
                paths
                    .iter()
                    .any(|path| result["custody"][field]["path"] == *path)
            );
        }
        assert!(paths.contains(&SELECTION.to_owned()));
        assert!(
            paths.contains(&".agentic-workspace/local/planning/owner-selection.lock".to_owned())
        );
        assert!(
            paths.contains(&".agentic-workspace/local/planning/owner-selection.*.*.tmp".to_owned())
        );
        let mut unrelated = pending.clone();
        unrelated["source_owner"] = json!("other");
        assert!(write_scope(&unrelated).is_err());
        assert!(write_scope(&decision["primary_action"]).is_err());
    }
    #[test]
    fn native_planning_explicit_reworded_continuation_reuses_owner_custody() {
        let target = Target::new();
        target.plan();
        target.share();
        let (invocation, contract) = action(&target);
        let result = execute(&target.0, &work(), &invocation, &contract).unwrap();
        let reworded = json!({"kind":"current-work","id":"same-owner-reworded-task"});
        let initial = resolve(&target.0, &reworded, None).unwrap();
        assert_eq!(initial["status"], "unresolved");
        assert!(initial["planning_input"].is_null());
        let mut unrelated = initial["requests"][0].clone();
        unrelated["arguments"]["answer"] = json!("unrelated-direct");
        assert!(
            resolve(&target.0, &reworded, Some(&unrelated)).unwrap()["planning_input"].is_null()
        );
        let current = resolve(&target.0, &reworded, Some(&initial["requests"][0])).unwrap();
        assert_eq!(current["planning_input"]["custody"], result["custody"]);
        let execution = resolve_for_execution(&target.0, &reworded, &contract).unwrap();
        let (_, detail) =
            crate::planning::compose_input(execution["planning_input"].clone()).unwrap();
        assert_eq!(detail["current"], true);
        assert_eq!(detail["committed_operation"]["invocation"], invocation);
        assert_eq!(detail["committed_operation"]["custody"], result["custody"]);
        let replay = execute(&target.0, &reworded, &invocation, &contract).unwrap();
        assert_eq!(replay["custody"], result["custody"]);
        assert_eq!(
            fs::read_dir(target.0.join(".agentic-workspace/local/effects"))
                .unwrap()
                .count(),
            2
        );
    }
    #[test]
    fn native_planning_interrupted_admission_resumes_exact_attempt() {
        let target = Target::new();
        target.plan();
        target.share();
        let (invocation, contract) = action(&target);
        let failed = execute_observing(&target.0, &work(), &invocation, &contract, |_| {
            Err(error("test", "interrupt after retained admission"))
        });
        assert!(failed.is_err());
        let selection: Value =
            serde_json::from_slice(&fs::read(target.0.join(SELECTION)).unwrap()).unwrap();
        assert!(selection[RETAINED]["custody"]["committed"].is_null());
        assert!(!fresh_current(&target));
        let result = execute(&target.0, &work(), &invocation, &contract).unwrap();
        assert_eq!(
            result["custody"]["attempt"],
            selection[RETAINED]["custody"]["attempt"]
        );
        assert!(fresh_current(&target));
    }
    #[test]
    fn native_planning_commit_revalidates_global_sources_without_recursive_lock() {
        let target = Target::new();
        target.plan();
        target.share();
        let (invocation, contract) = action(&target);
        let failure = execute_checked(
            &target.0,
            &work(),
            &invocation,
            &contract,
            |custody| {
                if custody["committed"].is_null() {
                    target.write(".agentic-workspace/config.local.toml", "invalid = [");
                }
                Ok(())
            },
            || {
                let configuration = crate::native_config::view(&target.0)?;
                assert!(
                    !configuration["contribution"]["blockers"]
                        .as_array()
                        .unwrap()
                        .is_empty()
                );
                let mut current_contract = contract.clone();
                for field in ["owners", "restriction_authorities"] {
                    current_contract[field].as_array_mut().unwrap().extend(
                        configuration["capability_contract"][field]
                            .as_array()
                            .unwrap()
                            .iter()
                            .cloned(),
                    );
                }
                current_contract["revision"] = json!(digest(&current_contract)?);
                let view = resolve_for_execution(&target.0, &work(), &current_contract)?;
                let (mut input, _) =
                    crate::planning::compose_input(view["planning_input"].clone())?;
                input["contributions"]
                    .as_array_mut()
                    .unwrap()
                    .push(configuration["contribution"].clone());
                let decision = crate::compile_value(input)?;
                crate::admit_invocation_value(json!({"decision":decision,"invocation":invocation}))
                    .map(|_| ())
            },
        );
        assert!(failure.is_err());
        let selection: Value =
            serde_json::from_slice(&fs::read(target.0.join(SELECTION)).unwrap()).unwrap();
        assert!(selection[RETAINED]["custody"]["committed"].is_null());
        assert_eq!(
            fs::read_dir(target.0.join(".agentic-workspace/local/effects"))
                .unwrap()
                .count(),
            1
        );
        fs::remove_file(target.0.join(".agentic-workspace/config.local.toml")).unwrap();
        let recovered = execute_revalidating(&target.0, &work(), &invocation, &contract, || {
            let view = resolve_for_execution(&target.0, &work(), &contract)?;
            let (input, _) = crate::planning::compose_input(view["planning_input"].clone())?;
            let decision = crate::compile_value(input)?;
            crate::admit_invocation_value(json!({"decision":decision,"invocation":invocation}))
                .map(|_| ())
        })
        .unwrap();
        assert_eq!(
            recovered["custody"]["attempt"],
            selection[RETAINED]["custody"]["attempt"]
        );
        assert!(fresh_current(&target));
    }
    #[test]
    fn native_planning_unretained_result_and_unknown_temp_are_preserved() {
        let target = Target::new();
        target.plan();
        target.share();
        let (invocation, contract) = action(&target);
        let result = execute(&target.0, &work(), &invocation, &contract).unwrap();
        let result_path = result["custody"]["committed"]["path"].as_str().unwrap();
        let original = fs::read(target.0.join(result_path)).unwrap();
        let mut selection: Value =
            serde_json::from_slice(&fs::read(target.0.join(SELECTION)).unwrap()).unwrap();
        selection[RETAINED]["custody"]["committed"] = Value::Null;
        target.write(SELECTION, &selection.to_string());
        target.write(
            ".agentic-workspace/local/planning/owner-selection.unknown.tmp",
            "unowned",
        );
        let failed = execute(&target.0, &work(), &invocation, &contract)
            .unwrap_err()
            .to_string();
        assert!(failed.contains("requires exact custody; preserved"));
        assert_eq!(fs::read(target.0.join(result_path)).unwrap(), original);
        assert_eq!(
            fs::read_to_string(
                target
                    .0
                    .join(".agentic-workspace/local/planning/owner-selection.unknown.tmp")
            )
            .unwrap(),
            "unowned"
        );
    }
    #[test]
    fn native_planning_concurrent_writer_and_material_drift_fail_closed() {
        let target = Target::new();
        let mut body = target.plan();
        target.share();
        let (invocation, contract) = action(&target);
        let (entered_tx, entered_rx) = std::sync::mpsc::channel();
        let (release_tx, release_rx) = std::sync::mpsc::channel();
        let path = target.0.clone();
        let action = invocation.clone();
        let capability = contract.clone();
        let thread = std::thread::spawn(move || {
            let mut first = true;
            execute_observing(&path, &work(), &action, &capability, |_| {
                if first {
                    first = false;
                    entered_tx.send(()).unwrap();
                    release_rx.recv().unwrap();
                }
                Ok(())
            })
        });
        entered_rx
            .recv_timeout(std::time::Duration::from_secs(5))
            .unwrap();
        assert!(
            execute(&target.0, &work(), &invocation, &contract)
                .unwrap_err()
                .to_string()
                .contains("busy")
        );
        body["canonical_core"]["hard_constraints"] = json!("new material scope");
        target.write(PLAN, &body.to_string());
        release_tx.send(()).unwrap();
        assert!(thread.join().unwrap().is_err());
        let current = resolve(&target.0, &work(), None).unwrap();
        assert_eq!(current["status"], "unresolved");
        assert!(execute(&target.0, &work(), &invocation, &contract).is_err());
    }
    #[test]
    fn native_planning_real_owner_requires_explicit_current_continuation() {
        let target = Target::new();
        let body = target.plan();
        target.share();
        let initial = resolve(&target.0, &work(), None).unwrap();
        assert_eq!(initial["status"], "unresolved");
        assert!(initial["planning_input"].is_null());
        let current = continued(&target);
        assert_eq!(current["status"], "current");
        assert_eq!(current["custody_status"], "not-admitted");
        let input = crate::planning::pending_input(current["planning_input"].clone()).unwrap();
        let reconciliation = &input["contributions"][0]["facts"]["reconciliation"];
        assert_eq!(reconciliation["coverage"]["complete"], true);
        assert_eq!(
            reconciliation["subject"]["state"]["canonical_core"],
            body["canonical_core"]
        );
        assert_eq!(input["contributions"][0]["facts"]["current"], false);
        let mut unrelated = initial["requests"][0].clone();
        unrelated["arguments"]["answer"] = json!("unrelated-direct");
        let direct = resolve(&target.0, &work(), Some(&unrelated)).unwrap();
        assert_eq!(direct["status"], "direct");
        assert!(direct["planning_input"].is_null());
        assert!(!target.0.join(".agentic-workspace/local/effects").exists());
    }
    #[test]
    fn native_planning_bounded_answer_uses_actual_composed_contract() {
        let target = Target::new();
        target.plan();
        target.share();
        let initial = resolve(&target.0, &work(), None).unwrap();
        let mut contract = initial["capability_contract"].clone();
        contract["owners"]
            .as_array_mut()
            .unwrap()
            .push(json!({"owner":"workspace","revision":"configuration-current"}));
        contract["revision"] = json!(digest(&contract).unwrap());
        let decision = crate::compile_value(json!({"contributions":[initial["contribution"]],"intent":{"current_work":work()},"capability_contract":contract})).unwrap();
        assert!(
            !decision["pending_consequences"]["decisions"]
                .as_array()
                .unwrap()
                .is_empty()
        );
        assert!(decision["ready_actions"].as_array().unwrap().is_empty());
        let question = &decision["pending_consequences"]["decisions"][0];
        assert_eq!(
            question["response_request"]["capability_revision"],
            contract["revision"]
        );
        let response = crate::answer_decision_value(json!({"decision":decision,"question":question["consequence_id"],"answer":"unrelated-direct","capability_contract":contract})).unwrap();
        let request = response.get("request").unwrap_or(&response);
        let direct =
            resolve_with_contract(&target.0, &work(), Some(request), Some(&contract)).unwrap();
        assert_eq!(direct["status"], "direct");
        assert!(resolve(&target.0, &work(), Some(request)).is_err());
    }
    #[test]
    fn native_planning_source_and_work_drift_cannot_reuse_intention() {
        let target = Target::new();
        let mut body = target.plan();
        target.share();
        let initial = resolve(&target.0, &work(), None).unwrap();
        body["canonical_core"]["hard_constraints"] = json!("Require independent domain review");
        target.write(PLAN, &body.to_string());
        let stale = resolve(&target.0, &work(), Some(&initial["requests"][0])).unwrap();
        assert_eq!(stale["status"], "stale");
        assert!(stale["planning_input"].is_null());
        let changed_work = json!({"kind":"current-work","id":"unrelated-task"});
        assert!(resolve(&target.0, &changed_work, Some(&initial["requests"][0])).is_err());
        let mut forged = initial["requests"][0].clone();
        forged["arguments"]["source"] = json!({"owner":"planning"});
        assert!(resolve(&target.0, &work(), Some(&forged)).is_err());
    }
    #[test]
    fn native_planning_selection_is_authority_relation_not_file_presence() {
        let target = Target::new();
        target.plan();
        assert_eq!(
            resolve(&target.0, &work(), None).unwrap()["status"],
            "direct"
        );
        target.write(STATE,&format!("[[todo.active_items]]\nid = 'delegation-lane-sweep'\nsurface = '{PLAN}'\nstatus = 'active'\nrevision = 4\n"));
        assert_eq!(continued(&target)["status"], "current");
        target.select();
        target.write(THREADS, "{\"selected_thread_id\":\"other-work\"}");
        assert!(
            resolve(&target.0, &work(), None)
                .unwrap_err()
                .to_string()
                .contains("current-work mismatch")
        );
        target.write(THREADS, "{}");
        fs::remove_file(target.0.join(PLAN)).unwrap();
        assert!(
            resolve(&target.0, &work(), None)
                .unwrap_err()
                .to_string()
                .contains("selected owner missing")
        );
    }
    #[test]
    fn native_planning_identity_and_unsupported_authority_fail_at_source() {
        let target = Target::new();
        let mut body = target.plan();
        target.share();
        body["id"] = json!("different-owner");
        target.write(PLAN, &body.to_string());
        assert!(
            resolve(&target.0, &work(), None)
                .unwrap_err()
                .to_string()
                .contains("owner identity mismatch")
        );
        body["id"] = json!("delegation-lane-sweep");
        body["planning_revision"] = json!("old-global-revision");
        target.write(PLAN, &body.to_string());
        let failure = resolve(&target.0, &work(), None).unwrap_err().to_string();
        assert!(failure.contains(PLAN));
        assert!(failure.contains("planning_revision current authority projection"));
        body.as_object_mut().unwrap().remove("planning_revision");
        target.write(PLAN, &body.to_string());
        let other = Target::new();
        target.write(SELECTION, &json!({"kind":"agentic-planning/owner-selection/v1","current_work_id":"default","target_root":other.0,"selected_owner":{"id":"delegation-lane-sweep","ref":PLAN}}).to_string());
        assert!(
            resolve(&target.0, &work(), None)
                .unwrap_err()
                .to_string()
                .contains("target mismatch")
        );
    }
    #[test]
    fn native_planning_same_semantic_attempts_preserve_subject_but_constraints_stale() {
        let target = Target::new();
        let mut body = target.plan();
        target.share();
        let subject = |target: &Target| {
            crate::planning::pending_input(continued(target)["planning_input"].clone()).unwrap()["contributions"][0]["facts"]["reconciliation"]["subject"].clone()
        };
        let first = subject(&target);
        body["relationships"]["assignment"] = json!({"attempt_id":"second","status":"retrying"});
        target.write(PLAN, &body.to_string());
        let retry = subject(&target);
        assert_eq!(first["revision"], retry["revision"]);
        body["relationships"]["returned"] =
            json!({"result_id":"returned-1","status":"integration-pending"});
        target.write(PLAN, &body.to_string());
        let returned = subject(&target);
        assert_eq!(first["revision"], returned["revision"]);
        assert_eq!(
            returned["state"]["handoff"]["returned"]["result_id"],
            "returned-1"
        );
        body["canonical_core"]["agent_may_decide"] = json!("Only documentation scope");
        target.write(PLAN, &body.to_string());
        assert_ne!(first["revision"], subject(&target)["revision"]);
        body["unmapped_meaning"] = json!("Must not be dropped");
        target.write(PLAN, &body.to_string());
        let input =
            crate::planning::pending_input(continued(&target)["planning_input"].clone()).unwrap();
        assert_eq!(
            input["contributions"][0]["facts"]["reconciliation"]["coverage"]["complete"],
            false
        );
    }
}
