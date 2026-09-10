//! Exact material replacement under acquired Planning creation or reconciliation custody.
use crate::{CoreError, attempt_store, digest, prepare_request_value};
use serde_json::{Value, json};
use sha2::{Digest, Sha256};
use std::path::Path;
pub(crate) const KIND: &str = "planning/update/v1";
pub(crate) const ADOPT: &str = "planning/adopt-return/v1";
pub(crate) const RETAIN_HANDOFF: &str = "planning/retain-handoff/v1";
const HANDOFF: &str = "agentic-planning/handoff-continuation/v1";
const HANDOFF_SLOTS: [(&str, &str); 3] = [
    ("assignment", "attempt"),
    ("returned", "result"),
    ("integration_pending", "result"),
];
pub(crate) const RECOVER_KIND: &str = "planning/update-recovery/v1";
pub(crate) const PROVENANCE: &str = "update_provenance";
fn error(value: impl ToString) -> CoreError {
    CoreError::new(value.to_string())
}
fn schema() -> Value {
    crate::native_planning_create::canonical_schema()
}
fn fields() -> Vec<&'static str> {
    let mut fields = crate::native_planning_create::MATERIAL.to_vec();
    fields.retain(|field| *field != "canonical_core");
    fields.extend(["lifecycle", "phase"]);
    fields
}
const OPTIONAL_MATERIAL: &[&str] = &[
    "canonical_core",
    "goal",
    "non_goals",
    "intent_continuity",
    "execution_bounds",
    "touched_paths",
    "validation_commands",
    "completion_criteria",
    "stop_conditions",
    "required_continuation",
];
pub(crate) fn declaration() -> Value {
    let schema = schema();
    let fields = fields();
    let properties: serde_json::Map<String, Value> = fields
        .iter()
        .chain(crate::native_planning_create::ASSURANCE)
        .chain(OPTIONAL_MATERIAL)
        .map(|k| (k.to_string(), schema["properties"][k].clone()))
        .collect();
    json!({"kind":KIND,"result_kind":"agentic-planning/update-result/v1","input_schema":{"$schema":schema["$schema"],"$defs":schema["$defs"],"type":"object","properties":{"owner_ref":{"type":"string"},"material":{"type":"object","properties":properties,"required":fields,"additionalProperties":false}},"required":["owner_ref","material"],"additionalProperties":false}})
}
pub(crate) fn operation() -> Value {
    let mut operation = json!({"id":"planning.update","semantic_revision":"planning-update-v1","input_schema":{"$schema":"https://json-schema.org/draft/2020-12/schema","type":"object","properties":{"target":{"type":"string"},"request":{"type":"object"},"owner_path":{"type":"string"},"prior_revision":{"type":"string"},"document":{"type":"object"},"provenance_format":{"const":"repo-relative-v2"},"planning_request":{"type":["object","null"]}},"required":["target","request","owner_path","prior_revision","document","planning_request"],"additionalProperties":false},"result_kind":"agentic-planning/update-result/v1","effects":["planning-state"],"reads":["planning"]});
    operation["input_schema"]["properties"]["consumed_return"] = json!({"type":"object","properties":{"request":{"type":"object"},"result_revision":{"type":"string"},"judgment_revision":{"type":"string"},"assignment_identity":{"type":"object"},"execution_custody":{"type":"object"}},"required":["request","result_revision","judgment_revision","assignment_identity","execution_custody"],"additionalProperties":false});
    operation["input_schema"]["properties"]["consumed_return"]["properties"]["context"] =
        json!({"type":"object"});
    operation["input_schema"]["properties"]["consumed_return"]["properties"]["integration"] =
        crate::native_patch::result_schema();
    operation["input_schema"]["properties"]["retained_handoff"] = json!({"type":"object"});
    operation
}
pub(crate) fn adoption_declaration() -> Value {
    json!({"kind":ADOPT,"result_kind":"agentic-planning/update-result/v1","input_schema":{"$schema":"https://json-schema.org/draft/2020-12/schema","type":"object","properties":{"owner_ref":{"type":"string"},"destination":{"const":"continuation.frontier"}},"required":["owner_ref","destination"],"additionalProperties":false}})
}

pub(crate) fn handoff_declaration() -> Value {
    json!({"kind":RETAIN_HANDOFF,"result_kind":"agentic-planning/update-result/v1","input_schema":{"$schema":"https://json-schema.org/draft/2020-12/schema","type":"object","properties":{"owner_ref":{"type":"string"}},"required":["owner_ref"],"additionalProperties":false}})
}

fn update_material(body: &Value) -> Value {
    let mut material = serde_json::Map::new();
    for field in fields()
        .iter()
        .chain(crate::native_planning_create::ASSURANCE)
        .chain(OPTIONAL_MATERIAL)
    {
        if let Some(value) = body.get(*field) {
            material.insert((*field).to_owned(), value.clone());
        }
    }
    json!(material)
}

fn held_handoff(body: &Value) -> Option<&Value> {
    ["returned", "assignment"].iter().find_map(|field| {
        let key = if *field == "assignment" {
            "attempt"
        } else {
            "result"
        };
        let held = &body["relationships"][*field][key];
        (held["kind"] == HANDOFF).then_some(held)
    })
}

/// An observation-only update may preserve this exact earlier continuation.
/// A material edit, selector switch, foreign source, or different answer cannot.
pub(crate) fn retained_continuation_current(
    target: &Path,
    selected: &Value,
    request: &Value,
) -> Result<bool, CoreError> {
    if request["arguments"]["answer"] != "continue-selected" {
        return Ok(false);
    }
    let Some(reference) = selected["ref"].as_str() else {
        return Ok(false);
    };
    let body: Value = serde_json::from_slice(&read(target, reference)?).map_err(error)?;
    let Some(held) = held_handoff(&body) else {
        return Ok(false);
    };
    if held["owner_ref"] != reference
        || !held["reentry"]["request"]
            .as_array()
            .is_some_and(|rows| rows.contains(request))
    {
        return Ok(false);
    }
    let Some(retained) = inspect(target, reference, &body)? else {
        return Ok(false);
    };
    if retained["committed"] != true
        || payload(&retained["invocation"], &retained["custody"])? != body
    {
        return Ok(false);
    }
    let current = crate::planning::source_subject(target, &selected["source"])?;
    Ok(held["planning_subject"] == json!({"id":current["id"],"revision":current["revision"]}))
}

