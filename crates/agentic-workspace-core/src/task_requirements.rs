//! Role-specific task judgment consumes current owner constraints; it grants none.
use crate::{CoreError, digest};
use serde_json::{Value, json};
use std::collections::BTreeSet;

fn classes(value: &Value) -> Vec<String> {
    value
        .as_array()
        .into_iter()
        .flatten()
        .map(|v| v.as_str().unwrap().to_owned())
        .collect::<BTreeSet<_>>()
        .into_iter()
        .collect()
}

pub fn view(input: Value) -> Result<Value, CoreError> {
    let declaration: Value = serde_json::from_str(include_str!(
        "../../../src/agentic_workspace/contracts/schemas/source_decision_input.schema.json"
    ))
    .expect("checked schema");
    let schema = json!({"$schema":declaration["$schema"],"$defs":declaration["$defs"],"$ref":"#/$defs/task_requirements_input"});
    crate::schema_validator(&schema, "task requirements")?
        .validate(&input)
        .map_err(|e| {
            CoreError::new(format!(
                "invalid task requirements input at {}",
                e.instance_path()
            ))
        })?;
    let judgment = &input["judgment"];
    let verification = &input["verification"];
    let verification_identity = if verification.is_null() {
        Value::Null
    } else {
        json!({"id":verification["id"],"revision":verification["revision"]})
    };
    let mut gaps = Vec::new();
    if judgment.is_null() {
        gaps.push("current-task-judgment-required");
    } else {
        if judgment["task_identity"] != input["task_identity"] {
            gaps.push("task-judgment-identity-stale");
        }
        if judgment["current_work"] != input["current_work"] {
            gaps.push("task-judgment-work-stale");
        }
        if judgment["verification_identity"] != verification_identity {
            gaps.push("task-judgment-verification-stale");
        }
        if judgment["required_result_classes"]
            .as_array()
            .unwrap()
            .is_empty()
        {
            gaps.push("task-result-requirement-missing");
        }
    }
    let mut independent = false;
    if verification.is_null() {
        if judgment["role"] == "evaluator" {
            gaps.push("current-evaluator-obligation-required");
        }
    } else {
        if verification["current"] != true {
            gaps.push("verification-obligation-not-current");
        }
        if !judgment.is_null() && verification["role"] != judgment["role"] {
            gaps.push("verification-obligation-role-mismatch");
        }
        match verification["independence_mode"].as_str().unwrap() {
            "none" | "not-applicable" => (),
            "fresh-context" => independent = true,
            "separate-actor" => gaps.push("separate-actor-eligibility-unrepresentable"),
            "distinct-provider" => gaps.push("distinct-provider-eligibility-unrepresentable"),
            "human" => gaps.push("human-authority-eligibility-unrepresentable"),
            _ => gaps.push("verification-independence-mode-unsupported"),
        }
    }
    let results = classes(&judgment["required_result_classes"]);
    let proof = classes(&judgment["required_proof_classes"])
        .into_iter()
        .chain(classes(&verification["required_proof_classes"]))
        .collect::<BTreeSet<_>>()
        .into_iter()
        .collect::<Vec<_>>();
    let guarantees = classes(&input["required_execution_guarantees"]);
    let requirements = json!({"required_result_classes":results,"required_proof_classes":proof,"independent_context":independent,"required_execution_guarantees":guarantees});
    let revision = digest(
        &json!({"kind":"agentic-workspace/task-requirements/v1","task_identity":input["task_identity"],"current_work":input["current_work"],"role":judgment["role"],"verification_identity":verification_identity,"verification_role":verification["role"],"requirements":requirements,"gaps":gaps}),
    )?;
    Ok(
        json!({"kind":"agentic-workspace/task-requirements/v1","status":if gaps.is_empty(){"resolved"}else{"unresolved"},"revision":revision,
        "role":judgment["role"],"verification_identity":verification_identity,"requirements":if gaps.is_empty(){requirements}else{Value::Null},"gaps":gaps,
        "claim_boundary":"Execution feasibility requirements only; no transport, proof, human or completion authority."}),
    )
}

