//! Terminal Proof source disposition. Historical location is discovery, never
//! deletion authority. Exact agent judgement, live references and effect custody
//! remain separate. Recovery is local and does not require a tracked tombstone.
use crate::{CoreError, digest};
use cap_std::{
    ambient_authority,
    fs::{Dir, OpenOptions},
};
use serde_json::{Value, json};
use std::{collections::BTreeMap, io::Write, path::Path};

pub(crate) const REQUEST: &str = "verification/retire-receipts/v1";
pub(crate) const RECOVER: &str = "verification/recover-retirement/v1";
pub(crate) const OP: &str = "verification.retire-receipts";
pub(crate) const RECOVERY: &str = "verification.recover-retirement";
const HOME: &str = ".agentic-workspace/proof/receipts/";
const PENDING: &str = ".agentic-workspace/local/verification/retire-receipts.json";
const LIMIT: usize = 32;
const INDEX: &str = ".agentic-workspace/proof/receipts/index.json";
const CARRIER: &str = ".agentic-workspace/proof/current/index-custody.json";

fn temporary(invocation: &Value) -> Result<String, CoreError> {
    Ok(format!(
        "{PENDING}.{}.tmp",
        &digest(effect_identity(invocation))?[7..]
    ))
}
fn effect_identity(action: &Value) -> &Value {
    action
        .get("idempotency_key")
        .unwrap_or(&action["logical_effect_id"])
}

fn err(e: impl ToString) -> CoreError {
    CoreError::new(e.to_string())
}
fn read(root: &Dir, path: &str) -> Result<Option<Vec<u8>>, CoreError> {
    crate::native_planning::read(root, path)
}
fn revision(bytes: &[u8]) -> String {
    crate::native_intent::hash(bytes)
}
fn record_bytes(record: &Value) -> Result<Vec<u8>, CoreError> {
    let bytes = serde_json::to_vec(record).map_err(err)?;
    if bytes.len() > crate::decision_source::MAX_SOURCE_BYTES {
        return Err(err(
            "Proof retirement recovery exceeds source bound; preserved",
        ));
    }
    Ok(bytes)
}

pub(crate) fn declarations() -> Vec<Value> {
    vec![
        json!({"kind":REQUEST,"result_kind":"agentic-workspace/proof-retirement/v1","input_schema":{
        "$schema":"https://json-schema.org/draft/2020-12/schema","type":"object","additionalProperties":false,
        "properties":{"sources":{"type":"array","minItems":0,"maxItems":32,"uniqueItems":true,"items":{"type":"string"}},
        "superseded":{"type":"boolean"},"no_unresolved_intent":{"type":"boolean"},"no_continuing_value":{"type":"boolean"},
        "reason":{"type":"string","maxLength":2048}},
        "required":["sources","superseded","no_unresolved_intent","no_continuing_value","reason"]}}),
        json!({"kind":RECOVER,"result_kind":"agentic-workspace/proof-retirement/v1","input_schema":{
        "$schema":"https://json-schema.org/draft/2020-12/schema","type":"object","additionalProperties":false,
        "properties":{"record_revision":{"type":"string"}},"required":["record_revision"]}}),
    ]
}
pub(crate) fn operations() -> Vec<Value> {
    [OP,RECOVERY].into_iter().map(|id| json!({"id":id,"semantic_revision":"proof-retirement-v1",
        "input_schema":{"$schema":"https://json-schema.org/draft/2020-12/schema","type":"object","additionalProperties":false,
        "properties":{"target":{"type":"string"},"request":{"type":"object"},"binding":{"type":"object"}},
        "required":["target","request","binding"]},"result_kind":"agentic-workspace/proof-retirement/v1",
        "effects":["proof-execution"],"reads":["verification"]})).collect()
}

use crate::retention_sources::files;

fn candidate(path: &str, bytes: &[u8]) -> bool {
    path.starts_with(HOME)
        && path.ends_with(".json")
        && path != INDEX
        && serde_json::from_slice::<Value>(bytes).is_ok()
}

fn observe_sources(root: &Dir) -> Result<BTreeMap<String, Vec<u8>>, CoreError> {
    let mut sources = BTreeMap::new();
    for path in [
        ".agentic-workspace/planning",
        ".agentic-workspace/proof",
        ".agentic-workspace/memory",
        ".agentic-workspace/verification",
        ".agentic-workspace/evaluations",
        ".agentic-workspace/reconstruction",
        ".agentic-workspace/system-intent",
        ".agentic-workspace/instructions",
    ] {
        files(root, path, &mut sources)?;
    }
    // Local selection and work continuation are consumers, not disposable history.
    for path in [
        ".agentic-workspace/config.toml",
        ".agentic-workspace/config.local.toml",
        "AGENTS.md",
        "SYSTEM_INTENT.md",
        ".agentic-workspace/evaluations.json",
        ".agentic-workspace/delegation-outcomes.json",
        ".agentic-workspace/local/planning/owner-selection.json",
        ".agentic-workspace/local/work-threads/index.json",
    ] {
        if let Some(bytes) = read(root, path)? {
            sources.insert(path.into(), bytes);
        }
    }
    sources.remove(&format!("{INDEX}.retirement.tmp"));
    sources.remove(&format!("{CARRIER}.tmp"));
    Ok(sources)
}

