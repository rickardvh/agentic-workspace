//! Public creation of one current Planning owner. Caller owns material intent;
//! native custody is acquired only through exclusive creation, never shape.
use crate::{CoreError, digest, prepare_request_value};
use serde_json::{Value, json};
use std::path::Path;

const KIND: &str = "planning/create/v1";
const PROVENANCE: &str = "creation_provenance";
pub(crate) const MATERIAL: &[&str] = &[
    "title",
    "owner_level",
    "intent",
    "parent",
    "scope",
    "relationships",
    "next_action",
    "proof",
    "continuation",
    "canonical_core",
    "references",
    "blockers",
];
pub(crate) const ASSURANCE: &[&str] =
    &["adaptive_assurance", "risk_registry_refs", "invariant_refs"];
pub(crate) const OPTIONAL: &[&str] = &[
    crate::planning_lifetime::FIELD,
    crate::planning_lifetime::PROPOSAL,
];
fn error(message: impl ToString) -> CoreError {
    CoreError::new(message.to_string())
}
pub(crate) fn canonical_schema() -> Value {
    serde_json::from_str(include_str!("../../../packages/planning/bootstrap/.agentic-workspace/planning/schemas/planning-execplan.schema.json")).expect("canonical Planning schema")
}
pub(crate) fn declaration() -> Value {
    let canonical = canonical_schema();
    let mut required = MATERIAL.to_vec();
    required.push(crate::planning_lifetime::FIELD);
    let properties: serde_json::Map<String, Value> = MATERIAL
        .iter()
        .chain(ASSURANCE)
        .chain(OPTIONAL)
        .map(|key| ((*key).to_owned(), canonical["properties"][key].clone()))
        .collect();
    json!({"kind":KIND,"result_kind":"agentic-planning/creation-result/v1","input_schema":{
        "$schema":canonical["$schema"],"$defs":canonical["$defs"],"type":"object","properties":{"material":{"type":"object","properties":properties,"required":required,"additionalProperties":false}},"required":["material"],"additionalProperties":false}})
}
pub(crate) fn operation() -> Value {
    json!({"id":"planning.create","semantic_revision":"planning-create-v1","input_schema":{"$schema":"https://json-schema.org/draft/2020-12/schema","type":"object","properties":{"target":{"type":"string"},"request":{"type":"object"},"owner_path":{"type":"string"},"document":{"type":"object"},"planning_request":{"type":["object","null"]},"provenance_format":{"const":"repo-relative-v2"}},"required":["target","request","owner_path","document","planning_request"],"additionalProperties":false},"result_kind":"agentic-planning/creation-result/v1","effects":["planning-state"],"reads":["planning"]})
}
fn path(work: &Value) -> Result<(String, String), CoreError> {
    let id = format!("work-{}", &digest(work)?[7..]);
    Ok((
        format!(".agentic-workspace/planning/execplans/{id}.plan.json"),
        id,
    ))
}
fn read(target: &Path, path: &str) -> Result<Option<Vec<u8>>, CoreError> {
    let root =
        cap_std::fs::Dir::open_ambient_dir(target, cap_std::ambient_authority()).map_err(error)?;
    crate::native_planning::read(&root, path)
}
fn document(material: &Value, work: &Value) -> Result<Value, CoreError> {
    let mut document = crate::planning_lifetime::durable(material);
    let object = document
        .as_object_mut()
        .ok_or_else(|| error("Planning material must be an object"))?;
    object.insert("kind".into(), json!("planning-execplan/v1"));
    object.insert("id".into(), json!(path(work)?.1));
    object.insert("revision".into(), json!(1));
    object.insert("lifecycle".into(), json!("planned"));
    object.insert("phase".into(), json!("shaping"));
    crate::schema_validator(&canonical_schema(), "canonical Planning creation")?
        .validate(&document)
        .map_err(error)?;
    // New work cannot import an existing execution or proof disposition.
    if document["relationships"]
        .as_object()
        .is_some_and(|o| o.keys().any(|k| k != "dependencies"))
    {
        return Err(error(
            "Planning creation accepts declared dependencies, not execution/return authority",
        ));
    }
    Ok(document)
}
fn outcome(invocation: &Value) -> Result<Value, CoreError> {
    Ok(
        json!({"status":"applied","effects":["planning-state"],"value":{"owner_path":invocation["arguments"]["owner_path"],"owner_id":invocation["arguments"]["document"]["id"],"material_revision":digest(&invocation["arguments"]["document"])?}}),
    )
}
fn with_provenance(invocation: &Value, custody: &Value) -> Result<Value, CoreError> {
    let mut value = invocation["arguments"]["document"].clone();
    let portable = invocation["arguments"]["provenance_format"] == "repo-relative-v2";
    let mut custody = custody.clone();
    if portable {
        for field in ["attempt", "committed"] {
            custody[field]["target"] = json!(".");
        }
    }
    value[PROVENANCE] = json!({"kind":if portable {"agentic-planning/creation-provenance/v2"} else {"agentic-planning/creation-provenance/v1"},"invocation_revision":digest(invocation)?,"custody":custody});
    if portable {
        value[PROVENANCE]["material_revision"] =
            json!(digest(&invocation["arguments"]["document"])?);
    }
    Ok(value)
}
/// Portable observation is source meaning only. Reuse the exact effect-reference
/// envelope validation; never turn an absent local producer into writer custody.
pub(crate) fn portable_observation(relative: &str, body: &Value) -> Result<bool, CoreError> {
    portable_envelope(relative, body, true)
}
fn portable_envelope(relative: &str, body: &Value, current: bool) -> Result<bool, CoreError> {
    let provenance = &body[PROVENANCE];
    if provenance["kind"] != "agentic-planning/creation-provenance/v2" {
        return Ok(false);
    }
    if provenance.as_object().map(|v| v.len()) != Some(4) {
        return Err(error("invalid portable Planning creation observation"));
    }
    let mut document = body.clone();
    document.as_object_mut().unwrap().remove(PROVENANCE);
    let updated = !body[crate::native_planning_update::PROVENANCE].is_null();
    if current && updated && !crate::native_planning_update::portable_observation(relative, body)? {
        return Err(error(
            "portable Planning creation requires current update observation",
        ));
    }
    document[crate::native_planning_update::PROVENANCE] = json!({
        "kind":"agentic-planning/update-provenance/v2", "invocation_revision":provenance["invocation_revision"], "custody":provenance["custody"],
        "outcome":{"status":"applied","effects":["planning-state"],"value":{"owner_path":relative,"owner_id":body["id"],"document_revision":provenance["material_revision"]}}
    });
    crate::native_planning_update::portable_envelope(relative, &document, current && !updated)
}
/// Validate before treating creation provenance as nonsemantic or usable custody.
pub(crate) fn inspect_origin(
    target: &Path,
    relative: &str,
    body: &Value,
) -> Result<Option<Value>, CoreError> {
    let Some(provenance) = body.get(PROVENANCE) else {
        return Ok(None);
    };
    let mut custody = provenance["custody"].clone();
    if provenance["kind"] == "agentic-planning/creation-provenance/v2" {
        portable_envelope(relative, body, false)?;
        let root = cap_std::fs::Dir::open_ambient_dir(target, cap_std::ambient_authority())
            .map_err(error)?;
        let mut absent = 0;
        for field in ["attempt", "committed"] {
            if crate::native_planning::read(&root, custody[field]["path"].as_str().unwrap())?
                .is_none()
            {
                absent += 1;
            }
            custody[field]["target"] = json!(target);
        }
        if absent == 2 {
            portable_observation(relative, body)?;
            return Ok(None);
        }
    }
    let record = crate::attempt_store::inspect_committed(
        target.to_str().ok_or_else(|| error("target encoding"))?,
        custody.clone(),
    )
    .map_err(|_| {
        error("Planning creation outcome remains uncertain without exact committed custody")
    })?;
    let invocation = &record["invocation"];
    if !matches!(
        provenance["kind"].as_str(),
        Some("agentic-planning/creation-provenance/v1" | "agentic-planning/creation-provenance/v2")
    ) || provenance["invocation_revision"] != digest(invocation)?
        || invocation["source_owner"] != "planning"
        || invocation["operation_id"] != "planning.create"
        || invocation["arguments"]["owner_path"] != relative
    {
        return Err(error(
            "Planning creation provenance has the wrong owner or operation",
        ));
    }
    let current = std::fs::canonicalize(
        invocation["arguments"]["target"]
            .as_str()
            .ok_or_else(|| error("creation target missing"))?,
    )
    .map_err(error)?;
    if current != target {
        return Err(error("Planning creation provenance target mismatch"));
    }
    let prepared = crate::attempt_store::prepare_commit(
        target.to_str().ok_or_else(|| error("target encoding"))?,
        custody.clone(),
        outcome(invocation)?,
    )?;
    if prepared["custody"] != custody
        || with_provenance(invocation, &prepared["custody"])?[PROVENANCE] != *provenance
        || body["id"] != invocation["arguments"]["document"]["id"]
        || body["kind"] != "planning-execplan/v1"
    {
        return Err(error(
            "Planning creation source differs from exact producer payload",
        ));
    }
    if record["outcome"] != outcome(invocation)? {
        return Err(error("Planning creation outcome mismatch"));
    }
    crate::native_planning_update::inspect(target, relative, body)?;
    Ok(Some(
        json!({"invocation":invocation,"outcome":record["outcome"],"custody":prepared["custody"],
            "post_effect_changed_paths":[record["outcome"]["value"]["owner_path"]]}),
    ))
}
pub(crate) fn view(
    target: &Path,
    work: &Value,
    contract: &Value,
    request: Option<&Value>,
    invocation: Option<&Value>,
) -> Result<Value, CoreError> {
    let Some(owner) = contract["owners"]
        .as_array()
        .into_iter()
        .flatten()
        .find(|o| {
            o["owner"] == "planning"
                && o["requests"]
                    .as_array()
                    .is_some_and(|requests| requests.iter().any(|request| request["kind"] == KIND))
        })
    else {
        if request.is_some() || invocation.is_some() {
            return Err(error("Planning creation owner is not available"));
        }
        return Ok(json!({"requests":[],"committed_operation":null}));
    };
    let (relative, _) = path(work)?;
    let bytes = read(target, &relative)?;
    let revision = digest(
        &json!({"target":target,"path":relative,"current":bytes.as_ref().map(|b|digest(&json!(b))).transpose()?}),
    )?;
    let template = json!({"kind":"agentic-workspace/public-request/v1","id":KIND,"owner":"planning","owner_revision":owner["revision"],"source_revision":revision,"capability_revision":contract["revision"],"task_identity":work,"request_kind":KIND,"arguments":{}});
    let mut result = json!({"requests":[template],"contribution":{"owner":"planning","revision":revision,"settled":true},"committed_operation":null});
    if let Some(bytes) = bytes.as_ref()
        && let Ok(body) = serde_json::from_slice::<Value>(bytes)
        && body.get(PROVENANCE).is_some()
    {
        let Some(committed) = inspect_origin(target, &relative, &body)? else {
            if request.is_some() || invocation.is_some() {
                return Err(error(
                    "Planning creation local outcome unknown; reconcile source meaning instead of replaying creation",
                ));
            }
            result["created_owner"] = json!({"path":relative,"id":body["id"],"source_revision":revision,"status":"source-observation-local-outcome-unknown","claim_authority":false});
            result["requests"] = json!([]);
            return Ok(result);
        };
        result["created_owner"] = json!({"path":relative,"id":body["id"],"creation_material_revision":committed["outcome"]["value"]["material_revision"],"source_revision":revision});
        result["requests"] = json!([]);
        if let Some(invocation) = invocation {
            if with_provenance(&committed["invocation"], &committed["custody"])? != body
                || bytes != &serde_json::to_vec_pretty(&body).map_err(error)?
            {
                return Err(error(
                    "Planning creation snapshot is stale; preserve current owner revision",
                ));
            }
            if committed["invocation"] != *invocation {
                return Err(error(
                    "Planning creation collision belongs to another invocation",
                ));
            }
            result["committed_operation"] = committed;
            return Ok(result);
        }
    }
    let effective = request.or_else(|| invocation.and_then(|i| i["arguments"].get("request")));
    if let Some(request) = effective {
        prepare_request_value(
            json!({"request":request,"current_work":work,"capability_contract":contract}),
        )?;
        if request["source_revision"] != revision {
            return Err(error("Planning creation request is stale"));
        }
        if bytes.is_some() {
            return Err(error(
                "Planning creation path is occupied; existing source preserved",
            ));
        }
        let body = document(&request["arguments"]["material"], work)?;
        result["contribution"]["settled"] = json!(false);
        result["contribution"]["actions"] = json!([{"operation_id":"planning.create","dependency_revision":digest(&json!({"source":revision,"document":body}))?,"arguments":{"target":target,"request":request,"owner_path":relative,"document":body,"provenance_format":"repo-relative-v2"},"effects":["planning-state"]}]);
    }
    Ok(result)
}
pub(crate) fn execute(
    target: &Path,
    decision: &Value,
    invocation: &Value,
    mut revalidate: impl FnMut() -> Result<(), CoreError>,
) -> Result<Value, CoreError> {
    use std::io::Write;
    let target_string = target.to_str().ok_or_else(|| error("target encoding"))?;
    let admission = crate::attempt_store::admit(
        json!({"target":target_string,"decision":decision,"invocation":invocation}),
    )?;
    let outcome = outcome(invocation)?;
    let prepared = crate::attempt_store::prepare_commit(
        target_string,
        admission["custody"].clone(),
        outcome.clone(),
    )?;
    let body = with_provenance(invocation, &prepared["custody"])?;
    revalidate()?;
    let root =
        cap_std::fs::Dir::open_ambient_dir(target, cap_std::ambient_authority()).map_err(error)?;
    let relative = invocation["arguments"]["owner_path"]
        .as_str()
        .ok_or_else(|| error("owner path missing"))?;
    crate::decision_source::relative(relative)?;
    root.create_dir_all(".agentic-workspace/planning/execplans")
        .map_err(error)?;
    // Recheck the complete confined path after creating its bounded parents.
    if read(target, relative)?.is_some() {
        return Err(error(
            "Planning creation collision; existing source preserved",
        ));
    }
    let mut file = root
        .open_with(
            relative,
            cap_std::fs::OpenOptions::new().write(true).create_new(true),
        )
        .map_err(error)?;
    file.write_all(&serde_json::to_vec_pretty(&body).map_err(error)?)
        .map_err(error)?;
    file.sync_all().map_err(error)?;
    drop(file);
    let committed = crate::attempt_store::commit(
        json!({"target":target_string,"custody":admission["custody"],"outcome":outcome}),
    )?;
    let mut result = outcome;
    result["custody"] = committed["custody"].clone();
    result["post_effect_changed_paths"] = json!([result["value"]["owner_path"]]);
    Ok(result)
}

pub(crate) fn created_reference(target: &Path, work: &Value) -> Result<Option<String>, CoreError> {
    let relative = path(work)?.0;
    let Some(bytes) = read(target, &relative)? else {
        return Ok(None);
    };
    let body = serde_json::from_slice(&bytes).map_err(error)?;
    let local = inspect_origin(target, &relative, &body)?.is_some();
    Ok((local || portable_observation(&relative, &body)?).then_some(relative))
}
