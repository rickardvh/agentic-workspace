//! Read-only ingress for existing governing sources and retained interpretation.
use crate::dependency_binding::{self, Basis, Currentness, Observation, Scheme};
use crate::{CoreError, digest};
use cap_std::{ambient_authority, fs::Dir};
use serde_json::{Value, json};
use std::path::Path;
pub(crate) const MIRROR: &str = ".agentic-workspace/system-intent/intent.toml";

pub(crate) fn bytes(root: &Dir, reference: &str) -> Result<Option<Vec<u8>>, CoreError> {
    dependency_binding::read(root, reference)
}
pub(crate) fn hash(bytes: &[u8]) -> String {
    dependency_binding::revision(bytes, Scheme::RawBytes).expect("raw bytes always have a revision")
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
pub(crate) fn stale_references(root: &Dir, declaration: &Value, value: &Value) -> Vec<String> {
    let references: Vec<&str> = declaration["sources"]
        .as_array()
        .into_iter()
        .flatten()
        .filter_map(Value::as_str)
        .collect();
    let preferred = declaration["preferred_source"]
        .as_str()
        .or_else(|| references.first().copied());
    let observed: Vec<_> = references
        .iter()
        .map(|reference| dependency_binding::observe(root, reference, Scheme::UniversalNewlineUtf8))
        .collect();
    // Adapt historical records without rewriting their hashes or review meaning.
    let records: Vec<_> = value["source_records"]
        .as_array()
        .into_iter()
        .flatten()
        .map(|r| Observation {
            identity: r["path"].as_str().unwrap_or("invalid-source-record").into(),
            scheme: Scheme::UniversalNewlineUtf8,
            revision: r["sha256"].as_str().map(|s| format!("sha256:{s}")),
            status: if r["present"] == true {
                Currentness::Current
            } else {
                Currentness::Missing
            },
        })
        .collect();
    // Records are an unordered set. Declaration/preference order still binds
    // the ordinary view and proposal revision.
    let mut observed = observed;
    let mut records = records;
    observed.sort_by(|a, b| a.identity.cmp(&b.identity));
    records.sort_by(|a, b| a.identity.cmp(&b.identity));
    let identity = json!({"owner":"system-intent","subject":MIRROR});
    let comparison = dependency_binding::compare(
        Basis {
            conclusion: &identity,
            dependencies: &observed,
        },
        Some(Basis {
            conclusion: &identity,
            dependencies: &records,
        }),
    );
    let mut stale = comparison.changed;
    if (comparison.membership_changed && comparison.status != Currentness::Current)
        || value["source_records"].as_array().is_none()
    {
        stale.push("source_records".into());
    }
    if value["preferred_source"].as_str() != preferred {
        stale.push("preferred_source".to_owned());
    }
    stale
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
            let stale = stale_references(&root, declaration, &value);
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
    crate::native_intent_write::extend_contract(&mut contract)?;
    let owner_revision = contract["owners"][0]["revision"].clone();
    let validation = full_contract.unwrap_or(&contract);
    let requests:Vec<Value>=sources.iter().filter(|s|s["status"]=="present").map(|source|json!({
        "kind":"agentic-workspace/public-request/v1","id":format!("system-intent/read:{}",source["reference"].as_str().unwrap()),"owner":"system-intent","owner_revision":owner_revision,
        "source_revision":revision,"capability_revision":validation["revision"],"task_identity":work,"request_kind":"system-intent/read-current-source/v1",
        "arguments":{"reference":source["reference"],"revision":source["revision"]}})).collect();
    let mut response = Value::Null;
    if let Some(request) =
        request.filter(|r| r["request_kind"] == "system-intent/read-current-source/v1")
    {
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
        let text = String::from_utf8(detail.clone())
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
        response["source_material"] =
            crate::operating::source_material(&json!(reference), &detail, &text, None);
    }
    let blockers:Vec<Value>=gaps.iter().map(|gap|json!({"code":gap,"message":"Preserve existing governing sources and interpretation; current semantic custody requires owner judgment, not a source rewrite or automatic waiver.","affects":["claim:complete"]})).collect();
    let mut result = json!({"kind":"agentic-workspace/native-system-intent-view/v1","status":if sources.is_empty(){"absent"}else{"source-owned"},"revision":revision,
        "declaration":declaration,"preferred_source":preferred,"sources":sources,"interpretation":interpretation,"gaps":gaps,"requests":requests,"response":response,
        "capability_contract":contract,"contribution":{"owner":"system-intent","revision":revision,"blockers":blockers,"settled":gaps.is_empty(),"material":response},
        "remaining_owner_contract":"Reconcile retained interpretation through the exact source-bound owner proposal. Planning intent_continuity and human acceptance remain separate."});
    crate::native_intent_write::view(
        target,
        work,
        configuration,
        &mut result,
        validation,
        request.filter(|r| r["request_kind"] != "system-intent/read-current-source/v1"),
    )?;
    Ok(result)
}
