//! Read-only ingress for existing governing sources and retained interpretation.
use crate::{CoreError, digest};
use cap_std::{ambient_authority, fs::Dir};
use serde_json::{Value, json};
use sha2::{Digest, Sha256};
use std::path::Path;
const MIRROR: &str = ".agentic-workspace/system-intent/intent.toml";

pub(crate) fn bytes(root: &Dir, reference: &str) -> Result<Option<Vec<u8>>, CoreError> {
    crate::native_verification::read(root, reference).map_err(CoreError::new)
}
pub(crate) fn hash(bytes: &[u8]) -> String {
    format!("sha256:{:x}", Sha256::digest(bytes))
}
pub(crate) fn observation(root: &Dir, reference: &str) -> Value {
    match bytes(root, reference) {
        Ok(Some(bytes)) => {
            json!({"reference":reference,"revision":hash(&bytes),"bytes":bytes.len(),"status":"present"})
        }
        Ok(None) => json!({"reference":reference,"status":"missing"}),
        Err(error) => {
            json!({"reference":reference,"status":"unavailable","reason":error.to_string()})
        }
    }
}
pub(crate) fn view(
    target: &Path,
    work: &Value,
    configuration: &Value,
    request: Option<&Value>,
    full_contract: Option<&Value>,
) -> Result<Value, CoreError> {
    let root = Dir::open_ambient_dir(target, ambient_authority())
        .map_err(|e| CoreError::new(e.to_string()))?;
    let declaration = &configuration["system_intent"];
    let references: Vec<&str> = declaration["sources"]
        .as_array()
        .into_iter()
        .flatten()
        .filter_map(Value::as_str)
        .collect();
    let preferred = declaration["preferred_source"]
        .as_str()
        .or_else(|| references.first().copied());
    let mut sources: Vec<Value> = references
        .iter()
        .map(|reference| observation(&root, reference))
        .collect();
    let mirror = observation(&root, MIRROR);
    let mut gaps: Vec<String> = sources
        .iter()
        .filter(|s| s["status"] != "present")
        .map(|s| {
            format!(
                "governing-source-unavailable:{}",
                s["reference"].as_str().unwrap()
            )
        })
        .collect();
    if preferred.is_some_and(|p| !references.contains(&p)) {
        gaps.push("preferred-source-outside-declaration".into());
    }
    let mut interpretation = json!({"status":"absent","alignment":"unresolved-owner-judgment"});
    if mirror["status"] != "missing" {
        sources.push(mirror.clone());
        interpretation["status"] = json!("unavailable");
        let parsed = bytes(&root, MIRROR)
            .ok()
            .flatten()
            .and_then(|b| String::from_utf8(b).ok())
            .and_then(|text| toml::from_str::<toml::Value>(&text).ok())
            .and_then(|value| serde_json::to_value(value).ok());
        if let Some(value) = parsed.filter(|v| {
            v["kind"] == "agentic-workspace/system-intent/v1" && v["schema_version"] == 1
        }) {
            let mut stale = Vec::new();
            for reference in &references {
                let record = value["source_records"]
                    .as_array()
                    .into_iter()
                    .flatten()
                    .find(|r| r["path"] == *reference);
                // Historical source_records hash Python universal-newline text.
                let observed = bytes(&root, reference)
                    .ok()
                    .flatten()
                    .and_then(|b| String::from_utf8(b).ok())
                    .map(|text| {
                        let normalized = text.replace("\r\n", "\n").replace('\r', "\n");
                        format!("{:x}", Sha256::digest(normalized.as_bytes()))
                    });
                if !record.is_some_and(|r| {
                    r["present"] == true
                        && r["sha256"].as_str() == observed.as_deref()
                        && observed.is_some()
                }) {
                    stale.push(*reference);
                }
            }
            for record in value["source_records"].as_array().into_iter().flatten() {
                if let Some(reference) = record["path"].as_str() {
                    if !references.contains(&reference) {
                        stale.push(reference);
                    }
                } else {
                    stale.push("invalid-source-record");
                }
            }
            if value["preferred_source"].as_str() != preferred {
                stale.push("preferred_source");
            }
            let unreviewed = value["needs_review"] != false;
            interpretation = json!({"status":"retained","source":mirror,"source_currentness":if stale.is_empty(){"matched"}else{"stale-or-unproven"},"stale_references":stale,
                "recorded_review_status":if unreviewed{"needs-review-or-unproven"}else{"recorded-no-review-needed"},
                "alignment":"unresolved-owner-judgment","detail_fields":["summary","governing_intents","anti_intents","decision_tests","open_questions","interpretation_notes","confidence","needs_review","source_records"]});
            if !stale.is_empty() {
                gaps.push("retained-interpretation-source-currentness-unproven".into());
            }
            if unreviewed {
                gaps.push("retained-interpretation-review-unresolved".into());
            }
        } else {
            gaps.push("retained-interpretation-invalid-or-unavailable".into());
        }
    }
    let revision = digest(
        &json!({"declaration":declaration,"sources":sources,"interpretation":interpretation}),
    )?;
    let schema = crate::source_schema();
    let mut arguments = schema["$defs"]["system_intent_read_arguments"].clone();
    arguments["$schema"] = schema["$schema"].clone();
    let shape = json!({"kind":"system-intent/read-current-source/v1","result_kind":"agentic-workspace/system-intent-source-read/v1","input_schema":arguments});
    let owner_revision = digest(&shape)?;
    let mut contract = json!({"kind":"agentic-workspace/capability-contract/v1","revision":"pending","owners":[{"owner":"system-intent","revision":owner_revision,"requests":[shape]}],
        "restriction_authorities":[{"owner":"system-intent","affects":["claim:complete"]}]});
    contract["revision"] = json!(digest(&contract)?);
    let validation = full_contract.unwrap_or(&contract);
    let requests:Vec<Value>=sources.iter().filter(|s|s["status"]=="present").map(|source|json!({
        "kind":"agentic-workspace/public-request/v1","id":format!("system-intent/read:{}",source["reference"].as_str().unwrap()),"owner":"system-intent","owner_revision":owner_revision,
        "source_revision":revision,"capability_revision":validation["revision"],"task_identity":work,"request_kind":"system-intent/read-current-source/v1",
        "arguments":{"reference":source["reference"],"revision":source["revision"]}})).collect();
    let mut response = Value::Null;
    if let Some(request) = request {
        let admitted = crate::prepare_request_value(
            json!({"request":request,"current_work":work,"capability_contract":validation}),
        )?;
        if request["owner"] != "system-intent"
            || request["source_revision"] != revision
            || !requests
                .iter()
                .any(|r| r["arguments"] == request["arguments"])
        {
            return Err(CoreError::new(
                "system-intent read is stale or outside current declared sources",
            ));
        }
        let reference = request["arguments"]["reference"].as_str().unwrap();
        let detail = bytes(&root, reference)?
            .ok_or_else(|| CoreError::new("governing source disappeared"))?;
        if hash(&detail) != request["arguments"]["revision"] {
            return Err(CoreError::new("governing source changed during read"));
        }
        let text = String::from_utf8(detail)
            .map_err(|_| CoreError::new("governing source is not UTF-8"))?;
        let current_configuration = crate::native_config::view(target)?;
        if current_configuration["revision"] != configuration["revision"] {
            return Err(CoreError::new(
                "system-intent configuration changed during read",
            ));
        }
        let fresh = view(target, work, &current_configuration, None, None)?;
        if fresh["revision"] != revision {
            return Err(CoreError::new("system-intent sources changed during read"));
        }
        response = json!({"kind":"agentic-workspace/system-intent-source-read/v1","status":"read","request_identity":admitted["identity"],"source":request["arguments"],"text":text,
            "authority_boundary":"Existing governing source content for acting-agent judgment; reading grants no alignment, proof, human acceptance or mutation authority."});
    }
    let blockers:Vec<Value>=gaps.iter().map(|gap|json!({"code":gap,"message":"Preserve existing governing sources and interpretation; current semantic custody requires owner judgment, not a source rewrite or automatic waiver.","affects":["claim:complete"]})).collect();
    Ok(
        json!({"kind":"agentic-workspace/native-system-intent-view/v1","status":if sources.is_empty(){"absent"}else{"source-owned"},"revision":revision,
        "declaration":declaration,"preferred_source":preferred,"sources":sources,"interpretation":interpretation,"gaps":gaps,"requests":requests,"response":response,
        "capability_contract":contract,"contribution":{"owner":"system-intent","revision":revision,"blockers":blockers,"settled":gaps.is_empty(),"material":response},
        "remaining_owner_contract":"Typed Planning update for newly judged larger-outcome alignment remains unavailable; existing intent_continuity is preserved."}),
    )
}
