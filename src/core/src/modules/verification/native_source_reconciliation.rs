//! Verification's proposed source assessments and exact publication authority.
//! Authorization retains a proposal, never attesting personal review or truth.
use crate::{CoreError, digest, native_planning};
use cap_std::{
    ambient_authority,
    fs::{Dir, OpenOptions},
};
use serde_json::{Value, json};
use std::{
    cell::RefCell,
    collections::{BTreeMap, BTreeSet},
    io::Write,
    path::Path,
};

pub(crate) const REQUEST: &str = "verification/reconcile-sources/v1";
pub(crate) const OP: &str = "verification.record-source-reconciliation";
const EFFECT: &str = "proof-execution";
const SEMANTICS: &str = "source-reconciliation/v3";
const GROUP_SIZE: usize = 64;

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
            "properties":{"relation_id":{"type":"string"},"binding_revision":{"type":"string"},"proposal_revision":{"type":"string"},"answer":{"enum":["confirm","defer"]},"read_references":{"type":"array","minItems":1,"maxItems":16,"uniqueItems":true,"items":{"type":"string"}},"judgments":{"type":"object","maxProperties":64,
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

fn observe(
    root: &Dir,
    path: &str,
    observations: &RefCell<BTreeMap<String, Value>>,
) -> Result<Value, CoreError> {
    if let Some(observed) = observations.borrow().get(path) {
        return Ok(observed.clone());
    }
    let observation =
        crate::dependency_binding::observe(root, path, crate::dependency_binding::Scheme::RawBytes);
    let observed = match observation.status {
        crate::dependency_binding::Currentness::Current => {
            json!({"status":"present","revision":observation.revision})
        }
        crate::dependency_binding::Currentness::Missing => json!({"status":"absent"}),
        _ => return Err(err(format!("source observation unavailable: {path}"))),
    };
    observations
        .borrow_mut()
        .insert(path.to_owned(), observed.clone());
    Ok(observed)
}

// Reobserve the applicable declared path set, including newly created files.
// No prior AW event stream or comprehensive caller change list is freshness.
pub(crate) fn scope_files(root: &Dir, patterns: &[String]) -> Result<BTreeSet<String>, CoreError> {
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
    Ok(paths)
}

fn assessment_semantics(binding: &Value) -> Value {
    json!({
        "assessment_role":"untrusted-caller-proposal",
        "decision_role":"authorize-exact-proposal-publication",
        "scope":{"relation_id":binding["relation_id"],
            "sources":binding["sources"].as_object().unwrap().keys().collect::<Vec<_>>(),
            "work_references":binding["work_postimages"].as_object().unwrap().keys().collect::<Vec<_>>(),
            "publication_scope":"this-group-only",
            "wider_completion":"not-authorized; consult current aggregate coverage"},
        "limits":{"identity_authentication":"not-claimed","assessment_authorship":"not-authenticated",
            "personal_source_review":"not-attested","semantic_truth":"judgment-not-mechanically-proven",
            "independent_review":"not-granted","completion_authority":false},
        "consequences":{"confirm":"Authorize publication of this exact proposed assessment for this group; no personal correctness attestation or independent acceptance.",
            "defer":"Do not publish this proposal; leave this group unresolved."}
    })
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
        "judgments":judgments,"assessment_semantics":assessment_semantics(binding),
        "authority_basis":binding.get("decision_authority").cloned().unwrap_or_else(||json!({"kind":"exact-bounded-human-answer","request_revision":digest(request).unwrap(),"proposal_revision":request["arguments"]["proposal_revision"],"identity_authentication":"not-claimed"})),
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

#[derive(Clone, Copy)]
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
    let observations = RefCell::new(BTreeMap::new());
    let mut relations = Vec::new();
    let mut ordinary = instructions.clone();
    ordinary["sources"] = json!(
        instructions["sources"]
            .as_array()
            .into_iter()
            .flatten()
            .filter(|row| !strings(&row["reconcile"]).is_empty())
            .collect::<Vec<_>>()
    );
    if ordinary["sources"]
        .as_array()
        .is_some_and(|rows| !rows.is_empty())
    {
        relations.push(("canonical-sources".to_owned(), ordinary));
    }
    for row in instructions["sources"].as_array().into_iter().flatten() {
        if strings(&row["governed_by"]).is_empty() {
            continue;
        }
        let mut relation = instructions.clone();
        let mut source = row.clone();
        source["reconcile"] = row["governed_by"].clone();
        // Governance is an explicit relation, not an inversion of read.
        source["relation_kind"] = json!("governed-scope");
        relation["sources"] = json!([source]);
        relations.push((
            row["source"]["reference"].as_str().unwrap().to_owned(),
            relation,
        ));
    }
    if relations.is_empty() {
        return relation_view(
            target,
            work,
            (instructions, &observations),
            configuration,
            contract,
            request,
            context,
        );
    }
    let selected_id = request.and_then(|r| r["arguments"]["relation_id"].as_str());
    let mut outputs = Vec::new();
    let mut selected = None;
    for (id, mut relation) in relations {
        relation["relation_id"] = json!(id);
        let current_request = request.filter(|_| selected_id.unwrap_or("canonical-sources") == id);
        let mut output = relation_view(
            target,
            work,
            (&relation, &observations),
            configuration,
            contract,
            current_request,
            Context {
                executing: context.executing && current_request.is_some(),
                ..context
            },
        )?;
        output["relation_id"] = json!(id);
        if current_request.is_some() {
            selected = Some(outputs.len());
        }
        outputs.push(output);
    }
    if request.is_some() && selected.is_none() {
        return Err(err("source relation is no longer applicable"));
    }
    let index = selected.unwrap_or_else(|| {
        outputs
            .iter()
            .position(|v| v["status"] != "current")
            .unwrap_or(0)
    });
    let mut output = outputs[index].clone();
    if output["status"] == "current" && outputs.iter().any(|v| v["status"] != "current") {
        output["status"] = json!("partial");
    }
    output["relations"] = json!(outputs.iter().map(|v|json!({"relation_id":v["relation_id"],"status":v["status"],"coverage":v["coverage"],"obligations":v["obligations"]})).collect::<Vec<_>>());
    Ok(output)
}

fn relation_view(
    target: &Path,
    work: &Value,
    inputs: (&Value, &RefCell<BTreeMap<String, Value>>),
    configuration: &Value,
    contract: &Value,
    request: Option<&Value>,
    context: Context<'_>,
) -> Result<Value, CoreError> {
    let (instructions, observations) = inputs;
    let subject = context.subject;
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
            sources.insert(source.clone(), observe(&root, source, observations)?);
        }
        for dependency in strings(&row["read"]) {
            dependencies.insert(
                dependency.clone(),
                observe(&root, &dependency, observations)?,
            );
        }
        // Admission is checked afresh; its transport (for example a Git
        // commit pointer) is not semantic evidence. The exact declaration
        // content below binds its requirements and authority.
        declarations.push(json!({"source":row["source"],"admission":{"status":row["binding_admission"]["status"]},"relation_kind":row["relation_kind"],"sources":refs,"paths":row["metadata"]["paths"]}));
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
        postimages.insert(path.clone(), observe(&root, &path, observations)?);
    }
    let binding = json!({"semantics":SEMANTICS,"relation_id":instructions["relation_id"],"subject":subject,"declarations":declarations,
        "sources":sources,"dependencies":dependencies,"work_postimages":postimages});
    // Retained semantic judgment is valid only under its actual producer as
    // well as current sources. No old receipt can survive an implementation
    // change merely because its repository dependencies stayed unchanged.
    let mut binding = binding;
    static PRODUCER: std::sync::LazyLock<String> = std::sync::LazyLock::new(|| {
        digest(&json!([
            include_str!("native_source_reconciliation.rs"),
            include_str!("../../dependency_binding.rs"),
            include_str!("../../current_projection.rs"),
            include_str!("../../native_decision_authority.rs")
        ]))
        .unwrap()
    });
    binding["producer_revision"] = json!(&*PRODUCER);
    let mut judgment_paths: Vec<String> = sources.keys().cloned().collect();
    judgment_paths.extend(postimages.keys().cloned());
    judgment_paths.sort();
    judgment_paths.dedup();
    if let Some(mut authority) =
        crate::native_decision_authority::delegated(configuration, "verification", &judgment_paths)
    {
        // Only the matching grant determines retained judgment authority.
        // Fresh requests/actions still bind the aggregate capability contract.
        authority.as_object_mut().unwrap().remove("policy_revision");
        binding["decision_authority"] = authority;
    }
    grouped_view(
        Inputs {
            target,
            work,
            instructions,
            observations,
            configuration,
            contract,
        },
        request,
        context,
        binding,
    )
}

