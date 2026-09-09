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
    let requests = owner_requests(if executing {
        input
            .invocation
            .as_ref()
            .and_then(|invocation| invocation.get("source_requests"))
    } else {
        input.request.as_ref()
    })?;
    if executing
        && input.invocation.as_ref().is_none_or(|i| {
            i["operation_id"] != "delegation.dispatch"
                && i["operation_id"] != "configuration.write"
                && i["operation_id"] != "configuration.recover-write"
                && !(i["operation_id"] == "planning.update"
                    && i["arguments"]["consumed_return"].is_object())
        })
        && requests.iter().any(|request| {
            !(request["owner"] == "startup-adapter"
                && request["request_kind"] == "startup-adapter/read-current-source/v1"
                || input
                    .invocation
                    .as_ref()
                    .is_some_and(|i| i["operation_id"] == "proof.report")
                    && request["owner"] == "planning"
                    && request["request_kind"] == "planning/continuation/v1")
        })
    {
        return Err(CoreError::new(
            "unsupported operation source request dependency",
        ));
    }
    let request_for = |owner: &str| requests.iter().find(|request| request["owner"] == owner);
    let planning_request = requests
        .iter()
        .find(|r| r["owner"] == "planning" && r["request_kind"] == "planning/continuation/v1")
        .or_else(|| {
            input
                .invocation
                .as_ref()
                .filter(|i| {
                    matches!(
                        i["operation_id"].as_str(),
                        Some("planning.create" | "planning.update-recover")
                    )
                })
                .and_then(|i| i["arguments"].get("planning_request"))
                .filter(|r| r.is_object())
        });
    let creation_request = requests
        .iter()
        .find(|r| r["owner"] == "planning" && r["request_kind"] == "planning/create/v1");
    let update_request = requests.iter().find(|r| {
        r["owner"] == "planning"
            && matches!(
                r["request_kind"].as_str(),
                Some(
                    crate::native_planning_update::KIND
                        | crate::native_planning_update::RECOVER_KIND
                )
            )
    });
    let verification_request = |kind: &str| {
        requests
            .iter()
            .find(|request| request["owner"] == "verification" && request["request_kind"] == kind)
    };
    let route_catalogue = native_routes::source(target)?;
    let (route_source, former_routes) = native_routes::former_selection(target, &route_catalogue)?;
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
    let config_write_contract = crate::native_config_write::contract()?;
    let mut startup_adapter =
        crate::native_startup::view(target, &work, &configuration, None, None)?;
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
    if let Some(view) = routes.as_mut()
        && view["status"] == "current"
        && let Some(parent) = view["discovery"]["parent"].as_str()
        && route_catalogue["routes"]
            .as_array()
            .is_some_and(|leaves| leaves.iter().any(|leaf| leaf == parent))
    {
        // The existing branch request also drills into a declared leaf. Only
        // this explicit query loads procedure references; applicability and
        // external mutation authority remain with their existing owners.
        let detail = native_routes::discovery(json!({"target":target,"exact":parent}))?;
        if detail["source_revision"] != route_catalogue["revision"]
            || native_routes::former_selection(target, &native_routes::source(target)?)?.0
                != route_source
        {
            return Err(CoreError::new(
                "route sources changed during leaf discovery",
            ));
        }
        view["discovery"]["detail"] = detail["routes"][0].clone();
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
    crate::native_startup::restrict_operations(
        &mut startup_adapter,
        &[
            &config_write_contract,
            &planning_probe["capability_contract"],
            &verification_probe["capability_contract"],
            &memory["capability_contract"],
            &instructions["capability_contract"],
        ],
    )?;
    let decision_read_contract = decision_source::read_contract()?;
    let contract = combined_contract(&[
        &config_write_contract,
        &decision_read_contract,
        &configuration["capability_contract"],
        &system_intent["capability_contract"],
        &startup_adapter["capability_contract"],
        &planning_probe["capability_contract"],
        &verification_probe["capability_contract"],
        &instructions["capability_contract"],
        &memory["capability_contract"],
        &native_requirements::contract()?,
        &crate::native_delegation::contract()?,
    ])?;
    if let Some(request) = request_for("startup-adapter") {
        startup_adapter = crate::native_startup::view(
            target,
            &work,
            &configuration,
            Some(request),
            Some(&contract),
        )?;
    } else {
        for request in startup_adapter["requests"].as_array_mut().unwrap() {
            request["capability_revision"] = contract["revision"].clone();
        }
    }
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
        native_planning::resolve_for_invocation(
            target,
            &work,
            &contract,
            input.invocation.as_ref().unwrap(),
        )?
    } else if planning_request.is_some() {
        native_planning::resolve_with_contract(target, &work, planning_request, Some(&contract))?
    } else {
        planning_probe
    };
    for request in planning["requests"].as_array_mut().into_iter().flatten() {
        request["capability_revision"] = contract["revision"].clone();
    }
    if let Some(request) = planning["selector_transfer"].get_mut("request") {
        request["capability_revision"] = contract["revision"].clone();
    }
    let config_write = crate::native_config_write::view(
        target,
        &work,
        &configuration,
        &contract,
        request_for("configuration"),
    )?;
    let mut contributions = vec![
        configuration["contribution"].clone(),
        config_write["contribution"].clone(),
    ];
    let mut planning_detail = Value::Null;
    if !planning["planning_input"].is_null() {
        let mut context = planning["planning_input"].clone();
        context["capability_contract"] = contract.clone();
        if startup_adapter["status"] == "source-context-delivered" {
            context["source_requests"] =
                json!([request_for("startup-adapter").expect("explicit current source request")]);
        }
        let (owner_input, detail) = if planning["status"] == "reentry-required" {
            planning::reentry_input(context)?
        } else {
            planning::compose_input(context)?
        };
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
    let update = crate::native_planning_update::view(
        target,
        &work,
        &contract,
        &planning,
        update_request,
        input.invocation.as_ref().filter(|i| {
            executing
                && matches!(
                    i["operation_id"].as_str(),
                    Some("planning.update" | "planning.update-recover")
                )
        }),
        planning_request,
    )?;
    planning["update_requests"] = update["requests"].clone();
    planning["update_retained"] = update["retained"].clone();
    planning["consumed_result"] = update["consumed_result"].clone();
    planning["pending_update"] = update["pending"].clone();
    planning["update_recovery_requests"] = update["recovery_requests"].clone();
    if update["pending"].is_object() {
        let owner = contributions
            .iter_mut()
            .find(|c| c["owner"] == "planning")
            .unwrap();
        owner["blockers"] = json!([{"code":"planning-update-pending","message":"The exact native update postimage is retained but its outcome remains uncertain. Resume only the returned invocation against current authority.","affects":["task"]}]);
        owner["settled"] = json!(false);
    }
    if update["action"].is_object()
        && !input.invocation.as_ref().is_some_and(|i| {
            executing
                && i["operation_id"] == "planning.update"
                && i["arguments"]["consumed_return"].is_object()
        })
    {
        let owner = contributions
            .iter_mut()
            .find(|c| c["owner"] == "planning")
            .unwrap();
        // The explicit exact owner update resolves only Planning's own reentry
        // decision. Independent source/safety/Verification restrictions survive.
        owner["actions"] = json!([update["action"]]);
        owner["decisions"] = json!([]);
        owner["blockers"] = json!([]);
        owner["settled"] = json!(false);
        owner["revision"] = json!(digest(&json!([owner["revision"], update["action"]]))?);
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
    let mut artifact_profile = configuration["artifact_profile"].clone();
    if artifact_profile["status"] != "absent" {
        artifact_profile["current_owner"] = json!({"status":planning["status"],"selected_owner":{"id":planning["selected_owner"]["id"],"ref":planning["selected_owner"]["ref"]},"source_revision":planning["source_revision"],"custody_status":planning["custody_status"],"subject":{"id":planning_detail["reconciliation"]["subject"]["id"],"revision":planning_detail["reconciliation"]["subject"]["revision"]},"current":planning_detail["current"]});
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
                                    | "verification/strategy/v1"
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
    let mut requirements = native_requirements::view(
        target,
        &input.task,
        &input.changed,
        &work,
        subject,
        &configuration,
        &verification,
        requests.iter().find(|r| {
            r["owner"] == "assignment"
                && r["request_kind"] == "assignment/judge-task-requirements/v1"
        }),
        verification_request("verification/requirements/v1"),
        requests.iter().find(|r| {
            r["owner"] == "assignment"
                && r["request_kind"] == "assignment/select-execution-configuration/v1"
        }),
        requests
            .iter()
            .find(|r| r["request_kind"] == "assignment/judge-readonly-inputs/v1"),
        &contract,
    )?;
    contributions.push(startup_adapter["contribution"].clone());
    requirements["bounded_outcome_evidence"] =
        if configuration["assignment_requirements"]["configured"] == true {
            crate::native_assignment::outcome_evidence(&input.task, &planning, &verification)?
        } else {
            json!([])
        };
    let mut assignment = crate::native_assignment::view(
        &work,
        &configuration,
        &requirements,
        requests.iter().find(|r| {
            r["owner"] == "assignment" && r["request_kind"] == "assignment/assess-best-fit/v1"
        }),
        &requests,
        &contract,
    )?;
    *contributions
        .iter_mut()
        .find(|c| c["owner"] == "workspace")
        .expect("configuration contribution") = native_config::assignment_consumption(
        &configuration,
        &assignment["result"],
        &requirements["execution_configurations"],
    );
    let mut assignment_contribution = assignment["contribution"].clone();
    assignment.as_object_mut().unwrap().remove("contribution");
    requirements["assignment"] = assignment;
    let handoff = crate::native_handoff::view(
        target,
        &input.task,
        &input.changed,
        &work,
        &requirements,
        &requests,
        &contract,
    )?;
    let mut delegation = crate::native_delegation::view(
        target,
        &work,
        &requirements,
        &handoff,
        &requests,
        &contract,
    )?;
    if !delegation["observed_invocation"].is_null() {
        let original = delegation["observed_invocation"].clone();
        let original_input = Input {
            target: input.target.clone(),
            task: input.task.clone(),
            changed: input.changed.clone(),
            request: None,
            invocation: Some(original.clone()),
        };
        let fresh = resolve(&original_input, target, true)?;
        crate::admit_invocation_value(
            json!({"decision":fresh["decision_packet"],"invocation":original}),
        )?;
    }
    delegation
        .as_object_mut()
        .unwrap()
        .remove("observed_invocation");
    let admission =
        crate::native_handoff::admission(&work, &delegation["observation"], &requests, &contract)?;
    if admission["result_use_allowed"] == true {
        assignment_contribution["blockers"]
            .as_array_mut()
            .unwrap()
            .retain(|b| b["code"] != "current-nonlocal-assignment-handoff-required");
        assignment_contribution["revision"] = json!(digest(&json!([
            assignment_contribution["revision"],
            admission["source_revision"],
            admission["judgment"]
        ]))?);
    }
    contributions.push(assignment_contribution);
    let adopted = crate::native_planning_update::adopt_return(
        target, &work, &contract, &planning, &admission, &requests,
    )?;
    planning["adoption_requests"] = adopted["requests"].clone();
    if adopted["action"].is_object() {
        let owner = contributions
            .iter_mut()
            .find(|c| c["owner"] == "planning")
            .ok_or_else(|| CoreError::new("Planning owner unavailable for result adoption"))?;
        owner["actions"] = json!([adopted["action"]]);
        owner["decisions"] = json!([]);
        owner["blockers"] = json!([]);
        owner["settled"] = json!(false);
        owner["revision"] = json!(digest(&json!([owner["revision"], adopted["action"]]))?);
    }
    requirements["assignment"]["result_admission"] = admission;
    contributions.push(delegation["contribution"].clone());
    delegation.as_object_mut().unwrap().remove("contribution");
    requirements["delegation"] = delegation;
    requirements["handoff"] = handoff;
    contributions.push(system_intent["contribution"].clone());
    contributions.push(memory["contribution"].clone());
    contributions.push(instructions["contribution"].clone());
    owner_input["contributions"] = json!(contributions);
    owner_input["capability_contract"] = contract.clone();
    if let Some(continuation) = planning_request {
        for owner in owner_input["contributions"].as_array_mut().unwrap() {
            for action in owner
                .get_mut("actions")
                .and_then(Value::as_array_mut)
                .into_iter()
                .flatten()
            {
                if matches!(
                    action["operation_id"].as_str(),
                    Some("proof.report" | "configuration.write" | "configuration.recover-write")
                ) {
                    let mut dependencies = action["source_requests"]
                        .as_array()
                        .cloned()
                        .unwrap_or_default();
                    if !dependencies.contains(continuation) {
                        dependencies.push(continuation.clone());
                    }
                    action["source_requests"] = json!(dependencies);
                }
            }
        }
    }
    if startup_adapter["status"] == "source-context-delivered" {
        let source_request =
            request_for("startup-adapter").expect("delivery requires explicit request");
        owner_input["intent"]["current_work"] = work.clone();
        for contribution in owner_input["contributions"].as_array_mut().unwrap() {
            for action in contribution
                .get_mut("actions")
                .and_then(Value::as_array_mut)
                .into_iter()
                .flatten()
            {
                if action["effects"]
                    .as_array()
                    .is_some_and(|effects| !effects.is_empty())
                {
                    let mut dependencies = action["source_requests"]
                        .as_array()
                        .cloned()
                        .unwrap_or_default();
                    if !dependencies.contains(source_request) {
                        dependencies.push(source_request.clone());
                    }
                    action["source_requests"] = json!(dependencies);
                }
            }
        }
    }
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
    let decision_context = owner_input["decision_context"].clone();
    let decision = compile_value(owner_input)?;
    let decision_sources = decision_source::public_read(
        target,
        &decision_context,
        &decision,
        &work,
        &contract,
        request_for("decision-continuity"),
    )?;
    planning.as_object_mut().unwrap().remove("planning_input");
    planning["current_owner"] = planning_detail;
    let mut public = json!({"runtime_compatibility":compatibility,"decision_sources":decision_sources,"decision_packet":decision, "capability_contract":contract, "current_work":work, "semantic_routes":routes, "configuration":configuration,"configuration_write":config_write,"system_intent":system_intent,"startup_adapter":startup_adapter,"workflow_artifact_profile":artifact_profile, "instructions":instructions,"memory":memory,"planning":planning, "verification":verification,"task_requirements":requirements});
    // Requests bind the composed contract above. Owner-local fragments remain
    // internal composition inputs, not additional public authorities.
    for owner in public.as_object_mut().unwrap().values_mut() {
        if let Some(object) = owner.as_object_mut() {
            object.remove("capability_contract");
            object.remove("contribution");
        }
    }
    // Keep the full current source requirement once, in applicability detail.
    // Evidence gaps identify that same row without copying its source body.
    if let Some(gaps) = public["verification"]["assurance_owner_gaps"].as_array_mut() {
        for gap in gaps {
            if let Some(object) = gap.as_object_mut() {
                object.remove("source_requirement");
            }
        }
    }
    Ok(public)
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
                        | "verification/strategy/v1"
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
                | "configuration"
                | "semantic-routes"
                | "verification"
                | "memory"
                | "assignment"
                | "system-intent"
                | "startup-adapter"
                | "decision-continuity"
                | "delegation"
        ) {
            return Err(CoreError::new("requested native owner is not available"));
        }
        if owner == "delegation"
            && !matches!(
                request["request_kind"].as_str(),
                Some("delegation/dispatch/v1" | "delegation/read-result/v1")
            )
        {
            return Err(CoreError::new(
                "requested Delegation request kind is not available",
            ));
        }
        if owner == "assignment"
            && !matches!(
                request["request_kind"].as_str(),
                Some(
                    "assignment/judge-task-requirements/v1"
                        | "assignment/select-execution-configuration/v1"
                        | "assignment/assess-best-fit/v1"
                        | "assignment/judge-readonly-inputs/v1"
                        | "assignment/export-readonly/v1"
                        | "assignment/observe-readonly-return/v1"
                        | "assignment/judge-return/v1"
                )
            )
        {
            return Err(CoreError::new(
                "requested Assignment request kind is not available",
            ));
        }
        let key = if matches!(owner, "verification" | "planning" | "assignment") {
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
        && invocation["operation_id"] != "planning.update"
        && invocation["operation_id"] != "planning.update-recover"
        && invocation["operation_id"] != "delegation.dispatch"
        && invocation["operation_id"] != "configuration.write"
        && invocation["operation_id"] != "configuration.recover-write"
    {
        return Err(CoreError::new(
            "requested native operation is not available",
        ));
    }
    let current = resolve(&input, &target, true)?;
    if current["status"] == "blocked" {
        return Ok(current);
    }
    if matches!(
        invocation["operation_id"].as_str(),
        Some("configuration.write" | "configuration.recover-write")
    ) {
        crate::admit_invocation_value(
            json!({"decision":current["decision_packet"],"invocation":invocation}),
        )?;
        let executed = crate::native_config_write::execute(
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
        )?;
        let next = resolve(&input, &target, false).ok();
        let mut result = crate::operation_result_value(
            json!({"invocation":invocation,"outcome":executed["outcome"],"decision":next.as_ref().map(|v|&v["decision_packet"])}),
        )?;
        result["custody"] = executed["custody"].clone();
        return Ok(result);
    }
    if invocation["operation_id"] == "delegation.dispatch" {
        let executed = crate::native_delegation::execute(
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
        )?;
        let next = resolve(&input, &target, false).ok();
        let mut result = crate::operation_result_value(
            json!({"invocation":invocation,"outcome":executed["outcome"],"decision":next.as_ref().map(|v|&v["decision_packet"])}),
        )?;
        result["custody"] = executed["custody"].clone();
        result["value"]["reentry"] =
            crate::native_delegation::result_reentry(&executed, invocation)?;
        return Ok(result);
    }
    if invocation["operation_id"] == "planning.update-recover" {
        crate::admit_invocation_value(
            json!({"decision":current["decision_packet"],"invocation":invocation}),
        )?;
        let executed = crate::native_planning_update::recover(
            &target,
            &current["decision_packet"],
            invocation,
            &current["planning"]["update_retained"],
            || {
                let fresh = resolve(&input, &target, true)?;
                crate::admit_invocation_value(
                    json!({"decision":fresh["decision_packet"],"invocation":invocation}),
                )?;
                Ok(())
            },
        )?;
        let next = resolve(&input, &target, false).ok();
        let mut result = crate::operation_result_value(
            json!({"invocation":invocation,"outcome":executed["outcome"],"decision":next.as_ref().map(|v|&v["decision_packet"])}),
        )?;
        result["custody"] = executed["custody"].clone();
        return Ok(result);
    }
    if invocation["operation_id"] == "planning.update" {
        let retained = &current["planning"]["update_retained"];
        crate::admit_invocation_value(
            json!({"decision":current["decision_packet"],"invocation":invocation,"previous_invocation":retained.get("invocation")}),
        )?;
        let executed = crate::native_planning_update::execute(
            &target,
            &current["decision_packet"],
            invocation,
            retained,
            || {
                let fresh = resolve(&input, &target, true)?;
                crate::admit_invocation_value(
                    json!({"decision":fresh["decision_packet"],"invocation":invocation,"previous_invocation":fresh["planning"]["update_retained"].get("invocation")}),
                )?;
                Ok(())
            },
        )?;
        let next = resolve(&input, &target, false).ok();
        let mut result = crate::operation_result_value(
            json!({"invocation":invocation,"outcome":{"status":executed["status"],"effects":executed["effects"],"value":executed["value"]},"decision":next.as_ref().map(|v|&v["decision_packet"])}),
        )?;
        result["custody"] = executed["custody"].clone();
        return Ok(result);
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
