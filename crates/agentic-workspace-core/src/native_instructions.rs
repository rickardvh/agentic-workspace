//! Scoped instruction consumption. Source admission, applicability and evidence
//! remain separate; a preferred procedure does not become a hard requirement.
use crate::{
    CoreError, digest, instruction_applicability, instruction_source, native_planning,
    native_verification,
};
use serde_json::{Value, json};
use std::{collections::BTreeSet, path::Path};

fn strings(value: &Value) -> Vec<String> {
    value
        .as_array()
        .into_iter()
        .flatten()
        .filter_map(Value::as_str)
        .map(str::to_owned)
        .collect()
}

fn applicability(metadata: &Value, changed: &[String], route: &Value) -> Result<Value, CoreError> {
    instruction_applicability::view(json!({
        "paths":strings(&metadata["paths"]), "routes":strings(&metadata["routes"]),
        "changed_paths":changed, "selected_routes":strings(&route["routes"]),
        "route_posture":if route["status"] == "current" {route["posture"].as_str().unwrap_or("unresolved")} else {"unresolved"}
    }))
}

fn hard(metadata: &Value) -> bool {
    !strings(&metadata["protect"]).is_empty()
        || metadata["checks"]
            .as_array()
            .into_iter()
            .flatten()
            .any(|check| {
                !check
                    .as_str()
                    .is_some_and(|value| value.starts_with("requirement:"))
            })
}

fn blocker(source: &str, code: &str, message: &str, affects: Vec<String>) -> Value {
    json!({"code":format!("instruction:{source}:{code}"),"message":message,"affects":affects})
}

pub fn resolve(
    target: &Path,
    changed: &[String],
    route: &Value,
    pin: &str,
) -> Result<Value, CoreError> {
    let documents = instruction_source::current_sources(target)?;
    let mut rows = Vec::new();
    let mut blockers = Vec::new();
    let mut scopes: BTreeSet<String> = ["task", "claim:complete", "effect:planning-state"]
        .map(str::to_owned)
        .into();
    for document in documents {
        let reference = document["source"]["reference"].as_str().unwrap();
        let metadata = &document["metadata"];
        let valid = document["valid"] == true;
        let applicable = valid && applicability(metadata, changed, route)?["applies"] == true;
        let binding = if valid && hard(metadata) {
            match instruction_source::view(json!({"target":target,"admitted_revision":pin,
                "sources":[{"reference":reference,"revision":document["source"]["revision"]}]}))
            {
                Ok(value) => value["sources"][0].clone(),
                Err(error) => {
                    json!({"status":"unavailable","diagnostic":error.to_string(),"checks":[],"protect":[]})
                }
            }
        } else {
            json!({"status":"not-required","checks":[],"protect":[]})
        };
        if !valid {
            blockers.push(blocker(reference,"source-unresolved","Current instruction syntax/scope cannot be safely consumed; preserve the source and resolve its owner.",vec!["task".into()]));
        }
        for pattern in strings(&metadata["protect"]) {
            scopes.insert(format!("effect:write:{pattern}"));
            for path in changed
                .iter()
                .filter(|path| native_verification::matches(&pattern, path))
            {
                scopes.insert(format!("effect:write:{path}"));
            }
        }
        if applicable && hard(metadata) {
            let mut affects = Vec::new();
            if metadata["checks"]
                .as_array()
                .into_iter()
                .flatten()
                .any(|check| {
                    !check
                        .as_str()
                        .is_some_and(|value| value.starts_with("requirement:"))
                })
            {
                affects.push("claim:complete".into());
            }
            for pattern in strings(&metadata["protect"]) {
                affects.push(format!("effect:write:{pattern}"));
                affects.extend(
                    changed
                        .iter()
                        .filter(|path| native_verification::matches(&pattern, path))
                        .map(|path| format!("effect:write:{path}")),
                );
            }
            affects.sort();
            affects.dedup();
            if !affects.is_empty() {
                blockers.push(blocker(reference,if binding["status"]=="current" {"current-binding"} else {"binding-unadmitted"},
                    if binding["status"]=="current" {"Current repository protection/check obligations remain binding; no proof success is inferred."} else {"Current hard instruction intent requires source admission before affected behavior."},affects));
            }
        }
        let guidance = if applicable {
            instruction_source::current_document(target, reference, true)?["body"].clone()
        } else {
            json!("")
        };
        rows.push(json!({"source":document["source"],"metadata":metadata,"valid":valid,"applicable":applicable,
            "guidance":guidance,"read":if applicable {metadata["read"].clone()} else {json!([])},
            "preferred_procedures":if applicable {metadata["use"].clone()} else {json!([])},
            "requirement_references":if applicable {json!(strings(&metadata["checks"]).into_iter().filter(|value| value.starts_with("requirement:")).collect::<Vec<_>>())} else {json!([])},
            "binding_admission":binding}));
    }
    let revision = digest(&json!({"sources":rows,"route":route,"changed":changed}))?;
    let mut contract = json!({"kind":"agentic-workspace/capability-contract/v1","revision":"pending",
        "owners":[{"owner":"scoped-instructions","revision":"native-scoped-instructions/v1"}],
        "restriction_authorities":[{"owner":"scoped-instructions","affects":scopes}]});
    contract["revision"] = json!(digest(&contract)?);
    Ok(
        json!({"kind":"agentic-workspace/native-instruction-view/v1","sources":rows,"revision":revision,
        "capability_contract":contract,"contribution":{"owner":"scoped-instructions","revision":revision,"blockers":blockers},
        "authority_boundary":"read/guidance surface context; use prefers a replaceable procedure; requirement references retain their owner; only admitted checks/protect bind and none grants proof or execution"}),
    )
}

pub fn restrict_pending(
    view: &mut Value,
    pending: &[Value],
    route: &Value,
) -> Result<(), CoreError> {
    let mut additions = Vec::new();
    for action in pending.iter().filter(|action| {
        action["source_owner"] == "planning" && action["operation_id"] == "planning.reconcile"
    }) {
        let writes = native_planning::write_scope(action)?;
        for source in view["sources"].as_array().into_iter().flatten() {
            let metadata = &source["metadata"];
            let patterns = strings(&metadata["paths"]);
            if source["valid"] != true
                || applicability(metadata, &[], route)?["route_applies"] != true
                || !(patterns.is_empty()
                    || patterns.iter().any(|pattern| {
                        writes
                            .iter()
                            .any(|path| instruction_applicability::patterns_overlap(pattern, path))
                    }))
            {
                continue;
            }
            if strings(&metadata["protect"]).iter().any(|pattern| {
                writes
                    .iter()
                    .any(|path| instruction_applicability::patterns_overlap(pattern, path))
            }) {
                additions.push(blocker(source["source"]["reference"].as_str().unwrap(),"protected-planning-write",
                    "The current Planning operation would write protected repository state; preserve the source and resolve that restriction before execution.",vec!["effect:planning-state".into()]));
            }
            if metadata["checks"]
                .as_array()
                .into_iter()
                .flatten()
                .any(|check| {
                    !check
                        .as_str()
                        .is_some_and(|value| value.starts_with("requirement:"))
                })
            {
                additions.push(blocker(source["source"]["reference"].as_str().unwrap(),"planning-write-checks",
                    "Current repository checks apply to this Planning write and still require Verification evidence.",vec!["claim:complete".into()]));
            }
        }
    }
    view["contribution"]["blockers"]
        .as_array_mut()
        .unwrap()
        .extend(additions);
    Ok(())
}
