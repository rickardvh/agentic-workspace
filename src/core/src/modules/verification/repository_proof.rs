//! Bounded repository observation, produced only from exact local execution.
//! Repository admission is source-owner provenance, not local effect recovery
//! or independent attestation. Machine locators never define portable identity.
use crate::{CoreError, digest};
use cap_std::{ambient_authority, fs::Dir};
use serde_json::{Value, json};
use std::path::Path;

const KIND: &str = "agentic-workspace/repository-proof/v1";
fn err(e: impl ToString) -> CoreError {
    CoreError::new(e.to_string())
}
pub(crate) fn is_repository(receipt: &Value) -> bool {
    receipt["repository_proof"]["kind"] == KIND
}

/// A positive publication decision needs current owner-authored material.
/// Retention's conservative raw-reference scan is deliberately not used here.
pub(crate) fn consumer(target: &Path, path: &str, reference: &str) -> Result<Value, CoreError> {
    crate::decision_source::relative(path)?;
    if !path.starts_with(".agentic-workspace/planning/execplans/") || !path.ends_with(".plan.json")
    {
        return Err(err("durable consumer requires an admitted Planning owner"));
    }
    let root = Dir::open_ambient_dir(target, ambient_authority()).map_err(err)?;
    let bytes = crate::native_planning::read(&root, path)?
        .ok_or_else(|| err("durable consumer missing"))?;
    let body: Value = serde_json::from_slice(&bytes).map_err(err)?;
    let current = if body.get("update_provenance").is_some() {
        crate::native_planning_update::inspect(target, path, &body)?;
        crate::native_planning_update::portable_observation(path, &body)?
    } else {
        crate::native_planning_create::inspect_origin(target, path, &body)?;
        crate::native_planning_create::portable_observation(path, &body)?
    };
    if !current
        || !(body["references"]
            .as_array()
            .is_some_and(|v| v.contains(&json!(reference)))
            || body["proof"].to_string().contains(reference))
    {
        return Err(err(
            "durable consumer requires a current owner-admitted exact proof reference",
        ));
    }
    Ok(
        json!({"owner":"planning","path":path,"revision":digest(&body)?,"id":body["id"],"reference":reference}),
    )
}

pub(crate) fn runtime(value: &Value) -> Value {
    let mut value = value.clone();
    for field in ["producer", "shell"] {
        if let Some(binary) = value[field].as_object_mut() {
            binary.remove("path");
        }
    }
    if let Some(executor) = value["executor"].as_object_mut() {
        executor.remove("daemon");
        if let Some(transport) = executor.get_mut("transport").and_then(Value::as_object_mut) {
            transport.remove("path");
        }
    }
    value
}
fn subject(value: &Value) -> Result<Value, CoreError> {
    let mut value = value.clone();
    value["runtime"] = runtime(&value["runtime"]);
    let mut identity = serde_json::Map::new();
    for key in [
        "claim_classes",
        "effect_scope",
        "source_inputs",
        "command_sha256",
        "runtime",
        "identity_complete",
        "unavailable_inputs",
    ] {
        identity.insert(key.into(), value[key].clone());
    }
    let fingerprint = crate::proof_subject::fingerprint(&json!(identity))?;
    value["id"] = json!(format!("proof-subject:{}", &fingerprint[..20]));
    value["fingerprint"] = json!(fingerprint);
    Ok(value)
}
fn absolute(value: &Value) -> bool {
    match value {
        Value::String(s) => {
            s.split([' ', '\t', '\n', '"', '\'', '='])
                .any(|part| part.starts_with('/'))
                || s.starts_with("\\\\")
                || s.as_bytes().windows(3).enumerate().any(|(i, w)| {
                    (i == 0 || !s.as_bytes()[i - 1].is_ascii_alphanumeric())
                        && w[0].is_ascii_alphabetic()
                        && w[1] == b':'
                        && matches!(w[2], b'/' | b'\\')
                })
        }
        Value::Array(v) => v.iter().any(absolute),
        Value::Object(v) => v.values().any(absolute),
        _ => false,
    }
}
fn payload(receipt: &Value) -> Value {
    let mut value = receipt.clone();
    value["repository_proof"]
        .as_object_mut()
        .unwrap()
        .remove("revision");
    value.as_object_mut().unwrap().remove("publication_custody");
    value
}