fn inventory(target: &Path) -> Result<Value, CoreError> {
    let root = Dir::open_ambient_dir(target, ambient_authority()).map_err(err)?;
    let sources = observe_sources(&root)?;
    let index_bytes = read(&root, INDEX)?;
    let index: Value = match &index_bytes {
        Some(bytes) => serde_json::from_slice(bytes).map_err(err)?,
        None => json!({"kind":"agentic-workspace/trusted-producer-receipt-index/v1","receipts":{}}),
    };
    if index["kind"] != "agentic-workspace/trusted-producer-receipt-index/v1"
        || index["receipts"].as_object().is_none_or(|o| o.len() > 2048)
    {
        return Err(err(
            "Unrecognised proof index preserved; exact owner transfer unavailable",
        ));
    }
    let carrier = read(&root, CARRIER)?;
    let transfer = index_bytes.is_some()
        && index.get("current_publication").is_none()
        && carrier.as_ref().is_none_or(|bytes| {
            serde_json::from_slice::<Value>(bytes)
                .is_ok_and(|value| value.get("target_revision").is_none())
        });
    let references: BTreeMap<_, _> = sources
        .iter()
        .filter(|(p, _)| p.as_str() != INDEX && p.as_str() != CARRIER)
        .map(|(p, b)| {
            (
                p,
                serde_json::from_slice::<Value>(b)
                    .ok()
                    .map(|v| v.to_string())
                    .unwrap_or_else(|| String::from_utf8_lossy(b).into_owned()),
            )
        })
        .collect();
    let mut offered = serde_json::Map::new();
    let mut protected = Vec::new();
    for (path, bytes) in &sources {
        if !candidate(path, bytes) {
            continue;
        }
        let body: Value = serde_json::from_slice(bytes).map_err(err)?;
        // Native carriers require a committed producer. Legacy shape supplies no
        // custody; exact agent disposition below transfers only removal authority.
        let uncertain = if body.get("publication_custody").is_some() {
            crate::proof_publication::retention_committed(target, &body).is_err()
        } else if body["invocation"]["operation_id"] == crate::native_source_reconciliation::OP {
            !crate::native_source_reconciliation::retention_committed(target, path, &body)?
        } else if body.get("invocation").is_some() || body.get("custody").is_some() {
            true
        } else if body["proof_subject"]["runtime"]["implementation"] == "native-aw-proof" {
            !matches!(
                crate::native_proof::committed_publication(target, &body),
                Ok(Some(_))
            )
        } else {
            false
        };
        let reusable = crate::proof_publication::retention_reusable(target, &body).unwrap_or(true);
        let id = path.strip_prefix(HOME).unwrap().trim_end_matches(".json");
        let consumers: Vec<_> = references
            .iter()
            .filter(|(p, b)| {
                p.as_str() != path
                    && (b.contains(path)
                        || b.contains(&format!("proof://receipts/{id}"))
                        || (id.len() >= 16 && b.contains(id)))
            })
            .map(|(p, _)| (*p).clone())
            .collect();
        if !uncertain && !reusable && consumers.is_empty() && offered.len() < LIMIT {
            offered.insert(path.clone(), json!(revision(bytes)));
        } else if (uncertain || reusable || !consumers.is_empty()) && protected.len() < LIMIT {
            protected.push(json!({"source":path,"uncertain_producer":uncertain,"reusable":reusable,"consumer_count":consumers.len(),"consumers":consumers.into_iter().take(8).collect::<Vec<_>>()}));
        }
    }
    let guards: BTreeMap<_, _> = sources
        .iter()
        .filter(|(p, _)| !offered.contains_key(*p) && p.as_str() != INDEX && p.as_str() != CARRIER)
        .map(|(p, b)| (p.clone(), revision(b)))
        .collect();
    Ok(
        json!({"sources":offered,"guard_revision":digest(&json!(guards))?,"protected":protected,
        "index":index,"index_transfer_required":transfer,"index_revision":index_bytes.as_ref().map(|b|revision(b)),
        "carrier_revision":read(&root,CARRIER)?.as_ref().map(|b|revision(b))}),
    )
}

