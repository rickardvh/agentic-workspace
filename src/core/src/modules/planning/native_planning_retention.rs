//! Terminal Planning source disposition. Historical location is discovery, never
//! deletion authority. Exact agent judgement, live references and effect custody
//! remain separate. Recovery is local and does not require a tracked tombstone.
use crate::{CoreError, digest};
use cap_std::{
    ambient_authority,
    fs::{Dir, OpenOptions},
};
use serde_json::{Value, json};
use std::{
    collections::{BTreeMap, BTreeSet},
    io::Write,
    path::Path,
};

pub(crate) const REQUEST: &str = "planning/terminal-disposition/v1";
pub(crate) const RECOVER: &str = "planning/recover-terminal-disposition/v1";
pub(crate) const OP: &str = "planning.retire-terminal";
pub(crate) const RECOVERY: &str = "planning.recover-terminal";
const HOME: &str = ".agentic-workspace/planning/execplans/";
const PENDING: &str = ".agentic-workspace/local/planning/terminal-disposition.json";
const LIMIT: usize = 32;

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
            "Planning retirement recovery exceeds source bound; preserved",
        ));
    }
    Ok(bytes)
}

pub(crate) fn declarations() -> Vec<Value> {
    vec![
        json!({"kind":REQUEST,"result_kind":"agentic-planning/terminal-disposition/v1","input_schema":{
        "$schema":"https://json-schema.org/draft/2020-12/schema","type":"object","additionalProperties":false,
        "properties":{"sources":{"type":"array","minItems":1,"maxItems":32,"uniqueItems":true,"items":{"type":"string"}},
        "terminal":{"type":"boolean"},"no_unresolved_intent":{"type":"boolean"},"no_continuing_value":{"type":"boolean"},
        "reason":{"type":"string","maxLength":2048}},
        "required":["sources","terminal","no_unresolved_intent","no_continuing_value","reason"]}}),
        json!({"kind":RECOVER,"result_kind":"agentic-planning/terminal-disposition/v1","input_schema":{
        "$schema":"https://json-schema.org/draft/2020-12/schema","type":"object","additionalProperties":false,
        "properties":{"record_revision":{"type":"string"}},"required":["record_revision"]}}),
    ]
}
pub(crate) fn operations() -> Vec<Value> {
    [OP,RECOVERY].into_iter().map(|id| json!({"id":id,"semantic_revision":"planning-terminal-disposition-v2",
        "input_schema":{"$schema":"https://json-schema.org/draft/2020-12/schema","type":"object","additionalProperties":false,
        "properties":{"target":{"type":"string"},"request":{"type":"object"},"binding":{"type":"object"}},
        "required":["target","request","binding"]},"result_kind":"agentic-planning/terminal-disposition/v1",
        "effects":["planning-state"],"reads":["planning"]})).collect()
}

use crate::retention_sources::files;

fn terminal(path: &str, bytes: &[u8]) -> bool {
    if !path.ends_with(".json") {
        return false;
    }
    let Ok(body) = serde_json::from_slice::<Value>(bytes) else {
        return false;
    };
    // Archive membership only offers a current semantic question. It cannot
    // supply either terminal meaning or permission to retire the source.
    (path.starts_with(HOME)
        && (path.starts_with(&format!("{HOME}archive/"))
            || body["lifecycle"] == "archived"
            || (body["lifecycle"] == "closed" && body["phase"] == "complete")))
        || ([
            (
                ".agentic-workspace/planning/decompositions/",
                "planning-decomposition/v1",
            ),
            (".agentic-workspace/planning/lanes/", "planning-lane/v1"),
        ]
        .iter()
        .any(|(prefix, kind)| path.starts_with(prefix) && body["kind"] == *kind)
            && body["status"] == "closed")
        || [
            ("reviews/", "planning-review/v1"),
            ("closeout-evidence/", "planning-closeout-evidence/v1"),
            ("integration-proposals/", "planning-integration-proposal/v1"),
            ("integration-receipts/", "planning-integration-receipt/v1"),
            ("assignments/", "agentic-workspace/planning-assignment/v1"),
            ("lanes/archive/", "planning-lane/v1"),
        ]
        .iter()
        .any(|(prefix, kind)| {
            path.starts_with(&format!(".agentic-workspace/planning/{prefix}"))
                && body["kind"] == *kind
        })
}

fn observe_sources(root: &Dir) -> Result<BTreeMap<String, Vec<u8>>, CoreError> {
    let mut sources = BTreeMap::new();
    files(root, ".agentic-workspace/planning", &mut sources)?;
    observe_consumers(root, &mut sources)?;
    Ok(sources)
}

fn observe_consumers(root: &Dir, sources: &mut BTreeMap<String, Vec<u8>>) -> Result<(), CoreError> {
    for path in [
        ".agentic-workspace/proof",
        ".agentic-workspace/memory",
        ".agentic-workspace/verification",
        ".agentic-workspace/evaluations",
        ".agentic-workspace/reconstruction",
        ".agentic-workspace/system-intent",
        ".agentic-workspace/instructions",
        ".agentic-workspace/local/decision-point-intent",
    ] {
        files(root, path, sources)?;
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
        ".agentic-workspace/local/verification/retire-receipts.json",
    ] {
        if let Some(bytes) = read(root, path)? {
            sources.insert(path.into(), bytes);
        }
    }
    Ok(())
}