/// A historical stable reference remains stable; the attested projection binds
/// both its original content identity and its portable representation.
pub(crate) fn project(
    target: &Path,
    receipt: &Value,
    consumer: &Value,
) -> Result<Value, CoreError> {
    let committed = crate::native_proof::committed_publication(target, receipt)?
        .ok_or_else(|| err("repository proof requires committed original execution"))?;
    let root = Dir::open_ambient_dir(target, ambient_authority()).map_err(err)?;
    let artifact = &receipt["execution_artifact"];
    let bytes = crate::native_planning::read(
        &root,
        artifact["path"]
            .as_str()
            .ok_or_else(|| err("execution detail missing"))?,
    )?
    .ok_or_else(|| err("execution detail unavailable"))?;
    if crate::native_intent::hash(&bytes)
        != format!("sha256:{}", artifact["sha256"].as_str().unwrap_or(""))
    {
        return Err(err("execution detail changed before repository promotion"));
    }
    let detail: Value = serde_json::from_slice(&bytes).map_err(err)?;
    let mut projected = serde_json::Map::new();
    for key in [
        "kind",
        "command",
        "result",
        "changed_paths",
        "recorded_at",
        "revision",
        "producer_class",
        "authority",
        "receipt_id",
        "publication_id",
        "source_ref",
    ] {
        projected.insert(key.into(), receipt[key].clone());
    }
    let mut projected = json!(projected);
    projected["proof_subject"] = subject(&receipt["proof_subject"])?;
    // A bounded process summary is sufficient for selected-command proof.
    // Raw output and optional measurement extraction remain local-only.
    projected["execution_artifact"] =
        json!({"sha256":artifact["sha256"],"scope":"repository-summary"});
    let selection = &committed["invocation"]["arguments"]["selection"];
    projected["repository_proof"] = json!({"kind":KIND,"owner":"verification",
        "origin":{"receipt_id":receipt["receipt_id"],"receipt_revision":digest(receipt)?,"subject_fingerprint":receipt["proof_subject"]["fingerprint"],"runtime_revision":digest(&receipt["proof_subject"]["runtime"])?},
        "producer":{"invocation_revision":digest(&committed["invocation"])?,"outcome_revision":digest(&committed["outcome"])?},
        "selection":{"choice":selection["choice"],"strategy":selection["strategy"],"work":selection["work"]},
        "consumer":consumer,"process":{"status":detail["status"],"exit_code":detail["exit_code"],"timed_out":detail["timed_out"]},
        "authority":"repository-owned observation; no independent review or local effect recovery"});
    if projected["repository_proof"]["process"]["status"] != receipt["result"]
        || absolute(&projected)
    {
        return Err(err(
            "repository proof projection is inconsistent or contains machine paths",
        ));
    }
    projected["repository_proof"]["revision"] = json!(digest(&payload(&projected))?);
    Ok(projected)
}

