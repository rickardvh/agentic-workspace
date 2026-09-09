//! One exact externally owned Memory disposition. Receiving authority is
//! observed independently; attempt evidence grants no corpus custody.
use crate::{CoreError, digest};
use cap_std::{
    ambient_authority,
    fs::{Dir, OpenOptions},
};
use serde_json::{Value, json};
use std::{io::Write, path::Path};

const MANIFEST: &str = ".agentic-workspace/memory/repo/manifest.toml";
pub(crate) const EDIT: &str = "memory/dispose-source/v1";
const RECOVER: &str = "memory/recover-disposition/v1";
const EFFECT: &str = "memory-state";
const SEMANTICS: &str = "memory-external-disposition-v1";

fn err(e: impl ToString) -> CoreError {
    CoreError::new(e.to_string())
}
fn read(root: &Dir, path: &str) -> Result<Vec<u8>, CoreError> {
    crate::native_planning::read(root, path)?
        .ok_or_else(|| err("Memory disposition source missing"))
}
fn revisions(target: &Path, references: &Value) -> Result<Value, CoreError> {
    let root = Dir::open_ambient_dir(target, ambient_authority()).map_err(err)?;
    let mut result = json!({});
    for reference in references
        .as_object()
        .ok_or_else(|| err("Memory source binding missing"))?
        .keys()
    {
        result[reference] = json!(crate::native_intent::hash(&read(&root, reference)?));
    }
    Ok(result)
}

pub(crate) fn extend_owner(owner: &mut Value) -> Result<(), CoreError> {
    let args = json!({"$schema":"https://json-schema.org/draft/2020-12/schema","type":"object","properties":{
        "source":{"type":"string","minLength":1},"fact":{"type":"string","minLength":1,"maxLength":256},"disposition":{"enum":["retain","retire","promote"]},
        "reason":{"type":"string","minLength":1,"maxLength":2048},
        "receiver":{"type":"object"},"answer":{"enum":["authorize-disposition","defer"]},
        "proposal_revision":{"type":"string"}},"required":["source","disposition","reason"],"additionalProperties":false});
    let recovery = json!({"$schema":"https://json-schema.org/draft/2020-12/schema","type":"object","properties":{
        "record_revision":{"type":"string"}},"required":["record_revision"],"additionalProperties":false});
    let operation = |id: &str| {
        json!({"id":id,"semantic_revision":SEMANTICS,
        "input_schema":{"$schema":"https://json-schema.org/draft/2020-12/schema","type":"object","properties":{
        "target":{"type":"string"},"request":{"type":"object"},"binding":{"type":"object"},
        "post_revision":{"type":"string"}},"required":["target","request","binding","post_revision"],"additionalProperties":false},
        "result_kind":"agentic-memory/disposition-result/v1","effects":[EFFECT],"reads":["memory"]})
    };
    owner["domains"] = json!(["memory"]);
    owner["effects"] = json!([{"id":EFFECT,"domain":"memory"}]);
    owner["operations"] = json!([
        operation("memory.dispose"),
        operation("memory.recover-disposition")
    ]);
    owner["requests"].as_array_mut().unwrap().extend([
        json!({"kind":EDIT,"result_kind":"agentic-memory/disposition-proposal/v1","input_schema":args}),
        json!({"kind":RECOVER,"result_kind":"agentic-memory/disposition-result/v1","input_schema":recovery})]);
    owner["revision"] = json!(digest(&json!([owner["requests"], owner["operations"]]))?);
    Ok(())
}

