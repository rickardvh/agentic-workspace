//! Read-only source/executable observations for the existing feasibility owner.
use crate::{CoreError, digest};
use cap_std::{ambient_authority, fs::Dir};
use serde_json::{Value, json};
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
fn executable(target: &Path, command: &str) -> Option<Value> {
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
        return Some(
            json!({"path":path,"size":metadata.len(),"modified":metadata.modified().ok().and_then(|t|t.duration_since(std::time::UNIX_EPOCH).ok()).map(|d|d.as_nanos().to_string())}),
        );
    }
    None
}
pub(crate) fn view(
    target: &Path,
    work: &Value,
    requirements: &Value,
    request: Option<&Value>,
    contract: &Value,
    transport_work: &Value,
) -> Result<Value, CoreError> {
    let root = Dir::open_ambient_dir(target, ambient_authority())
        .map_err(|e| CoreError::new(e.to_string()))?;
    let (local, local_revision) = crate::native_config::load(
        &root,
        ".agentic-workspace/config.local.toml",
        include_str!(
            "../../../src/agentic_workspace/contracts/schemas/workspace_local_override.schema.json"
        ),
    )
    .map_err(CoreError::new)?
    .unwrap_or((json!({}), "absent".into()));
    let (shared, shared_revision) = crate::native_config::load(
        &root,
        ".agentic-workspace/config.toml",
        include_str!(
            "../../../src/agentic_workspace/contracts/schemas/workspace_config.schema.json"
        ),
    )
    .map_err(CoreError::new)?
    .unwrap_or((json!({}), "absent".into()));
    let mut gaps = Vec::new();
    if shared.get("delegation").is_some() || shared.get("delegation_targets").is_some() {
        gaps.push("former-shared-assignment-source-reconciliation-required");
    }
    let policy = &local["delegation"];
    if policy.get("mode").is_some() || policy.get("execution_role").is_some() {
        gaps.push("former-delegation-control-reconciliation-required");
    }
    let source_revision = digest(
        &json!({"local":local_revision,"shared":shared_revision,"requirements":requirements["revision"],"work":work}),
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
    let mut candidates = Vec::new();
    let mut unavailable = Vec::new();
    for (name, profile) in targets.into_iter().flatten() {
        let transports = match crate::transport_source::decode(profile) {
            Ok(value) => value,
            Err(error) => {
                unavailable.push(json!({"target":name,"source_ref":format!(".agentic-workspace/config.local.toml#delegation_targets.{name}"),"gap":format!("transport-source-invalid:{error}")}));
                continue;
            }
        };
        let current = policy["current_target"].as_str().is_some_and(|id| {
            id == name
                || profile["target_id"] == id
                || profile["aliases"]
                    .as_array()
                    .is_some_and(|a| a.iter().any(|v| v == id))
        });
        let mut transports = transports;
        if current {
            transports.retain(|v| v["kind"] != "internal");
            transports.insert(
                0,
                json!({"kind":"current-host","method":"internal","command":[]}),
            );
        } else if policy["manual_transport_policy"] != "disabled"
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
                .and_then(|s| executable(target, s));
            let authority = gaps.is_empty()
                && (retained
                    || if manual {
                        policy["manual_transport_policy"] != "disabled"
                    } else {
                        policy["transport_authority"] == "automatic"
                    });
            let profile_safe = (profile["identity_status"].is_null()
                || profile["identity_status"] == "active")
                && !profile["forbidden_task_classes"]
                    .as_array()
                    .is_some_and(|v| !v.is_empty())
                && !profile["human_control_modes"]
                    .as_array()
                    .is_some_and(|v| v.iter().any(|i| i == "off"));
            let capability =
                digest(&json!({"profile":profile,"transport":transport,"executable":observed}))?;
            candidates.push(json!({"id":format!("{name}:{method}"),"target":name,"transport":method,"capability_revision":capability,"current":true,"authorized":authority,"safe":profile_safe&&(retained||manual||local["safety"]["safe_to_auto_run_commands"]==true),"constructible":retained||manual||observed.is_some()&&matches!(method,"cli"|"api"),"result_classes":["read-only","unapplied-patch"],"proof_classes":[],"independent_context":false,"concurrency_available":true,"execution":{"adapter":transport,"observed_executable":observed,"source_revision":source_revision,"context_strategy":"bounded","continuity":{"mode":"adapter-owned-unknown"}}}));
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
        json!({"status":"observed","source_revision":source_revision,"configurations":result,"requests":requests,"unavailable_adapters":unavailable,"gaps":gaps,"claim_boundary":"Feasibility and exact choice only; no best-fit assignment, dispatch, human authority, proof or completion. Provider adapter discovery remains separate."}),
    )
}
