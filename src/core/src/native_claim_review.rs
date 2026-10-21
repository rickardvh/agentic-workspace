//! A bounded semantic claim judgment over current Verification evidence. Caller
//! carriage retains the answer; every consumer reobserves its exact dependency set.
use crate::{CoreError, digest};
use serde_json::{Value, json};
use std::path::Path;
pub(crate) const REQUEST: &str = "verification/review-claim/v1";
const MAX_PROTOCOL_RECOVERY_BYTES: usize = 8192;
const MAX_POSTIMAGE_BYTES: u64 = 128 * 1024 * 1024;

fn postimages(
    target: &Path,
    changed: &[String],
) -> Result<serde_json::Map<String, Value>, CoreError> {
    let failure = |source: &str, error: CoreError| {
        CoreError::new(format!(
            "Verification claim source {source}: {error}; restore a confined, stable regular source \
             within the 32 MiB per-file and 128 MiB claim identity budgets, then resubmit the \
             current Verification claim. No claim confirmation was admitted."
        ))
    };
    let root = cap_std::fs::Dir::open_ambient_dir(target, cap_std::ambient_authority())
        .map_err(|e| failure("target", CoreError::new(e.to_string())))?;
    let paths = crate::native_source_reconciliation::scope_files(&root, changed)
        .map_err(|e| failure("scope (at most 4096 discovered entries)", e))?;
    if paths.len() > 4096 {
        return Err(failure(
            "scope",
            CoreError::new("claim scope exceeds 4096 source identities"),
        ));
    }
    let mut sources = serde_json::Map::new();
    let mut remaining = MAX_POSTIMAGE_BYTES;
    for path in paths {
        let observed = crate::dependency_binding::observe_raw(&root, &path, remaining)
            .map_err(|e| failure(&path, e))?;
        let revision = if let Some((revision, bytes)) = observed {
            remaining -= bytes;
            json!(revision)
        } else {
            // An absent result is a deliberate deletion postimage. Unreadable,
            // linked or over-budget sources return an error rather than null.
            Value::Null
        };
        sources.insert(path, revision);
    }
    Ok(sources)
}

pub(crate) fn declaration() -> Value {
    json!({"kind":REQUEST,"result_kind":"agentic-workspace/claim-review/v1","input_schema":{"$schema":"https://json-schema.org/draft/2020-12/schema","type":"object","additionalProperties":false,"required":["reason","disposition","evidence_refs"],"properties":{"reason":{"type":"string","minLength":1,"maxLength":4096},"disposition":{"enum":["satisfied","insufficient"]},"evidence_refs":{"type":"array","maxItems":64,"uniqueItems":true,"items":{"type":"string"}},"candidate_refs":{"type":"array","maxItems":64,"uniqueItems":true,"items":{"type":"string"}},"evidence_dispositions":{"type":"object","maxProperties":64,"additionalProperties":{"type":"object","additionalProperties":false,"required":["disposition","reason"],"properties":{"disposition":{"enum":["material","not-material","superseded"]},"reason":{"type":"string","minLength":1,"maxLength":4096},"superseding_ref":{"type":"string","minLength":1}}}},"proposal_revision":{"type":"string"},"answer":{"enum":["confirm","defer"]}}}})
}

