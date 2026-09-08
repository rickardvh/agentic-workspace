//! Public native ingress. Callers express work and public requests; repository
//! facts and owner admission are derived here, never accepted as debug inputs.
use crate::{
    CoreError, compile_value, decision_source, digest, native_config, native_instructions,
    native_memory, native_planning, native_requirements, native_routes, native_verification,
    planning,
};
use serde::Deserialize;
use serde_json::{Value, json};
use std::path::PathBuf;

#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct Input {
    target: String,
    #[serde(default)]
    task: String,
    #[serde(default)]
    changed: Vec<String>,
    request: Option<Value>,
    invocation: Option<Value>,
}

fn input(value: Value) -> Result<(Input, PathBuf), CoreError> {
    let mut input: Input =
        serde_json::from_value(value).map_err(|e| CoreError::new(e.to_string()))?;
    for path in &input.changed {
        decision_source::relative(path)?;
    }
    input.changed.sort();
    input.changed.dedup();
    let target = std::fs::canonicalize(&input.target).map_err(|e| CoreError::new(e.to_string()))?;
    if !target.is_dir() {
        return Err(CoreError::new("target must be an existing directory"));
    }
    Ok((input, target))
}

pub fn start(value: Value) -> Result<Value, CoreError> {
    let (input, target) = input(value)?;
    if input.invocation.is_some() {
        return Err(CoreError::new(
            "start accepts a public request, not an invocation",
        ));
    }
    resolve(&input, &target, false)
}

