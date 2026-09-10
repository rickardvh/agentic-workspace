//! Verification's exact source-consistency judgments. The answer establishes a
//! bounded judgment basis, never authenticated human identity or semantic truth.
use crate::{CoreError, digest, native_planning};
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

pub(crate) const REQUEST: &str = "verification/reconcile-sources/v1";
pub(crate) const OP: &str = "verification.record-source-reconciliation";
const EFFECT: &str = "proof-execution";
const SEMANTICS: &str = "source-reconciliation/v1";

fn err(e: impl std::fmt::Display) -> CoreError {
    CoreError::new(e.to_string())
}
fn strings(value: &Value) -> Vec<String> {
    value
        .as_array()
        .into_iter()
        .flatten()
        .filter_map(Value::as_str)
        .map(str::to_owned)
        .collect()
}

pub(crate) fn extend_contract(owner: &mut Value) -> Result<(), CoreError> {
    owner["requests"].as_array_mut().unwrap().push(json!({
        "kind":REQUEST,"result_kind":"agentic-workspace/source-reconciliation/v1",
        "input_schema":{"$schema":"https://json-schema.org/draft/2020-12/schema","type":"object","additionalProperties":false,
            "properties":{"binding_revision":{"type":"string"},"proposal_revision":{"type":"string"},"answer":{"enum":["confirm","defer"]},"judgments":{"type":"object","minProperties":1,"maxProperties":64,
                "additionalProperties":{"type":"object","additionalProperties":false,
                    "properties":{"disposition":{"enum":["updated","reviewed-current"]},"reason":{"type":"string","minLength":1,"maxLength":4096}},
                    "required":["disposition","reason"]}}},"required":["binding_revision","judgments"]}}));
    owner["operations"].as_array_mut().unwrap().push(json!({"id":OP,"semantic_revision":SEMANTICS,
        "input_schema":{"$schema":"https://json-schema.org/draft/2020-12/schema","type":"object","additionalProperties":false,"properties":{
            "target":{"type":"string"},"request":{"type":"object"},"binding":{"type":"object"},"receipt_ref":{"type":"string"}},
            "required":["target","request","binding","receipt_ref"]},
        "result_kind":"agentic-workspace/source-reconciliation/v1","effects":[EFFECT],"reads":["verification"]}));
    owner["revision"] = json!(digest(&json!([owner["requests"], owner["operations"]]))?);
    Ok(())
}

fn observe(root: &Dir, path: &str) -> Result<Value, CoreError> {
    Ok(match native_planning::read(root, path)? {
        Some(bytes) => json!({"status":"present","revision":crate::decision_source::hash(&bytes)}),
        None => json!({"status":"absent"}),
    })
}

// Reobserve the applicable declared path set, including newly created files.
// No prior AW event stream or comprehensive caller change list is freshness.
fn scope_files(root: &Dir, patterns: &[String]) -> Result<BTreeSet<String>, CoreError> {
    let mut paths = BTreeSet::new();
    let mut visited = BTreeSet::new();
    let mut pending = Vec::new();
    for pattern in patterns {
        let prefix = pattern.split(['*', '?', '[']).next().unwrap();
        if prefix == pattern {
            crate::decision_source::relative(prefix)?;
            paths.insert(prefix.to_owned());
        } else {
            let directory = prefix.rsplit_once('/').map(|(p, _)| p).unwrap_or("");
            pending.push(directory.to_owned());
        }
    }
    let mut count = 0;
    while let Some(directory) = pending.pop() {
        if !visited.insert(directory.clone()) {
            continue;
        }
        if !directory.is_empty() {
            crate::decision_source::relative(&directory)?;
            // Check every prefix without opening a directory as a file.
            native_planning::read(root, &format!("{directory}/.aw-scope-confinement"))?;
        }
        let entries = match root.read_dir(if directory.is_empty() {
            "."
        } else {
            &directory
        }) {
            Ok(entries) => entries,
            Err(e) if e.kind() == std::io::ErrorKind::NotFound => continue,
            Err(e) => return Err(err(e)),
        };
        for entry in entries {
            count += 1;
            if count > 4096 {
                return Err(err(
                    "source reconciliation scope exceeds bounded discovery; narrow the current work scope",
                ));
            }
            let entry = entry.map_err(err)?;
            let name = entry
                .file_name()
                .into_string()
                .map_err(|_| err("scope filename must be UTF-8"))?;
            if name == ".git" {
                continue;
            }
            let path = if directory.is_empty() {
                name
            } else {
                format!("{directory}/{name}")
            };
            if path.starts_with(".agentic-workspace/local/")
                || path == ".agentic-workspace/local"
                || path.starts_with(".agentic-workspace/proof/")
                || path == ".agentic-workspace/proof"
            {
                continue;
            }
            let meta = root.symlink_metadata(&path).map_err(err)?;
            #[cfg(windows)]
            let linked = {
                use cap_std::fs::MetadataExt;
                meta.file_attributes() & 0x400 != 0
            };
            #[cfg(not(windows))]
            let linked = meta.is_symlink();
            if linked {
                return Err(err("source reconciliation cannot traverse a linked scope"));
            }
            if meta.is_dir() {
                pending.push(path);
            } else if patterns
                .iter()
                .any(|p| crate::native_verification::matches(p, &path))
            {
                paths.insert(path);
            }
        }
    }
    if paths.len() > 256 {
        return Err(err(
            "source reconciliation selects more than 256 exact work files",
        ));
    }
    Ok(paths)
}

