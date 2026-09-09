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
    let mut declarations = vec![
        declaration,
        crate::native_execution::declaration(),
        crate::native_assignment::declaration(),
    ];
    declarations.extend(crate::native_handoff::declarations());
    let mut contract = json!({"kind":"agentic-workspace/capability-contract/v1","revision":"pending",
        "owners":[{"owner":"assignment","revision":digest(&json!(declarations))?,"requests":declarations}],"restriction_authorities":[{"owner":"assignment","affects":["effect:implementation","claim:claim-work-complete","claim:claim-slice-complete"]}]});
    contract["revision"] = json!(digest(&contract)?);
    Ok(contract)
}

#[allow(clippy::too_many_arguments)]
pub(crate) fn view(
    target: &std::path::Path,
    task: &str,
    changed: &[String],
    transport_work: &Value,
    planning_subject: Option<&Value>,
    configuration: &Value,
    verification: &Value,
    request: Option<&Value>,
    verification_request: Option<&Value>,
    execution_request: Option<&Value>,
    input_request: Option<&Value>,
    contract: &Value,
) -> Result<Value, CoreError> {
    if configuration["assignment_requirements"]["configured"] != true {
        if request.is_some()
            || verification_request.is_some()
            || execution_request.is_some()
            || input_request.is_some()
        {
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
    let mut template = json!({"kind":"agentic-workspace/public-request/v1","id":"assignment/task-requirements",
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
    let mut judgment = request
        .map(|r| r["arguments"].clone())
        .unwrap_or(Value::Null);
    let target_scope = judgment
        .as_object_mut()
        .and_then(|j| j.remove("target_scope"))
        .unwrap_or_else(|| json!({}));
    let nested = judgment
        .as_object_mut()
        .and_then(|j| j.remove("verification_request"));
    if nested.is_some() && verification_request.is_some() {
        return Err(CoreError::new(
            "supply one current Verification requirements request",
        ));
    }
    let selected_request = verification_request
        .or(nested.as_ref())
        .filter(|v| !v.is_null());
    let mut obligation = Value::Null;
    if judgment["role"] == "evaluator" || selected_request.is_some() {
        obligation = crate::verification_requirements::resolve(
            json!({"target":target,"task":task,"changed_paths":changed,
            "current_work":current_work,"role":judgment["role"].as_str().unwrap_or("evaluator"),"request":selected_request}),
            Some(transport_work),
            Some(contract),
        )?;
        if !obligation["verification"].is_null()
            && judgment["verification_identity"].is_null()
            && !judgment.is_null()
        {
            judgment["verification_identity"] = json!({"id":obligation["verification"]["id"],"revision":obligation["verification"]["revision"]});
        }
    }
    let result = task_requirements::view(
        json!({"kind":"agentic-workspace/task-requirements-input/v1",
        "task_identity":task_identity,"current_work":current_work,
        "judgment":judgment,"verification":obligation["verification"],
        "required_execution_guarantees":configuration["assignment_requirements"]["required_execution_guarantees"]}),
    )?;
    let mut handoff_inputs = crate::native_handoff::inputs_view(
        target,
        transport_work,
        configuration,
        &result,
        input_request,
        contract,
    )?;
    let mut input_requests = Vec::new();
    if result["status"] == "resolved"
        && let Some(task_request) = request
    {
        let mut packet = vec![task_request.clone()];
        if let Some(verification_request) = verification_request {
            packet.push(verification_request.clone());
        }
        packet.push(handoff_inputs["request"].clone());
        input_requests.push(json!(packet));
    }
    handoff_inputs["requests"] = json!(input_requests);
    handoff_inputs.as_object_mut().unwrap().remove("request");
    let mut execution = crate::native_execution::view(
        target,
        &current_work,
        &result,
        execution_request,
        contract,
        transport_work,
        &handoff_inputs,
        &target_scope,
    )?;
    for question in execution["target_scope_questions"]
        .as_array()
        .into_iter()
        .flatten()
    {
        let name = question["target"].as_str().expect("observed target");
        template["arguments"]["target_scope"][name] = json!({"status":"unresolved","reason":"Current task applicability has not been judged."});
    }
    if let Some(task_request) = request
        && let Some(choices) = execution["requests"].as_array_mut()
    {
        for choice in choices {
            let mut prerequisites = vec![task_request.clone()];
            if let Some(obligation_request) = verification_request {
                prerequisites.push(obligation_request.clone());
            }
            if let Some(input_request) = input_request {
                prerequisites.push(input_request.clone());
            }
            prerequisites.push(choice.clone());
            *choice = json!(prerequisites);
        }
    }
    Ok(
        json!({"status":result["status"],"source_revision":source_revision,"requests":[template],"result":result,"verification_requirements":obligation,
        "execution_configurations":execution,"handoff_inputs":handoff_inputs,"remaining_owner_contracts":["current-native-best-fit-assignment-and-execution"],
        "claim_boundary":"Current task judgment only; no assignment choice, local implementation, launch or proof authority."}),
    )
}