fn proposed(target: &Path, args: &Value, binding: &Value) -> Result<Vec<u8>, CoreError> {
    let source = args["source"]
        .as_str()
        .ok_or_else(|| err("Memory source missing"))?;
    let root = Dir::open_ambient_dir(target, ambient_authority()).map_err(err)?;
    let raw = read(&root, MANIFEST)?;
    let text = std::str::from_utf8(&raw).map_err(err)?;
    let crlf = text.contains("\r\n");
    if crlf && text.replace("\r\n", "").contains('\n') {
        return Err(err(
            "Mixed Memory source line endings require source-owner repair",
        ));
    }
    let normalized = text.replace("\r\n", "\n");
    let text = normalized.as_str();
    let mut document = text.parse::<toml_edit::DocumentMut>().map_err(err)?;
    let (table, key) = args["fact"]
        .as_str()
        .map_or(("notes", source), |fact| ("durable_facts", fact));
    let note = document
        .get_mut(table)
        .and_then(|n| n.get_mut(key))
        .and_then(toml_edit::Item::as_table_mut)
        .ok_or_else(|| err("Memory disposition requires one declared ordinary note table"))?;
    let previous = note.get("disposition").cloned();
    let mut material = json!({"status":args["disposition"],"note_revision":binding["sources"][source],
        "reason":args["reason"]});
    if let Some(receiver) = args.get("receiver") {
        material["receiver"] = receiver.clone();
    }
    let payload = toml_edit::ser::to_document(&material).map_err(err)?;
    note.insert(
        "disposition",
        toml_edit::Item::Value(toml_edit::Value::InlineTable(
            payload.as_table().clone().into_inline_table(),
        )),
    );
    let rendered = document.to_string();
    let note = document[table][key].as_table_mut().unwrap();
    if let Some(previous) = previous {
        note.insert("disposition", previous);
    } else {
        note.remove("disposition");
    }
    if document.to_string() != text {
        return Err(err(
            "Memory disposition cannot preserve unrelated source bytes",
        ));
    }
    let _: toml::Value = toml::from_str(&rendered).map_err(err)?;
    let bytes = if crlf {
        rendered.replace('\n', "\r\n")
    } else {
        rendered
    }
    .into_bytes();
    if bytes.len() > 262144 {
        return Err(err("Memory postimage exceeds the bounded source size"));
    }
    Ok(bytes)
}

fn marker(post: &str) -> String {
    format!(
        ".agentic-workspace/local/effects/memory-{}.prepared.json",
        &post[7..]
    )
}
fn outcome(invocation: &Value) -> Value {
    json!({"status":"applied","effects":[EFFECT],"value":{"kind":"agentic-memory/disposition-result/v1",
        "source":invocation["arguments"]["request"]["arguments"]["source"],
        "fact":invocation["arguments"]["request"]["arguments"]["fact"],
        "disposition":invocation["arguments"]["request"]["arguments"]["disposition"],
        "post_revision":invocation["arguments"]["post_revision"],"source_ownership":"repo-human",
        "continuing_custody":false,"completion_authority":false}})
}
fn retained(target: &Path, post: &str) -> Result<Option<Value>, CoreError> {
    let root = Dir::open_ambient_dir(target, ambient_authority()).map_err(err)?;
    let Some(raw) = crate::native_planning::read(&root, &marker(post))? else {
        return Ok(None);
    };
    let record: Value = serde_json::from_slice(&raw).map_err(err)?;
    let evidence = serde_json::from_value(record["custody"]["attempt"].clone()).map_err(err)?;
    let attempt = crate::attempt_store::read_source(target.to_str().unwrap(), &evidence)?;
    let i = &record["invocation"];
    if attempt["invocation"] != *i
        || i["operation_id"] != "memory.dispose"
        || i["arguments"]["target"] != target.to_str().unwrap()
        || i["arguments"]["post_revision"] != post
        || record["outcome"] != outcome(i)
    {
        return Err(err(
            "Memory disposition evidence does not match its exact attempt",
        ));
    }
    crate::attempt_store::prepare_commit(
        target.to_str().unwrap(),
        record["custody"].clone(),
        record["outcome"].clone(),
    )?;
    Ok(Some(record))
}