#[derive(Clone, Copy)]
struct Inputs<'a> {
    target: &'a Path,
    work: &'a Value,
    instructions: &'a Value,
    observations: &'a RefCell<BTreeMap<String, Value>>,
    configuration: &'a Value,
    contract: &'a Value,
}

// Only this owner-local current projection is operational. Historical immutable
// receipts are never enumerated. Absence grants no coverage; malformed or missing
// referenced evidence is an explicit gap, not a reason to resurrect history.
pub(crate) fn projection_path(binding: &Value) -> Result<String, CoreError> {
    Ok(format!(
        ".agentic-workspace/proof/current/source-reconciliation-{}.json",
        &digest(&binding["relation_id"])?[7..]
    ))
}
fn current_groups(root: &Dir, binding: &Value) -> Result<Vec<String>, CoreError> {
    let Some(value) = crate::current_projection::read(root, &projection_path(binding)?)? else {
        return Ok(Vec::new());
    };
    let paths: Vec<String> = serde_json::from_value(value).map_err(err)?;
    if paths.len() > 4096 || paths.iter().collect::<BTreeSet<_>>().len() != paths.len() {
        return Err(err("invalid bounded current reconciliation projection"));
    }
    for path in &paths {
        if !path.starts_with(".agentic-workspace/proof/receipts/source-reconciliation-")
            || !path.ends_with(".json")
        {
            return Err(err("invalid current reconciliation reference"));
        }
        crate::decision_source::relative(path)?;
    }
    Ok(paths)
}
fn publish_group(root: &Dir, target: &Path, binding: &Value, path: &str) -> Result<(), CoreError> {
    let mut paths = Vec::new();
    let observations = RefCell::new(BTreeMap::new());
    for old_path in current_groups(root, binding)? {
        let bytes = native_planning::read(root, &old_path)?
            .or(native_planning::read(root, &format!("{old_path}.tmp"))?)
            .ok_or_else(|| err("current reconciliation receipt unavailable"))?;
        let record: Value = serde_json::from_slice(&bytes).map_err(err)?;
        let old = &record["invocation"]["arguments"]["binding"];
        retained(target, &old_path, old)?
            .ok_or_else(|| err("current reconciliation custody unavailable"))?;
        let group = old["work_postimages"]
            .as_object()
            .ok_or_else(|| err("invalid current group"))?;
        let mut projected = binding.clone();
        projected["work_postimages"] = Value::Object(
            group
                .keys()
                .map(|key| Ok((key.clone(), observe(root, key, &observations)?)))
                .collect::<Result<_, CoreError>>()?,
        );
        // A new source/policy basis supersedes all old groups. An overlapping
        // group supersedes the whole prior judgment, never individual subjects.
        if same_basis(&projected, old)?
            && !group
                .keys()
                .any(|key| binding["work_postimages"].get(key).is_some())
        {
            paths.push(old_path);
        }
    }
    paths.push(path.to_owned());
    if paths.len() > 4096 {
        return Err(err(
            "current reconciliation projection exceeds subject bound",
        ));
    }
    crate::current_projection::write(root, &projection_path(binding)?, &json!(paths))
}