fn clear_handoff(document: &mut Value, assignment: &Value) {
    for (field, key) in HANDOFF_SLOTS {
        let Some(record) = document["relationships"].get_mut(field) else {
            continue;
        };
        if record[key]["kind"] == HANDOFF && record[key]["assignment_identity"] == *assignment {
            record.as_object_mut().unwrap().remove(key);
            record.as_object_mut().unwrap().remove("status");
            if record.as_object().unwrap().is_empty() {
                document["relationships"]
                    .as_object_mut()
                    .unwrap()
                    .remove(field);
            }
        }
    }
}

fn validate_document(document: &Value) -> Result<(), CoreError> {
    crate::schema_validator(&schema(), "Planning handoff postimage")?
        .validate(document)
        .map_err(error)?;
    if serde_json::to_vec_pretty(document)
        .map_err(error)?
        .len()
        .saturating_add(8192)
        > crate::decision_source::MAX_SOURCE_BYTES
    {
        return Err(error(
            "Planning postimage exceeds bounded source size; narrow retained handoff material",
        ));
    }
    Ok(())
}

/// Planning retains a route back to the responsible owners, not their authority.
/// Observations use existing attempt/result fields and do not redefine the subject.
pub(crate) fn retain_handoff(
    target: &Path,
    work: &Value,
    contract: &Value,
    planning: &Value,
    context: &Value,
    submitted: &[Value],
) -> Result<Value, CoreError> {
    let request = submitted
        .iter()
        .find(|r| r["request_kind"] == RETAIN_HANDOFF);
    let template = &planning["update_requests"][0];
    let mut result = json!({"requests":[],"action":null});
    let handoff = &context["handoff"];
    let observation = &context["delegation"]["observation"];
    if planning["status"] != "current"
        || !template.is_object()
        || !matches!(
            handoff["status"].as_str(),
            Some("exported-read-only" | "exported-patch" | "returned-unproven")
        )
    {
        if request.is_some() {
            return Err(error(
                "current selected Planning custody and sealed handoff required",
            ));
        }
        return Ok(result);
    }
    let reference = template["arguments"]["owner_ref"].as_str().unwrap();
    if planning["selected_owner"]["ref"] != reference {
        return Err(error(
            "handoff retention must use the selected Planning owner",
        ));
    }
    let prerequisites: Vec<_> = submitted
        .iter()
        .filter(|r| r["request_kind"] != RETAIN_HANDOFF)
        .cloned()
        .collect();
    if prerequisites.iter().any(|r| {
        [KIND, RECOVER_KIND, ADOPT]
            .iter()
            .any(|k| r["request_kind"] == *k)
    }) {
        if request.is_some() {
            return Err(error(
                "handoff retention conflicts with another Planning material request",
            ));
        }
        return Ok(result);
    }
    let assignment = &handoff["packet"]["assignment_identity"]["current_assignment"];
    let observed = observation["status"] == "current-executed-observation";
    if handoff["status"] == "returned-unproven" && !observed {
        if request.is_some() {
            return Err(error(
                "retaining returned work requires the current execution owner observation",
            ));
        }
        return Ok(result);
    }
    let status = if !observed {
        "assigned"
    } else if !observation["delta"].is_null()
        && context["admission"]["integration"]["status"] != "integrated"
    {
        "integration-pending"
    } else {
        "returned"
    };
    let held = json!({"kind":HANDOFF,"status":status,"assignment_identity":assignment,"owner_ref":reference,
        "planning_subject":{"id":context["planning_subject"]["id"],"revision":context["planning_subject"]["revision"]},
        "reentry":{"task":context["task"],"changed":context["changed"],"request":prerequisites},
        "execution_custody":observation["custody"],"returned_revision":if observed {json!(digest(&observation["returned"])?)} else {Value::Null},
        "authority_effect":"continuation-only; revalidate through responsible owners"});
    let body: Value = serde_json::from_slice(&read(target, reference)?).map_err(error)?;
    if let Some(previous) = held_handoff(&body) {
        if previous == &held {
            if request.is_some() {
                return Err(error(
                    "Planning handoff request is stale; this continuation is already retained",
                ));
            }
            return Ok(result);
        }
        if previous["assignment_identity"] != *assignment {
            if request.is_some() {
                return Err(error(
                    "another unresolved Planning handoff must be reconciled before replacement",
                ));
            }
            result["unresolved"] =
                json!("another retained handoff requires responsible-owner reconciliation");
            return Ok(result);
        }
        if previous["status"] != "assigned" && !observed {
            if request.is_some() {
                return Err(error("retained returned work cannot regress to assigned"));
            }
            return Ok(result);
        }
    }
    for (field, key) in HANDOFF_SLOTS {
        let prior = &body["relationships"][field][key];
        if prior["kind"] == HANDOFF && prior["assignment_identity"] != *assignment {
            if request.is_some() {
                return Err(error(
                    "another unresolved Planning handoff must be reconciled before replacement",
                ));
            }
            return Ok(result);
        }
    }
    let mut retention = template.clone();
    retention["id"] = json!(RETAIN_HANDOFF);
    retention["request_kind"] = json!(RETAIN_HANDOFF);
    retention["source_revision"] = json!(digest(&json!([template["source_revision"], held]))?);
    retention["arguments"] = json!({"owner_ref":reference});
    let mut requests = prerequisites;
    requests.push(retention.clone());
    result["requests"] = json!([requests]);
    let Some(request) = request else {
        return Ok(result);
    };
    prepare_request_value(
        json!({"request":request,"current_work":work,"capability_contract":contract}),
    )?;
    if *request != retention {
        return Err(error(
            "Planning handoff retention is stale or differs from the exact request",
        ));
    }
    let mut update = template.clone();
    update["arguments"]["material"] = update_material(&body);
    let mut action =
        view(target, work, contract, planning, Some(&update), None, None)?["action"].clone();
    if !action.is_object() {
        return Err(error("Planning did not admit handoff retention"));
    }
    clear_handoff(&mut action["arguments"]["document"], assignment);
    let relationships = &mut action["arguments"]["document"]["relationships"];
    let field = if observed { "returned" } else { "assignment" };
    let key = if observed { "result" } else { "attempt" };
    if relationships[field].is_null() {
        relationships[field] = json!({});
    }
    if !relationships[field].is_object() || relationships[field].get("status").is_some() {
        return Err(error("unknown Planning handoff observation preserved"));
    }
    if relationships[field]
        .get(key)
        .is_some_and(|old| !old.is_null() && old["kind"] != HANDOFF)
    {
        return Err(error("unknown Planning handoff observation preserved"));
    }
    relationships[field][key] = held.clone();
    relationships[field]["status"] = json!(status);
    if status == "integration-pending" {
        if relationships["integration_pending"].is_null() {
            relationships["integration_pending"] = json!({});
        }
        if !relationships["integration_pending"].is_object()
            || relationships["integration_pending"].get("status").is_some()
        {
            return Err(error("unknown Planning integration observation preserved"));
        }
        if relationships["integration_pending"]
            .get("result")
            .is_some_and(|old| !old.is_null() && old["kind"] != HANDOFF)
        {
            return Err(error("unknown Planning integration observation preserved"));
        }
        relationships["integration_pending"]["result"] =
            json!({"kind":HANDOFF,"assignment_identity":assignment});
        relationships["integration_pending"]["status"] = json!(status);
    }
    validate_document(&action["arguments"]["document"])?;
    action["dependency_revision"] = json!(digest(
        &json!({"source":action["arguments"]["prior_revision"],"document":action["arguments"]["document"]})
    )?);
    action["arguments"]["retained_handoff"] = held;
    action["source_requests"] = json!(submitted);
    result["action"] = action;
    Ok(result)
}

