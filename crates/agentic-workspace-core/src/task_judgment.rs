//! Exact task judgment matching. Host observations do not become public authority.
use crate::CoreError;
use serde_json::{Value, json};

fn task_identity(input: &Value) -> Result<Value, CoreError> {
    let paths = input["changed_paths"]
        .as_array()
        .unwrap()
        .iter()
        .map(|v| v.as_str().unwrap().to_owned())
        .collect::<Vec<_>>();
    crate::direct_task::subject(input["task"].as_str().unwrap(), &paths)
}
fn task_bound(input: &Value, receipt: &Value, task_identity: &Value) -> bool {
    let judgment = &receipt["task_claim_judgment"];
    match judgment.get("task_identity") {
        Some(identity) => identity == task_identity,
        None => {
            judgment["work_ref"] == task_identity["id"]
                && judgment["work_revision"] == task_identity["id"]
                && input["work_ref"] == task_identity["id"]
                && input["work_revision"] == task_identity["id"]
        }
    }
}
fn candidate(input: &Value, receipt: &Value) -> bool {
    let judgment = &receipt["task_claim_judgment"];
    !input["task"]
        .as_str()
        .unwrap_or("")
        .trim_matches(|c: char| c.is_whitespace() || ('\u{1c}'..='\u{1f}').contains(&c))
        .is_empty()
        && !input["work_ref"].as_str().unwrap_or("").is_empty()
        && !input["work_revision"].as_str().unwrap_or("").is_empty()
        && judgment["work_ref"] == input["work_ref"]
        && judgment["work_revision"] == input["work_revision"]
        && judgment["claim_class"] == "slice_complete"
        && judgment["status"] == "sufficient"
}
fn fingerprint(value: &Value) -> bool {
    value.as_str().is_some_and(|s| {
        s.len() == 64
            && s.bytes()
                .all(|c| c.is_ascii_digit() || (b'a'..=b'f').contains(&c))
    })
}

pub fn view(input: Value) -> Result<Value, CoreError> {
    let schema: Value = serde_json::from_str(include_str!(
        "../../../src/agentic_workspace/contracts/schemas/source_decision_input.schema.json"
    ))
    .expect("checked schema");
    let mut shape = schema["$defs"]["task_judgment_input"].clone();
    shape["$schema"] = schema["$schema"].clone();
    crate::schema_validator(&shape, "task judgment")?
        .validate(&input)
        .map_err(|e| {
            CoreError::new(format!(
                "invalid task judgment input at {}",
                e.instance_path()
            ))
        })?;
    if input["action"] == "summarize" {
        let batches = input["batches"].as_array().unwrap();
        let current = batches
            .iter()
            .map(|v| v["current_judgment_count"].as_u64().unwrap())
            .sum::<u64>();
        let matched = batches
            .iter()
            .map(|v| v["matched_judgment_count"].as_u64().unwrap())
            .sum::<u64>();
        let classifications = batches
            .iter()
            .flat_map(|v| v["classifications"].as_array().unwrap().clone())
            .collect::<Vec<_>>();
        return Ok(summary(
            current,
            matched,
            classifications,
            batches.iter().any(|v| v["manual_missing"] == true),
            batches.iter().any(|v| v["independent_missing"] == true),
        ));
    }
    let task_identity = task_identity(&input)?;
    if input["action"] == "candidates" {
        return Ok(
            json!({"indices":input["receipts"].as_array().unwrap().iter().enumerate().filter_map(|(i,r)|(candidate(&input,r) && task_bound(&input,r,&task_identity)).then_some(i)).collect::<Vec<_>>() }),
        );
    }
    let mut matched = 0;
    let mut current = 0;
    let mut classifications = Vec::new();
    for observation in input["observations"].as_array().unwrap() {
        let receipt = &observation["receipt"];
        let mut reasons = Vec::new();
        if !candidate(&input, receipt) {
            reasons.push("task-claim-mismatch-or-missing-identity");
        }
        if !task_bound(&input, receipt, &task_identity) {
            reasons.push("exact-task-request-identity-mismatch");
        }
        if observation["publication_current"] != true {
            reasons.push("current-producer-publication-missing");
        }
        let stored = &receipt["proof_subject"]["fingerprint"];
        let judgment = &receipt["task_claim_judgment"]["proof_subject_fingerprint"];
        if !fingerprint(stored) || !fingerprint(judgment) {
            reasons.push("proof-subject-fingerprint-invalid");
        } else if stored != judgment {
            reasons.push("task-judgment-proof-subject-binding-mismatch");
        }
        if observation["proof_sufficient"] != true {
            reasons.push("receipt-proof-insufficient");
        }
        let is_matched = reasons.is_empty();
        if is_matched {
            matched += 1;
        }
        if observation["evidence_freshness"] != "reusable" {
            reasons.push("proof-evidence-freshness-unresolved");
        }
        let is_current = reasons.is_empty();
        if is_current {
            current += 1;
        }
        classifications.push(json!({"matched":is_matched,"current":is_current,"reasons":reasons}));
    }
    let independent_missing = input["independent_required"] == true
        && !matches!(
            input["independent_status"].as_str(),
            Some("not-applicable" | "satisfied")
        );
    let manual_missing = input["manual_required"] == true
        && !matches!(
            input["manual_status"].as_str(),
            Some("passed" | "accepted" | "satisfied" | "not-required")
        );
    Ok(summary(
        current,
        matched,
        classifications,
        manual_missing,
        independent_missing,
    ))
}