#[cfg(test)]
fn inventory(target: &Path, selected: &Value) -> Result<Value, CoreError> {
    inventory_for(target, selected, &[])
}
fn inventory_for(
    target: &Path,
    selected: &Value,
    preferred: &[String],
) -> Result<Value, CoreError> {
    let root = Dir::open_ambient_dir(target, ambient_authority()).map_err(err)?;
    let mut sources = BTreeMap::new();
    files(&root, ".agentic-workspace/planning", &mut sources)?;
    // Ordinary reads need no cross-owner graph unless Planning has a terminal
    // candidate. Reuse this scan when group analysis is actually required.
    if !sources
        .iter()
        .any(|(path, bytes)| terminal(path, bytes) && selected["ref"] != path.as_str())
    {
        return Ok(json!({"sources":{},"required":{},"selected":selected["ref"],"protected":[]}));
    }
    observe_consumers(&root, &mut sources)?;
    let mut eligible = BTreeSet::new();
    let mut provenance = BTreeSet::new();
    let mut proof_subjects = BTreeMap::new();
    let mut aliases: BTreeMap<String, BTreeSet<String>> = BTreeMap::new();
    let mut protected = Vec::new();
    for (path, bytes) in &sources {
        let Ok(body) = serde_json::from_slice::<Value>(bytes) else {
            continue;
        };
        let is_plan = terminal(path, bytes) && selected["ref"] != path.as_str();
        let uncertain = is_plan
            && (crate::native_planning_create::inspect_origin(target, path, &body).is_err()
                || match crate::native_planning_update::inspect(target, path, &body) {
                    Ok(Some(update)) => update["committed"] != true,
                    Ok(None) => false,
                    Err(_) => true,
                });
        if is_plan && !uncertain {
            eligible.insert(path.clone());
        } else if uncertain && protected.len() < LIMIT {
            protected.push(json!({"source":path,"reason":"producer outcome uncertain or provenance unrecognised"}));
        }
        // Committed/legacy receipt provenance is traversed to its actual consumers,
        // not treated as an eternal root merely because the receipt exists.
        let proof = path.starts_with(".agentic-workspace/proof/receipts/")
            && path.ends_with(".json")
            && [
                "agentic-workspace/proof-receipt/v1",
                "agentic-workspace/assignment-structural-proof-receipt/v1",
            ]
            .contains(&body["kind"].as_str().unwrap_or(""));
        let planning_subject = if proof {
            crate::proof_publication::retention_planning_subject(target, &body)
                .ok()
                .flatten()
        } else {
            None
        };
        if let Some(subject) = &planning_subject {
            proof_subjects.insert(path.clone(), subject.clone());
        }
        if proof
            && (planning_subject.is_some()
                || !crate::proof_publication::retention_reusable(target, &body).unwrap_or(true))
            && (body["proof_subject"]["runtime"]["implementation"] != "native-aw-proof"
                || crate::proof_publication::retention_committed(target, &body).is_ok())
            && (body.get("publication_custody").is_none()
                || crate::proof_publication::retention_committed(target, &body).is_ok())
            && body.get("custody").is_none()
            && body.get("invocation").is_none()
        {
            provenance.insert(path.clone());
        }
        if is_plan || proof {
            let mut names = vec![path.clone()];
            for field in ["id", "assignment_id", "receipt_id"] {
                if let Some(id) = body[field].as_str().filter(|id| !id.is_empty()) {
                    names.push(id.into());
                }
            }
            if path.starts_with(HOME)
                && let Some(id) = body["id"].as_str()
            {
                names.push(format!(
                    "planning:{}",
                    digest(&json!({"target":std::fs::canonicalize(target).map_err(err)?,"id":id}))?
                ));
            }
            for name in names {
                aliases.entry(name).or_default().insert(path.clone());
            }
        }
    }
    let patterns: Vec<_> = aliases.keys().collect();
    let mut referrers: BTreeMap<String, BTreeSet<String>> = BTreeMap::new();
    if !patterns.is_empty() {
        let matcher = aho_corasick::AhoCorasick::new(&patterns).map_err(err)?;
        for (path, bytes) in &sources {
            if [
                ".agentic-workspace/proof/receipts/index.json",
                ".agentic-workspace/proof/current/index-custody.json",
            ]
            .contains(&path.as_str())
            {
                continue;
            }
            let text = serde_json::from_slice::<Value>(bytes)
                .ok()
                .map(|mut value| {
                    if provenance.contains(path)
                        && let Some(body) = value.as_object_mut()
                    {
                        body.remove("publication_custody");
                        if let Some(subject) = proof_subjects.get(path) {
                            body.insert("planning_subject".into(), json!(subject));
                        }
                    }
                    value.to_string()
                })
                .unwrap_or_else(|| String::from_utf8_lossy(bytes).into_owned());
            for found in matcher.find_overlapping_iter(&text) {
                for subject in &aliases[patterns[found.pattern().as_usize()]] {
                    if subject != path {
                        referrers
                            .entry(subject.clone())
                            .or_default()
                            .insert(path.clone());
                    }
                }
            }
        }
    }
    let mut offered = serde_json::Map::new();
    let mut required = serde_json::Map::new();
    let ordered: Vec<_> = if preferred.is_empty() {
        eligible.iter().collect()
    } else {
        preferred.iter().filter(|p| eligible.contains(*p)).collect()
    };
    let mut queue = ordered
        .into_iter()
        .cloned()
        .collect::<std::collections::VecDeque<_>>();
    let mut processed = BTreeSet::new();
    while let Some(seed) = queue.pop_front() {
        if !processed.insert(seed.clone()) {
            continue;
        }
        let mut group = BTreeSet::new();
        let mut visited = BTreeSet::new();
        let mut frontier = vec![seed.clone()];
        let mut blockers = BTreeSet::new();
        while let Some(path) = frontier.pop() {
            if !visited.insert(path.clone()) {
                continue;
            }
            if eligible.contains(&path) {
                group.insert(path.clone());
            } else if !provenance.contains(&path) {
                blockers.insert(path);
                continue;
            }
            if let Some(consumers) = referrers.get(&path) {
                frontier.extend(consumers.iter().cloned());
            }
            if group.len() > LIMIT {
                blockers.insert("terminal group exceeds current batch bound".into());
                break;
            }
        }
        if blockers.is_empty()
            && offered
                .keys()
                .chain(group.iter())
                .collect::<BTreeSet<_>>()
                .len()
                <= LIMIT
        {
            required.insert(seed.clone(), json!(group));
            for path in group {
                if !processed.contains(&path) {
                    queue.push_back(path.clone());
                }
                offered.insert(path.clone(), json!(revision(&sources[&path])));
            }
        } else if !blockers.is_empty() && protected.len() < LIMIT {
            protected.push(
                json!({"source":seed,"consumers":blockers.into_iter().take(8).collect::<Vec<_>>()}),
            );
        }
    }
    // Every offered member must carry its own transitive requirement even when
    // it entered through another seed's group.
    for path in offered.keys() {
        if !required.contains_key(path) {
            return Err(err("Planning closed group binding incomplete; preserved"));
        }
    }
    let guards: BTreeMap<_, _> = sources
        .iter()
        .filter(|(p, _)| !offered.contains_key(*p))
        .map(|(p, b)| (p.clone(), revision(b)))
        .collect();
    Ok(
        json!({"sources":offered,"required":required,"guard_revision":digest(&json!(guards))?,"selected":selected["ref"],"protected":protected}),
    )
}

