//! Terminal Memory source and declaration disposition. Selection retirement is never
//! deletion authority. Exact agent judgement, live references and effect custody
//! remain separate. Recovery is local and does not require a tracked tombstone.
use crate::{CoreError, digest};
use cap_std::{
    ambient_authority,
    fs::{Dir, OpenOptions},
};
use serde_json::{Value, json};
use std::{collections::BTreeMap, io::Write, path::Path};

pub(crate) const REQUEST: &str = "memory/terminal-disposition/v1";
pub(crate) const RECOVER: &str = "memory/recover-terminal-disposition/v1";
pub(crate) const OP: &str = "memory.retire-terminal";
pub(crate) const RECOVERY: &str = "memory.recover-terminal";
const HOME: &str = ".agentic-workspace/memory/repo/";
const MANIFEST: &str = ".agentic-workspace/memory/repo/manifest.toml";
const PENDING: &str = ".agentic-workspace/local/memory/terminal-disposition.json";

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
            "Memory retirement recovery exceeds source bound; preserved",
        ));
    }
    Ok(bytes)
}

pub(crate) fn declarations() -> Vec<Value> {
    vec![
        json!({"kind":REQUEST,"result_kind":"agentic-memory/terminal-disposition/v1","input_schema":{
        "$schema":"https://json-schema.org/draft/2020-12/schema","type":"object","additionalProperties":false,
        "properties":{"sources":{"type":"array","minItems":1,"maxItems":1,"uniqueItems":true,"items":{"type":"string"}},
        "terminal":{"type":"boolean"},"no_unresolved_intent":{"type":"boolean"},"no_continuing_value":{"type":"boolean"},
        "reason":{"type":"string","maxLength":2048}},
        "required":["sources","terminal","no_unresolved_intent","no_continuing_value","reason"]}}),
        json!({"kind":RECOVER,"result_kind":"agentic-memory/terminal-disposition/v1","input_schema":{
        "$schema":"https://json-schema.org/draft/2020-12/schema","type":"object","additionalProperties":false,
        "properties":{"record_revision":{"type":"string"}},"required":["record_revision"]}}),
    ]
}
pub(crate) fn operations() -> Vec<Value> {
    [OP,RECOVERY].into_iter().map(|id| json!({"id":id,"semantic_revision":"memory-terminal-disposition-v1",
        "input_schema":{"$schema":"https://json-schema.org/draft/2020-12/schema","type":"object","additionalProperties":false,
        "properties":{"target":{"type":"string"},"request":{"type":"object"},"binding":{"type":"object"}},
        "required":["target","request","binding"]},"result_kind":"agentic-memory/terminal-disposition/v1",
        "effects":["memory-state"],"reads":["memory"]})).collect()
}

use crate::retention_sources::files;

fn observe_sources(root: &Dir) -> Result<BTreeMap<String, Vec<u8>>, CoreError> {
    let mut sources = BTreeMap::new();
    for path in [
        ".agentic-workspace/memory",
        ".agentic-workspace/planning",
        ".agentic-workspace/proof",
        ".agentic-workspace/verification",
        ".agentic-workspace/evaluations",
        ".agentic-workspace/reconstruction",
        ".agentic-workspace/system-intent",
        ".agentic-workspace/instructions",
        ".agentic-workspace/local/decision-point-intent",
        "docs/decisions",
    ] {
        files(root, path, &mut sources)?;
    }
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
    Ok(sources)
}

