//! Applicability only: exact source facts and current agent judgment, never proof or waiver authority.
use crate::{CoreError, digest};
use serde_json::{Value, json};
use std::collections::BTreeSet;

fn strings(value: &Value) -> Vec<&str> {
    value
        .as_array()
        .into_iter()
        .flatten()
        .filter_map(Value::as_str)
        .collect()
}
pub(crate) fn schema() -> Value {
    serde_json::from_str(include_str!(
        "../../../src/agentic_workspace/contracts/schemas/assurance_applicability.schema.json"
    ))
    .expect("checked schema")
}
pub fn view(input: Value) -> Result<Value, CoreError> {
    crate::schema_validator(&schema(), "assurance applicability")?
        .validate(&input)
        .map_err(|e| CoreError::new(e.to_string()))?;
    let requirements = input["requirements"].as_array().unwrap();
    let mut ids = BTreeSet::new();
    for row in requirements {
        let id = row["id"]
            .as_str()
            .filter(|s| !s.is_empty())
            .ok_or_else(|| CoreError::new("assurance requirement id must be nonempty"))?;
        if !ids.insert(id) {
            return Err(CoreError::new("duplicate assurance requirement id"));
        }
    }
    let judgment = &input["judgment"];
    let mut judgment_gap = None;
    if !judgment.is_null() {
        if judgment["decisions"]
            .as_object()
            .unwrap()
            .keys()
            .any(|id| !ids.contains(id.as_str()))
        {
            return Err(CoreError::new(
                "assurance judgment names unknown requirement",
            ));
        }
        if ["source_revision", "task_identity", "current_work"]
            .iter()
            .any(|key| input[*key] != judgment[*key])
        {
            judgment_gap = Some("assurance-applicability-judgment-stale");
        }
    }
    let mut rows = vec![];
    for requirement in requirements {
        let id = requirement["id"].as_str().unwrap();
        let mut reasons = vec![];
        let mut paths = BTreeSet::new();
        for path in strings(&input["changed_paths"]) {
            for pattern in strings(&requirement["applies_to_paths"]) {
                if crate::instruction_applicability::matches(pattern, path) {
                    reasons.push(format!("changed path matched {pattern}"));
                    paths.insert(path);
                }
            }
        }
        let mut planning_unknown = false;
        for (selector, fact, label) in [
            ("applies_to_planning_refs", "refs", "planning ref"),
            (
                "applies_to_proof_profiles",
                "proof_profiles",
                "proof profile",
            ),
            ("applies_to_risk_refs", "risk_refs", "risk ref"),
            (
                "applies_to_invariant_refs",
                "invariant_refs",
                "invariant ref",
            ),
        ] {
            let expected = strings(&requirement[selector]);
            if !expected.is_empty() && input["planning_facts"][fact].is_null() {
                planning_unknown = true;
            }
            for value in expected {
                if strings(&input["planning_facts"][fact]).contains(&value) {
                    reasons.push(format!("{label} matched {value}"));
                }
            }
        }
        let selectors = strings(&requirement["applies_to_semantic_routes"]);
        let posture = if input["route_fact"]["status"]
            .as_str()
            .is_some_and(|s| s != "current")
        {
            "unresolved"
        } else {
            input["route_fact"]["posture"]
                .as_str()
                .unwrap_or("unresolved")
        };
        if !selectors.is_empty() && posture == "selected" {
            let result = crate::instruction_applicability::view(
                json!({"paths":[],"routes":selectors,"changed_paths":[],"selected_routes":input["route_fact"]["routes"],"route_posture":"selected"}),
            )?;
            if result["applies"] == true {
                reasons.push("current semantic task route matched".into());
            }
        }
        let legacy = !strings(&requirement["applies_to_task_markers"]).is_empty()
            || strings(&requirement["applies_to_planning_refs"])
                .iter()
                .any(|r| strings(&input["planning_facts"]["legacy_refs"]).contains(r));
        let semantic_unknown = legacy
            || planning_unknown
            || (!selectors.is_empty() && !matches!(posture, "selected" | "none"));
        let answer = if judgment_gap.is_none() {
            judgment["decisions"][id].as_str()
        } else {
            None
        };
        let status = if !reasons.is_empty() {
            "applicable"
        } else if planning_unknown {
            "unresolved"
        } else if semantic_unknown {
            answer.unwrap_or("unresolved")
        } else {
            "not-applicable"
        };
        if reasons.is_empty() && semantic_unknown && answer.is_some() && !planning_unknown {
            reasons.push("current agent applicability judgment".into());
        }
        rows.push(json!({"id":id,"status":status,"applies_because":reasons,"matched_paths":paths,
            "legacy_scope":requirement["applies_to_task_markers"],"authority_refs":requirement["authority_refs"],
            "force":requirement["force"],"source_requirement":requirement,
            "blocking_claims":if strings(&requirement["blocking_claims"]).is_empty() && matches!(requirement["force"].as_str(),Some("blocking"|"required-before-closeout")) {json!(["claim-work-complete","close-parent-lane"])} else {requirement["blocking_claims"].clone()},
            "gap":if status=="unresolved" {judgment_gap.unwrap_or("assurance-semantic-scope-unresolved")} else {""}}));
    }
    Ok(
        json!({"kind":"agentic-workspace/assurance-applicability/v1","revision":digest(&input)?,"requirements":rows,
        "authority_boundary":"applicability-only; no waiver, evidence, execution or claim grants"}),
    )
}

