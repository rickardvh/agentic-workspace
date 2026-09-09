//! Exact bounded-human-answer decisions in the existing Memory fallback archive.
//! Publication custody and deciding authority are checked separately. This is
//! not identity authentication, a trust-pin writer, or generic archive custody.
use crate::{CoreError, digest};
use cap_std::{
    ambient_authority,
    fs::{Dir, OpenOptions},
};
use serde_json::{Value, json};
use std::{io::Write, path::Path};

pub(crate) const CAPTURE: &str = "memory/capture-decision/v1";
pub(crate) const RECOVER: &str = "memory/recover-decision/v1";
const SEMANTICS: &str = "memory-bounded-human-decision-v1";
const EFFECT: &str = "memory-state";
const DEFAULT_ARCHIVE: &str = ".agentic-workspace/memory/repo/decisions";
const MANIFEST: &str = ".agentic-workspace/memory/repo/manifest.toml";
fn err(e: impl ToString) -> CoreError {
    CoreError::new(e.to_string())
}
fn read(root: &Dir, path: &str) -> Result<Option<Vec<u8>>, CoreError> {
    crate::native_planning::read(root, path)
}
fn archive(config: &Value) -> Result<String, CoreError> {
    let path = config["admissions"]["decision_record_fallback"]["archive"]
        .as_str()
        .unwrap_or(DEFAULT_ARCHIVE);
    crate::decision_source::relative(path)?;
    if !path.starts_with(".agentic-workspace/memory/repo/") {
        return Err(err(
            "Fallback capture requires the existing Memory archive owner",
        ));
    }
    Ok(path.to_owned())
}
fn source(config: &Value, id: &str) -> Result<String, CoreError> {
    Ok(format!(
        "{}/native-{}.md",
        archive(config)?,
        &digest(&json!(id))?[7..]
    ))
}
fn marker(source: &str) -> Result<String, CoreError> {
    Ok(format!(
        ".agentic-workspace/local/effects/decision-{}.prepared.json",
        &digest(&json!(source))?[7..]
    ))
}
pub(crate) fn extend_owner(owner: &mut Value) -> Result<(), CoreError> {
    let text = json!({"type":"string","minLength":1,"maxLength":8192});
    let strings = json!({"type":"array","maxItems":32,"uniqueItems":true,"items":text});
    let material = json!({"type":"object","additionalProperties":false,"properties":{
        "id":{"type":"string","minLength":1,"maxLength":256},"decision":text,"consequence":text,
        "rationale":text,"alternatives":strings,"dependency_paths":strings,
        "supersedes":{"type":"array","maxItems":16,"items":{"type":"object","additionalProperties":false,
            "properties":{"id":text,"material_revision":text,"scope":strings},"required":["id","material_revision","scope"]}}},
        "required":["id","decision","consequence","rationale","alternatives","dependency_paths","supersedes"]});
    let args = json!({"$schema":"https://json-schema.org/draft/2020-12/schema","type":"object","additionalProperties":false,
        "properties":{"material":material,"answer":{"enum":["confirm-decision","defer"]},"proposal_revision":text},"required":["material"]});
    let recovery = json!({"$schema":"https://json-schema.org/draft/2020-12/schema","type":"object","additionalProperties":false,
        "properties":{"source":text,"record_revision":text},"required":["source","record_revision"]});
    owner["domains"] = json!(["memory"]);
    owner["effects"] = json!([{"id":EFFECT,"domain":"memory"}]);
    if !owner["operations"].is_array() {
        owner["operations"] = json!([]);
    }
    for id in ["memory.capture-decision", "memory.recover-decision"] {
        owner["operations"].as_array_mut().unwrap().push(json!({"id":id,"semantic_revision":SEMANTICS,
            "input_schema":{"$schema":"https://json-schema.org/draft/2020-12/schema","type":"object","additionalProperties":false,
                "properties":{"target":{"type":"string"},"request":{"type":"object"},"binding":{"type":"object"},"post_revision":{"type":"string"}},
                "required":["target","request","binding","post_revision"]},"result_kind":"agentic-memory/decision-publication/v1","effects":[EFFECT],"reads":["memory"]}));
    }
    owner["requests"].as_array_mut().unwrap().extend([
        json!({"kind":CAPTURE,"result_kind":"agentic-memory/decision-proposal/v1","input_schema":args}),
        json!({"kind":RECOVER,"result_kind":"agentic-memory/decision-publication/v1","input_schema":recovery})]);
    owner["revision"] = json!(digest(&json!([owner["requests"], owner["operations"]]))?);
    Ok(())
}
fn dependencies(root: &Dir, paths: &Value) -> Result<Value, CoreError> {
    let mut result = json!({});
    for path in paths.as_array().into_iter().flatten() {
        let path = path
            .as_str()
            .ok_or_else(|| err("Decision dependency must be an exact path"))?;
        let bytes = read(root, path)?.ok_or_else(|| err("Decision dependency is missing"))?;
        result[path] = json!(crate::decision_source::hash(&bytes));
    }
    Ok(result)
}
fn manifest_postimage(
    root: &Dir,
    source: &str,
    scope: &[String],
) -> Result<(Value, String), CoreError> {
    let before = read(root, MANIFEST)?;
    let text = std::str::from_utf8(before.as_deref().unwrap_or(b"version=1\n")).map_err(err)?;
    let crlf = text.contains("\r\n");
    if crlf && text.replace("\r\n", "").contains('\n') {
        return Err(err(
            "Mixed manifest line endings require source-owner repair",
        ));
    }
    let normalized = text.replace("\r\n", "\n");
    let mut document = normalized.parse::<toml_edit::DocumentMut>().map_err(err)?;
    if document
        .get("version")
        .and_then(toml_edit::Item::as_integer)
        != Some(1)
    {
        return Err(err("Unsupported Memory manifest; source preserved"));
    }
    if document.to_string() != normalized {
        return Err(err("Manifest rendering cannot preserve unrelated source"));
    }
    let had_notes = document.contains_key("notes");
    if !had_notes {
        document["notes"] = toml_edit::Item::Table(toml_edit::Table::new());
    }
    let notes = document["notes"]
        .as_table_mut()
        .ok_or_else(|| err("Unsupported Memory notes representation"))?;
    if notes.contains_key(source) {
        return Err(err("Decision manifest destination already exists"));
    }
    let entry = json!({"native_decision":true,"decision_scope":scope,
        "routes_from":scope.iter().filter_map(|s|s.strip_prefix("path:")).collect::<Vec<_>>()});
    let entry = toml_edit::ser::to_document(&entry).map_err(err)?;
    notes.insert(source, toml_edit::Item::Table(entry.as_table().clone()));
    let rendered = document.to_string();
    document["notes"].as_table_mut().unwrap().remove(source);
    if !had_notes {
        document.remove("notes");
    }
    if document.to_string() != normalized {
        return Err(err("Manifest update cannot preserve unrelated bytes"));
    }
    Ok((
        before
            .as_ref()
            .map(|b| json!(crate::native_intent::hash(b)))
            .unwrap_or(Value::Null),
        if crlf {
            rendered.replace('\n', "\r\n")
        } else {
            rendered
        },
    ))
}
fn manifest_current(root: &Dir, binding: &Value, allow_before: bool) -> Result<bool, CoreError> {
    let current = read(root, MANIFEST)?
        .map(|b| json!(crate::native_intent::hash(&b)))
        .unwrap_or(Value::Null);
    Ok(current
        == crate::native_intent::hash(binding["manifest_postimage"].as_str().unwrap().as_bytes())
        || allow_before && current == binding["manifest_before"])
}
fn declaration_current(root: &Dir, binding: &Value) -> Result<bool, CoreError> {
    let Some(bytes) = read(root, MANIFEST)? else {
        return Ok(false);
    };
    let current: toml::Value = match std::str::from_utf8(&bytes)
        .ok()
        .and_then(|s| toml::from_str(s).ok())
    {
        Some(value) => value,
        None => return Ok(false),
    };
    let expected: toml::Value =
        toml::from_str(binding["manifest_postimage"].as_str().unwrap()).map_err(err)?;
    let source = binding["source"].as_str().unwrap();
    let row = current.get("notes").and_then(|v| v.get(source));
    Ok(expected["notes"][source]
        .as_table()
        .unwrap()
        .iter()
        .all(|(k, v)| row.and_then(|r| r.get(k)) == Some(v)))
}
fn publish_manifest(root: &Dir, binding: &Value) -> Result<(), CoreError> {
    if !manifest_current(root, binding, true)? {
        return Err(err("Memory manifest changed before publication/recovery"));
    }
    if manifest_current(root, binding, false)? {
        return Ok(());
    }
    let bytes = binding["manifest_postimage"].as_str().unwrap().as_bytes();
    let temporary = format!("{MANIFEST}.{}.tmp", &digest(binding)?[7..]);
    if let Some(prior) = read(root, &temporary)? {
        if prior != bytes {
            return Err(err("Unowned manifest temporary preserved"));
        }
    } else {
        let mut f = root
            .open_with(&temporary, OpenOptions::new().write(true).create_new(true))
            .map_err(err)?;
        if let Ok(metadata) = root.metadata(MANIFEST) {
            f.set_permissions(metadata.permissions()).map_err(err)?;
        }
        f.write_all(bytes).map_err(err)?;
        f.sync_all().map_err(err)?;
    }
    if !manifest_current(root, binding, true)? {
        return Err(err("Manifest drift before publication"));
    }
    if binding["manifest_before"].is_null() {
        root.hard_link(&temporary, root, MANIFEST).map_err(err)?;
        root.remove_file(&temporary).map_err(err)?;
    } else {
        root.rename(&temporary, root, MANIFEST).map_err(err)?;
    }
    Ok(())
}
fn material_bytes(material: &Value, binding: &Value) -> Result<Vec<u8>, CoreError> {
    let basis = digest(&json!([SEMANTICS, material, binding]))?;
    let reference = json!({"owner":"bounded-human-answer","reference":basis,"revision":basis});
    let record = json!({"id":material["id"],"decision":material["decision"],"consequence":material["consequence"],
        "authors":[{"kind":"unattributed","id":format!("request-material:{}",digest(material)?)}],"contributors":[],
        "authority":{"actor":{"kind":"human","id":format!("bounded-answer:{basis}")},"basis":[reference]},
        "scope":binding["scope"],"dependencies":binding["dependencies"].as_object().unwrap().iter().map(|(p,r)|json!({"owner":"repository","reference":p,"revision":r})).collect::<Vec<_>>(),
        "context":[],"supersedes":material["supersedes"]});
    let text = format!(
        "# Fallback decision\n\nMaterial supplied through an AW owner request. Deciding provenance is an exact bounded human answer, not cryptographically authenticated identity. Publication alone does not admit this consequence.\n\n{}\n\nRejected alternatives / trade-offs:\n{}\n\n```aw-decision\n{}\n```\n",
        material["rationale"].as_str().unwrap(),
        serde_json::to_string(&material["alternatives"]).map_err(err)?,
        serde_json::to_string_pretty(&record).map_err(err)?
    );
    if text.len() > 262144 {
        return Err(err("Decision exceeds bounded source size"));
    }
    crate::decision_source::record(
        text.as_bytes(),
        binding["source"].as_str().unwrap(),
        "memory",
    )?;
    Ok(text.into_bytes())
}
fn proposal(material: &Value, binding: &Value, post: &str) -> Result<String, CoreError> {
    digest(
        &json!({"semantics":SEMANTICS,"material":material,"binding":binding,"post_revision":post}),
    )
}
fn outcome(invocation: &Value) -> Value {
    json!({"status":"applied","effects":[EFFECT],"value":{"kind":"agentic-memory/decision-publication/v1",
        "source":invocation["arguments"]["binding"]["source"],"post_revision":invocation["arguments"]["post_revision"],
        "authority_effect":"publication-only","continuing_custody":false,"completion_authority":false}})
}
// An immutable publication attempt is necessary but insufficient. Reconstruct
// the exact owner proposal and bounded answer before admitting deciding basis.
fn retained(target: &Path, source: &str) -> Result<Option<Value>, CoreError> {
    let root = Dir::open_ambient_dir(target, ambient_authority()).map_err(err)?;
    let Some(raw) = read(&root, &marker(source)?)? else {
        return Ok(None);
    };
    let record: Value = serde_json::from_slice(&raw).map_err(err)?;
    let i = &record["invocation"];
    let args = &i["arguments"];
    let request = &args["request"];
    let binding = &args["binding"];
    let attempt = crate::attempt_store::read_source(
        target.to_str().unwrap(),
        &serde_json::from_value(record["custody"]["attempt"].clone()).map_err(err)?,
    )?;
    if attempt["invocation"] != *i
        || i["operation_id"] != "memory.capture-decision"
        || i["source_owner"] != "memory"
        || args["target"] != target.to_str().unwrap()
        || binding["source"] != source
        || binding["semantics"] != SEMANTICS
        || request["request_kind"] != CAPTURE
        || request["task_identity"] != binding["work"]
        || request["capability_revision"] != binding["capability_revision"]
        || request["arguments"]["answer"] != "confirm-decision"
        || record["outcome"] != outcome(i)
    {
        return Err(err(
            "Decision publication lacks its exact bounded-human-answer basis",
        ));
    }
    let mut owner = json!({"requests":[]});
    extend_owner(&mut owner)?;
    let schema = &owner["requests"][0]["input_schema"];
    crate::schema_validator(schema, "retained decision answer")?
        .validate(&request["arguments"])
        .map_err(err)?;
    if !binding["scope"]
        .as_array()
        .is_some_and(|rows| !rows.is_empty() && rows.iter().all(Value::is_string))
        || !binding["dependencies"]
            .as_object()
            .is_some_and(|rows| rows.values().all(Value::is_string))
        || !binding["manifest_postimage"].is_string()
        || !binding["policy_revision"].is_string()
    {
        return Err(err("Malformed decision binding; no admission"));
    }
    let bytes = material_bytes(&request["arguments"]["material"], binding)?;
    let post = crate::native_intent::hash(&bytes);
    if args["post_revision"] != post
        || request["arguments"]["proposal_revision"]
            != proposal(&request["arguments"]["material"], binding, &post)?
    {
        return Err(err(
            "Decision answer does not bind the complete proposal/postimage",
        ));
    }
    crate::attempt_store::prepare_commit(
        target.to_str().unwrap(),
        record["custody"].clone(),
        record["outcome"].clone(),
    )?;
    Ok(Some(record))
}
fn committed(root: &Dir, target: &Path, record: &Value) -> Result<bool, CoreError> {
    let prepared = crate::attempt_store::prepare_commit(
        target.to_str().unwrap(),
        record["custody"].clone(),
        record["outcome"].clone(),
    )?;
    let Some(raw) = read(
        root,
        prepared["custody"]["committed"]["path"].as_str().unwrap(),
    )?
    else {
        return Ok(false);
    };
    let expected = serde_json::from_value(prepared["custody"]["committed"].clone()).map_err(err)?;
    let result = crate::attempt_store::read_source(target.to_str().unwrap(), &expected)?;
    let _ = raw;
    Ok(result["outcome"] == record["outcome"])
}

