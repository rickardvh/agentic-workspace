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
    resolve_with_baseline(input, target, executing, None)
}

fn resolve_with_baseline(
    input: &Input,
    target: &std::path::Path,
    executing: bool,
    baseline: Option<&Value>,
) -> Result<Value, CoreError> {
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
    let retained_baseline = crate::native_delegation::retained_packet(target, &requests)?;
    let baseline = baseline.or(retained_baseline.as_ref());
    if executing
        && input.invocation.as_ref().is_none_or(|i| {
            !i["source_owner"]
                .as_str()
                .is_some_and(crate::native_independent::linked)
                && i["operation_id"] != "delegation.dispatch"
                && i["operation_id"] != crate::native_patch::OP
                && i["operation_id"] != "configuration.write"
                && i["operation_id"] != "configuration.recover-write"
                && i["operation_id"] != "memory.dispose"
                && i["operation_id"] != "memory.recover-disposition"
                && i["operation_id"] != "memory.capture-decision"
                && i["operation_id"] != "memory.recover-decision"
                && i["operation_id"] != "decision-continuity.capture-decision"
                && i["operation_id"] != "decision-continuity.recover-decision"
                && i["operation_id"] != crate::native_source_reconciliation::OP
                && !(i["operation_id"] == "planning.update"
                    && (i["arguments"]["consumed_return"].is_object()
                        || i["arguments"]["retained_handoff"].is_object()))
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
    let independent = crate::native_independent::Runtime::discover(
        target,
        &work,
        &input.changed,
        &requests,
        &configuration,
    )?;
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
    let mut config_write_contract = crate::native_config_write::contract()?;
    let mut startup_adapter =
        crate::native_startup::view(target, &work, &configuration, None, None)?;
    let mut system_intent = crate::native_intent::view(target, &work, &configuration, None, None)?;
    let admissions = &configuration["admissions"];
    let repository_capture_available = admissions["decision_record_target"]
        .as_str()
        .is_some_and(|s| !s.is_empty());
    let decision_scope: Vec<_> = input.changed.iter().map(|p| format!("path:{p}")).collect();
    let native_decisions =
        crate::native_memory_capture::context(target, &configuration, &decision_scope);
    let decision_observation = native_decisions.and_then(|native| {
        let repository = if repository_capture_available {
            Some(crate::native_memory_capture::context_for(target, &configuration, &decision_scope, crate::native_memory_capture::Destination::Repository)?)
        } else { None };
        decision_source::resolve_with_publications(json!({
        "target":target,
        "archive":admissions["decision_record_target"].as_str().unwrap_or(""),
        "admitted_revision":admissions["decision_record_revision"].as_str().unwrap_or(""),
        "fallback":if available("memory") {admissions["decision_record_fallback"].clone()} else {Value::Null},
        "applicable_scope":input.changed.iter().map(|path| format!("path:{path}")).collect::<Vec<_>>(),
        "semantic_routes":route_input
    }), Some(native), repository)});
    let mut decision_source_problem = None;
    let (mut owner_input, mut routes) = match decision_observation {
        Ok(observed) => observed,
        Err(problem) => {
            if request_for("decision-continuity").is_some() {
                return Err(problem);
            }
            // An unavailable governing destination must block effects while
            // leaving retained advisory lessons available for reconciliation.
            // The routing owner still owns applicability; no failed decision
            // admission is substituted with Memory authority.
            let (route_view, intent) = crate::semantic_routes::resolve(route_input.clone())?;
            decision_source_problem = Some(problem.to_string());
            (
                json!({"contributions":[],"intent":intent}),
                Some(route_view),
            )
        }
    };
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
    let capture_available = !decision_scope.is_empty()
        && configuration["admissions"]["decision_record_target"]
            .as_str()
            .is_none_or(str::is_empty);
    let mut memory = if available("memory") {
        native_memory::public_view(
            target,
            &input.changed,
            &route_fact,
            &work,
            None,
            None,
            capture_available,
        )?
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
    let mut decision_read_contract = decision_source::read_contract()?;
    if repository_capture_available {
        crate::native_memory_capture::extend_destination(
            &mut decision_read_contract["owners"][0],
            crate::native_memory_capture::Destination::Repository,
        )?;
        decision_read_contract["restriction_authorities"][0]["affects"] =
            json!(["task", "effect:decision-source"]);
        decision_read_contract["revision"] = json!(digest(&decision_read_contract)?);
    }
    crate::native_startup::restrict_operations(&mut startup_adapter, &[&decision_read_contract])?;
    crate::native_startup::restrict_operations(&mut startup_adapter, &[&independent.contract])?;
    native_instructions::restrict_operations(&mut instructions, &independent.contract)?;
    // A missing native-owner setting permits only its Configuration repair.
    // Keep all other declared effects and completion claims restricted while
    // that repair action is available; a read request never releases the task.
    let mut configuration_gap_scopes =
        vec![json!("effect:implementation"), json!("claim:complete")];
    for fragment in [
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
        &independent.contract,
    ] {
        for owner in fragment["owners"].as_array().into_iter().flatten() {
            for effect in owner["effects"].as_array().into_iter().flatten() {
                let scope = json!(format!("effect:{}", effect["id"].as_str().unwrap()));
                if scope != "effect:configuration-source"
                    && !configuration_gap_scopes.contains(&scope)
                {
                    configuration_gap_scopes.push(scope);
                }
            }
        }
        for claim in fragment["claim_authorities"]
            .as_array()
            .into_iter()
            .flatten()
        {
            let scope = json!(format!("claim:{}", claim["claim"].as_str().unwrap()));
            if !configuration_gap_scopes.contains(&scope) {
                configuration_gap_scopes.push(scope);
            }
        }
    }
    config_write_contract["restriction_authorities"][0]["affects"]
        .as_array_mut()
        .unwrap()
        .extend(configuration_gap_scopes.clone());
    config_write_contract["revision"] = json!(digest(&config_write_contract)?);
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
        &independent.contract,
    ])?;
    for request in &requests {
        // Route selection has its own independently bound read-only contract and
        // is already validated by its responsible owner above.
        if request["owner"] != "semantic-routes" {
            // Each responsible owner validates its exact request below. Check
            // membership here without recompiling every schema for every input.
            if !contract["owners"]
                .as_array()
                .into_iter()
                .flatten()
                .any(|owner| {
                    owner["owner"] == request["owner"]
                        && owner["requests"]
                            .as_array()
                            .into_iter()
                            .flatten()
                            .any(|kind| kind["kind"] == request["request_kind"])
                })
            {
                return Err(CoreError::new("undeclared request kind or owner"));
            }
        }
    }
    let (independent_contributions, independent_views) =
        independent.resolve(target, &work, &contract, &requests)?;
    if let Some(request) = request_for("startup-adapter") {
        startup_adapter = crate::native_startup::view(
            target,
            &work,
            &configuration,
            Some(request),
            Some(&contract),
        )?;
    } else {
        startup_adapter = crate::native_startup::deliver_required(
            startup_adapter,
            target,
            &work,
            &configuration,
            &contract,
        );
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
    if let Some(request) =
        request_for("memory").filter(|r| r["request_kind"] == "memory/read-current-note/v1")
    {
        memory = native_memory::public_view(
            target,
            &input.changed,
            &route_fact,
            &work,
            Some(request),
            Some(&contract),
            capture_available,
        )?;
    } else {
        for request in memory["requests"].as_array_mut().unwrap() {
            request["capability_revision"] = contract["revision"].clone();
        }
    }
    if available("memory")
        && (memory["selected_notes"]
            .as_array()
            .is_some_and(|notes| !notes.is_empty())
            || request_for("memory")
                .is_some_and(|r| r["request_kind"] != "memory/read-current-note/v1"))
    {
        memory["receiving_admissions"] =
            match native_memory::receiving_admissions(target, &memory, &owner_input) {
                Ok(receivers) => receivers,
                Err(problem) => {
                    memory["diagnostics"]
                        .as_array_mut()
                        .unwrap()
                        .push(json!({"code":"receiving-admission-unavailable",
                    "diagnostic":problem.to_string(),"authority_effect":"advisory-only"}));
                    memory["contribution"]["facts"]["diagnostics"] = memory["diagnostics"].clone();
                    json!([])
                }
            };
        let disposition = crate::native_memory_write::view(
            target,
            &work,
            &memory,
            &configuration,
            &contract,
            request_for("memory").filter(|r| {
                matches!(
                    r["request_kind"].as_str(),
                    Some("memory/dispose-source/v1" | "memory/recover-disposition/v1")
                )
            }),
        )?;
        crate::native_memory_write::apply_view(&mut memory, disposition);
    }
    if available("memory") {
        let capture = crate::native_memory_capture::view(
            target,
            &work,
            &decision_scope,
            &configuration,
            &contract,
            &owner_input["decision_context"],
            request_for("memory").filter(|r| {
                matches!(
                    r["request_kind"].as_str(),
                    Some(
                        crate::native_memory_capture::CAPTURE
                            | crate::native_memory_capture::RECOVER
                    )
                )
            }),
        )?;
        if request_for("memory").is_some_and(|r| {
            matches!(
                r["request_kind"].as_str(),
                Some(crate::native_memory_capture::CAPTURE | crate::native_memory_capture::RECOVER)
            )
        }) {
            memory["contribution"]["relevant"] = json!(true);
            memory["contribution"]["settled"] = json!(false);
            for field in ["revision", "actions", "decisions"] {
                if let Some(v) = capture["contribution"].get(field) {
                    memory["contribution"][field] = v.clone();
                }
            }
        }
        if let Some(blockers) = capture["contribution"].get("blockers") {
            memory["contribution"]["relevant"] = json!(true);
            memory["contribution"]["settled"] = json!(false);
            memory["contribution"]["blockers"] = blockers.clone();
        }
        memory["capture"] = capture;
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
    let mut config_write = crate::native_config_write::view(
        target,
        &work,
        &configuration,
        &contract,
        request_for("configuration"),
    )?;
    if independent_views
        .as_object()
        .into_iter()
        .flat_map(|views| views.values())
        .any(|view| view["status"] == "configuration-required")
    {
        let repairing = config_write["contribution"]["actions"]
            .as_array()
            .into_iter()
            .flatten()
            .any(|action| {
                action["operation_id"] == "configuration.write"
                    && action["arguments"]["request"]["arguments"]["key"] == "modules.independent"
            });
        let affects = if repairing {
            json!(configuration_gap_scopes)
        } else {
            json!(["task"])
        };
        config_write["contribution"]["blockers"] = json!([{"code":"independent-owner-configuration-required","message":"A relevant admitted native owner requires durable settings. Follow its exact Configuration request before affected work.","affects":affects}]);
    }
    let mut contributions = vec![
        configuration["contribution"].clone(),
        config_write["contribution"].clone(),
    ];
    let repository_capture = if repository_capture_available {
        let mut capture = crate::native_memory_capture::view_for(
            target,
            &work,
            &decision_scope,
            &configuration,
            &contract,
            (
                crate::native_memory_capture::Destination::Repository,
                &owner_input["decision_context"],
            ),
            request_for("decision-continuity").filter(|r| {
                matches!(
                    r["request_kind"].as_str(),
                    Some(
                        crate::native_memory_capture::REPOSITORY_CAPTURE
                            | crate::native_memory_capture::REPOSITORY_RECOVER
                    )
                )
            }),
        )?;
        capture["contribution"]["relevant"] = json!(
            request_for("decision-continuity").is_some()
                || capture["contribution"]["blockers"].is_array()
        );
        if decision_source_problem.is_none() {
            contributions.push(capture["contribution"].clone());
        }
        capture
    } else {
        json!({"status":"not-configured","requests":[]})
    };
    if let Some(problem) = decision_source_problem {
        contributions.push(json!({"owner":"decision-continuity","revision":digest(&json!([admissions,problem]))?,
            "settled":false,"blockers":[{"code":"receiving-decision-source-unavailable","message":problem,"affects":["task"]}]}));
    }
    let mut planning_detail = Value::Null;
    if !planning["planning_input"].is_null() {
        let mut context = planning["planning_input"].clone();
        context["capability_contract"] = contract.clone();
        if startup_adapter["status"] == "source-context-delivered" {
            context["source_requests"] =
                json!([request_for("startup-adapter").unwrap_or(&startup_adapter["requests"][0])]);
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
    planning["handoff_continuation"] = update["handoff_continuation"].clone();
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
                && (i["arguments"]["consumed_return"].is_object()
                    || i["arguments"]["retained_handoff"].is_object())
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
    let mut verification = if available("verification") {
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
    if available("verification") {
        let reconciliation = crate::native_source_reconciliation::view(
            target,
            &work,
            &instructions,
            &configuration,
            &contract,
            verification_request(crate::native_source_reconciliation::REQUEST),
            crate::native_source_reconciliation::Context {
                subject,
                executing: executing
                    && input.invocation.as_ref().is_some_and(|i| {
                        i["operation_id"] == crate::native_source_reconciliation::OP
                    }),
            },
        )?;
        if reconciliation["status"] == "current" {
            instructions["contribution"]["blockers"]
                .as_array_mut()
                .unwrap()
                .retain(|b| {
                    !b["code"]
                        .as_str()
                        .unwrap_or("")
                        .ends_with(":source-reconciliation-required")
                });
        }
        if reconciliation["action"].is_object() {
            verification["contribution"]["actions"]
                .as_array_mut()
                .unwrap()
                .push(reconciliation["action"].clone());
        }
        if !reconciliation["source_revision"].is_null() {
            verification["contribution"]["revision"] = reconciliation["source_revision"].clone();
        }
        if reconciliation["decisions"]
            .as_array()
            .is_some_and(|a| !a.is_empty())
        {
            verification["contribution"]["decisions"] = reconciliation["decisions"].clone();
        }
        verification["source_reconciliation"] = reconciliation.clone();
        // Reobserve these owner obligations on every selected-Plan entry. Direct
        // work remains stateless; this projection never creates Planning.
        if subject.is_some() {
            planning["source_reconciliation"] = reconciliation;
        }
    }
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
        requests.iter().find(|r| {
            r["request_kind"] == "assignment/judge-readonly-inputs/v1"
                || r["request_kind"] == crate::native_handoff::PATCH_INPUTS
        }),
        &contract,
        baseline,
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
        None,
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
        baseline,
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
        let fresh = resolve_with_baseline(&original_input, target, true, baseline)?;
        crate::admit_invocation_value(
            json!({"decision":fresh["decision_packet"],"invocation":original}),
        )?;
    }
    delegation
        .as_object_mut()
        .unwrap()
        .remove("observed_invocation");
    let mut admission =
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
    let integration = crate::native_patch::view(
        target,
        &work,
        &admission,
        &requests,
        &contract,
        executing
            && input
                .invocation
                .as_ref()
                .is_some_and(|i| i["operation_id"] == crate::native_patch::OP),
    )?;
    admission["integration"] = integration["result"].clone();
    if admission["result_use_allowed"] == true && !admission["delta"].is_null() {
        *contributions
            .iter_mut()
            .find(|c| c["owner"] == "workspace")
            .unwrap() = native_config::assignment_consumption(
            &configuration,
            &requirements["assignment"]["result"],
            &requirements["execution_configurations"],
            Some(&admission),
        );
    }
    if integration["action"].is_object() {
        assignment_contribution["actions"] = json!([integration["action"]]);
        assignment_contribution["settled"] = json!(false);
        assignment_contribution["revision"] = json!(digest(&json!([
            assignment_contribution["revision"],
            integration["action"]
        ]))?);
    }
    requirements["patch_integration"] = integration;
    contributions.push(assignment_contribution);
    let adopted = crate::native_planning_update::adopt_return(
        target, &work, &contract, &planning, &admission, &requests,
    )?;
    planning["adoption_requests"] = adopted["requests"].clone();
    let retained_handoff = if executing
        && input.invocation.as_ref().is_some_and(|i| {
            i["arguments"]["retained_handoff"].is_object() && update["retained"]["invocation"] == *i
        }) {
        let mut action = update["action"].clone();
        action["source_requests"] = json!(requests);
        json!({"requests":[],"action":action})
    } else {
        crate::native_planning_update::retain_handoff(
            target,
            &work,
            &contract,
            &planning,
            &json!({"task":input.task,"changed":input.changed,"handoff":handoff,"delegation":delegation,"admission":admission,"planning_subject":planning_detail["reconciliation"]["subject"]}),
            &requests,
        )?
    };
    planning["handoff_retention_requests"] = retained_handoff["requests"].clone();
    let planning_action = if adopted["action"].is_object() {
        &adopted["action"]
    } else {
        &retained_handoff["action"]
    };
    if planning_action.is_object() {
        let owner = contributions
            .iter_mut()
            .find(|c| c["owner"] == "planning")
            .ok_or_else(|| CoreError::new("Planning owner unavailable for result adoption"))?;
        owner["actions"] = json!([planning_action]);
        owner["decisions"] = json!([]);
        owner["blockers"] = json!([]);
        owner["settled"] = json!(false);
        owner["revision"] = json!(digest(&json!([owner["revision"], planning_action]))?);
    }
    requirements["assignment"]["result_admission"] = admission;
    contributions.push(delegation["contribution"].clone());
    delegation.as_object_mut().unwrap().remove("contribution");
    requirements["delegation"] = delegation;
    requirements["handoff"] = handoff;
    contributions.push(system_intent["contribution"].clone());
    contributions.push(memory["contribution"].clone());
    contributions.extend(independent_contributions);
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
                    Some(
                        "proof.report"
                            | "configuration.write"
                            | "configuration.recover-write"
                            | "memory.dispose"
                            | "memory.recover-disposition"
                            | "memory.capture-decision"
                            | "memory.recover-decision"
                            | "decision-continuity.capture-decision"
                            | "decision-continuity.recover-decision"
                            | "verification.record-source-reconciliation"
                    )
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
            request_for("startup-adapter").unwrap_or(&startup_adapter["requests"][0]);
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
    let mut decision_sources = decision_source::public_read(
        target,
        &decision_context,
        &decision,
        &work,
        &contract,
        request_for("decision-continuity")
            .filter(|r| r["request_kind"] == "decision-continuity/read-current-source/v1"),
    )?;
    decision_sources["capture"] = repository_capture;
    planning.as_object_mut().unwrap().remove("planning_input");
    planning["current_owner"] = planning_detail;
    let mut public = json!({"runtime_compatibility":compatibility,"decision_sources":decision_sources,"decision_packet":decision, "capability_contract":contract, "current_work":work, "semantic_routes":routes, "configuration":configuration,"configuration_write":config_write,"system_intent":system_intent,"startup_adapter":startup_adapter,"workflow_artifact_profile":artifact_profile, "instructions":instructions,"memory":memory,"planning":planning, "verification":verification,"task_requirements":requirements});
    public["configuration"]
        .as_object_mut()
        .unwrap()
        .remove("independent_admissions");
    public["configuration"]["admissions"]
        .as_object_mut()
        .unwrap()
        .remove("decision_delegations");
    if independent_views
        .as_object()
        .is_some_and(|views| !views.is_empty())
    {
        public["independent_owners"] = independent_views;
        let request = public["configuration_write"]["choice_requests"][0].clone();
        for view in public["independent_owners"]
            .as_object_mut()
            .unwrap()
            .values_mut()
        {
            if view["status"] == "configuration-required" {
                view["configuration_request"] = request.clone();
            }
        }
    }
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

#[derive(Default)]
struct InvocationProgress {
    entered_effect_owner: bool,
    confirmed: Option<Value>,
}

fn reentry(value: &Value) -> Value {
    json!({"operation":"start","context":{"target":value["target"],
        "task":value.get("task").cloned().unwrap_or(json!("")),
        "changed":value.get("changed").cloned().unwrap_or(json!([]))}})
}

pub(crate) fn rejected_invocation(value: &Value, message: &str) -> Value {
    invocation_failure(value, message, &InvocationProgress::default())
}

fn invocation_failure(value: &Value, message: &str, progress: &InvocationProgress) -> Value {
    if let Some(confirmed) = &progress.confirmed {
        let mut result = confirmed.clone();
        result["continuation_status"] = json!("unavailable");
        result["next_decision"] = Value::Null;
        result["continuation"] = json!({"status":"unavailable","reentry":reentry(value),
            "diagnostic":message,"retry_effect":false});
        return result;
    }
    let uncertain = progress.entered_effect_owner;
    json!({"kind":"agentic-workspace/operation-result/v1",
        "operation_id":value["invocation"]["operation_id"],
        "status":if uncertain{"uncertain"}else{"rejected"},"effects":if uncertain{Value::Null}else{json!([])},
        "effect_outcome":{"status":if uncertain{"uncertain"}else{"rejected-before-effect"},
            "claim_boundary":if uncertain{"The effect owner was entered; no committed or absent effect is inferred. Re-enter current recovery before any retry."}else{"Rejected before effect-owner entry; no effect was attempted."}},
        "error":{"message":message},"next_decision":null,"continuation_status":"unavailable",
        "continuation":{"status":"reentry-required","reentry":reentry(value),"retry_effect":false},
        "recovery":{"submitted_invocation":value["invocation"],"reentry":reentry(value),
            "authority":"Submitted material is recovery context only; current source owners retain admission."}})
}

/// Public Rust callers receive the same explicit effect/continuation result as
/// CLI, JSON and thin bindings, including pre-effect rejection and uncertainty.
pub fn invoke(value: Value) -> Result<Value, CoreError> {
    Ok(invoke_operating(value))
}

// Existing interruption fixtures assert diagnostic text as an error. Translate
// the explicit public result for those assertions; never bypass public admission.
#[cfg(test)]
pub(crate) fn invoke_checked(value: Value) -> Result<Value, CoreError> {
    let result = invoke(value)?;
    if matches!(
        result["effect_outcome"]["status"].as_str(),
        Some("uncertain" | "rejected-before-effect")
    ) {
        Err(CoreError::new(
            result["error"]["message"]
                .as_str()
                .unwrap_or("effect not established"),
        ))
    } else {
        Ok(result)
    }
}

pub(crate) fn invoke_operating(value: Value) -> Value {
    let mut progress = InvocationProgress::default();
    match invoke_inner(value.clone(), &mut progress) {
        Ok(result) => result,
        Err(error) => invocation_failure(&value, &error.to_string(), &progress),
    }
}

fn finish_invocation(
    input: &Input,
    target: &std::path::Path,
    invocation: &Value,
    executed: &Value,
    progress: &mut InvocationProgress,
) -> Result<Value, CoreError> {
    let outcome = executed.get("outcome").cloned().unwrap_or_else(|| {
        json!({"status":executed["status"],"effects":executed["effects"],"value":executed["value"]})
    });
    let mut result = crate::operation_result_value(
        json!({"invocation":invocation,"outcome":outcome,"decision":null}),
    )?;
    result["custody"] = executed["custody"].clone();
    result["effect_outcome"] = json!({"status":if outcome["status"] == "rejected"{"rejected-before-effect"}else{"committed"},
        "owner_status":outcome["status"],"reported_effects":outcome["effects"],
        "claim_boundary":"Only the exact owner result is established; continuation and task completion are separate facts."});
    progress.confirmed = Some(result.clone());
    // This is precisely fresh public entry, without replaying the mutation's
    // request or treating its previous source snapshot as current.
    let mut context = json!({"target":target,"task":input.task,"changed":input.changed});
    match post_effect_changed_paths(&input.changed, executed, &outcome) {
        Ok(changed) => {
            context["changed"] = json!(changed);
            let current = start(context.clone());
            Ok(attach_continuation(result, current, &context))
        }
        Err(error) => {
            let mut result = attach_continuation(result, Err(error), &context);
            // The old context is a recovery starting point, not a complete
            // post-effect work scope. Never infer paths from dirty state or
            // accept worker/caller claims as owner-established effect facts.
            result["continuation"]["reentry"]["required_material"] = json!({
                "changed":"Establish the complete post-effect changed-path set through the effect owner before continuing affected work."});
            Ok(result)
        }
    }
}

fn post_effect_changed_paths(
    before: &[String],
    executed: &Value,
    outcome: &Value,
) -> Result<Vec<String>, CoreError> {
    let mut changed = before.to_vec();
    if let Some(paths) = executed.get("post_effect_changed_paths") {
        let paths: Vec<String> = serde_json::from_value(paths.clone())
            .map_err(|_| CoreError::new("Owner post-effect changed-path identity is invalid"))?;
        for path in paths {
            decision_source::relative(&path)?;
            changed.push(path);
        }
    } else if outcome["effects"] != json!([]) {
        return Err(CoreError::new(
            "Owner post-effect changed-path identity is unavailable; effect outcome remains established; do not retry the effect",
        ));
    }
    changed.sort();
    changed.dedup();
    Ok(changed)
}

fn attach_continuation(
    mut result: Value,
    current: Result<Value, CoreError>,
    context: &Value,
) -> Value {
    result["next_decision"] = Value::Null;
    result["continuation_status"] = json!("unavailable");
    match current {
        Ok(full) if full["decision_packet"].is_object() => {
            result["continuation_status"] = json!("current");
            result["next_decision"] = full["decision_packet"].clone();
            result["continuation"] = json!({"status":"current","result":full,"context":context,
                "reentry":reentry(context),"retry_effect":false});
        }
        Ok(blocked) => {
            result["continuation"] = json!({"status":"unavailable","reentry":reentry(context),
                "blocked":blocked,"retry_effect":false});
        }
        Err(error) => {
            result["continuation"] = json!({"status":"unavailable","reentry":reentry(context),
                "diagnostic":error.to_string(),"retry_effect":false});
        }
    }
    result
}

fn invoke_inner(value: Value, progress: &mut InvocationProgress) -> Result<Value, CoreError> {
    let (input, target) = input(value)?;
    if input.request.is_some() || input.invocation.is_none() {
        return Err(CoreError::new(
            "invoke requires exactly an operation invocation",
        ));
    }
    let invocation = input.invocation.as_ref().unwrap();
    let independent = invocation["source_owner"]
        .as_str()
        .is_some_and(crate::native_independent::linked);
    if !independent
        && invocation["operation_id"] != "planning.reconcile"
        && invocation["operation_id"] != "proof.report"
        && invocation["operation_id"] != "planning.create"
        && invocation["operation_id"] != "planning.update"
        && invocation["operation_id"] != "planning.update-recover"
        && invocation["operation_id"] != "delegation.dispatch"
        && invocation["operation_id"] != crate::native_patch::OP
        && invocation["operation_id"] != "configuration.write"
        && invocation["operation_id"] != "configuration.recover-write"
        && invocation["operation_id"] != "memory.dispose"
        && invocation["operation_id"] != "memory.recover-disposition"
        && invocation["operation_id"] != "memory.capture-decision"
        && invocation["operation_id"] != "memory.recover-decision"
        && invocation["operation_id"] != "decision-continuity.capture-decision"
        && invocation["operation_id"] != "decision-continuity.recover-decision"
        && invocation["operation_id"] != crate::native_source_reconciliation::OP
    {
        return Err(CoreError::new(
            "requested native operation is not available",
        ));
    }
    let current = resolve(&input, &target, true)?;
    if current["status"] == "blocked" {
        let mut rejected = rejected_invocation(
            &json!({"target":target,"task":input.task,
            "changed":input.changed,"invocation":invocation}),
            "Current runtime blocks invocation",
        );
        rejected["blockers"] = current;
        return Ok(rejected);
    }
    if independent {
        crate::admit_invocation_value(
            json!({"decision":current["decision_packet"],"invocation":invocation}),
        )?;
        progress.entered_effect_owner = true;
        let executed = crate::native_independent_publication::execute(
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
        let result = finish_invocation(&input, &target, invocation, &executed, progress)?;
        return Ok(result);
    }
    if invocation["operation_id"] == crate::native_source_reconciliation::OP {
        crate::admit_invocation_value(
            json!({"decision":current["decision_packet"],"invocation":invocation}),
        )?;
        progress.entered_effect_owner = true;
        let executed = crate::native_source_reconciliation::execute(
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
        let result = finish_invocation(&input, &target, invocation, &executed, progress)?;
        return Ok(result);
    }
    if matches!(
        invocation["operation_id"].as_str(),
        Some(
            "configuration.write"
                | "configuration.recover-write"
                | "memory.dispose"
                | "memory.recover-disposition"
                | "memory.capture-decision"
                | "memory.recover-decision"
                | "decision-continuity.capture-decision"
                | "decision-continuity.recover-decision"
        )
    ) {
        crate::admit_invocation_value(
            json!({"decision":current["decision_packet"],"invocation":invocation}),
        )?;
        let revalidate = || {
            let fresh = resolve(&input, &target, true)?;
            crate::admit_invocation_value(
                json!({"decision":fresh["decision_packet"],"invocation":invocation}),
            )?;
            Ok(())
        };
        progress.entered_effect_owner = true;
        let executed = if matches!(
            invocation["operation_id"].as_str(),
            Some(
                "memory.capture-decision"
                    | "memory.recover-decision"
                    | "decision-continuity.capture-decision"
                    | "decision-continuity.recover-decision"
            )
        ) {
            crate::native_memory_capture::execute(
                &target,
                &current["decision_packet"],
                invocation,
                revalidate,
            )?
        } else if invocation["source_owner"] == "memory" {
            crate::native_memory_write::execute(
                &target,
                &current["decision_packet"],
                invocation,
                revalidate,
            )?
        } else {
            crate::native_config_write::execute(
                &target,
                &current["decision_packet"],
                invocation,
                revalidate,
            )?
        };
        let result = finish_invocation(&input, &target, invocation, &executed, progress)?;
        return Ok(result);
    }
    if invocation["operation_id"] == crate::native_patch::OP {
        progress.entered_effect_owner = true;
        let executed =
            crate::native_patch::execute(&target, &current["decision_packet"], invocation, || {
                let fresh = resolve(&input, &target, true)?;
                crate::admit_invocation_value(
                    json!({"decision":fresh["decision_packet"],"invocation":invocation}),
                )?;
                Ok(())
            })?;
        let mut result = finish_invocation(&input, &target, invocation, &executed, progress)?;
        result["value"]["reentry"] = json!({"task":input.task,"changed":input.changed,"request":invocation["source_requests"]});
        return Ok(result);
    }
    if invocation["operation_id"] == "delegation.dispatch" {
        progress.entered_effect_owner = true;
        let executed = crate::native_delegation::execute(
            &target,
            &current["decision_packet"],
            invocation,
            |after_worker| {
                let baseline = (after_worker
                    && invocation["arguments"]["packet"]["assignment_identity"]["scope_class"]
                        == "unapplied-patch")
                    .then_some(&invocation["arguments"]["packet"]);
                let fresh = resolve_with_baseline(&input, &target, true, baseline)?;
                crate::admit_invocation_value(
                    json!({"decision":fresh["decision_packet"],"invocation":invocation}),
                )?;
                Ok(())
            },
        )?;
        let mut result = finish_invocation(&input, &target, invocation, &executed, progress)?;
        result["value"]["reentry"] =
            crate::native_delegation::result_reentry(&executed, invocation)?;
        return Ok(result);
    }
    if invocation["operation_id"] == "planning.update-recover" {
        crate::admit_invocation_value(
            json!({"decision":current["decision_packet"],"invocation":invocation}),
        )?;
        progress.entered_effect_owner = true;
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
        let result = finish_invocation(&input, &target, invocation, &executed, progress)?;
        return Ok(result);
    }
    if invocation["operation_id"] == "planning.update" {
        let retained = &current["planning"]["update_retained"];
        crate::admit_invocation_value(
            json!({"decision":current["decision_packet"],"invocation":invocation,"previous_invocation":retained.get("invocation")}),
        )?;
        progress.entered_effect_owner = true;
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
        let result = finish_invocation(&input, &target, invocation, &executed, progress)?;
        return Ok(result);
    }
    if invocation["operation_id"] == "planning.create" {
        let committed = &current["planning"]["creation_committed_operation"];
        crate::admit_invocation_value(
            json!({"decision":current["decision_packet"],"invocation":invocation,"previous_invocation":committed.get("invocation")}),
        )?;
        progress.entered_effect_owner = true;
        let executed = if committed.is_object() {
            let mut result = committed["outcome"].clone();
            result["custody"] = committed["custody"].clone();
            result["post_effect_changed_paths"] = committed["post_effect_changed_paths"].clone();
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
        let mut result = finish_invocation(&input, &target, invocation, &executed, progress)?;
        // Creation is bound to the former work identity, so its deterministic
        // discovery path need not be rediscovered by the expanded work scope.
        // Ask Planning about the exact published owner using the fresh context.
        if let Some(next) = result["continuation"].get("result").cloned() {
            if let Some(reference) = result["value"]["owner_path"].as_str() {
                match native_planning::candidate(
                    &target,
                    &next["current_work"],
                    reference,
                    &next["capability_contract"],
                ) {
                    Ok(candidate) => {
                        result["value"]["selection_request"] = candidate["requests"][0].clone();
                        result["value"]["selection_context"] =
                            result["continuation"]["context"].clone();
                    }
                    Err(error) => result["value"]["selection_gap"] = json!(error.to_string()),
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
        progress.entered_effect_owner = true;
        let executed = crate::native_proof::execute(&target, &current, invocation, || {
            let fresh = resolve(&input, &target, true)?;
            crate::admit_invocation_value(
                json!({"decision":fresh["decision_packet"],"invocation":invocation}),
            )?;
            Ok(())
        })?;
        let result = finish_invocation(&input, &target, invocation, &executed, progress)?;
        return Ok(result);
    }
    let committed = &current["planning"]["current_owner"]["committed_operation"];
    crate::admit_invocation_value(
        json!({"decision":current["decision_packet"], "invocation":invocation,
            "previous_invocation":committed.get("invocation")}),
    )?;
    progress.entered_effect_owner = true;
    let mut executed = if committed.is_object() {
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
    executed["post_effect_changed_paths"] = native_planning::post_effect_paths();
    let result = finish_invocation(&input, &target, invocation, &executed, progress)?;
    Ok(result)
}

#[cfg(test)]
mod continuation_tests {
    use super::*;

    #[test]
    fn missing_or_invalid_owner_paths_preserve_effect_without_claiming_currentness() {
        let input: Input = serde_json::from_value(
            json!({"target":"unused","task":"same work","changed":["existing.txt"]}),
        )
        .unwrap();
        let invocation = json!({"operation_id":"fixture.write","effects":["implementation"]});
        // Neither a caller's proposal nor arbitrary result material is a path
        // report by the responsible execution owner.
        let executed = json!({"outcome":{"status":"applied","effects":["implementation"],
            "value":{"changed_paths":["untrusted.txt"]}}});
        for paths in [
            None,
            Some(Value::Null),
            Some(json!(["../foreign.txt"])),
            Some(json!([7])),
        ] {
            let mut reported = executed.clone();
            if let Some(paths) = paths {
                reported["post_effect_changed_paths"] = paths;
            }
            let result = finish_invocation(
                &input,
                std::path::Path::new("unused"),
                &invocation,
                &reported,
                &mut InvocationProgress::default(),
            )
            .unwrap();
            assert_eq!(result["effect_outcome"]["status"], "committed");
            assert_eq!(result["value"], executed["outcome"]["value"]);
            assert_eq!(result["continuation"]["status"], "unavailable");
            assert_eq!(result["continuation"]["retry_effect"], false);
            assert!(result["continuation"]["reentry"]["required_material"].is_object());
            assert_eq!(
                result["continuation"]["reentry"]["context"]["changed"],
                json!(["existing.txt"])
            );
        }
    }

    #[test]
    fn committed_effect_survives_failed_or_blocked_continuation() {
        let root = std::env::temp_dir().join(format!(
            "aw-continuation-{}-{}",
            std::process::id(),
            std::time::SystemTime::now()
                .duration_since(std::time::UNIX_EPOCH)
                .unwrap()
                .as_nanos()
        ));
        std::fs::create_dir(&root).unwrap();
        let context = json!({"target":root,"task":"Set configured invocation","changed":[]});
        let initial = start(context.clone()).unwrap();
        let mut request = initial["configuration_write"]["creation_requests"]
            .as_array()
            .unwrap()
            .iter()
            .find(|r| r["arguments"]["key"] == "workspace.cli_invoke")
            .unwrap()
            .clone();
        request["arguments"]["value"] = json!("exact-native");
        let mut proposed = context.clone();
        proposed["request"] = request;
        let question = start(proposed).unwrap();
        let mut answer =
            question["decision_packet"]["decision_request"]["response_request"].clone();
        answer["arguments"]["answer"] = json!("authorize-write");
        let mut answered = context.clone();
        answered["request"] = answer;
        let selected = start(answered).unwrap();
        let mut execution = context.clone();
        execution["invocation"] = selected["decision_packet"]["primary_action"].clone();
        let mut committed = invoke_operating(execution);
        assert_eq!(committed["effect_outcome"]["status"], "committed");
        committed["next_decision"] = Value::Null;
        let source = root.join(".agentic-workspace/config.toml");
        let bytes = std::fs::read(&source).unwrap();
        for next in [
            Err(CoreError::new("source unavailable after commit")),
            Ok(json!({"status":"blocked","recovery":"restore compatible runtime"})),
        ] {
            let result = attach_continuation(committed.clone(), next, &context);
            for field in ["status", "effects", "value", "custody", "effect_outcome"] {
                assert_eq!(result[field], committed[field]);
            }
            assert_eq!(result["continuation"]["status"], "unavailable");
            assert_eq!(result["continuation"]["reentry"]["context"], context);
            assert_eq!(result["continuation"]["retry_effect"], false);
            assert!(result["next_decision"].is_null());
            assert_eq!(std::fs::read(&source).unwrap(), bytes);
        }
        std::fs::remove_dir_all(root).unwrap();
    }

    #[test]
    fn failure_stage_never_conflates_rejection_uncertainty_and_commit() {
        let input = json!({"target":"exact-target","task":"same-work","changed":[],
            "invocation":{"operation_id":"owner.write","arguments":{"postimage":"exact"}}});
        let mut progress = InvocationProgress::default();
        let rejected = invocation_failure(&input, "admission failed", &progress);
        assert_eq!(
            rejected["effect_outcome"]["status"],
            "rejected-before-effect"
        );
        progress.entered_effect_owner = true;
        let uncertain = invocation_failure(&input, "owner interrupted", &progress);
        assert_eq!(uncertain["effect_outcome"]["status"], "uncertain");
        assert_eq!(
            uncertain["recovery"]["submitted_invocation"],
            input["invocation"]
        );
        assert_eq!(uncertain["continuation"]["retry_effect"], false);
        progress.confirmed = Some(json!({"status":"applied","effects":["owned-write"],
            "effect_outcome":{"status":"committed"},"value":{"receipt":"exact"}}));
        let committed = invocation_failure(&input, "post-effect metadata unavailable", &progress);
        assert_eq!(committed["effect_outcome"]["status"], "committed");
        assert_eq!(committed["value"]["receipt"], "exact");
        assert_eq!(committed["continuation"]["status"], "unavailable");
    }
}
