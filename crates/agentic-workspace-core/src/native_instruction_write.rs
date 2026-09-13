//! Instruction-owned exact Markdown publication. Correction nominates meaning/scope;
//! the current human answer authorizes one source, never a general write grant.
use crate::{CoreError, digest};
use cap_std::{
    ambient_authority,
    fs::{Dir, OpenOptions},
};
use serde_json::{Value, json};
use std::{io::Write, path::Path};
pub(crate) const EDIT: &str = "instructions/edit-source/v1";
const RECOVER: &str = "instructions/recover-source/v1";
pub(crate) const WRITE: &str = "instructions.write";
pub(crate) const RECOVERY: &str = "instructions.recover-write";
const EFFECT: &str = "instruction-source";
fn err(e: impl ToString) -> CoreError {
    CoreError::new(e.to_string())
}
fn marker(source: &str, post: &str) -> Result<String, CoreError> {
    Ok(format!(
        ".agentic-workspace/local/effects/instruction-{}.prepared.json",
        &digest(&json!([source, post]))?[7..]
    ))
}
fn outcome(i: &Value) -> Value {
    json!({"status":"applied","effects":[EFFECT],"value":{"kind":"agentic-workspace/instruction-write-result/v1","source":i["arguments"]["request"]["arguments"]["source"],"post_revision":i["arguments"]["post_revision"],"continuing_custody":false,"completion_authority":false}})
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
        || i["source_owner"] != "scoped-instructions"
        || i["operation_id"] != WRITE
        || i["arguments"]["target"] != target.to_str().unwrap()
        || i["arguments"]["request"]["arguments"]["source"] != source
        || i["arguments"]["post_revision"] != post
        || record["outcome"] != outcome(i)
    {
        return Err(err(
            "instruction publication lacks exact owner attempt custody; preserve source",
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
    owner["domains"] = json!(["scoped-instructions"]);
    owner["effects"] = json!([{"id":EFFECT,"domain":"scoped-instructions"}]);
    owner["requests"] = json!([
        {"kind":EDIT,"result_kind":"agentic-workspace/instruction-write-proposal/v1","input_schema":{"$schema":"https://json-schema.org/draft/2020-12/schema","type":"object","additionalProperties":false,"required":["source","content"],"properties":{"source":{"type":"string","maxLength":256},"content":{"type":"string","maxLength":65536},"proposal_revision":{"type":"string"},"answer":{"enum":["authorize-write","defer"]}}}},
        {"kind":RECOVER,"result_kind":"agentic-workspace/instruction-write-result/v1","input_schema":{"$schema":"https://json-schema.org/draft/2020-12/schema","type":"object","additionalProperties":false,"required":["source","post_revision"],"properties":{"source":{"type":"string"},"post_revision":{"type":"string"}}}}
    ]);
    owner["operations"] = json!([WRITE,RECOVERY].iter().map(|op| json!({"id":op,"semantic_revision":"instruction-publication/v1","input_schema":{"$schema":"https://json-schema.org/draft/2020-12/schema","type":"object","additionalProperties":false,"required":["target","request","binding","post_revision"],"properties":{"target":{"type":"string"},"request":{"type":"object"},"binding":{"type":"object"},"post_revision":{"type":"string"}}},"result_kind":"agentic-workspace/instruction-write-result/v1","effects":[EFFECT],"reads":["scoped-instructions"]})).collect::<Vec<_>>());
    owner["revision"] = json!(digest(&json!([owner["requests"], owner["operations"]]))?);
    contract["restriction_authorities"][0]["affects"]
        .as_array_mut()
        .unwrap()
        .push(json!("effect:instruction-source"));
    contract["revision"] = json!("pending");
    contract["revision"] = json!(digest(contract)?);
    Ok(())
}
fn source(target: &Path, path: &str) -> Result<Option<Vec<u8>>, CoreError> {
    crate::decision_source::relative(path)?;
    let scope = crate::instruction_source::source_scope(path)
        .ok_or_else(|| err("select an exact canonical instruction Markdown source"))?;
    if scope == "machine-local" {
        let output = std::process::Command::new("git")
            .arg("-C")
            .arg(target)
            .args(["check-ignore", "--no-index", "-q", "--", path])
            .env_remove("GIT_LITERAL_PATHSPECS")
            .output()
            .map_err(err)?;
        let tracked = std::process::Command::new("git")
            .arg("-C")
            .arg(target)
            .args(["ls-files", "--", path])
            .env("GIT_LITERAL_PATHSPECS", "1")
            .output()
            .map_err(err)?;
        if !output.status.success() || !tracked.status.success() || !tracked.stdout.is_empty() {
            return Err(err(
                "local instruction destination must be gitignored and untracked; preserve repository ignore policy",
            ));
        }
    }
    let root = Dir::open_ambient_dir(target, ambient_authority()).map_err(err)?;
    crate::native_planning::read(&root, path)
}
fn postimage(args: &Value) -> Result<Vec<u8>, CoreError> {
    let bytes = args["content"]
        .as_str()
        .ok_or_else(|| err("instruction content missing"))?
        .as_bytes();
    if bytes.is_empty()
        || bytes.len() > 65536
        || crate::instruction_source::parsed(bytes, false)["valid"] != true
        || !crate::instruction_source::parsed(bytes, false)["metadata"]["routes"]
            .as_array()
            .unwrap()
            .is_empty()
    {
        return Err(err(
            "instruction postimage must satisfy the bounded shared Markdown contract",
        ));
    }
    Ok(bytes.to_vec())
}
pub(crate) fn view(
    target: &Path,
    work: &Value,
    config: &Value,
    instructions: &mut Value,
    contract: &Value,
    request: Option<&Value>,
) -> Result<(), CoreError> {
    let owner = contract["owners"]
        .as_array()
        .unwrap()
        .iter()
        .find(|o| o["owner"] == "scoped-instructions")
        .unwrap();
    let binding = json!({"sources":instructions["sources"].as_array().unwrap().iter().map(|s|s["source"].clone()).collect::<Vec<_>>(),"policy":config["revision"],"capability":contract["revision"]});
    let revision = digest(&binding)?;
    instructions["contribution"]["revision"] = json!(revision);
    let template = |kind: &str, args: Value| json!({"kind":"agentic-workspace/public-request/v1","id":kind,"owner":"scoped-instructions","owner_revision":owner["revision"],"source_revision":revision,"capability_revision":contract["revision"],"task_identity":work,"request_kind":kind,"arguments":args});
    let mut write = json!({"status":"not-requested","requests":[template(EDIT,json!({"source":".agentic-workspace/instructions/behavior.md","content":""})),template(EDIT,json!({"source":".agentic-workspace/local/instructions/behavior.md","content":""}))],"recovery_requests":[]});
    for row in instructions["sources"].as_array().unwrap() {
        let path = row["source"]["reference"].as_str().unwrap();
        let post = row["source"]["revision"].as_str().unwrap();
        if held(target, path, post)?.is_some() && !admitted(target, path, post)? {
            write["recovery_requests"]
                .as_array_mut()
                .unwrap()
                .push(template(
                    RECOVER,
                    json!({"source":path,"post_revision":post}),
                ));
        }
    }
    if let Some(request) = request {
        crate::prepare_request_value(
            json!({"request":request,"current_work":work,"capability_contract":contract}),
        )?;
        if request["source_revision"] != revision {
            return Err(err(
                "instruction source/policy changed; resolve a fresh request",
            ));
        }
        let args = &request["arguments"];
        let path = args["source"].as_str().unwrap();
        let before = source(target, path)?;
        let mut bound = binding.clone();
        bound["before_revision"] = before
            .as_ref()
            .map(|b| json!(crate::decision_source::hash(b)))
            .unwrap_or(Value::Null);
        let (op, post) = if request["request_kind"] == RECOVER {
            let post = args["post_revision"].as_str().unwrap();
            let record = held(target, path, post)?
                .ok_or_else(|| err("instruction recovery attempt missing"))?;
            if before
                .as_ref()
                .map(|b| crate::decision_source::hash(b))
                .as_deref()
                != Some(post)
                || record["invocation"]["arguments"]["binding"]["policy"] != config["revision"]
            {
                return Err(err(
                    "instruction recovery source or policy changed; preserve",
                ));
            }
            (RECOVERY, post.to_owned())
        } else {
            let bytes = postimage(args)?;
            let post = crate::decision_source::hash(&bytes);
            let proposal = json!({"binding":bound,"source":path,"scope":crate::instruction_source::source_scope(path),"before":before.as_ref().map(|b|String::from_utf8_lossy(b).into_owned()),"postimage":args["content"],"post_revision":post,"authority":"exact-bounded-human-answer"});
            let pr = digest(&proposal)?;
            write["proposal"] = proposal;
            if before.as_ref() == Some(&bytes) && admitted(target, path, &post)? {
                write["status"] = json!("already-current");
                instructions["authoring"] = write;
                return Ok(());
            }
            if args["answer"].is_null() {
                if crate::native_decision_authority::delegated(
                    config,
                    "scoped-instructions",
                    &[path.to_owned()],
                )
                .is_some()
                {
                    let mut authorized = request.clone();
                    authorized["arguments"]["answer"] = json!("authorize-write");
                    authorized["arguments"]["proposal_revision"] = json!(pr);
                    return self::view(
                        target,
                        work,
                        config,
                        instructions,
                        contract,
                        Some(&authorized),
                    );
                }

                write["status"] = json!("human-decision-required");
                let mut answer = args.clone();
                answer["proposal_revision"] = json!(pr);
                instructions["contribution"]["decisions"] = json!([{"id":"instruction-write-authorization","question":"Retain this exact instruction in the selected repository scope?","material":write["proposal"],"response_request":{"request_kind":EDIT,"arguments":answer},"choices":[{"id":"authorize-write","label":"Authorize this exact instruction"},{"id":"defer","label":"Do not retain"}],"affects":["effect:instruction-source"]}]);
                instructions["authoring"] = write;
                return Ok(());
            }
            if args["proposal_revision"] != pr {
                return Err(err(
                    "instruction answer differs from the exact proposed source",
                ));
            }
            if args["answer"] == "defer" {
                write["status"] = json!("not-retained");
                instructions["authoring"] = write;
                return Ok(());
            }
            (WRITE, post)
        };
        if op == WRITE {
            let repaired = format!("instruction:{path}:source-unresolved");
            instructions["contribution"]["blockers"]
                .as_array_mut()
                .unwrap()
                .retain(|b| b["code"] != repaired);
        }
        write["status"] = json!("write-ready");
        instructions["contribution"]["actions"] = json!([{"operation_id":op,"dependency_revision":digest(&json!([bound,request,post]))?,"arguments":{"target":target,"request":request,"binding":bound,"post_revision":post},"effects":[EFFECT],"source_requests":[request]}]);
    }
    instructions["authoring"] = write;
    Ok(())
}
pub(crate) fn write_scope(action: &Value) -> Result<Vec<String>, CoreError> {
    let source = action["arguments"]["request"]["arguments"]["source"]
        .as_str()
        .ok_or_else(|| err("instruction destination missing"))?;
    let post = action["arguments"]["post_revision"].as_str().unwrap();
    let mut paths =
        crate::attempt_store::write_paths(&json!({"idempotency_key":action["logical_effect_id"]}))?;
    paths.extend([
        source.to_owned(),
        format!("{source}.*.tmp"),
        marker(source, post)?,
        ".agentic-workspace/local/effects/instructions.lock".into(),
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
            "instruction publication exceeds bounded recovery size; preserve source",
        ));
    }
    let root = Dir::open_ambient_dir(target, ambient_authority()).map_err(err)?;
    crate::native_planning::read(&root, ".agentic-workspace/local/effects/instructions.lock")?;
    root.create_dir_all(".agentic-workspace/local/effects")
        .map_err(err)?;
    let lock = root
        .open_with(
            ".agentic-workspace/local/effects/instructions.lock",
            OpenOptions::new().read(true).write(true).create(true),
        )
        .map_err(err)?
        .into_std();
    if lock.metadata().map_err(err)?.len() != 0 {
        return Err(err("unknown instruction lock preserved"));
    }
    lock.try_lock().map_err(err)?;
    revalidate()?;
    let args = &i["arguments"];
    let path = args["request"]["arguments"]["source"].as_str().unwrap();
    let post = args["post_revision"].as_str().unwrap();
    if i["operation_id"] == RECOVERY {
        let record =
            held(target, path, post)?.ok_or_else(|| err("instruction recovery missing"))?;
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
        return Err(err("exact instruction write already consumed"));
    }
    if previous.as_ref().is_some_and(|r| r["invocation"] != *i) {
        return Err(err("instruction attempt collision preserved"));
    }
    let temp = format!("{path}.{}.tmp", &digest(i)?[7..]);
    if previous.is_none() && crate::native_planning::read(&root, &temp)?.is_some() {
        return Err(err("unknown instruction temporary preserved"));
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
            return Err(err("unknown instruction temporary preserved"));
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
        .map(|b| json!(crate::decision_source::hash(&b)))
        .unwrap_or(Value::Null);
    if current != args["binding"]["before_revision"] {
        return Err(err("instruction source changed at publication barrier"));
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