fn inventory_for(target: &Path, preferred: &[String]) -> Result<Value, CoreError> {
    let root = Dir::open_ambient_dir(target, ambient_authority()).map_err(err)?;
    let mut sources = observe_sources(&root)?;
    let Some(raw) = sources.remove(MANIFEST) else {
        return Ok(json!({"sources":{}}));
    };
    let text = std::str::from_utf8(&raw).map_err(err)?;
    let crlf = text.contains("\r\n");
    if crlf && text.replace("\r\n", "").contains('\n') {
        return Err(err(
            "Mixed Memory manifest line endings require source repair",
        ));
    }
    let normalized = text.replace("\r\n", "\n");
    let text = normalized.as_str();
    let document = text.parse::<toml_edit::DocumentMut>().map_err(err)?;
    if document.to_string() != text {
        return Err(err("Memory manifest cannot be preserved exactly"));
    }
    let manifest: toml::Value = toml::from_str(text).map_err(err)?;
    let mut protected = Vec::new();
    let mut offered = json!({});
    let mut post = String::new();
    for (source, note) in manifest
        .get("notes")
        .and_then(toml::Value::as_table)
        .into_iter()
        .flatten()
    {
        if !preferred.is_empty() && !preferred.contains(source) {
            continue;
        }
        crate::decision_source::relative(source)?;
        if !source.starts_with(HOME) || !source.ends_with(".md") || source == MANIFEST {
            continue;
        }
        let Some(bytes) = sources.get(source) else {
            continue;
        };
        let status = note
            .get("disposition")
            .and_then(|d| d.get("status"))
            .and_then(toml::Value::as_str);
        // Selection retirement nominates a value question; it never authorizes
        // destroying source text promised to remain available by that action.
        let dependency_changed = note
            .get("dependencies")
            .and_then(toml::Value::as_table)
            .into_iter()
            .flatten()
            .any(|(path, expected)| {
                read(&root, path)
                    .ok()
                    .flatten()
                    .is_none_or(|bytes| expected.as_str() != Some(revision(&bytes).as_str()))
            });
        if preferred.is_empty()
            && !dependency_changed
            && !matches!(status, Some("retire" | "promote"))
        {
            continue;
        }
        let mut proposed_document = document.clone();
        proposed_document["notes"]
            .as_table_mut()
            .ok_or_else(|| err("Memory notes table absent"))?
            .remove(source)
            .ok_or_else(|| err("Memory note absent"))?;
        let proposed = proposed_document.to_string();
        // Removing this exact declaration must preserve every sibling semantically.
        let remaining: toml::Value = toml::from_str(&proposed).map_err(err)?;
        let mut expected = manifest.clone();
        expected
            .get_mut("notes")
            .and_then(toml::Value::as_table_mut)
            .unwrap()
            .remove(source);
        if remaining.get("notes").is_none()
            && expected["notes"]
                .as_table()
                .is_some_and(|notes| notes.is_empty())
        {
            expected.as_table_mut().unwrap().remove("notes");
        }
        if remaining != expected {
            return Err(err("Memory sibling declaration changed"));
        }
        let relative = source.strip_prefix(HOME).unwrap();
        let consumers: Vec<_> = sources
            .iter()
            .filter(|(p, b)| {
                *p != source && {
                    let value = String::from_utf8_lossy(b);
                    value.contains(source) || value.contains(relative)
                }
            })
            .map(|(p, _)| p.clone())
            .chain(
                (proposed.contains(source) || proposed.contains(relative))
                    .then(|| MANIFEST.to_owned()),
            )
            .collect();
        if !consumers.is_empty() {
            protected.push(json!({"source":source,"consumers":consumers}));
            continue;
        }
        offered[source] = json!(revision(bytes));
        post = if crlf {
            proposed.replace("\n", "\r\n")
        } else {
            proposed
        };
        break;
    }
    let guards: BTreeMap<_, _> = sources
        .iter()
        .filter(|(p, _)| offered.get(*p).is_none())
        .map(|(p, b)| (p.clone(), revision(b)))
        .collect();
    Ok(
        json!({"sources":offered,"manifest_revision":revision(&raw),"manifest_post":post,
        "guard_revision":digest(&json!(guards))?,"protected":protected}),
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
        || invocation["source_owner"] != "memory"
        || record["outcome"] != outcome(invocation)
    {
        return Err(err("Unrecognised Memory retirement recovery preserved"));
    }
    let prepared = crate::attempt_store::prepare_commit(
        target.to_str().unwrap(),
        record["custody"].clone(),
        record["outcome"].clone(),
    )?;
    if prepared["record"]["invocation"] != *invocation {
        return Err(err("Memory retirement custody mismatch"));
    }
    if let Some(recovery) = record.get("recovery") {
        let prepared = crate::attempt_store::prepare_commit(
            target.to_str().unwrap(),
            recovery["custody"].clone(),
            recovery_outcome(&record),
        )?;
        if prepared["record"]["invocation"] != recovery["invocation"]
            || recovery["invocation"]["operation_id"] != RECOVERY
            || recovery["invocation"]["source_owner"] != "memory"
        {
            return Err(err("Memory recovery attempt custody mismatch"));
        }
    }
    Ok(Some(record))
}
fn outcome(invocation: &Value) -> Value {
    json!({"status":"applied","effects":["memory-state"],"value":{"kind":"agentic-memory/terminal-disposition/v1",
        "retired":invocation["arguments"]["request"]["arguments"]["sources"],"tracked_tombstone":false,"completion_authority":false}})
}
fn recovery_outcome(record: &Value) -> Value {
    json!({"status":"applied","effects":["memory-state"],"value":{"kind":"agentic-memory/terminal-disposition/v1","retired":record["outcome"]["value"]["retired"],"recovered":true,"tracked_tombstone":false,"completion_authority":false}})
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
        .find(|o| o["owner"] == "memory")
        .ok_or_else(|| err("Memory owner unavailable"))?;
    let pending = retained(target)?;
    let binding = if let Some(record) = &pending {
        json!({"record_revision":digest(record)?})
    } else {
        match inventory_for(
            target,
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

    let kind = if recovery { RECOVER } else { REQUEST };
    let args = if recovery {
        binding.clone()
    } else {
        json!({"sources":if sources.is_empty() {vec!["<exact declared Memory source>".to_owned()]} else {sources.clone()},"terminal":false,"no_unresolved_intent":false,"no_continuing_value":false,"reason":""})
    };
    let template = json!({"kind":"agentic-workspace/public-request/v1","id":kind,"owner":"memory","owner_revision":owner["revision"],
        "source_revision":if !recovery && sources.is_empty() {digest(&json!([]))?} else {digest(&json!([binding["sources"],binding["manifest_revision"],binding["manifest_post"],binding["guard_revision"],binding["record_revision"]]))?},"capability_revision":contract["revision"],"task_identity":work,"request_kind":kind,"arguments":args});
    let mut result = json!({"status":if recovery {"recovery-required"} else if sources.is_empty() {"quiet"} else {"judgment-required"},"requests":[template],
        "sources":binding["sources"],"protected":binding["protected"],"authority":"Read the exact sources and judge terminal intent and future value; discovery grants no deletion authority."});
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
                "Memory retirement source changed; resolve current disposition",
            ));
        }
        let args = &request["arguments"];
        if recovery {
            if args != &binding {
                return Err(err("Memory retirement recovery changed"));
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
                    return Err(err("Memory retirement source is not offered"));
                }
            }
        }
        result["action"] = json!({"operation_id":if recovery {RECOVERY} else {OP},"dependency_revision":digest(&json!([binding,request]))?,
            "arguments":{"target":target,"request":request,"binding":binding},"effects":["memory-state"],"source_requests":[request]});
    }
    Ok(result)
}

