//! Read current Planning selection through its owner contract. Public requests
//! express applicability or an explicit bounded domain selector transfer answer;
//! source evidence and effect bindings are derived from confined reads.
use crate::{CoreError, decision_source, digest, prepare_request_value};
use cap_std::{ambient_authority, fs::Dir};
use serde_json::{Value, json};
use sha2::{Digest, Sha256};
use std::path::{Path, PathBuf};

const SELECTION: &str = ".agentic-workspace/local/planning/owner-selection.json";
const THREADS: &str = ".agentic-workspace/local/work-threads/index.json";
pub(crate) fn explicit_continuation(request: &Value) -> bool {
    request["request_kind"] == "planning/select-owner/v1"
        || request["arguments"]["answer"] == "continue-selected"
}
inventory::submit! { crate::native_enclave::Registration { declarations: enclave } }
pub(crate) fn enclave() -> Value {
    serde_json::from_str(include_str!("contracts/enclave.json")).expect("Planning enclave contract")
}

pub(crate) const STATE: &str = ".agentic-workspace/planning/state.toml";
const RETAINED: &str = "reconciliation";
pub(crate) fn post_effect_paths() -> Value {
    json!([SELECTION])
}
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
        "../../../contracts/schemas/planning_reconciliation.schema.json"
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

fn inspect_carrier(
    target: &Path,
    selection: &Value,
    require_committed: bool,
) -> Result<Value, CoreError> {
    let retained = &selection[RETAINED];
    validate_retained(retained)?;
    let invocation = &retained["invocation"];
    if let Some(work) = invocation["arguments"].get("current_work")
        && *work != retained["current_work"]
    {
        return Err(error(
            SELECTION,
            "current work differs from its retained Planning producer",
        ));
    }
    if invocation["source_owner"] != "planning"
        || invocation["operation_id"] != "planning.reconcile"
        || invocation["arguments"]["reconciliation"]["former_source"] != retained["source"]
        || retained["source"]["path"] != selection["selected_owner"]["ref"]
    {
        return Err(error(
            SELECTION,
            "selector does not match its retained Planning producer",
        ));
    }
    let outcome = json!({"status":"applied","effects":["planning-state"],"value":invocation["arguments"]["reconciliation"]});
    let prepared = crate::attempt_store::prepare_commit(
        target
            .to_str()
            .ok_or_else(|| error(SELECTION, "target encoding"))?,
        retained["custody"].clone(),
        outcome,
    )?;
    if prepared["record"]["invocation"] != *invocation {
        return Err(error(
            SELECTION,
            "retained invocation differs from its producer",
        ));
    }
    if require_committed {
        crate::attempt_store::inspect_committed(
            target.to_str().unwrap(),
            retained["custody"].clone(),
        )?;
    }
    let expected_subject = format!(
        "planning:{}",
        digest(&json!({"target":target,"id":selection["selected_owner"]["id"]}))?
    );
    if invocation["arguments"]["reconciliation"]["subject"]["id"] != expected_subject {
        return Err(error(
            SELECTION,
            "selector identity differs from retained Planning work",
        ));
    }
    Ok(retained.clone())
}

/// Material mutation needs an acquired, committed owner relation, not a path
/// or a former selector that merely looks familiar. Source currentness is
/// checked separately so a genuine owner can reconcile later material edits.
pub(crate) fn update_custody(target: &Path, reference: &str) -> Result<Option<Value>, CoreError> {
    let root =
        Dir::open_ambient_dir(target, ambient_authority()).map_err(|e| error(SELECTION, e))?;
    let Some(bytes) = read(&root, SELECTION)? else {
        return Ok(None);
    };
    let selection = parsed(SELECTION, &bytes)?;
    if selection["selected_owner"]["ref"] != reference || selection.get(RETAINED).is_none() {
        return Ok(None);
    }
    let retained = inspect_carrier(target, &selection, false)?;
    if crate::attempt_store::inspect_committed(
        target.to_str().unwrap(),
        retained["custody"].clone(),
    )
    .is_err()
    {
        return Ok(None);
    }
    Ok(Some(retained))
}

