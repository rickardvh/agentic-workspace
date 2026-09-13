//! A bounded semantic claim judgment over current Verification evidence. Caller
//! carriage retains the answer; every consumer reobserves its exact dependency set.
use crate::{CoreError, digest};
use serde_json::{Value, json};
use std::path::Path;
pub(crate) const REQUEST: &str = "verification/review-claim/v1";
pub(crate) fn declaration() -> Value {
    json!({"kind":REQUEST,"result_kind":"agentic-workspace/claim-review/v1","input_schema":{"$schema":"https://json-schema.org/draft/2020-12/schema","type":"object","additionalProperties":false,"required":["reason","disposition","evidence_refs"],"properties":{"reason":{"type":"string","minLength":1,"maxLength":4096},"disposition":{"enum":["satisfied","insufficient"]},"evidence_refs":{"type":"array","maxItems":64,"uniqueItems":true,"items":{"type":"string"}},"proposal_revision":{"type":"string"},"answer":{"enum":["confirm","defer"]}}}})
}
pub(crate) struct Context<'a> {
    pub target: &'a Path,
    pub work: &'a Value,
    pub subject: &'a Value,
    pub changed: &'a [String],
    pub config: &'a Value,
    pub instructions: &'a Value,
    pub strategy: &'a Value,
    pub evidence: &'a [Value],
    pub source_revision: &'a str,
    pub contract: &'a Value,
}
pub(crate) fn view(context: Context<'_>, request: Option<&Value>) -> Result<Value, CoreError> {
    let Context {
        target,
        work,
        subject,
        changed,
        config,
        instructions,
        strategy,
        evidence,
        source_revision,
        contract,
    } = context;
    let owner = contract["owners"]
        .as_array()
        .unwrap()
        .iter()
        .find(|o| o["owner"] == "verification")
        .unwrap();
    let template = json!({"kind":"agentic-workspace/public-request/v1","id":REQUEST,"owner":"verification","owner_revision":owner["revision"],"source_revision":source_revision,"capability_revision":contract["revision"],"task_identity":work,"request_kind":REQUEST,"arguments":{"reason":"Review the exact resulting work against the required evidence and outcome.","disposition":"insufficient","evidence_refs":[]}});
    let mut result = json!({"kind":"agentic-workspace/claim-review/v1","status":"not-requested","request":template,"decisions":[],"completion_authority":false});
    let Some(request) = request else {
        return Ok(result);
    };
    let mut patterns: Vec<String> = changed.to_vec();
    for row in instructions["sources"]
        .as_array()
        .into_iter()
        .flatten()
        .filter(|r| r["applicable"] == true)
    {
        patterns.extend(
            row["metadata"]["paths"]
                .as_array()
                .into_iter()
                .flatten()
                .filter_map(Value::as_str)
                .map(str::to_owned),
        );
    }
    let root = cap_std::fs::Dir::open_ambient_dir(target, cap_std::ambient_authority())
        .map_err(|e| CoreError::new(e.to_string()))?;
    let paths = crate::native_source_reconciliation::scope_files(&root, &patterns)?;
    let mut sources = serde_json::Map::new();
    for path in paths {
        sources.insert(
            path.clone(),
            crate::native_planning::read(&root, &path)?
                .map(|b| json!(crate::decision_source::hash(&b)))
                .unwrap_or(Value::Null),
        );
    }
    let mut stable_evidence = evidence.to_vec();
    for e in &mut stable_evidence {
        if let Some(f) = e["runtime_admission"].as_object_mut() {
            f.remove("validation_duration_us");
        }
    }
    let binding = json!({"work":work,"subject":subject,"postimages":sources,"source_revision":source_revision,"policy_revision":config["revision"],"instructions":instructions["sources"].as_array().unwrap().iter().filter(|r|r["applicable"]==true).collect::<Vec<_>>(),"strategy":strategy,"evidence":stable_evidence,"producer":digest(&json!(include_str!("native_claim_review.rs")))?});
    let args = &request["arguments"];
    let proposal =
        json!({"binding":binding,"judgment":args["disposition"],"reason":args["reason"]});
    let pr = digest(&proposal)?;
    result["proposal"] = proposal;
    let mut answer = args.clone();
    answer["proposal_revision"] = json!(pr);
    answer.as_object_mut().unwrap().remove("answer");
    let decisions = json!([{"id":"verification-claim-review","question":"Confirm this exact claim judgment against the resulting work and current evidence?","material":result["proposal"],"response_request":{"request_kind":REQUEST,"arguments":answer},"choices":[{"id":"confirm","label":"Confirm exact claim judgment"},{"id":"defer","label":"Leave claim unresolved"}],"affects":["claim:complete"]}]);
    let compiled = crate::compile_value(
        json!({"intent":{"current_work":work},"capability_contract":contract,"contributions":[{"owner":"verification","revision":source_revision,"decisions":decisions}]}),
    )?;
    let mut exact = compiled["pending_consequences"]["decisions"][0]["response_request"].clone();
    let scope: Vec<String> = sources.keys().cloned().collect();
    let delegated = crate::native_decision_authority::delegated(config, "verification", &scope);
    if args["answer"].is_null() && delegated.is_none() {
        result["status"] = json!("bounded-human-answer-required");
        result["decisions"] = decisions;
        return Ok(result);
    }
    if !args["answer"].is_null() {
        exact["arguments"]["answer"] = args["answer"].clone();
        if exact != *request || args["proposal_revision"] != pr {
            return Err(CoreError::new("claim review answer changed or is stale"));
        }
        if args["answer"] == "defer" {
            result["status"] = json!("deferred");
            return Ok(result);
        }
    }
    let mut gaps = Vec::new();
    if args["disposition"] != "satisfied" {
        gaps.push("review-judgment-insufficient".to_owned());
    }
    for e in evidence {
        if e["checked_scope"]["claim"] != "selected-command-passed" {
            gaps.push(format!("current-evidence-required:{}", e["reference"]));
        }
    }
    for (id, protocol) in strategy["protocols"].as_object().into_iter().flatten() {
        // A semantic reviewer grant cannot manufacture independent/maintainer evidence.
        if protocol.get("review_owner").is_some()
            || protocol["independent_required"] == true
            || protocol["manual_required"] == true
        {
            gaps.push(format!("required-review-producer:{id}"));
        }
        let covered = evidence
            .iter()
            .filter(|e| e["checked_scope"]["claim"] == "selected-command-passed")
            .any(|e| {
                let route = e["runtime_admission"]["command_coverage"]["route_id"]
                    .as_str()
                    .unwrap_or("");
                strategy["proof_routes"][route]["protocol_refs"]
                    .as_array()
                    .is_some_and(|refs| refs.contains(&json!(id)))
            });
        if !covered {
            gaps.push(format!("protocol-evidence-required:{id}"));
        }
    }
    result["status"] = json!(if gaps.is_empty() {
        "current"
    } else {
        "insufficient"
    });
    result["gaps"] = json!(gaps);
    result["authority_basis"]=delegated.unwrap_or_else(||json!({"kind":"exact-bounded-human-answer","request_revision":digest(request).unwrap(),"identity_authentication":"not-claimed"}));
    result["claim"] = json!({"work":work,"subject":subject,"judgment":args["disposition"],"binding_revision":digest(&binding)?});
    Ok(result)
}