fn next_index(invocation: &Value) -> Result<Value, CoreError> {
    let mut index = invocation["arguments"]["binding"]["index"].clone();
    let paths = invocation["arguments"]["request"]["arguments"]["sources"]
        .as_array()
        .ok_or_else(|| err("Proof retirement sources absent"))?;
    let entries = index["receipts"]
        .as_object_mut()
        .ok_or_else(|| err("Proof index entries absent"))?;
    entries.retain(|id, entry| {
        !paths.contains(&json!(format!("{HOME}{id}.json")))
            && !entry["path"]
                .as_str()
                .is_some_and(|p| paths.contains(&json!(format!("{HOME}{p}"))))
    });
    index.as_object_mut().unwrap().remove("current_publication");
    Ok(index)
}

fn carrier_bytes(custody: &Value, outcome: &Value) -> Result<Vec<u8>, CoreError> {
    let target_revision = digest(&custody["attempt"]["target"])?;
    let mut relative = custody.clone();
    for field in ["attempt", "committed"] {
        relative[field]["target"] = json!(".");
    }
    serde_json::to_vec(&json!({"kind":"agentic-workspace/proof-index-custody/v1",
        "target_revision":target_revision,"custody":relative,"outcome":outcome}))
    .map_err(err)
}

pub(crate) fn index_custody(target: &Path, bytes: &[u8]) -> Result<bool, CoreError> {
    let root = Dir::open_ambient_dir(target, ambient_authority()).map_err(err)?;
    let Some(carrier) = read(&root, CARRIER)? else {
        return Ok(false);
    };
    let mut record: Value = serde_json::from_slice(&carrier).map_err(err)?;
    if record["kind"] != "agentic-workspace/proof-index-custody/v1" {
        return Ok(false);
    }
    if let Some(expected) = record.get("target_revision") {
        let canonical = std::fs::canonicalize(target).map_err(err)?;
        if expected != &digest(&json!(canonical))? {
            return Err(err("Proof index custody belongs to a different target"));
        }
        for field in ["attempt", "committed"] {
            if record["custody"][field]["target"] != "." {
                return Err(err("Proof index relative custody invalid"));
            }
            record["custody"][field]["target"] = json!(canonical);
        }
    }
    let committed = crate::attempt_store::inspect_committed(
        &target.to_string_lossy(),
        record["custody"].clone(),
    )?;
    let invocation = &committed["invocation"];
    Ok(invocation["source_owner"] == "verification"
        && invocation["operation_id"] == OP
        && committed["outcome"] == record["outcome"]
        && record["outcome"]["value"]["index_revision"] == revision(bytes)
        && serde_json::to_vec_pretty(&next_index(invocation)?).map_err(err)? == bytes)
}

fn retained(target: &Path) -> Result<Option<Value>, CoreError> {
    let root = Dir::open_ambient_dir(target, ambient_authority()).map_err(err)?;
    let Some(bytes) = read(&root, PENDING)? else {
        return Ok(None);
    };
    let record: Value = serde_json::from_slice(&bytes).map_err(err)?;
    let invocation = &record["invocation"];
    if invocation["operation_id"] != OP
        || invocation["source_owner"] != "verification"
        || record["outcome"] != outcome(invocation)?
    {
        return Err(err("Unrecognised Proof retirement recovery preserved"));
    }
    let prepared = crate::attempt_store::prepare_commit(
        target.to_str().unwrap(),
        record["custody"].clone(),
        record["outcome"].clone(),
    )?;
    if prepared["record"]["invocation"] != *invocation {
        return Err(err("Proof retirement custody mismatch"));
    }
    if let Some(recovery) = record.get("recovery") {
        let prepared = crate::attempt_store::prepare_commit(
            target.to_str().unwrap(),
            recovery["custody"].clone(),
            recovery_outcome(&record),
        )?;
        if prepared["record"]["invocation"] != recovery["invocation"]
            || recovery["invocation"]["operation_id"] != RECOVERY
            || recovery["invocation"]["source_owner"] != "verification"
        {
            return Err(err("Proof recovery attempt custody mismatch"));
        }
    }
    Ok(Some(record))
}
fn outcome(invocation: &Value) -> Result<Value, CoreError> {
    let bytes = serde_json::to_vec_pretty(&next_index(invocation)?).map_err(err)?;
    Ok(
        json!({"status":"applied","effects":["proof-execution"],"value":{"kind":"agentic-workspace/proof-retirement/v1",
        "retired":invocation["arguments"]["request"]["arguments"]["sources"],"tracked_tombstone":false,"completion_authority":false,
        "index_revision":revision(&bytes),"proof_authority":"unchanged; disposition grants no proof sufficiency"}}),
    )
}

fn recovery_outcome(record: &Value) -> Value {
    json!({"status":"applied","effects":["proof-execution"],"value":{"kind":"agentic-workspace/proof-retirement/v1","retired":record["outcome"]["value"]["retired"],"recovered":true,"tracked_tombstone":false,"completion_authority":false}})
}

