//! A bounded disposition of an explicit observable candidate. No transcript
//! inference, event store, automatic retention or additional publication owner.
use crate::{CoreError, digest};
use serde_json::{Value, json};
use std::path::Path;

pub(crate) const KIND: &str = "memory/dispose-future-value/v1";
fn err(e: impl ToString) -> CoreError {
    CoreError::new(e.to_string())
}

pub(crate) fn signal(detail: &Value) -> Value {
    let stdout = &detail["output"]["stdout"];
    if stdout["truncated"] != false {
        return Value::Null;
    }
    let Some(text) = stdout["tail"].as_str().filter(|s| s.len() <= 8192) else {
        return Value::Null;
    };
    let Ok(value) = serde_json::from_str::<Value>(text) else {
        return Value::Null;
    };
    let candidate = &value["future_value_candidate"];
    if candidate.as_object().is_none_or(|o| o.len() != 2)
        || ["lesson", "rationale"].iter().any(|k| {
            candidate[*k]
                .as_str()
                .is_none_or(|s| s.trim().is_empty() || s.len() > 2048)
        })
    {
        return Value::Null;
    }
    candidate.clone()
}

pub(crate) fn declaration() -> Value {
    let text = json!({"type":"string","minLength":1,"maxLength":2048});
    json!({"kind":KIND,"result_kind":"agentic-memory/future-value-disposition/v1","input_schema":{
        "$schema":"https://json-schema.org/draft/2020-12/schema","type":"object","additionalProperties":false,
        "properties":{"candidate_revision":text,"disposition":{"enum":["unresolved","advisory-memory","stronger-owner","already-absorbed","no-retention"]},
        "lesson":text,"reason":text,"receiving_source":{"type":"object","additionalProperties":false,"properties":{"reference":text,"revision":text},"required":["reference","revision"]},
        "receiving_consequence":{"type":"object","additionalProperties":false,"required":["claim","evidence_reference","proof_subject"],
            "properties":{"claim":text,"evidence_reference":text,"proof_subject":text}},
        "candidate_evidence_requests":{"type":"array","maxItems":8,"items":{"type":"object"}}},
        "required":["candidate_revision","disposition","lesson","reason","candidate_evidence_requests"]}})
}

/// Verification owns command admission/currentness. The acting agent judges
/// what the current check establishes; Memory cannot infer behaviour from prose.
fn receiving_consequence(args: &Value, verification: &Value) -> Result<Value, CoreError> {
    let consequence = &args["receiving_consequence"];
    if !consequence.is_object() {
        return Err(err(
            "stronger-owner absorption requires a bounded consequence and current receiving-source proof; copied lesson text is insufficient",
        ));
    }
    let evidence = verification["evidence"].as_array().into_iter().flatten().find(|e|
        e["reference"] == consequence["evidence_reference"]
            && e["proof_subject"] == consequence["proof_subject"]
            && e["checked_scope"]["claim"] == "selected-command-passed"
            && e["checked_scope"]["source_inputs"].as_array().into_iter().flatten().any(|s|
                s["path"] == args["receiving_source"]["reference"])
    ).ok_or_else(|| err("receiving consequence needs current Verification evidence bound to the exact receiving source"))?;
    Ok(
        json!({"claim":consequence["claim"],"evidence_reference":evidence["reference"],
        "proof_subject":evidence["proof_subject"],"checked_scope":evidence["checked_scope"],
        "semantic_basis":"acting-agent judgment of the claimed consequence; selected-command success alone is not semantic equivalence or completion"}),
    )
}

/// Exact Verification prerequisites travel with the disposition/authorization,
/// including handoff or fresh-process reentry. Each owner revalidates them.
pub(crate) fn prerequisites(request: &Value) -> Result<Vec<Value>, CoreError> {
    let Some(values) = request["arguments"].get("candidate_evidence_requests") else {
        return Ok(vec![]);
    };
    if request["owner"] != "memory"
        || !matches!(
            request["request_kind"].as_str(),
            Some(KIND | crate::native_memory_capture::ADVISORY_CAPTURE)
        )
    {
        return Err(err(
            "candidate prerequisites belong to their Memory disposition",
        ));
    }
    let values = values
        .as_array()
        .filter(|a| a.len() <= 8)
        .ok_or_else(|| err("candidate evidence requests exceed their bound"))?;
    if values.iter().any(|r| r["owner"] != "verification") {
        return Err(err(
            "candidate evidence must use exact Verification requests",
        ));
    }
    Ok(values.clone())
}