fn retained_transition(target: &Path, selection: &Value) -> Result<Option<Value>, CoreError> {
    let Some(transition) =
        selection[RETAINED]["invocation"]["arguments"].get("selection_transition")
    else {
        return Ok(None);
    };
    inspect_carrier(target, selection, false)?;
    let mut expected = transition["selection"].clone();
    expected[RETAINED] = selection[RETAINED].clone();
    let root =
        Dir::open_ambient_dir(target, ambient_authority()).map_err(|e| error(SELECTION, e))?;
    if expected != *selection
        || read(&root, SELECTION)?.as_deref()
            != Some(
                serde_json::to_vec_pretty(&expected)
                    .map_err(|e| error(SELECTION, e))?
                    .as_slice(),
            )
    {
        return Err(error(
            SELECTION,
            "selection transition postimage differs; current bytes preserved",
        ));
    }
    Ok(Some(transition.clone()))
}
fn error(path: &str, reason: impl std::fmt::Display) -> CoreError {
    CoreError::new(format!(
        "Planning source {path}: {reason}; reconcile the current Planning owner"
    ))
}
#[cfg(test)]
thread_local! {
    pub(crate) static TEST_READS: std::cell::RefCell<Vec<String>> = const { std::cell::RefCell::new(Vec::new()) };
}
pub(crate) fn read(root: &Dir, path: &str) -> Result<Option<Vec<u8>>, CoreError> {
    #[cfg(test)]
    TEST_READS.with(|reads| reads.borrow_mut().push(path.to_owned()));
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
fn legacy_references(state: &Value, retirement: bool) -> Result<Vec<Value>, CoreError> {
    let fields = state
        .as_object()
        .ok_or_else(|| error(STATE, "legacy aggregate must be an object"))?;
    if (retirement
        && fields
            .keys()
            .any(|k| !matches!(k.as_str(), "kind" | "schema_version" | "active" | "todo")))
        || state.get("kind").is_some_and(|v| v != "planning-state/v1")
    {
        return Err(error(
            STATE,
            "unsupported legacy aggregate; unfamiliar material is preserved",
        ));
    }
    let mut candidates = Vec::new();
    for (group, field) in [("active", "execplans"), ("todo", "active_items")] {
        if state[group].is_null() {
            continue;
        }
        if state[group]
            .as_object()
            .is_none_or(|g| retirement && g.keys().any(|k| k != field))
        {
            return Err(error(
                STATE,
                "unsupported legacy aggregate group; preserved",
            ));
        }
        let entries = state[group][field]
            .as_array()
            .ok_or_else(|| error(STATE, "legacy owner relations must be an array"))?;
        for entry in entries {
            let reference = entry.get("surface").or_else(|| entry.get("path"));
            if matches!(
                entry["status"].as_str().or(entry["maturity"].as_str()),
                Some("closed" | "complete" | "completed" | "archived" | "done")
            ) && reference.is_none()
            {
                continue;
            }
            let reference = reference.and_then(Value::as_str).ok_or_else(|| error(STATE, "legacy owner relation is incomplete; select a canonical current owner before migration"))?;
            let id = entry["id"]
                .as_str()
                .filter(|s| !s.is_empty())
                .ok_or_else(|| error(STATE, "legacy owner identity missing"))?;
            let candidate = json!({"id":id,"ref":reference});
            if candidates
                .iter()
                .any(|c: &Value| c["ref"] == candidate["ref"] && c["id"] != candidate["id"])
            {
                return Err(error(
                    STATE,
                    "conflicting legacy owner identities; preserved",
                ));
            }
            if !candidates.contains(&candidate) {
                candidates.push(candidate);
            }
        }
    }
    Ok(candidates)
}

/// Only migration input: aggregate status/revision/continuation never supplies
/// substantive current meaning. All meaning must survive in canonical owners.
pub(crate) fn legacy_disposition(target: &Path) -> Result<Value, CoreError> {
    let root =
        Dir::open_ambient_dir(target, cap_std::ambient_authority()).map_err(|e| error(STATE, e))?;
    let Some(bytes) = read(&root, STATE)? else {
        return Ok(json!({"status":"absent"}));
    };
    let state = parsed(STATE, &bytes)?;
    let candidates = legacy_references(&state, true)?;
    for candidate in &candidates {
        owner(&root, target, candidate, "legacy-upgrade-input", true)?;
        let body = parsed(
            candidate["ref"].as_str().unwrap(),
            &read(&root, candidate["ref"].as_str().unwrap())?.unwrap(),
        )?;
        crate::schema_validator(
            &crate::native_planning_create::canonical_schema(),
            "legacy migration owner",
        )?
        .validate(&body)
        .map_err(|e| error(STATE, e))?;
    }
    if !candidates.is_empty() {
        let selection_bytes = read(&root, SELECTION)?.ok_or_else(|| {
            error(
                STATE,
                "current owner selection must be reconciled before retiring legacy input",
            )
        })?;
        let selection = parsed(SELECTION, &selection_bytes)?;
        let held = inspect_carrier(target, &selection, true)?;
        let current = owner(&root, target, &selection["selected_owner"], SELECTION, true)?;
        if held["source"] != current["source"] {
            return Err(error(
                STATE,
                "current owner selection is stale; reconcile it before migration",
            ));
        }
    }
    Ok(
        json!({"status":"retirement-ready","role":"legacy-migration-input","owner_candidates":candidates,"authority":"No aggregate continuation authority; retire through exact Planning disposition after judging preserved owner intent."}),
    )
}

fn owner(
    root: &Dir,
    target: &Path,
    selected: &Value,
    provenance: &str,
    incumbent: bool,
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
    let bytes = read(root, path)?.ok_or_else(|| error(path, format!("selected owner missing ({id}); this checkout/base cannot represent the remembered work. Return to the source checkout or use a Git seed containing {path}, then resolve the current task relation through fresh start. Preserve the selector; absence supplies no independence, completion or deletion authority")))?;
    let body = parsed(path, &bytes)?;
    if body["id"] != id {
        return Err(error(path, "owner identity mismatch"));
    }
    let blocked = body["lifecycle"] == "blocked";
    let quiescent = matches!(
        body["lifecycle"].as_str(),
        Some("closed" | "complete" | "completed" | "archived")
    ) || matches!(
        body["phase"].as_str(),
        Some("closed" | "complete" | "completed" | "archived")
    );
    if !matches!(
        body["lifecycle"].as_str(),
        Some("live" | "planned" | "blocked" | "closed" | "complete" | "completed" | "archived")
    ) || ((quiescent || blocked) && !incumbent)
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
    let mut result = json!({"id":id,"ref":path,"selection_source":provenance,"source":{
        "target":target,"path":path,"owner":"planning","revision":format!("sha256:{:x}",Sha256::digest(&bytes))}});
    if quiescent {
        result["quiescent"] = json!(true);
    }
    if blocked {
        result["blocked"] = json!(true);
    }
    Ok(result)
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

/// Explicit Configuration maintenance is bounded independent work. Resolve its
/// posture through the same current Planning request semantics as ordinary work,
/// without taking custody of, selecting, or changing the remembered owner.
/// Only native ingress for the typed maintenance operation calls this method;
/// task wording and setup's write authorization are not relation evidence.
pub(crate) fn resolve_configuration_maintenance(
    target: &Path,
    current_work: &Value,
) -> Result<Value, CoreError> {
    let current = resolve(target, current_work, None)?;
    let Some(mut request) = current["requests"]
        .as_array()
        .and_then(|r| r.first())
        .cloned()
    else {
        return Ok(current);
    };
    request["arguments"] = json!({"answer":"independent", "task_posture":"direct"});
    resolve(target, current_work, Some(&request))
}

/// A posture answer refines an independent relation; it cannot override a
/// different relation or posture. Validate both envelopes against current owner
/// sources before selecting the refinement, regardless of carriage order.
pub(crate) fn compose_answers<'a>(
    target: &Path,
    work: &Value,
    requests: &'a [Value],
    contract: &Value,
) -> Result<Option<&'a Value>, CoreError> {
    let find = |kind: &str| {
        requests
            .iter()
            .find(|r| r["owner"] == "planning" && r["request_kind"] == kind)
    };
    let continuation = find("planning/continuation/v1");
    let selection = find("planning/select-owner/v1");
    let posture = find("planning/posture/v1");
    if selection.is_some() && (continuation.is_some() || posture.is_some()) {
        return Err(error(
            "request",
            "conflicting Planning selection and relation/posture answers",
        ));
    }
    if let (Some(relation), Some(posture)) = (continuation, posture) {
        for request in [relation, posture] {
            let current = resolve_with_contract(target, work, Some(request), Some(contract))?;
            if current["status"] == "stale" {
                return Err(CoreError::new(
                    "stale Planning answer composition; resolve current Planning choices",
                ));
            }
        }
        let args = &relation["arguments"];
        let declared_posture = if args["answer"] == "unrelated-direct" {
            Some("direct")
        } else {
            args["task_posture"].as_str()
        };
        if !matches!(
            args["answer"].as_str(),
            Some("independent" | "unrelated-direct")
        ) || declared_posture.is_some_and(|answer| posture["arguments"]["answer"] != answer)
        {
            return Err(CoreError::new(
                "conflicting Planning relation/posture answers",
            ));
        }
    }
    Ok(selection.or(posture).or(continuation))
}

/// Existing artifact-profile intent is realized by this bounded Planning owner.
/// Scratchpad presence is uncertain source context, never current work custody.
pub(crate) fn artifact_profile(target: &Path, profile: &Value) -> Result<Value, CoreError> {
    if profile.is_null() {
        return Ok(json!({"status":"absent","sources":[],"blockers":[]}));
    }
    let root = Dir::open_ambient_dir(target, ambient_authority())
        .map_err(|e| CoreError::new(e.to_string()))?;
    let declaration: Value = serde_json::from_str(include_str!(
        "../../../contracts/workflow_artifact_profiles.json"
    ))
    .map_err(|e| CoreError::new(e.to_string()))?;
    let selected = declaration["profiles"]
        .as_array()
        .and_then(|profiles| profiles.iter().find(|item| item["profile"] == *profile))
        .ok_or_else(|| {
            CoreError::new("selected workflow artifact profile has no canonical declaration")
        })?;
    let artifacts = selected["native_artifacts"]
        .as_array()
        .ok_or_else(|| CoreError::new("canonical artifact profile is missing native_artifacts"))?;
    let mut sources = vec![];
    for reference in artifacts {
        let reference = reference
            .as_str()
            .ok_or_else(|| CoreError::new("canonical native artifact reference must be text"))?;
        let source = crate::native_intent::observation(&root, reference);
        if source["status"] != "missing" {
            sources.push(source);
        }
    }
    let blockers = if sources.is_empty() {
        vec![]
    } else {
        vec![json!({
            "code":"native-artifact-durable-transfer-unresolved",
            "message":"Preserve optional runtime artifacts. Current durable facts must reach the existing Planning owner before delegation, handoff, review or completion; file presence is not current custody and the native typed transfer/update path remains unavailable.",
            "affects":["effect:delegation","claim:complete","claim:pr-complete"]
        })]
    };
    Ok(json!({"status":"current-owner-method","profile":profile,
        "canonical_owner":"planning","canonical_operation":"planning.reconcile",
        "source_rule":"Bounded repository-owned Planning state remains authoritative; local owner selection is not a cross-agent source of truth.",
        "native_artifacts":if artifacts.is_empty(){"not-relied-on"}else{"optional-runtime-scratchpads"},
        "handoff_rule":"Retain durable execution facts in the current Planning owner before handoff, review or session end; do not reconstruct retired aggregate record forests.",
        "sources":sources,"blockers":blockers,"transfer_status":if blockers.is_empty(){"not-required"}else{"unresolved-owner-update"},
        "authority_boundary":"Operational method only; profile selection, artifact recognition and Planning status confer no custody, proof or acceptance."}))
}

