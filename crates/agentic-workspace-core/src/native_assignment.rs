//! Source-owned current comparative Assignment judgment; no persistent preference.
use crate::{CoreError, digest};
use serde_json::{Value, json};

pub(crate) const IMPLEMENTATION_SCOPES: &[&str] = &[
    "effect:implementation",
    "claim:complete",
    "claim:pr-complete",
    "claim:claim-work-complete",
    "claim:claim-slice-complete",
];

/// Current admission at the shared native continuation/claim boundary. This is
/// a projection and restriction of Assignment/result owners, never a second ledger.
pub(crate) fn implementation_admission(
    requirements: &Value,
    contribution: &mut Value,
) -> Result<Value, CoreError> {
    let assignment = &requirements["assignment"]["result"];
    if assignment["binding"] != true {
        return Ok(json!({"status":"not-required","historical_compliance":"not-established"}));
    }
    let result = &requirements["assignment"]["result_admission"];
    let materialized = requirements["result"]["requirements"]["required_result_classes"]
        .as_array()
        .is_some_and(|classes| classes.contains(&json!("already-materialized")));
    let observed = materialized || requirements["delegation"]["observation"].is_object();
    let status = if result["result_use_allowed"] == true {
        "returned-admitted"
    } else if observed {
        "returned-unadmitted"
    } else if assignment["local_assignment_satisfied"] == true {
        "admitted-local"
    } else if assignment["status"] == "assigned-nonlocal-handoff-required" {
        "admitted-nonlocal"
    } else {
        "assessment-required"
    };
    let admission = json!({"status":status,"assignment_identity":assignment["assignment_identity"],
        "local_continuation_allowed":assignment["local_assignment_satisfied"] == true && !observed,
        "result_use_allowed":result["result_use_allowed"] == true,
        "historical_compliance":if result["result_use_allowed"] == true {"owner-admitted-result"} else {"not-established"},
        "recovery_owner":"assignment",
        "boundary":"Native start/invoke continuation, patch integration and completion claims. External editor, shell and Git effects are not intercepted. A current local choice does not attest earlier external implementation."});
    if status == "returned-unadmitted" {
        contribution["blockers"].as_array_mut().unwrap().push(json!({
            "code":"implementation-result-unadmitted",
            "message":"Observed implementation remains unadmitted. A later local Assignment does not authorize those results or completion claims; use the current Assignment/result recovery.",
            "affects":IMPLEMENTATION_SCOPES
        }));
        contribution["revision"] = json!(digest(&json!([
            contribution["revision"],
            admission,
            result,
            requirements["delegation"]["observation"]
        ]))?);
    }
    Ok(admission)
}

fn configuration_key(value: &Value) -> Result<String, CoreError> {
    digest(&json!([
        value["id"],
        value["target"],
        value["transport"],
        value["capability_revision"],
        value["execution"]["adapter"],
        value["execution"]["observed_executable"]
    ]))
}