fn retained(target: &Path) -> Result<Option<Value>, CoreError> {
    let root = Dir::open_ambient_dir(target, ambient_authority()).map_err(err)?;
    let Some(bytes) = read(&root, PENDING)? else {
        return Ok(None);
    };
    let record: Value = serde_json::from_slice(&bytes).map_err(err)?;
    let invocation = &record["invocation"];
    if invocation["operation_id"] != OP
        || invocation["source_owner"] != "planning"
        || record["outcome"] != outcome(invocation)
    {
        return Err(err("Unrecognised Planning retirement recovery preserved"));
    }
    let prepared = crate::attempt_store::prepare_commit(
        target.to_str().unwrap(),
        record["custody"].clone(),
        record["outcome"].clone(),
    )?;
    if prepared["record"]["invocation"] != *invocation {
        return Err(err("Planning retirement custody mismatch"));
    }
    if let Some(recovery) = record.get("recovery") {
        let prepared = crate::attempt_store::prepare_commit(
            target.to_str().unwrap(),
            recovery["custody"].clone(),
            recovery_outcome(&record),
        )?;
        if prepared["record"]["invocation"] != recovery["invocation"]
            || recovery["invocation"]["operation_id"] != RECOVERY
            || recovery["invocation"]["source_owner"] != "planning"
        {
            return Err(err("Planning recovery attempt custody mismatch"));
        }
    }
    Ok(Some(record))
}
fn outcome(invocation: &Value) -> Value {
    json!({"status":"applied","effects":["planning-state"],"value":{"kind":"agentic-planning/terminal-disposition/v1",
        "retired":invocation["arguments"]["request"]["arguments"]["sources"],"tracked_tombstone":false,"completion_authority":false}})
}
fn recovery_outcome(record: &Value) -> Value {
    json!({"status":"applied","effects":["planning-state"],"value":{"kind":"agentic-planning/terminal-disposition/v1","retired":record["outcome"]["value"]["retired"],"recovered":true,"tracked_tombstone":false,"completion_authority":false}})
}