fn grouped_view(
    inputs: Inputs<'_>,
    request: Option<&Value>,
    context: Context<'_>,
    binding: Value,
) -> Result<Value, CoreError> {
    let Inputs { target, .. } = inputs;
    let root = Dir::open_ambient_dir(target, ambient_authority()).map_err(err)?;
    let all = binding["work_postimages"].as_object().unwrap();
    let membership = digest(&json!(all.keys().collect::<Vec<_>>()))?;
    let mut uncovered: BTreeSet<String> = all.keys().cloned().collect();
    let mut evidence = Vec::new();
    let mut selected = None;
    for path in current_groups(&root, &binding)? {
        let bytes = native_planning::read(&root, &path)?
            .or(native_planning::read(&root, &format!("{path}.tmp"))?)
            .ok_or_else(|| err("current reconciliation receipt unavailable"))?;
        let record: Value = serde_json::from_slice(&bytes).map_err(err)?;
        let old = &record["invocation"]["arguments"]["binding"];
        let group = old["work_postimages"]
            .as_object()
            .ok_or_else(|| err("invalid current group"))?;
        let mut projected = binding.clone();
        projected["work_postimages"] = Value::Object(
            group
                .keys()
                .filter_map(|key| all.get(key).map(|v| (key.clone(), v.clone())))
                .collect(),
        );
        if !same_basis(&projected, old)? {
            continue;
        }
        let prior = retained(target, &path, old)?;
        if request
            .is_some_and(|r| r["arguments"]["binding_revision"] == digest(old).unwrap_or_default())
        {
            selected = Some(old.clone());
        }
        if let Some(prior) = prior.filter(|p| p["committed"] == true && p["published"] == true) {
            for key in group.keys() {
                uncovered.remove(key);
            }
            evidence.push(prior["value"].clone());
        }
    }
    let total = all.len();
    let covered = total - uncovered.len();
    let mut group = binding.clone();
    group["work_postimages"] = Value::Object(
        uncovered
            .iter()
            .take(GROUP_SIZE)
            .map(|key| (key.clone(), all[key].clone()))
            .collect(),
    );
    if let Some(selected) = selected {
        group = selected;
    }
    let mut output = if uncovered.is_empty()
        && !evidence.is_empty()
        && request.is_none()
        && !context.executing
    {
        json!({"status":"current","obligations":binding["sources"].as_object().unwrap().keys().collect::<Vec<_>>(),"requests":[],"action":null,"decisions":[],"evidence":evidence[0]})
    } else {
        group_view(inputs, request, context, group, &membership)?
    };
    if output["status"] == "current" && !uncovered.is_empty() {
        output["status"] = json!("partial");
    }
    output["coverage"] = json!({"status":if uncovered.is_empty() && !evidence.is_empty(){"current"}else if covered>0{"partial"}else{"unassessed"},"total":total,"accepted":covered,"pending":uncovered.len(),"membership_revision":membership,"complete_enumeration":true,"group_limit":GROUP_SIZE,"accepted_groups":evidence.len()});
    Ok(output)
}