pub(crate) fn view(
    target: &Path,
    work: &Value,
    contract: &Value,
    request: Option<&Value>,
) -> Result<Value, CoreError> {
    let owner = contract["owners"]
        .as_array()
        .unwrap()
        .iter()
        .find(|o| o["owner"] == "verification")
        .ok_or_else(|| err("Proof owner unavailable"))?;
    let pending = retained(target)?;
    let binding = if let Some(record) = &pending {
        json!({"record_revision":digest(record)?})
    } else {
        match inventory(target) {
            Ok(binding) => binding,
            Err(error) if request.is_none() => {
                return Ok(json!({
                    "status":"preserved","requests":[],"reason":error.to_string(),
                    "authority":"No disposition is offered until the source boundary is readable and confined."
                }));
            }
            Err(error) => return Err(error),
        }
    };
    let recovery = pending.is_some();
    let sources: Vec<_> = binding["sources"]
        .as_object()
        .into_iter()
        .flat_map(|o| o.keys().cloned())
        .collect();
    if !recovery && sources.is_empty() && binding["index_transfer_required"] != true {
        return Ok(json!({"status":"quiet","requests":[],"protected":binding["protected"]}));
    }
    let kind = if recovery { RECOVER } else { REQUEST };
    let args = if recovery {
        binding.clone()
    } else {
        json!({"sources":sources,"superseded":false,"no_unresolved_intent":false,"no_continuing_value":false,"reason":""})
    };
    let template = json!({"kind":"agentic-workspace/public-request/v1","id":kind,"owner":"verification","owner_revision":owner["revision"],
        "source_revision":digest(&binding)?,"capability_revision":contract["revision"],"task_identity":work,"request_kind":kind,"arguments":args});
    let mut result = json!({"status":if recovery {"recovery-required"} else {"judgment-required"},"requests":[template],
        "sources":binding["sources"],"index_transfer_required":binding["index_transfer_required"],"protected":binding["protected"],"authority":"Read the exact sources and judge supersession and future value; discovery grants no deletion authority."});
    if let Some(request) = request {
        crate::prepare_request_value(
            json!({"request":request,"current_work":work,"capability_contract":contract}),
        )?;
        if request["request_kind"] != kind
            || request["source_revision"] != template["source_revision"]
        {
            return Err(err(
                "Proof retirement source changed; resolve current disposition",
            ));
        }
        let args = &request["arguments"];
        if recovery {
            if args != &binding {
                return Err(err("Proof retirement recovery changed"));
            }
        } else {
            if args["superseded"] != true
                || args["no_unresolved_intent"] != true
                || args["no_continuing_value"] != true
                || args["reason"].as_str().unwrap_or("").trim().is_empty()
            {
                return Ok(result);
            }
            if args["sources"].as_array().unwrap().is_empty()
                && binding["index_transfer_required"] != true
            {
                return Err(err("Proof index transfer is not required"));
            }
            for path in args["sources"].as_array().unwrap() {
                if binding["sources"].get(path.as_str().unwrap()).is_none() {
                    return Err(err("Proof retirement source is not offered"));
                }
            }
        }
        result["action"] = json!({"operation_id":if recovery {RECOVERY} else {OP},"dependency_revision":digest(&json!([binding,request]))?,
            "arguments":{"target":target,"request":request,"binding":binding},"effects":["proof-execution"],"source_requests":[request]});
    }
    Ok(result)
}

fn verify(root: &Dir, invocation: &Value, allow_absent: bool) -> Result<(), CoreError> {
    let binding = &invocation["arguments"]["binding"];
    let expected = binding["sources"]
        .as_object()
        .ok_or_else(|| err("Proof retirement sources missing"))?;
    let retiring = invocation["arguments"]["request"]["arguments"]["sources"]
        .as_array()
        .ok_or_else(|| err("Proof retirement selection missing"))?;
    let before = &binding["index_revision"];
    let after = revision(&serde_json::to_vec_pretty(&next_index(invocation)?).map_err(err)?);
    let current = read(root, INDEX)?
        .as_ref()
        .map(|b| json!(revision(b)))
        .unwrap_or(Value::Null);
    if &current != before && !(allow_absent && current == after) {
        return Err(err("Proof index changed; preserve remaining sources"));
    }
    let carrier = read(root, CARRIER)?;
    if carrier
        .as_ref()
        .map(|b| json!(revision(b)))
        .unwrap_or(Value::Null)
        != binding["carrier_revision"]
    {
        let pending =
            read(root, PENDING)?.ok_or_else(|| err("Proof index carrier changed; preserved"))?;
        let record: Value = serde_json::from_slice(&pending).map_err(err)?;
        let prepared = crate::attempt_store::prepare_commit(
            invocation["arguments"]["target"].as_str().unwrap(),
            record["custody"].clone(),
            record["outcome"].clone(),
        )?;
        let post = carrier_bytes(&prepared["custody"], &record["outcome"])?;
        if !allow_absent
            || record["invocation"] != *invocation
            || carrier.as_deref() != Some(post.as_slice())
        {
            return Err(err("Proof index carrier changed; preserved"));
        }
    }
    let mut observed: BTreeMap<_, _> = observe_sources(root)?
        .into_iter()
        .filter(|(p, _)| p != INDEX && p != CARRIER)
        .map(|(p, b)| (p, revision(&b)))
        .collect();
    for (path, revision) in expected {
        match observed.remove(path) {
            Some(current) if revision == &current => {}
            None if allow_absent && retiring.contains(&json!(path)) => {}
            _ => {
                return Err(err(
                    "Proof retirement source changed; preserve remaining sources",
                ));
            }
        }
    }
    if binding["guard_revision"] != digest(&json!(observed))? {
        return Err(err(
            "Proof retirement consumer changed; preserve remaining sources",
        ));
    }
    Ok(())
}