fn result(binding: &Value, request: &Value) -> Result<Value, CoreError> {
    let judgments = request["arguments"]["judgments"]
        .as_object()
        .ok_or_else(|| err("source judgments missing"))?;
    let expected: BTreeSet<_> = binding["sources"].as_object().unwrap().keys().collect();
    if expected != judgments.keys().collect() {
        return Err(err("judge exactly the owner-issued source set"));
    }
    if request["arguments"]["answer"] != "confirm" {
        return Err(err(
            "source judgment requires the exact bounded confirmation",
        ));
    }
    Ok(
        json!({"kind":"agentic-workspace/source-reconciliation/v1","binding_revision":digest(binding)?,
        "judgments":judgments,"authority_basis":{"kind":"exact-bounded-human-answer","request_revision":digest(request)?,
            "proposal_revision":request["arguments"]["proposal_revision"],"identity_authentication":"not-claimed"},
        "completion_authority":false,"semantic_truth":"judgment-not-mechanically-proven"}),
    )
}

fn retained(target: &Path, path: &str, binding: &Value) -> Result<Option<Value>, CoreError> {
    let root = Dir::open_ambient_dir(target, ambient_authority()).map_err(err)?;
    let published = native_planning::read(&root, path)?;
    let temporary = native_planning::read(&root, &format!("{path}.tmp"))?;
    if published.is_some() && temporary.is_some() && published != temporary {
        return Err(err("conflicting source reconciliation temporary preserved"));
    }
    let Some(bytes) = published.as_ref().or(temporary.as_ref()) else {
        return Ok(None);
    };
    let record: Value = serde_json::from_slice(bytes).map_err(err)?;
    let invocation = &record["invocation"];
    if invocation["operation_id"] != OP
        || invocation["source_owner"] != "verification"
        || invocation["arguments"]["binding"] != *binding
        || invocation["arguments"]["receipt_ref"] != path
    {
        return Err(err("unowned source reconciliation receipt preserved"));
    }
    let request = &invocation["arguments"]["request"];
    if request["arguments"]["binding_revision"] != digest(binding)?
        || record["value"] != result(binding, request)?
    {
        return Err(err(
            "source reconciliation basis differs from the exact answer",
        ));
    }
    let attempt = crate::attempt_store::read_source(
        target.to_str().unwrap(),
        &serde_json::from_value(record["custody"]["attempt"].clone()).map_err(err)?,
    )?;
    if attempt["invocation"] != *invocation {
        return Err(err(
            "source reconciliation publication has different producer custody",
        ));
    }
    let outcome = json!({"status":"applied","effects":[EFFECT],"value":record["value"]});
    let prepared = crate::attempt_store::prepare_commit(
        target.to_str().unwrap(),
        record["custody"].clone(),
        outcome,
    )?;
    if prepared["custody"] != record["custody"] {
        return Err(err("source reconciliation result custody differs"));
    }
    let mut record = record;
    record["published"] = json!(published.is_some());
    record["committed"] = json!(
        crate::attempt_store::inspect_committed(
            target.to_str().unwrap(),
            record["custody"].clone()
        )
        .is_ok()
    );
    Ok(Some(record))
}

