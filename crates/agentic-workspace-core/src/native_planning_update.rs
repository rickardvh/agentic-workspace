//! Exact material replacement of a native-created Planning owner.
use crate::{CoreError, attempt_store, digest, prepare_request_value};
use serde_json::{Value, json};
use sha2::{Digest, Sha256};
use std::path::Path;
pub(crate) const KIND: &str = "planning/update/v1";
pub(crate) const PROVENANCE: &str = "update_provenance";
fn error(value: impl ToString) -> CoreError {
    CoreError::new(value.to_string())
}
fn schema() -> Value {
    crate::native_planning_create::canonical_schema()
}
fn fields() -> Vec<&'static str> {
    let mut fields = crate::native_planning_create::MATERIAL.to_vec();
    fields.extend(["lifecycle", "phase"]);
    fields
}
pub(crate) fn declaration() -> Value {
    let schema = schema();
    let fields = fields();
    let properties: serde_json::Map<String, Value> = fields
        .iter()
        .map(|k| (k.to_string(), schema["properties"][k].clone()))
        .collect();
    json!({"kind":KIND,"result_kind":"agentic-planning/update-result/v1","input_schema":{"$schema":schema["$schema"],"$defs":schema["$defs"],"type":"object","properties":{"owner_ref":{"type":"string"},"material":{"type":"object","properties":properties,"required":fields,"additionalProperties":false}},"required":["owner_ref","material"],"additionalProperties":false}})
}
pub(crate) fn operation() -> Value {
    json!({"id":"planning.update","semantic_revision":"planning-update-v1","input_schema":{"$schema":"https://json-schema.org/draft/2020-12/schema","type":"object","properties":{"target":{"type":"string"},"request":{"type":"object"},"owner_path":{"type":"string"},"prior_revision":{"type":"string"},"document":{"type":"object"},"planning_request":{"type":["object","null"]}},"required":["target","request","owner_path","prior_revision","document","planning_request"],"additionalProperties":false},"result_kind":"agentic-planning/update-result/v1","effects":["planning-state"],"reads":["planning"]})
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
    body[PROVENANCE] = json!({"kind":"agentic-planning/update-provenance/v1","invocation_revision":digest(invocation)?,"custody":custody,"outcome":outcome(invocation)?});
    Ok(body)
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
    let prepared = attempt_store::prepare_commit(
        target.to_str().ok_or_else(|| error("target encoding"))?,
        provenance["custody"].clone(),
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
    selected: &Value,
    request: Option<&Value>,
    invocation: Option<&Value>,
) -> Result<Value, CoreError> {
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
    if crate::native_planning_create::inspect_origin(target, reference, &body)?.is_none() {
        if effective.is_some() {
            return Err(error(
                "Planning update requires native creation custody; historical owner preserved",
            ));
        }
        return Ok(result);
    }
    let current_revision = revision(&bytes);
    result["requests"] = json!([{"kind":"agentic-workspace/public-request/v1","id":KIND,"owner":"planning","owner_revision":owner["revision"],"source_revision":current_revision,"capability_revision":contract["revision"],"task_identity":work,"request_kind":KIND,"arguments":{"owner_ref":reference}}]);
    let retained = inspect(target, reference, &body)?;
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
        result["action"] = json!({"operation_id":"planning.update","dependency_revision":digest(&json!({"source":current_revision,"document":document}))?,"arguments":{"target":target,"request":request,"owner_path":reference,"prior_revision":current_revision,"document":document,"planning_request":null},"effects":["planning-state"]});
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
    execute_checked(target, decision, invocation, retained, revalidate, |_| {
        Ok(())
    })
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
        crate::native_public::invoke(value)
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
        let select = request(target, created["value"]["selection_request"].clone());
        invoke(target, select["decision_packet"]["primary_action"].clone()).unwrap();
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
                assert_eq!(invoke(&target, recovered).unwrap()["status"], "applied");
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
                .contains("native creation custody")
        );
        assert_eq!(
            serde_json::from_slice::<Value>(&read(&target, &relative).unwrap()).unwrap(),
            historical
        );
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