pub(crate) fn write_scope(action: &Value) -> Result<Vec<String>, CoreError> {
    let mut paths =
        crate::attempt_store::write_paths(&json!({"idempotency_key":effect_identity(action)}))?;
    paths.extend([
        PENDING.into(),
        ".agentic-workspace/proof/receipts/publication.lock".into(),
        ".agentic-workspace/local/effects/source-reconciliation.lock".into(),
        INDEX.into(),
        CARRIER.into(),
        format!("{INDEX}.retirement.tmp"),
        format!("{CARRIER}.tmp"),
    ]);
    paths.push(temporary(action)?);
    if action["operation_id"] == OP {
        paths.extend(
            action["arguments"]["request"]["arguments"]["sources"]
                .as_array()
                .unwrap()
                .iter()
                .map(|p| p.as_str().unwrap().to_owned()),
        );
    } else {
        // The exact original source paths are observed during recovery, never
        // accepted from caller-selected recovery material.
        let target = Path::new(action["arguments"]["target"].as_str().unwrap());
        let held = retained(target)?.ok_or_else(|| err("Proof retirement recovery absent"))?;
        paths.extend(write_scope(&held["invocation"])?);
    }
    Ok(paths)
}

pub(crate) fn execute(
    target: &Path,
    decision: &Value,
    invocation: &Value,
    mut revalidate: impl FnMut() -> Result<(), CoreError>,
) -> Result<Value, CoreError> {
    execute_checked(target, decision, invocation, &mut revalidate, &mut |_| {
        Ok(())
    })
}
fn execute_checked(
    target: &Path,
    decision: &Value,
    invocation: &Value,
    revalidate: &mut dyn FnMut() -> Result<(), CoreError>,
    observe: &mut dyn FnMut(&str) -> Result<(), CoreError>,
) -> Result<Value, CoreError> {
    let root = Dir::open_ambient_dir(target, ambient_authority()).map_err(err)?;
    root.create_dir_all(".agentic-workspace/local/verification")
        .map_err(err)?;
    let _publication = crate::proof_publication::retention_lock(&root)?;
    let _reconciliation = crate::native_source_reconciliation::retention_lock(&root)?;
    revalidate()?;
    let recovery = invocation["operation_id"] == RECOVERY;
    let previous = retained(target)?;
    if previous.is_some() != recovery {
        return Err(err("Proof retirement requires its exact recovery route"));
    }
    let admission = crate::attempt_store::admit(
        json!({"target":target,"decision":decision,"invocation":invocation}),
    )?;
    let record = if let Some(mut record) = previous {
        // Retain the current recovery attempt before further deletion. Fresh
        // reentry observes a new exact record identity even if recovery itself
        // is interrupted, without replaying its uncertain invocation.
        verify(&root, &record["invocation"], true)?;
        record["recovery"] = json!({"invocation":invocation,"custody":admission["custody"]});
        let temporary = temporary(invocation)?;
        read(&root, &temporary)?;
        let mut file = root
            .open_with(&temporary, OpenOptions::new().write(true).create_new(true))
            .map_err(err)?;
        file.write_all(&record_bytes(&record)?).map_err(err)?;
        file.sync_all().map_err(err)?;
        drop(file);
        revalidate()?;
        root.rename(&temporary, &root, PENDING).map_err(err)?;
        record
    } else {
        verify(&root, invocation, false)?;
        let record = json!({"invocation":invocation,"custody":admission["custody"],"outcome":outcome(invocation)?});
        read(&root, PENDING)?;
        let temporary = temporary(invocation)?;
        read(&root, &temporary)?;
        let mut file = root
            .open_with(&temporary, OpenOptions::new().write(true).create_new(true))
            .map_err(err)?;
        file.write_all(&record_bytes(&record)?).map_err(err)?;
        file.sync_all().map_err(err)?;
        drop(file);
        revalidate()?;
        verify(&root, invocation, false)?;
        root.rename(&temporary, &root, PENDING).map_err(err)?;
        record
    };
    observe("prepared")?;
    let next = serde_json::to_vec_pretty(&next_index(&record["invocation"])?).map_err(err)?;
    verify(&root, &record["invocation"], recovery)?;
    replace_exact(
        &root,
        INDEX,
        &next,
        &record["invocation"]["arguments"]["binding"]["index_revision"],
    )?;
    observe("index-replaced")?;
    verify(&root, &record["invocation"], true)?;
    for path in record["outcome"]["value"]["retired"].as_array().unwrap() {
        verify(&root, &record["invocation"], true)?;
        let path = path.as_str().unwrap();
        if read(&root, path)?.is_some() {
            root.remove_file(path).map_err(err)?;
        }
        observe("removed")?;
    }
    let prepared = crate::attempt_store::prepare_commit(
        target.to_str().unwrap(),
        record["custody"].clone(),
        record["outcome"].clone(),
    )?;
    let mut original_custody = prepared["custody"].clone();
    if read(
        &root,
        original_custody["committed"]["path"].as_str().unwrap(),
    )?
    .is_none()
    {
        original_custody["committed"] = Value::Null;
    }
    let original = crate::attempt_store::commit(
        json!({"target":target,"custody":original_custody,"outcome":record["outcome"]}),
    )?;
    observe("committed")?;
    let carrier = carrier_bytes(&original["custody"], &record["outcome"])?;
    replace_exact(
        &root,
        CARRIER,
        &carrier,
        &record["invocation"]["arguments"]["binding"]["carrier_revision"],
    )?;
    let (out, custody) = if recovery {
        let out = recovery_outcome(&record);
        let committed = crate::attempt_store::commit(
            json!({"target":target,"custody":admission["custody"],"outcome":out}),
        )?;
        (out, committed["custody"].clone())
    } else {
        (record["outcome"].clone(), original["custody"].clone())
    };
    root.remove_file(PENDING).map_err(err)?;
    Ok(
        json!({"outcome":out,"custody":custody,"post_effect_changed_paths":record["outcome"]["value"]["retired"]}),
    )
}