/// A sparse projection of two current source-owner outcomes, not another store.
/// Replacing the Planning result or losing its checked sources de-adopts it.
pub(crate) fn outcome_evidence(
    task: &str,
    planning: &Value,
    verification: &Value,
) -> Result<Value, CoreError> {
    let used = &planning["consumed_result"];
    let consumption = &used["consumption"];
    let scope = consumption["context"]["scope_class"].as_str().unwrap_or("");
    if used["status"] != "current"
        || consumption["context"]["task"] != task
        || !matches!(scope, "read-only" | "unapplied-patch")
    {
        return Ok(json!([]));
    }
    let integration = &consumption["integration"];
    let evaluation = &consumption["context"]["result_evaluation"];
    let repair = matches!(
        evaluation["status"].as_str(),
        Some("repair-required" | "rejected")
    );
    if scope == "unapplied-patch"
        && !repair
        && (integration["status"] != "integrated"
            || integration["execution_custody"] != consumption["execution_custody"]
            || !integration["postimages"]
                .as_array()
                .is_some_and(|rows| !rows.is_empty()))
    {
        return Ok(json!([]));
    }
    let Some(proof) =
        verification["evidence"]
            .as_array()
            .into_iter()
            .flatten()
            .find(|proof| {
                proof["checked_scope"]["task"] == task
                    && proof["checked_scope"]["source_inputs"]
                        .as_array()
                        .is_some_and(|inputs| {
                            inputs.iter().any(|input| {
                                input["path"] == used["owner_ref"]
                                    && used["source_revision"]
                                        .as_str()
                                        .and_then(|r| r.strip_prefix("sha256:"))
                                        == input["sha256"].as_str()
                            }) && (repair
                                || scope != "unapplied-patch"
                                || integration["postimages"].as_array().unwrap().iter().all(
                                    |post| {
                                        inputs.iter().any(|input| {
                                            input["path"] == post["path"]
                                                && post["revision"]
                                                    .as_str()
                                                    .and_then(|r| r.strip_prefix("sha256:"))
                                                    == input["sha256"].as_str()
                                        })
                                    },
                                ))
                        })
            })
    else {
        return Ok(json!([]));
    };
    let configuration = if consumption["context"]["executed_configuration"].is_object() {
        &consumption["context"]["executed_configuration"]
    } else {
        &consumption["assignment_identity"]["selected"]["configuration"]
    };
    if !configuration.is_object() {
        return Ok(json!([]));
    }
    let mut observation = json!({"kind":"agentic-workspace/contextual-target-outcome/v1","status":"current-owner-derived","claim":"result-retained-and-selected-command-passed","target":configuration["target"],"configuration_key":configuration_key(configuration)?,"context":{"task":task,"role":consumption["context"]["role"],"scope_class":"read-only","owner_ref":used["owner_ref"],"source_revision":used["source_revision"]},"support":{"observed_outcomes":1,"confidence":"single-current-outcome","proof_ref":proof["reference"],"proof_subject":proof["proof_subject"],"planning_custody":used["custody"],"execution_custody":consumption["execution_custody"],"result_revision":consumption["result_revision"],"judgment_revision":consumption["judgment_revision"],"result_use_authority":"acting-orchestrator","check_authority":"native-verification"},"context_cost":consumption["context"]["context_cost"],"routing_effect":"context-for-agent-comparison-among-eligible-configurations","claim_boundary":{"task_success":false,"general_target_quality":false,"eligibility":false,"completion":false,"independent_review":false}});
    observation["context"]["scope_class"] = json!(scope);
    if repair {
        observation["claim"] = json!("responsible-owner-repair-evaluation-retained-and-checked");
        observation["evaluation"] = evaluation.clone();
    } else if scope == "unapplied-patch" {
        observation["claim"] =
            json!("patch-integrated-result-retained-and-selected-command-passed");
        observation["support"]["integration"] = integration.clone();
    }
    observation["revision"] = json!(digest(&observation)?);
    Ok(json!([observation]))
}
pub(crate) fn declaration() -> Value {
    let schema: Value = serde_json::from_str(include_str!(
        "../../../src/agentic_workspace/contracts/schemas/source_decision_input.schema.json"
    ))
    .expect("schema");
    let mut shape = schema["$defs"]["assignment_comparative_judgment"].clone();
    shape["$schema"] = schema["$schema"].clone();
    json!({"kind":"assignment/assess-best-fit/v1","result_kind":"agentic-workspace/assignment-decision/v1","input_schema":shape})
}
pub(crate) fn view(
    work: &Value,
    configuration: &Value,
    requirements: &Value,
    request: Option<&Value>,
    submitted: &[Value],
    contract: &Value,
) -> Result<Value, CoreError> {
    let policy = &configuration["assignment_policy"];
    let execution = &requirements["execution_configurations"];
    let source = digest(
        &json!({"work":work,"configuration":configuration["revision"],"requirements":requirements["result"],"execution":execution,"outcome_evidence":requirements["bounded_outcome_evidence"]}),
    )?;
    let owner = contract["owners"]
        .as_array()
        .unwrap()
        .iter()
        .find(|o| o["owner"] == "assignment")
        .unwrap();
    if configuration["assignment_requirements"]["configured"] != true && policy["binding"] != true {
        if request.is_some() {
            return Err(CoreError::new(
                "assignment assessment has no current configured scope",
            ));
        }
        return Ok(
            json!({"status":"not-applicable","requests":[],"contribution":{"owner":"assignment","revision":owner["revision"],"blockers":[]}}),
        );
    }
    if let Some(request) = request {
        crate::prepare_request_value(
            json!({"request":request,"current_work":work,"capability_contract":contract}),
        )?;
        if request["source_revision"] != source {
            return Err(CoreError::new(
                "assignment assessment source changed; resolve current request",
            ));
        }
    }
    let mut result = crate::assignment::comparative_assessment(
        json!({"work":work,"policy":policy,"requirements":requirements["result"],"execution":execution,"judgment":request.map(|r|&r["arguments"])}),
    )?;
    if let Some(answer) = configuration["residuals"]
        .as_array()
        .into_iter()
        .flatten()
        .find(|r| {
            r["source"] == ".agentic-workspace/config.local.toml"
                && r["field"] == "delegation.replacement"
        })
    {
        // A former exact answer is not standing policy. A different work id
        // cannot govern this independently admitted local Assignment. Matching
        // ids (even with different revisions) remain unresolved: no inferred
        // retirement, transfer, replacement permission or legacy admission.
        let unrelated = answer["work_identity"]["id"]
            .as_str()
            .zip(work["id"].as_str())
            .is_some_and(|(old, current)| !old.is_empty() && !current.is_empty() && old != current);
        result["former_replacement"] = json!({"source":answer["source"],"value_revision":answer["value_revision"],
            "status":if result["local_assignment_satisfied"] != true {"current-assignment-required"}
                else if unrelated {"outside-current-work"} else {"current-owner-answer-required"},
            "authority_boundary":"Applicability to this admitted local work only; no source write, retirement, adoption or delegation permission."});
    }
    for alternative in result["alternatives"].as_array_mut().into_iter().flatten() {
        let candidate = execution["configurations"]["candidates"]
            .as_array()
            .into_iter()
            .flatten()
            .find(|row| row["eligible"] == true && row["configuration"]["id"] == alternative["id"]);
        if let Some(candidate) = candidate {
            let key = configuration_key(&candidate["configuration"])?;
            alternative["contextual_evidence"] = json!(
                requirements["bounded_outcome_evidence"]
                    .as_array()
                    .into_iter()
                    .flatten()
                    .filter(|e| e["configuration_key"] == key
                        && e["context"]["role"] == requirements["result"]["role"]
                        && requirements["result"]["requirements"]["required_result_classes"]
                            .as_array()
                            .is_some_and(|classes| classes.contains(&e["context"]["scope_class"])))
                    .collect::<Vec<_>>()
            );
        }
    }
    let mut requests = Vec::new();
    if requirements["result"]["status"] == "resolved"
        && !result["alternatives"].as_array().unwrap().is_empty()
    {
        let mut packet = submitted
            .iter()
            .filter(|r| r["request_kind"] != "assignment/assess-best-fit/v1")
            .cloned()
            .collect::<Vec<_>>();
        packet.push(json!({"kind":"agentic-workspace/public-request/v1","id":"assignment/comparative-assessment","owner":"assignment","owner_revision":owner["revision"],"source_revision":source,"capability_revision":contract["revision"],"task_identity":work,"request_kind":"assignment/assess-best-fit/v1","arguments":{"revision":result["revision"],"alternative":"","reason":"","uncertainties":[]}}));
        requests.push(json!(packet));
    }
    let mut blockers = Vec::new();
    if policy["binding"] == true && result["local_assignment_satisfied"] != true {
        blockers.push(json!({"code":if policy["enforceable"]!=true{"binding-policy-current-target-unresolved"}else if result["status"]=="assigned-nonlocal-handoff-required"{"current-nonlocal-assignment-handoff-required"}else{"current-binding-assignment-required"},"message":"Current binding assignment requires resolved comparison and exact admitted continuation; unavailable manual/provider alternatives cannot silently authorize local implementation or completion of externally produced work.","affects":IMPLEMENTATION_SCOPES}));
    }
    Ok(
        json!({"result":result,"requests":requests,"source_revision":source,"contribution":{"owner":"assignment","revision":owner["revision"],"blockers":blockers}}),
    )
}

