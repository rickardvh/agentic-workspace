//! Confined immutable publication for admitted independent owners. The carrier
//! preserves exact existing attempt custody across process interruption.
use crate::{CoreError, attempt_store, digest};
use cap_std::{
    ambient_authority,
    fs::{Dir, OpenOptions},
};
use serde_json::{Value, json};
use std::{io::Write, path::Path};

fn err(value: impl ToString) -> CoreError {
    CoreError::new(value.to_string())
}
fn read(root: &Dir, path: &str) -> Result<Option<Vec<u8>>, CoreError> {
    crate::native_planning::read(root, path)
}
fn destination(invocation: &Value) -> Result<&str, CoreError> {
    let owner = invocation["source_owner"]
        .as_str()
        .ok_or_else(|| err("Independent publication owner missing"))?;
    let path = invocation["arguments"]["publication"]["path"]
        .as_str()
        .ok_or_else(|| err("Independent publication destination missing"))?;
    crate::decision_source::relative(path)?;
    let prefix = format!(".agentic-workspace/modules/{owner}/");
    let leaf = path
        .strip_prefix(&prefix)
        .ok_or_else(|| err("Independent publication cannot mutate foreign owner state"))?;
    if leaf.contains('/') || !leaf.ends_with(".json") {
        return Err(err("Independent publication must be one owned source"));
    }
    Ok(path)
}
fn outcome(invocation: &Value) -> Value {
    json!({"status":"applied","effects":invocation["effects"],"value":invocation["arguments"]["value"]})
}
fn carrier(invocation: &Value, custody: &Value) -> Value {
    json!({"kind":"agentic-workspace/independent-publication/v1","publication":invocation["arguments"]["publication"],"invocation":invocation,"custody":custody})
}
fn bytes(invocation: &Value, custody: &Value) -> Result<Vec<u8>, CoreError> {
    let bytes = serde_json::to_vec(&carrier(invocation, custody)).map_err(err)?;
    if bytes.len() > crate::decision_source::MAX_SOURCE_BYTES {
        return Err(err(
            "Independent publication carrier exceeds bounded source size",
        ));
    }
    Ok(bytes)
}
fn retained(target: &Path, root: &Dir, invocation: &Value) -> Result<Option<Value>, CoreError> {
    let published = read(root, destination(invocation)?)?;
    let temporary = format!(
        "{}.{}.tmp",
        destination(invocation)?,
        &digest(invocation)?[7..]
    );
    let raw = match &published {
        Some(raw) => raw.clone(),
        None => match read(root, &temporary)? {
            Some(raw) => raw,
            None => return Ok(None),
        },
    };
    let body: Value = serde_json::from_slice(&raw).map_err(|_| {
        err("Unrecognized independent source preserved; exact owner custody required")
    })?;
    if body["invocation"] != *invocation
        || body["kind"] != "agentic-workspace/independent-publication/v1"
    {
        return Err(err(
            "Existing independent destination belongs to a different proposal or owner; preserved",
        ));
    }
    let prepared = attempt_store::prepare_commit(
        target.to_str().unwrap(),
        body["custody"].clone(),
        outcome(invocation),
    )?;
    if prepared["record"]["invocation"] != *invocation
        || prepared["custody"] != body["custody"]
        || bytes(invocation, &prepared["custody"])? != raw
    {
        return Err(err(
            "Independent publication differs from exact admitted attempt; preserved",
        ));
    }
    let committed =
        attempt_store::inspect_committed(target.to_str().unwrap(), body["custody"].clone()).is_ok();
    Ok(Some(
        json!({"custody":body["custody"],"committed":committed,"published":published.is_some()}),
    ))
}
pub(crate) fn write_scope(action: &Value) -> Result<Vec<String>, CoreError> {
    if action["arguments"]["publication"].is_null() {
        return Ok(vec![]);
    }
    let path = destination(action)?.to_owned();
    let mut writes = attempt_store::write_paths(
        &json!({"idempotency_key":action.get("idempotency_key").unwrap_or(&action["logical_effect_id"])}),
    )?;
    writes.extend([
        path.clone(),
        format!("{path}.*.tmp"),
        format!("{}.lock", path.trim_end_matches(".json")),
    ]);
    Ok(writes)
}
pub(crate) fn execute(
    target: &Path,
    decision: &Value,
    invocation: &Value,
    mut revalidate: impl FnMut() -> Result<(), CoreError>,
) -> Result<Value, CoreError> {
    if invocation["arguments"]["publication"].is_null() {
        revalidate()?;
        if !invocation["effects"].as_array().is_some_and(Vec::is_empty) {
            return Err(err("Read-only independent result advertises effects"));
        }
        return Ok(
            json!({"outcome":{"status":"unchanged","effects":[],"value":invocation["arguments"]["value"]},"custody":null}),
        );
    }
    // Bound the full carrier before opening a lock or admitting any effect.
    let allowance = json!({"attempt":{"target":target,"path":"x".repeat(160),"owner":invocation["source_owner"],"revision":"x".repeat(71)},"committed":{"target":target,"path":"x".repeat(160),"owner":invocation["source_owner"],"revision":"x".repeat(71)}});
    bytes(invocation, &allowance)?;
    let root = Dir::open_ambient_dir(target, ambient_authority()).map_err(err)?;
    let path = destination(invocation)?;
    let parent = path.rsplit_once('/').unwrap().0;
    read(&root, path)?;
    root.create_dir_all(parent).map_err(err)?;
    let lock_path = format!("{}.lock", path.trim_end_matches(".json"));
    if read(&root, &lock_path)?.is_some_and(|bytes| !bytes.is_empty()) {
        return Err(err("Foreign independent publication lock preserved"));
    }
    let lock = root
        .open_with(
            &lock_path,
            OpenOptions::new().read(true).write(true).create(true),
        )
        .map_err(err)?
        .into_std();
    lock.try_lock().map_err(err)?;
    revalidate()?;
    let previous = retained(target, &root, invocation)?;
    if previous.as_ref().is_some_and(|p| p["committed"] == true) {
        if previous.as_ref().unwrap()["published"] != true {
            return Err(err(
                "Committed independent publication disappeared; retained evidence preserved; an owner restoration decision is required",
            ));
        }
        return Ok(
            json!({"outcome":outcome(invocation),"custody":previous.unwrap()["custody"],
            "post_effect_changed_paths":[invocation["arguments"]["publication"]["path"]]}),
        );
    }
    let mut custody = match &previous {
        Some(previous) => previous["custody"].clone(),
        None => attempt_store::admit(
            json!({"target":target,"decision":decision,"invocation":invocation}),
        )?["custody"]
            .clone(),
    };
    let prepared = attempt_store::prepare_commit(
        target.to_str().unwrap(),
        custody.clone(),
        outcome(invocation),
    )?;
    let raw = bytes(invocation, &prepared["custody"])?;
    if previous
        .as_ref()
        .is_none_or(|previous| previous["published"] != true)
    {
        let temporary = format!("{path}.{}.tmp", &digest(invocation)?[7..]);
        // An interrupted prepared carrier may be reused only after exact custody
        // admission. No recognisable filename or client label acquires custody.
        if previous.is_none() {
            let mut file = root
                .open_with(&temporary, OpenOptions::new().write(true).create_new(true))
                .map_err(err)?;
            file.write_all(&raw).map_err(err)?;
            file.sync_all().map_err(err)?;
            drop(file);
        } else if read(&root, &temporary)?.as_deref() != Some(raw.as_slice()) {
            return Err(err("Independent prepared publication changed; preserved"));
        }
        revalidate()?;
        read(&root, path)?;
        root.hard_link(&temporary, &root, path).map_err(err)?;
    }
    if previous.is_some() {
        custody["committed"] = Value::Null;
    }
    revalidate()?;
    if read(&root, path)?.as_deref() != Some(raw.as_slice()) {
        return Err(err(
            "Independent publication changed before finalization; preserved",
        ));
    }
    let committed = attempt_store::commit(
        json!({"target":target,"custody":custody,"outcome":outcome(invocation)}),
    )?;
    Ok(
        json!({"outcome":outcome(invocation),"custody":committed["custody"],
        "post_effect_changed_paths":[invocation["arguments"]["publication"]["path"]]}),
    )
}
