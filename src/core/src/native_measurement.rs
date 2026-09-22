//! Finite measurement admission from current native proof output, not labels or
//! caller-reported receipts. The existing proof owner retains all evidence.
use serde_json::{Value, json};

pub(crate) fn observations(detail: &Value) -> Value {
    let stream = &detail["output"]["stdout"];
    if detail["status"] != "passed" || stream["truncated"] != false {
        return Value::Null;
    }
    let parsed = stream["tail"]
        .as_str()
        .and_then(|text| serde_json::from_str::<Value>(text).ok());
    parsed
        .filter(|v| {
            v["kind"] == "agentic-workspace/assurance-evidence-records/v1"
                && v["records"].as_array().is_some_and(|rows| rows.len() <= 64)
        })
        .unwrap_or(Value::Null)
}

fn assess(requirement: &Value, record: &Value) -> Result<Value, String> {
    let condition = &requirement["measurement"];
    let result = &record["measurement"];
    if result["kind"] != "agentic-workspace/measurement-evidence/v1" {
        return Err("measurement-evidence-contract-unsupported".into());
    }
    if result["status"] != "passed" {
        return Err("measurement-producer-result-not-passed".into());
    }
    for field in [
        "metric",
        "unit",
        "comparator",
        "threshold",
        "aggregation",
        "subject",
        "subject_revision",
        "environment",
        "source_revision",
    ] {
        if result[field] != condition[field] {
            return Err(format!("measurement-{field}-mismatch"));
        }
    }
    if result["requirement_revision"] != requirement["source_intent_revision"] {
        return Err("measurement-requirement-revision-mismatch".into());
    }
    let count = result["sample_count"]
        .as_u64()
        .filter(|n| *n >= condition["minimum_samples"].as_u64().unwrap_or(u64::MAX))
        .ok_or("measurement-minimum-samples-not-met")?;
    let mut value = result["observed_value"]
        .as_f64()
        .filter(|v| v.is_finite())
        .ok_or("measurement-observation-invalid")?;
    let comparator = condition["comparator"].as_str().unwrap_or("");
    if comparator.starts_with("ratio-") {
        for field in ["control_subject", "control_revision"] {
            if result[field] != condition[field] {
                return Err(format!("measurement-{field}-mismatch"));
            }
        }
        let baseline = result["baseline_value"]
            .as_f64()
            .filter(|v| v.is_finite() && *v != 0.0)
            .ok_or("measurement-baseline-invalid")?;
        value /= baseline;
    }
    if !value.is_finite() {
        return Err("measurement-observation-invalid".into());
    }
    let threshold = condition["threshold"]
        .as_f64()
        .ok_or("measurement-threshold-invalid")?;
    let tolerance = condition["tolerance"].as_f64().unwrap_or(0.0);
    let passed = match comparator {
        "lte" | "ratio-lte" => value <= threshold + tolerance,
        "gte" | "ratio-gte" => value >= threshold - tolerance,
        "eq" => (value - threshold).abs() <= tolerance,
        _ => return Err("measurement-comparator-unsupported".into()),
    };
    if !passed {
        return Err("measurement-threshold-not-met".into());
    }
    Ok(
        json!({"evaluated_value":value,"sample_count":count,"metric":condition["metric"],"unit":condition["unit"],"aggregation":condition["aggregation"]}),
    )
}

pub(crate) fn admit(row: &Value, evidence: &[Value]) -> Value {
    let requirement = &row["source_requirement"];
    let condition = &requirement["measurement"];
    if condition.is_null() || row["status"] == "not-applicable" {
        return Value::Null;
    }
    let mut gap = "measurement-current-native-producer-evidence-unavailable".to_owned();
    if row["status"] != "applicable" {
        gap = "measurement-applicability-unresolved".into();
    } else {
        for item in evidence {
            if item["checked_scope"]["claim"] != "selected-command-passed"
                || item["runtime_admission"]["command_coverage"]["command"]
                    != condition["producer_command"]
            {
                continue;
            }
            let candidates: Vec<_> = item["measurement_observations"]["records"]
                .as_array()
                .into_iter()
                .flatten()
                .filter(|r| {
                    r["requirement_id"] == row["id"]
                        && r["evidence_label"] == condition["evidence_label"]
                })
                .collect();
            if candidates.len() != 1 {
                gap = "measurement-exact-observation-unavailable-or-ambiguous".into();
                continue;
            }
            match assess(requirement, candidates[0]) {
                Ok(value) => {
                    return json!({"requirement_id":row["id"],"status":"current-measurement-satisfied","evidence_label":condition["evidence_label"],"evidence_ref":item["reference"],"observation":value,"completion_authority":false,"boundary":"Only the declared compact producer measurement; source reconciliation, other evidence and independent review remain separate."});
                }
                Err(reason) => gap = reason,
            }
        }
    }
    json!({"requirement_id":row["id"],"status":"measurement-not-admitted","gap":gap,"repair":"Select the current producer and supply its complete exact compact measurement through native proof output.","completion_authority":false})
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn comparisons_use_source_bounds_and_exact_relative_identity() {
        let mut condition = json!({"metric":"latency","unit":"seconds","comparator":"ratio-lte","threshold":1.2,"tolerance":0.01,"aggregation":"ratio","minimum_samples":5,"subject":"loaded","subject_revision":"1","environment":"fixture","source_revision":"method1","control_subject":"empty","control_revision":"1"});
        let mut observation = condition.clone();
        observation["kind"] = json!("agentic-workspace/measurement-evidence/v1");
        observation["sample_count"] = json!(5);
        observation["observed_value"] = json!(1.2);
        observation["baseline_value"] = json!(1.0);
        observation["requirement_revision"] = json!("policy1");
        observation["status"] = json!("passed");
        let check = |condition: &Value, observation: &Value| {
            assess(
                &json!({"measurement":condition,"source_intent_revision":"policy1"}),
                &json!({"measurement":observation}),
            )
        };
        assert!(check(&condition, &observation).is_ok());
        observation["baseline_value"] = json!(0);
        assert_eq!(
            check(&condition, &observation).unwrap_err(),
            "measurement-baseline-invalid"
        );
        observation["baseline_value"] = json!(1.0);
        observation["control_revision"] = json!("old");
        assert_eq!(
            check(&condition, &observation).unwrap_err(),
            "measurement-control_revision-mismatch"
        );
        for (comparator, observed, expected) in [
            ("eq", 1.2, true),
            ("eq", 2.0, false),
            ("gte", 2.0, true),
            ("gte", 1.0, false),
        ] {
            condition["comparator"] = json!(comparator);
            observation["comparator"] = json!(comparator);
            observation["observed_value"] = json!(observed);
            assert_eq!(check(&condition, &observation).is_ok(), expected);
        }
        observation["sample_count"] = json!(true);
        assert_eq!(
            check(&condition, &observation).unwrap_err(),
            "measurement-minimum-samples-not-met"
        );
    }
}