fn replace_exact(root: &Dir, path: &str, bytes: &[u8], before: &Value) -> Result<(), CoreError> {
    let held = read(root, path)?;
    if held.as_deref() == Some(bytes) {
        return Ok(());
    }
    if held
        .as_ref()
        .map(|b| json!(revision(b)))
        .unwrap_or(Value::Null)
        != *before
    {
        return Err(err("Proof retention replacement changed; preserved"));
    }
    let temp = if path == INDEX {
        format!("{path}.retirement.tmp")
    } else {
        format!("{path}.tmp")
    };
    if let Some(old) = read(root, &temp)? {
        if old != bytes {
            return Err(err("Conflicting proof retirement temporary preserved"));
        }
    } else {
        if let Some(parent) = Path::new(path).parent() {
            root.create_dir_all(parent).map_err(err)?;
        }
        let mut f = root
            .open_with(&temp, OpenOptions::new().write(true).create_new(true))
            .map_err(err)?;
        f.write_all(bytes).map_err(err)?;
        f.sync_all().map_err(err)?;
    }
    if read(root, path)? != held {
        return Err(err("Proof retention replacement drift preserved"));
    }
    root.rename(&temp, root, path).map_err(err)
}

// Producer-local retirement is restricted to authenticated semantic supersession.
// The exact plan is carried by the new producer's own authenticated outcome.
pub(crate) fn automatic_plan(
    root: &Dir,
    candidates: &[String],
    excluded: &[String],
) -> Result<Value, CoreError> {
    publication_ready(root)?;
    if candidates.is_empty() {
        return Ok(json!({"sources":{},"excluded":excluded,"guard_revision":null}));
    }
    let observed = observe_sources(root)?;
    let references: Vec<_> = observed
        .iter()
        .filter(|(p, _)| p.as_str() != INDEX && p.as_str() != CARRIER && !excluded.contains(p))
        .map(|(p, b)| {
            let mut value = serde_json::from_slice::<Value>(b).ok();
            if let Some(Value::Object(v)) = value.as_mut() {
                v.remove("publication_custody");
                v.remove("retention");
            }
            (
                p,
                value
                    .map(|v| v.to_string())
                    .unwrap_or_else(|| String::from_utf8_lossy(b).into_owned()),
            )
        })
        .collect();
    let mut sources = serde_json::Map::new();
    for path in candidates {
        let id = path
            .strip_prefix(HOME)
            .ok_or_else(|| err("Retirement outside proof receipt store"))?
            .trim_end_matches(".json");
        if references
            .iter()
            .any(|(p, b)| *p != path && (b.contains(path) || (id.len() >= 16 && b.contains(id))))
        {
            continue;
        }
        if let Some(bytes) = observed.get(path) {
            sources.insert(path.clone(), json!(revision(bytes)));
        }
    }
    let guards: BTreeMap<_, _> = observed
        .iter()
        .filter(|(p, _)| {
            !sources.contains_key(*p)
                && p.as_str() != INDEX
                && p.as_str() != CARRIER
                && !excluded.contains(p)
        })
        .map(|(p, b)| (p.clone(), revision(b)))
        .collect();
    Ok(json!({"sources":sources,"excluded":excluded,"guard_revision":digest(&json!(guards))?}))
}
pub(crate) fn automatic_check(
    root: &Dir,
    plan: &Value,
    allow_absent: bool,
) -> Result<(), CoreError> {
    let sources = plan["sources"]
        .as_object()
        .ok_or_else(|| err("Proof retirement plan missing"))?;
    if sources.is_empty() {
        return Ok(());
    }
    let excluded: Vec<String> = serde_json::from_value(plan["excluded"].clone()).map_err(err)?;
    let mut observed = observe_sources(root)?;
    for (source, expected) in sources {
        match observed.remove(source) {
            Some(bytes) if revision(&bytes) == *expected => {}
            None if allow_absent => {}
            _ => return Err(err("Superseded proof source changed; preserved")),
        }
    }
    observed.remove(INDEX);
    observed.remove(CARRIER);
    for source in &excluded {
        observed.remove(source);
    }
    let guards: BTreeMap<_, _> = observed
        .iter()
        .map(|(p, b)| (p.clone(), revision(b)))
        .collect();
    if digest(&json!(guards))? != plan["guard_revision"] {
        return Err(err("Proof consumer changed; retirement recovery required"));
    }
    Ok(())
}
pub(crate) fn automatic_remove(root: &Dir, plan: &Value) -> Result<(), CoreError> {
    for path in plan["sources"]
        .as_object()
        .ok_or_else(|| err("Proof retirement plan missing"))?
        .keys()
    {
        automatic_check(root, plan, true)?;
        if read(root, path)?.is_some() {
            root.remove_file(path).map_err(err)?;
        }
    }
    Ok(())
}

