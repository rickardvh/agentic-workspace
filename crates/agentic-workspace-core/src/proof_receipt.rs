//! Receipt shape admission is separate from publication, freshness and claims.
//! Timestamp decoding is a host codec observation, never producer authority.
use crate::CoreError;
use serde_json::{Value, json};
use sha2::{Digest, Sha256};

pub fn assignment_binding(receipt: &Value) -> Result<String, CoreError> {
    let mut paths: Vec<String> = receipt["changed_paths"]
        .as_array()
        .into_iter()
        .flatten()
        .map(|path| {
            path.as_str()
                .map(str::to_owned)
                .unwrap_or_else(|| path.to_string())
        })
        .filter(|path| !path.is_empty())
        .collect();
    paths.sort();
    let value = json!({"assignment_proof_obligation":receipt["assignment_proof_obligation"],
        "proof_subject_fingerprint":receipt["proof_subject"]["fingerprint"], "command":receipt["command"],
        "result":receipt["result"], "changed_paths":paths, "authority":receipt["authority"],"producer_class":receipt["producer_class"]});
    Ok(format!(
        "sha256:{:x}",
        Sha256::digest(crate::proof_subject::compact_json(&value)?.as_bytes())
    ))
}

fn text(value: &Value) -> String {
    match value {
        Value::Null => String::new(),
        Value::String(value) => value.clone(),
        Value::Bool(false) => String::new(),
        Value::Bool(true) => "True".into(),
        Value::Number(value) if value.as_f64() == Some(0.0) => String::new(),
        _ => value.to_string(),
    }
}

fn unresolved(command: &str) -> bool {
    [("<", ">"), ("{{", "}}"), ("${", "}")]
        .iter()
        .any(|(open, close)| {
            command.split(open).skip(1).any(|tail| {
                tail.split_once(close).is_some_and(|(body, _)| {
                    !body.is_empty()
                        && !body.contains(['\r', '\n'])
                        && !body
                            .chars()
                            .any(|ch| open.contains(ch) || close.contains(ch))
                })
            })
        })
}

pub fn result(value: &Value) -> Value {
    let observed = text(value).trim().to_lowercase();
    let class = match observed.as_str() {
        "passed" | "pass" | "success" | "succeeded" => "passed",
        "failed" | "fail" | "failure" | "error" => "failed",
        "skipped" | "skip" => "skipped",
        "waived" | "waive" => "waived",
        _ => "",
    };
    json!({"admitted":!class.is_empty(),"observed_result":observed,"result_class":class,"proof_sufficient":class=="passed"})
}

pub fn command(value: &Value) -> Value {
    let value = text(value);
    let (reason, recovery) = if value.trim().is_empty() {
        (
            "missing-command",
            "Supply the exact command that was executed with --receipt-command.",
        )
    } else if unresolved(value.trim()) {
        (
            "unresolved-command-template",
            "Substitute every placeholder, execute the concrete command, then record that exact command.",
        )
    } else {
        ("admissible", "none")
    };
    json!({"admitted":reason=="admissible","reason":reason,"safe_recovery":recovery})
}

pub fn admit(receipt: &Value, timestamp_valid: bool, assignment_binding: Option<&str>) -> Value {
    let mut failures = Vec::new();
    let mut reject = |reason: &str, field: &str, recovery: &str| {
        failures.push(json!({"reason":reason,"field":field,"recovery":recovery}));
    };
    if receipt["kind"] != "agentic-workspace/proof-receipt/v1" {
        reject(
            "unsupported-receipt-kind",
            "kind",
            "Record evidence through `agentic-workspace proof --record-receipt`.",
        );
    }
    let command = command(&receipt["command"]);
    if command["admitted"] != true {
        reject(
            command["reason"].as_str().unwrap(),
            "command",
            command["safe_recovery"].as_str().unwrap(),
        );
    }
    let result = result(&receipt["result"]);
    if result["observed_result"] == "" {
        reject(
            "missing-result",
            "result",
            "Supply the observed result with --receipt-result.",
        );
    } else if result["admitted"] != true {
        reject(
            "unsupported-result",
            "result",
            "Use an admitted result class: passed, failed, skipped, or waived.",
        );
    }
    if !timestamp_valid {
        reject(
            "invalid-recorded-at",
            "recorded_at",
            "Record the receipt again so AW supplies an ISO-8601 timestamp with timezone.",
        );
    }
    match receipt["changed_paths"].as_array() {
        Some(paths) if !paths.is_empty() => {
            if paths
                .iter()
                .any(|path| text(path).trim().is_empty() || unresolved(text(path).trim()))
            {
                reject(
                    "invalid-changed-path-scope",
                    "changed_paths",
                    "Replace empty or templated --changed values with concrete repo-relative paths.",
                );
            }
        }
        _ => reject(
            "missing-changed-path-scope",
            "changed_paths",
            "Pass one or more concrete --changed paths matching the proof scope.",
        ),
    }
    if !receipt["assignment_proof_obligation"].is_null() {
        if receipt["assignment_proof_obligation"]["kind"]
            != "agentic-workspace/assignment-task-proof-obligation/v1"
        {
            reject(
                "invalid-assignment-proof-obligation",
                "assignment_proof_obligation",
                "Record assignment proof through the AW proof producer while the exact run is integrated.",
            );
        }
        if receipt["producer_class"] != "aw-proof" || receipt["authority"] != "aw-proof" {
            reject(
                "assignment-proof-not-aw-owned",
                "producer_class|authority",
                "Record assignment proof through the AW proof producer.",
            );
        }
        if assignment_binding.is_none()
            || receipt["assignment_proof_binding"].as_str() != assignment_binding
        {
            reject(
                "assignment-proof-binding-mismatch",
                "assignment_proof_binding",
                "Record the proof again against the current integrated assignment.",
            );
        }
    }
    let admitted = failures.is_empty();
    json!({"kind":"agentic-workspace/proof-receipt-admission/v1","status":if admitted {"admitted"} else {"rejected"},
        "admitted":admitted,"result_class":result["result_class"],"proof_sufficient":admitted && result["proof_sufficient"]==true,
        "reason":failures.first().map(|f| f["reason"].clone()).unwrap_or(json!("admissible")),
        "safe_recovery":failures.first().map(|f| f["recovery"].clone()).unwrap_or(json!("none")),"failures":failures,
        "rule":"Only admitted receipts may be persisted, selected, or counted as trusted proof state."})
}