// Domain adapters supply observations and conclusion metadata to the common
// comparison; accepted publication custody is checked separately by retained.
fn same_basis(current: &Value, accepted: &Value) -> Result<bool, CoreError> {
    use crate::dependency_binding::{Basis, Currentness, Observation, Scheme};
    let adapt = |value: &Value| -> Result<_, CoreError> {
        let mut identity = value.clone();
        let mut dependencies = Vec::new();
        for field in ["sources", "dependencies", "work_postimages"] {
            for (path, observation) in value[field]
                .as_object()
                .ok_or_else(|| err("invalid dependency basis"))?
            {
                dependencies.push(Observation {
                    identity: format!("{field}:{path}"),
                    scheme: Scheme::RawBytes,
                    revision: observation["revision"].as_str().map(str::to_owned),
                    status: if observation["status"] == "present" {
                        Currentness::Current
                    } else {
                        Currentness::Missing
                    },
                });
            }
            identity.as_object_mut().unwrap().remove(field);
        }
        Ok((identity, dependencies))
    };
    let (current_identity, current_observations) = adapt(current)?;
    let (accepted_identity, accepted_observations) = adapt(accepted)?;
    Ok(crate::dependency_binding::compare(
        Basis {
            conclusion: &current_identity,
            dependencies: &current_observations,
        },
        Some(Basis {
            conclusion: &accepted_identity,
            dependencies: &accepted_observations,
        }),
    )
    .status
        == Currentness::Current)
}