// Assess only the candidate observations explicitly carried by this bounded
// work. No receipt-history discovery or caller-authored authenticity is added.
pub(crate) fn negative_evidence(
    evidence: &[Value],
    strategy: &Value,
    obligations: &Value,
    instruction_checks: &[Value],
    request: Option<&Value>,
) -> Vec<Value> {
    evidence.iter().filter(|e| e["receipt_admission"]["result_class"] == "failed").map(|e| {
        let reference = &e["reference"];
        let current = e["runtime_admission"]["status"] == "reusable"
            && e["runtime_admission"]["strategy_coverage"] == "selected-command-covered"
            && e["detail"]["status"] == "current";
        let choice = &e["runtime_admission"]["command_coverage"];
        let route_id = choice["route_id"].as_str().unwrap_or("");
        let route = &strategy["proof_routes"][route_id];
        let requirements: Vec<_> = obligations.as_array().into_iter().flatten().filter(|o| {
            let profile = o["profile_id"].as_str().unwrap_or("");
            o["required_commands"].as_array().is_some_and(|commands| commands.contains(&choice["command"]))
                && (route_id == format!("profile:{profile}") || route["protocol_refs"].as_array().into_iter().flatten()
                    .filter_map(Value::as_str).any(|id| strategy["protocols"][id]["proof_profiles"].as_array()
                        .is_some_and(|profiles| profiles.contains(&json!(profile)))))
        }).collect();
        let required = !requirements.is_empty() || instruction_checks.iter().any(|check| {
            check["route_id"] == choice["route_id"] && matches!(check["status"].as_str(), Some("current" | "evidence-required"))
        });
        let disposition = request.map(|r| &r["arguments"]["evidence_dispositions"][reference.as_str().unwrap_or("")])
            .unwrap_or(&Value::Null);
        // Supersession is a bound semantic judgment, supported by a current pass
        // for this same declared command, route and subject. It never turns the
        // old failure green or accepts unrelated proof as a replacement.
        let recorded = |item: &Value| item["observation"]["recorded_at"].as_str()
            .and_then(|time| chrono::DateTime::parse_from_rfc3339(time).ok());
        let superseded = disposition["disposition"] == "superseded" && evidence.iter().any(|pass| {
            pass["reference"] == disposition["superseding_ref"]
                && pass["checked_scope"]["claim"] == "selected-command-passed"
                && pass["runtime_admission"]["command_coverage"] == *choice
                && pass["proof_subject"] == e["proof_subject"]
                && matches!((recorded(pass), recorded(e)), (Some(p), Some(f)) if p >= f)
        });
        let status = if !current { "historical-or-unproven" }
            else if superseded { "superseded" }
            else if required { "required-failure" }
            else if disposition["disposition"] == "material" { "material-failure" }
            else if disposition["disposition"] == "not-material" { "not-material" }
            else if disposition["disposition"] == "superseded" { "disposition-unproven" }
            else { "relevance-unresolved" };
        json!({"reference":reference,"status":status,"required":required,"source_obligations":requirements,
            "instruction_checks":instruction_checks.iter().filter(|c| c["route_id"] == choice["route_id"]).collect::<Vec<_>>(),
            "judgment":disposition,"observation":e["observation"],
            "authority":"Current required-command coverage or the acting domain's exact bound relevance/supersession judgment; selection alone supplies neither."})
    }).collect()
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
    pub negative_evidence: &'a [Value],
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
        negative_evidence,
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
        .filter(|entry| entry["checked_scope"]["claim"] == "selected-command-passed")
        .filter_map(|entry| entry["reference"].as_str())
        .collect();
    evidence_refs.sort_unstable();
    evidence_refs.dedup();
    let candidate_refs: Vec<_> = evidence
        .iter()
        .filter_map(|entry| entry["reference"].as_str())
        .collect();
    let mut template = json!({"kind":"agentic-workspace/public-request/v1","id":REQUEST,"owner":"verification","owner_revision":owner["revision"],"source_revision":source_revision,"capability_revision":contract["revision"],"task_identity":work,"request_kind":REQUEST,"arguments":{"reason":"Review the exact resulting work against the required evidence and outcome.","disposition":"insufficient","evidence_refs":evidence_refs}});
    // The schema advertises optional judgments. Empty candidate/disposition
    // carriage says nothing and need not accompany every unrelated task.
    if !candidate_refs.is_empty() {
        template["arguments"]["candidate_refs"] = json!(candidate_refs);
    }
    let mut result = json!({"kind":"agentic-workspace/claim-review/v1","status":"not-requested","request":template,"decisions":[],"completion_authority":false});
    let Some(request) = request else {
        return Ok(result);
    };
    // Current work supplies the result scope. Instruction applicability describes
    // where a rule governs, not additional results of this claim. The applicable
    // instruction sources remain independently bound below, alongside the subject,
    // policy and evidence; reconciliation owns discovery of their other consumers.
    let sources = postimages(target, changed)?;
    let args = &request["arguments"];
    let selected = |entry: &&Value| {
        args["evidence_refs"]
            .as_array()
            .is_some_and(|refs| refs.contains(&entry["reference"]))
    };
    // Supporting selection does not discard the bounded work's known negatives.
    // Their source requirement or explicit relevance judgment decides force.
    let current_failure = |entry: &&Value| {
        entry["receipt_admission"]["result_class"] == "failed"
            && entry["runtime_admission"]["status"] == "reusable"
            && entry["runtime_admission"]["strategy_coverage"] == "selected-command-covered"
    };
    let mut stable_evidence: Vec<Value> = evidence
        .iter()
        .filter(|entry| selected(entry) || current_failure(entry))
        .cloned()
        .collect();
    for e in &mut stable_evidence {
        if let Some(f) = e["runtime_admission"].as_object_mut() {
            f.remove("validation_duration_us");
        }
    }
    let binding = json!({"work":work,"subject":subject,"postimages":sources,"source_revision":source_revision,"policy_revision":config["revision"],"instructions":instructions["sources"].as_array().unwrap().iter().filter(|r|r["applicable"]==true).collect::<Vec<_>>(),"strategy":strategy,"evidence":stable_evidence,"candidate_refs":candidate_refs,"negative_evidence":negative_evidence,"producer":digest(&json!(include_str!("native_claim_review.rs")))?});
    let proposal =
        json!({"binding":binding,"judgment":args["disposition"],"reason":args["reason"]});
    let pr = digest(&proposal)?;
    result["proposal"] = proposal;
    let mut answer = args.clone();
    answer["proposal_revision"] = json!(pr);
    answer["candidate_refs"] = json!(candidate_refs);
    answer.as_object_mut().unwrap().remove("answer");
    let mut gaps = Vec::new();
    if args["disposition"] != "satisfied" {
        gaps.push("review-judgment-insufficient".to_owned());
    }
    for row in negative_evidence {
        match row["status"].as_str() {
            Some("required-failure" | "material-failure") => {
                gaps.push(format!("current-failing-evidence:{}", row["reference"]))
            }
            Some("relevance-unresolved" | "disposition-unproven") => {
                gaps.push(format!("failure-relevance-unresolved:{}", row["reference"]))
            }
            _ => (),
        }
    }
    let mut protocol_coverage = serde_json::Map::new();
    for (id, protocol) in strategy["protocols"].as_object().into_iter().flatten() {
        // A semantic reviewer grant cannot manufacture independent/maintainer evidence.
        if protocol["independent_required"] == true || protocol["manual_required"] == true {
            gaps.push(format!("required-review-producer:{id}"));
        }
        let supporting: Vec<_> = stable_evidence
            .iter()
            .filter(|e| crate::native_proof::covers_protocol(e, strategy, id))
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
        "protocol_obligations":strategy["protocols"],"protocol_coverage":protocol_coverage,"negative_evidence":negative_evidence,
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
    let decisions = json!([{"id":"verification-claim-review","question":"Confirm this exact claim judgment against the resulting work and current evidence?","material":material,"response_request":{"request_kind":REQUEST,"arguments":answer},"choices":[{"id":"confirm","label":"Confirm exact claim judgment"},{"id":"defer","label":"Leave claim unresolved"}],"affects":["attestation:verification"],
        "basis":crate::restriction_basis("attestation-limit",&json!(source_revision),REQUEST,&material)}]);

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

#[cfg(test)]
mod source_tests {
    use super::*;

    #[test]
    fn claim_postimages_preserve_bytes_membership_and_source_limits() {
        let temp = std::env::temp_dir().join(format!(
            "aw-claim-sources-{}-{}",
            std::process::id(),
            std::time::SystemTime::now()
                .duration_since(std::time::UNIX_EPOCH)
                .unwrap()
                .as_nanos()
        ));
        std::fs::create_dir_all(temp.join("results")).unwrap();
        let bytes = [0xff, 0xfe, 0, b'\r', b'\n'];
        std::fs::write(temp.join("results/binary"), bytes).unwrap();
        let scope = vec!["results/*".into(), "deleted".into()];
        let first = postimages(&temp, &scope).unwrap();
        assert_eq!(
            first["results/binary"],
            crate::dependency_binding::revision(
                &bytes,
                crate::dependency_binding::Scheme::RawBytes
            )
            .unwrap()
        );
        assert_eq!(first["deleted"], Value::Null);
        std::fs::write(temp.join("results/new"), "new member").unwrap();
        assert_ne!(postimages(&temp, &scope).unwrap(), first);
        let excess: Vec<_> = (0..4097).map(|i| format!("absent-{i}")).collect();
        assert!(
            postimages(&temp, &excess)
                .unwrap_err()
                .to_string()
                .contains("4096")
        );
        std::fs::File::create(temp.join("oversized"))
            .unwrap()
            .set_len(crate::dependency_binding::MAX_OBSERVATION_BYTES + 1)
            .unwrap();
        for path in ["oversized", "results", "../escape"] {
            let error = postimages(&temp, &[path.into()]).unwrap_err().to_string();
            assert!(error.contains("Verification claim source"));
            assert!(error.contains("resubmit the current Verification claim"));
            assert!(!error.contains("Planning"));
        }
        #[cfg(unix)]
        std::os::unix::fs::symlink("results", temp.join("linked")).unwrap();
        #[cfg(windows)]
        junction::create(temp.join("results"), temp.join("linked")).unwrap();
        for path in ["linked/binary", "linked/*"] {
            let error = postimages(&temp, &[path.into()]).unwrap_err().to_string();
            assert!(error.contains("Verification claim source"));
            assert!(error.contains("linked"));
        }
        #[cfg(windows)]
        junction::delete(temp.join("linked")).unwrap();
        std::fs::remove_dir_all(temp).unwrap();
    }
}
