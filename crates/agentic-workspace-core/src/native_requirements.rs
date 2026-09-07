//! Current-source ingress for acting-agent task requirements. A judgment is not
//! a capability fact, Verification evidence, or durable routing preference.
use crate::{CoreError, digest, direct_task, task_requirements};
use serde_json::{Value, json};

pub(crate) fn contract() -> Result<Value, CoreError> {
    let schema: Value = serde_json::from_str(include_str!(
        "../../../src/agentic_workspace/contracts/schemas/source_decision_input.schema.json"
    ))
    .expect("checked schema");
    let arguments = json!({"$schema":schema["$schema"],"$defs":{
        "task_requirements_identity":schema["$defs"]["task_requirements_identity"],
        "task_requirements_judgment":schema["$defs"]["task_requirements_judgment"]},
        "$ref":"#/$defs/task_requirements_judgment"});
    let declaration = json!({"kind":"assignment/judge-task-requirements/v1",
        "result_kind":"agentic-workspace/task-requirements/v1","input_schema":arguments});
    let mut contract = json!({"kind":"agentic-workspace/capability-contract/v1","revision":"pending",
        "owners":[{"owner":"assignment","revision":digest(&declaration)?,"requests":[declaration]}]});
    contract["revision"] = json!(digest(&contract)?);
    Ok(contract)
}

#[allow(clippy::too_many_arguments)]
pub(crate) fn view(
    task: &str,
    changed: &[String],
    transport_work: &Value,
    planning_subject: Option<&Value>,
    configuration: &Value,
    verification: &Value,
    request: Option<&Value>,
    contract: &Value,
) -> Result<Value, CoreError> {
    if configuration["assignment_requirements"]["configured"] != true {
        if request.is_some() {
            return Err(CoreError::new(
                "task requirements require current configured assignment scope",
            ));
        }
        return Ok(json!({"status":"not-applicable","requests":[]}));
    }
    let task_identity = direct_task::subject(task, changed)?;
    let current_work = planning_subject
        .map(|s| json!({"id":s["id"],"revision":s["revision"]}))
        .unwrap_or_else(|| task_identity.clone());
    let source_revision = digest(&json!({"task":task_identity,"work":current_work,
        "configuration":configuration["revision"],"verification_strategy":verification["strategy_revision"]}))?;
    let declaration = self::contract()?;
    let owner_revision = &declaration["owners"][0]["revision"];
    let template = json!({"kind":"agentic-workspace/public-request/v1","id":"assignment/task-requirements",
        "owner":"assignment","owner_revision":owner_revision,"source_revision":source_revision,
        "capability_revision":contract["revision"],"task_identity":transport_work,
        "request_kind":"assignment/judge-task-requirements/v1","arguments":{
            "task_identity":task_identity,"current_work":current_work,"role":"executor",
            "required_result_classes":[],"required_proof_classes":[],"verification_identity":null}});
    if let Some(request) = request {
        crate::prepare_request_value(
            json!({"request":request,"current_work":transport_work,"capability_contract":contract}),
        )?;
        if request["owner"] != "assignment" || request["source_revision"] != source_revision {
            return Err(CoreError::new(
                "task requirements source changed; resolve current judgment request",
            ));
        }
    }
    // The native Verification owner has not yet admitted a role-specific
    // evaluator obligation. Never turn its strategy document into one here.
    let result = task_requirements::view(
        json!({"kind":"agentic-workspace/task-requirements-input/v1",
        "task_identity":task_identity,"current_work":current_work,
        "judgment":request.map(|r|r["arguments"].clone()),"verification":null,
        "required_execution_guarantees":configuration["assignment_requirements"]["required_execution_guarantees"]}),
    )?;
    Ok(
        json!({"status":result["status"],"source_revision":source_revision,"requests":[template],"result":result,
        "remaining_owner_contracts":["current-native-execution-capability-feasibility","role-specific-verification-obligation"],
        "claim_boundary":"Current task judgment only; no assignment choice, local implementation, launch or proof authority."}),
    )
}