pub(crate) fn view(
    target: &Path,
    work: &Value,
    contract: &Value,
    planning: &Value,
    request: Option<&Value>,
) -> Result<Value, CoreError> {
    let owner = contract["owners"]
        .as_array()
        .unwrap()
        .iter()
        .find(|o| o["owner"] == "planning")
        .ok_or_else(|| err("Planning owner unavailable"))?;
    let pending = retained(target)?;
    let binding = if let Some(record) = &pending {
        json!({"record_revision":digest(record)?})
    } else {
        match inventory_for(
            target,
            &planning["selected_owner"],
            &request
                .and_then(|r| r["arguments"]["sources"].as_array())
                .map(|paths| {
                    paths
                        .iter()
                        .filter_map(|p| p.as_str().map(str::to_owned))
                        .collect::<Vec<_>>()
                })
                .unwrap_or_default(),
        ) {
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
    if !recovery && sources.is_empty() {
        return Ok(json!({"status":"quiet","requests":[],"protected":binding["protected"]}));
    }
    let kind = if recovery { RECOVER } else { REQUEST };
    let args = if recovery {
        binding.clone()
    } else {
        json!({"sources":sources,"terminal":false,"no_unresolved_intent":false,"no_continuing_value":false,"reason":""})
    };
    let template = json!({"kind":"agentic-workspace/public-request/v1","id":kind,"owner":"planning","owner_revision":owner["revision"],
        "source_revision":digest(&json!([binding["sources"],binding["required"],binding["guard_revision"],binding["selected"],binding["record_revision"]]))?,"capability_revision":contract["revision"],"task_identity":work,"request_kind":kind,"arguments":args});
    let mut result = json!({"status":if recovery {"recovery-required"} else {"judgment-required"},"requests":[template],
        "sources":binding["sources"],"groups":binding["required"],"protected":binding["protected"],"authority":"Read the exact sources and judge terminal intent and future value; discovery grants no deletion authority."});
    if let Some(request) = request {
        crate::prepare_request_value(
            json!({"request":request,"current_work":work,"capability_contract":contract}),
        )?;
        if !recovery
            && request["arguments"]["terminal"] == false
            && request["arguments"]["no_unresolved_intent"] == false
            && request["arguments"]["no_continuing_value"] == false
        {
            return Ok(result);
        }
        if request["request_kind"] != kind
            || request["source_revision"] != template["source_revision"]
        {
            return Err(err(
                "Planning retirement source changed; resolve current disposition",
            ));
        }
        let args = &request["arguments"];
        if recovery {
            if args != &binding {
                return Err(err("Planning retirement recovery changed"));
            }
        } else {
            if args["terminal"] != true
                || args["no_unresolved_intent"] != true
                || args["no_continuing_value"] != true
                || args["reason"].as_str().unwrap_or("").trim().is_empty()
            {
                return Ok(result);
            }
            for path in args["sources"].as_array().unwrap() {
                if binding["sources"].get(path.as_str().unwrap()).is_none() {
                    return Err(err("Planning retirement source is not offered"));
                }
                for required in binding["required"][path.as_str().unwrap()]
                    .as_array()
                    .unwrap()
                {
                    if !args["sources"].as_array().unwrap().contains(required) {
                        return Err(err(
                            "Planning retirement requires the complete closed group",
                        ));
                    }
                }
            }
        }
        result["action"] = json!({"operation_id":if recovery {RECOVERY} else {OP},"dependency_revision":digest(&json!([binding,request]))?,
            "arguments":{"target":target,"request":request,"binding":binding},"effects":["planning-state"],"source_requests":[request]});
    }
    Ok(result)
}

fn verify(root: &Dir, invocation: &Value, allow_absent: bool) -> Result<(), CoreError> {
    let binding = &invocation["arguments"]["binding"];
    let expected = binding["sources"]
        .as_object()
        .ok_or_else(|| err("Planning retirement sources missing"))?;
    let retiring = invocation["arguments"]["request"]["arguments"]["sources"]
        .as_array()
        .ok_or_else(|| err("Planning retirement selection missing"))?;
    let mut observed: BTreeMap<_, _> = observe_sources(root)?
        .into_iter()
        .map(|(p, b)| (p, revision(&b)))
        .collect();
    for (path, revision) in expected {
        match observed.remove(path) {
            Some(current) if revision == &current => {}
            None if allow_absent && retiring.contains(&json!(path)) => {}
            _ => {
                return Err(err(
                    "Planning retirement source changed; preserve remaining sources",
                ));
            }
        }
    }
    if binding["guard_revision"] != digest(&json!(observed))? {
        return Err(err(
            "Planning retirement consumer changed; preserve remaining sources",
        ));
    }
    Ok(())
}

pub(crate) fn write_scope(action: &Value) -> Result<Vec<String>, CoreError> {
    let mut paths =
        crate::attempt_store::write_paths(&json!({"idempotency_key":effect_identity(action)}))?;
    paths.extend([
        PENDING.into(),
        ".agentic-workspace/local/planning/owner-selection.lock".into(),
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
        let held = retained(target)?.ok_or_else(|| err("Planning retirement recovery absent"))?;
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
    let _lock = crate::native_planning::owner_lock(&root)?;
    revalidate()?;
    let recovery = invocation["operation_id"] == RECOVERY;
    let previous = retained(target)?;
    if previous.is_some() != recovery {
        return Err(err("Planning retirement requires its exact recovery route"));
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
        let record = json!({"invocation":invocation,"custody":admission["custody"],"outcome":outcome(invocation)});
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
    verify(&root, &record["invocation"], recovery)?;
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

#[cfg(test)]
mod tests {
    use super::*;
    static NEXT_FIXTURE: std::sync::atomic::AtomicU64 = std::sync::atomic::AtomicU64::new(0);
    struct Fixture(std::path::PathBuf);
    impl Fixture {
        fn new() -> Self {
            let path = std::env::temp_dir().join(format!(
                "aw-retention-{}-{}-{}",
                std::process::id(),
                std::time::SystemTime::now()
                    .duration_since(std::time::UNIX_EPOCH)
                    .unwrap()
                    .as_nanos(),
                NEXT_FIXTURE.fetch_add(1, std::sync::atomic::Ordering::Relaxed)
            ));
            std::fs::create_dir_all(&path).unwrap();
            Self(path)
        }
        fn put(&self, path: &str, value: Value) {
            let path = self.0.join(path);
            std::fs::create_dir_all(path.parent().unwrap()).unwrap();
            std::fs::write(path, serde_json::to_vec(&value).unwrap()).unwrap();
        }
        fn archive(&self, name: &str) -> String {
            let path = format!("{HOME}archive/{name}.json");
            self.put(&path, json!({"legacy":"source only"}));
            path
        }
        fn start(&self, request: Option<Value>) -> Value {
            let mut input = json!({"target":self.0,"task":"Retire terminal history"});
            if let Some(request) = request {
                input["request"] = request;
            }
            crate::native_public::start(input).unwrap()
        }
        fn ready(&self) -> Value {
            let mut request =
                self.start(None)["planning"]["terminal_retention"]["requests"][0].clone();
            if request["request_kind"] == REQUEST {
                request["arguments"]["terminal"] = json!(true);
                request["arguments"]["no_unresolved_intent"] = json!(true);
                request["arguments"]["no_continuing_value"] = json!(true);
                request["arguments"]["reason"] =
                    json!("Fixture intent is complete; no continuing consumer or knowledge.");
            }
            self.start(Some(request))
        }
    }
    impl Drop for Fixture {
        fn drop(&mut self) {
            let _ = std::fs::remove_dir_all(&self.0);
        }
    }

    #[test]
    fn closed_group_requires_all_members_and_preserves_outside_consumers() {
        let f = Fixture::new();
        let plan = f.archive("closed");
        let review = ".agentic-workspace/planning/reviews/closed.json";
        f.put(&plan, json!({"review":review}));
        f.put(review, json!({"kind":"planning-review/v1","owner":plan}));
        let decomposition = ".agentic-workspace/planning/decompositions/closed.json";
        f.put(
            decomposition,
            json!({"kind":"planning-decomposition/v1","status":"closed","review":review}),
        );
        let ready = f.ready();
        let action = &ready["decision_packet"]["primary_action"];
        assert_eq!(
            action["arguments"]["binding"]["sources"]
                .as_object()
                .unwrap()
                .len(),
            3
        );
        let mut partial = action["arguments"]["request"].clone();
        partial["arguments"]["sources"] = json!([plan]);
        assert!(
            crate::native_public::start(
                json!({"target":f.0,"task":"Retire terminal history","request":partial})
            )
            .is_err()
        );
        f.put(
            ".agentic-workspace/memory/live.json",
            json!({"review":review}),
        );
        assert!(
            inventory(&f.0, &Value::Null).unwrap()["sources"]
                .get(&plan)
                .is_none()
        );
        let root = Dir::open_ambient_dir(&f.0, ambient_authority()).unwrap();
        assert!(verify(&root, action, false).is_err());
    }
    #[test]
    fn historical_receipt_provenance_is_not_a_root_but_its_consumers_are() {
        let f = Fixture::new();
        let plan = f.archive("closed");
        let proof = ".agentic-workspace/proof/receipts/0123456789abcdef.json";
        f.put(proof, json!({"kind":"agentic-workspace/proof-receipt/v1","receipt_id":"0123456789abcdef","owner":plan}));
        assert!(
            inventory(&f.0, &Value::Null).unwrap()["sources"]
                .get(&plan)
                .is_some()
        );
        f.put(
            ".agentic-workspace/memory/live.json",
            json!({"proof":"proof://receipts/0123456789abcdef"}),
        );
        assert!(
            inventory(&f.0, &Value::Null).unwrap()["sources"]
                .get(&plan)
                .is_none()
        );
    }
    #[test]
    fn explicit_readonly_nomination_can_reach_beyond_unanswered_frontier() {
        let f = Fixture::new();
        for n in 0..40 {
            f.archive(&format!("a{n:02}"));
        }
        let later = f.archive("z-last");
        let mut request = f.start(None)["planning"]["terminal_retention"]["requests"][0].clone();
        request["arguments"]["sources"] = json!([later]);
        let nominated = f.start(Some(request));
        let detail = &nominated["planning"]["terminal_retention"];
        assert!(detail["action"].is_null());
        assert!(detail["sources"].get(&later).is_some());
        let mut request = detail["requests"][0].clone();
        request["arguments"]["terminal"] = json!(true);
        request["arguments"]["no_unresolved_intent"] = json!(true);
        request["arguments"]["no_continuing_value"] = json!(true);
        request["arguments"]["reason"] = json!("Exact nominated fixture group is disposable.");
        assert_eq!(
            f.start(Some(request))["decision_packet"]["primary_action"]["operation_id"],
            OP
        );
    }
    #[test]
    fn new_consumers_and_unselected_source_drift_preserve_history() {
        let f = Fixture::new();
        let first = f.archive("first");
        let second = f.archive("second");
        let binding = inventory(&f.0, &Value::Null).unwrap();
        let invocation =
            json!({"arguments":{"binding":binding,"request":{"arguments":{"sources":[first]}}}});
        let root = Dir::open_ambient_dir(&f.0, ambient_authority()).unwrap();
        verify(&root, &invocation, false).unwrap();
        f.put(".agentic-workspace/proof/new.json", json!({"owner":first}));
        assert!(verify(&root, &invocation, false).is_err());
        std::fs::remove_file(f.0.join(".agentic-workspace/proof/new.json")).unwrap();
        f.put(&second, json!({"changed":true}));
        assert!(verify(&root, &invocation, false).is_err());
        assert!(f.0.join(first).exists());
    }

    #[test]
    fn protected_frontier_cannot_starve_later_candidates_or_retire_selection() {
        let f = Fixture::new();
        let mut refs = Vec::new();
        for n in 0..40 {
            refs.push(f.archive(&format!("a{n:02}")));
        }
        f.put(".agentic-workspace/proof/consumers.json", json!(refs));
        let uncertain = f.archive("uncertain");
        f.put(
            &uncertain,
            json!({"creation_provenance":{"kind":"unknown"}}),
        );
        let named = f.archive("named");
        f.put(&named, json!({"id":"named-owner"}));
        f.put(
            ".agentic-workspace/memory/consumer.json",
            json!({"owner_id":"named-owner"}),
        );
        let selected = f.archive("selected");
        let eligible = f.archive("zlast");
        let inventory = inventory(&f.0, &json!({"ref":selected})).unwrap();
        assert_eq!(inventory["sources"].as_object().unwrap().len(), 1);
        assert!(inventory["sources"].get(&eligible).is_some());
    }

    #[test]
    fn public_disposition_requires_judgment_and_becomes_quiet_after_effect() {
        let f = Fixture::new();
        let path = f.archive("terminal");
        let compact =
            crate::operating::start(json!({"target":f.0,"task":"Retire terminal history"}))
                .unwrap();
        assert_eq!(compact["planning_retention"]["candidate_count"], 1);
        assert!(
            compact["planning_retention"]["reference"]
                .as_str()
                .unwrap()
                .starts_with("detail:planning:")
        );
        let start = f.start(None);
        assert_eq!(
            start["planning"]["terminal_retention"]["status"],
            "judgment-required"
        );
        let unanswered = start["planning"]["terminal_retention"]["requests"][0].clone();
        assert!(f.start(Some(unanswered))["planning"]["terminal_retention"]["action"].is_null());
        let ready = f.ready();
        let action = &ready["decision_packet"]["primary_action"];
        assert_eq!(action["operation_id"], OP, "{ready}");
        let mut pending = action.clone();
        pending.as_object_mut().unwrap().remove("idempotency_key");
        pending["logical_effect_id"] = action["idempotency_key"].clone();
        assert_eq!(write_scope(&pending).unwrap(), write_scope(action).unwrap());
        crate::native_public::invoke_checked(
            json!({"target":f.0,"task":"Retire terminal history","invocation":action}),
        )
        .unwrap();
        assert!(!f.0.join(path).exists());
        assert!(!f.0.join(PENDING).exists());
        assert_eq!(
            f.start(None)["planning"]["terminal_retention"]["status"],
            "quiet"
        );
    }
    #[test]
    fn interrupted_deletion_recovers_before_during_and_after_commit() {
        for boundary in ["prepared", "removed", "committed"] {
            let f = Fixture::new();
            let paths = [f.archive("first"), f.archive("second")];
            let ready = f.ready();
            let action = &ready["decision_packet"]["primary_action"];
            let stopped = execute_checked(
                &f.0,
                &ready["decision_packet"],
                action,
                &mut || Ok(()),
                &mut |phase| {
                    if phase == boundary {
                        Err(err("simulated interruption"))
                    } else {
                        Ok(())
                    }
                },
            );
            assert!(stopped.is_err());
            assert!(f.0.join(PENDING).exists());
            let recovery = f.ready();
            let action = &recovery["decision_packet"]["primary_action"];
            assert_eq!(action["operation_id"], RECOVERY, "{recovery}");
            assert!(write_scope(action).unwrap().contains(&paths[0]));
            assert!(
                execute_checked(
                    &f.0,
                    &recovery["decision_packet"],
                    action,
                    &mut || Ok(()),
                    &mut |phase| {
                        if phase == boundary {
                            Err(err("interrupted recovery"))
                        } else {
                            Ok(())
                        }
                    }
                )
                .is_err()
            );
            let recovery = f.ready();
            let action = &recovery["decision_packet"]["primary_action"];
            crate::native_public::invoke_checked(
                json!({"target":f.0,"task":"Retire terminal history","invocation":action}),
            )
            .unwrap();
            assert!(paths.iter().all(|p| !f.0.join(p).exists()));
            assert!(!f.0.join(PENDING).exists());
            assert_eq!(
                f.start(None)["planning"]["terminal_retention"]["status"],
                "quiet"
            );
        }
    }

    #[test]
    fn recovery_preserves_remaining_sources_when_a_consumer_arrives() {
        let f = Fixture::new();
        let first = f.archive("first");
        let second = f.archive("second");
        let ready = f.ready();
        let stopped = execute_checked(
            &f.0,
            &ready["decision_packet"],
            &ready["decision_packet"]["primary_action"],
            &mut || Ok(()),
            &mut |phase| {
                if phase == "removed" {
                    Err(err("simulated interruption"))
                } else {
                    Ok(())
                }
            },
        );
        assert!(stopped.is_err());
        assert!(!f.0.join(first).exists());
        f.put(".agentic-workspace/proof/new.json", json!({"owner":second}));
        let recovery = f.ready();
        let action = &recovery["decision_packet"]["primary_action"];
        assert!(
            crate::native_public::invoke_checked(
                json!({"target":f.0,"task":"Retire terminal history","invocation":action})
            )
            .is_err()
        );
        assert!(f.0.join(second).exists());
        assert!(f.0.join(PENDING).exists());
    }

    #[test]
    fn linked_history_is_preserved_without_following_the_target() {
        let f = Fixture::new();
        let outside = Fixture::new();
        outside.put("terminal.json", json!({"retained":true}));
        let parent = f.0.join(HOME);
        std::fs::create_dir_all(&parent).unwrap();
        let link = parent.join("archive");
        #[cfg(windows)]
        junction::create(&outside.0, &link).unwrap();
        #[cfg(unix)]
        std::os::unix::fs::symlink(&outside.0, &link).unwrap();
        assert!(inventory(&f.0, &Value::Null).is_err());
        assert!(outside.0.join("terminal.json").exists());
        #[cfg(windows)]
        junction::delete(&link).unwrap();
        #[cfg(unix)]
        std::fs::remove_file(&link).unwrap();

        // Unrelated consumer trees are not a dependency of a no-candidate read.
        // A linked tree makes accidental eager enumeration observable without
        // a timing threshold. Once a candidate exists, confinement still applies.
        let link = f.0.join(".agentic-workspace/proof");
        #[cfg(windows)]
        junction::create(&outside.0, &link).unwrap();
        #[cfg(unix)]
        std::os::unix::fs::symlink(&outside.0, &link).unwrap();
        assert_eq!(inventory(&f.0, &Value::Null).unwrap()["sources"], json!({}));
        let selected = f.archive("selected");
        assert_eq!(
            inventory(&f.0, &json!({"ref":selected})).unwrap()["sources"],
            json!({})
        );
        assert!(inventory(&f.0, &Value::Null).is_err());
        assert!(outside.0.join("terminal.json").exists());
        #[cfg(windows)]
        junction::delete(&link).unwrap();
        #[cfg(unix)]
        std::fs::remove_file(&link).unwrap();
    }
    #[test]
    fn native_planning_proof_assignment_lifetime_has_bounded_current_state() {
        fn start(context: &Value, request: Value) -> Value {
            let mut input = context.clone();
            if !request.is_null() {
                input["request"] = request;
            }
            crate::native_public::start(input).unwrap()
        }
        fn invoke(context: &Value, ready: &Value) -> Value {
            let mut input = context.clone();
            input["invocation"] = ready["decision_packet"]["primary_action"].clone();
            crate::native_public::invoke_checked(input).unwrap()
        }
        let f = Fixture::new();
        let mut material: Value = serde_json::from_str(include_str!(
            "../../../../../tests/fixtures/external_consumer/planning-material.json"
        ))
        .unwrap();
        material["continuation"] =
            json!({"frontier":"No residual intent outside this bounded fixture."});
        std::fs::write(f.0.join("a.txt"), "current proof input").unwrap();
        std::fs::create_dir_all(f.0.join(".agentic-workspace/verification")).unwrap();
        std::fs::write(f.0.join(".agentic-workspace/verification/manifest.toml"), "schema_version='agentic-workspace/verification-manifest/v1'\n[protocols.check]\napplies_to_paths=['a.txt']\n[proof_routes.check]\nprotocol_refs=['check']\ncommands=['echo verified']\n").unwrap();
        std::fs::write(f.0.join(".agentic-workspace/config.local.toml"), "[delegation]\nassignment_policy='required-best-fit'\ncurrent_target='local'\ntransport_authority='manual'\n[delegation_targets.local]\ntransports=[{kind='internal'}]\n").unwrap();
        let unresolved = f.archive("unresolved-control");
        f.put(
            ".agentic-workspace/memory/control.json",
            json!({"owner":unresolved}),
        );
        let unresolved_bytes = std::fs::read(f.0.join(&unresolved)).unwrap();
        let began = std::time::Instant::now();
        let mut maximum = (0, 0);
        let cycles = std::env::var("AW_RETENTION_CYCLES")
            .ok()
            .and_then(|s| s.parse().ok())
            .unwrap_or(3);
        for n in 0..cycles {
            let context = json!({"target":f.0,"task":format!("Bounded fixture work {n}"),"changed":["a.txt"]});
            let mut create =
                start(&context, Value::Null)["planning"]["creation_requests"][0].clone();
            create["arguments"] = json!({"material":material});
            let created = invoke(&context, &start(&context, create));
            let selection_context = &created["value"]["selection_context"];
            invoke(
                selection_context,
                &start(
                    selection_context,
                    created["value"]["selection_request"].clone(),
                ),
            );
            let continuation = start(&context, Value::Null)["planning"]["requests"][0].clone();
            let mut task =
                start(&context, continuation.clone())["task_requirements"]["requests"][0].clone();
            task["arguments"]["required_result_classes"] = json!(["read-only"]);
            let mut assignment = start(&context, json!([continuation, task]))["task_requirements"]
                ["assignment"]["requests"][0]
                .clone();
            let answer = assignment.as_array_mut().unwrap().last_mut().unwrap();
            answer["arguments"]["alternative"] = json!("local:internal");
            answer["arguments"]["reason"] =
                json!("Current local target is sufficient for this bounded fixture.");
            let assessed = start(&context, assignment.clone());
            assert_eq!(
                assessed["task_requirements"]["implementation_admission"]["status"],
                "admitted-local"
            );
            assignment
                .as_array_mut()
                .unwrap()
                .push(assessed["verification"]["execution_requests"][0].clone());
            let proof = invoke(&context, &start(&context, assignment));
            assert_eq!(proof["effect_outcome"]["status"], "committed", "{proof}");
            let proof_id = proof["value"]["publication"]["reference"]
                .as_str()
                .unwrap()
                .rsplit('/')
                .next()
                .unwrap();
            let proof_path =
                f.0.join(format!(".agentic-workspace/proof/receipts/{proof_id}.json"));
            let proof_bytes = std::fs::read(&proof_path).unwrap();
            let mut update =
                start(&context, continuation.clone())["planning"]["update_requests"][0].clone();
            let mut closed = material.clone();
            closed["lifecycle"] = json!("closed");
            closed["phase"] = json!("complete");

            update["arguments"]["material"] = closed;
            invoke(&context, &start(&context, json!([continuation, update])));
            let current = start(&context, Value::Null);
            if n > 0 {
                let mut disposition =
                    current["planning"]["terminal_retention"]["requests"][0].clone();
                disposition["arguments"]["terminal"] = json!(true);
                disposition["arguments"]["no_unresolved_intent"] = json!(true);
                disposition["arguments"]["no_continuing_value"] = json!(true);
                disposition["arguments"]["reason"] = json!(
                    "Previous fixture work is complete; only current selection retains value."
                );
                invoke(&context, &start(&context, disposition));
            }
            let current = start(&context, Value::Null);
            if n > 0 {
                let mut retire = current["verification"]["retention"]["requests"][0].clone();
                retire["arguments"]["superseded"] = json!(true);
                retire["arguments"]["no_unresolved_intent"] = json!(true);
                retire["arguments"]["no_continuing_value"] = json!(true);
                retire["arguments"]["reason"] = json!(
                    "The completed prior Planning subject no longer exists; current reusable proof remains protected."
                );
                invoke(&context, &start(&context, retire));
            }
            assert_eq!(std::fs::read(&proof_path).unwrap(), proof_bytes);
            assert_eq!(
                std::fs::read(f.0.join(&unresolved)).unwrap(),
                unresolved_bytes
            );
            let root = Dir::open_ambient_dir(&f.0, ambient_authority()).unwrap();
            let mut retained = BTreeMap::new();
            for directory in [
                ".agentic-workspace/planning",
                ".agentic-workspace/proof",
                ".agentic-workspace/memory",
                ".agentic-workspace/verification",
            ] {
                files(&root, directory, &mut retained).unwrap();
            }
            retained.retain(|p, _| {
                !p.starts_with(".agentic-workspace/local/") && !p.ends_with(".lock")
            });
            let footprint = (
                retained.len(),
                retained.values().map(Vec::len).sum::<usize>(),
            );
            maximum = (maximum.0.max(footprint.0), maximum.1.max(footprint.1));
            assert!(
                footprint.0 <= 8 && footprint.1 < 65536,
                "{n}: {footprint:?}"
            );
            if n % 25 == 0 {
                eprintln!(
                    "mixed retention cycle {n}: {footprint:?}, {:?}",
                    began.elapsed()
                );
            }
            assert_eq!(
                start(&context, Value::Null)["verification"]["retention"]["status"],
                "quiet"
            );
            assert_eq!(
                start(&context, Value::Null)["planning"]["terminal_retention"]["status"],
                "quiet"
            );
        }
        eprintln!(
            "mixed retention {cycles} cycles: maximum {maximum:?}, {:?}",
            began.elapsed()
        );
    }
}