pub(crate) fn validate(receipt: &Value) -> Result<(), CoreError> {
    let held = &receipt["repository_proof"];
    if !is_repository(receipt)
        || !receipt["receipt_id"]
            .as_str()
            .is_some_and(|id| id.len() == 16 && id.bytes().all(|b| b.is_ascii_hexdigit()))
        || !held["consumer"].is_object()
        || held["consumer"]["dependencies"]
            .as_array()
            .is_some_and(|chain| {
                chain.len() > 32
                    || chain.iter().any(|v| {
                        !v.as_str().is_some_and(|s| {
                            s.len() == 16 && s.bytes().all(|b| b.is_ascii_hexdigit())
                        })
                    })
            })
        || held["owner"] != "verification"
        || held["revision"] != digest(&payload(receipt))?
        || held["origin"]["receipt_id"] != receipt["receipt_id"]
        || held["selection"]["choice"]["command"] != receipt["command"]
        || held["process"]["status"] != receipt["result"]
        || subject(&receipt["proof_subject"])? != receipt["proof_subject"]
        || absolute(&payload(receipt))
    {
        return Err(err("repository proof owner projection invalid"));
    }
    for value in [
        &held["producer"]["invocation_revision"],
        &held["producer"]["outcome_revision"],
        &held["origin"]["receipt_revision"],
        &held["origin"]["runtime_revision"],
    ] {
        if !value.as_str().is_some_and(|s| {
            s.starts_with("sha256:")
                && s.len() == 71
                && s[7..].bytes().all(|b| b.is_ascii_hexdigit())
        }) {
            return Err(err("repository proof producer identity missing"));
        }
    }
    Ok(())
}

pub(crate) fn selection(target: &Path, receipt: &Value) -> Result<Value, CoreError> {
    validate(receipt)?;
    let held = &receipt["repository_proof"];
    // The declaration is validated through its owner on every fresh claim.
    let observed = consumer(
        target,
        held["consumer"]["path"].as_str().unwrap_or(""),
        held["consumer"]["reference"].as_str().unwrap_or(""),
    )?;
    let mut expected = held["consumer"].clone();
    let chain = expected
        .as_object_mut()
        .unwrap()
        .remove("dependencies")
        .unwrap_or(json!([]));
    if observed != expected {
        return Err(err("repository proof consumer changed"));
    }
    let mut reference = observed["reference"].as_str().unwrap().to_owned();
    let root = Dir::open_ambient_dir(target, ambient_authority()).map_err(err)?;
    for child in chain
        .as_array()
        .ok_or_else(|| err("repository dependency chain invalid"))?
    {
        let id = reference
            .strip_prefix("proof://receipts/")
            .ok_or_else(|| err("repository dependency reference invalid"))?;
        let bytes = crate::native_planning::read(
            &root,
            &format!(".agentic-workspace/proof/receipts/{id}.json"),
        )?
        .ok_or_else(|| err("repository dependency missing"))?;
        let parent: Value = serde_json::from_slice(&bytes).map_err(err)?;
        validate(&parent)?;
        let child = child
            .as_str()
            .ok_or_else(|| err("repository dependency identity invalid"))?;
        if !parent["changed_paths"].as_array().is_some_and(|p| {
            p.contains(&json!(format!(
                ".agentic-workspace/proof/receipts/{child}.json"
            )))
        }) {
            return Err(err("repository dependency no longer referenced"));
        }
        reference = format!("proof://receipts/{child}");
    }
    if reference
        != format!(
            "proof://receipts/{}",
            receipt["receipt_id"].as_str().unwrap_or("")
        )
    {
        return Err(err("repository consumer names different proof"));
    }
    Ok(held["selection"].clone())
}