/// Consume the public Assignment admission. Only Planning reads/writes its own
/// material; the caller cannot substitute a worker result or widen this effect.
pub(crate) fn adopt_return(
    target: &Path,
    work: &Value,
    contract: &Value,
    planning: &Value,
    admission: &Value,
    submitted: &[Value],
) -> Result<Value, CoreError> {
    let request = submitted.iter().find(|r| r["request_kind"] == ADOPT);
    let mut result = json!({"requests":[],"action":null});
    let template = &planning["update_requests"][0];
    if admission["result_use_allowed"] != true
        || (!admission["delta"].is_null() && admission["integration"]["status"] != "integrated")
        || planning["status"] != "current"
        || !template.is_object()
    {
        if request.is_some() {
            return Err(error(
                "current selected Planning custody and admitted result required",
            ));
        }
        return Ok(result);
    }
    let reference = template["arguments"]["owner_ref"]
        .as_str()
        .ok_or_else(|| error("Planning adoption destination missing"))?;
    if planning["selected_owner"]["ref"] != reference {
        if request.is_some() {
            return Err(error("Planning adoption must use the selected owner"));
        }
        return Ok(result);
    }
    let mut adoption = template.clone();
    adoption["id"] = json!(ADOPT);
    adoption["request_kind"] = json!(ADOPT);
    adoption["source_revision"] = json!(digest(
        &json!({"owner":template["source_revision"],"admission":admission["source_revision"],"judgment":admission["judgment"],"integration":admission["integration"]})
    )?);
    adoption["arguments"] = json!({"owner_ref":reference,"destination":"continuation.frontier"});
    let mut prerequisites = submitted
        .iter()
        .filter(|r| r["request_kind"] != ADOPT)
        .cloned()
        .collect::<Vec<_>>();
    prerequisites.push(adoption.clone());
    result["requests"] = json!([prerequisites]);
    let Some(request) = request else {
        return Ok(result);
    };
    prepare_request_value(
        json!({"request":request,"current_work":work,"capability_contract":contract}),
    )?;
    if *request != adoption
        || submitted
            .iter()
            .any(|r| r["request_kind"] == KIND || r["request_kind"] == RECOVER_KIND)
    {
        return Err(error(
            "Planning return adoption is stale or conflicts with another material request",
        ));
    }
    let body: Value = serde_json::from_slice(&read(target, reference)?).map_err(error)?;
    let mut material = update_material(&body);
    if !material["continuation"].is_object() {
        return Err(error("Planning continuation is not an object"));
    }
    material["continuation"]["frontier"] = admission["returned"]["summary"].clone();
    let mut update = template.clone();
    update["arguments"]["material"] = material;
    let mut action =
        view(target, work, contract, planning, Some(&update), None, None)?["action"].clone();
    if !action.is_object() {
        return Err(error("Planning did not admit the bounded return update"));
    }
    clear_handoff(
        &mut action["arguments"]["document"],
        &admission["assignment_identity"],
    );
    validate_document(&action["arguments"]["document"])?;
    action["dependency_revision"] = json!(digest(
        &json!({"source":action["arguments"]["prior_revision"],"document":action["arguments"]["document"]})
    )?);
    action["arguments"]["consumed_return"] = json!({"request":adoption,"result_revision":digest(&admission["returned"])? ,"judgment_revision":admission["source_revision"],"assignment_identity":admission["assignment_identity"],"execution_custody":admission["execution_custody"]});
    action["arguments"]["consumed_return"]["context"] = admission["context"].clone();
    if !admission["integration"].is_null() {
        action["arguments"]["consumed_return"]["integration"] = admission["integration"].clone();
    }
    action["source_requests"] = json!(submitted);
    result["action"] = action;
    Ok(result)
}
pub(crate) fn recovery_declaration() -> Value {
    let canonical: Value = serde_json::from_str(include_str!(
        "../../../src/agentic_workspace/contracts/schemas/planning_reconciliation.schema.json"
    ))
    .expect("checked schema");
    let mut shape = canonical["$defs"]["update_recovery_request"].clone();
    shape["$schema"] = canonical["$schema"].clone();
    json!({"kind":RECOVER_KIND,"result_kind":"agentic-planning/update-recovery-result/v1","input_schema":shape})
}
pub(crate) fn recovery_operation() -> Value {
    json!({"id":"planning.update-recover","semantic_revision":"planning-update-recovery-v1","input_schema":{"$schema":"https://json-schema.org/draft/2020-12/schema","type":"object","properties":{"target":{"type":"string"},"request":{"type":"object"},"planning_request":{"type":"object"},"owner_path":{"type":"string"},"retained_invocation":{"type":"object"}},"required":["target","request","planning_request","owner_path","retained_invocation"],"additionalProperties":false},"result_kind":"agentic-planning/update-recovery-result/v1","effects":["planning-state"],"reads":["planning"]})
}
fn revision(bytes: &[u8]) -> String {
    format!("sha256:{:x}", Sha256::digest(bytes))
}
fn read(target: &Path, relative: &str) -> Result<Vec<u8>, CoreError> {
    let root =
        cap_std::fs::Dir::open_ambient_dir(target, cap_std::ambient_authority()).map_err(error)?;
    crate::native_planning::read(&root, relative)?
        .ok_or_else(|| error("Planning update owner missing"))
}
fn outcome(invocation: &Value) -> Result<Value, CoreError> {
    Ok(
        json!({"status":"applied","effects":["planning-state"],"value":{"owner_path":invocation["arguments"]["owner_path"],"owner_id":invocation["arguments"]["document"]["id"],"document_revision":digest(&invocation["arguments"]["document"])?}}),
    )
}
fn payload(invocation: &Value, custody: &Value) -> Result<Value, CoreError> {
    let mut body = invocation["arguments"]["document"].clone();
    let portable = invocation["arguments"]["provenance_format"] == "repo-relative-v2";
    let mut custody = custody.clone();
    if portable {
        for field in ["attempt", "committed"] {
            custody[field]["target"] = json!(".");
        }
    }
    body[PROVENANCE] = json!({"kind":if portable {"agentic-planning/update-provenance/v2"} else {"agentic-planning/update-provenance/v1"},"invocation_revision":digest(invocation)?,"custody":custody,"outcome":outcome(invocation)?});
    Ok(body)
}

