//! Public native ingress. Callers express work and public requests; repository
//! facts and owner admission are derived here, never accepted as debug inputs.
use crate::{
    CoreError, compile_value, decision_source, digest, native_config, native_instructions,
    native_memory, native_planning, native_routes, native_verification, planning,
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
    let work = json!({"kind":"current-work", "id":digest(&json!({
        "target":target, "task":input.task, "changed":input.changed
    }))?});
    let requests = owner_requests(input.request.as_ref())?;
    let request_for = |owner: &str| requests.iter().find(|request| request["owner"] == owner);
    let route_input = json!({
        "current_work":work, "source":native_routes::source(target)?,
        "request":request_for("semantic-routes")
    });
    let configuration = native_config::view(target)?;
    let admissions = &configuration["admissions"];
    let (mut owner_input, routes) = decision_source::resolve(json!({
        "target":target,
        "archive":admissions["decision_record_target"].as_str().unwrap_or(""),
        "admitted_revision":admissions["decision_record_revision"].as_str().unwrap_or(""),
        "applicable_scope":input.changed.iter().map(|path| format!("path:{path}")).collect::<Vec<_>>(),
        "semantic_routes":route_input
    }))?;
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
    let mut memory =
        native_memory::public_view(target, &input.changed, &route_fact, &work, None, None)?;
    let planning_probe = native_planning::resolve(target, &work, None)?;
    let verification_probe =
        native_verification::view(target, &input.task, &input.changed, &work, None, None)?;
    let contract = combined_contract(&[
        &configuration["capability_contract"],
        &planning_probe["capability_contract"],
        &verification_probe["capability_contract"],
        &instructions["capability_contract"],
        &memory["capability_contract"],
    ])?;
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
    let mut planning = if executing {
        native_planning::resolve_for_execution(target, &work, &contract)?
    } else if request_for("planning").is_some() {
        native_planning::resolve_with_contract(
            target,
            &work,
            request_for("planning"),
            Some(&contract),
        )?
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
    let subject = planning_detail
        .get("reconciliation")
        .and_then(|value| value.get("subject"));
    let verification = native_verification::view(
        target,
        &input.task,
        &input.changed,
        &work,
        subject,
        request_for("verification").cloned(),
    )?;
    contributions.push(verification["contribution"].clone());
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
        json!({"decision_packet":decision, "capability_contract":contract, "current_work":work, "semantic_routes":routes, "configuration":configuration, "instructions":instructions,"memory":memory,"planning":planning, "verification":verification}),
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
        if !matches!(
            owner,
            "planning" | "semantic-routes" | "verification" | "memory"
        ) {
            return Err(CoreError::new("requested native owner is not available"));
        }
        if !owners.insert(owner) {
            return Err(CoreError::new(
                "supply at most one current request per owner",
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
    if invocation["operation_id"] != "planning.reconcile" {
        return Err(CoreError::new(
            "requested native operation is not available",
        ));
    }
    let current = resolve(&input, &target, true)?;
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
