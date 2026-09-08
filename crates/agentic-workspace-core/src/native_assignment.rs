//! Source-owned current comparative Assignment judgment; no persistent preference.
use crate::{CoreError, digest};
use serde_json::{Value, json};
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
        &json!({"work":work,"configuration":configuration["revision"],"requirements":requirements["result"],"execution":execution}),
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
    let result = crate::assignment::comparative_assessment(
        json!({"work":work,"policy":policy,"requirements":requirements["result"],"execution":execution,"judgment":request.map(|r|&r["arguments"])}),
    )?;
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
        blockers.push(json!({"code":if policy["enforceable"]!=true{"binding-policy-current-target-unresolved"}else if result["status"]=="assigned-nonlocal-handoff-required"{"current-nonlocal-assignment-handoff-required"}else{"current-binding-assignment-required"},"message":"Current binding assignment requires resolved comparison and exact admitted continuation; unavailable manual/provider alternatives cannot silently authorize local implementation.","affects":["effect:implementation","claim:claim-work-complete","claim:claim-slice-complete"]}));
    }
    Ok(
        json!({"result":result,"requests":requests,"source_revision":source,"contribution":{"owner":"assignment","revision":owner["revision"],"blockers":blockers}}),
    )
}