pub(crate) fn resolve_with_contract(
    target: &Path,
    current_work: &Value,
    request: Option<&Value>,
    current_full_contract: Option<&Value>,
) -> Result<Value, CoreError> {
    if let Some(request) = request.filter(|r| r["request_kind"] == "planning/select-owner/v1") {
        let quiet = resolve_context(target, current_work, None, current_full_contract, None)?;
        let contract = current_full_contract.unwrap_or(&quiet["capability_contract"]);
        prepare_request_value(
            json!({"request":request,"current_work":current_work,"capability_contract":contract}),
        )?;
        if request["source_revision"] != quiet["source_revision"]
            && !crate::native_planning_update::retained_continuation_current(
                target,
                &quiet["incumbent_owner"],
                request,
            )?
        {
            return Err(error(
                "selection request",
                "stale current-work selection request",
            ));
        }
    }
    resolve_context(
        target,
        current_work,
        request,
        current_full_contract,
        request.and_then(|r| r["arguments"]["owner_ref"].as_str()),
    )
}

/// Exact source choice for a producer-returned current affordance. This is a
/// private read-only projection, never a public request with validation skipped.
pub(crate) fn candidate(
    target: &Path,
    current_work: &Value,
    reference: &str,
    contract: &Value,
) -> Result<Value, CoreError> {
    resolve_context(target, current_work, None, Some(contract), Some(reference))
}
fn resolve_context(
    target: &Path,
    current_work: &Value,
    request: Option<&Value>,
    current_full_contract: Option<&Value>,
    reference: Option<&str>,
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
    // The local cursor is a resume hint. Only an exact retained work binding or
    // an explicit current request makes its sources dependencies of this task.
    // Malformed unrelated hints are preserved, never repaired or admitted.
    let hint = read(&root, SELECTION)
        .ok()
        .flatten()
        .and_then(|bytes| parsed(SELECTION, &bytes).ok());
    let bound = reference.is_some()
        || request.is_some_and(|r| {
            matches!(
                r["request_kind"].as_str(),
                Some(
                    "planning/select-owner/v1" | "planning/continuation/v1" | "planning/posture/v1"
                )
            ) || matches!(
                r["arguments"]["answer"].as_str(),
                Some("continue-selected" | "authorize-selector-transfer")
            )
        })
        || hint.as_ref().is_some_and(|s| {
            s[RETAINED]["invocation"]["arguments"]["current_work"] == *current_work
                || s[RETAINED]["current_work"] == *current_work
                    && s[RETAINED]["invocation"]["arguments"]
                        .get("current_work")
                        .is_some()
        });
    let creation_continuation = hint
        .as_ref()
        .and_then(|s| s["selected_owner"]["ref"].as_str())
        .map(|reference| {
            crate::native_planning_create::created_work_current(&target, reference, current_work)
        })
        .transpose()?
        .unwrap_or(false);
    let threads = if bound || creation_continuation {
        load(THREADS)?.unwrap_or(json!({}))
    } else {
        json!({})
    };
    let selection_scope = threads["selected_thread_id"]
        .as_str()
        .filter(|s| !s.is_empty())
        .unwrap_or("default");
    let selection = if bound || creation_continuation {
        load(SELECTION)?
    } else {
        None
    };
    let legacy = if bound || creation_continuation {
        load(STATE)?
    } else {
        None
    };
    let mut migration = json!({"status":"absent"});
    let legacy_candidates = if let Some(state) = &legacy {
        match legacy_references(state, false) {
            Ok(candidates) => {
                migration = json!({"status":"migration-required","role":"legacy-migration-input","owner_candidates":candidates,"current_authority":false});
                if let Err(error) = legacy_references(state, true) {
                    migration["status"] = json!("unsupported-preserved");
                    migration["reason"] = json!(error.to_string());
                }
                candidates
            }
            Err(e) => {
                migration = json!({"status":"unsupported-preserved","role":"legacy-migration-input","reason":e.to_string(),"current_authority":false});
                Vec::new()
            }
        }
    } else {
        Vec::new()
    };
    let retained = selection
        .as_ref()
        .map(|s| s[RETAINED].clone())
        .unwrap_or(Value::Null);
    let mut selected = Value::Null;
    let mut transition = Value::Null;
    if let Some(selection) = &selection {
        retained_transition(&target, selection)?;
        if selection["kind"] != "agentic-planning/owner-selection/v1"
            || selection["mode"].as_str().unwrap_or("local") != "local"
        {
            return Err(error(SELECTION, "unsupported selection kind or mode"));
        }
        if selection.get("selection_scope").is_some()
            && selection.get("current_work_id").is_some()
            && selection["selection_scope"] != selection["current_work_id"]
        {
            return Err(error(
                SELECTION,
                "conflicting local selection scope aliases",
            ));
        }
        // Legacy current_work_id is a local cursor alias, never public task identity.
        if selection
            .get("selection_scope")
            .unwrap_or(&selection["current_work_id"])
            .as_str()
            .filter(|s| !s.is_empty())
            .unwrap_or("default")
            != selection_scope
        {
            return Err(error(SELECTION, "local selection scope mismatch"));
        }
        for field in ["target_root", "repo_root", "worktree"] {
            if let Some(path) = selection[field].as_str().filter(|s| !s.is_empty())
                && std::fs::canonicalize(path).map_err(|e| error(SELECTION, e))? != target
            {
                return Err(error(SELECTION, "local selection target mismatch"));
            }
        }
        if reference.is_none_or(|r| selection["selected_owner"]["ref"] == r) {
            selected = owner(
                &root,
                &target,
                &selection["selected_owner"],
                SELECTION,
                true,
            )?;
        }
    } else if legacy_candidates.len() == 1 && migration["status"] != "unsupported-preserved" {
        selected = owner(
            &root,
            &target,
            &legacy_candidates[0],
            "legacy-upgrade-input",
            true,
        )?;
    }
    if let Some(reference) = reference {
        if selected.is_null() && selection.is_none() {
            let bytes = read(&root, reference)?
                .ok_or_else(|| error(reference, "requested owner missing"))?;
            let body = parsed(reference, &bytes)?;
            crate::native_planning_create::inspect_origin(&target, reference, &body)?;
            selected = owner(
                &root,
                &target,
                &json!({"id":body["id"],"ref":reference}),
                "explicit-current-owner",
                false,
            )?;
        } else if selected["ref"] != reference {
            let previous = selection
                .as_ref()
                .ok_or_else(|| error(SELECTION, "current native selection custody required"))?;
            let previous_retained = inspect_carrier(&target, previous, true)
                .map_err(|_|error(SELECTION,"existing selection is preserved; owner transfer requires current native custody"))?;
            let bytes = read(&root, reference)?
                .ok_or_else(|| error(reference, "requested owner missing"))?;
            let body = parsed(reference, &bytes)?;
            crate::native_planning_create::inspect_origin(&target, reference, &body)?;
            selected = owner(
                &root,
                &target,
                &json!({"id":body["id"],"ref":reference}),
                "explicit-current-owner",
                false,
            )?;
            let prior = read(&root, SELECTION)?
                .ok_or_else(|| error(SELECTION, "prior selector disappeared"))?;
            if parsed(SELECTION, &prior)? != *previous {
                return Err(error(SELECTION, "prior selector changed during proposal"));
            }
            let mut destination = previous.clone();
            destination.as_object_mut().unwrap().remove(RETAINED);
            // These former producer annotations describe the prior selection,
            // not the new owner's authority. The exact prior bytes and custody
            // remain bound below; do not copy stale annotations into the strict
            // current successor schema.
            destination
                .as_object_mut()
                .unwrap()
                .remove("planning_revision");
            destination.as_object_mut().unwrap().remove("reason");
            destination["selected_owner"] = json!({"id":selected["id"],"ref":selected["ref"]});
            transition = json!({"prior_sha256":format!("sha256:{:x}",Sha256::digest(&prior)),"prior_custody":previous_retained["custody"],"selection":destination});
        }
    }
    let revision = if transition.is_null() {
        digest(&json!({"sources":sources,"selected":selected}))?
    } else {
        digest(&json!({"sources":sources,"selected":selected,"selection_transition":transition}))?
    };
    let schema: Value = serde_json::from_str(include_str!(
        "../../../contracts/schemas/planning_reconciliation.schema.json"
    ))
    .expect("checked schema");
    let mut shape = schema["$defs"]["continuation_request"].clone();
    shape["$schema"] = schema["$schema"].clone();
    let declaration = json!({"kind":"planning/continuation/v1","result_kind":"agentic-workspace/planning-continuation-result/v1","input_schema":shape});
    let mut posture_shape = schema["$defs"]["posture_request"].clone();
    posture_shape["$schema"] = schema["$schema"].clone();
    let posture_declaration = json!({"kind":"planning/posture/v1","result_kind":"agentic-workspace/planning-continuation-result/v1","input_schema":posture_shape});
    let creation_declaration = crate::native_planning_create::declaration();
    let update_declaration = crate::native_planning_update::declaration();
    let recovery_declaration = crate::native_planning_update::recovery_declaration();
    let adoption_declaration = crate::native_planning_update::adoption_declaration();
    let handoff_declaration = crate::native_planning_update::handoff_declaration();
    let mut selection_shape = schema["$defs"]["selection_request"].clone();
    selection_shape["$schema"] = schema["$schema"].clone();
    let selection_declaration = json!({"kind":"planning/select-owner/v1","result_kind":"agentic-workspace/planning-continuation-result/v1","input_schema":selection_shape});
    let owner_revision = digest(&json!([
        declaration,
        selection_declaration,
        posture_declaration,
        creation_declaration,
        update_declaration,
        recovery_declaration,
        adoption_declaration,
        handoff_declaration,
        crate::native_planning_retention::declarations(),
        crate::native_planning_retention::operations()
    ]))?;
    let mut contract = json!({"kind":"agentic-workspace/capability-contract/v1","revision":"pending","owners":[{"owner":"planning","revision":owner_revision,"requests":[declaration,selection_declaration,posture_declaration,creation_declaration,update_declaration,recovery_declaration,adoption_declaration,handoff_declaration]}],"restriction_authorities":[{"owner":"planning","affects":["task","effect:planning-state","claim:complete"]}]});
    {
        contract["owners"][0]["effects"] = json!([{"id":"planning-state","domain":"planning"}]);
        contract["owners"][0]["domains"] = json!(["planning"]);
        let mut arguments = schema["$defs"]["operation_arguments"].clone();
        arguments["$schema"] = schema["$schema"].clone();
        arguments["$defs"] = schema["$defs"].clone();
        // Public operation discovery needs its input graph, not the internal
        // carrier, former-file reader or separate recovery request schemas.
        for unused in [
            "retained_reconciliation",
            "former_execplan",
            "update_recovery_request",
            "operation_arguments",
            "posture_request",
            "selection_request",
        ] {
            arguments["$defs"].as_object_mut().unwrap().remove(unused);
        }
        contract["owners"][0]["operations"] = json!([{"id":"planning.reconcile","semantic_revision":"planning-reconciliation-v1","input_schema":arguments,"result_kind":"agentic-planning/reconciliation-result/v1","effects":["planning-state"],"reads":["planning"]}]);
    }
    contract["owners"][0]["effects"] = json!([{"id":"planning-state","domain":"planning"}]);
    contract["owners"][0]["domains"] = json!(["planning"]);
    if contract["owners"][0]["operations"].is_null() {
        contract["owners"][0]["operations"] = json!([]);
    }
    contract["owners"][0]["operations"]
        .as_array_mut()
        .unwrap()
        .extend([
            crate::native_planning_create::operation(),
            crate::native_planning_update::operation(),
            crate::native_planning_update::recovery_operation(),
        ]);
    contract["owners"][0]["requests"]
        .as_array_mut()
        .unwrap()
        .extend(crate::native_planning_retention::declarations());
    contract["owners"][0]["operations"]
        .as_array_mut()
        .unwrap()
        .extend(crate::native_planning_retention::operations());
    contract["revision"] = json!(digest(&contract)?);
    let validation_contract = current_full_contract.unwrap_or(&contract);
    let mut template = json!({"kind":"agentic-workspace/public-request/v1","id":"planning/continuation/v1","owner":"planning","owner_revision":owner_revision,"source_revision":revision,"capability_revision":validation_contract["revision"],"task_identity":current_work,"request_kind":"planning/continuation/v1","arguments":{"answer":"continue-selected"}});
    if let Some(reference) = reference {
        template["arguments"]["owner_ref"] = json!(reference);
    }
    // Recognition grants no mutation authority. The owner supplies the entire
    // exact transition binding; the acting agent supplies the bounded domain answer.
    let transfer = if let Some(previous) = selection.as_ref().filter(|s| s.get(RETAINED).is_none())
    {
        let bytes = read(&root, SELECTION)?
            .ok_or_else(|| error(SELECTION, "selector disappeared during transfer proposal"))?;
        if parsed(SELECTION, &bytes)? != *previous || selected["selection_source"] != SELECTION {
            return Err(error(
                SELECTION,
                "selector changed during transfer proposal",
            ));
        }
        let binding = json!({"target":target,"selector":{"path":SELECTION,"revision":format!("sha256:{:x}",Sha256::digest(&bytes))},"selected_owner":selected,"current_work":current_work,"operation":"planning.reconcile","destination":{"path":SELECTION,"selection":previous},"effect":"one-time-selector-custody-transfer","prior_native_custody":"absent"});
        let mut request = template.clone();
        request["arguments"] = json!({"transfer_revision":digest(&binding)?});
        json!({"binding":binding,"request":request})
    } else {
        Value::Null
    };
    let mut transfer_authorized = false;
    let quiescent = selected["quiescent"] == true;
    let mut status = if selected.is_null() || quiescent {
        "direct"
    } else {
        "unresolved"
    };
    let mut planning_input = Value::Null;
    if !selected.is_null()
        && retained["kind"] == "agentic-planning/reconciliation-custody/v1"
        && (retained["current_work"] == *current_work || creation_continuation)
        && (retained["source"] == selected["source"]
            || crate::native_planning_update::retained_work_current(
                &target,
                &selected,
                current_work,
            )?)
    {
        status = "current";
        planning_input = json!({"target":target,"relevant":true,"source":selected["source"],"intent":{"current_work":current_work}});
        if retained["source"] == selected["source"] {
            planning_input["custody"] = retained["custody"].clone();
            planning_input["invocation"] = retained["invocation"].clone();
        }
        if let Some(previous) = &selection
            && let Some(recovered) = retained_transition(&target, previous)?
        {
            planning_input["selection_transition"] = recovered;
        }
    }
    if let Some(request) = request {
        prepare_request_value(
            json!({"request":request,"current_work":current_work,"capability_contract":validation_contract}),
        )?;
        if request["owner"] != "planning" {
            return Err(error("request", "another owner requested"));
        }
        if request["request_kind"] != "planning/select-owner/v1"
            && request["source_revision"] != revision
            && !crate::native_planning_update::retained_continuation_current(
                &target, &selected, request,
            )?
        {
            status = "stale";
            planning_input = Value::Null;
        } else if request["request_kind"] == "planning/posture/v1" {
            status = if request["arguments"]["answer"] == "direct" {
                "direct"
            } else {
                "planned"
            };
            planning_input = Value::Null;
        } else if request["arguments"]["answer"] == "authorize-selector-transfer" {
            if transfer.is_null()
                || request["arguments"]["transfer_revision"]
                    != transfer["request"]["arguments"]["transfer_revision"]
            {
                return Err(error(
                    SELECTION,
                    "domain selector transfer authorization is stale or already consumed",
                ));
            }
            transfer_authorized = true;
            transition = json!({"prior_sha256":transfer["binding"]["selector"]["revision"],"domain_authorization":request,"selection":selection});
            status = "current";
            planning_input = json!({"target":target,"relevant":true,"source":selected["source"],"intent":{"current_work":current_work}});
        } else if matches!(
            request["arguments"]["answer"].as_str(),
            Some("independent" | "unrelated-direct")
        ) {
            status = if request["arguments"]["answer"] == "unrelated-direct"
                || request["arguments"]["task_posture"] == "direct"
            {
                "direct"
            } else if request["arguments"]["task_posture"] == "planned" {
                "planned"
            } else {
                "independent"
            };
            planning_input = Value::Null;
        } else if selected.is_null() {
            if request["request_kind"] == "planning/select-owner/v1" && legacy.is_some() {
                status = "planned";
            } else {
                return Err(error(
                    "request",
                    "no currently selected owner to continue; name owner_ref or return to the source checkout",
                ));
            }
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
                planning_input["invocation"] = retained["invocation"].clone();
                if let Some(previous) = &selection
                    && let Some(recovered) = retained_transition(&target, previous)?
                {
                    planning_input["selection_transition"] = recovered;
                }
            }
        }
    }
    if (quiescent || selected["blocked"] == true) && status != "stale" && !transfer_authorized {
        let continuing = retained["current_work"] == *current_work
            || creation_continuation
            || request.is_some_and(explicit_continuation);
        let unrelated = request.is_some_and(|r| {
            matches!(
                r["arguments"]["answer"].as_str(),
                Some("independent" | "unrelated-direct")
            ) || r["request_kind"] == "planning/posture/v1"
        });
        if continuing && !unrelated {
            status = "reentry-required";
            planning_input = json!({"target":target,"relevant":true,"source":selected["source"],"intent":{"current_work":current_work}});
        } else if quiescent && !unrelated {
            status = "direct";
            planning_input = Value::Null;
        }
    }
    if !planning_input.is_null() && !transition.is_null() {
        planning_input["selection_transition"] = transition.clone();
    }
    let custody_required = status == "current"
        && selected["selection_source"] == SELECTION
        && retained.is_null()
        && !transfer_authorized;
    if custody_required {
        status = "custody-required";
        planning_input = Value::Null;
    }
    // The pending transfer decision itself constrains the task. A second
    // blocker would falsely promise a separate owner recovery for that choice.
    let mut blockers = json!([]);
    let mut migration_requests = Vec::new();
    if legacy.is_some()
        && selected.is_null()
        && (!legacy_candidates.is_empty() || migration["status"] == "unsupported-preserved")
    {
        for candidate_ref in &legacy_candidates {
            if let Ok(candidate) = candidate(
                &target,
                current_work,
                candidate_ref["ref"].as_str().unwrap(),
                validation_contract,
            ) {
                migration_requests.extend(
                    candidate["requests"]
                        .as_array()
                        .into_iter()
                        .flatten()
                        .cloned(),
                );
            }
        }
        status = "legacy-choice-required";
        planning_input = Value::Null;
        blockers = if migration_requests.is_empty() {
            json!([{"code":"legacy-planning-owner-resolution-unavailable","message":"Preserve the legacy aggregate: no safe existing canonical owner selection is available. Use Planning creation or explicit canonical-owner discovery for current work; no legacy selection or retirement request is supplied. Unfamiliar intent remains preserved.","affects":["claim:complete"]}])
        } else {
            json!([{"code":"legacy-planning-owner-choice-required","message":"Legacy aggregate is migration input, not current continuation. Select/reconcile a canonical owner with one exact legacy_aggregate.selection_requests entry. Unsupported material stays preserved; retirement is offered only for fully supported input.","affects":["task","claim:complete"]}])
        };
    }
    if legacy.is_some() {
        migration["selection_requests"] = json!(migration_requests);
    }
    let decisions = if custody_required {
        json!([{"id":"planning-selector-transfer","question":"Let native Planning maintain the existing saved plan selection?",
            "material":transfer["binding"],
            "response_request":{"request_kind":"planning/continuation/v1","arguments":transfer["request"]["arguments"]},
            "choices":[{"id":"authorize-selector-transfer","label":"Authorize this one-time transfer"}],"affects":["task"]}])
    } else if matches!(status, "unresolved" | "stale") {
        json!([{"id":"planning-continuation","question":"Does the current task continue the remembered Planning owner?","material":{"incumbent_owner":selected},"response_request":{"request_kind":"planning/continuation/v1","arguments":{}},"choices":[{"id":"continue-selected","label":"Continue the remembered Planning owner"},{"id":"independent","label":"This work is independent of that owner"}],"affects":["task"]}])
    } else if status == "independent" {
        json!([{"id":"planning-posture","question":"Is this independent work direct or planned?","response_request":{"request_kind":"planning/posture/v1","arguments":{"task_relation":"independent"}},"choices":[{"id":"direct","label":"Bounded direct work"},{"id":"planned","label":"Create or select a Planning owner"}],"affects":["task"]}])
    } else {
        json!([])
    };
    let task_relation = if status == "legacy-choice-required" {
        "unresolved"
    } else if matches!(status, "current" | "reentry-required" | "custody-required") {
        "continues"
    } else if request.is_some_and(|r| {
        matches!(
            r["arguments"]["answer"].as_str(),
            Some("independent" | "unrelated-direct")
        ) || r["request_kind"] == "planning/posture/v1"
    }) && status != "stale"
    {
        "independent"
    } else if selected.is_null() {
        "no-incumbent"
    } else {
        "unresolved"
    };
    let required_transition = match status {
        "direct" => "direct",
        "planned" => "create-or-select-owner",
        "independent" => "determine-posture",
        "current" => "continue",
        "reentry-required" => "reconcile",
        "custody-required" => "acquire-custody",
        "legacy-choice-required" => "select-canonical-owner",
        _ => "determine-relation",
    };
    let admitted = if task_relation == "continues" {
        selected.clone()
    } else {
        Value::Null
    };
    let contribution = json!({"owner":"planning","revision":revision,"facts":{"continuation":status,"task_relation":task_relation,"required_transition":required_transition,"incumbent_owner":selected,"selected_owner":admitted},"decisions":decisions,"blockers":blockers,"settled":status=="direct"});
    let mut selection_request = template.clone();
    selection_request["id"] = json!("planning/select-owner/v1");
    selection_request["request_kind"] = json!("planning/select-owner/v1");
    selection_request["arguments"] = json!({});
    Ok(
        json!({"status":status,"legacy_aggregate":migration,"source_revision":revision,"current_work_id":current_work["id"],"selection_scope":selection_scope,"task_relation":task_relation,"required_transition":required_transition,"incumbent_owner":selected,"selected_owner":admitted,"requests":if selected.is_null(){json!([])}else{json!([template])},"selection_requests":[selection_request],"selector_transfer":transfer,"capability_contract":contract,"contribution":contribution,"planning_input":planning_input,"selection_transition":transition,"custody_status":"not-admitted"}),
    )
}

