//! Current configured startup text is source context, never inferred mutation custody.
use crate::{CoreError, digest, native_intent};
use cap_std::{ambient_authority, fs::Dir};
use serde_json::{Value, json};
use std::path::Path;

/// Startup text can govern every currently declared effectful owner operation.
/// Read requests remain available: their contracts declare no operation effects.
pub(crate) fn restrict_operations(view: &mut Value, contracts: &[&Value]) -> Result<(), CoreError> {
    let effects: std::collections::BTreeSet<String> = contracts
        .iter()
        .flat_map(|contract| contract["owners"].as_array().into_iter().flatten())
        .flat_map(|owner| owner["operations"].as_array().into_iter().flatten())
        .flat_map(|operation| operation["effects"].as_array().into_iter().flatten())
        .filter_map(Value::as_str)
        .map(|effect| format!("effect:{effect}"))
        .collect();
    let capability = &mut view["capability_contract"];
    let scopes = capability["restriction_authorities"][0]["affects"]
        .as_array_mut()
        .unwrap();
    for effect in &effects {
        if !scopes.iter().any(|scope| scope == effect) {
            scopes.push(json!(effect));
        }
    }
    capability["revision"] = json!("pending");
    capability["revision"] = json!(digest(capability)?);
    for blocker in view["contribution"]["blockers"].as_array_mut().unwrap() {
        let scopes = blocker["affects"].as_array_mut().unwrap();
        for effect in &effects {
            if !scopes.iter().any(|scope| scope == effect) {
                scopes.push(json!(effect));
            }
        }
    }
    Ok(())
}

pub(crate) fn view(
    target: &Path,
    work: &Value,
    configuration: &Value,
    request: Option<&Value>,
    contract: Option<&Value>,
) -> Result<Value, CoreError> {
    let root = Dir::open_ambient_dir(target, ambient_authority())
        .map_err(|e| CoreError::new(e.to_string()))?;
    let reference = configuration["agent_instructions_file"].as_str();
    let source = reference
        .map(|r| native_intent::observation(&root, r))
        .unwrap_or(Value::Null);
    let revision = digest(&json!({"source":source,"configuration":configuration["revision"]}))?;
    let schema: Value = serde_json::from_str(include_str!(
        "../../../src/agentic_workspace/contracts/schemas/source_decision_input.schema.json"
    ))
    .expect("checked schema");
    let mut arguments = schema["$defs"]["system_intent_read_arguments"].clone();
    arguments["$schema"] = schema["$schema"].clone();
    let shape = json!({"kind":"startup-adapter/read-current-source/v1","result_kind":"agentic-workspace/startup-adapter-source-read/v1","input_schema":arguments});
    let owner_revision = digest(&shape)?;
    let mut scopes = vec![json!("effect:implementation"), json!("claim:complete")];
    if let Some(reference) = reference {
        scopes.push(json!(format!("effect:write:{reference}")));
    }
    let mut capability = json!({"kind":"agentic-workspace/capability-contract/v1","revision":"pending","owners":[{"owner":"startup-adapter","revision":owner_revision,"requests":[shape]}],"restriction_authorities":[{"owner":"startup-adapter","affects":scopes}]});
    capability["revision"] = json!(digest(&capability)?);
    let validation = contract.unwrap_or(&capability);
    let requests = if source["status"] == "present" {
        vec![
            json!({"kind":"agentic-workspace/public-request/v1","id":"startup-adapter/read-current","owner":"startup-adapter","owner_revision":owner_revision,"source_revision":revision,"capability_revision":validation["revision"],"task_identity":work,"request_kind":"startup-adapter/read-current-source/v1","arguments":{"reference":source["reference"],"revision":source["revision"]}}),
        ]
    } else {
        vec![]
    };
    let mut response = Value::Null;
    if let Some(request) = request {
        let admitted = crate::prepare_request_value(
            json!({"request":request,"current_work":work,"capability_contract":validation}),
        )?;
        if request["owner"] != "startup-adapter"
            || request["source_revision"] != revision
            || !requests
                .iter()
                .any(|r| r["arguments"] == request["arguments"])
        {
            return Err(CoreError::new(
                "startup adapter read is stale or outside current configured source",
            ));
        }
        let detail = native_intent::bytes(&root, reference.unwrap())?
            .ok_or_else(|| CoreError::new("startup adapter disappeared"))?;
        if native_intent::hash(&detail) != source["revision"] {
            return Err(CoreError::new("startup adapter changed during read"));
        }
        let text = String::from_utf8(detail)
            .map_err(|_| CoreError::new("startup adapter is not UTF-8"))?;
        let current = crate::native_config::view(target)?;
        if current["revision"] != configuration["revision"]
            || view(target, work, &current, None, None)?["revision"] != revision
        {
            return Err(CoreError::new(
                "startup adapter source or configuration changed during read",
            ));
        }
        response = json!({"kind":"agentic-workspace/startup-adapter-source-read/v1","status":"read","source":source,"text":text,"request_identity":admitted["identity"],"authority_boundary":"Exact existing startup text for acting-agent judgment. Delivery grants no rule satisfaction, proof, acceptance or mutation custody; a generated fence cannot authorize overwriting surrounding source."});
    }
    let mut blockers = vec![];
    if reference.is_some() && response.is_null() {
        let unavailable = source["status"] != "present";
        blockers.push(json!({"code":if unavailable{"configured-startup-source-unavailable"}else{"configured-startup-source-read-required"},"message":"Read the exact current configured startup source before affected implementation or completion judgment; preserve its contents and use source-owner repair if unavailable.","affects":if unavailable{scopes}else{vec![json!("effect:implementation"),json!("claim:complete")]}}));
    }
    let mut result = json!({"kind":"agentic-workspace/native-startup-adapter-view/v1","status":if reference.is_none(){"absent"}else if response.is_null(){"source-context-required"}else{"source-context-delivered"},"revision":revision,"source":source,"requests":requests,"response":response,"capability_contract":capability,"contribution":{"owner":"startup-adapter","revision":revision,"settled":blockers.is_empty(),"blockers":blockers}});
    if let Some(contract) = contract {
        restrict_operations(&mut result, &[contract])?;
    }
    Ok(result)
}