pub(crate) fn view(
    target: &Path,
    work: &Value,
    memory: &Value,
    config: &Value,
    contract: &Value,
    request: Option<&Value>,
) -> Result<Value, CoreError> {
    let owner = contract["owners"]
        .as_array()
        .unwrap()
        .iter()
        .find(|o| o["owner"] == "memory")
        .unwrap();
    let mut result = json!({"status":"not-applicable","requests":[],"recovery_requests":[],
        "contribution":{"owner":"memory","revision":memory["revision"],"actions":[]}});
    let mut references = json!({});
    for note in memory["selected_notes"].as_array().into_iter().flatten() {
        if note["source"]["revision"].is_string() {
            references[note["source"]["reference"].as_str().unwrap()] = Value::Null;
        }
    }
    if references.as_object().unwrap().is_empty() {
        if request.is_some() {
            return Err(err("Memory disposition has no current selected source"));
        }
        return Ok(result);
    }
    references[MANIFEST] = Value::Null;
    let sources = match revisions(target, &references) {
        Ok(sources) => sources,
        Err(e) => {
            if request.is_some() {
                return Err(e);
            }
            return Ok(result);
        }
    };
    let binding = json!({"sources":sources,"selection_revision":memory["revision"],
        "effective_policy_revision":config["revision"],"capability_revision":contract["revision"],
        "receiving_admissions":memory["receiving_admissions"]});
    result["contribution"]["revision"] = json!(digest(&binding)?);
    let template = |kind: &str, args: Value| {
        json!({"kind":"agentic-workspace/public-request/v1",
        "id":kind,"owner":"memory","owner_revision":owner["revision"],"source_revision":digest(&binding).unwrap(),
        "capability_revision":contract["revision"],"task_identity":work,"request_kind":kind,"arguments":args})
    };
    for source in references
        .as_object()
        .unwrap()
        .keys()
        .filter(|p| p.as_str() != MANIFEST)
    {
        result["requests"].as_array_mut().unwrap().push(template(EDIT,
            json!({"source":source,"disposition":"retain","reason":"Assess the selected note's durable value and current disposition."})));
    }
    let root = Dir::open_ambient_dir(target, ambient_authority()).map_err(err)?;
    let manifest: toml::Value =
        toml::from_str(std::str::from_utf8(&read(&root, MANIFEST)?).map_err(err)?).map_err(err)?;
    if manifest.get("version").and_then(toml::Value::as_integer) != Some(1) {
        if request.is_some() {
            return Err(err("Unsupported Memory manifest version; source preserved"));
        }
        result["requests"] = json!([]);
        result["diagnostics"] = json!([{"code":"unsupported-manifest-version","source":MANIFEST}]);
        return Ok(result);
    }
    for (id, fact) in manifest
        .get("durable_facts")
        .and_then(toml::Value::as_table)
        .into_iter()
        .flatten()
        .take(128)
    {
        let source = fact
            .get("note_ref")
            .and_then(toml::Value::as_str)
            .unwrap_or("")
            .split('#')
            .next()
            .unwrap_or("");
        if references.get(source).is_some()
            && fact.get("authority_class").and_then(toml::Value::as_str) == Some("advisory")
            && fact
                .get("summary")
                .and_then(toml::Value::as_str)
                .is_some_and(|s| !s.trim().is_empty())
        {
            result["requests"].as_array_mut().unwrap().push(template(EDIT,
                json!({"source":source,"fact":id,"disposition":"retain","reason":"Assess the selected advisory fact's durable value and current disposition."})));
        }
    }
    let current_post = sources[MANIFEST].as_str().unwrap();
    let record = match retained(target, current_post) {
        Ok(record) => record,
        Err(e) if request.is_none() => {
            result["diagnostics"] =
                json!([{"code":"disposition-evidence-unavailable","message":e.to_string()}]);
            return Ok(result);
        }
        Err(e) => return Err(e),
    };
    if let Some(record) = record {
        let prepared = crate::attempt_store::prepare_commit(
            target.to_str().unwrap(),
            record["custody"].clone(),
            record["outcome"].clone(),
        )?;
        if crate::native_planning::read(
            &root,
            prepared["custody"]["committed"]["path"].as_str().unwrap(),
        )?
        .is_none()
        {
            result["recovery_requests"]
                .as_array_mut()
                .unwrap()
                .push(template(
                    RECOVER,
                    json!({"record_revision":digest(&record)?}),
                ));
        } else {
            let old = &record["invocation"]["arguments"]["binding"];
            let args = &record["invocation"]["arguments"]["request"]["arguments"];
            let source = args["source"].as_str().unwrap_or("");
            let same_source = sources
                .get(source)
                .is_some_and(|revision| old["sources"][source] == *revision);
            let current_receiver = args["disposition"] != "promote"
                || memory["receiving_admissions"]
                    .as_array()
                    .into_iter()
                    .flatten()
                    .any(|r| {
                        r["note"]["reference"] == source
                            && r.get("fact") == args.get("fact")
                            && r["receiving_admission"] == args["receiver"]
                    });
            if same_source
                && current_receiver
                && old["effective_policy_revision"] == binding["effective_policy_revision"]
                && old["capability_revision"] == binding["capability_revision"]
            {
                result["admitted_disposition"] = json!({"source":source,"fact":args["fact"],"status":args["disposition"],"reason":args["reason"],
                    "authority_effect":"advisory-disposition-only","completion_authority":false});
            } else {
                result["diagnostics"] = json!([{"code":"disposition-currentness-lost","source":source,
                    "message":"Retained disposition no longer has current source/policy/receiver admission; preserve and expose the advisory lesson."}]);
            }
        }
    }
    let Some(request) = request else {
        return Ok(result);
    };
    crate::prepare_request_value(
        json!({"request":request,"current_work":work,"capability_contract":contract}),
    )?;
    if request["source_revision"] != digest(&binding)? {
        return Err(err(
            "Memory source, current work, policy, receiver or capability changed; resolve a fresh disposition",
        ));
    }
    let args = &request["arguments"];
    let post;
    let operation = if request["request_kind"] == RECOVER {
        post = current_post.to_owned();
        let record =
            retained(target, &post)?.ok_or_else(|| err("Memory disposition attempt missing"))?;
        if args["record_revision"] != digest(&record)? {
            return Err(err("Memory disposition recovery is stale"));
        }
        let old = &record["invocation"]["arguments"]["binding"];
        if sources
            .as_object()
            .unwrap()
            .iter()
            .any(|(p, r)| p != MANIFEST && old["sources"][p] != *r)
            || old["effective_policy_revision"] != binding["effective_policy_revision"]
            || old["capability_revision"] != binding["capability_revision"]
            || old["receiving_admissions"] != binding["receiving_admissions"]
        {
            return Err(err("Memory disposition recovery dependencies changed"));
        }
        "memory.recover-disposition"
    } else if request["request_kind"] == EDIT {
        let source = args["source"].as_str().unwrap();
        if source == MANIFEST || !references.as_object().unwrap().contains_key(source) {
            return Err(err(
                "Memory disposition is outside the current selected sources",
            ));
        }
        if !result["requests"].as_array().unwrap().iter().any(|r| {
            r["arguments"]["source"] == source && r["arguments"].get("fact") == args.get("fact")
        }) {
            return Err(err(
                "Memory disposition does not name a current declared advisory subject",
            ));
        }
        if args["disposition"] == "promote" {
            if memory["selected_notes"]
                .as_array()
                .into_iter()
                .flatten()
                .any(|note| {
                    note["source"]["reference"] == source
                        && ["superseded_by", "contradicted_by"].iter().any(|key| {
                            note["metadata"][*key]
                                .as_array()
                                .is_some_and(|rows| !rows.is_empty())
                        })
                })
            {
                return Err(err(
                    "Memory source contradictions require reconciliation before promotion",
                ));
            }
            if !memory["receiving_admissions"]
                .as_array()
                .into_iter()
                .flatten()
                .any(|r| {
                    r["note"]["reference"] == source
                        && r.get("fact") == args.get("fact")
                        && r["receiving_admission"] == args["receiver"]
                })
            {
                return Err(err(
                    "Memory promotion requires current receiving-owner admission of the whole lesson",
                ));
            }
        } else if args.get("receiver").is_some() {
            return Err(err("Only promotion may nominate a receiving owner"));
        }
        let bytes = proposed(target, args, &binding)?;
        post = crate::native_intent::hash(&bytes);
        if post == current_post {
            result["status"] = json!("unchanged");
            return Ok(result);
        }
        let proposal = digest(
            &json!({"binding":binding,"work":work,"source":source,"fact":args["fact"],
            "disposition":args["disposition"],"reason":args["reason"],"receiver":args["receiver"],"post_revision":post}),
        )?;
        if args["answer"].is_null() {
            let mut answer = args.clone();
            answer["proposal_revision"] = json!(proposal);
            result["status"] = json!("human-decision-required");
            let field = args["fact"].as_str().map_or_else(
                || format!("notes.{source}.disposition"),
                |id| format!("durable_facts.{id}.disposition"),
            );
            let (table, key) = args["fact"]
                .as_str()
                .map_or(("notes", source), |id| ("durable_facts", id));
            let after: toml::Value =
                toml::from_str(std::str::from_utf8(&bytes).map_err(err)?).map_err(err)?;
            result["proposal"] = json!({"source":source,"fact":args["fact"],"disposition":args["disposition"],"reason":args["reason"],
                "receiver":args["receiver"],"affected_fields":[field],
                "before":manifest[table][key].get("disposition"),"after":after[table][key]["disposition"],"post_revision":post});
            result["contribution"]["decisions"] = json!([{"id":"memory-disposition-authorization",
                "question":"Authorize this exact Memory disposition? Retire means obsolete with no future value. Source authorship and all former material remain preserved; promotion needs independent receiving admission.",
                "response_request":{"request_kind":EDIT,"arguments":answer},
                "material":result["proposal"],
                "choices":[{"id":"authorize-disposition","label":"Authorize this exact disposition"},{"id":"defer","label":"Defer without mutation"}],
                "affects":["task","effect:memory-state"]}]);
            return Ok(result);
        }
        if args["proposal_revision"] != proposal {
            return Err(err("Memory answer is not bound to this exact disposition"));
        }
        if args["answer"] == "defer" {
            result["status"] = json!("deferred");
            return Ok(result);
        }
        "memory.dispose"
    } else {
        return Err(err("Unsupported Memory disposition request"));
    };
    result["status"] = json!("write-ready");
    result["contribution"]["actions"] = json!([{"operation_id":operation,"dependency_revision":digest(&json!([binding,request,post]))?,
        "arguments":{"target":target,"request":request,"binding":binding,"post_revision":post},"effects":[EFFECT],"source_requests":[request]}]);
    Ok(result)
}