/// Execute only after the public host has admitted this invocation against its
/// full composed decision (including configuration restrictions). Re-derive
/// source ownership under the selected owner's lock; public fields never supply
/// source or producer custody.
#[cfg(test)]
pub(crate) fn resolve_for_execution(
    target: &Path,
    current_work: &Value,
    current_full_contract: &Value,
) -> Result<Value, CoreError> {
    resolve_execution(target, current_work, current_full_contract, None)
}
pub(crate) fn resolve_for_invocation(
    target: &Path,
    current_work: &Value,
    current_full_contract: &Value,
    invocation: &Value,
) -> Result<Value, CoreError> {
    resolve_execution(
        target,
        current_work,
        current_full_contract,
        Some(invocation),
    )
}
fn resolve_execution(
    target: &Path,
    current_work: &Value,
    current_full_contract: &Value,
    invocation: Option<&Value>,
) -> Result<Value, CoreError> {
    let reference = invocation
        // The exact invocation names its source even when creation expanded
        // the work scope and the old deterministic creation path no longer
        // follows from current_work. This is a selector, never a custody grant;
        // resolve_context and invocation admission still validate it fully.
        .filter(|i| i["operation_id"] == "planning.reconcile")
        .and_then(|i| i["arguments"]["reconciliation"]["former_source"]["path"].as_str());
    let mut view = resolve_context(
        target,
        current_work,
        None,
        Some(current_full_contract),
        reference,
    )?;
    if !view["selector_transfer"].is_null()
        && let Some(request) = invocation.and_then(|i| {
            i["arguments"]["selection_transition"]
                .get("domain_authorization")
                .or_else(|| i["arguments"]["selection_transition"].get("human_authorization"))
        })
    {
        view = resolve_context(
            target,
            current_work,
            Some(request),
            Some(current_full_contract),
            reference,
        )?;
    }
    if view["incumbent_owner"].is_null()
        && let Some(reference) =
            crate::native_planning_create::created_reference(target, current_work)?
    {
        view = candidate(target, current_work, &reference, current_full_contract)?;
    }
    if view["incumbent_owner"].is_null() {
        return Err(error(
            SELECTION,
            "current source-selected owner required for reconciliation execution",
        ));
    }
    if view["planning_input"].is_null() {
        view["planning_input"] = json!({"target":std::fs::canonicalize(target).map_err(|e|error("target",e))?,"relevant":true,"source":view["incumbent_owner"]["source"],"intent":{"current_work":current_work}});
    }
    let target = std::fs::canonicalize(target).map_err(|e| error("target", e))?;
    let root =
        Dir::open_ambient_dir(&target, ambient_authority()).map_err(|e| error("target", e))?;
    let selection = read(&root, SELECTION)?
        .map(|bytes| parsed(SELECTION, &bytes))
        .transpose()?;
    if let Some(retained) = selection.as_ref().and_then(|value| value.get(RETAINED)) {
        validate_retained(retained)?;
        if retained["source"] == view["incumbent_owner"]["source"] {
            view["planning_input"]["custody"] = retained["custody"].clone();
            view["planning_input"]["invocation"] = retained["invocation"].clone();
            if let Some(transition) = retained_transition(&target, selection.as_ref().unwrap())? {
                view["planning_input"]["selection_transition"] = transition;
            }
        }
    }
    if !view["selection_transition"].is_null() {
        view["planning_input"]["selection_transition"] = view["selection_transition"].clone();
    }
    view["planning_input"]["capability_contract"] = current_full_contract.clone();
    // The invocation is an execution intention, not a fabricated public answer.
    // Exact operation and all final composed restrictions are admitted by the
    // caller before any handler effect is permitted.
    Ok(view)
}