fn summary(
    current: u64,
    matched: u64,
    classifications: Vec<Value>,
    manual_missing: bool,
    independent_missing: bool,
) -> Value {
    let status = if independent_missing {
        "independent-review-required"
    } else if manual_missing {
        "manual-evidence-required"
    } else if current > 0 {
        "accepted"
    } else {
        "task-judgment-required"
    };
    json!({"status":status,"current_judgment_count":current,"matched_judgment_count":matched,
        "classifications":classifications,"manual_missing":manual_missing,"independent_missing":independent_missing})
}

#[cfg(test)]
mod tests {
    use super::*;
    fn input() -> Value {
        let hash = "a".repeat(64);
        let task_identity = crate::direct_task::subject("Current task", &[]).unwrap();
        json!({"action":"classify","task":"Current task","changed_paths":[],"work_ref":"direct-task:current","work_revision":"current",
        "observations":[{"receipt":{"task_claim_judgment":{"work_ref":"direct-task:current","work_revision":"current","claim_class":"slice_complete","status":"sufficient","task_identity":task_identity,"proof_subject_fingerprint":hash},"proof_subject":{"fingerprint":hash}},"publication_current":true,"proof_sufficient":true,"evidence_freshness":"reusable"}],
        "manual_required":false,"manual_status":"","independent_required":false,"independent_status":""})
    }
    #[test]
    fn exact_judgment_keeps_publication_freshness_and_review_separate() {
        assert_eq!(view(input()).unwrap()["status"], "accepted");
        let mut value = input();
        value["observations"][0]["evidence_freshness"] = json!("unproven");
        let result = view(value).unwrap();
        assert_eq!(result["matched_judgment_count"], 1);
        assert_eq!(result["current_judgment_count"], 0);
        let mut value = input();
        value["independent_required"] = json!(true);
        assert_eq!(
            view(value).unwrap()["status"],
            "independent-review-required"
        );
    }
    #[test]
    fn different_tasks_in_same_planning_owner_cannot_share_a_judgment() {
        let mut value = input();
        value["task"] = json!("A different task in the same Planning owner");
        assert_eq!(view(value).unwrap()["matched_judgment_count"], 0);
        let mut value = input();
        value["changed_paths"] = json!(["another-path"]);
        assert_eq!(view(value).unwrap()["matched_judgment_count"], 0);
        let mut value = input();
        value["observations"][0]["receipt"]["task_claim_judgment"]
            .as_object_mut()
            .unwrap()
            .remove("task_identity");
        assert_eq!(view(value).unwrap()["matched_judgment_count"], 0);
        let mut value = input();
        value["task"] = json!("Current   task");
        assert_eq!(view(value).unwrap()["matched_judgment_count"], 1);
    }
    #[test]
    fn legacy_direct_work_already_binds_task_but_explicit_invalid_identity_never_falls_back() {
        let mut value = input();
        let identity = crate::direct_task::subject("Current task", &[]).unwrap();
        value["work_ref"] = identity["id"].clone();
        value["work_revision"] = identity["revision"].clone();
        let judgment = &mut value["observations"][0]["receipt"]["task_claim_judgment"];
        judgment["work_ref"] = identity["id"].clone();
        judgment["work_revision"] = identity["revision"].clone();
        judgment.as_object_mut().unwrap().remove("task_identity");
        assert_eq!(view(value.clone()).unwrap()["matched_judgment_count"], 1);
        value["observations"][0]["receipt"]["task_claim_judgment"]["task_identity"] = Value::Null;
        assert_eq!(view(value).unwrap()["matched_judgment_count"], 0);
    }
    #[test]
    fn invalid_identity_cannot_match_itself() {
        for hash in [Value::Null, json!(""), json!("not-a-digest")] {
            let mut value = input();
            value["observations"][0]["receipt"]["proof_subject"]["fingerprint"] = hash.clone();
            value["observations"][0]["receipt"]["task_claim_judgment"]["proof_subject_fingerprint"] =
                hash;
            assert_eq!(view(value).unwrap()["matched_judgment_count"], 0);
        }
        let mut value = input();
        value["work_revision"] = json!("other");
        assert_eq!(view(value).unwrap()["current_judgment_count"], 0);
        let mut value = input();
        value["observations"][0]["publication_current"] = json!(false);
        assert_eq!(view(value).unwrap()["matched_judgment_count"], 0);
    }
}