pub(crate) fn view(
    target: &Path,
    work: &Value,
    scope: &[String],
    config: &Value,
    contract: &Value,
    context: &Value,
    request: Option<&Value>,
) -> Result<Value, CoreError> {
    let owner = contract["owners"]
        .as_array()
        .unwrap()
        .iter()
        .find(|o| o["owner"] == "memory")
        .unwrap();
    let revision = digest(&json!([config["revision"], work, scope, SEMANTICS]))?;
    let template = |kind: &str, args: Value| {
        json!({"kind":"agentic-workspace/public-request/v1","id":kind,"owner":"memory","owner_revision":owner["revision"],
        "source_revision":revision,"capability_revision":contract["revision"],"task_identity":work,"request_kind":kind,"arguments":args})
    };
    let mut view = json!({"status":"available","requests":[],"contribution":{"owner":"memory","revision":revision,"actions":[]},
        "agent_authority":"not-established-by-current-policy-facts"});
    if let Some(destination) = config["admissions"]["decision_record_target"]
        .as_str()
        .filter(|s| !s.is_empty())
    {
        view["status"] = json!("stronger-owner-required");
        view["destination"] = json!(destination);
        view["gap"] = json!("repository-decision-owner-capture-request-unavailable");
        if request.is_some() {
            return Err(err(
                "Configured repository decision owner must be used; competing fallback capture is forbidden",
            ));
        }
        return Ok(view);
    }
    if scope.is_empty() {
        view["status"] = json!("exact-decision-scope-required");
        if request.is_some() {
            return Err(err(
                "Fallback decision requires exact current changed-path scope",
            ));
        }
        return Ok(view);
    }
    view["requests"] = json!([template(
        CAPTURE,
        json!({"material":{"id":"<deliberate-decision-id>","decision":"<deliberate decision>","consequence":"<bounded future consequence>",
        "rationale":"<rationale>","alternatives":[],"dependency_paths":[],"supersedes":[]}})
    )]);
    let Some(request) = request else {
        let root = Dir::open_ambient_dir(target, ambient_authority()).map_err(err)?;
        let archive = archive(config)?;
        if read(&root, &format!("{archive}/.confinement-check")).is_err() {
            view["status"] = json!("capture-source-reconciliation-required");
            view["requests"] = json!([]);
            return Ok(view);
        }
        if let Ok(entries) = root.read_dir(&archive) {
            let mut count = 0;
            for entry in entries {
                let name = entry
                    .map_err(err)?
                    .file_name()
                    .to_string_lossy()
                    .to_string();
                if !name.starts_with("native-") || !name.ends_with(".md") {
                    continue;
                }
                let source = format!("{archive}/{name}");
                let hint = read(&root, &marker(&source)?)?
                    .and_then(|b| serde_json::from_slice::<Value>(&b).ok());
                if !hint.as_ref().is_some_and(|r| {
                    r["invocation"]["arguments"]["binding"]["scope"]
                        .as_array()
                        .is_some_and(|rows| rows.iter().any(|s| scope.iter().any(|p| s == p)))
                }) {
                    continue;
                }
                if let Some(record) = retained(target, &source)? {
                    count += 1;
                    if count > 64 {
                        return Err(err(
                            "Relevant native decision recovery exceeds bounded selection",
                        ));
                    }
                    let b = &record["invocation"]["arguments"]["binding"];
                    let published = committed(&root, target, &record)?;
                    if published && !declaration_current(&root, b)? {
                        view["contribution"]["blockers"] = json!([{"code":"decision-declaration-currentness-lost","message":"The exact declared decision source/scope changed; preserve source and reconcile its bounded answer.","affects":["task"]}]);
                    } else if !published && b["work"] == *work && b["scope"] == json!(scope) {
                        view["requests"].as_array_mut().unwrap().push(template(
                            RECOVER,
                            json!({"source":source,"record_revision":digest(&record)?}),
                        ));
                    }
                }
            }
        }
        return Ok(view);
    };
    crate::prepare_request_value(
        json!({"request":request,"current_work":work,"capability_contract":contract}),
    )?;
    if request["source_revision"] != revision {
        return Err(err(
            "Fallback decision request is stale; resolve current work/policy/scope",
        ));
    }
    let root = Dir::open_ambient_dir(target, ambient_authority()).map_err(err)?;
    let args = &request["arguments"];
    let (binding, post, operation) = if request["request_kind"] == RECOVER {
        let source = args["source"].as_str().unwrap();
        let record =
            retained(target, source)?.ok_or_else(|| err("Decision recovery evidence missing"))?;
        let binding = &record["invocation"]["arguments"]["binding"];
        let post = record["invocation"]["arguments"]["post_revision"]
            .as_str()
            .unwrap();
        if args["record_revision"] != digest(&record)?
            || binding["work"] != *work
            || binding["scope"] != json!(scope)
            || binding["policy_revision"] != config["revision"]
            || binding["capability_revision"] != contract["revision"]
            || committed(&root, target, &record)?
            || !manifest_current(&root, binding, true)?
            || read(&root, source)?.is_none_or(|b| crate::native_intent::hash(&b) != post)
            || dependencies(
                &root,
                &json!(
                    binding["dependencies"]
                        .as_object()
                        .unwrap()
                        .keys()
                        .collect::<Vec<_>>()
                ),
            )? != binding["dependencies"]
        {
            return Err(err(
                "Decision recovery is stale, consumed, or lacks current dependencies",
            ));
        }
        (binding.clone(), post.to_owned(), "memory.recover-decision")
    } else {
        let material = &args["material"];
        if context["records"]
            .as_array()
            .is_some_and(|records| records.len() >= 64)
        {
            return Err(err(
                "Relevant decision closure is at its bounded capacity; preserve source and narrow the proposed decision scope",
            ));
        }
        let source = source(config, material["id"].as_str().unwrap())?;
        if read(&root, &source)?.is_some() {
            return Err(err(
                "Decision destination collision; existing source preserved",
            ));
        }
        for old in material["supersedes"].as_array().unwrap() {
            if !context["admissions"]
                .as_array()
                .into_iter()
                .flatten()
                .any(|a| a["id"] == old["id"] && a["material_revision"] == old["material_revision"])
            {
                return Err(err(
                    "Supersession requires an exact currently admitted former decision",
                ));
            }
        }
        let (manifest_before, manifest_postimage) = manifest_postimage(&root, &source, scope)?;
        let binding = json!({"semantics":SEMANTICS,"source":source,"before":null,"work":work,"scope":scope,
            "manifest_before":manifest_before,"manifest_postimage":manifest_postimage,
            "policy_revision":config["revision"],"capability_revision":contract["revision"],
            "dependencies":dependencies(&root,&material["dependency_paths"])?,
            "superseded_sources":material["supersedes"].as_array().unwrap().iter().map(|old| context["admissions"].as_array().unwrap().iter().find(|a| a["id"] == old["id"] && a["material_revision"] == old["material_revision"]).unwrap().clone()).collect::<Vec<_>>()});
        let bytes = material_bytes(material, &binding)?;
        let post = crate::native_intent::hash(&bytes);
        let proposal = proposal(material, &binding, &post)?;
        if args["answer"].is_null() {
            let mut answer = args.clone();
            answer["proposal_revision"] = json!(proposal);
            view["status"] = json!("human-decision-required");
            view["proposal"] = json!({"binding":binding,"postimage":std::str::from_utf8(&bytes).map_err(err)?,"post_revision":post,"proposal_revision":proposal,
                "authority_basis":"exact-bounded-human-answer; no authenticated identity claim"});
            view["contribution"]["decisions"] = json!([{"id":"memory-fallback-decision","question":"Confirm this exact fallback decision and its bounded future consequence? Publication alone grants no deciding authority.",
                "response_request":{"request_kind":CAPTURE,"arguments":answer},"choices":[{"id":"confirm-decision","label":"Confirm this exact bounded decision"},{"id":"defer","label":"Defer without publication"}],"affects":["task","effect:memory-state"]}]);
            return Ok(view);
        }
        if args["proposal_revision"] != proposal {
            return Err(err(
                "Human answer is stale or does not bind this exact decision proposal",
            ));
        }
        if args["answer"] == "defer" {
            view["status"] = json!("deferred");
            return Ok(view);
        }
        if let Some(record) = retained(target, &source)?
            && committed(&root, target, &record)?
        {
            return Err(err("This decision authorization was already consumed"));
        }
        (binding, post, "memory.capture-decision")
    };
    view["status"] = json!("write-ready");
    view["contribution"]["actions"] = json!([{"operation_id":operation,"dependency_revision":digest(&json!([binding,request,post]))?,
        "arguments":{"target":target,"request":request,"binding":binding,"post_revision":post},"effects":[EFFECT],"source_requests":[request]}]);
    Ok(view)
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
    read(&root, lock_path)?;
    let lock = root
        .open_with(
            lock_path,
            OpenOptions::new().read(true).write(true).create(true),
        )
        .map_err(err)?
        .into_std();
    if lock.metadata().map_err(err)?.len() != 0 {
        return Err(err("Unknown Memory lock preserved"));
    }
    lock.try_lock().map_err(err)?;
    revalidate()?;
    let args = &invocation["arguments"];
    let source = args["binding"]["source"].as_str().unwrap();
    let prior = retained(target, source)?;
    if invocation["operation_id"] == "memory.recover-decision" {
        let record = prior.ok_or_else(|| err("Decision recovery missing"))?;
        let admitted = crate::attempt_store::admit(
            json!({"target":target,"decision":decision,"invocation":invocation}),
        )?;
        revalidate()?;
        publish_manifest(&root, &args["binding"])?;
        crate::attempt_store::commit(
            json!({"target":target,"custody":record["custody"],"outcome":record["outcome"]}),
        )?;
        let out = outcome(invocation);
        let done = crate::attempt_store::commit(
            json!({"target":target,"custody":admitted["custody"],"outcome":out}),
        )?;
        return Ok(json!({"outcome":out,"custody":done["custody"]}));
    }
    if prior
        .as_ref()
        .is_some_and(|r| r["invocation"] != *invocation)
    {
        return Err(err("Decision attempt collision preserved"));
    }
    let bytes = material_bytes(&args["request"]["arguments"]["material"], &args["binding"])?;
    if crate::native_intent::hash(&bytes) != args["post_revision"] {
        return Err(err("Decision postimage changed"));
    }
    let temporary = format!("{source}.{}.tmp", &digest(invocation)?[7..]);
    if prior.is_none() && read(&root, &temporary)?.is_some() {
        return Err(err("Unowned decision temporary preserved"));
    }
    let manifest_temporary = format!("{MANIFEST}.{}.tmp", &digest(&args["binding"])?[7..]);
    if prior.is_none() && read(&root, &manifest_temporary)?.is_some() {
        return Err(err("Unowned manifest temporary preserved"));
    }
    read(&root, source)?;
    let parent = source.rsplit_once('/').unwrap().0;
    root.create_dir_all(parent).map_err(err)?;
    read(&root, source)?;
    let admitted = crate::attempt_store::admit(
        json!({"target":target,"decision":decision,"invocation":invocation,"custody":prior.as_ref().map(|r|&r["custody"])}),
    )?;
    let out = outcome(invocation);
    let record = json!({"invocation":invocation,"custody":admitted["custody"],"outcome":out});
    if prior.is_none() {
        let mut f = root
            .open_with(
                marker(source)?,
                OpenOptions::new().write(true).create_new(true),
            )
            .map_err(err)?;
        f.write_all(&serde_json::to_vec(&record).map_err(err)?)
            .map_err(err)?;
        f.sync_all().map_err(err)?;
    }
    observe("prepared")?;
    if let Some(existing) = read(&root, &temporary)? {
        if existing != bytes {
            return Err(err("Unknown decision temporary preserved"));
        }
    } else {
        let mut f = root
            .open_with(&temporary, OpenOptions::new().write(true).create_new(true))
            .map_err(err)?;
        f.write_all(&bytes).map_err(err)?;
        f.sync_all().map_err(err)?;
    }
    revalidate()?;
    // Atomic no-clobber publication. Neither a race nor recovery can overwrite
    // an externally created destination; the prepared source remains recoverable.
    root.hard_link(&temporary, &root, source).map_err(err)?;
    root.remove_file(&temporary).map_err(err)?;
    observe("source-published")?;
    publish_manifest(&root, &args["binding"])?;
    observe("manifest-published")?;
    let done = crate::attempt_store::commit(
        json!({"target":target,"custody":admitted["custody"],"outcome":out}),
    )?;
    Ok(json!({"outcome":out,"custody":done["custody"]}))
}