fn resolve(input: &Input, target: &std::path::Path, executing: bool) -> Result<Value, CoreError> {
    let compatibility = crate::runtime_compatibility::native(target)?;
    if compatibility["status"] == "blocked" {
        return Ok(compatibility);
    }
    let work = json!({"kind":"current-work", "id":digest(&json!({
        "target":target, "task":input.task, "changed":input.changed
    }))?});
    let requests = owner_requests(input.request.as_ref())?;
    let request_for = |owner: &str| requests.iter().find(|request| request["owner"] == owner);
    let planning_request = requests
        .iter()
        .find(|r| r["owner"] == "planning" && r["request_kind"] == "planning/continuation/v1")
        .or_else(|| {
            input
                .invocation
                .as_ref()
                .filter(|i| i["operation_id"] == "planning.create")
                .and_then(|i| i["arguments"].get("planning_request"))
                .filter(|r| r.is_object())
        });
    let creation_request = requests
        .iter()
        .find(|r| r["owner"] == "planning" && r["request_kind"] == "planning/create/v1");
    let verification_request = |kind: &str| {
        requests
            .iter()
            .find(|request| request["owner"] == "verification" && request["request_kind"] == kind)
    };
    let (route_source, former_routes) =
        native_routes::former_selection(target, &native_routes::source(target)?)?;
    let route_input = json!({
        "current_work":work, "source":route_source,
        "request":request_for("semantic-routes")
    });
    let configuration = native_config::view(target)?;
    let available = |owner: &str| native_config::module_enabled(&configuration, owner);
    for request in &requests {
        if matches!(
            request["owner"].as_str(),
            Some("planning" | "memory" | "verification")
        ) && !available(request["owner"].as_str().unwrap())
        {
            return Err(CoreError::new(
                "requested owner is disabled by current module enablement",
            ));
        }
    }
    if input.invocation.as_ref().is_some_and(|invocation| {
        invocation["source_owner"].as_str().is_some_and(|owner| {
            matches!(owner, "planning" | "memory" | "verification") && !available(owner)
        })
    }) {
        return Err(CoreError::new(
            "invoked owner is disabled by current module enablement",
        ));
    }
    let mut system_intent = crate::native_intent::view(target, &work, &configuration, None, None)?;
    let admissions = &configuration["admissions"];
    let (mut owner_input, mut routes) = decision_source::resolve(json!({
        "target":target,
        "archive":admissions["decision_record_target"].as_str().unwrap_or(""),
        "admitted_revision":admissions["decision_record_revision"].as_str().unwrap_or(""),
        "applicable_scope":input.changed.iter().map(|path| format!("path:{path}")).collect::<Vec<_>>(),
        "semantic_routes":route_input
    }))?;
    if let (Some(view), Some(mut candidate)) = (routes.as_mut(), former_routes) {
        if candidate["status"] == "candidate" {
            let mut request = view["requests"]
                .as_array()
                .unwrap()
                .iter()
                .find(|request| request["request_kind"] == "semantic-routes/select/v1")
                .unwrap()
                .clone();
            request["arguments"] =
                json!({"posture":candidate["posture"],"routes":candidate["routes"]});
            candidate["selection_request"] = request;
        }
        view["former_selection"] = candidate;
    }
    let route_fact = routes
        .as_ref()
        .map(|value| value["decision"]["semantic_task_routes"].clone())
        .unwrap_or(Value::Null);
    let mut instructions = native_instructions::resolve(
        target,
        &input.changed,
        &route_fact,
        admissions["instruction_revision"].as_str().unwrap_or(""),
    )?;
    let mut memory = if available("memory") {
        native_memory::public_view(target, &input.changed, &route_fact, &work, None, None)?
    } else {
        native_memory::disabled(target)?
    };
    let planning_probe = if available("planning") {
        native_planning::resolve(target, &work, None)?
    } else {
        native_planning::disabled(target)?
    };
    let verification_probe = if available("verification") {
        native_verification::view(target, &input.task, &input.changed, &work, None, None)?
    } else {
        native_verification::disabled(target)?
    };
    let contract = combined_contract(&[
        &configuration["capability_contract"],
        &system_intent["capability_contract"],
        &planning_probe["capability_contract"],
        &verification_probe["capability_contract"],
        &instructions["capability_contract"],
        &memory["capability_contract"],
        &native_requirements::contract()?,
    ])?;
    if let Some(request) = request_for("system-intent") {
        system_intent = crate::native_intent::view(
            target,
            &work,
            &configuration,
            Some(request),
            Some(&contract),
        )?;
    } else {
        for request in system_intent["requests"].as_array_mut().unwrap() {
            request["capability_revision"] = contract["revision"].clone();
        }
    }
    if let Some(request) = request_for("memory") {
        memory = native_memory::public_view(
            target,
            &input.changed,
            &route_fact,
            &work,
            Some(request),
            Some(&contract),
        )?;
    } else {
        for request in memory["requests"].as_array_mut().unwrap() {
            request["capability_revision"] = contract["revision"].clone();
        }
    }
    let mut planning = if executing
        && input
            .invocation
            .as_ref()
            .is_some_and(|i| i["operation_id"] == "planning.reconcile")
    {
        native_planning::resolve_for_execution(target, &work, &contract)?
    } else if planning_request.is_some() {
        native_planning::resolve_with_contract(target, &work, planning_request, Some(&contract))?
    } else {
        planning_probe
    };
    let mut contributions = vec![configuration["contribution"].clone()];
    let mut planning_detail = Value::Null;
    if !planning["planning_input"].is_null() {
        let mut context = planning["planning_input"].clone();
        context["capability_contract"] = contract.clone();
        let (owner_input, detail) = planning::compose_input(context)?;
        contributions.extend(
            owner_input["contributions"]
                .as_array()
                .into_iter()
                .flatten()
                .cloned(),
        );
        planning_detail = detail;
    } else {
        contributions.push(planning["contribution"].clone());
    }
    let mut creation = crate::native_planning_create::view(
        target,
        &work,
        &contract,
        creation_request,
        input
            .invocation
            .as_ref()
            .filter(|i| i["operation_id"] == "planning.create"),
    )?;
    if let Some(actions) = creation["contribution"]["actions"].as_array_mut() {
        for action in actions {
            action["arguments"]["planning_request"] =
                planning_request.cloned().unwrap_or(Value::Null);
        }
    }
    planning["created_owner"] = creation["created_owner"].clone();
    if let Some(reference) = creation["created_owner"]["path"].as_str() {
        let candidate = native_planning::candidate(target, &work, reference, &contract);
        match candidate {
            Ok(candidate) => {
                planning["created_owner"]["selection_request"] = candidate["requests"][0].clone()
            }
            Err(error) => planning["created_owner"]["selection_gap"] = json!(error.to_string()),
        }
    }
    planning["creation_requests"] = creation["requests"].clone();
    planning["creation_committed_operation"] = creation["committed_operation"].clone();
    if let Some(actions) = creation["contribution"]["actions"].as_array() {
        let owner = contributions
            .iter_mut()
            .find(|c| c["owner"] == "planning")
            .unwrap();
        let mut combined = owner["actions"].as_array().cloned().unwrap_or_default();
        combined.extend(actions.iter().cloned());
        owner["actions"] = json!(combined);
        owner["settled"] = json!(false);
        owner["revision"] = json!(digest(&json!([
            owner["revision"],
            creation["contribution"]["revision"]
        ]))?);
    }
    let subject = planning_detail
        .get("reconciliation")
        .and_then(|value| value.get("subject"));
    let verification = if available("verification") {
        native_verification::view_with_applicability(
            target,
            &input.task,
            &input.changed,
            &work,
            subject,
            Some(json!(
                requests
                    .iter()
                    .filter(|r| r["owner"] == "verification"
                        && matches!(
                            r["request_kind"].as_str(),
                            Some(
                                "verification/claim/v1"
                                    | "verification/authenticate-host-review/v1"
                                    | "verification/execute-selected/v1"
                                    | "verification/record-receipt/v1"
                            )
                        ))
                    .cloned()
                    .collect::<Vec<_>>()
            )),
            native_verification::ApplicabilityContext {
                facts: &json!({"route_fact":route_fact,"planning":{"status":planning["status"],"source_revision":planning["source_revision"]}}),
                request: verification_request("verification/assurance-applicability/v1").cloned(),
                contract: Some(&contract),
                invocation: input
                    .invocation
                    .as_ref()
                    .filter(|i| i["operation_id"] == "proof.report"),
            },
        )?
    } else {
        verification_probe
    };
    contributions.push(verification["contribution"].clone());
    let requirements = native_requirements::view(
        target,
        &input.task,
        &input.changed,
        &work,
        subject,
        &configuration,
        &verification,
        request_for("assignment"),
        verification_request("verification/requirements/v1"),
        &contract,
    )?;
    contributions.push(system_intent["contribution"].clone());
    contributions.push(memory["contribution"].clone());
    contributions.push(instructions["contribution"].clone());
    owner_input["contributions"] = json!(contributions);
    owner_input["capability_contract"] = contract.clone();
    if instructions["sources"]
        .as_array()
        .into_iter()
        .flatten()
        .any(|source| source["binding_admission"]["status"] != "not-required")
        && owner_input["contributions"]
            .as_array()
            .into_iter()
            .flatten()
            .any(|owner| {
                owner["actions"]
                    .as_array()
                    .is_some_and(|actions| !actions.is_empty())
            })
    {
        let prepared = compile_value(owner_input.clone())?;
        native_instructions::restrict_pending(
            &mut instructions,
            prepared["pending_consequences"]["actions"]
                .as_array()
                .map(Vec::as_slice)
                .unwrap_or(&[]),
            &route_fact,
        )?;
        *owner_input["contributions"]
            .as_array_mut()
            .unwrap()
            .last_mut()
            .unwrap() = instructions["contribution"].clone();
    }
    let decision = compile_value(owner_input)?;
    planning.as_object_mut().unwrap().remove("planning_input");
    planning["current_owner"] = planning_detail;
    Ok(
        json!({"runtime_compatibility":compatibility,"decision_packet":decision, "capability_contract":contract, "current_work":work, "semantic_routes":routes, "configuration":configuration,"system_intent":system_intent, "instructions":instructions,"memory":memory,"planning":planning, "verification":verification,"task_requirements":requirements}),
    )
}