pub(crate) fn apply_view(memory: &mut Value, disposition: Value) {
    for field in ["revision", "actions", "decisions"] {
        if let Some(value) = disposition["contribution"].get(field) {
            memory["contribution"][field] = value.clone();
        }
    }
    let admitted = &disposition["admitted_disposition"];
    if admitted["status"] == "retain" && admitted["fact"].is_null() {
        for note in memory["selected_notes"]
            .as_array_mut()
            .into_iter()
            .flatten()
        {
            if note["source"]["reference"] == admitted["source"] {
                note["disposition"] = admitted.clone();
            }
        }
        if memory["response"]["detail"]["source"]["reference"] == admitted["source"] {
            memory["response"]["detail"]["disposition"] = admitted.clone();
        }
        memory["contribution"]["facts"]["advisory_sources"] = memory["selected_notes"].clone();
    }
    if matches!(admitted["status"].as_str(), Some("retire" | "promote")) {
        if let Some(fact) = admitted["fact"].as_str() {
            let reference = format!("{MANIFEST}#durable_facts.{fact}");
            memory["diagnostics"]
                .as_array_mut()
                .unwrap()
                .retain(|row| row["source"] != reference);
            memory["suppressed_facts"] = json!([admitted]);
        } else {
            memory["selected_notes"]
                .as_array_mut()
                .unwrap()
                .retain(|note| note["source"]["reference"] != admitted["source"]);
            memory["requests"]
                .as_array_mut()
                .unwrap()
                .retain(|request| request["arguments"]["reference"] != admitted["source"]);
            memory["suppressed_notes"] = json!([admitted]);
        }
        memory["contribution"]["facts"]["advisory_sources"] = memory["selected_notes"].clone();
        memory["contribution"]["facts"]["diagnostics"] = memory["diagnostics"].clone();
    }
    memory["disposition"] = disposition;
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
    // Check every existing parent before even creating scratch directories.
    crate::native_planning::read(&root, lock_path)?;
    root.create_dir_all(".agentic-workspace/local/effects")
        .map_err(err)?;
    crate::native_planning::read(&root, lock_path)?;
    let lock = root
        .open_with(
            lock_path,
            OpenOptions::new().read(true).write(true).create(true),
        )
        .map_err(err)?
        .into_std();
    if lock.metadata().map_err(err)?.len() != 0 {
        return Err(err("unrecognized Memory lock preserved"));
    }
    lock.try_lock().map_err(err)?;
    revalidate()?;
    let args = &invocation["arguments"];
    let source = MANIFEST;
    let post = args["post_revision"].as_str().unwrap();
    if invocation["operation_id"] == "memory.recover-disposition" {
        let record = retained(target, post)?.ok_or_else(|| err("recovery evidence missing"))?;
        let admission = crate::attempt_store::admit(
            json!({"target":target,"decision":decision,"invocation":invocation}),
        )?;
        revalidate()?;
        if crate::native_intent::hash(&read(&root, source)?) != post {
            return Err(err("recovery source changed"));
        }
        crate::attempt_store::commit(
            json!({"target":target,"custody":record["custody"],"outcome":record["outcome"]}),
        )?;
        let out = json!({"status":"applied","effects":[EFFECT],"value":{"kind":"agentic-memory/disposition-result/v1","source":source,"post_revision":post,"material_written":false,"continuing_custody":false,"completion_authority":false}});
        let committed = crate::attempt_store::commit(
            json!({"target":target,"custody":admission["custody"],"outcome":out}),
        )?;
        return Ok(json!({"outcome":out,"custody":committed["custody"]}));
    }
    let bytes = proposed(target, &args["request"]["arguments"], &args["binding"])?;
    if crate::native_intent::hash(&bytes) != post {
        return Err(err("Memory postimage changed"));
    }
    let previous = retained(target, post)?;
    if let Some(record) = &previous {
        let committed = crate::attempt_store::prepare_commit(
            target.to_str().unwrap(),
            record["custody"].clone(),
            record["outcome"].clone(),
        )?;
        if crate::native_planning::read(
            &root,
            committed["custody"]["committed"]["path"].as_str().unwrap(),
        )?
        .is_some()
        {
            return Err(err(
                "this exact Memory write was already consumed; source preserved",
            ));
        }
    }
    let temporary = format!("{source}.{}.tmp", &digest(invocation)?[7..]);
    if previous.is_none() && crate::native_planning::read(&root, &temporary)?.is_some() {
        return Err(err("unowned Memory temporary preserved"));
    }
    if previous
        .as_ref()
        .is_some_and(|r| r["invocation"] != *invocation)
    {
        return Err(err("Memory evidence collision preserved"));
    }
    let admission = crate::attempt_store::admit(
        json!({"target":target,"decision":decision,"invocation":invocation,"custody":previous.as_ref().map(|r|&r["custody"])}),
    )?;
    let out = outcome(invocation);
    let record = json!({"invocation":invocation,"custody":admission["custody"],"outcome":out});
    let path = marker(post);
    if previous.is_none() {
        let mut f = root
            .open_with(&path, OpenOptions::new().write(true).create_new(true))
            .map_err(err)?;
        f.write_all(&serde_json::to_vec(&record).map_err(err)?)
            .map_err(err)?;
        f.sync_all().map_err(err)?;
    }
    observe("prepared")?;
    // Exclusive temporary creation preserves unknown prior work after a crash.
    if let Some(existing) = crate::native_planning::read(&root, &temporary)? {
        if existing != bytes {
            return Err(err("unknown Memory temporary preserved"));
        }
    } else {
        let mut f = root
            .open_with(&temporary, OpenOptions::new().write(true).create_new(true))
            .map_err(err)?;
        f.set_permissions(root.metadata(source).map_err(err)?.permissions())
            .map_err(err)?;
        f.write_all(&bytes).map_err(err)?;
        f.sync_all().map_err(err)?;
    }
    revalidate()?;
    if revisions(target, &args["binding"]["sources"])? != args["binding"]["sources"]
        || crate::native_config::view(target)?["revision"]
            != args["binding"]["effective_policy_revision"]
    {
        return Err(err("Memory sources changed before publication"));
    }
    root.rename(&temporary, &root, source).map_err(err)?;
    observe("published")?;
    let committed = crate::attempt_store::commit(
        json!({"target":target,"custody":admission["custody"],"outcome":out}),
    )?;
    Ok(json!({"outcome":out,"custody":committed["custody"]}))
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn memory_disposition_recovers_interruption_and_rejects_policy_drift() {
        for stage in ["prepared", "published", "drift"] {
            let target = std::env::temp_dir().join(format!(
                "aw-memory-write-{}-{}",
                std::process::id(),
                std::time::SystemTime::now()
                    .duration_since(std::time::UNIX_EPOCH)
                    .unwrap()
                    .as_nanos()
            ));
            let reference = ".agentic-workspace/memory/repo/decisions/former.md";
            std::fs::create_dir_all(target.join(reference).parent().unwrap()).unwrap();
            std::fs::write(target.join(reference), "A useful former lesson.\n").unwrap();
            let before = format!("version=1\n[notes.\"{reference}\"]\nroutes_from=['src/**']\n");
            std::fs::write(target.join(MANIFEST), &before).unwrap();
            let context = json!({"target":target,"task":"Fixture exact Memory disposition","changed":["src/core.rs"]});
            let resolve = |request: Option<Value>| {
                let mut c = context.clone();
                if let Some(request) = request {
                    c["request"] = request;
                }
                crate::native_public::start(c).unwrap()
            };
            let mut request = resolve(None)["memory"]["disposition"]["requests"][0].clone();
            request["arguments"]["reason"] =
                json!("Fixture human retains this useful advisory source.");
            let mut answer =
                resolve(Some(request))["decision_packet"]["decision_request"]["response_request"]
                    .clone();
            answer["arguments"]["answer"] = json!("authorize-disposition");
            let ready = resolve(Some(answer));
            let action = &ready["decision_packet"]["primary_action"];
            assert_eq!(action["operation_id"], "memory.dispose");
            let failure = execute_checked(
                &target,
                &ready["decision_packet"],
                action,
                &mut || Ok(()),
                &mut |point| {
                    if stage == "drift" && point == "prepared" {
                        std::fs::write(
                            target.join(".agentic-workspace/config.local.toml"),
                            "schema_version=1\n# Changed human source\n",
                        )
                        .unwrap();
                    } else if point == stage {
                        return Err(err("simulated interruption"));
                    }
                    Ok(())
                },
            )
            .unwrap_err();
            if stage == "drift" {
                assert!(failure.to_string().contains("sources changed"));
                assert_eq!(
                    std::fs::read_to_string(target.join(MANIFEST)).unwrap(),
                    before
                );
            } else {
                assert!(failure.to_string().contains("simulated"));
                let mut invocation = context.clone();
                if stage == "prepared" {
                    assert_eq!(
                        std::fs::read_to_string(target.join(MANIFEST)).unwrap(),
                        before
                    );
                    invocation["invocation"] = action.clone();
                } else {
                    let request =
                        resolve(None)["memory"]["disposition"]["recovery_requests"][0].clone();
                    invocation["invocation"] =
                        resolve(Some(request))["decision_packet"]["primary_action"].clone();
                    assert_eq!(
                        invocation["invocation"]["operation_id"],
                        "memory.recover-disposition"
                    );
                }
                crate::native_public::invoke_checked(invocation).unwrap();
                let current = resolve(None);
                assert!(
                    current["memory"]["disposition"]["recovery_requests"]
                        .as_array()
                        .unwrap()
                        .is_empty()
                );
                assert_eq!(
                    current["memory"]["disposition"]["admitted_disposition"]["status"],
                    "retain"
                );
                assert_eq!(
                    current["memory"]["selected_notes"]
                        .as_array()
                        .unwrap()
                        .len(),
                    1
                );
            }
            std::fs::remove_dir_all(&target).unwrap();
        }
    }
}
