//! Current-source ingress for acting-agent task requirements. A judgment is not
//! a capability fact, Verification evidence, or durable routing preference.
use crate::{CoreError, digest, direct_task, task_requirements};
use serde_json::{Value, json};

pub(crate) fn contract() -> Result<Value, CoreError> {
    let schema = crate::source_schema();
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
    declarations.push(crate::native_patch::declaration());
    let operation = crate::native_patch::operation();
    let mut contract = json!({"kind":"agentic-workspace/capability-contract/v1","revision":"pending",
        "owners":[{"owner":"assignment","revision":digest(&json!([declarations,operation]))?,"requests":declarations,"operations":[operation],"domains":["assignment"],"effects":[{"id":"implementation","domain":"assignment"}]}],"restriction_authorities":[{"owner":"assignment","affects":crate::native_assignment::IMPLEMENTATION_SCOPES}]});
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
    route_fact: &Value,
    request: Option<&Value>,
    verification_request: Option<&Value>,
    execution_request: Option<&Value>,
    input_request: Option<&Value>,
    contract: &Value,
    baseline: Option<&Value>,
    requested: bool,
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
    let mut required = configuration["assignment_requirements"]["required_execution_guarantees"]
        .as_array()
        .cloned()
        .unwrap_or_default();
    let mut preferred = Vec::new();
    let mut posture = serde_json::Map::new();
    for route in route_fact["routes"]
        .as_array()
        .into_iter()
        .flatten()
        .filter_map(Value::as_str)
    {
        if route_fact["status"] == "current"
            && let Some(value) = configuration["execution_posture"].get(route)
        {
            posture.insert(route.into(), value.clone());
            required.extend(
                value["required_execution_guarantees"]
                    .as_array()
                    .into_iter()
                    .flatten()
                    .cloned(),
            );
            preferred.extend(
                value["preferred_execution_guarantees"]
                    .as_array()
                    .into_iter()
                    .flatten()
                    .cloned(),
            );
        }
    }
    required.sort_by_key(Value::to_string);
    required.dedup();
    preferred.sort_by_key(Value::to_string);
    preferred.dedup();
    let mut policy = configuration["assignment_policy"].clone();
    if let Some(fields) = policy.as_object_mut() {
        fields.remove("source_revision");
    }
    let source_revision = digest(&json!({"task":task_identity,"work":current_work,
        "configuration":policy,"posture":posture,"required_execution_guarantees":required,"verification_strategy":verification["strategy_revision"]}))?;
    let declaration = self::contract()?;
    let owner_revision = &declaration["owners"][0]["revision"];
    let mut template = json!({"kind":"agentic-workspace/public-request/v1","id":"assignment/task-requirements",
        "owner":"assignment","owner_revision":owner_revision,"source_revision":source_revision,
        "capability_revision":contract["revision"],"task_identity":transport_work,
        "request_kind":"assignment/judge-task-requirements/v1","arguments":{
            "task_identity":task_identity,"current_work":current_work,"role":"executor",
            "required_result_classes":[],"required_proof_classes":[],"verification_identity":null}});
    // Profiles are latent capability. Enter comparative/execution construction
    // only for a current opportunity, binding policy or source-shaped executor.
    let relevant = requested
        || configuration["assignment_policy"]["assignment_policy"] != "local-preferred"
        || !required.is_empty()
        || posture.values().any(|p| p["independent_context"] == true)
        || planning_subject.is_some_and(|s| s["state"]["assignment_inputs"].is_object())
        || verification["strategy"]["protocols"]
            .as_object()
            .is_some_and(|p| p.values().any(|v| v["analysis"].is_object()));
    if !relevant {
        return Ok(
            json!({"status":"not-applicable","requests":[],"opportunity_request":template,
            "claim_boundary":"Configured targets remain latent. Submit current task requirements only for a concrete delegation opportunity; no assessment, binding or execution authority is inferred."}),
        );
    }
    #[cfg(test)]
    crate::native_frontier::built("assignment-requirements");
    // Expose source restrictions with the first semantic question. Reading
    // declarations needs no candidate construction or handoff preparation.
    // Configuration already owns failed source admission. This optional
    // question must not turn its recoverable blocker into a transport error.
    let declarations = crate::native_assignment_policy::load(target).ok();
    let scope_questions: Vec<_> = declarations
        .as_ref()
        .map(|source| &source.effective["delegation_targets"])
        .and_then(Value::as_object)
        .into_iter()
        .flatten()
        .filter(|(_, profile)| {
            profile["forbidden_task_classes"]
                .as_array()
                .is_some_and(|classes| !classes.is_empty())
        })
        .map(|(name, profile)| {
            json!({"target":name,"restrictions":profile["forbidden_task_classes"],
                "answer_field":format!("target_scope.{name}"),
                "choices":["applies","not-applicable","unresolved"]})
        })
        .collect();
    let mut source_work = crate::planning::assignment_work(target, planning_subject)?;
    if source_work["status"] == "ready" {
        template["arguments"]["required_result_classes"] =
            json!([source_work["definition"]["result_class"]]);
        template["arguments"]["required_proof_classes"] =
            source_work["definition"]["required_proof_classes"].clone();
    }
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
    let mut judgment = request.map(|r| r["arguments"].clone()).unwrap_or_else(|| {
        if source_work["status"] == "ready" {
            template["arguments"].clone()
        } else {
            Value::Null
        }
    });
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
    if judgment["role"] == "evaluator"
        || selected_request.is_some()
        || (request.is_none()
            && verification["strategy"]["protocols"]
                .as_object()
                .is_some_and(|p| p.values().any(|v| v["analysis"].is_object())))
    {
        obligation = crate::verification_requirements::resolve(
            json!({"target":target,"task":task,"changed_paths":changed,
            "current_work":current_work,"role":judgment["role"].as_str().or_else(|| selected_request.and_then(|r|r["arguments"]["role"].as_str())).unwrap_or("executor"),"request":selected_request}),
            Some(transport_work),
            Some(contract),
        )?;
        if obligation["source_work"].is_object() {
            source_work = obligation["source_work"].clone();
            template["arguments"]["required_result_classes"] = json!(["read-only"]);
            template["arguments"]["required_proof_classes"] = json!([]);
            template["arguments"]["verification_identity"] = json!({"id":obligation["verification"]["id"],"revision":obligation["verification"]["revision"]});
            if request.is_none() && source_work["status"] == "ready" {
                judgment = template["arguments"].clone();
            }
            if !judgment.is_null()
                && (judgment["role"] != "executor"
                    || judgment["required_result_classes"] != json!(["read-only"])
                    || judgment["required_proof_classes"] != json!([]))
            {
                return Err(CoreError::new(
                    "Verification investigation permits read-only analysis only; commands and repair use their existing separately scoped owner paths.",
                ));
            }
        }
        if !obligation["verification"].is_null()
            && judgment["verification_identity"].is_null()
            && !judgment.is_null()
        {
            judgment["verification_identity"] = json!({"id":obligation["verification"]["id"],"revision":obligation["verification"]["revision"]});
        }
    }
    let mut result = task_requirements::view(
        json!({"kind":"agentic-workspace/task-requirements-input/v1",
        "task_identity":task_identity,"current_work":current_work,
        "judgment":judgment,"verification":obligation["verification"],
        "required_execution_guarantees":required}),
    )?;
    if source_work["status"] == "shaping-required" {
        result["status"] = json!("unresolved");
        result["gaps"]
            .as_array_mut()
            .unwrap()
            .push(json!("selected-bounded-work-requires-shaping"));
        result["revision"] = json!(digest(&json!([result, source_work]))?);
    }
    if !posture.is_empty() {
        if result["status"] == "resolved"
            && posture.values().any(|p| p["independent_context"] == true)
        {
            result["requirements"]["independent_context"] = json!(true);
        }
        result["execution_posture"] =
            json!({"classes":posture,"preferred_execution_guarantees":preferred});
        result["revision"] = json!(digest(&result)?);
    }
    let mut handoff_inputs = crate::native_handoff::inputs_view(
        target,
        transport_work,
        configuration,
        &result,
        input_request,
        contract,
        baseline,
        source_work.get("definition"),
    )
    .map_err(|error| {
        error.dispatch_mismatch(crate::native_delegation::DispatchMismatch::AssignmentHandoff)
    })?;
    let mut input_requests = Vec::new();
    if result["status"] == "resolved" {
        let mut packet = vec![request.cloned().unwrap_or_else(|| template.clone())];
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
    )
    .map_err(|error| {
        error.dispatch_mismatch(crate::native_delegation::DispatchMismatch::ExecutionConfiguration)
    })?;
    for question in execution["target_scope_questions"]
        .as_array()
        .into_iter()
        .flatten()
    {
        let name = question["target"].as_str().expect("observed target");
        template["arguments"]["target_scope"][name] = json!({"status":"unresolved","reason":"Current task applicability has not been judged."});
    }
    if result["status"] == "resolved"
        && let Some(choices) = execution["requests"].as_array_mut()
    {
        for choice in choices {
            let mut prerequisites = vec![request.cloned().unwrap_or_else(|| template.clone())];
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
        json!({"status":result["status"],"source_revision":source_revision,"requests":[template],"result":result,"target_scope_questions":scope_questions,"verification_requirements":obligation,"source_work":source_work,
        "execution_configurations":execution,"handoff_inputs":handoff_inputs,"remaining_owner_contracts":["current-native-best-fit-assignment-and-execution"],
        "claim_boundary":"Current task judgment only; no assignment choice, local implementation, launch or proof authority."}),
    )
}
