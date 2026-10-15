//! A bounded semantic claim judgment over current Verification evidence. Caller
//! carriage retains the answer; every consumer reobserves its exact dependency set.
use crate::{CoreError, digest};
use serde_json::{Value, json};
use std::path::Path;
pub(crate) const REQUEST: &str = "verification/review-claim/v1";
const MAX_PROTOCOL_RECOVERY_BYTES: usize = 8192;
pub(crate) fn declaration() -> Value {
    json!({"kind":REQUEST,"result_kind":"agentic-workspace/claim-review/v1","input_schema":{"$schema":"https://json-schema.org/draft/2020-12/schema","type":"object","additionalProperties":false,"required":["reason","disposition","evidence_refs"],"properties":{"reason":{"type":"string","minLength":1,"maxLength":4096},"disposition":{"enum":["satisfied","insufficient"]},"evidence_refs":{"type":"array","maxItems":64,"uniqueItems":true,"items":{"type":"string"}},"proposal_revision":{"type":"string"},"answer":{"enum":["confirm","defer"]}}}})
}
pub(crate) struct Context<'a> {
    pub target: &'a Path,
    pub task: &'a str,
    pub work: &'a Value,
    pub subject: &'a Value,
    pub changed: &'a [String],
    pub config: &'a Value,
    pub instructions: &'a Value,
    pub strategy: &'a Value,
    pub evidence: &'a [Value],
    pub execution_request: &'a dyn Fn(Value) -> Value,
    pub source_revision: &'a str,
    pub contract: &'a Value,
}
pub(crate) fn view(context: Context<'_>, request: Option<&Value>) -> Result<Value, CoreError> {
    let Context {
        target,
        task,
        work,
        subject,
        changed,
        config,
        instructions,
        strategy,
        evidence,
        execution_request,
        source_revision,
        contract,
    } = context;
    let owner = contract["owners"]
        .as_array()
        .unwrap()
        .iter()
        .find(|o| o["owner"] == "verification")
        .unwrap();
    // Preserve the evidence already selected and admitted by Verification. Its
    // presence is not sufficiency: failed and stale observations remain visible
    // and all claim/currentness checks below still apply to the semantic answer.
    let mut evidence_refs: Vec<_> = evidence
        .iter()
        .filter_map(|entry| entry["reference"].as_str())
        .collect();
    evidence_refs.sort_unstable();
    evidence_refs.dedup();
    let template = json!({"kind":"agentic-workspace/public-request/v1","id":REQUEST,"owner":"verification","owner_revision":owner["revision"],"source_revision":source_revision,"capability_revision":contract["revision"],"task_identity":work,"request_kind":REQUEST,"arguments":{"reason":"Review the exact resulting work against the required evidence and outcome.","disposition":"insufficient","evidence_refs":evidence_refs}});
    let mut result = json!({"kind":"agentic-workspace/claim-review/v1","status":"not-requested","request":template,"decisions":[],"completion_authority":false});
    let Some(request) = request else {
        return Ok(result);
    };
    // Current work supplies the result scope. Instruction applicability describes
    // where a rule governs, not additional results of this claim. The applicable
    // instruction sources remain independently bound below, alongside the subject,
    // policy and evidence; reconciliation owns discovery of their other consumers.
    let root = cap_std::fs::Dir::open_ambient_dir(target, cap_std::ambient_authority())
        .map_err(|e| CoreError::new(e.to_string()))?;
    let paths = crate::native_source_reconciliation::scope_files(&root, changed)?;
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
    let mut gaps = Vec::new();
    if args["disposition"] != "satisfied" {
        gaps.push("review-judgment-insufficient".to_owned());
    }
    for e in evidence {
        if e["checked_scope"]["claim"] != "selected-command-passed" {
            gaps.push(format!("current-evidence-required:{}", e["reference"]));
        }
    }
    let mut protocol_coverage = serde_json::Map::new();
    for (id, protocol) in strategy["protocols"].as_object().into_iter().flatten() {
        // A semantic reviewer grant cannot manufacture independent/maintainer evidence.
        if protocol.get("review_owner").is_some()
            || protocol["independent_required"] == true
            || protocol["manual_required"] == true
        {
            gaps.push(format!("required-review-producer:{id}"));
        }
        let supporting: Vec<_> = evidence
            .iter()
            .filter(|e| e["checked_scope"]["claim"] == "selected-command-passed")
            // Command/source/runtime reuse does not prove that the original
            // execution covered the current route and protocol declarations.
            .filter(|e| e["runtime_admission"]["sufficiency_currentness"] == "current")
            .filter(|e| {
                let route = e["runtime_admission"]["command_coverage"]["route_id"]
                    .as_str()
                    .unwrap_or("");
                strategy["proof_routes"][route]["protocol_refs"]
                    .as_array()
                    .is_some_and(|refs| refs.contains(&json!(id)))
            })
            .collect();
        let covered = !supporting.is_empty();
        // An explicitly manual-only protocol has no command to authenticate.
        // Its semantic judgment and any separate producer requirement remain.
        let manual_only = protocol["commands"]
            .as_array()
            .is_some_and(|commands| commands.is_empty());
        if !covered && !manual_only {
            gaps.push(format!("protocol-evidence-required:{id}"));
        }
        protocol_coverage.insert(id.clone(), json!({
            "status":if manual_only {"manual-only"} else if covered {"current-command-evidence-satisfied"} else {"command-evidence-required"},
            "evidence_refs":supporting.iter().map(|e| &e["reference"]).collect::<Vec<_>>(),
            "next_requests":[],"omitted_request_count":0,
            "authority":"Only current evidence with unchanged route/protocol semantics from an explicitly protocol-linked route counts; profile selection and matching command text do not supply protocol authority."
        }));
    }
    // Recovery is one bounded candidate for the entire claim, not a second
    // catalogue. Index current source linkage in one pass, only when uncovered
    // protocols exist. Leave every obligation and alternative at its owner.
    if protocol_coverage
        .values()
        .any(|row| row["status"] == "command-evidence-required")
    {
        let mut recovery_attempted = false;
        for (route_id, route) in strategy["proof_routes"].as_object().into_iter().flatten() {
            let uncovered: Vec<_> = route["protocol_refs"]
                .as_array()
                .into_iter()
                .flatten()
                .filter_map(Value::as_str)
                .filter(|id| {
                    protocol_coverage
                        .get(*id)
                        .is_some_and(|row| row["status"] == "command-evidence-required")
                })
                .collect();
            if uncovered.is_empty() {
                continue;
            }
            let Some(commands) = route["commands"].as_array() else {
                continue;
            };
            for id in &uncovered {
                let row = protocol_coverage.get_mut(*id).unwrap();
                row["omitted_request_count"] =
                    json!(row["omitted_request_count"].as_u64().unwrap() + commands.len() as u64);
            }
            if recovery_attempted {
                continue;
            }
            if let Some(command) = commands.first() {
                // Construct only the bounded offer, including the owner's
                // current prerequisites, even when its optional catalogue was
                // not requested by this compact claim continuation.
                let request = execution_request(json!({"route_id":route_id,"command":command}));
                recovery_attempted = true;
                if serde_json::to_vec(&request)
                    .is_ok_and(|bytes| bytes.len() <= MAX_PROTOCOL_RECOVERY_BYTES)
                {
                    let row = protocol_coverage.get_mut(uncovered[0]).unwrap();
                    row["next_requests"] = json!([request]);
                    row["omitted_request_count"] =
                        json!(row["omitted_request_count"].as_u64().unwrap() - 1);
                }
            }
        }
    }
    result["protocol_coverage"] = json!(protocol_coverage);
    // Keep the cryptographic proposal once, in selected owner detail. Compile
    // only the decision-bearing material: binding bytes are not a second set of
    // instructions for the consumer. Applicable instruction text is delivered
    // by the composed packet; exact source/proposal detail remains addressable.
    let material = json!({"task":task,"work":work,"subject":subject,
        "result_paths":sources.keys().collect::<Vec<_>>(),
        "judgment":args["disposition"],"reason":args["reason"],"proposal_revision":pr,
        "instruction_sources":instructions["sources"].as_array().unwrap().iter()
            .filter(|r|r["applicable"]==true).map(|r|json!({"source":r["source"],
                "binding_admission":r["binding_admission"]["status"],"requirements":r["metadata"]})).collect::<Vec<_>>(),
        "protocol_obligations":strategy["protocols"],"protocol_coverage":protocol_coverage,
        "protocol_recovery_boundary":{"maximum_request_count":1,"maximum_request_bytes":MAX_PROTOCOL_RECOVERY_BYTES,
            "alternatives_source":"/verification/execution_requests",
            "use":"At most one source-linked candidate is offered for uncovered protocols. Use the current detail_refs /verification reference to inspect other execution_requests or an oversized candidate. Omitted choices and all protocol obligations retain their authority. Selecting or repeating a command is not itself protocol sufficiency."},
        "evidence":stable_evidence.iter().map(|e|json!({"reference":e["reference"],"status":e["status"],
            "admission_scope":e["admission_scope"],"publication_admission":e["publication_admission"],
            "receipt_admission":e["receipt_admission"],"runtime_admission":{
                "status":e["runtime_admission"]["status"],"strategy_coverage":e["runtime_admission"]["strategy_coverage"],
                "sufficiency_currentness":e["runtime_admission"]["sufficiency_currentness"],
                "environment_scope":e["runtime_admission"]["environment_scope"],"nested_tool_runtime":e["runtime_admission"]["nested_tool_runtime"],
                "reason":e["runtime_admission"]["reason"]},
            "task_judgment":e["task_judgment"],"limits":e["limits"],
            "claim":e["checked_scope"]["claim"],"command":e["checked_scope"]["command"],
            "route":e["runtime_admission"]["command_coverage"]["route_id"],"gaps":e["gaps"]})).collect::<Vec<_>>(),
        "gaps":gaps,"claim_limits":"Confirmation supplies this semantic judgment only. All current blockers, required evidence and independent/manual reviewer producers remain binding; it grants no review, approval or whole-task completion."});
    let decisions = json!([{"id":"verification-claim-review","question":"Confirm this exact claim judgment against the resulting work and current evidence?","material":material,"response_request":{"request_kind":REQUEST,"arguments":answer},"choices":[{"id":"confirm","label":"Confirm exact claim judgment"},{"id":"defer","label":"Leave claim unresolved"}],"affects":["claim:complete"]}]);

    let compiled = crate::compile_value(
        json!({"intent":{"current_work":work},"capability_contract":contract,"contributions":[{"owner":"verification","revision":source_revision,"decisions":decisions}]}),
    )?;
    let mut exact = compiled["pending_consequences"]["decisions"][0]["response_request"].clone();
    let scope: Vec<String> = sources.keys().cloned().collect();
    let delegated = crate::native_decision_authority::delegated(config, "verification", &scope);
    if args["answer"].is_null() && delegated.is_none() {
        result["status"] = json!("bounded-domain-answer-required");
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
    result["status"] = json!(if gaps.is_empty() {
        "current"
    } else {
        "insufficient"
    });
    result["gaps"] = json!(gaps);
    result["authority_basis"]=delegated.unwrap_or_else(||json!({"kind":"exact-bounded-domain-answer","request_revision":digest(request).unwrap(),"identity_authentication":"not-claimed"}));
    result["claim"] = json!({"work":work,"subject":subject,"judgment":args["disposition"],"binding_revision":digest(&binding)?});
    Ok(result)
}
