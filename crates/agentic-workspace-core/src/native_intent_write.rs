//! Exact retained interpretation publication after explicit semantic judgment.
//! Governing sources remain human authority; observation never implies alignment.
use crate::{CoreError, digest};
use cap_std::{
    ambient_authority,
    fs::{Dir, OpenOptions},
};
use serde_json::{Value, json};
use std::{io::Write, path::Path};
pub(crate) const EDIT: &str = "system-intent/edit-source/v1";
const RECOVER: &str = "system-intent/recover-source/v1";
pub(crate) const WRITE: &str = "system-intent.write";
pub(crate) const RECOVERY: &str = "system-intent.recover-write";
const EFFECT: &str = "system-intent-source";
fn err(e: impl ToString) -> CoreError {
    CoreError::new(e.to_string())
}
fn marker(source: &str, post: &str) -> Result<String, CoreError> {
    Ok(format!(
        ".agentic-workspace/local/effects/intent-{}.prepared.json",
        &digest(&json!([source, post]))?[7..]
    ))
}
fn outcome(i: &Value) -> Value {
    json!({"status":"applied","effects":[EFFECT],"value":{"kind":"agentic-workspace/intent-write-result/v1","source":json!(MIRROR),"post_revision":i["arguments"]["post_revision"],"continuing_custody":false,"completion_authority":false}})
}
fn held(target: &Path, source: &str, post: &str) -> Result<Option<Value>, CoreError> {
    let root = Dir::open_ambient_dir(target, ambient_authority()).map_err(err)?;
    let Some(bytes) = crate::native_planning::read(&root, &marker(source, post)?)? else {
        return Ok(None);
    };
    let record: Value = serde_json::from_slice(&bytes).map_err(err)?;
    let evidence = serde_json::from_value(record["custody"]["attempt"].clone()).map_err(err)?;
    let attempt = crate::attempt_store::read_source(target.to_str().unwrap(), &evidence)?;
    let i = &record["invocation"];
    if attempt["invocation"] != *i
        || i["source_owner"] != "system-intent"
        || i["operation_id"] != WRITE
        || i["arguments"]["target"] != target.to_str().unwrap()
        || source != MIRROR
        || i["arguments"]["post_revision"] != post
        || record["outcome"] != outcome(i)
    {
        return Err(err(
            "intent publication lacks exact owner attempt custody; preserve source",
        ));
    }
    Ok(Some(record))
}
pub(crate) fn admitted(target: &Path, source: &str, post: &str) -> Result<bool, CoreError> {
    let Some(record) = held(target, source, post)? else {
        return Ok(false);
    };
    let prepared = crate::attempt_store::prepare_commit(
        target.to_str().unwrap(),
        record["custody"].clone(),
        record["outcome"].clone(),
    )?;
    let root = Dir::open_ambient_dir(target, ambient_authority()).map_err(err)?;
    if crate::native_planning::read(
        &root,
        prepared["custody"]["committed"]["path"].as_str().unwrap(),
    )?
    .is_none()
    {
        return Ok(false);
    }
    crate::attempt_store::inspect_committed(target.to_str().unwrap(), prepared["custody"].clone())?;
    Ok(true)
}
pub(crate) fn extend_contract(contract: &mut Value) -> Result<(), CoreError> {
    let owner = &mut contract["owners"][0];
    owner["domains"] = json!(["system-intent"]);
    owner["effects"] = json!([{"id":EFFECT,"domain":"system-intent"}]);
    owner["requests"].as_array_mut().unwrap().extend([
        json!({"kind":EDIT,"result_kind":"agentic-workspace/intent-write-proposal/v1","input_schema":{"$schema":"https://json-schema.org/draft/2020-12/schema","type":"object","additionalProperties":false,"required":["content","judgment","reason"],"properties":{"content":{"type":"string","maxLength":65536},"judgment":{"enum":["faithful","revised","unresolved"]},"reason":{"type":"string","minLength":1,"maxLength":4096},"proposal_revision":{"type":"string"},"answer":{"enum":["authorize-write","defer"]}}}}),
        json!({"kind":RECOVER,"result_kind":"agentic-workspace/intent-write-result/v1","input_schema":{"$schema":"https://json-schema.org/draft/2020-12/schema","type":"object","additionalProperties":false,"required":["post_revision"],"properties":{"post_revision":{"type":"string"}}}})
    ]);
    owner["operations"] = json!([WRITE,RECOVERY].iter().map(|op| json!({"id":op,"semantic_revision":"intent-publication/v1","input_schema":{"$schema":"https://json-schema.org/draft/2020-12/schema","type":"object","additionalProperties":false,"required":["target","request","binding","post_revision"],"properties":{"target":{"type":"string"},"request":{"type":"object"},"binding":{"type":"object"},"post_revision":{"type":"string"}}},"result_kind":"agentic-workspace/intent-write-result/v1","effects":[EFFECT],"reads":["system-intent"]})).collect::<Vec<_>>());
    owner["revision"] = json!(digest(&json!([owner["requests"], owner["operations"]]))?);
    contract["restriction_authorities"][0]["affects"]
        .as_array_mut()
        .unwrap()
        .push(json!("effect:system-intent-source"));
    contract["revision"] = json!("pending");
    contract["revision"] = json!(digest(contract)?);
    Ok(())
}
const MIRROR: &str = crate::native_intent::MIRROR;
fn source(target: &Path, path: &str) -> Result<Option<Vec<u8>>, CoreError> {
    if path != MIRROR {
        return Err(err("intent destination is fixed by its owner"));
    }
    let root = Dir::open_ambient_dir(target, ambient_authority()).map_err(err)?;
    crate::native_intent::bytes(&root, path)
}
fn postimage(args: &Value) -> Result<Vec<u8>, CoreError> {
    let text = args["content"]
        .as_str()
        .ok_or_else(|| err("intent content missing"))?;
    if text.len() > 65536
        || args["reason"].as_str().is_none_or(|s| s.trim().is_empty())
        || !["faithful", "revised"].contains(&args["judgment"].as_str().unwrap_or(""))
    {
        return Err(err(
            "intent requires bounded content and explicit resolved semantic judgment",
        ));
    }
    let value: toml::Value = toml::from_str(text).map_err(err)?;
    if value.get("kind").and_then(toml::Value::as_str) != Some("agentic-workspace/system-intent/v1")
        || value
            .get("schema_version")
            .and_then(toml::Value::as_integer)
            != Some(1)
        || value.get("needs_review").and_then(toml::Value::as_bool) != Some(false)
        || value
            .get("summary")
            .and_then(toml::Value::as_str)
            .is_none_or(|s| s.trim().is_empty())
    {
        return Err(err(
            "intent postimage must be an explicitly reviewed retained interpretation",
        ));
    }
    Ok(text.as_bytes().to_vec())
}
fn proposed_content(target: &Path, config: &Value, args: &Value) -> Result<Vec<u8>, CoreError> {
    let bytes = postimage(args)?;
    let value: toml::Value =
        toml::from_str(std::str::from_utf8(&bytes).map_err(err)?).map_err(err)?;
    let value = serde_json::to_value(value).map_err(err)?;
    let root = Dir::open_ambient_dir(target, ambient_authority()).map_err(err)?;
    if !crate::native_intent::stale_references(&root, &config["system_intent"], &value).is_empty() {
        return Err(err(
            "intent postimage source records do not match exact current governing sources",
        ));
    }
    if config["system_intent"]["sources"]
        .as_array()
        .is_none_or(Vec::is_empty)
    {
        return Err(err(
            "intent reconciliation requires declared governing sources",
        ));
    }
    Ok(bytes)
}
pub(crate) fn view(
    target: &Path,
    work: &Value,
    config: &Value,
    intent: &mut Value,
    contract: &Value,
    request: Option<&Value>,
) -> Result<(), CoreError> {
    let owner = contract["owners"]
        .as_array()
        .unwrap()
        .iter()
        .find(|o| o["owner"] == "system-intent")
        .unwrap();
    let binding = json!({"sources":intent["sources"],"declaration":intent["declaration"],"policy":config["revision"],"capability":contract["revision"]});
    let revision = intent["revision"].clone();
    let template = |kind: &str, args: Value| json!({"kind":"agentic-workspace/public-request/v1","id":kind,"owner":"system-intent","owner_revision":owner["revision"],"source_revision":revision,"capability_revision":contract["revision"],"task_identity":work,"request_kind":kind,"arguments":args});
    let mut write = json!({"status":"not-requested","requests":[],"recovery_requests":[]});
    // Authoring guidance belongs to selected reconciliation, not quiet reads.
    if request.is_some() || !intent["gaps"].as_array().unwrap().is_empty() {
        write["boundary"] = json!(
            "Read every declared source and retained interpretation. Supply a complete reviewable interpretation and exact source_records after semantic judgment; an exact accepted proposal authorizes only this mirror, never governing intent or Planning completion."
        );
    }
    if !intent["gaps"].as_array().unwrap().is_empty() {
        write["requests"] = json!([template(
            EDIT,
            json!({"content":"","judgment":"unresolved","reason":"Semantic review required"})
        )]);
    }
    let before = source(target, MIRROR)?;
    if let Some(bytes) = &before {
        let post = crate::native_intent::hash(bytes);
        if held(target, MIRROR, &post)?.is_some() && !admitted(target, MIRROR, &post)? {
            write["recovery_requests"] = json!([template(RECOVER, json!({"post_revision":post}))]);
        }
    }
    if let Some(request) = request {
        crate::prepare_request_value(
            json!({"request":request,"current_work":work,"capability_contract":contract}),
        )?;
        if request["source_revision"] != revision {
            return Err(err(
                "intent sources or retained interpretation changed; reconsider judgment",
            ));
        }
        let args = &request["arguments"];
        let mut bound = binding.clone();
        bound["before_revision"] = before
            .as_ref()
            .map(|b| json!(crate::native_intent::hash(b)))
            .unwrap_or(Value::Null);
        let (op, post) = if request["request_kind"] == RECOVER {
            let post = args["post_revision"].as_str().unwrap();
            let record = held(target, MIRROR, post)?
                .ok_or_else(|| err("intent recovery attempt missing"))?;
            let original = &record["invocation"]["arguments"];
            if bound["before_revision"] != post
                || original["binding"]["policy"] != config["revision"]
            {
                return Err(err("intent recovery source or policy changed; preserve"));
            }
            proposed_content(target, config, &original["request"]["arguments"])?;
            // The original exact governing bytes, not normalized hashes alone, bind recovery.
            let original_sources = original["binding"]["sources"].as_array().unwrap();
            let current_sources = binding["sources"].as_array().unwrap();
            if original_sources
                .iter()
                .filter(|s| s["reference"] != MIRROR)
                .ne(current_sources.iter().filter(|s| s["reference"] != MIRROR))
            {
                return Err(err("intent governing sources changed before recovery"));
            }
            (RECOVERY, post.to_owned())
        } else {
            if request["request_kind"] != EDIT {
                return Err(err("unsupported intent authoring request"));
            }
            if args["judgment"] == "unresolved" {
                write["status"] = json!("semantic-judgment-required");
                intent["reconciliation"] = write;
                return Ok(());
            }
            let bytes = proposed_content(target, config, args)?;
            let post = crate::native_intent::hash(&bytes);
            let proposal = json!({"binding":bound,"source":MIRROR,"before":before.as_ref().map(|b|String::from_utf8_lossy(b).into_owned()),"postimage":args["content"],"post_revision":post,"judgment":args["judgment"],"reason":args["reason"],"authority":"exact-bounded-owner-answer"});
            let pr = digest(&proposal)?;
            write["proposal"] = proposal;
            if args["answer"].is_null() {
                write["status"] = json!("owner-decision-required");
                let mut answer = args.clone();
                answer["proposal_revision"] = json!(pr);
                intent["contribution"]["decisions"] = json!([{"id":"intent-write-authorization","question":"Accept this semantic reconciliation and authorize this exact retained interpretation?","material":write["proposal"],"response_request":{"request_kind":EDIT,"arguments":answer},"choices":[{"id":"authorize-write","label":"Accept this exact reconciliation"},{"id":"defer","label":"Preserve unresolved interpretation"}],"affects":["effect:system-intent-source"]}]);
                intent["reconciliation"] = write;
                return Ok(());
            }
            if args["proposal_revision"] != pr {
                return Err(err("intent answer differs from exact semantic proposal"));
            }
            if args["answer"] == "defer" {
                write["status"] = json!("not-retained");
                intent["reconciliation"] = write;
                return Ok(());
            }
            (WRITE, post)
        };
        write["status"] = json!("write-ready");
        intent["contribution"]["actions"] = json!([{"operation_id":op,"dependency_revision":digest(&json!([bound,request,post]))?,"arguments":{"target":target,"request":request,"binding":bound,"post_revision":post},"effects":[EFFECT],"source_requests":[request]}]);
    }
    intent["reconciliation"] = write;
    Ok(())
}
pub(crate) fn write_scope(action: &Value) -> Result<Vec<String>, CoreError> {
    let source = MIRROR;
    let post = action["arguments"]["post_revision"].as_str().unwrap();
    let mut paths =
        crate::attempt_store::write_paths(&json!({"idempotency_key":action["logical_effect_id"]}))?;
    paths.extend([
        source.to_owned(),
        format!("{source}.*.tmp"),
        marker(source, post)?,
        ".agentic-workspace/local/effects/system-intent.lock".into(),
    ]);
    Ok(paths)
}
pub(crate) fn execute(
    target: &Path,
    decision: &Value,
    i: &Value,
    mut revalidate: impl FnMut() -> Result<(), CoreError>,
) -> Result<Value, CoreError> {
    if serde_json::to_vec(i).map_err(err)?.len() > 100_000 {
        return Err(err(
            "intent publication exceeds bounded recovery size; preserve source",
        ));
    }
    let root = Dir::open_ambient_dir(target, ambient_authority()).map_err(err)?;
    crate::native_planning::read(&root, ".agentic-workspace/local/effects/system-intent.lock")?;
    root.create_dir_all(".agentic-workspace/local/effects")
        .map_err(err)?;
    let lock = root
        .open_with(
            ".agentic-workspace/local/effects/system-intent.lock",
            OpenOptions::new().read(true).write(true).create(true),
        )
        .map_err(err)?
        .into_std();
    if lock.metadata().map_err(err)?.len() != 0 {
        return Err(err("unknown intent lock preserved"));
    }
    lock.try_lock().map_err(err)?;
    revalidate()?;
    let args = &i["arguments"];
    let path = MIRROR;
    let post = args["post_revision"].as_str().unwrap();
    if i["operation_id"] == RECOVERY {
        let record = held(target, path, post)?.ok_or_else(|| err("intent recovery missing"))?;
        let admission = crate::attempt_store::admit(
            json!({"target":target,"decision":decision,"invocation":i}),
        )?;
        revalidate()?;
        crate::attempt_store::commit(
            json!({"target":target,"custody":record["custody"],"outcome":record["outcome"]}),
        )?;
        let out = outcome(i);
        let committed = crate::attempt_store::commit(
            json!({"target":target,"custody":admission["custody"],"outcome":out}),
        )?;
        return Ok(json!({"outcome":out,"custody":committed["custody"]}));
    }
    let bytes = postimage(&args["request"]["arguments"])?;
    let previous = held(target, path, post)?;
    if admitted(target, path, post)? {
        return Err(err("exact intent write already consumed"));
    }
    if previous.as_ref().is_some_and(|r| r["invocation"] != *i) {
        return Err(err("intent attempt collision preserved"));
    }
    let temp = format!("{path}.{}.tmp", &digest(i)?[7..]);
    if previous.is_none() && crate::native_planning::read(&root, &temp)?.is_some() {
        return Err(err("unknown intent temporary preserved"));
    }
    let admission = crate::attempt_store::admit(
        json!({"target":target,"decision":decision,"invocation":i,"custody":previous.as_ref().map(|r|&r["custody"])}),
    )?;
    let out = outcome(i);
    if previous.is_none() {
        let mut f = root
            .open_with(
                marker(path, post)?,
                OpenOptions::new().write(true).create_new(true),
            )
            .map_err(err)?;
        f.write_all(
            &serde_json::to_vec(
                &json!({"invocation":i,"custody":admission["custody"],"outcome":out}),
            )
            .map_err(err)?,
        )
        .map_err(err)?;
        f.sync_all().map_err(err)?;
    }
    source(target, path)?;
    root.create_dir_all(Path::new(path).parent().unwrap())
        .map_err(err)?;
    if let Some(existing) = crate::native_planning::read(&root, &temp)? {
        if existing != bytes {
            return Err(err("unknown intent temporary preserved"));
        }
    } else {
        let mut f = root
            .open_with(&temp, OpenOptions::new().write(true).create_new(true))
            .map_err(err)?;
        if let Ok(m) = root.metadata(path) {
            f.set_permissions(m.permissions()).map_err(err)?;
        }
        f.write_all(&bytes).map_err(err)?;
        f.sync_all().map_err(err)?;
    }
    revalidate()?;
    let current = source(target, path)?
        .map(|b| json!(crate::native_intent::hash(&b)))
        .unwrap_or(Value::Null);
    if current != args["binding"]["before_revision"] {
        return Err(err("intent source changed at publication barrier"));
    }
    if current.is_null() {
        root.hard_link(&temp, &root, path).map_err(err)?;
        root.remove_file(&temp).map_err(err)?;
    } else {
        root.rename(&temp, &root, path).map_err(err)?;
    }
    let committed = crate::attempt_store::commit(
        json!({"target":target,"custody":admission["custody"],"outcome":out}),
    )?;
    Ok(json!({"outcome":out,"custody":committed["custody"],"post_effect_changed_paths":[path]}))
}