fn verify(root: &Dir, invocation: &Value, allow_absent: bool) -> Result<(), CoreError> {
    let binding = &invocation["arguments"]["binding"];
    let expected = binding["sources"]
        .as_object()
        .ok_or_else(|| err("Memory retirement sources missing"))?;
    let retiring = invocation["arguments"]["request"]["arguments"]["sources"]
        .as_array()
        .ok_or_else(|| err("Memory retirement selection missing"))?;
    let mut observed: BTreeMap<_, _> = observe_sources(root)?
        .into_iter()
        .map(|(p, b)| (p, revision(&b)))
        .collect();
    let manifest = observed
        .remove(MANIFEST)
        .ok_or_else(|| err("Memory manifest disappeared"))?;
    if binding["manifest_revision"] != manifest
        && !(allow_absent
            && revision(
                binding["manifest_post"]
                    .as_str()
                    .ok_or_else(|| err("Memory manifest postimage absent"))?
                    .as_bytes(),
            ) == manifest)
    {
        return Err(err(
            "Memory manifest changed; preserve source and declarations",
        ));
    }
    for (path, revision) in expected {
        match observed.remove(path) {
            Some(current) if revision == &current => {}
            None if allow_absent && retiring.contains(&json!(path)) => {}
            _ => {
                return Err(err(
                    "Memory retirement source changed; preserve remaining sources",
                ));
            }
        }
    }
    if binding["guard_revision"] != digest(&json!(observed))? {
        return Err(err(
            "Memory retirement consumer changed; preserve remaining sources",
        ));
    }
    Ok(())
}