/// Selected native sources join the existing continuity context. No scan or
/// retained artifact is needed for work without an exact decision scope.
pub(crate) fn context(target: &Path, config: &Value, scope: &[String]) -> Result<Value, CoreError> {
    let mut result = json!({"records":[],"admissions":[],"current_dependencies":[],"required_records":[],"applicable_scope":scope});
    if scope.is_empty() || !crate::native_config::module_enabled(config, "memory") {
        return Ok(result);
    }
    let root = Dir::open_ambient_dir(target, ambient_authority()).map_err(err)?;
    let archive = archive(config)?;
    let Ok(Some(manifest)) = read(&root, MANIFEST) else {
        return Ok(result);
    };
    let Some(manifest): Option<toml::Value> = std::str::from_utf8(&manifest)
        .ok()
        .and_then(|s| toml::from_str(s).ok())
    else {
        // Advisory source errors are already exposed by Memory. Only an exact
        // native declaration/retained answer can introduce a governing blocker.
        return Ok(result);
    };
    let entries = manifest.get("notes").and_then(toml::Value::as_table);
    let mut pending: Vec<String> = entries
        .into_iter()
        .flatten()
        .filter(|(_, entry)| {
            entry.get("native_decision").and_then(toml::Value::as_bool) == Some(true)
                && entry
                    .get("decision_scope")
                    .and_then(toml::Value::as_array)
                    .is_some_and(|rows| {
                        rows.iter()
                            .any(|s| s.as_str().is_some_and(|s| scope.iter().any(|p| p == s)))
                    })
        })
        .map(|(source, _)| source.clone())
        .collect();
    let mut selected = std::collections::BTreeSet::new();
    while let Some(source) = pending.pop() {
        if !selected.insert(source.clone()) {
            continue;
        }
        if selected.len() > 64 {
            return Err(err(
                "Relevant native decision supersession closure exceeds bounded selection",
            ));
        }
        if !source.starts_with(&format!("{archive}/native-")) {
            return Err(err(
                "Native decision declaration is outside current fallback archive",
            ));
        }
        let bytes = read(&root, &source)?.ok_or_else(|| {
            err("Native decision source disappeared; preserve declaration and reconcile")
        })?;
        let normalized = crate::decision_source::record(&bytes, &source, "memory")?;
        let record = retained(target, &source)?
            .ok_or_else(|| err("Native decision lacks bounded answer; source remains advisory"))?;
        let args = &record["invocation"]["arguments"];
        let binding = &args["binding"];
        if !declaration_current(&root, binding)? {
            return Err(err(
                "Decision declaration changed; reconcile exact source/scope",
            ));
        }
        if !committed(&root, target, &record)? {
            continue;
        }
        if crate::native_intent::hash(&bytes) != args["post_revision"] {
            return Err(err(
                "Native decision source changed; reconcile bounded answer",
            ));
        }
        for ancestor in normalized["supersedes"].as_array().unwrap() {
            let admission = binding["superseded_sources"]
                .as_array()
                .into_iter()
                .flatten()
                .find(|a| {
                    a["id"] == ancestor["id"]
                        && a["material_revision"] == ancestor["material_revision"]
                })
                .ok_or_else(|| err("Supersession lacks its bound source admission"))?;
            let reference = admission["source"]["reference"]
                .as_str()
                .ok_or_else(|| err("Supersession source locator is missing"))?;
            if reference == self::source(config, ancestor["id"].as_str().unwrap())?
                && retained(target, reference)?.is_some()
            {
                pending.push(reference.to_owned());
            } else {
                result["required_records"]
                    .as_array_mut()
                    .unwrap()
                    .push(admission.clone());
            }
        }
        result["admissions"].as_array_mut().unwrap().push(json!({"id":normalized["id"],"material_revision":normalized["material_revision"],"source":normalized["source"],"rationale_reference":source}));
        for dependency in normalized["authority"]["basis"]
            .as_array()
            .unwrap()
            .iter()
            .chain(normalized["dependencies"].as_array().unwrap())
            .chain(std::iter::once(&normalized["source"]))
        {
            // Retain admitted history when policy or facts drift, but do not
            // invent current authority. Continuity suppresses stale consequences
            // and permits a new exact decision to supersede the former record.
            if dependency["owner"] == "bounded-human-answer"
                && binding["policy_revision"] != config["revision"]
            {
                continue;
            }
            if dependency["owner"] == "repository"
                && read(&root, dependency["reference"].as_str().unwrap())?
                    .is_none_or(|b| crate::decision_source::hash(&b) != dependency["revision"])
            {
                continue;
            }
            if !result["current_dependencies"]
                .as_array()
                .unwrap()
                .contains(dependency)
            {
                result["current_dependencies"]
                    .as_array_mut()
                    .unwrap()
                    .push(dependency.clone());
            }
        }
        result["records"].as_array_mut().unwrap().push(normalized);
    }
    Ok(result)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn bounded_answer_publication_recovers_each_interruption() {
        for stage in ["prepared", "source-published", "manifest-published"] {
            let target = std::env::temp_dir().join(format!(
                "aw-decision-{}-{}",
                std::process::id(),
                std::time::SystemTime::now()
                    .duration_since(std::time::UNIX_EPOCH)
                    .unwrap()
                    .as_nanos()
            ));
            std::fs::create_dir_all(&target).unwrap();
            let target = std::fs::canonicalize(target).unwrap();
            let input = json!({"target":target,"task":"Exact fixture human decision","changed":["src/a.rs"]});
            let start = |request: Option<Value>| {
                let mut v = input.clone();
                v["request"] = request.unwrap_or(Value::Null);
                crate::native_public::start(v).unwrap()
            };
            let mut request = start(None)["memory"]["capture"]["requests"][0].clone();
            request["arguments"]["material"] = json!({"id":"fixture:recovery","decision":"A deliberate fixture decision","consequence":"Preserve the fixture boundary","rationale":"Test interruption only; no actual repository decision.","alternatives":[],"dependency_paths":[],"supersedes":[]});
            let mut answer =
                start(Some(request))["decision_packet"]["decision_request"]["response_request"]
                    .clone();
            answer["arguments"]["answer"] = json!("confirm-decision");
            let ready = start(Some(answer.clone()));
            let action = &ready["decision_packet"]["primary_action"];
            let revalidate = || {
                let current = start(Some(answer.clone()));
                crate::admit_invocation_value(
                    json!({"decision":current["decision_packet"],"invocation":action}),
                )?;
                Ok(())
            };
            let interrupted = execute_checked(
                &target,
                &ready["decision_packet"],
                action,
                &mut { revalidate },
                &mut |point| {
                    if point == stage {
                        Err(err("fixture interruption"))
                    } else {
                        Ok(())
                    }
                },
            );
            assert!(
                interrupted
                    .unwrap_err()
                    .to_string()
                    .contains("fixture interruption")
            );
            let fresh = start(None);
            assert!(
                fresh["decision_packet"]["decision_context"]["states"]
                    .as_array()
                    .is_none_or(Vec::is_empty)
            );
            let next = if stage == "prepared" {
                action.clone()
            } else {
                let recovery = fresh["memory"]["capture"]["requests"]
                    .as_array()
                    .unwrap()
                    .iter()
                    .find(|r| r["request_kind"] == RECOVER)
                    .unwrap()
                    .clone();
                start(Some(recovery))["decision_packet"]["primary_action"].clone()
            };
            assert!(next.is_object(), "{fresh}");
            let mut invoke = input.clone();
            invoke["invocation"] = next;
            crate::native_public::invoke(invoke).unwrap();
            assert_eq!(
                start(None)["decision_packet"]["decision_context"]["states"]
                    .as_array()
                    .unwrap()
                    .len(),
                1
            );
            // Only this test-created directory is removed.
            std::fs::remove_dir_all(target).unwrap();
        }
    }
}
