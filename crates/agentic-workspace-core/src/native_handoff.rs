//! Read-only handoff. Source observation and agent completeness judgment stay separate.
use crate::{CoreError, digest};
use serde_json::{Value, json};
use sha2::{Digest, Sha256};
use std::path::Path;
pub(crate) const JUDGE_RETURN: &str = "assignment/judge-return/v1";
pub(crate) const PATCH_INPUTS: &str = "assignment/judge-patch-inputs/v1";
const PATCH_EXPORT: &str = "assignment/export-patch/v1";
const PATCH_RETURN: &str = "assignment/observe-patch-return/v1";
pub(crate) fn return_shape(patch: bool) -> Value {
    let schema: Value = serde_json::from_str(include_str!(
        "../../../src/agentic_workspace/contracts/schemas/source_decision_input.schema.json"
    ))
    .expect("schema");
    let mut shape = schema["$defs"]["readonly_handoff_return"].clone();
    shape["$schema"] = schema["$schema"].clone();
    if patch {
        shape["properties"]["returned"]["properties"]["patch"] =
            json!({"type":"string","maxLength":262144});
        shape["properties"]["returned"]["properties"]["changed_paths"] = json!({"type":"array","maxItems":8,"uniqueItems":true,"items":{"type":"string","minLength":1,"maxLength":256}});
    }
    shape
}
pub(crate) fn declarations() -> Vec<Value> {
    let schema: Value = serde_json::from_str(include_str!(
        "../../../src/agentic_workspace/contracts/schemas/source_decision_input.schema.json"
    ))
    .expect("schema");
    let mut declarations: Vec<Value> = [("assignment/judge-readonly-inputs/v1","readonly_handoff_inputs"),("assignment/export-readonly/v1","readonly_handoff_export"),("assignment/observe-readonly-return/v1","readonly_handoff_return")].iter().map(|(kind,key)|{let mut shape=schema["$defs"][*key].clone();shape["$schema"]=schema["$schema"].clone();json!({"kind":kind,"result_kind":"agentic-workspace/assignment-readonly-handoff/v1","input_schema":shape})}).collect();
    declarations.push(json!({"kind":JUDGE_RETURN,"result_kind":"agentic-workspace/assignment-result-admission/v1","input_schema":{"$schema":schema["$schema"],"type":"object","properties":{"answer":{"enum":["use-result","repair-required","reject-result"]},"reason":{"type":"string","minLength":1,"maxLength":4096}},"required":["answer","reason"],"additionalProperties":false}}));
    let mut inputs = schema["$defs"]["readonly_handoff_inputs"].clone();
    inputs["$schema"] = schema["$schema"].clone();
    inputs["properties"]["mutation_paths"] = inputs["properties"]["input_refs"].clone();
    inputs["required"]
        .as_array_mut()
        .unwrap()
        .push(json!("mutation_paths"));
    let mut export = schema["$defs"]["readonly_handoff_export"].clone();
    export["$schema"] = schema["$schema"].clone();
    for (kind, shape) in [
        (PATCH_INPUTS, inputs),
        (PATCH_EXPORT, export),
        (PATCH_RETURN, return_shape(true)),
    ] {
        declarations.push(json!({"kind":kind,"result_kind":"agentic-workspace/assignment-patch-handoff/v1","input_schema":shape}));
    }
    declarations
}