pub(crate) fn write_scope(action: &Value) -> Result<Vec<String>, CoreError> {
    let mut paths =
        crate::attempt_store::write_paths(&json!({"idempotency_key":effect_identity(action)}))?;
    paths.extend([
        PENDING.into(),
        ".agentic-workspace/local/effects/memory.lock".into(),
        MANIFEST.into(),
    ]);
    paths.push(temporary(action)?);
    paths.push(format!("{}.manifest", temporary(action)?));
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
        let held = retained(target)?.ok_or_else(|| err("Memory retirement recovery absent"))?;
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
    let lock_path = ".agentic-workspace/local/effects/memory.lock";
    read(&root, lock_path)?;
    root.create_dir_all(".agentic-workspace/local/effects")
        .map_err(err)?;
    root.create_dir_all(".agentic-workspace/local/memory")
        .map_err(err)?;
    read(&root, lock_path)?;
    let lock = root
        .open_with(
            lock_path,
            OpenOptions::new().read(true).write(true).create(true),
        )
        .map_err(err)?;
    let lock = lock.into_std();
    if lock.metadata().map_err(err)?.len() != 0 {
        return Err(err("Unknown Memory lock preserved"));
    }
    lock.try_lock().map_err(err)?;
    revalidate()?;
    let recovery = invocation["operation_id"] == RECOVERY;
    let previous = retained(target)?;
    if previous.is_some() != recovery {
        return Err(err("Memory retirement requires its exact recovery route"));
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
    let post = record["invocation"]["arguments"]["binding"]["manifest_post"]
        .as_str()
        .ok_or_else(|| err("Memory manifest postimage missing"))?;
    if read(&root, MANIFEST)?.as_deref() != Some(post.as_bytes()) {
        let temp = format!("{}.manifest", temporary(invocation)?);
        // A prior interrupted attempt's exact postimage may be resumed; unknown
        // temporary bytes remain protected instead of being overwritten.
        if let Some(bytes) = read(&root, &temp)? {
            if bytes != post.as_bytes() {
                return Err(err("Memory manifest temporary changed"));
            }
        } else {
            let mut file = root
                .open_with(&temp, OpenOptions::new().write(true).create_new(true))
                .map_err(err)?;
            file.write_all(post.as_bytes()).map_err(err)?;
            file.sync_all().map_err(err)?;
        }
        verify(&root, &record["invocation"], recovery)?;
        root.rename(&temp, &root, MANIFEST).map_err(err)?;
    }
    observe("manifest")?;
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
    let mut changed = record["outcome"]["value"]["retired"]
        .as_array()
        .unwrap()
        .clone();
    changed.push(json!(MANIFEST));
    Ok(json!({"outcome":out,"custody":custody,"post_effect_changed_paths":changed}))
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
            let path = format!("{HOME}domains/{name}.md");
            let source = self.0.join(&path);
            std::fs::create_dir_all(source.parent().unwrap()).unwrap();
            std::fs::write(&source, "Expired fixture lesson.").unwrap();
            std::fs::write(self.0.join(MANIFEST),format!("version=1\n# Sibling comment\n[notes.\"{path}\"]\nnote_type='domain'\ndisposition={{status='retire'}}\n")).unwrap();
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
                self.start(None)["memory"]["terminal_retention"]["requests"][0].clone();
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
    fn interrupted_deletion_recovers_before_during_and_after_commit() {
        for boundary in ["prepared", "manifest", "removed", "committed"] {
            let f = Fixture::new();
            let paths = [f.archive("first")];
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
                f.start(None)["memory"]["terminal_retention"]["status"],
                "quiet"
            );
        }
    }

    #[test]
    fn protects_live_consumers_manifest_siblings_and_stale_sources() {
        let f = Fixture::new();
        let source = f.archive("first");
        let ready = f.ready();
        let action = &ready["decision_packet"]["primary_action"];
        assert_eq!(action["operation_id"], OP, "{ready}");
        let root = Dir::open_ambient_dir(&f.0, ambient_authority()).unwrap();
        verify(&root, action, false).unwrap();
        f.put(
            ".agentic-workspace/planning/live.json",
            json!({"source":source}),
        );
        assert!(verify(&root, action, false).is_err());
        assert!(
            inventory_for(&f.0, &[]).unwrap()["sources"]
                .as_object()
                .unwrap()
                .is_empty()
        );
        std::fs::remove_file(f.0.join(".agentic-workspace/planning/live.json")).unwrap();
        let mut manifest = std::fs::read_to_string(f.0.join(MANIFEST)).unwrap();
        manifest.push_str(&format!(
            "[durable_facts.live]\nsummary='Keep this useful fact'\nnote_ref='{source}#fact'\n"
        ));
        std::fs::write(f.0.join(MANIFEST), manifest).unwrap();
        assert!(verify(&root, action, false).is_err());
        assert!(
            inventory_for(&f.0, &[]).unwrap()["sources"]
                .as_object()
                .unwrap()
                .is_empty()
        );
        assert!(f.0.join(source).exists());
    }
    #[test]
    fn unanswered_disposition_is_readonly_and_preserves_retired_text() {
        let f = Fixture::new();
        let source = f.archive("first");
        let start = f.start(None);
        let request = start["memory"]["terminal_retention"]["requests"][0].clone();
        assert!(f.start(Some(request))["memory"]["terminal_retention"]["action"].is_null());
        assert!(f.0.join(source).exists());
        assert!(!f.0.join(PENDING).exists());
    }
    #[test]
    fn recovery_preserves_source_after_new_consumer() {
        let f = Fixture::new();
        let source = f.archive("first");
        let ready = f.ready();
        assert!(
            execute_checked(
                &f.0,
                &ready["decision_packet"],
                &ready["decision_packet"]["primary_action"],
                &mut || Ok(()),
                &mut |phase| if phase == "manifest" {
                    Err(err("stop"))
                } else {
                    Ok(())
                }
            )
            .is_err()
        );
        f.put(
            ".agentic-workspace/planning/new.json",
            json!({"source":source}),
        );
        let ready = f.ready();
        assert!(crate::native_public::invoke_checked(json!({"target":f.0,"task":"Retire terminal history","invocation":ready["decision_packet"]["primary_action"]})).is_err());
        assert!(f.0.join(source).exists());
        assert!(f.0.join(PENDING).exists());
    }
    #[test]
    fn repeated_native_advisory_capture_and_disposition_is_bounded() {
        let f = Fixture::new();
        std::fs::write(f.0.join("policy.md"), "initial").unwrap();
        let context = json!({"target":f.0,"task":"Bounded Memory lifecycle fixture","changed":["src/core.rs"]});
        let start = |request: Value| {
            let mut input = context.clone();
            if !request.is_null() {
                input["request"] = request;
            }
            crate::native_public::start(input).unwrap()
        };
        let invoke = |ready: &Value| {
            let mut input = context.clone();
            input["invocation"] = ready["decision_packet"]["primary_action"].clone();
            crate::native_public::invoke_checked(input).unwrap()
        };
        let cycles = std::env::var("AW_MEMORY_RETENTION_CYCLES")
            .ok()
            .and_then(|v| v.parse::<usize>().ok())
            .unwrap_or(3);
        let began = std::time::Instant::now();
        let mut maximum = (0, 0);
        for n in 0..cycles {
            let mut request =
                start(Value::Null)["memory"]["advisory_capture"]["requests"][0].clone();
            request["arguments"]["material"] = json!({"id":format!("lesson-{n}"),"lesson":"Fixture lesson tied to exact policy bytes.","rationale":"Avoid rediscovery during the current fixture phase.","dependency_paths":["policy.md"]});
            let proposed = start(request);
            let mut answer =
                proposed["decision_packet"]["decision_request"]["response_request"].clone();
            answer["arguments"]["answer"] = json!("confirm-retention");
            let ready = start(answer);
            assert_eq!(
                ready["decision_packet"]["primary_action"]["operation_id"],
                "memory.capture-advisory",
                "{}",
                ready["decision_packet"]
            );
            invoke(&ready);
            std::fs::write(f.0.join("policy.md"), format!("phase-{}", n + 1)).unwrap();
            let mut request =
                start(Value::Null)["memory"]["terminal_retention"]["requests"][0].clone();
            request["arguments"]["terminal"] = json!(true);
            request["arguments"]["no_unresolved_intent"] = json!(true);
            request["arguments"]["no_continuing_value"] = json!(true);
            request["arguments"]["reason"] = json!(
                "Fixture phase completed; changed policy makes its advisory lesson obsolete. No unresolved intent or reusable fact remains."
            );
            let ready = start(request);
            assert_eq!(
                ready["decision_packet"]["primary_action"]["operation_id"], OP,
                "{}",
                ready["decision_packet"]
            );
            invoke(&ready);
            let root = Dir::open_ambient_dir(&f.0, ambient_authority()).unwrap();
            let mut fileset = BTreeMap::new();
            files(&root, HOME.trim_end_matches('/'), &mut fileset).unwrap();
            let count = (fileset.len(), fileset.values().map(Vec::len).sum::<usize>());
            maximum = maximum.max(count);
            assert!(count.0 <= 1 && count.1 < 1024, "{count:?}");
            assert_eq!(
                start(Value::Null)["memory"]["terminal_retention"]["status"],
                "quiet"
            );
            if n % 25 == 0 {
                eprintln!("Memory cycle {n}: {count:?}, {:?}", began.elapsed());
            }
        }
        eprintln!(
            "Memory {cycles} cycles: maximum {maximum:?}, {:?}",
            began.elapsed()
        );
    }
    #[test]
    fn manifest_line_endings_comments_and_unrelated_entries_survive() {
        let f = Fixture::new();
        let source = f.archive("first");
        let other = format!("{HOME}domains/keep.md");
        std::fs::write(f.0.join(&other), "Useful source stays.").unwrap();
        let sibling =
            format!("# Exact sibling comment\n[notes.\"{other}\"]\nnote_type = 'domain'\n");
        let before = std::fs::read_to_string(f.0.join(MANIFEST)).unwrap() + &sibling;
        std::fs::write(f.0.join(MANIFEST), before.replace("\n", "\r\n")).unwrap();
        let ready = f.ready();
        crate::native_public::invoke_checked(json!({"target":f.0,"task":"Retire terminal history","invocation":ready["decision_packet"]["primary_action"]})).unwrap();
        let after = std::fs::read_to_string(f.0.join(MANIFEST)).unwrap();
        assert!(after.contains(&sibling.replace("\n", "\r\n")));
        assert!(!after.contains(&source));
        assert!(f.0.join(other).exists());
    }
    #[test]
    fn linked_memory_preserves_external_source() {
        let f = Fixture::new();
        let external = Fixture::new();
        let source = f.archive("first");
        std::fs::create_dir_all(external.0.join("outside")).unwrap();
        let link = f.0.join(format!("{HOME}linked"));
        #[cfg(windows)]
        junction::create(external.0.join("outside"), &link).unwrap();
        #[cfg(unix)]
        std::os::unix::fs::symlink(external.0.join("outside"), &link).unwrap();
        assert!(inventory_for(&f.0, &[]).is_err());
        assert!(f.0.join(source).exists());
        #[cfg(windows)]
        junction::delete(&link).unwrap();
        #[cfg(unix)]
        std::fs::remove_file(&link).unwrap();
    }
}
