//! Read-only source/executable observations for the existing feasibility owner.
use crate::{CoreError, digest};
use serde_json::{Value, json};
use sha2::{Digest, Sha256};
use std::io::Read;
use std::path::{Path, PathBuf};
pub(crate) fn declaration() -> Value {
    let schema: Value = serde_json::from_str(include_str!(
        "../../../src/agentic_workspace/contracts/schemas/source_decision_input.schema.json"
    ))
    .expect("schema");
    let mut shape = schema["$defs"]["execution_configuration_choice"].clone();
    shape["$schema"] = schema["$schema"].clone();
    json!({"kind":"assignment/select-execution-configuration/v1","result_kind":"agentic-workspace/execution-configurations/v1","input_schema":shape})
}
fn executable(
    target: &Path,
    command: &str,
    observed_paths: &mut std::collections::BTreeMap<PathBuf, Value>,
) -> Option<Value> {
    let mut candidates = Vec::<PathBuf>::new();
    if command.contains(['/', '\\']) || Path::new(command).is_absolute() {
        candidates.push(target.join(command));
    } else {
        if let Some(path) = std::env::var_os("PATH") {
            for directory in std::env::split_paths(&path) {
                candidates.push(directory.join(command));
            }
        }
        candidates.push(target.join(command));
    }
    let mut paths = Vec::new();
    for path in candidates {
        paths.push(path.clone());
        #[cfg(windows)]
        if path.extension().is_none() {
            for extension in ["exe", "com", "cmd", "bat"] {
                paths.push(path.with_extension(extension));
            }
        }
    }
    for path in paths {
        let Ok(metadata) = std::fs::metadata(&path) else {
            continue;
        };
        if !metadata.is_file() {
            continue;
        }
        #[cfg(unix)]
        {
            use std::os::unix::fs::PermissionsExt;
            if metadata.permissions().mode() & 0o111 == 0 {
                continue;
            }
        }
        let Ok(path) = path.canonicalize() else {
            continue;
        };
        if let Some(observed) = observed_paths.get(&path) {
            return Some(observed.clone());
        }
        // Observe bytes, not only replaceable path/mtime hints. Discovery never
        // executes them, and a failure cannot authorize a different PATH peer.
        let mut file = std::fs::File::open(&path).ok()?;
        let before = file.metadata().ok()?;
        if before.len() > 134_217_728 {
            return None;
        }
        let mut hasher = Sha256::new();
        let mut buffer = [0u8; 65536];
        let mut total = 0u64;
        loop {
            let count = file.read(&mut buffer).ok()?;
            if count == 0 {
                break;
            }
            total += count as u64;
            if total > 134_217_728 {
                return None;
            }
            hasher.update(&buffer[..count]);
        }
        let after = file.metadata().ok()?;
        if total != before.len()
            || after.len() != before.len()
            || after.modified().ok() != before.modified().ok()
        {
            return None;
        }
        let observed = json!({"path":path,"size":after.len(),"modified":after.modified().ok().and_then(|t|t.duration_since(std::time::UNIX_EPOCH).ok()).map(|d|d.as_nanos().to_string()),"content_digest":format!("sha256:{:x}",hasher.finalize())});
        observed_paths.insert(path, observed.clone());
        return Some(observed);
    }
    None
}
#[allow(clippy::too_many_arguments)]
pub(crate) fn view(
    target: &Path,
    work: &Value,
    requirements: &Value,
    request: Option<&Value>,
    contract: &Value,
    transport_work: &Value,
    handoff_inputs: &Value,
    target_scope: &Value,
) -> Result<Value, CoreError> {
    let observed = match crate::native_assignment_policy::load(target) {
        Ok(value) => value,
        Err(error) => {
            return Ok(
                json!({"status":"unresolved","gaps":[error.to_string()],"requests":[],"candidates":[]}),
            );
        }
    };
    let local = observed.effective;
    let source_policy = observed.policy;
    let mut gaps = Vec::new();
    if source_policy["enforceable"] != true {
        gaps.push("binding-policy-current-target-unresolved");
    }
    let source_revision = digest(
        &json!({"sources":observed.revision,"requirements":requirements["revision"],"handoff_inputs":handoff_inputs["revision"],"work":work,"target_scope":target_scope}),
    )?;
    if requirements["status"] != "resolved" {
        return Ok(
            json!({"status":"unresolved","gaps":["current-task-requirements-required"],"source_revision":source_revision,"requests":[],"candidates":[]}),
        );
    }
    let targets = local["delegation_targets"].as_object();
    if targets.is_some_and(|v| v.len() > 32) {
        return Err(CoreError::new(
            "native configuration inventory exceeds 32 targets; preserve source and narrow owner scope",
        ));
    }
    for name in target_scope
        .as_object()
        .into_iter()
        .flatten()
        .map(|(name, _)| name)
    {
        if !local["delegation_targets"][name]["forbidden_task_classes"]
            .as_array()
            .is_some_and(|v| !v.is_empty())
        {
            return Err(CoreError::new(
                "target scope judgment names no current configured restriction",
            ));
        }
    }
    let mut scope_questions = Vec::new();
    let mut target_context = Vec::new();
    let mut candidates = Vec::new();
    let mut unavailable = Vec::new();
    let mut manual_targets = Vec::new();
    let mut observed_paths = std::collections::BTreeMap::new();
    for (name, profile) in targets.into_iter().flatten() {
        let transports = match crate::transport_source::decode(profile) {
            Ok(value) => value,
            Err(error) => {
                unavailable.push(json!({"target":name,"source_ref":format!(".agentic-workspace/config.local.toml#delegation_targets.{name}"),"gap":format!("transport-source-invalid:{error}")}));
                continue;
            }
        };
        if serde_json::to_vec(profile).is_ok_and(|bytes| bytes.len() <= 8192) {
            target_context.push(json!({"target":name,"profile":profile,"revision":digest(profile)?,"claim_boundary":"Configured human priors and restrictions, not learned proof or capability grants."}));
        } else {
            unavailable.push(json!({"target":name,"gap":"target-context-exceeds-bound"}));
        }
        let current = source_policy["current_target_status"] == "known-profile"
            && source_policy["current_profile"]["name"] == *name;
        if profile["forbidden_task_classes"]
            .as_array()
            .is_some_and(|v| !v.is_empty())
        {
            scope_questions.push(json!({"target":name,"source_ref":format!("delegation_targets.{name}.forbidden_task_classes"),"restrictions":profile["forbidden_task_classes"],"answer_field":format!("target_scope.{name}"),"choices":["applies","not-applicable","unresolved"],"judgment":target_scope[name],"authority":"acting-agent applicability only; no waiver"}));
            if !matches!(
                target_scope[name]["status"].as_str(),
                Some("applies" | "not-applicable")
            ) {
                unavailable.push(json!({"target":name,"source_ref":format!("delegation_targets.{name}.forbidden_task_classes"),"gap":"current-target-task-scope-judgment-required","claim_boundary":"Unknown current task taxonomy does not establish target failure or waive a source prohibition."}));
            }
        }
        let mut transports = transports;
        if current {
            transports.retain(|v| v["kind"] != "internal");
            transports.insert(
                0,
                json!({"kind":"current-host","method":"internal","command":[]}),
            );
        } else if source_policy["manual_transport_policy"] != "disabled"
            && !transports.iter().any(|v| v["method"] == "manual")
        {
            transports.push(json!({"kind":"manual","method":"manual","command":[]}));
        }
        for transport in transports {
            if candidates.len() >= 32 {
                unavailable.push(json!({"target":name,"gap":"native-configuration-candidate-bound","source_ref":format!(".agentic-workspace/config.local.toml#delegation_targets.{name}")}));
                break;
            }
            if serde_json::to_vec(&transport).is_ok_and(|v| v.len() > 8192) {
                unavailable.push(json!({"target":name,"gap":"native-transport-detail-bound","source_ref":format!(".agentic-workspace/config.local.toml#delegation_targets.{name}")}));
                continue;
            }
            if transport["kind"] == "native" {
                unavailable.push(json!({"target":name,"source":transport,"gap":"native-provider-adapter-observation-unavailable"}));
                continue;
            }
            let method = transport["method"].as_str().unwrap();
            let retained = current && transport["kind"] == "current-host";
            let manual = method == "manual";
            let observed = transport["command"]
                .as_array()
                .and_then(|v| v.first())
                .and_then(Value::as_str)
                .and_then(|s| executable(target, s, &mut observed_paths));
            let authority = source_policy["effective_mode"] != "off"
                && gaps.is_empty()
                && (retained
                    || if manual {
                        source_policy["manual_transport_policy"] != "disabled"
                    } else {
                        source_policy["transport_authority"] == "automatic"
                            && source_policy["effective_mode"] != "off"
                    });
            let profile_safe = (profile["identity_status"].is_null()
                || profile["identity_status"] == "active")
                && (!profile["forbidden_task_classes"]
                    .as_array()
                    .is_some_and(|v| !v.is_empty())
                    || target_scope[name]["status"] == "not-applicable")
                && !profile["human_control_modes"]
                    .as_array()
                    .is_some_and(|v| v.iter().any(|i| i == "off"));
            if manual {
                manual_targets.push(json!({"target":name,"source_ref":format!(".agentic-workspace/config.local.toml#delegation_targets.{name}"),"source_policy_eligible":authority&&profile_safe,"required_result_classes_supported":requirements["requirements"]["required_result_classes"].as_array().is_some_and(|classes| classes.iter().all(|class| class == "read-only")),"handoff_constructible":handoff_inputs["status"]=="ready","automatic_invocation":false,"gap":if handoff_inputs["status"]=="ready"{""}else{"native-manual-input-completeness-unresolved"},"target_best_fit":"unresolved-not-rejected"}));
            }
            // Discovery must describe the same return path that dispatch implements.
            let process = crate::native_delegation::supports_process(&transport);
            let result_classes = if retained || process {
                json!(["read-only", "unapplied-patch"])
            } else {
                json!(["read-only"])
            };
            let capability = digest(
                &json!({"profile":profile,"target_scope":target_scope[name],"transport":transport,"executable":observed,"process_supported":process,"result_classes":result_classes,"handoff_inputs":if manual{handoff_inputs["revision"].clone()}else{Value::Null}}),
            )?;
            candidates.push(json!({"id":format!("{name}:{method}"),"target":name,"transport":method,"capability_revision":capability,"current":true,"authorized":authority,"safe":profile_safe&&(retained||manual||local["safety"]["safe_to_auto_run_commands"]==true),"constructible":(manual&&handoff_inputs["status"]=="ready")||retained||observed.is_some()&&process,"result_classes":result_classes,"proof_classes":[],"independent_context":false,"concurrency_available":true,"execution":{"adapter":transport,"observed_executable":observed,"source_revision":source_revision,"context_strategy":"bounded","continuity":{"mode":"adapter-owned-unknown"}}}));
        }
    }
    let mut input = requirements["requirements"].clone();
    input["work"] = work.clone();
    input["candidates"] = json!(candidates);
    input["selection"] = Value::Null;
    let preview = crate::assignment::configurations(input.clone())?;
    if let Some(request) = request {
        crate::prepare_request_value(
            json!({"request":request,"current_work":transport_work,"capability_contract":contract}),
        )?;
        if request["owner"] != "assignment"
            || request["request_kind"] != "assignment/select-execution-configuration/v1"
            || request["source_revision"] != source_revision
        {
            return Err(CoreError::new(
                "execution configuration source/task/requirements changed",
            ));
        }
        input["selection"] = request["arguments"].clone();
    }
    let result = crate::assignment::configurations(input)?;
    let owner = contract["owners"]
        .as_array()
        .unwrap()
        .iter()
        .find(|o| o["owner"] == "assignment")
        .unwrap();
    let requests:Vec<Value>=preview["candidates"].as_array().into_iter().flatten().filter(|r|r["eligible"]==true).map(|r|json!({"kind":"agentic-workspace/public-request/v1","id":"assignment/execution-configuration","owner":"assignment","owner_revision":owner["revision"],"source_revision":source_revision,"capability_revision":contract["revision"],"task_identity":transport_work,"request_kind":"assignment/select-execution-configuration/v1","arguments":{"revision":preview["revision"],"candidate":r["configuration"]["id"]}})).collect();
    Ok(
        json!({"status":"observed","source_revision":source_revision,"configurations":result,"requests":requests,"unavailable_adapters":unavailable,"manual_targets":manual_targets,"target_scope_questions":scope_questions,"target_context":target_context,"policy":source_policy,"gaps":gaps,"claim_boundary":"Feasibility and exact choice only; no best-fit assignment, dispatch, human authority, proof or completion. Provider adapter discovery remains separate."}),
    )
}
