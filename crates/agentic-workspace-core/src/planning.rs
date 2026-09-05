//! Same-owner reconciliation of one admitted former Planning execplan.
//! Source admission and semantic applicability come from the trusted host/owner,
//! never from the filename, JSON shape, package installation or a caller label.
use crate::{CoreError, attempt_store, compile_value, digest, operation_result_value};
use serde::Deserialize;
use serde_json::{Value, json};

#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct Input {
    target: String,
    relevant: bool,
    source: Option<attempt_store::Evidence>,
    #[serde(default)]
    irrelevant_history: bool,
    #[serde(default = "crate::empty_object")]
    intent: Value,
    capability_contract: Option<Value>,
    custody: Option<Value>,
    invocation: Option<Value>,
}

fn error(message: impl ToString) -> CoreError {
    CoreError::new(message.to_string())
}

fn reconciliation(input: &Input) -> Result<Value, CoreError> {
    let source = input
        .source
        .as_ref()
        .ok_or_else(|| error("Planning source admission required"))?;
    if source.owner != "planning" {
        return Err(error(
            "former source is not admitted as Planning-owned; preserve and route its disposition",
        ));
    }
    let body = attempt_store::read_source(&input.target, source)?;
    let schema: Value = serde_json::from_str(include_str!(
        "../../../src/agentic_workspace/contracts/schemas/planning_reconciliation.schema.json"
    ))
    .map_err(error)?;
    let mut former_shape = schema["$defs"]["former_execplan"].clone();
    former_shape["$schema"] = schema["$schema"].clone();
    crate::schema_validator(&former_shape, "former Planning source")?
        .validate(&body)
        .map_err(|e| error(format!("invalid former Planning source; preserve it: {e}")))?;
    let id = body["id"]
        .as_str()
        .filter(|id| !id.is_empty())
        .ok_or_else(|| error("former Planning subject identity missing"))?;
    // These are this representation's fields, not a general migration mapping.
    // No judgmental text classification or completion inference is performed.
    let material = json!({
        "outcome": {"intent": body["intent"], "goals": body["goal"]},
        "scope": {"declared": body["scope"], "paths": body["touched_paths"], "owner_level": body["owner_level"], "selection": body["relationships"]["selection"]},
        "dependencies": {"declared": body["relationships"]["dependencies"], "parent": body["parent"], "references": body["references"], "external_posture": body["relationships"]["external_posture"]},
        "constraints": {"non_goals": body["non_goals"], "bounds": body["execution_bounds"]},
        "frontier": {"lifecycle": body["lifecycle"], "phase": body["phase"], "next_action": body["next_action"], "blockers": body["blockers"]},
        "proof": {"declared": body["proof"], "commands": body["validation_commands"], "completion_criteria": body["completion_criteria"], "posture": body["relationships"]["proof_posture"]},
        "handoff": {"delegation": body["relationships"]["delegation"], "assignment": body["relationships"]["assignment"], "returned": body["relationships"]["returned"], "integration_pending": body["relationships"]["integration_pending"], "contracts": body["specialist_contracts"]},
        "residual": {"continuation": body["continuation"], "intent_continuity": body["intent_continuity"]}
    });
    let known = [
        "kind",
        "id",
        "title",
        "owner_level",
        "revision",
        "intent",
        "goal",
        "scope",
        "touched_paths",
        "parent",
        "references",
        "non_goals",
        "execution_bounds",
        "lifecycle",
        "phase",
        "next_action",
        "blockers",
        "proof",
        "validation_commands",
        "completion_criteria",
        "relationships",
        "specialist_contracts",
        "continuation",
        "intent_continuity",
    ];
    let mut ambiguity = Vec::new();
    let mut omitted = Vec::new();
    for key in body
        .as_object()
        .ok_or_else(|| error("former source must be an object"))?
        .keys()
    {
        if known.contains(&key.as_str()) {
            continue;
        }
        if input.irrelevant_history && key == "drift_log" {
            omitted.push(key.clone());
        } else {
            ambiguity.push(key.clone());
        }
    }
    if let Some(relationships) = body["relationships"].as_object() {
        for key in relationships.keys() {
            if ![
                "selection",
                "proof_posture",
                "external_posture",
                "delegation",
                "dependencies",
                "assignment",
                "returned",
                "integration_pending",
            ]
            .contains(&key.as_str())
            {
                ambiguity.push(format!("relationships.{key}"));
            }
        }
    }
    let subject_id = format!(
        "planning:{}",
        digest(
            &json!({"target": std::fs::canonicalize(&source.target).map_err(error)?, "id": id})
        )?
    );
    Ok(json!({
        "kind": "agentic-planning/reconciliation/v1", "owner": "planning",
        "former_source": source,
        "subject": {"id": subject_id, "revision": digest(&material)?, "label": body["title"], "state": material},
        "coverage": {"complete": ambiguity.is_empty(), "ambiguities": ambiguity, "omitted_history": omitted},
        "former_source_retained": true
    }))
}