fn owner_requests(request: Option<&Value>) -> Result<Vec<Value>, CoreError> {
    let Some(request) = request else {
        return Ok(vec![]);
    };
    let declaration: Value = serde_json::from_str(include_str!(
        "../../../src/agentic_workspace/contracts/schemas/source_decision_input.schema.json"
    ))
    .expect("checked schema");
    let schema = json!({"$schema":declaration["$schema"], "$defs":declaration["$defs"], "$ref":"#/$defs/public_request_set"});
    crate::schema_validator(&schema, "native public requests")?
        .validate(request)
        .map_err(|e| CoreError::new(e.to_string()))?;
    let requests = request
        .as_array()
        .cloned()
        .unwrap_or_else(|| vec![request.clone()]);
    let mut owners = std::collections::BTreeSet::new();
    for request in &requests {
        let owner = request["owner"].as_str().unwrap();
        if owner == "verification"
            && !matches!(
                request["request_kind"].as_str(),
                Some(
                    "verification/claim/v1"
                        | "verification/execute-selected/v1"
                        | "verification/record-receipt/v1"
                        | "verification/requirements/v1"
                        | "verification/authenticate-host-review/v1"
                        | "verification/assurance-applicability/v1"
                )
            )
        {
            return Err(CoreError::new(
                "requested Verification request kind is not available",
            ));
        }
        if !matches!(
            owner,
            "planning"
                | "semantic-routes"
                | "verification"
                | "memory"
                | "assignment"
                | "system-intent"
        ) {
            return Err(CoreError::new("requested native owner is not available"));
        }
        let key = if matches!(owner, "verification" | "planning") {
            format!("{owner}:{}", request["request_kind"].as_str().unwrap())
        } else {
            owner.to_owned()
        };
        if !owners.insert(key) {
            return Err(CoreError::new(
                "supply at most one current request per owner and Verification request kind",
            ));
        }
    }
    Ok(requests)
}