#[allow(clippy::too_many_arguments)] // Current owner views; no persisted aggregate state.
pub(crate) fn view(
    target: &Path,
    work: &Value,
    changed: &[String],
    config: &Value,
    contract: &Value,
    verification: &Value,
    memory: &Value,
    decision_context: &Value,
    requests: &[Value],
) -> Result<Value, CoreError> {
    let candidates: Vec<_> = verification["evidence"]
        .as_array()
        .into_iter()
        .flatten()
        .filter(|e| e["future_value_candidate"].is_object())
        .collect();
    let selected = requests
        .iter()
        .find(|r| r["owner"] == "memory" && r["request_kind"] == KIND);
    if candidates.is_empty() {
        if selected.is_some() {
            return Err(err("future-value candidate source is unavailable or stale"));
        }
        return Ok(Value::Null);
    }
    let owner = contract["owners"]
        .as_array()
        .unwrap()
        .iter()
        .find(|o| o["owner"] == "memory")
        .unwrap();
    let evidence_requests: Vec<_> = requests
        .iter()
        .filter(|r| r["owner"] == "verification")
        .cloned()
        .collect();
    let source_revision = digest(&json!([
        work,
        candidates
            .iter()
            .map(|e| json!([
                e["reference"],
                e["proof_subject"],
                e["future_value_candidate"]
            ]))
            .collect::<Vec<_>>()
    ]))?;
    if selected.is_some_and(|r| r["source_revision"] != source_revision) {
        return Err(err("future-value source set changed"));
    }
    let mut decisions = Vec::new();
    let mut dispositions = Vec::new();
    let actions: Vec<Value> = Vec::new();
    for evidence in candidates {
        let candidate = &evidence["future_value_candidate"];
        let revision = digest(&json!([
            work,
            evidence["reference"],
            evidence["proof_subject"],
            candidate
        ]))?;
        let id = format!("observed-{}", revision.trim_start_matches("sha256:"));
        // The existing publication owner handles the exact follow-up answer.
        if requests.iter().any(|r| {
            r["request_kind"] == crate::native_memory_capture::ADVISORY_CAPTURE
                && r["arguments"]["material"]["id"] == id
        }) {
            return Ok(Value::Null);
        }
        let template = json!({"kind":"agentic-workspace/public-request/v1","id":KIND,"owner":"memory","owner_revision":owner["revision"],
            "source_revision":source_revision,"capability_revision":contract["revision"],"task_identity":work,"request_kind":KIND,
            "arguments":{"candidate_revision":revision,"disposition":"unresolved","lesson":candidate["lesson"],"reason":candidate["rationale"],"candidate_evidence_requests":evidence_requests}});
        let current = selected.filter(|r| r["arguments"]["candidate_revision"] == revision);
        if let Some(request) = current {
            crate::prepare_request_value(
                json!({"request":request,"current_work":work,"capability_contract":contract}),
            )?;
            if request["source_revision"] != source_revision {
                return Err(err("future-value disposition is stale"));
            }
            let args = &request["arguments"];
            match args["disposition"].as_str().unwrap() {
                "no-retention" => {
                    dispositions.push(json!({"candidate_revision":revision,"status":"not-retained","retained":false}));
                    continue;
                }
                "stronger-owner" | "already-absorbed" => {
                    let receiver = &args["receiving_source"];
                    let reference = receiver["reference"].as_str().ok_or_else(|| {
                        err("stronger-owner disposition needs exact receiving source evidence")
                    })?;
                    crate::decision_source::relative(reference)?;
                    if reference.starts_with(".agentic-workspace/memory/") {
                        return Err(err("Memory is not a stronger receiving owner"));
                    }
                    let root =
                        cap_std::fs::Dir::open_ambient_dir(target, cap_std::ambient_authority())
                            .map_err(err)?;
                    let bytes = crate::native_planning::read(&root, reference)?
                        .ok_or_else(|| err("receiving source missing"))?;
                    if crate::decision_source::hash(&bytes) != receiver["revision"] {
                        return Err(err("receiving source changed"));
                    }
                    let consequence = receiving_consequence(args, verification)?;
                    dispositions.push(json!({"candidate_revision":revision,"status":args["disposition"],"receiving_source":receiver,"reason":args["reason"],"retained":false,
                        "receiving_consequence":consequence,
                        "authority":"bounded semantic disposition supported by current Verification evidence; no source admission, authorship, policy, learned-skill promotion, independent review or completion grant"}));
                    continue;
                }
                "advisory-memory" => {
                    if verification["evidence"]
                        .as_array()
                        .into_iter()
                        .flatten()
                        .filter(|e| e["future_value_candidate"].is_object())
                        .count()
                        != 1
                    {
                        return Err(err(
                            "Multiple explicit candidates remain; narrow the current evidence to one disposition before publication, preserving the other candidate references",
                        ));
                    }
                    let mut capture = memory["advisory_capture"]["requests"][0].clone();
                    if !capture.is_object() {
                        return Err(err("current advisory publication is unavailable"));
                    }
                    capture["arguments"] = json!({"material":{"id":id,"lesson":args["lesson"],"rationale":args["reason"],"dependency_paths":changed},"candidate_evidence_requests":evidence_requests});
                    let scope: Vec<_> = changed.iter().map(|p| format!("path:{p}")).collect();
                    let mut proposed = crate::native_memory_capture::view_for(
                        target,
                        work,
                        &scope,
                        config,
                        contract,
                        (
                            crate::native_memory_capture::Destination::Advisory,
                            decision_context,
                        ),
                        Some(&capture),
                    )?;
                    proposed["contribution"]["settled"] = json!(false);
                    proposed["remaining_candidates"] = json!(verification["evidence"].as_array().into_iter().flatten().filter(|e| e["future_value_candidate"].is_object() && e["reference"] != evidence["reference"]).map(|e| json!({"reference":e["reference"],"candidate":e["future_value_candidate"]})).collect::<Vec<_>>());
                    return Ok(proposed);
                }
                _ => {}
            }
        }
        decisions.push(json!({"id":format!("future-value:{revision}"),"question":"Does this explicit observation have future decision value? Choose the strongest owner, advisory Memory, or no retention; supply only the unresolved lesson/materiality judgment.",
            "material":{"candidate":candidate,"source_receipt":evidence["reference"],"candidate_revision":revision,"authority":"untrusted producer suggestion; not evidence of durable value or permission to retain"},
            "response_request":{"request_kind":KIND,"arguments":template["arguments"]},"affects":["claim:complete"]}));
    }
    if selected.is_some() && dispositions.is_empty() && decisions.is_empty() {
        return Err(err(
            "candidate disposition no longer names current material",
        ));
    }
    Ok(
        json!({"status":if decisions.is_empty(){"disposition-returned"}else{"judgment-required"},"dispositions":dispositions,
        "contribution":{"owner":"memory","revision":source_revision,"relevant":true,"settled":decisions.is_empty(),"decisions":decisions,"actions":actions},
        "authority":"nomination/disposition only; no automatic retention or completion authority"}),
    )
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn receiving_evidence_is_exact_current_and_semantically_bounded() {
        for reference in [
            "config/readiness.json",
            "tools/skills/method/SKILL.md",
            "tests/check.rs",
        ] {
            let mut args = json!({"lesson":"Do not copy this sentence into the receiving source.",
                "receiving_source":{"reference":reference,"revision":"current"}});
            let proof = json!({"evidence":[{"reference":"proof:check","proof_subject":"subject:current",
                "checked_scope":{"claim":"selected-command-passed","source_inputs":[{"path":reference}]}}]});
            assert!(receiving_consequence(&args, &proof).is_err());
            args["receiving_consequence"] = json!({"claim":"The receiving owner enforces the stable behaviour.","evidence_reference":"proof:check","proof_subject":"subject:current"});
            assert!(receiving_consequence(&args, &proof).is_ok());
            for (pointer, replacement) in [
                ("/evidence/0/proof_subject", json!("stale")),
                ("/evidence/0/checked_scope", Value::Null),
                (
                    "/evidence/0/checked_scope/source_inputs",
                    json!([{"path":"unrelated.txt"}]),
                ),
                ("/evidence/0/reference", json!("other-proof")),
            ] {
                let mut changed = proof.clone();
                *changed.pointer_mut(pointer).unwrap() = replacement;
                assert!(receiving_consequence(&args, &changed).is_err());
            }
        }
    }
    #[test]
    fn only_complete_explicit_producer_signals_nominate() {
        let candidate =
            json!({"lesson":"a bounded observation","rationale":"future decision value"});
        let detail = json!({"output":{"stdout":{"truncated":false,"tail":json!({"future_value_candidate":candidate}).to_string()}}});
        assert_eq!(signal(&detail), candidate);
        for tail in [
            "retry fixed it".to_owned(),
            "{}".to_owned(),
            json!({"future_value_candidate":{"lesson":"incomplete"}}).to_string(),
        ] {
            let mut invalid = detail.clone();
            invalid["output"]["stdout"]["tail"] = json!(tail);
            assert!(signal(&invalid).is_null());
        }
        let mut truncated = detail;
        truncated["output"]["stdout"]["truncated"] = json!(true);
        assert!(signal(&truncated).is_null());
    }
}