fn decision(input: &Input, reconciled: &Value, current: bool) -> Result<Value, CoreError> {
    let actions = if !current && reconciled["coverage"]["complete"] == true {
        json!([{
            "operation_id": "planning.reconcile",
            "dependency_revision": digest(reconciled)?,
            "arguments": {"target": input.target, "reconciliation": reconciled},
            "effects": ["planning-state"]
        }])
    } else {
        json!([])
    };
    let mut value = json!({"contributions": [{
        "owner": "planning", "revision": digest(reconciled)?,
        "facts": {"reconciliation": reconciled, "current": current},
        "actions": actions, "settled": current
    }], "intent": input.intent});
    if let Some(contract) = &input.capability_contract {
        // A producer revision is descriptive; the host still must independently
        // admit this operation/effect authority through the shared contract.
        let operation = contract["owners"]
            .as_array()
            .into_iter()
            .flatten()
            .filter(|owner| owner["owner"] == "planning")
            .flat_map(|owner| owner["operations"].as_array().into_iter().flatten())
            .find(|operation| operation["id"] == "planning.reconcile");
        if operation
            .is_none_or(|operation| operation["semantic_revision"] != "planning-reconciliation-v1")
        {
            return Err(error(
                "current Planning reconciliation semantics are not admitted",
            ));
        }
        value["capability_contract"] = contract.clone();
    }
    let mut result = compile_value(value)?;
    result["planning"] = json!({"reconciliation": reconciled, "current": current});
    Ok(result)
}

fn direct(input: &Input) -> Result<Value, CoreError> {
    compile_value(json!({"contributions": [], "intent": input.intent}))
}

/// Read-only host boundary. Source/custody inputs must be independently admitted
/// owner evidence. Ordinary clients select intentions, not these authority facts.
pub fn view(value: Value) -> Result<Value, CoreError> {
    let input: Input = serde_json::from_value(value).map_err(error)?;
    if !input.relevant {
        return direct(&input);
    }
    let reconciled = reconciliation(&input)?;
    let pending = decision(&input, &reconciled, false)?;
    if reconciled["coverage"]["complete"] != true {
        return Ok(pending);
    }
    if let Some(custody) = &input.custody {
        let action = &pending["primary_action"];
        let admission = attempt_store::admit(
            json!({"target": input.target, "decision": pending, "invocation": action, "custody": custody}),
        )?;
        if admission["disposition"] == "replay" {
            if admission["record"]["outcome"]["value"] != reconciled {
                return Err(error(
                    "committed Planning reconciliation does not match current source semantics",
                ));
            }
            return decision(&input, &reconciled, true);
        }
        return Err(error(
            "Planning reconciliation is uncertain; former source remains authoritative",
        ));
    }
    Ok(pending)
}

/// Execute only the exact owner-derived operation. Its sole mutation is the
/// durable reconciliation result; the former representation is never edited.
pub fn reconcile(value: Value) -> Result<Value, CoreError> {
    let input: Input = serde_json::from_value(value).map_err(error)?;
    if !input.relevant {
        return Err(error("no Planning reconciliation is applicable"));
    }
    let reconciled = reconciliation(&input)?;
    let pending = decision(&input, &reconciled, false)?;
    let invocation = input
        .invocation
        .as_ref()
        .ok_or_else(|| error("exact Planning invocation required"))?;
    let admission = attempt_store::admit(
        json!({"target": input.target, "decision": pending, "invocation": invocation, "custody": input.custody}),
    )?;
    if admission["disposition"] == "uncertain" {
        return Ok(admission);
    }
    let stored = if admission["disposition"] == "execute" {
        // Recheck the former authority before the only semantic commit.
        reconciliation(&input)?;
        attempt_store::commit(
            json!({"target": input.target, "custody": admission["custody"], "outcome": {
                "status": "applied", "effects": ["planning-state"], "value": reconciled
            }}),
        )?
    } else {
        json!({"record": admission["record"], "custody": admission["custody"]})
    };
    if stored["record"]["outcome"]["value"] != reconciled {
        return Err(error(
            "committed Planning reconciliation does not match current source semantics",
        ));
    }
    // Committed truth survives even when current source reconciliation fails.
    let continuation = reconciliation(&input)
        .and_then(|current| decision(&input, &current, true))
        .ok();
    let mut result = operation_result_value(
        json!({"invocation": stored["record"]["invocation"], "outcome": stored["record"]["outcome"], "decision": continuation}),
    )?;
    result["custody"] = stored["custody"].clone();
    Ok(result)
}