pub(crate) struct Context<'a> {
    pub subject: Option<&'a Value>,
    pub executing: bool,
}

pub(crate) fn view(
    target: &Path,
    work: &Value,
    instructions: &Value,
    configuration: &Value,
    contract: &Value,
    request: Option<&Value>,
    context: Context<'_>,
) -> Result<Value, CoreError> {
    let Context { subject, executing } = context;
    let mut view = json!({"status":"not-required","obligations":[],"requests":[],"action":null,"decisions":[]});
    let mut sources = BTreeMap::new();
    let mut dependencies = BTreeMap::new();
    let mut declarations = Vec::new();
    let mut scope = BTreeSet::new();
    let root = Dir::open_ambient_dir(target, ambient_authority()).map_err(err)?;
    for row in instructions["sources"].as_array().into_iter().flatten() {
        let refs = strings(&row["reconcile"]);
        if refs.is_empty() {
            continue;
        }
        for source in &refs {
            sources.insert(source.clone(), observe(&root, source)?);
        }
        for dependency in strings(&row["read"]) {
            dependencies.insert(dependency.clone(), observe(&root, &dependency)?);
        }
        declarations.push(json!({"source":row["source"],"admission":row["binding_admission"],"sources":refs,"paths":row["metadata"]["paths"]}));
        let patterns = strings(&row["metadata"]["paths"]);
        let global = ["**".to_owned()];
        let observed = scope_files(
            &root,
            if patterns.is_empty() {
                // Global really means global, including discovery after opaque entry.
                &global
            } else {
                &patterns
            },
        );
        match observed {
            Ok(paths) => scope.extend(paths),
            Err(error) => {
                if request.is_some() {
                    return Err(error);
                }
                view["status"] = json!("scope-observation-required");
                view["obligations"] = json!(sources.keys().collect::<Vec<_>>());
                view["reason"] = json!(error.to_string());
                return Ok(view);
            }
        }
    }
    if sources.is_empty() {
        if request.is_some() {
            return Err(err(
                "source reconciliation request no longer has current obligations",
            ));
        }
        return Ok(view);
    }
    view["obligations"] = json!(sources.keys().collect::<Vec<_>>());
    if declarations
        .iter()
        .any(|d| d["admission"]["status"] != "current")
        || sources.values().any(|s| s["status"] != "present")
    {
        view["status"] = json!("source-admission-required");
        return Ok(view);
    }
    let mut postimages = BTreeMap::new();
    for path in scope {
        postimages.insert(path.clone(), observe(&root, &path)?);
    }
    let binding = json!({"semantics":SEMANTICS,"work":work,"subject":subject,"declarations":declarations,
        "sources":sources,"dependencies":dependencies,"work_postimages":postimages,"policy_revision":configuration["revision"],"capability_revision":contract["revision"]});
    let revision = digest(&binding)?;
    view["source_revision"] = json!(revision);
    let path = format!(
        ".agentic-workspace/proof/receipts/source-reconciliation-{}.json",
        &revision[7..]
    );
    let issued = json!({"kind":"agentic-workspace/public-request/v1","owner":"verification","id":REQUEST,"request_kind":REQUEST,
        "owner_revision":contract["owners"].as_array().unwrap().iter().find(|o|o["owner"]=="verification").unwrap()["revision"],
        "source_revision":revision,"capability_revision":contract["revision"],"task_identity":work,
        "arguments":{"binding_revision":revision,"judgments":{}}});
    let prior = match retained(target, &path, &binding) {
        Ok(prior) => prior,
        Err(error) => {
            if request.is_some() || executing {
                return Err(error);
            }
            view["status"] = json!("publication-review-required");
            view["reason"] = json!(error.to_string());
            return Ok(view);
        }
    };
    let selected = request.or_else(|| {
        prior
            .as_ref()
            .map(|p| &p["invocation"]["arguments"]["request"])
    });
    view["proposal"] = binding.clone();
    if let Some(request) = selected {
        crate::prepare_request_value(
            json!({"request":request,"current_work":work,"capability_contract":contract}),
        )?;
        let mut expected = issued.clone();
        expected["arguments"] = request["arguments"].clone();
        // Bounded decisions use a compiler-issued answer identity. Its fixed
        // arguments and source binding are validated below, never an actor label.
        expected["id"] = request["id"].clone();
        if *request != expected {
            return Err(err(
                "source reconciliation answer is stale or differs from the exact owner request",
            ));
        }
        if request["arguments"]["binding_revision"] != revision {
            return Err(err(
                "source reconciliation answer is stale or differs from the exact owner request",
            ));
        }
        let judgments = &request["arguments"]["judgments"];
        if judgments
            .as_object()
            .unwrap()
            .keys()
            .collect::<BTreeSet<_>>()
            != sources.keys().collect()
        {
            return Err(err("judge exactly the owner-issued source set"));
        }
        let proposal = json!({"binding":binding,"judgments":judgments,"destination":path,
            "completion_authority":false,"semantic_truth":"judgment-not-mechanically-proven"});
        let proposal_revision = digest(&proposal)?;
        view["proposal"] = proposal;
        let arguments = json!({"binding_revision":revision,"judgments":judgments,"proposal_revision":proposal_revision});
        let decisions = json!([{"id":"source-reconciliation","question":"Confirm these exact source judgments against the bound resulting work?",
                "material":view["proposal"],
                "response_request":{"request_kind":REQUEST,"arguments":arguments},
                "choices":[{"id":"confirm","label":"Confirm these exact judgments"},{"id":"defer","label":"Leave reconciliation unresolved"}],"affects":["claim:complete"]}]);
        if request["arguments"]["answer"].is_null() {
            if request["id"] != REQUEST {
                return Err(err(
                    "judgment material must use the issued material request",
                ));
            }
            view["status"] = json!("bounded-human-answer-required");
            view["decisions"] = decisions;
            return Ok(view);
        }
        let compiled = crate::compile_value(
            json!({"intent":{"current_work":work},"capability_contract":contract,
            "contributions":[{"owner":"verification","revision":revision,"decisions":decisions}]}),
        )?;
        let mut exact =
            compiled["pending_consequences"]["decisions"][0]["response_request"].clone();
        exact["arguments"]["answer"] = request["arguments"]["answer"].clone();
        if exact != *request {
            return Err(err(
                "answer differs from the exact owner-issued bounded request",
            ));
        }
        if request["arguments"]["proposal_revision"] != proposal_revision {
            return Err(err(
                "source reconciliation proposal changed; obtain a current bounded answer",
            ));
        }
        if request["arguments"]["answer"] == "defer" {
            view["status"] = json!("deferred");
            return Ok(view);
        }
        let _ = result(&binding, request)?;
        if prior
            .as_ref()
            .is_some_and(|r| r["committed"] == true && r["published"] == true)
            && !executing
        {
            if prior.as_ref().unwrap()["invocation"]["arguments"]["request"] != *request {
                return Err(err(
                    "current judgment already published for another exact answer",
                ));
            }
            view["status"] = json!("current");
            view["evidence"] = prior.unwrap()["value"].clone();
            view["receipt_ref"] = json!(path);
            return Ok(view);
        }
        view["status"] = json!("publication-required");
        view["action"] = json!({"operation_id":OP,"dependency_revision":digest(&json!([binding,request]))?,
            "arguments":{"target":target,"request":request,"binding":binding,"receipt_ref":path},"effects":[EFFECT],"source_requests":[request]});
    } else {
        view["status"] = json!("judgment-material-required");
        view["requests"] = json!([issued]);
        view["question"] = json!(
            "For each exact current canonical source, confirm updated or reviewed-current against the resulting work and give the bounded reason."
        );
    }
    Ok(view)
}