fn combined_contract(contracts: &[&Value]) -> Result<Value, CoreError> {
    let mut combined =
        json!({"kind":"agentic-workspace/capability-contract/v1", "revision":"pending"});
    for field in ["owners", "claim_authorities", "restriction_authorities"] {
        let mut entries = Vec::new();
        for contract in contracts {
            for entry in contract[field].as_array().into_iter().flatten() {
                if !entries.contains(entry) {
                    entries.push(entry.clone());
                }
            }
        }
        combined[field] = json!(entries);
    }
    combined["revision"] = json!(digest(&combined)?);
    Ok(combined)
}

pub fn invoke(value: Value) -> Result<Value, CoreError> {
    let (input, target) = input(value)?;
    if input.request.is_some() || input.invocation.is_none() {
        return Err(CoreError::new(
            "invoke requires exactly an operation invocation",
        ));
    }
    let invocation = input.invocation.as_ref().unwrap();
    if invocation["operation_id"] != "planning.reconcile"
        && invocation["operation_id"] != "proof.report"
        && invocation["operation_id"] != "planning.create"
    {
        return Err(CoreError::new(
            "requested native operation is not available",
        ));
    }
    let current = resolve(&input, &target, true)?;
    if current["status"] == "blocked" {
        return Ok(current);
    }
    if invocation["operation_id"] == "planning.create" {
        let committed = &current["planning"]["creation_committed_operation"];
        crate::admit_invocation_value(
            json!({"decision":current["decision_packet"],"invocation":invocation,"previous_invocation":committed.get("invocation")}),
        )?;
        let executed = if committed.is_object() {
            let mut result = committed["outcome"].clone();
            result["custody"] = committed["custody"].clone();
            result
        } else {
            crate::native_planning_create::execute(
                &target,
                &current["decision_packet"],
                invocation,
                || {
                    let fresh = resolve(&input, &target, true)?;
                    crate::admit_invocation_value(
                        json!({"decision":fresh["decision_packet"],"invocation":invocation}),
                    )?;
                    Ok(())
                },
            )?
        };
        let next = resolve(&input, &target, false).ok();
        let mut result = crate::operation_result_value(
            json!({"invocation":invocation,"outcome":{"status":executed["status"],"effects":executed["effects"],"value":executed["value"]},"decision":next.as_ref().map(|v|&v["decision_packet"])}),
        )?;
        result["custody"] = executed["custody"].clone();
        // Reuse the post-result owner projection instead of another source read.
        if let Some(next) = next {
            for key in ["selection_request", "selection_gap"] {
                if let Some(value) = next["planning"]["created_owner"].get(key) {
                    result["value"][key] = value.clone();
                }
            }
        } else {
            result["value"]["selection_gap"] = json!(
                "Post-creation owner resolution unavailable; fresh current entry is required"
            );
        }
        return Ok(result);
    }
    if invocation["operation_id"] == "proof.report" {
        crate::admit_invocation_value(
            json!({"decision":current["decision_packet"],"invocation":invocation}),
        )?;
        let executed = crate::native_proof::execute(&target, &current, invocation, || {
            let fresh = resolve(&input, &target, true)?;
            crate::admit_invocation_value(
                json!({"decision":fresh["decision_packet"],"invocation":invocation}),
            )?;
            Ok(())
        })?;
        let next = resolve(&input, &target, false).ok();
        let mut result = crate::operation_result_value(
            json!({"invocation":invocation,"outcome":{"status":executed["status"],"effects":executed["effects"],"value":executed["value"]},"decision":next.as_ref().map(|view| &view["decision_packet"])}),
        )?;
        result["custody"] = executed["custody"].clone();
        return Ok(result);
    }
    let committed = &current["planning"]["current_owner"]["committed_operation"];
    crate::admit_invocation_value(
        json!({"decision":current["decision_packet"], "invocation":invocation,
            "previous_invocation":committed.get("invocation")}),
    )?;
    let executed = if committed.is_object() {
        let mut result = committed["outcome"].clone();
        result["custody"] = committed["custody"].clone();
        result
    } else {
        native_planning::execute_revalidating(
            &target,
            &current["current_work"],
            invocation,
            &current["capability_contract"],
            || {
                let fresh = resolve(&input, &target, true)?;
                crate::admit_invocation_value(json!({
                    "decision":fresh["decision_packet"], "invocation":invocation
                }))?;
                Ok(())
            },
        )?
    };
    let next = resolve(&input, &target, false).ok();
    let mut result = crate::operation_result_value(json!({"invocation":invocation,
        "outcome":{"status":executed["status"], "effects":executed["effects"], "value":executed["value"]},
        "decision":next.as_ref().map(|view| &view["decision_packet"])}))?;
    result["custody"] = executed["custody"].clone();
    Ok(result)
}