pub(crate) fn publication_ready(root: &Dir) -> Result<(), CoreError> {
    if read(root, PENDING)?.is_some() {
        return Err(err(
            "Pending proof disposition requires recovery before publication",
        ));
    }
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;
    static NEXT_FIXTURE: std::sync::atomic::AtomicU64 = std::sync::atomic::AtomicU64::new(0);
    struct Fixture(std::path::PathBuf);
    impl Fixture {
        fn new() -> Self {
            let p = std::env::temp_dir().join(format!(
                "aw-proof-retirement-{}-{}-{}",
                std::process::id(),
                std::time::SystemTime::now()
                    .duration_since(std::time::UNIX_EPOCH)
                    .unwrap()
                    .as_nanos(),
                NEXT_FIXTURE.fetch_add(1, std::sync::atomic::Ordering::Relaxed)
            ));
            std::fs::create_dir_all(&p).unwrap();
            Self(p)
        }
        fn put(&self, path: &str, value: Value) {
            let p = self.0.join(path);
            std::fs::create_dir_all(p.parent().unwrap()).unwrap();
            std::fs::write(p, serde_json::to_vec(&value).unwrap()).unwrap();
        }
        fn legacy(&self) -> String {
            let id = "0123456789abcdef";
            let p = format!("{HOME}{id}.json");
            self.put(
                &p,
                json!({"receipt_id":id,"result":"passed","authority":"legacy-unproven"}),
            );
            self.put(INDEX,json!({"kind":"agentic-workspace/trusted-producer-receipt-index/v1","receipts":{id:{"path":format!("{id}.json")}}}));
            p
        }
        fn start(&self, request: Option<Value>) -> Value {
            let mut input = json!({"target":self.0,"task":"Retire superseded proof history"});
            if let Some(r) = request {
                input["request"] = r;
            }
            crate::native_public::start(input).unwrap()
        }
        fn ready(&self) -> Value {
            let mut r = self.start(None)["verification"]["retention"]["requests"][0].clone();
            if r["request_kind"] == REQUEST {
                r["arguments"]["superseded"] = json!(true);
                r["arguments"]["no_unresolved_intent"] = json!(true);
                r["arguments"]["no_continuing_value"] = json!(true);
                r["arguments"]["reason"] =
                    json!("Fixture producer retired; no reusable evidence or unresolved claims.");
            }
            self.start(Some(r))
        }
    }
    impl Drop for Fixture {
        fn drop(&mut self) {
            let _ = std::fs::remove_dir_all(&self.0);
        }
    }
    #[test]
    fn exact_legacy_disposition_transfers_index_only_and_repeats_quietly() {
        let f = Fixture::new();
        let path = f.legacy();
        let compact =
            crate::operating::start(json!({"target":f.0,"task":"Retire superseded proof history"}))
                .unwrap();
        assert_eq!(compact["proof_retention"]["candidate_count"], 1);
        assert!(
            compact["proof_retention"]["reference"]
                .as_str()
                .unwrap()
                .starts_with("detail:verification:")
        );
        assert!(crate::proof_publication::check(&f.0).is_err());
        let ready = f.ready();
        let action = &ready["decision_packet"]["primary_action"];
        assert_eq!(action["operation_id"], OP, "{}", ready["decision_packet"]);
        let result = crate::native_public::invoke(
            json!({"target":f.0,"task":"Retire superseded proof history","invocation":action}),
        )
        .unwrap();
        assert_eq!(result["effect_outcome"]["status"], "committed", "{result}");
        assert!(!f.0.join(path).exists());
        assert!(!f.0.join(PENDING).exists());
        crate::proof_publication::check(&f.0).unwrap();
        assert_eq!(
            f.start(None)["verification"]["retention"]["status"],
            "quiet"
        );
    }
    #[test]
    fn empty_index_transfer_has_relative_but_target_bound_custody() {
        let f = Fixture::new();
        f.put(
            INDEX,
            json!({"kind":"agentic-workspace/trusted-producer-receipt-index/v1","receipts":{}}),
        );
        let ready = f.ready();
        let action = &ready["decision_packet"]["primary_action"];
        assert_eq!(
            action["arguments"]["request"]["arguments"]["sources"],
            json!([])
        );
        execute(&f.0, &ready["decision_packet"], action, || Ok(())).unwrap();
        let bytes = std::fs::read(f.0.join(INDEX)).unwrap();
        assert!(index_custody(&f.0, &bytes).unwrap());
        let mut carrier: Value =
            serde_json::from_slice(&std::fs::read(f.0.join(CARRIER)).unwrap()).unwrap();
        assert_eq!(carrier["custody"]["attempt"]["target"], ".");
        assert_eq!(
            f.start(None)["verification"]["retention"]["status"],
            "quiet"
        );
        carrier["target_revision"] = json!("another-checkout");
        f.put(CARRIER, carrier);
        assert!(index_custody(&f.0, &bytes).is_err());
    }
    #[test]
    fn every_live_root_and_new_consumer_preserve_receipts() {
        for consumer in [
            "planning/consumer.json",
            "instructions/consumer.json",
            "memory/consumer.json",
            "verification/consumer.json",
            "evaluations/consumer.json",
            "reconstruction/consumer.json",
            "system-intent/consumer.json",
            "proof/current/consumer.json",
            "evaluations.json",
            "delegation-outcomes.json",
        ] {
            let f = Fixture::new();
            let path = f.legacy();
            let current = f.ready();
            let action = &current["decision_packet"]["primary_action"];
            let root = Dir::open_ambient_dir(&f.0, ambient_authority()).unwrap();
            let automatic = automatic_plan(&root, std::slice::from_ref(&path), &[]).unwrap();
            f.put(
                &format!(".agentic-workspace/{consumer}"),
                json!({"proof":path}),
            );
            let root = Dir::open_ambient_dir(&f.0, ambient_authority()).unwrap();
            assert!(verify(&root, action, false).is_err());
            assert!(automatic_check(&root, &automatic, false).is_err());
            assert!(
                inventory(&f.0).unwrap()["sources"]
                    .as_object()
                    .unwrap()
                    .is_empty()
            );
        }
    }
    #[test]
    fn interrupted_index_and_deletion_recover_from_local_custody() {
        for stage in ["prepared", "index-replaced", "removed", "committed"] {
            let f = Fixture::new();
            let path = f.legacy();
            let ready = f.ready();
            let action = &ready["decision_packet"]["primary_action"];
            let result = execute_checked(
                &f.0,
                &ready["decision_packet"],
                action,
                &mut || Ok(()),
                &mut |at| {
                    if at == stage {
                        Err(err("interrupted"))
                    } else {
                        Ok(())
                    }
                },
            );
            assert!(result.is_err());
            let recovery = f.ready();
            let action = &recovery["decision_packet"]["primary_action"];
            assert_eq!(
                action["operation_id"], RECOVERY,
                "{}",
                recovery["decision_packet"]
            );
            execute(&f.0, &recovery["decision_packet"], action, || Ok(())).unwrap();
            assert!(!f.0.join(path).exists());
            crate::proof_publication::check(&f.0).unwrap();
        }
    }
}