pub(crate) fn execute(
    target: &Path,
    decision: &Value,
    invocation: &Value,
    mut revalidate: impl FnMut() -> Result<(), CoreError>,
) -> Result<Value, CoreError> {
    let binding = &invocation["arguments"]["binding"];
    let value = result(binding, &invocation["arguments"]["request"])?;
    // Bound the fully escaped material, not character counts in the answer.
    // Custody has two fixed-shape references; reserve their path/target strings
    // and fixed metadata before acquiring any admission or writing a carrier.
    let carrier =
        serde_json::to_vec(&json!({"invocation":invocation,"value":value,"custody":null}))
            .map_err(err)?;
    let custody_budget = 8192 + 4 * serde_json::to_vec(&target).map_err(err)?.len();
    if carrier.len().saturating_add(custody_budget) > crate::decision_source::MAX_SOURCE_BYTES {
        return Err(err(
            "source reconciliation carrier exceeds bounded recovery size; shorten judgment reasons or narrow the declaration",
        ));
    }
    let root = Dir::open_ambient_dir(target, ambient_authority()).map_err(err)?;
    let lock_path = ".agentic-workspace/local/effects/source-reconciliation.lock";
    native_planning::read(&root, lock_path)?;
    root.create_dir_all(".agentic-workspace/local/effects")
        .map_err(err)?;
    native_planning::read(&root, lock_path)?;
    let lock = root
        .open_with(
            lock_path,
            OpenOptions::new().read(true).write(true).create(true),
        )
        .map_err(err)?
        .into_std();
    if lock.metadata().map_err(err)?.len() != 0 {
        return Err(err("unowned reconciliation lock preserved"));
    }
    lock.try_lock().map_err(err)?;
    let path = invocation["arguments"]["receipt_ref"].as_str().unwrap();
    let prior = retained(target, path, binding)?;
    if prior
        .as_ref()
        .is_some_and(|p| p["invocation"] != *invocation)
    {
        return Err(err("source reconciliation attempt collision preserved"));
    }
    revalidate()?;
    let mut custody = prior.as_ref().map(|p| p["custody"].clone());
    if prior.as_ref().is_some_and(|p| p["committed"] != true) {
        custody.as_mut().unwrap()["committed"] = Value::Null;
    }
    let admission = crate::attempt_store::admit(
        json!({"target":target,"decision":decision,"invocation":invocation,
        "custody":custody}),
    )?;
    let outcome = json!({"status":"applied","effects":[EFFECT],"value":value});
    let prepared = crate::attempt_store::prepare_commit(
        target.to_str().unwrap(),
        admission["custody"].clone(),
        outcome.clone(),
    )?;
    let record = json!({"invocation":invocation,"value":value,"custody":prepared["custody"]});
    let bytes = serde_json::to_vec(&record).map_err(err)?;
    if bytes.len() > crate::decision_source::MAX_SOURCE_BYTES {
        return Err(err(
            "source reconciliation receipt exceeds bounded recovery size",
        ));
    }
    revalidate()?;
    let temporary = format!("{path}.tmp");
    if prior.is_none() {
        native_planning::read(&root, path)?;
        root.create_dir_all(".agentic-workspace/proof/receipts")
            .map_err(err)?;
        native_planning::read(&root, path)?;
        let mut file = root
            .open_with(&temporary, OpenOptions::new().write(true).create_new(true))
            .map_err(err)?;
        file.write_all(&bytes).map_err(err)?;
        file.sync_all().map_err(err)?;
    }
    revalidate()?;
    if prior.as_ref().is_none_or(|p| p["published"] != true) {
        root.hard_link(&temporary, &root, path).map_err(err)?;
    }
    if native_planning::read(&root, &temporary)?.is_some() {
        root.remove_file(&temporary).map_err(err)?;
    }
    revalidate()?;
    let committed = crate::attempt_store::commit(
        json!({"target":target,"custody":admission["custody"],"outcome":outcome}),
    )?;
    Ok(json!({"outcome":outcome,"custody":committed["custody"],"post_effect_changed_paths":[path]}))
}