/// A transported plan can preserve this observation without transporting local
/// producer authority. Missing local records never produce update custody.
pub(crate) fn portable_observation(relative: &str, body: &Value) -> Result<bool, CoreError> {
    portable_envelope(relative, body, true)
}
fn portable_envelope(
    relative: &str,
    body: &Value,
    current_material: bool,
) -> Result<bool, CoreError> {
    let provenance = &body[PROVENANCE];
    if provenance["kind"] != "agentic-planning/update-provenance/v2" {
        return Ok(false);
    }
    let valid_hash = |value: &Value| {
        value
            .as_str()
            .and_then(|s| s.strip_prefix("sha256:"))
            .is_some_and(|s| s.len() == 64 && s.bytes().all(|b| b.is_ascii_hexdigit()))
    };
    let mut document = body.clone();
    document
        .as_object_mut()
        .ok_or_else(|| error("invalid Planning document"))?
        .remove(PROVENANCE);
    let material_revision = if current_material {
        json!(digest(&document)?)
    } else {
        provenance["outcome"]["value"]["document_revision"].clone()
    };
    let expected = json!({"status":"applied","effects":["planning-state"],"value":{"owner_path":relative,"owner_id":body["id"],"document_revision":material_revision}});
    if provenance.as_object().map(|v| v.len()) != Some(4)
        || !valid_hash(&provenance["invocation_revision"])
        || !valid_hash(&material_revision)
        || provenance["outcome"] != expected
        || provenance["custody"].as_object().map(|v| v.len()) != Some(2)
    {
        return Err(error("invalid portable Planning update observation"));
    }
    let mut key = None;
    for (field, suffix) in [("attempt", ".attempt.json"), ("committed", ".result.json")] {
        let reference = &provenance["custody"][field];
        let path = reference["path"].as_str().unwrap_or("");
        let name = path
            .strip_prefix(".agentic-workspace/local/effects/")
            .and_then(|s| s.strip_suffix(suffix));
        if reference.as_object().map(|v| v.len()) != Some(4)
            || reference["target"] != "."
            || reference["owner"] != "planning"
            || !valid_hash(&reference["revision"])
            || !name.is_some_and(|s| s.len() == 64 && s.bytes().all(|b| b.is_ascii_hexdigit()))
            || key.is_some_and(|previous| Some(previous) != name)
        {
            return Err(error("invalid portable Planning custody reference"));
        }
        key = name;
    }
    Ok(true)
}
/// Validate the latest producer without mistaking its initial bytes for the
/// permanent material lifetime. Pending publication requires the exact postimage.
pub(crate) fn inspect(
    target: &Path,
    relative: &str,
    body: &Value,
) -> Result<Option<Value>, CoreError> {
    let Some(provenance) = body.get(PROVENANCE) else {
        return Ok(None);
    };
    let mut custody = provenance["custody"].clone();
    if provenance["kind"] == "agentic-planning/update-provenance/v2" {
        // Validate the envelope even when local custody exists. Material may
        // evolve after a committed write; only a source-only copy requires its
        // exact recorded material digest below.
        portable_envelope(relative, body, false)?;
        let root = cap_std::fs::Dir::open_ambient_dir(target, cap_std::ambient_authority())
            .map_err(error)?;
        let mut absent = 0;
        for field in ["attempt", "committed"] {
            let path = custody[field]["path"].as_str().unwrap();
            if crate::native_planning::read(&root, path)?.is_none() {
                absent += 1;
            }
            custody[field]["target"] = json!(
                std::fs::canonicalize(target)
                    .map_err(error)?
                    .to_string_lossy()
            );
        }
        if absent == 2 {
            portable_observation(relative, body)?;
            return Ok(None);
        }
    }
    let prepared = attempt_store::prepare_commit(
        target.to_str().ok_or_else(|| error("target encoding"))?,
        custody,
        provenance["outcome"].clone(),
    )?;
    let invocation = &prepared["record"]["invocation"];
    if invocation["source_owner"] != "planning"
        || invocation["operation_id"] != "planning.update"
        || invocation["arguments"]["owner_path"] != relative
        || invocation["arguments"]["document"]["id"] != body["id"]
        || invocation["arguments"]["document"]["creation_provenance"] != body["creation_provenance"]
        || payload(invocation, &prepared["custody"])?[PROVENANCE] != *provenance
    {
        return Err(error(
            "Planning update provenance does not belong to this exact native owner",
        ));
    }
    let committed =
        attempt_store::inspect_committed(target.to_str().unwrap(), prepared["custody"].clone())
            .is_ok();
    if !committed
        && (payload(invocation, &prepared["custody"])? != *body
            || read(target, relative)? != serde_json::to_vec_pretty(body).map_err(error)?)
    {
        return Err(error(
            "uncertain Planning update postimage changed; preserve it",
        ));
    }
    Ok(Some(
        json!({"invocation":invocation,"custody":prepared["custody"],"outcome":prepared["record"]["outcome"],"committed":committed}),
    ))
}
pub(crate) fn view(
    target: &Path,
    work: &Value,
    contract: &Value,
    planning: &Value,
    request: Option<&Value>,
    invocation: Option<&Value>,
    continuation: Option<&Value>,
) -> Result<Value, CoreError> {
    let selected = &planning["selected_owner"];
    let mut result = json!({"requests":[],"action":null,"retained":null});
    let owner = contract["owners"]
        .as_array()
        .into_iter()
        .flatten()
        .find(|o| {
            o["owner"] == "planning"
                && o["requests"]
                    .as_array()
                    .into_iter()
                    .flatten()
                    .any(|r| r["kind"] == KIND)
        });
    let Some(owner) = owner else {
        if request.is_some() || invocation.is_some() {
            return Err(error("Planning update owner unavailable"));
        }
        return Ok(result);
    };
    let effective = request.or_else(|| invocation.and_then(|i| i["arguments"].get("request")));
    let reference = effective
        .and_then(|r| r["arguments"]["owner_ref"].as_str())
        .or(selected["ref"].as_str());
    let Some(reference) = reference else {
        return Ok(result);
    };
    if !reference.starts_with(".agentic-workspace/planning/execplans/")
        || !reference.ends_with(".json")
    {
        return Err(error("Planning update outside canonical owner paths"));
    }
    let bytes = read(target, reference)?;
    let body: Value = serde_json::from_slice(&bytes).map_err(error)?;
    let origin = crate::native_planning_create::inspect_origin(target, reference, &body)?;
    let retained = inspect(target, reference, &body)?;
    let acquired = if origin.is_none() && selected["ref"] == reference {
        crate::native_planning::update_custody(target, reference)?.filter(|custody| {
            custody["source"] == selected["source"]
                || retained.as_ref().is_some_and(|r| {
                    payload(&r["invocation"], &r["custody"]).is_ok_and(|p| p == body)
                })
        })
    } else {
        None
    };
    if origin.is_none() && acquired.is_none() {
        if effective.is_some() {
            return Err(error(
                "Planning update requires acquired creation or reconciliation custody; historical owner preserved",
            ));
        }
        return Ok(result);
    }
    let current_revision = revision(&bytes);
    if planning["status"] == "current"
        && let Some(held) = held_handoff(&body)
    {
        result["handoff_continuation"] = json!({"status":"revalidation-required","retained":held,
            "authority_effect":"No execution, result-use, integration, proof or completion authority is renewed by retention."});
    }
    // Only this owner inspects its producer records. A transported observation,
    // pending publication or later material edit is not a current consumed result.
    if planning["status"] == "current"
        && let Some(retained) = &retained
        && retained["committed"] == true
        && retained["invocation"]["arguments"]["consumed_return"].is_object()
        && payload(&retained["invocation"], &retained["custody"])? == body
    {
        result["consumed_result"] = json!({"kind":"agentic-planning/consumed-result/v1","status":"current","owner_ref":reference,"source_revision":current_revision,"custody":retained["custody"],"consumption":retained["invocation"]["arguments"]["consumed_return"]});
    }
    result["requests"] = json!([{"kind":"agentic-workspace/public-request/v1","id":KIND,"owner":"planning","owner_revision":owner["revision"],"source_revision":current_revision,"capability_revision":contract["revision"],"task_identity":work,"request_kind":KIND,"arguments":{"owner_ref":reference}}]);
    let recovery_request = effective.filter(|r| r["request_kind"] == RECOVER_KIND);
    if let Some(retained) = &retained
        && (retained["committed"] != true || recovery_request.is_some())
    {
        let pending_revision = digest(&retained["invocation"])?;
        let mut template = result["requests"][0].clone();
        template["id"] = json!(RECOVER_KIND);
        template["request_kind"] = json!(RECOVER_KIND);
        template["arguments"] = json!({"owner_ref":reference,"pending_revision":pending_revision});
        result["recovery_requests"] = json!([template]);
        if let Some(request) = recovery_request {
            prepare_request_value(
                json!({"request":request,"current_work":work,"capability_contract":contract}),
            )?;
            let continuation = continuation.ok_or_else(|| {
                error("Planning recovery requires current continue-selected judgment")
            })?;
            if continuation["arguments"]["answer"] != "continue-selected"
                || !matches!(
                    planning["status"].as_str(),
                    Some("current" | "reentry-required")
                )
                || !planning["selection_transition"].is_null()
                || selected["ref"] != reference
                || request["source_revision"] != current_revision
                || request["arguments"]["pending_revision"] != pending_revision
                || payload(&retained["invocation"], &retained["custody"])? != body
                || bytes != serde_json::to_vec_pretty(&body).map_err(error)?
            {
                return Err(error(
                    "Planning recovery is stale or does not continue the exact selected owner",
                ));
            }
            prepare_request_value(
                json!({"request":continuation,"current_work":work,"capability_contract":contract}),
            )?;
            result["retained"] = retained.clone();
            result["action"] = json!({"operation_id":"planning.update-recover","dependency_revision":digest(&json!({"source":current_revision,"pending":pending_revision,"continuation":continuation}))?,"arguments":{"target":target,"request":request,"planning_request":continuation,"owner_path":reference,"retained_invocation":retained["invocation"]},"effects":["planning-state"]});
            return Ok(result);
        }
    }
    if let Some(invocation) = invocation
        && let Some(retained) = &retained
        && retained["invocation"] == *invocation
    {
        if payload(invocation, &retained["custody"])? != body
            || bytes != serde_json::to_vec_pretty(&body).map_err(error)?
        {
            return Err(error(
                "Planning update replay is stale; preserve current material",
            ));
        }
        prepare_request_value(
            json!({"request":invocation["arguments"]["request"],"current_work":work,"capability_contract":contract}),
        )?;
        result["retained"] = retained.clone();
        result["action"] = json!({"operation_id":"planning.update","dependency_revision":digest(&json!({"source":invocation["arguments"]["prior_revision"],"document":invocation["arguments"]["document"]}))?,"arguments":invocation["arguments"],"effects":["planning-state"]});
        return Ok(result);
    }
    if retained.as_ref().is_some_and(|r| r["committed"] != true) {
        if effective.is_some() {
            return Err(error(
                "Planning update outcome remains uncertain; resume its exact current invocation",
            ));
        }
        result["pending"] = json!(retained);
        result["requests"] = json!([]);
        return Ok(result);
    }
    if let Some(request) = effective {
        prepare_request_value(
            json!({"request":request,"current_work":work,"capability_contract":contract}),
        )?;
        if request["source_revision"] != current_revision {
            return Err(error("Planning update request is stale"));
        }
        let mut document = body.clone();
        document
            .as_object_mut()
            .ok_or_else(|| error("Planning owner must be an object"))?
            .remove(PROVENANCE);
        for key in fields() {
            document[key] = request["arguments"]["material"][key].clone();
        }
        for key in crate::native_planning_create::ASSURANCE
            .iter()
            .chain(OPTIONAL_MATERIAL)
        {
            if let Some(value) = request["arguments"]["material"].get(*key) {
                document[*key] = value.clone();
            }
        }
        // Current execution and returned authority may only be changed by those
        // owners. Material updates preserve their existing relationship records.
        let old_relationships = body["relationships"]
            .as_object()
            .ok_or_else(|| error("Planning relationships missing"))?;
        let new_relationships = document["relationships"]
            .as_object()
            .ok_or_else(|| error("Planning relationships missing"))?;
        for key in old_relationships
            .keys()
            .chain(new_relationships.keys())
            .filter(|k| k.as_str() != "dependencies")
        {
            if old_relationships.get(key) != new_relationships.get(key) {
                return Err(error(
                    "Planning update cannot manufacture execution or return authority",
                ));
            }
        }
        document["revision"] = json!(
            body["revision"]
                .as_u64()
                .ok_or_else(|| error("Planning revision missing"))?
                .checked_add(1)
                .ok_or_else(|| error("Planning revision overflow"))?
        );
        crate::schema_validator(&schema(), "canonical Planning update")?
            .validate(&document)
            .map_err(error)?;
        if document["lifecycle"] == "unknown" || document["phase"] == "unknown" {
            return Err(error(
                "Planning update needs an explicit supported frontier",
            ));
        }
        result["action"] = json!({"operation_id":"planning.update","dependency_revision":digest(&json!({"source":current_revision,"document":document}))?,"arguments":{"target":target,"request":request,"owner_path":reference,"prior_revision":current_revision,"document":document,"provenance_format":"repo-relative-v2","planning_request":null},"effects":["planning-state"]});
    }
    Ok(result)
}
pub(crate) fn execute(
    target: &Path,
    decision: &Value,
    invocation: &Value,
    retained: &Value,
    revalidate: impl FnMut() -> Result<(), CoreError>,
) -> Result<Value, CoreError> {
    let mut result = execute_checked(target, decision, invocation, retained, revalidate, |_| {
        Ok(())
    })?;
    result["post_effect_changed_paths"] = json!([result["value"]["owner_path"]]);
    Ok(result)
}
/// A current re-entry has its own admitted effect. It finalizes only the old
/// retained outcome, without replaying that operation's material mutation.
pub(crate) fn recover(
    target: &Path,
    decision: &Value,
    invocation: &Value,
    retained: &Value,
    revalidate: impl FnMut() -> Result<(), CoreError>,
) -> Result<Value, CoreError> {
    let mut result = recover_checked(target, decision, invocation, retained, revalidate, |_| {
        Ok(())
    })?;
    result["post_effect_changed_paths"] =
        json!([result["outcome"]["value"]["original_outcome"]["value"]["owner_path"]]);
    Ok(result)
}
fn recover_checked(
    target: &Path,
    decision: &Value,
    invocation: &Value,
    retained: &Value,
    mut revalidate: impl FnMut() -> Result<(), CoreError>,
    mut observe: impl FnMut(&str) -> Result<(), CoreError>,
) -> Result<Value, CoreError> {
    let root =
        cap_std::fs::Dir::open_ambient_dir(target, cap_std::ambient_authority()).map_err(error)?;
    let _lock = crate::native_planning::owner_lock(&root)?;
    revalidate()?;
    let relative = invocation["arguments"]["owner_path"]
        .as_str()
        .ok_or_else(|| error("recovery owner missing"))?;
    let bytes = read(target, relative)?;
    let body: Value = serde_json::from_slice(&bytes).map_err(error)?;
    let current = inspect(target, relative, &body)?
        .ok_or_else(|| error("recovery retained update missing"))?;
    if current != *retained
        || current["invocation"] != invocation["arguments"]["retained_invocation"]
        || payload(&current["invocation"], &current["custody"])? != body
        || bytes != serde_json::to_vec_pretty(&body).map_err(error)?
    {
        return Err(error("recovery retained postimage changed; preserve it"));
    }
    let admission =
        attempt_store::admit(json!({"target":target,"decision":decision,"invocation":invocation}))?;
    observe("recovery-admission")?;
    let mut original_custody = current["custody"].clone();
    if current["committed"] != true {
        original_custody["committed"] = Value::Null;
    }
    revalidate()?;
    if read(target, relative)? != bytes {
        return Err(error(
            "recovery postimage changed before commit; preserve it",
        ));
    }
    let original = attempt_store::commit(
        json!({"target":target,"custody":original_custody,"outcome":current["outcome"]}),
    )?;
    observe("original-finalization")?;
    let outcome = json!({"status":"applied","effects":["planning-state"],"value":{"status":"retained-update-finalized","original_invocation_revision":digest(&current["invocation"])?,"original_outcome":original["record"]["outcome"],"original_custody":original["custody"],"material_written":false}});
    let committed = attempt_store::commit(
        json!({"target":target,"custody":admission["custody"],"outcome":outcome}),
    )?;
    Ok(json!({"outcome":outcome,"custody":committed["custody"]}))
}
fn execute_checked(
    target: &Path,
    decision: &Value,
    invocation: &Value,
    retained: &Value,
    mut revalidate: impl FnMut() -> Result<(), CoreError>,
    mut observe: impl FnMut(&str) -> Result<(), CoreError>,
) -> Result<Value, CoreError> {
    use std::io::Write;
    validate_document(&invocation["arguments"]["document"])?;
    let root =
        cap_std::fs::Dir::open_ambient_dir(target, cap_std::ambient_authority()).map_err(error)?;
    let _lock = crate::native_planning::owner_lock(&root)?;
    revalidate()?;
    let mut custody = if retained.is_object() {
        retained["custody"].clone()
    } else {
        attempt_store::admit(json!({"target":target,"decision":decision,"invocation":invocation}))?
            ["custody"]
            .clone()
    };
    let outcome = outcome(invocation)?;
    let prepared =
        attempt_store::prepare_commit(target.to_str().unwrap(), custody.clone(), outcome.clone())?;
    observe("admission")?;
    let body = payload(invocation, &prepared["custody"])?;
    let relative = invocation["arguments"]["owner_path"]
        .as_str()
        .ok_or_else(|| error("owner path missing"))?;
    let bytes = serde_json::to_vec_pretty(&body).map_err(error)?;
    if bytes.len() > crate::decision_source::MAX_SOURCE_BYTES {
        return Err(error("Planning publication exceeds bounded source size"));
    }
    if read(target, relative)? != bytes {
        if revision(&read(target, relative)?) != invocation["arguments"]["prior_revision"] {
            return Err(error(
                "Planning update preimage changed; preserve current source",
            ));
        }
        let temporary = format!("{relative}.{}.tmp", &digest(invocation)?[7..]);
        let mut file = root
            .open_with(
                &temporary,
                cap_std::fs::OpenOptions::new().write(true).create_new(true),
            )
            .map_err(error)?;
        file.write_all(&bytes).map_err(error)?;
        file.sync_all().map_err(error)?;
        drop(file);
        revalidate()?;
        if revision(&read(target, relative)?) != invocation["arguments"]["prior_revision"] {
            return Err(error(
                "Planning update preimage changed; temporary preserved",
            ));
        }
        root.rename(&temporary, &root, relative).map_err(error)?;
    }
    observe("publication")?;
    if retained.is_object() && retained["committed"] != true {
        custody["committed"] = Value::Null;
    }
    let committed =
        attempt_store::commit(json!({"target":target,"custody":custody,"outcome":outcome}))?;
    let mut result = outcome;
    result["custody"] = committed["custody"].clone();
    Ok(result)
}