pub(crate) fn disabled(target: &std::path::Path) -> Result<Value, CoreError> {
    crate::native_config::disabled_owner(
        target,
        "planning",
        &[SELECTION, THREADS, STATE],
        &[
            "effect:planning-state",
            "effect:implementation",
            "claim:complete",
        ],
    )
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

/// All native Planning mutations share the existing owner carrier lock.
pub(crate) fn owner_lock(root: &Dir) -> Result<std::fs::File, CoreError> {
    use cap_std::fs::OpenOptions;
    root.create_dir_all(".agentic-workspace/local/planning")
        .map_err(|e| error(SELECTION, e))?;
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
    Ok(lock)
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
    // acquired through this absent-only path. An occupied legacy carrier needs
    // the separately bound explicit human transfer, never ordinary continuation.
    let mut expected = read(&root, SELECTION)?;
    if let Some(bytes) = &expected {
        let value = parsed(SELECTION, bytes)?;
        if let Some(retained) = value.get(RETAINED) {
            validate_retained(retained)?;
        } else {
            let view =
                resolve_for_invocation(&target, current_work, current_full_contract, invocation)?;
            let transition = &view["selection_transition"];
            if (transition["domain_authorization"].is_null()
                && transition["human_authorization"].is_null())
                || *transition != invocation["arguments"]["selection_transition"]
                || transition["prior_sha256"] != format!("sha256:{:x}", Sha256::digest(bytes))
                || transition["selection"] != value
            {
                return Err(error(
                    SELECTION,
                    "existing local selection requires producer custody or exact domain transfer authorization; preserved",
                ));
            }
        }
    }

    root.create_dir_all(".agentic-workspace/local/planning")
        .map_err(|e| error(SELECTION, e))?;
    // Recheck confinement and absence after creating the bounded parents.
    if read(&root, SELECTION)? != expected {
        return Err(error(SELECTION, "selection changed before lock admission"));
    }
    let _lock = owner_lock(&root)?;
    if read(&root, SELECTION)? != expected {
        return Err(error(SELECTION, "selection changed before lock admission"));
    }
    let view = resolve_for_invocation(&target, current_work, current_full_contract, invocation)?;
    let initial_selection = json!({
        "kind":"agentic-planning/owner-selection/v1", "mode":"local",
        "selection_scope":view["selection_scope"],
        // Mechanically derived compatibility cursor, never the public work ID.
        "current_work_id":view["selection_scope"],
        "selected_owner":{"id":view["incumbent_owner"]["id"],"ref":view["incumbent_owner"]["ref"]}
    });
    let source = view["incumbent_owner"]["source"].clone();
    let mut input = json!({"target":target,"relevant":true,"source":source,"intent":{"current_work":current_work},"capability_contract":current_full_contract,"invocation":invocation});
    if let Some(requests) = invocation.get("source_requests") {
        input["source_requests"] = requests.clone();
    }
    if !view["planning_input"]["custody"].is_null() {
        input["custody"] = view["planning_input"]["custody"].clone();
    }
    let transition = view["planning_input"]["selection_transition"].clone();
    if !transition.is_null() {
        input["selection_transition"] = transition.clone();
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
            let fresh = candidate(
                &target,
                current_work,
                source["path"].as_str().unwrap(),
                current_full_contract,
            )?;
            if fresh["incumbent_owner"]["source"] != source {
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
            if !transition.is_null() {
                selection = transition["selection"].clone();
            }
            let producer_work = invocation["arguments"]
                .get("current_work")
                .unwrap_or(current_work);
            let retained = json!({"kind":"agentic-planning/reconciliation-custody/v1","current_work":producer_work,"source":source,"invocation":invocation,"custody":custody});
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
            static NEXT_TARGET: std::sync::atomic::AtomicU64 = std::sync::atomic::AtomicU64::new(0);
            let path = std::env::temp_dir().join(format!(
                "aw-native-planning-{}-{}-{}",
                std::process::id(),
                SystemTime::now()
                    .duration_since(UNIX_EPOCH)
                    .unwrap()
                    .as_nanos(),
                NEXT_TARGET.fetch_add(1, std::sync::atomic::Ordering::Relaxed)
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
                "../../../../../tests/fixtures/native_planning/delegation-lane-sweep.plan.json"
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
        let initial = selected_fixture(target);
        resolve(&target.0, &work(), Some(&initial["requests"][0])).unwrap()
    }
    // These controls deliberately select the named fixture before exercising
    // continuation, custody or mutation. Ordinary startup uses resolve(None).
    fn selected_fixture(target: &Target) -> Value {
        let quiet = resolve(&target.0, &work(), None).unwrap();
        candidate(&target.0, &work(), PLAN, &quiet["capability_contract"]).unwrap()
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
    fn switch_action(target: &Target) -> (Value, Value, String) {
        let (first, contract) = action(target);
        execute(&target.0, &work(), &first, &contract).unwrap();
        let mut body: Value =
            serde_json::from_slice(&fs::read(target.0.join(PLAN)).unwrap()).unwrap();
        body["id"] = json!("another-bounded-owner");
        let path = ".agentic-workspace/planning/execplans/another-bounded-owner.plan.json";
        target.write(path, &body.to_string());
        let proposed = candidate(&target.0, &work(), path, &contract).unwrap();
        let current = resolve_with_contract(
            &target.0,
            &work(),
            Some(&proposed["requests"][0]),
            Some(&contract),
        )
        .unwrap();
        let mut input = current["planning_input"].clone();
        input["capability_contract"] = contract.clone();
        let (input, _) = crate::planning::compose_input(input).unwrap();
        (
            crate::compile_value(input).unwrap()["primary_action"].clone(),
            contract,
            path.to_owned(),
        )
    }
    #[test]
    fn native_selection_switch_interruption_retains_exact_postimage() {
        for boundary in ["attempt", "commit", "foreign-postimage"] {
            let target = shared_target();
            let (invocation, contract, next) = switch_action(&target);
            let old_source = fs::read(target.0.join(PLAN)).unwrap();
            let mut stopped = false;
            let result = execute_observing(&target.0, &work(), &invocation, &contract, |custody| {
                if !stopped && (boundary != "commit" || !custody["committed"].is_null()) {
                    stopped = true;
                    if boundary == "foreign-postimage" {
                        let mut selector: Value =
                            serde_json::from_slice(&fs::read(target.0.join(SELECTION)).unwrap())
                                .unwrap();
                        selector["foreign"] = json!("unowned change");
                        target.write(SELECTION, &selector.to_string());
                    }
                    return Err(error(
                        "test",
                        "interrupted after exact selector replacement",
                    ));
                }
                Ok(())
            });
            assert!(result.is_err());
            let bytes = fs::read(target.0.join(SELECTION)).unwrap();
            if boundary == "foreign-postimage" {
                assert!(execute(&target.0, &work(), &invocation, &contract).is_err());
                assert_eq!(fs::read(target.0.join(SELECTION)).unwrap(), bytes);
            } else {
                execute(&target.0, &work(), &invocation, &contract).unwrap();
                assert!(fresh_current(&target));
                let selection: Value =
                    serde_json::from_slice(&fs::read(target.0.join(SELECTION)).unwrap()).unwrap();
                assert_eq!(selection["selected_owner"]["ref"], next);
                let reworded = json!({"kind":"current-work","id":"same-owner-reworded-task"});
                let initial = resolve(&target.0, &reworded, None).unwrap();
                let current = resolve(
                    &target.0,
                    &reworded,
                    Some(&initial["selection_requests"][0]),
                )
                .unwrap();
                let mut input = current["planning_input"].clone();
                input["capability_contract"] = contract.clone();
                assert_eq!(
                    crate::planning::compose_input(input).unwrap().1["current"],
                    true
                );
                execute(&target.0, &reworded, &invocation, &contract).unwrap();
            }
            assert_eq!(fs::read(target.0.join(PLAN)).unwrap(), old_source);
        }
    }
    #[test]
    fn native_selection_switch_stale_inputs_preserve_current_carrier() {
        for drift in ["selector", "destination", "submitted-custody"] {
            let target = shared_target();
            let (mut invocation, contract, next) = switch_action(&target);
            match drift {
                "selector" => {
                    let mut bytes = fs::read(target.0.join(SELECTION)).unwrap();
                    bytes.push(b' ');
                    fs::write(target.0.join(SELECTION), bytes).unwrap();
                }
                "destination" => {
                    let mut body: Value =
                        serde_json::from_slice(&fs::read(target.0.join(&next)).unwrap()).unwrap();
                    body["canonical_core"]["hard_constraints"] = json!("changed destination");
                    target.write(&next, &body.to_string());
                }
                _ => {
                    invocation["arguments"]["selection_transition"]["prior_custody"]["committed"]
                        ["revision"] = json!("forged")
                }
            }
            let before = fs::read(target.0.join(SELECTION)).unwrap();
            assert!(execute(&target.0, &work(), &invocation, &contract).is_err());
            assert_eq!(fs::read(target.0.join(SELECTION)).unwrap(), before);
        }
    }
    #[test]
    #[ignore = "subprocess-only selector interruption fixture"]
    fn native_selection_switch_process_child() {
        let target = PathBuf::from(std::env::var("AW_SELECTOR_TEST_TARGET").unwrap());
        let packet: Value =
            serde_json::from_slice(&fs::read(target.join("selector-test.json")).unwrap()).unwrap();
        let boundary = std::env::var("AW_SELECTOR_TEST_BOUNDARY").unwrap();
        execute_observing(
            &target,
            &work(),
            &packet["invocation"],
            &packet["contract"],
            |custody| {
                if boundary == "attempt" && custody["committed"].is_null()
                    || boundary == "commit" && !custody["committed"].is_null()
                {
                    std::process::exit(77);
                }
                Ok(())
            },
        )
        .unwrap();
    }
    #[test]
    fn native_selection_switch_process_exit_recovers_in_new_process() {
        for (human_transfer, boundary) in [
            (false, "attempt"),
            (false, "commit"),
            (true, "attempt"),
            (true, "commit"),
        ] {
            let target = shared_target();
            let (invocation, contract) = if human_transfer {
                target.select();
                human_transfer_action(&target)
            } else {
                let (invocation, contract, _) = switch_action(&target);
                (invocation, contract)
            };
            let material = fs::read(target.0.join(PLAN)).unwrap();
            target.write(
                "selector-test.json",
                &json!({"invocation":invocation,"contract":contract}).to_string(),
            );
            for (stage, expected) in [(boundary, 77), ("resume", 0)] {
                let output = std::process::Command::new(std::env::current_exe().unwrap())
                    .args([
                        "--ignored",
                        "--exact",
                        "native_planning::tests::native_selection_switch_process_child",
                    ])
                    .env("AW_SELECTOR_TEST_TARGET", &target.0)
                    .env("AW_SELECTOR_TEST_BOUNDARY", stage)
                    .output()
                    .unwrap();
                assert_eq!(
                    output.status.code(),
                    Some(expected),
                    "{}{}",
                    String::from_utf8_lossy(&output.stdout),
                    String::from_utf8_lossy(&output.stderr)
                );
            }
            assert!(fresh_current(&target));
            assert_eq!(fs::read(target.0.join(PLAN)).unwrap(), material);
        }
    }
    fn human_transfer_action(target: &Target) -> (Value, Value) {
        let view = continued(target);
        let mut request = view["selector_transfer"]["request"].clone();
        assert!(request["arguments"].get("answer").is_none());
        request["arguments"]["answer"] = json!("authorize-selector-transfer");
        let view = resolve(&target.0, &work(), Some(&request)).unwrap();
        let contract = view["capability_contract"].clone();
        let mut input = view["planning_input"].clone();
        input["capability_contract"] = contract.clone();
        let (input, _) = crate::planning::compose_input(input).unwrap();
        (
            crate::compile_value(input).unwrap()["primary_action"].clone(),
            contract,
        )
    }
    #[test]
    fn human_selector_transfer_rejects_drift_and_substituted_authority() {
        for drift in [
            "selector-bytes",
            "source-bytes",
            "work",
            "target",
            "destination",
            "answer",
            "binding",
            "missing-answer",
            "owner-choice",
        ] {
            let target = shared_target();
            target.select();
            let (mut invocation, contract) = human_transfer_action(&target);
            let mut current_work = work();
            match drift {
                "selector-bytes" => {
                    let mut bytes = fs::read(target.0.join(SELECTION)).unwrap();
                    bytes.push(b' ');
                    fs::write(target.0.join(SELECTION), bytes).unwrap();
                }
                "source-bytes" => {
                    let mut bytes = fs::read(target.0.join(PLAN)).unwrap();
                    bytes.push(b' ');
                    fs::write(target.0.join(PLAN), bytes).unwrap();
                }
                "work" => current_work["id"] = json!("different-work"),
                "target" => invocation["arguments"]["target"] = json!("different-target"),
                "destination" => {
                    invocation["arguments"]["selection_transition"]["selection"]["selected_owner"]
                        ["id"] = json!("different-owner")
                }
                "answer" => {
                    invocation["arguments"]["selection_transition"]["domain_authorization"]["arguments"]
                        ["answer"] = json!("continue-selected")
                }
                "binding" => {
                    invocation["arguments"]["selection_transition"]["domain_authorization"]["arguments"]
                        ["transfer_revision"] = json!("different-binding")
                }
                "owner-choice" => {
                    invocation["arguments"]["selection_transition"]["domain_authorization"]["arguments"]
                        ["owner_ref"] = json!(PLAN)
                }
                _ => {
                    invocation["arguments"]["selection_transition"]["domain_authorization"]["arguments"].as_object_mut().unwrap().remove("answer");
                }
            }
            let selector = fs::read(target.0.join(SELECTION)).unwrap();
            let source = fs::read(target.0.join(PLAN)).unwrap();
            assert!(
                execute(&target.0, &current_work, &invocation, &contract).is_err(),
                "{drift}"
            );
            assert_eq!(
                fs::read(target.0.join(SELECTION)).unwrap(),
                selector,
                "{drift}"
            );
            assert_eq!(fs::read(target.0.join(PLAN)).unwrap(), source, "{drift}");
            assert!(
                !target.0.join(".agentic-workspace/local/effects").exists(),
                "{drift}"
            );
        }
    }
    #[test]
    fn human_selector_transfer_is_consumed_and_foreign_postimage_is_preserved() {
        let target = shared_target();
        target.select();
        let original = fs::read(target.0.join(SELECTION)).unwrap();
        let (invocation, contract) = human_transfer_action(&target);
        execute(&target.0, &work(), &invocation, &contract).unwrap();
        let postimage = fs::read(target.0.join(SELECTION)).unwrap();
        fs::write(target.0.join(SELECTION), &original).unwrap();
        assert!(execute(&target.0, &work(), &invocation, &contract).is_err());
        assert_eq!(fs::read(target.0.join(SELECTION)).unwrap(), original);
        let mut changed = postimage;
        changed.push(b' ');
        fs::write(target.0.join(SELECTION), &changed).unwrap();
        assert!(execute(&target.0, &work(), &invocation, &contract).is_err());
        assert_eq!(fs::read(target.0.join(SELECTION)).unwrap(), changed);
    }
    #[test]
    fn native_planning_shared_continuation_acquires_selection_in_one_reconciliation() {
        let target = shared_target();
        let original = fs::read(target.0.join(PLAN)).unwrap();
        let initial = selected_fixture(&target);
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
        assert!(
            view["contribution"]["blockers"]
                .as_array()
                .unwrap()
                .is_empty()
        );
        assert_eq!(
            view["contribution"]["decisions"][0]["id"],
            "planning-selector-transfer"
        );
        assert!(
            view["contribution"]["actions"]
                .as_array()
                .is_none_or(|actions| actions.is_empty())
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
    fn remembered_scope_never_admits_task_relation_or_posture() {
        for explicit_thread in [false, true] {
            let target = Target::new();
            target.plan();
            target.select();
            if explicit_thread {
                target.write(THREADS, "{\"selected_thread_id\":\"thread-a\"}");
            }
            let before = fs::read(target.0.join(SELECTION)).unwrap();
            for absent in [false, true] {
                if absent {
                    fs::remove_file(target.0.join(PLAN)).unwrap();
                }
                let initial = resolve(&target.0, &work(), None).unwrap();
                assert_eq!(initial["status"], "direct");
                assert_eq!(initial["task_relation"], "no-incumbent");
                assert!(initial["incumbent_owner"].is_null());
                assert!(initial["planning_input"].is_null());
                assert_eq!(initial["contribution"]["decisions"], json!([]));
                assert_eq!(fs::read(target.0.join(SELECTION)).unwrap(), before);
            }
        }
    }
    #[test]
    fn native_planning_retains_current_custody_across_fresh_reads() {
        let target = Target::new();
        target.plan();
        target.share();
        let before = selected_fixture(&target);
        let (invocation, contract) = action(&target);
        let result = execute(&target.0, &work(), &invocation, &contract).unwrap();
        assert!(!result["custody"]["committed"].is_null());
        assert!(fresh_current(&target));
        let after = resolve(&target.0, &work(), None).unwrap();
        assert_eq!(
            before["incumbent_owner"]["source"],
            after["selected_owner"]["source"]
        );
        let selection: Value =
            serde_json::from_slice(&fs::read(target.0.join(SELECTION)).unwrap()).unwrap();
        assert_eq!(
            selection["selected_owner"],
            json!({"id":"delegation-lane-sweep","ref":PLAN})
        );
        assert_eq!(selection["current_work_id"], selection["selection_scope"]);
        assert_ne!(selection["current_work_id"], work()["id"]);
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
        assert_eq!(initial["status"], "direct");
        assert!(initial["planning_input"].is_null());
        let current = resolve(
            &target.0,
            &reworded,
            Some(&initial["selection_requests"][0]),
        )
        .unwrap();
        assert_eq!(current["planning_input"]["custody"], result["custody"]);
        let execution =
            resolve_for_invocation(&target.0, &reworded, &contract, &invocation).unwrap();
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
        let initial = selected_fixture(&target);
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
        let initial = selected_fixture(&target);
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
        let response = crate::answer_decision_value(json!({"decision":decision,"question":question["consequence_id"],"answer":"independent","capability_contract":contract})).unwrap();
        let request = response.get("request").unwrap_or(&response);
        let direct =
            resolve_with_contract(&target.0, &work(), Some(request), Some(&contract)).unwrap();
        assert_eq!(direct["status"], "independent");
        assert_eq!(direct["required_transition"], "determine-posture");
        assert!(resolve(&target.0, &work(), Some(request)).is_err());
        for posture in ["direct", "planned"] {
            let decision = crate::compile_value(json!({"contributions":[direct["contribution"]],"intent":{"current_work":work()},"capability_contract":contract})).unwrap();
            let question = &decision["pending_consequences"]["decisions"][0];
            let response = crate::answer_decision_value(json!({"decision":decision,"question":question["consequence_id"],"answer":posture,"capability_contract":contract})).unwrap();
            let request = response.get("request").unwrap_or(&response);
            let result =
                resolve_with_contract(&target.0, &work(), Some(request), Some(&contract)).unwrap();
            assert_eq!(result["status"], posture);
            assert_eq!(result["task_relation"], "independent");
            assert!(result["selected_owner"].is_null());
            assert!(
                result["contribution"]["decisions"]
                    .as_array()
                    .unwrap()
                    .is_empty()
            );
        }
    }
    #[test]
    fn native_planning_source_and_work_drift_cannot_reuse_intention() {
        let target = Target::new();
        let mut body = target.plan();
        target.share();
        let initial = selected_fixture(&target);
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
            candidate(
                &target.0,
                &work(),
                PLAN,
                &resolve(&target.0, &work(), None).unwrap()["capability_contract"]
            )
            .unwrap_err()
            .to_string()
            .contains("selection scope mismatch")
        );
        target.write(THREADS, "{}");
        fs::remove_file(target.0.join(PLAN)).unwrap();
        let quiet = resolve(&target.0, &work(), None).unwrap();
        let missing = resolve(&target.0, &work(), Some(&quiet["selection_requests"][0]))
            .unwrap_err()
            .to_string();
        assert!(missing.contains("selected owner missing"));
        assert!(missing.contains("checkout/base"));
        assert!(missing.contains("Return to the source checkout"));
    }
    #[test]
    fn native_planning_identity_and_unsupported_authority_fail_at_source() {
        let target = Target::new();
        let mut body = target.plan();
        target.share();
        body["id"] = json!("different-owner");
        target.write(PLAN, &body.to_string());
        assert!(
            candidate(
                &target.0,
                &work(),
                PLAN,
                &resolve(&target.0, &work(), None).unwrap()["capability_contract"]
            )
            .unwrap_err()
            .to_string()
            .contains("owner identity mismatch")
        );
        body["id"] = json!("delegation-lane-sweep");
        body["planning_revision"] = json!("old-global-revision");
        target.write(PLAN, &body.to_string());
        let quiet = resolve(&target.0, &work(), None).unwrap();
        let failure = candidate(&target.0, &work(), PLAN, &quiet["capability_contract"])
            .unwrap_err()
            .to_string();
        assert!(failure.contains(PLAN));
        assert!(failure.contains("planning_revision current authority projection"));
        body.as_object_mut().unwrap().remove("planning_revision");
        target.write(PLAN, &body.to_string());
        let other = Target::new();
        target.write(SELECTION, &json!({"kind":"agentic-planning/owner-selection/v1","current_work_id":"default","target_root":other.0,"selected_owner":{"id":"delegation-lane-sweep","ref":PLAN}}).to_string());
        assert!(
            candidate(
                &target.0,
                &work(),
                PLAN,
                &resolve(&target.0, &work(), None).unwrap()["capability_contract"]
            )
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