pub fn view(value: Value) -> Result<Value, CoreError> {
    let declaration: Value = serde_json::from_str(include_str!(
        "../../../src/agentic_workspace/contracts/schemas/source_decision_input.schema.json"
    ))
    .expect("checked schema");
    let schema = json!({"$schema":declaration["$schema"],"$defs":declaration["$defs"],"$ref":"#/$defs/proof_receipt_input"});
    crate::schema_validator(&schema, "proof receipt admission")?
        .validate(&value)
        .map_err(|error| CoreError::new(error.to_string()))?;
    match value["action"].as_str() {
        Some("admit-many") => {
            let mut results = Vec::new();
            for item in value["items"].as_array().unwrap() {
                let binding = assignment_binding(&item["receipt"])?;
                results.push(admit(
                    &item["receipt"],
                    item["timestamp_valid"] == true,
                    Some(&binding),
                ));
            }
            Ok(json!({"items":results}))
        }
        Some("result") => Ok(result(&value["value"])),
        Some("command") => Ok(command(&value["value"])),
        Some("binding") => Ok(json!({"binding":assignment_binding(&value["receipt"])?})),
        Some("admit") => {
            let binding = assignment_binding(&value["receipt"])?;
            Ok(admit(
                &value["receipt"],
                value["timestamp_valid"] == true,
                Some(&binding),
            ))
        }
        _ => Err(CoreError::new(
            "unsupported proof receipt admission request",
        )),
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn original_python_receipt_admission_vectors() {
        let fixture: Value = serde_json::from_str(include_str!(
            "../../../tests/fixtures/proof_receipt_admission.json"
        ))
        .unwrap();
        for case in fixture["cases"].as_array().unwrap() {
            let valid_time = case["receipt"]["recorded_at"]
                .as_str()
                .and_then(|value| value.parse::<toml::value::Datetime>().ok())
                .is_some_and(|value| {
                    value.date.is_some() && value.time.is_some() && value.offset.is_some()
                });
            assert_eq!(
                view(
                    json!({"action":"admit","receipt":case["receipt"],"timestamp_valid":valid_time})
                )
                .unwrap(),
                case["expected"]
            );
        }
        assert_eq!(
            assignment_binding(&fixture["assignment_binding"]["receipt"]).unwrap(),
            fixture["assignment_binding"]["expected"]
        );
    }

    #[test]
    fn supplied_binding_cannot_replace_derived_assignment_identity() {
        assert!(view(json!({"action":"admit","receipt":{},"timestamp_valid":true,"assignment_binding":"invented"})).is_err());
        let receipt = json!({"kind":"agentic-workspace/proof-receipt/v1","command":"make test","result":"passed",
            "changed_paths":["a.txt"],"assignment_proof_obligation":{"kind":"agentic-workspace/assignment-task-proof-obligation/v1"},
            "producer_class":"aw-proof","authority":"aw-proof","assignment_proof_binding":"invented"});
        let result =
            view(json!({"action":"admit","receipt":receipt,"timestamp_valid":true})).unwrap();
        assert_eq!(result["reason"], "assignment-proof-binding-mismatch");
        assert_eq!(result["proof_sufficient"], false);
    }
}