#[cfg(test)]
mod tests {
    use super::*;
    fn context(target: &Path) -> Value {
        json!({"target":target,"task":"Update current bounded native owner"})
    }
    fn start(target: &Path) -> Value {
        crate::native_public::start(context(target)).unwrap()
    }
    fn request(target: &Path, request: Value) -> Value {
        let mut value = context(target);
        value["request"] = request;
        crate::native_public::start(value).unwrap()
    }
    fn invoke(target: &Path, action: Value) -> Result<Value, CoreError> {
        let mut value = context(target);
        value["invocation"] = action;
        crate::native_public::invoke_checked(value)
    }
    fn material() -> Value {
        let source: Value = serde_json::from_str(include_str!(
            "../../../.agentic-workspace/planning/execplans/delegation-lane-sweep.plan.json"
        ))
        .unwrap();
        let mut value = json!({});
        for field in crate::native_planning_create::MATERIAL {
            value[*field] = source[*field].clone();
        }
        value["relationships"] = json!({"dependencies":{"refs":[]}});
        value
    }
    fn setup(target: &Path) -> String {
        let mut create = start(target)["planning"]["creation_requests"][0].clone();
        create["arguments"] = json!({"material":material()});
        let created = invoke(
            target,
            request(target, create)["decision_packet"]["primary_action"].clone(),
        )
        .unwrap();
        let mut selection_context = created["value"]["selection_context"].clone();
        selection_context["request"] = created["value"]["selection_request"].clone();
        let select = crate::native_public::start(selection_context.clone()).unwrap();
        selection_context.as_object_mut().unwrap().remove("request");
        selection_context["invocation"] = select["decision_packet"]["primary_action"].clone();
        crate::native_public::invoke_checked(selection_context).unwrap();
        created["value"]["owner_path"].as_str().unwrap().to_owned()
    }
    fn ready(target: &Path) -> Value {
        let mut update = start(target)["planning"]["update_requests"][0].clone();
        let mut material = material();
        material["lifecycle"] = json!("live");
        material["phase"] = json!("implementation");
        material["scope"] = json!({"allowed":"one exact revised component"});
        update["arguments"]["material"] = material;
        request(target, update)
    }
    #[test]
    #[ignore = "subprocess fixture"]
    fn update_process_child() {
        let target = std::path::PathBuf::from(std::env::var("AW_UPDATE_TEST_TARGET").unwrap());
        let boundary = std::env::var("AW_UPDATE_TEST_BOUNDARY").unwrap();
        let ready = ready(&target);
        let action = &ready["decision_packet"]["primary_action"];
        execute_checked(
            &target,
            &ready["decision_packet"],
            action,
            &Value::Null,
            || Ok(()),
            |phase| {
                if phase == boundary {
                    std::process::exit(77);
                }
                Ok(())
            },
        )
        .unwrap();
    }
    #[test]
    fn update_process_interruption_preserves_admission_uncertainty_and_recovers_postimage() {
        for boundary in ["admission", "publication", "publication-drift"] {
            let target = std::env::temp_dir().join(format!(
                "aw-update-{}-{}-{boundary}",
                std::process::id(),
                std::time::SystemTime::now()
                    .duration_since(std::time::UNIX_EPOCH)
                    .unwrap()
                    .as_nanos()
            ));
            std::fs::create_dir(&target).unwrap();
            let relative = setup(&target);
            let original = read(&target, &relative).unwrap();
            let action = ready(&target)["decision_packet"]["primary_action"].clone();
            let result = std::process::Command::new(std::env::current_exe().unwrap())
                .args([
                    "--exact",
                    "native_planning_update::tests::update_process_child",
                    "--ignored",
                    "--nocapture",
                ])
                .env("AW_UPDATE_TEST_TARGET", &target)
                .env(
                    "AW_UPDATE_TEST_BOUNDARY",
                    if boundary == "publication-drift" {
                        "publication"
                    } else {
                        boundary
                    },
                )
                .output()
                .unwrap();
            assert_eq!(
                result.status.code(),
                Some(77),
                "{}",
                String::from_utf8_lossy(&result.stderr)
            );
            if boundary == "admission" {
                assert_eq!(read(&target, &relative).unwrap(), original);
                assert!(
                    invoke(&target, action)
                        .unwrap_err()
                        .to_string()
                        .contains("existing effect evidence")
                );
                assert_eq!(read(&target, &relative).unwrap(), original);
            } else if boundary == "publication-drift" {
                let mut foreign = read(&target, &relative).unwrap();
                foreign.push(b' ');
                std::fs::write(target.join(&relative), &foreign).unwrap();
                assert!(
                    invoke(&target, action)
                        .unwrap_err()
                        .to_string()
                        .contains("postimage changed")
                );
                assert_eq!(read(&target, &relative).unwrap(), foreign);
            } else {
                let fresh = start(&target);
                let recovered = fresh["planning"]["pending_update"]["invocation"].clone();
                assert_eq!(recovered, action);
                assert_ne!(fresh["decision_packet"]["status"], "terminal");
                // A current continuation cannot rewrite the old task binding.
                // Recovery instead has its own current admitted action.
                let mut reworded = context(&target);
                reworded["task"] = json!("Continue this same bounded native owner update");
                let reentry = crate::native_public::start(reworded.clone()).unwrap();
                reworded["request"] = reentry["planning"]["requests"][0].clone();
                let continued = crate::native_public::start(reworded.clone()).unwrap();
                assert!(continued["planning"]["pending_update"].is_object());
                let current_bytes = read(&target, &relative).unwrap();
                reworded.as_object_mut().unwrap().remove("request");
                reworded["invocation"] = recovered.clone();
                assert!(crate::native_public::invoke_checked(reworded.clone()).is_err());
                assert_eq!(read(&target, &relative).unwrap(), current_bytes);
                reworded.as_object_mut().unwrap().remove("invocation");
                let continuation = reentry["planning"]["requests"][0].clone();
                let recovery = continued["planning"]["update_recovery_requests"][0].clone();
                let mut unrelated = continuation.clone();
                unrelated["arguments"]["answer"] = json!("unrelated-direct");
                reworded["request"] = json!([unrelated, recovery]);
                assert!(crate::native_public::start(reworded.clone()).is_err());
                reworded["request"] = json!([continuation, recovery]);
                let current = crate::native_public::start(reworded.clone()).unwrap();
                let recovery_action = current["decision_packet"]["primary_action"].clone();
                assert_eq!(recovery_action["operation_id"], "planning.update-recover");
                assert_ne!(
                    recovery_action["arguments"]["request"]["task_identity"],
                    recovered["arguments"]["request"]["task_identity"]
                );
                reworded.as_object_mut().unwrap().remove("request");
                reworded["invocation"] = recovery_action;
                // Exact material drift after action selection cannot be finalized.
                let mut drift = current_bytes.clone();
                drift.push(b' ');
                std::fs::write(target.join(&relative), &drift).unwrap();
                assert!(crate::native_public::invoke_checked(reworded.clone()).is_err());
                assert_eq!(read(&target, &relative).unwrap(), drift);
                std::fs::write(target.join(&relative), &current_bytes).unwrap();
                let result = crate::native_public::invoke_checked(reworded).unwrap();
                assert_eq!(result["status"], "applied");
                assert_eq!(result["value"]["material_written"], false);
                assert_eq!(
                    result["value"]["original_invocation_revision"],
                    digest(&recovered).unwrap()
                );
                assert_eq!(read(&target, &relative).unwrap(), current_bytes);
                assert_ne!(read(&target, &relative).unwrap(), original);
                assert_ne!(start(&target)["decision_packet"]["status"], "terminal");
            }
        }
    }
    #[test]
    fn update_preserves_drift_and_never_acquires_historical_source() {
        let target = std::env::temp_dir().join(format!(
            "aw-update-negatives-{}-{}",
            std::process::id(),
            std::time::SystemTime::now()
                .duration_since(std::time::UNIX_EPOCH)
                .unwrap()
                .as_nanos()
        ));
        std::fs::create_dir(&target).unwrap();
        let relative = setup(&target);
        let original = read(&target, &relative).unwrap();
        let ready = ready(&target);
        let action = ready["decision_packet"]["primary_action"].clone();
        let mut stale = original.clone();
        stale.push(b' ');
        std::fs::write(target.join(&relative), &stale).unwrap();
        assert!(invoke(&target, action.clone()).is_err());
        assert_eq!(read(&target, &relative).unwrap(), stale);
        std::fs::write(target.join(&relative), &original).unwrap();
        let mut forged = action.clone();
        forged["arguments"]["document"]["id"] = json!("another-owner");
        assert!(invoke(&target, forged).is_err());
        assert_eq!(read(&target, &relative).unwrap(), original);
        let mut historical: Value = serde_json::from_slice(&original).unwrap();
        historical
            .as_object_mut()
            .unwrap()
            .remove("creation_provenance");
        std::fs::write(
            target.join(&relative),
            serde_json::to_vec(&historical).unwrap(),
        )
        .unwrap();
        assert!(
            start(&target)["planning"]["update_requests"]
                .as_array()
                .unwrap()
                .is_empty()
        );
        assert!(
            invoke(&target, action)
                .unwrap_err()
                .to_string()
                .contains("acquired creation or reconciliation custody")
        );
        assert_eq!(
            serde_json::from_slice::<Value>(&read(&target, &relative).unwrap()).unwrap(),
            historical
        );
    }
    #[test]
    fn recovery_interruption_keeps_its_attempt_distinct_from_original_outcome() {
        for boundary in ["recovery-admission", "original-finalization"] {
            let target = std::env::temp_dir().join(format!(
                "aw-recovery-{}-{}-{boundary}",
                std::process::id(),
                std::time::SystemTime::now()
                    .duration_since(std::time::UNIX_EPOCH)
                    .unwrap()
                    .as_nanos()
            ));
            std::fs::create_dir(&target).unwrap();
            let relative = setup(&target);
            let ready = ready(&target);
            assert!(
                execute_checked(
                    &target,
                    &ready["decision_packet"],
                    &ready["decision_packet"]["primary_action"],
                    &Value::Null,
                    || Ok(()),
                    |phase| {
                        if phase == "publication" {
                            Err(error("interrupted original writer"))
                        } else {
                            Ok(())
                        }
                    }
                )
                .is_err()
            );
            let bytes = read(&target, &relative).unwrap();
            let mut context = context(&target);
            context["task"] = json!("Continue the same owner after interruption");
            let fresh = crate::native_public::start(context.clone()).unwrap();
            context["request"] = json!([
                fresh["planning"]["requests"][0],
                fresh["planning"]["update_recovery_requests"][0]
            ]);
            let recovery = crate::native_public::start(context.clone()).unwrap();
            let action = &recovery["decision_packet"]["primary_action"];
            let failed = recover_checked(
                &target,
                &recovery["decision_packet"],
                action,
                &recovery["planning"]["update_retained"],
                || Ok(()),
                |phase| {
                    if phase == boundary {
                        Err(error("interrupted recovery"))
                    } else {
                        Ok(())
                    }
                },
            );
            assert!(
                failed
                    .unwrap_err()
                    .to_string()
                    .contains("interrupted recovery")
            );
            assert_eq!(read(&target, &relative).unwrap(), bytes);
            let body: Value = serde_json::from_slice(&bytes).unwrap();
            let original = inspect(&target, &relative, &body).unwrap().unwrap();
            assert_eq!(original["committed"], boundary == "original-finalization");
            context.as_object_mut().unwrap().remove("request");
            context["invocation"] = action.clone();
            assert!(
                crate::native_public::invoke_checked(context)
                    .unwrap_err()
                    .to_string()
                    .contains("existing effect evidence")
            );
            assert_eq!(read(&target, &relative).unwrap(), bytes);
        }
    }
    #[test]
    fn update_final_revalidation_preserves_concurrent_material() {
        let target = std::env::temp_dir().join(format!(
            "aw-update-race-{}-{}",
            std::process::id(),
            std::time::SystemTime::now()
                .duration_since(std::time::UNIX_EPOCH)
                .unwrap()
                .as_nanos()
        ));
        std::fs::create_dir(&target).unwrap();
        let relative = setup(&target);
        let ready = ready(&target);
        let action = &ready["decision_packet"]["primary_action"];
        let mut calls = 0;
        let result = execute_checked(
            &target,
            &ready["decision_packet"],
            action,
            &Value::Null,
            || {
                calls += 1;
                if calls == 2 {
                    std::fs::write(target.join(&relative), b"foreign concurrent material").unwrap();
                }
                Ok(())
            },
            |_| Ok(()),
        );
        assert!(result.unwrap_err().to_string().contains("preimage changed"));
        assert_eq!(
            read(&target, &relative).unwrap(),
            b"foreign concurrent material"
        );
    }
}