pub(crate) fn declaration() -> Value {
    let schema = schema();
    json!({"kind":"verification/assurance-applicability/v1","result_kind":"agentic-workspace/assurance-applicability/v1",
        "input_schema":{"$schema":schema["$schema"],"$defs":schema["$defs"],"$ref":"#/$defs/arguments"}})
}

pub(crate) fn native_input(
    config: &Value,
    revision: &str,
    task: &str,
    changed: &[String],
    work: &Value,
    planning: Option<&Value>,
    context: &Value,
) -> Result<Value, CoreError> {
    let requirements: Vec<Value> = config["assurance"]["requirements"]
        .as_object()
        .into_iter()
        .flatten()
        .map(|(id, row)| {
            let mut row = row.clone();
            row["id"] = json!(id);
            row
        })
        .collect();
    // Consume exact facts already validated and preserved by Planning. Missing
    // owner declarations remain unknown, never guessed from prose or evidence.
    let absent = if context["planning"]["status"] == "direct" {
        json!({"refs":[],"proof_profiles":[],"risk_refs":[],"invariant_refs":[]})
    } else {
        json!({})
    };
    let facts = planning.map_or(absent, |subject| {
        let proof = &subject["state"]["proof"];
        let mut facts = json!({"refs":[subject["id"]]});
        for (field, value) in [
            (
                "proof_profiles",
                &proof["adaptive_assurance"]["proof_profiles"],
            ),
            ("risk_refs", &proof["risk_registry_refs"]),
            ("invariant_refs", &proof["invariant_refs"]),
        ] {
            if !value.is_null() {
                facts[field] = value.clone();
            }
        }
        facts
    });
    // Applicability consumes material identity and these projected facts, not
    // an owner's attempt/frontier or physical source revision. Recompute the
    // small semantic input instead of expiring judgment on unrelated state.
    let source_revision = digest(&json!({"source":revision,
        "planning":planning.map(|p| json!({"id":p["id"],"revision":p["revision"]})),
        "planning_facts":facts,"route_fact":context["route_fact"]}))?;
    Ok(
        json!({"requirements":requirements,"changed_paths":changed,"planning_facts":facts,"route_fact":context["route_fact"],
        "source_revision":source_revision,"task_identity":crate::direct_task::subject(task,changed)?,"current_work":work}),
    )
}

#[cfg(test)]
mod tests {
    use super::*;
    fn input() -> Value {
        json!({"requirements":[{"id":"r","applies_to_paths":["src/**"],"applies_to_task_markers":["proof"],"force":"blocking","blocking_claims":["claim-work-complete"]}],"changed_paths":[],"planning_facts":{},"route_fact":null,"source_revision":"s","task_identity":{"id":"task"},"current_work":{"id":"work","revision":"1"}})
    }
    #[test]
    fn exact_paths_settle_old_scope_without_judgment() {
        let mut i = input();
        i["changed_paths"] = json!(["src/a.rs"]);
        assert_eq!(view(i).unwrap()["requirements"][0]["status"], "applicable");
    }
    #[test]
    fn legacy_scope_is_unresolved_without_keyword_authority() {
        assert_eq!(
            view(input()).unwrap()["requirements"][0]["status"],
            "unresolved"
        );
    }
    #[test]
    fn bound_judgment_does_not_waive_exact_requirement() {
        let mut i = input();
        i["judgment"] = json!({"source_revision":"s","task_identity":i["task_identity"],"current_work":i["current_work"],"decisions":{"r":"not-applicable"}});
        assert_eq!(
            view(i.clone()).unwrap()["requirements"][0]["status"],
            "not-applicable"
        );
        i["changed_paths"] = json!(["src/a.rs"]);
        assert_eq!(
            view(i.clone()).unwrap()["requirements"][0]["status"],
            "applicable"
        );
        i["changed_paths"] = json!([]);
        i["current_work"]["revision"] = json!("2");
        assert_eq!(view(i).unwrap()["requirements"][0]["status"], "unresolved");
    }
    #[test]
    fn unknown_judgment_id_is_rejected() {
        let mut i = input();
        i["judgment"] = json!({"source_revision":"s","task_identity":i["task_identity"],"current_work":i["current_work"],"decisions":{"unknown":"not-applicable"}});
        assert!(view(i).is_err());
    }
    #[test]
    fn planning_owner_gap_cannot_be_answered_away() {
        let mut i = input();
        i["requirements"][0]["applies_to_risk_refs"] = json!(["risk:boundary"]);
        i["judgment"] = json!({"source_revision":"s","task_identity":i["task_identity"],"current_work":i["current_work"],"decisions":{"r":"not-applicable"}});
        assert_eq!(
            view(i.clone()).unwrap()["requirements"][0]["status"],
            "unresolved"
        );
        i["planning_facts"]["risk_refs"] = json!(["risk:boundary"]);
        assert_eq!(view(i).unwrap()["requirements"][0]["status"], "applicable");
    }
    #[test]
    fn enforcing_default_claims_survive_projection() {
        let mut i = input();
        i["requirements"][0]
            .as_object_mut()
            .unwrap()
            .remove("blocking_claims");
        assert_eq!(
            view(i).unwrap()["requirements"][0]["blocking_claims"],
            json!(["claim-work-complete", "close-parent-lane"])
        );
    }
}