fn group_view(
    inputs: Inputs<'_>,
    request: Option<&Value>,
    context: Context<'_>,
    binding: Value,
    membership: &str,
) -> Result<Value, CoreError> {
    let Inputs {
        target,
        work,
        instructions,
        observations,
        configuration,
        contract,
    } = inputs;
    let Context { subject, executing } = context;
    let sources = binding["sources"].as_object().unwrap();
    let mut view = json!({"status":"unassessed","obligations":sources.keys().collect::<Vec<_>>(),"requests":[],"action":null,"decisions":[]});
    let revision = digest(&binding)?;
    let source_revision = digest(&json!([revision, membership]))?;
    view["source_revision"] = json!(source_revision);
    let path = format!(
        ".agentic-workspace/proof/receipts/source-reconciliation-{}.json",
        &revision[7..]
    );
    let issued = json!({"kind":"agentic-workspace/public-request/v1","owner":"verification","id":REQUEST,"request_kind":REQUEST,
        "owner_revision":contract["owners"].as_array().unwrap().iter().find(|o|o["owner"]=="verification").unwrap()["revision"],
        "source_revision":source_revision,"capability_revision":contract["revision"],"task_identity":work,
        "arguments":{"relation_id":binding["relation_id"],"binding_revision":revision,"judgments":{}}});
    let mut material_request = issued.clone();
    material_request["arguments"]["read_references"] = json!(
        sources
            .keys()
            .chain(binding["work_postimages"].as_object().unwrap().keys())
            .take(16)
            .collect::<BTreeSet<_>>()
    );
    view["material_request"] = material_request;
    if let Some(request) = request.filter(|r| r["arguments"]["read_references"].is_array()) {
        crate::prepare_request_value(
            json!({"request":request,"current_work":work,"capability_contract":contract}),
        )?;
        let mut expected = issued.clone();
        expected["arguments"] = request["arguments"].clone();
        if *request != expected
            || request["arguments"]["binding_revision"] != revision
            || request["arguments"]["judgments"] != json!({})
        {
            return Err(err(
                "source material request is stale or differs from the exact owner request",
            ));
        }
        let root = Dir::open_ambient_dir(target, ambient_authority()).map_err(err)?;
        let mut material = Vec::new();
        let mut size = 0;
        for reference in strings(&request["arguments"]["read_references"]) {
            let observation = sources
                .get(&reference)
                .or_else(|| binding["work_postimages"].get(&reference))
                .ok_or_else(|| err("material outside current group"))?;
            let bytes = crate::dependency_binding::read(&root, &reference)?
                .ok_or_else(|| err("group material disappeared"))?;
            size += bytes.len();
            if size > crate::decision_source::MAX_SOURCE_BYTES {
                return Err(err(
                    "group material exceeds bounded read; select fewer references",
                ));
            }
            if observation["revision"]
                != crate::dependency_binding::revision(
                    &bytes,
                    crate::dependency_binding::Scheme::RawBytes,
                )?
            {
                return Err(err("group material changed during read"));
            }
            material.push(json!({"reference":reference,"revision":observation["revision"],"text":String::from_utf8(bytes).map_err(err)?}));
        }
        view["status"] = json!("judgment-material-required");
        view["requests"] = json!([issued]);
        view["proposal"] = binding;
        view["material"] = json!(material);
        return Ok(view);
    }
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
    if request.is_none()
        && !executing
        && let Some(prior) = prior
            .as_ref()
            .filter(|p| p["committed"] == true && p["published"] == true)
    {
        view["status"] = json!("current");
        view["evidence"] = prior["value"].clone();
        view["receipt_ref"] = json!(path);
        return Ok(view);
    }
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
            "assessment_semantics":assessment_semantics(&binding),
            "completion_authority":false,"semantic_truth":"judgment-not-mechanically-proven"});
        let proposal_revision = digest(&proposal)?;
        view["proposal"] = proposal;
        let arguments = json!({"relation_id":binding["relation_id"],"binding_revision":revision,"judgments":judgments,"proposal_revision":proposal_revision});
        let decisions = json!([{"id":"source-reconciliation","question":"Authorize publication of this caller-proposed source assessment for this exact group? This does not attest personal source review or independently approve the work.",
                "material":view["proposal"],
                "response_request":{"request_kind":REQUEST,"arguments":arguments},
                "choices":[{"id":"confirm","label":"Authorize this exact proposal for this group"},{"id":"defer","label":"Do not publish; leave this group unresolved"}],"affects":["claim:complete"]}]);
        if request["arguments"]["answer"].is_null() {
            if request["id"] != REQUEST {
                return Err(err(
                    "judgment material must use the issued material request",
                ));
            }
            if binding.get("decision_authority").is_some() {
                let compiled = crate::compile_value(
                    json!({"intent":{"current_work":work},"capability_contract":contract,"contributions":[{"owner":"verification","revision":source_revision,"decisions":decisions}]}),
                )?;
                let mut authorized =
                    compiled["pending_consequences"]["decisions"][0]["response_request"].clone();
                authorized["arguments"]["answer"] = json!("confirm");
                return relation_view(
                    target,
                    work,
                    (instructions, observations),
                    configuration,
                    contract,
                    Some(&authorized),
                    Context { subject, executing },
                );
            }
            view["status"] = json!("bounded-human-answer-required");
            view["decisions"] = decisions;
            return Ok(view);
        }
        let compiled = crate::compile_value(
            json!({"intent":{"current_work":work},"capability_contract":contract,
            "contributions":[{"owner":"verification","revision":source_revision,"decisions":decisions}]}),
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
    publish_group(&root, target, binding, path)?;
    let committed = crate::attempt_store::commit(
        json!({"target":target,"custody":admission["custody"],"outcome":outcome}),
    )?;
    Ok(json!({"outcome":outcome,"custody":committed["custody"],"post_effect_changed_paths":[path]}))
}