#[cfg(test)]
mod tests {
    use super::*;
    fn input() -> Value {
        let task =
            crate::direct_task::subject("Inspect current links", &["doc.md".into()]).unwrap();
        let work = json!({"id":"planning:work","revision":"semantic-1"});
        json!({"kind":"agentic-workspace/task-requirements-input/v1","task_identity":task,"current_work":work,
            "judgment":{"task_identity":task,"current_work":work,"role":"executor","required_result_classes":["read-only"],"required_proof_classes":[],"verification_identity":null},
            "verification":null,"required_execution_guarantees":["history.non-persisted"]})
    }
    #[test]
    fn exact_task_judgment_preserves_constraints_and_stales_on_change() {
        let value = input();
        let result = view(value.clone()).unwrap();
        assert_eq!(result["status"], "resolved");
        assert_eq!(
            result["requirements"]["required_execution_guarantees"],
            json!(["history.non-persisted"])
        );
        for field in ["task_identity", "current_work"] {
            let mut changed = value.clone();
            changed[field]["revision"] = json!("other");
            assert_eq!(view(changed).unwrap()["status"], "unresolved");
        }
        let mut changed = value.clone();
        changed["judgment"] = Value::Null;
        assert!(view(changed).unwrap()["requirements"].is_null());
        let mut duplicate = value.clone();
        duplicate["required_execution_guarantees"] =
            json!(["history.non-persisted", "history.non-persisted"]);
        assert_eq!(view(duplicate).unwrap()["revision"], result["revision"]);
        let mut stronger = value;
        stronger["required_execution_guarantees"] = json!(["history.never-visible"]);
        assert_ne!(view(stronger).unwrap()["revision"], result["revision"]);
    }
    #[test]
    fn evaluator_requirements_are_verification_owned_and_not_model_strength() {
        let mut value = input();
        value["judgment"]["role"] = json!("evaluator");
        assert_eq!(
            view(value.clone()).unwrap()["gaps"],
            json!(["current-evaluator-obligation-required"])
        );
        value["verification"] = json!({"id":"proof:current","revision":"1","current":true,"role":"evaluator","independence_mode":"fresh-context","required_proof_classes":["worker-check"]});
        value["judgment"]["verification_identity"] = json!({"id":"proof:current","revision":"1"});
        let resolved = view(value.clone()).unwrap();
        assert_eq!(resolved["requirements"]["independent_context"], true);
        assert_eq!(
            resolved["requirements"]["required_proof_classes"],
            json!(["worker-check"])
        );
        for mode in ["separate-actor", "distinct-provider", "human", "unknown"] {
            let mut changed = value.clone();
            changed["verification"]["independence_mode"] = json!(mode);
            assert!(view(changed).unwrap()["requirements"].is_null());
        }
        let mut changed = value.clone();
        changed["verification"]["revision"] = json!("2");
        assert_eq!(view(changed).unwrap()["status"], "unresolved");
        let mut changed = value;
        changed["judgment"]["role"] = json!("executor");
        assert_eq!(view(changed).unwrap()["status"], "unresolved");
    }
    #[test]
    fn projected_requirements_feed_existing_configuration_feasibility() {
        let requirements = view(input()).unwrap()["requirements"].clone();
        let mut value = json!({"work":{"id":"work","revision":"1"},"selection":null,"candidates":[{"id":"worker","target":"worker","transport":"manual","capability_revision":"1","current":true,"authorized":true,"safe":true,"constructible":true,"result_classes":["read-only"],"proof_classes":[],"independent_context":false,"concurrency_available":true,"execution_guarantees":[],"execution":{}}]});
        value
            .as_object_mut()
            .unwrap()
            .extend(requirements.as_object().unwrap().clone());
        assert_eq!(
            crate::assignment::configurations(value.clone()).unwrap()["candidates"][0]["eligible"],
            false
        );
        value["candidates"][0]["execution_guarantees"] = json!(["history.non-persisted"]);
        assert_eq!(
            crate::assignment::configurations(value).unwrap()["candidates"][0]["eligible"],
            true
        );
    }
}