/// Existing owner-authored Planning references root the historical dependency
/// closure. Only authenticated executions are converted; unknown classes stay
/// protected. This is a format transfer under the existing disposition owner.
pub(crate) fn transfers(
    target: &Path,
    sources: &std::collections::BTreeMap<String, Vec<u8>>,
) -> Result<Value, CoreError> {
    let mut result = serde_json::Map::new();
    let mut gaps = Vec::new();
    let mut pending = Vec::new();
    for (path, bytes) in sources {
        if !path.starts_with(".agentic-workspace/proof/receipts/") {
            continue;
        }
        let Ok(receipt) = serde_json::from_slice::<Value>(bytes) else {
            continue;
        };
        if is_repository(&receipt)
            || crate::native_proof::committed_publication(target, &receipt)
                .ok()
                .flatten()
                .is_none()
        {
            continue;
        }
        let reference = format!(
            "proof://receipts/{}",
            receipt["receipt_id"].as_str().unwrap_or("")
        );
        for candidate in sources.keys().filter(|p| {
            p.starts_with(".agentic-workspace/planning/execplans/")
                && String::from_utf8_lossy(&sources[*p]).contains(&reference)
        }) {
            match consumer(target, candidate, &reference) {
                Ok(owner) => {
                    pending.push((path.clone(), owner));
                    break;
                }
                Err(error) => gaps
                    .push(json!({"source":path,"consumer":candidate,"reason":error.to_string()})),
            }
        }
    }
    while let Some((path, owner)) = pending.pop() {
        if result.contains_key(&path) {
            continue;
        }
        if result.len() >= 32 {
            return Err(err("repository proof dependency closure exceeds bound"));
        }
        let Some(bytes) = sources.get(&path) else {
            continue;
        };
        let original: Value = serde_json::from_slice(bytes).map_err(err)?;
        if is_repository(&original) {
            continue;
        }
        let projected = match project(target, &original, &owner) {
            Ok(value) => value,
            Err(error) => {
                gaps.push(json!({"source":path,"reason":error.to_string()}));
                continue;
            }
        };
        for child in original["changed_paths"]
            .as_array()
            .into_iter()
            .flatten()
            .filter_map(Value::as_str)
        {
            let Some(id) = child
                .strip_prefix(".agentic-workspace/proof/receipts/")
                .and_then(|p| p.strip_suffix(".json"))
            else {
                continue;
            };
            if id.len() != 16 || child == path {
                continue;
            }
            let mut inherited = owner.clone();
            if inherited.get("dependencies").is_none() {
                inherited["dependencies"] = json!([]);
            }
            inherited["dependencies"]
                .as_array_mut()
                .unwrap()
                .push(json!(id));
            pending.push((child.to_owned(), inherited));
        }
        result.insert(path, json!({"before_revision":crate::native_intent::hash(bytes),"receipt":projected,"local_path":format!("{}.receipt.json",original["source_ref"].as_str().unwrap())}));
    }
    Ok(json!({"transfers":result,"gaps":gaps}))
}

pub(crate) fn published(
    target: &Path,
    original: &Value,
    invocation: &Value,
) -> Result<Value, CoreError> {
    let mut projected = project(
        target,
        original,
        &invocation["arguments"]["selection"]["promotion"]["consumer"],
    )?;
    let local = format!(
        "{}.publication.json",
        crate::native_proof::run_path(invocation)?
    );
    let mut custody = original["publication_custody"]["custody"].clone();
    for field in ["attempt", "committed"] {
        custody[field]["target"] = json!(".");
    }
    projected["publication_custody"] = json!({"kind":"agentic-workspace/proof-publication-custody/v2",
        "custody":custody,"local_carrier":local,"local_revision":digest(original)?,
        "index_sha256":original["publication_custody"]["outcome"]["value"]["publication"]["index_sha256"]});
    Ok(projected)
}

pub(crate) fn publication_original(target: &Path, receipt: &Value) -> Result<Value, CoreError> {
    validate(receipt)?;
    let root = Dir::open_ambient_dir(target, ambient_authority()).map_err(err)?;
    let held = &receipt["publication_custody"];
    let path = held["local_carrier"]
        .as_str()
        .ok_or_else(|| err("publication recovery carrier missing"))?;
    if !path.starts_with(".agentic-workspace/local/proof-receipts/runs/native-")
        || !path.ends_with("/run.json.publication.json")
    {
        return Err(err("publication recovery carrier invalid"));
    }
    let bytes = crate::native_planning::read(&root, path)?
        .ok_or_else(|| err("local publication recovery unavailable"))?;
    let original: Value = serde_json::from_slice(&bytes).map_err(err)?;
    if digest(&original)? != held["local_revision"]
        || original["receipt_id"] != receipt["receipt_id"]
    {
        return Err(err("local publication recovery changed"));
    }
    Ok(original)
}