/// Current orchestrator judgment is not independent review or target calibration.
pub(crate) fn admission(
    work: &Value,
    execution: &Value,
    submitted: &[Value],
    contract: &Value,
) -> Result<Value, CoreError> {
    let judgment = submitted.iter().find(|r| r["request_kind"] == JUDGE_RETURN);
    if execution["status"] != "current-executed-observation" {
        if judgment.is_some() {
            return Err(CoreError::new(
                "current executed result required before Assignment judgment",
            ));
        }
        return Ok(json!({"status":"not-ready","requests":[]}));
    }
    let source = digest(&json!({"work":work,"execution":execution}))?;
    let mut prerequisites = submitted
        .iter()
        .filter(|r| r["request_kind"] != JUDGE_RETURN)
        .cloned()
        .collect::<Vec<_>>();
    let mut status = "judgment-required";
    let mut reason = "";
    if let Some(value) = judgment {
        validate(value, work, &source, contract)?;
        reason = value["arguments"]["reason"].as_str().unwrap_or("").trim();
        if reason.is_empty() {
            return Err(CoreError::new(
                "Assignment return judgment requires a reason",
            ));
        }
        status = match value["arguments"]["answer"].as_str() {
            Some("use-result") => "admitted-for-use",
            Some("repair-required") => "repair-required",
            Some("reject-result") => "rejected",
            _ => return Err(CoreError::new("unsupported Assignment return judgment")),
        };
    }
    prerequisites.push(request(
        JUDGE_RETURN,
        json!({"answer":"use-result","reason":""}),
        work,
        &source,
        contract,
    ));
    Ok(
        json!({"kind":"agentic-workspace/assignment-result-admission/v1","status":status,"source_revision":source,"assignment_identity":execution["assignment_identity"],"context":execution["context"],"result_use_allowed":status=="admitted-for-use","judgment":{"source":"acting-orchestrator","reason":reason},"execution_custody":execution["custody"],"returned":execution["returned"],"delta":execution["delta"],"requests":[prerequisites],"claim_boundary":{"proof":false,"independent_review":false,"completion":false,"target_quality":false}}),
    )
}
fn request(kind: &str, args: Value, work: &Value, source: &str, contract: &Value) -> Value {
    let owner = contract["owners"]
        .as_array()
        .unwrap()
        .iter()
        .find(|o| o["owner"] == "assignment")
        .unwrap();
    json!({"kind":"agentic-workspace/public-request/v1","id":kind,"owner":"assignment","owner_revision":owner["revision"],"source_revision":source,"capability_revision":contract["revision"],"task_identity":work,"request_kind":kind,"arguments":args})
}
fn validate(value: &Value, work: &Value, source: &str, contract: &Value) -> Result<(), CoreError> {
    crate::prepare_request_value(
        json!({"request":value,"current_work":work,"capability_contract":contract}),
    )?;
    if value["source_revision"] != source {
        return Err(CoreError::new(
            "read-only handoff source/task/requirements changed",
        ));
    }
    Ok(())
}
fn read_inputs(
    target: &Path,
    refs: &Value,
    body: bool,
    baseline: Option<&Value>,
) -> Result<Value, CoreError> {
    let root = cap_std::fs::Dir::open_ambient_dir(target, cap_std::ambient_authority())
        .map_err(|e| CoreError::new(e.to_string()))?;
    let mut inputs = Vec::new();
    let mut size = 0;
    for reference in refs.as_array().into_iter().flatten() {
        let name = reference
            .as_str()
            .ok_or_else(|| CoreError::new("handoff input reference must be text"))?;
        let retained = baseline.and_then(|packet| {
            packet["assignment_identity"]["mutation_paths"]
                .as_array()
                .filter(|v| v.iter().any(|p| p == name))?;
            packet["assignment_identity"]["input_capsule"]
                .as_array()?
                .iter()
                .find(|i| i["reference"] == name)?["content"]
                .as_str()
        });
        let bytes = if let Some(content) = retained {
            content.as_bytes().to_vec()
        } else {
            crate::native_verification::read(&root, name)
                .map_err(|e| CoreError::new(format!("handoff input {name}: {e}")))?
                .ok_or_else(|| CoreError::new(format!("handoff input {name} is missing")))?
        };
        size += bytes.len();
        if size > 262144 {
            return Err(CoreError::new("handoff inputs exceed 256 KiB bound"));
        }
        let content = std::str::from_utf8(&bytes)
            .map_err(|_| CoreError::new(format!("handoff input {name} requires UTF-8 text")))?;
        let mut item =
            json!({"reference":name,"revision":format!("sha256:{:x}",Sha256::digest(&bytes))});
        if body {
            item["content"] = json!(content);
        }
        inputs.push(item);
    }
    Ok(json!(inputs))
}
pub(crate) fn inputs_view(
    target: &Path,
    work: &Value,
    configuration: &Value,
    requirements: &Value,
    submitted: Option<&Value>,
    contract: &Value,
    baseline: Option<&Value>,
) -> Result<Value, CoreError> {
    let patch = requirements["requirements"]["required_result_classes"]
        .as_array()
        .is_some_and(|v| v.iter().any(|c| c == "unapplied-patch"));
    let source = digest(
        &json!({"work":work,"configuration":configuration["revision"],"requirements":requirements}),
    )?;
    let mut template = request(
        if patch {
            PATCH_INPUTS
        } else {
            "assignment/judge-readonly-inputs/v1"
        },
        if patch {
            json!({"input_refs":[],"mutation_paths":[],"complete":false,"reason":""})
        } else {
            json!({"input_refs":[],"complete":false,"reason":""})
        },
        work,
        &source,
        contract,
    );
    let mut inputs = json!([]);
    let mut gaps = Vec::new();
    if let Some(value) = submitted {
        crate::prepare_request_value(
            json!({"request":value,"current_work":work,"capability_contract":contract}),
        )?;
        if value["arguments"]["reason"]
            .as_str()
            .is_none_or(|s| s.trim().is_empty())
        {
            return Err(CoreError::new(
                "read-only input completeness reason required",
            ));
        }
        if value["request_kind"] != template["request_kind"] {
            return Err(CoreError::new(
                "handoff input kind differs from the current result class",
            ));
        }
        for path in value["arguments"]["mutation_paths"]
            .as_array()
            .into_iter()
            .flatten()
        {
            let path = path
                .as_str()
                .ok_or_else(|| CoreError::new("concrete mutation path required"))?;
            crate::native_patch::concrete_source(target, path)?;
            if !value["arguments"]["input_refs"]
                .as_array()
                .is_some_and(|v| v.iter().any(|p| p == path))
            {
                return Err(CoreError::new(
                    "mutation path must have an owner-observed baseline input",
                ));
            }
        }
        match read_inputs(target, &value["arguments"]["input_refs"], false, baseline) {
            Ok(v) => inputs = v,
            Err(e) => gaps.push(e.to_string()),
        }
        let observed_source = digest(
            &json!({"source":source,"input_refs":value["arguments"]["input_refs"],"inputs":inputs,"read_gaps":gaps}),
        )?;
        if value["arguments"]["complete"] == true {
            if value["source_revision"] != observed_source {
                return Err(CoreError::new(
                    "handoff input sources changed or not yet observed; judge the current observed input set",
                ));
            }
        } else {
            if value["source_revision"] != source && value["source_revision"] != observed_source {
                return Err(CoreError::new("handoff input selection source changed"));
            }
            gaps.push("acting-agent-input-completeness-unresolved".to_owned());
        }
        template["source_revision"] = json!(observed_source);
        template["arguments"] = value["arguments"].clone();
        template["arguments"]["complete"] = json!(false);
    } else {
        gaps.push("current-input-completeness-judgment-required".to_owned());
    }
    let revision =
        digest(&json!({"source":source,"judgment":submitted,"inputs":inputs,"gaps":gaps}))?;
    Ok(
        json!({"status":if gaps.is_empty(){"ready"}else{"unresolved"},"revision":revision,"source_revision":source,"inputs":inputs,"gaps":gaps,"request":template,"judgment":submitted.map(|r|&r["arguments"])}),
    )
}
#[allow(clippy::too_many_arguments)]
pub(crate) fn view(
    target: &Path,
    task: &str,
    changed: &[String],
    work: &Value,
    requirements: &Value,
    submitted: &[Value],
    contract: &Value,
    baseline: Option<&Value>,
) -> Result<Value, CoreError> {
    let assessment = &requirements["assignment"]["result"];
    let selected = &assessment["selected"]["configuration"];
    let patch = requirements["result"]["requirements"]["required_result_classes"]
        .as_array()
        .is_some_and(|v| v.iter().any(|c| c == "unapplied-patch"));
    let export_kind = if patch {
        PATCH_EXPORT
    } else {
        "assignment/export-readonly/v1"
    };
    let return_kind = if patch {
        PATCH_RETURN
    } else {
        "assignment/observe-readonly-return/v1"
    };
    let export = submitted.iter().find(|r| r["request_kind"] == export_kind);
    let returned = submitted.iter().find(|r| r["request_kind"] == return_kind);
    let inputs = &requirements["handoff_inputs"];
    let available = assessment["status"] == "assigned-nonlocal-handoff-required"
        && (selected["transport"] == "manual"
            || selected["transport"] == "cli"
                && selected["execution"]["adapter"]["kind"] == "process")
        && inputs["status"] == "ready"
        && requirements["result"]["requirements"]["required_result_classes"]
            .as_array()
            .is_some_and(|classes| {
                classes
                    .iter()
                    .all(|class| class == "read-only" || class == "unapplied-patch")
            });
    if !available {
        if export.is_some() || returned.is_some() {
            return Err(CoreError::new(
                "current eligible read-only assignment required before handoff",
            ));
        }
        return Ok(
            json!({"status":"not-ready","requests":[],"claim_boundary":"No handoff or result admitted."}),
        );
    }
    let identity = &assessment["assignment_identity"];
    let assignment_revision = identity["assignment_decision_revision"].as_str().unwrap();
    let source = digest(&json!({"work":work,"identity":identity,"inputs":inputs["revision"]}))?;
    let mut prerequisites = submitted
        .iter()
        .filter(|r| {
            !matches!(
                r["request_kind"].as_str(),
                Some(
                    "assignment/export-readonly/v1"
                        | "assignment/observe-readonly-return/v1"
                        | "delegation/dispatch/v1"
                        | "delegation/read-result/v1"
                        | "assignment/judge-return/v1"
                        | "planning/adopt-return/v1"
                        | "planning/retain-handoff/v1"
                        | "assignment/integrate-patch/v1"
                        | PATCH_EXPORT
                        | PATCH_RETURN
                )
            )
        })
        .cloned()
        .collect::<Vec<_>>();
    let export_request = request(
        export_kind,
        json!({"assignment_revision":assignment_revision}),
        work,
        &source,
        contract,
    );
    prerequisites.push(export_request.clone());
    if export.is_none() {
        return Ok(
            json!({"status":"export-ready","requests":[prerequisites],"claim_boundary":"Read-only export is current; no dispatch or result exists."}),
        );
    }
    let export = export.unwrap();
    validate(export, work, &source, contract)?;
    if export["arguments"]["assignment_revision"] != assignment_revision {
        return Err(CoreError::new("handoff assignment revision changed"));
    }
    let capsule = read_inputs(target, &inputs["judgment"]["input_refs"], true, baseline)?;
    let mut compact = capsule.clone();
    for item in compact.as_array_mut().unwrap() {
        item.as_object_mut().unwrap().remove("content");
    }
    if compact != inputs["inputs"] {
        return Err(CoreError::new("handoff inputs changed before export"));
    }
    let return_request = request(
        return_kind,
        json!({"returned":null}),
        work,
        &source,
        contract,
    );
    let mut reentry = prerequisites.clone();
    reentry.push(return_request);
    let mut packet = crate::assignment_packet::seal(
        &json!({"kind":"agentic-workspace/assignment-export-packet/v1","assignment_id":format!("assignment:{assignment_revision}"),"assignment_revision":assignment_revision,"run_id":format!("readonly:{assignment_revision}"),"target":selected["target"],"transport":selected["transport"],"scope":changed,
    "assignment_identity":{"revision":assignment_revision,"human_intent":task,"task_class":"","role":requirements["result"]["role"].as_str().unwrap_or("executor"),"scope_class":"read-only","allowed_paths":changed,"allowed_effects":["read-provided-inputs","return-observations"],"prohibited_effects":["write-files","execute-commands","grant-proof","claim-completion"],"required_inputs":inputs["judgment"]["input_refs"],"read_first":inputs["judgment"]["input_refs"],"input_capsule":capsule,"task_requirements":requirements["result"],"proof_obligation_id":requirements["result"]["verification_identity"]["id"].as_str().unwrap_or(""),"proof_obligation_revision":requirements["result"]["verification_identity"]["revision"].as_str().unwrap_or(""),"stop_conditions":["Necessary input absent or ambiguous: return a blocker; do not infer missing parent context.","No file mutation or proof/authority claim is permitted."],"claim_authority":{"proof":false,"completion":false},"current_assignment":identity},
    "return_contract":{"kind":"agentic-workspace/delegated-return/v1","required_fields":["assignment_revision","run_id","target","changed_paths","patch","summary","stop_conditions_hit"],"result_delivery":{"field":"result_delivery","modes":["unapplied-patch"],"default":"unapplied-patch"},"worker_proof_authority":false,"worker_completion_authority":false,"rule":"Return observations with empty changed_paths and patch. Identity matching is not reviewer authentication or evidence sufficiency.","reentry":{"task":task,"changed":changed,"request":reentry}},"packet_integrity":""}),
    )?;
    if patch {
        let paths = &inputs["judgment"]["mutation_paths"];
        for path in paths
            .as_array()
            .into_iter()
            .flatten()
            .filter_map(Value::as_str)
        {
            if !changed
                .iter()
                .any(|pattern| crate::native_verification::matches(pattern, path))
            {
                return Err(CoreError::new(
                    "mutation baseline is outside the current allowed scope",
                ));
            }
        }
        packet["run_id"] = json!(format!("patch:{assignment_revision}"));
        packet["assignment_identity"]["scope_class"] = json!("unapplied-patch");
        packet["assignment_identity"]["mutation_paths"] = paths.clone();
        packet["assignment_identity"]["allowed_effects"] =
            json!(["read-provided-inputs", "return-unapplied-delta"]);
        packet["return_contract"]["rule"] = json!(
            "Return patch as a JSON-encoded array of objects containing only path and diff. Each diff is one canonical unified diff with --- original and +++ modified headers, exact captured baseline line positions, no Git metadata or trailing text. LF and CRLF transport are equivalent. Only the listed concrete mutation paths may change. Return changed_paths equal to the delta paths. Do not modify the checkout. File creation, deletion, binary changes and renames require a different admitted delivery contract."
        );
        packet["return_contract"]["mutation_paths"] = paths.clone();
        packet["return_contract"]["maximum_complete_stdout_bytes"] = json!(65536);
        packet = crate::assignment_packet::seal(&packet)?;
    }
    let schema: Value = serde_json::from_str(include_str!(
        "../../../src/agentic_workspace/contracts/schemas/assignment_worker_context.schema.json"
    ))
    .expect("schema");
    crate::schema_validator(&schema, "worker context")?
        .validate(&packet["worker_context"])
        .map_err(|e| CoreError::new(e.to_string()))?;
    let mut observation = Value::Null;
    if let Some(value) = returned {
        validate(value, work, &source, contract)?;
        let result = &value["arguments"]["returned"];
        if patch {
            crate::native_patch::delta(&packet, result)?;
        }
        for (key, expected) in packet["return_contract"]["required_identity"]
            .as_object()
            .unwrap()
        {
            if &result[key] != expected {
                return Err(CoreError::new(format!(
                    "read-only return {key} does not match current sealed assignment"
                )));
            }
        }
        observation = json!({"status":"current-unproven-observation","returned":result,"assignment_identity":identity,"proof_current":false,"completion_allowed":false,"authenticated_reviewer":false});
    }
    Ok(
        json!({"status":if observation.is_null(){if patch {"exported-patch"} else {"exported-read-only"}}else{"returned-unproven"},"packet":packet,"observation":observation,"requests":[],"claim_boundary":"Seal binds source and assignment integrity only. Return is an unproven observation; local implementation, Verification and Planning completion remain unavailable."}),
    )
}