#[cfg(test)]
mod admission_tests {
    use super::*;

    #[test]
    fn later_local_assignment_cannot_admit_materialized_or_observed_work() {
        for materialized in [true, false] {
            let mut requirements = json!({"assignment":{"result":{"binding":true,"local_assignment_satisfied":false}},
                "result":{"requirements":{"required_result_classes":if materialized {json!(["already-materialized"])} else {json!(["unapplied-patch"])}}},
                "delegation":{"observation":if materialized {Value::Null} else {json!({"revision":"returned-result"})}}});
            for local in [false, true] {
                requirements["assignment"]["result"]["local_assignment_satisfied"] = json!(local);
                let mut contribution =
                    json!({"owner":"assignment","revision":"current","blockers":[]});
                let admission = implementation_admission(&requirements, &mut contribution).unwrap();
                assert_eq!(admission["status"], "returned-unadmitted");
                assert_eq!(admission["historical_compliance"], "not-established");
                assert_eq!(admission["local_continuation_allowed"], false);
                assert_eq!(
                    contribution["blockers"][0]["affects"],
                    json!(IMPLEMENTATION_SCOPES)
                );
                assert_ne!(contribution["revision"], "current");
            }
            requirements["assignment"]["result_admission"] = json!({"result_use_allowed":true});
            let mut contribution = json!({"owner":"assignment","revision":"current","blockers":[]});
            let admission = implementation_admission(&requirements, &mut contribution).unwrap();
            assert_eq!(admission["status"], "returned-admitted");
            assert_eq!(contribution["blockers"], json!([]));
        }
    }
}
