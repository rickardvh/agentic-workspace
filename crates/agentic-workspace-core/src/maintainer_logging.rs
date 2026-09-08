//! Failure-isolated native transport diagnostics. Never a semantic input.
use crate::{CoreError, native_config};
use cap_std::{
    ambient_authority,
    fs::{Dir, OpenOptions},
};
use rsa::rand_core::{OsRng, RngCore};
use serde_json::{Value, json};
use sha2::{Digest, Sha256};
use std::{
    io::{Read, Write},
    path::Path,
    time::SystemTime,
};

const ROOT: &str = ".agentic-workspace/local/session-logging";
const REGISTRY: &str = ".agentic-workspace/local/session-logging/sessions.json";
const LOCAL_SCHEMA: &str = include_str!(
    "../../../src/agentic_workspace/contracts/schemas/workspace_local_override.schema.json"
);
const LIMIT: u64 = 1_048_576;

pub fn policy(input: Value) -> Result<Value, CoreError> {
    let declaration: Value = serde_json::from_str(include_str!(
        "../../../src/agentic_workspace/contracts/schemas/source_decision_input.schema.json"
    ))
    .unwrap();
    crate::schema_validator(
        &json!({"$schema": declaration["$schema"], "$defs":declaration["$defs"], "$ref":"#/$defs/session_logging_policy_input"}),
        "logging policy",
    )?
    .validate(&input)
    .map_err(|e| CoreError::new(e.to_string()))?;
    let schema: Value = serde_json::from_str(LOCAL_SCHEMA).unwrap();
    crate::schema_validator(&schema, "logging local configuration")?
        .validate(&input["local"])
        .map_err(|e| CoreError::new(e.to_string()))?;
    let settings = &input["local"]["session_logging"];
    let mode =
        settings["path_mode"]
            .as_str()
            .unwrap_or(if settings["redact_local_paths"] == true {
                "redacted"
            } else {
                "absolute"
            });
    Ok(
        json!({"enabled":settings["enabled"] == true && input["disable_override"] != "1", "path_mode":mode}),
    )
}
fn trim_identity(value: &str) -> &str {
    value.trim_matches(|c: char| c.is_whitespace() || ('\u{1c}'..='\u{1f}').contains(&c))
}
fn related_identity(salt: &str, variable: &str, prefix: &str) -> String {
    let value = std::env::var(variable).unwrap_or_default();
    let value = trim_identity(&value);
    if value.is_empty() || value.len() > 8192 {
        return String::new();
    }
    format!(
        "{prefix}-{}",
        &hash(format!("{salt}\0{value}").as_bytes())[..24]
    )
}
fn hash(bytes: &[u8]) -> String {
    format!("{:x}", Sha256::digest(bytes))
}
fn measure(value: &Value) -> Result<(u64, String), String> {
    struct Counter {
        hash: Sha256,
        bytes: u64,
    }
    impl Write for Counter {
        fn write(&mut self, bytes: &[u8]) -> std::io::Result<usize> {
            self.hash.update(bytes);
            self.bytes = self.bytes.saturating_add(bytes.len() as u64);
            Ok(bytes.len())
        }
        fn flush(&mut self) -> std::io::Result<()> {
            Ok(())
        }
    }
    let mut output = Counter {
        hash: Sha256::new(),
        bytes: 0,
    };
    serde_json::to_writer(&mut output, value).map_err(|e| e.to_string())?;
    Ok((output.bytes, format!("{:x}", output.hash.finalize())))
}
fn now() -> String {
    chrono::DateTime::<chrono::Utc>::from(SystemTime::now()).to_rfc3339()
}
fn random() -> Result<String, String> {
    let mut bytes = [0u8; 16];
    OsRng
        .try_fill_bytes(&mut bytes)
        .map_err(|e| e.to_string())?;
    Ok(hash(&bytes)[..32].to_owned())
}
fn safe(root: &Dir, path: &str) -> Result<(), String> {
    let mut current = std::path::PathBuf::new();
    for part in Path::new(path).components() {
        if !matches!(part, std::path::Component::Normal(_)) {
            return Err("invalid diagnostic path".into());
        }
        current.push(part);
        match root.symlink_metadata(&current) {
            Ok(m) => {
                #[cfg(windows)]
                let linked = {
                    use cap_std::fs::MetadataExt;
                    m.file_attributes() & 0x400 != 0
                };
                #[cfg(not(windows))]
                let linked = m.is_symlink();
                if linked {
                    return Err("linked diagnostic path".into());
                }
            }
            Err(e) if e.kind() == std::io::ErrorKind::NotFound => {}
            Err(e) => return Err(e.to_string()),
        }
    }
    Ok(())
}
fn dirs(root: &Dir, path: &str) -> Result<(), String> {
    safe(root, path)?;
    root.create_dir_all(path).map_err(|e| e.to_string())
}
fn read(root: &Dir, path: &str) -> Result<Option<Vec<u8>>, String> {
    safe(root, path)?;
    let mut file = match root.open(path) {
        Ok(f) => f,
        Err(e) if e.kind() == std::io::ErrorKind::NotFound => return Ok(None),
        Err(e) => return Err(e.to_string()),
    };
    let mut bytes = Vec::new();
    std::io::Read::by_ref(&mut file)
        .take(LIMIT + 1)
        .read_to_end(&mut bytes)
        .map_err(|e| e.to_string())?;
    if bytes.len() as u64 > LIMIT {
        return Err("diagnostic read bound".into());
    }
    Ok(Some(bytes))
}
fn create(root: &Dir, path: &str, bytes: &[u8]) -> Result<(), String> {
    safe(root, path)?;
    root.open_with(path, OpenOptions::new().write(true).create_new(true))
        .and_then(|mut f| f.write_all(bytes))
        .map_err(|e| e.to_string())
}
struct Lock<'a> {
    root: &'a Dir,
    path: String,
}
impl Drop for Lock<'_> {
    fn drop(&mut self) {
        let _ = self.root.remove_dir(&self.path);
    }
}
fn lock<'a>(root: &'a Dir, path: String) -> Result<Lock<'a>, String> {
    safe(root, &path)?;
    root.create_dir(&path).map_err(|e| e.to_string())?;
    Ok(Lock { root, path })
}

const CUSTODY: &str = "native_registration_custody";
const PUBLICATION_LOCK: &str = ".agentic-workspace/local/session-logging/.native-publication.lock";

fn publication_lock(root: &Dir) -> Result<std::fs::File, String> {
    // Bridge the historical directory lock only while establishing the stable
    // process lock. Retained Python writers refuse this native carrier.
    let entry = lock(root, format!("{ROOT}/.sessions.lock"))?;
    safe(root, PUBLICATION_LOCK)?;
    let file = root
        .open_with(
            PUBLICATION_LOCK,
            OpenOptions::new().write(true).create(true),
        )
        .map_err(|e| e.to_string())?
        .into_std();
    file.try_lock().map_err(|e| e.to_string())?;
    drop(entry);
    Ok(file)
}
fn body_revision(registry: &Value) -> Result<String, String> {
    let mut body = registry.clone();
    body.as_object_mut()
        .ok_or("invalid registry")?
        .remove(CUSTODY);
    Ok(hash(&serde_json::to_vec(&body).map_err(|e| e.to_string())?))
}
fn registration_invocation(target: &str, previous: &Value, desired: &str) -> Value {
    let effect = hash(format!("{target}\0{previous}").as_bytes());
    json!({"kind":"agentic-workspace/operation-invocation/v1", "operation_id":"session-logging.register",
        "operation_revision":"native-session-registration/v1", "source_owner":"session-logging",
        "idempotency_key":effect,"arguments":{"target":target,"previous_revision":previous,"registry_revision":desired},
        "effects":["local-session-registration"]})
}
fn registration_outcome(revision: &str) -> Value {
    json!({"status":"applied","effects":["local-session-registration"],"value":{"registry_revision":revision}})
}
fn admit_registry(target: &str, registry: &Value) -> Result<(), String> {
    let retained = &registry[CUSTODY];
    let revision = body_revision(registry)?;
    let invocation = registration_invocation(
        target,
        &retained["invocation"]["arguments"]["previous_revision"],
        &revision,
    );
    if retained["kind"] != "agentic-workspace/session-registration-custody/v1"
        || retained["invocation"] != invocation
    {
        return Err("registry has no exact native publication custody".into());
    }
    let outcome = registration_outcome(&revision);
    let planned =
        crate::attempt_store::prepare_commit(target, retained["custody"].clone(), outcome.clone())
            .map_err(|e| e.to_string())?;
    if planned["custody"] != retained["custody"] || planned["record"]["invocation"] != invocation {
        return Err("registry differs from retained publication".into());
    }
    // Exact published bytes can finish the immutable commit after interruption.
    // Missing or conflicting prepublication state cannot reach this point.
    if crate::attempt_store::inspect_committed(target, retained["custody"].clone()).is_err() {
        let mut pending = retained["custody"].clone();
        pending["committed"] = Value::Null;
        let committed = crate::attempt_store::commit(
            json!({"target":target,"custody":pending,"outcome":outcome}),
        )
        .map_err(|e| e.to_string())?;
        if committed["custody"] != retained["custody"] {
            return Err("publication commit mismatch".into());
        }
    }
    Ok(())
}
fn publish_registry(
    root: &Dir,
    target: &str,
    previous: Option<&[u8]>,
    registry: &mut Value,
    session: &Value,
) -> Result<(), String> {
    let previous_revision = previous
        .map(|bytes| json!(hash(bytes)))
        .unwrap_or(Value::Null);
    let revision = body_revision(registry)?;
    let invocation = registration_invocation(target, &previous_revision, &revision);
    let admission = crate::attempt_store::admit(
        json!({"target":target,"decision":{"ready_actions":[invocation]},"invocation":invocation}),
    )
    .map_err(|e| e.to_string())?;
    registration_stage("admitted");
    let outcome = registration_outcome(&revision);
    let planned =
        crate::attempt_store::prepare_commit(target, admission["custody"].clone(), outcome.clone())
            .map_err(|e| e.to_string())?;
    registry[CUSTODY] = json!({"kind":"agentic-workspace/session-registration-custody/v1","invocation":invocation,"custody":planned["custody"]});
    let bytes = serde_json::to_vec(registry).map_err(|e| e.to_string())?;
    if bytes.len() > LIMIT as usize {
        return Err("registry publication bound".into());
    }
    let log = session["log_path"].as_str().ok_or("session path absent")?;
    let folder = Path::new(log).parent().unwrap().to_str().unwrap();
    dirs(root, folder)?;
    create(
        root,
        log,
        b"# Native maintainer diagnostics\n\nCanonical events contain bounded metadata only.\n",
    )?;
    create(root,&format!("{folder}/index.json"),serde_json::to_string(&json!({"kind":"agentic-workspace/session-log-index/v2","session_id":session["session_id"],"log_path":log,"entries":[],"notes":[],"records":{},"local_only":true,"authoritative":false})).unwrap().as_bytes())?;
    if read(root, REGISTRY)?.as_deref() != previous {
        return Err("registry changed before publication".into());
    }
    match previous {
        None => create(root, REGISTRY, &bytes)?,
        Some(_) => {
            let temporary = format!(
                "{ROOT}/registration-{}.tmp",
                invocation["idempotency_key"].as_str().unwrap()
            );
            create(root, &temporary, &bytes)?;
            if read(root, REGISTRY)?.as_deref() != previous {
                return Err("registry changed before replacement; temporary preserved".into());
            }
            // All admitted native writers hold the stable OS owner lock;
            // historical writers refuse this carrier. No external-writer CAS is claimed.
            root.rename(&temporary, root, REGISTRY)
                .map_err(|e| e.to_string())?;
        }
    }
    registration_stage("published");
    crate::attempt_store::commit(
        json!({"target":target,"custody":admission["custody"],"outcome":outcome}),
    )
    .map_err(|e| e.to_string())?;
    Ok(())
}
fn registration_stage(_stage: &str) {
    #[cfg(test)]
    if std::env::var("AW_TEST_REGISTRATION_CRASH").ok().as_deref() == Some(_stage) {
        std::process::exit(73);
    }
}

/// Invoked only by the native executable's public transport, after resolution.
/// Errors are diagnostic omissions and cannot modify the operation result.
pub fn capture(request: &Value, result: &Result<Value, CoreError>, elapsed: std::time::Duration) {
    let _ = capture_inner(request, result, elapsed);
}
fn capture_inner(
    request: &Value,
    result: &Result<Value, CoreError>,
    elapsed: std::time::Duration,
) -> Result<(), String> {
    if std::env::var("AW_SESSION_LOGGING_DISABLE").ok().as_deref() == Some("1") {
        return Ok(());
    }
    let Some(object) = request.as_object().filter(|v| v.len() == 1) else {
        return Ok(());
    };
    let (operation, input) = object.iter().next().unwrap();
    if !matches!(operation.as_str(), "start" | "invoke") {
        return Ok(());
    }
    let identity = std::env::var("AW_SESSION_LOGICAL_IDENTITY").unwrap_or_default();
    if trim_identity(&identity).is_empty() || identity.len() > 8192 {
        return Ok(());
    }
    let target = input["target"].as_str().unwrap_or(".");
    let root = Dir::open_ambient_dir(target, ambient_authority()).map_err(|e| e.to_string())?;
    let Some((local, _)) =
        native_config::load(&root, ".agentic-workspace/config.local.toml", LOCAL_SCHEMA)?
    else {
        return Ok(());
    };
    let policy = policy(json!({"local":local,"disable_override":""})).map_err(|e| e.to_string())?;
    if policy["enabled"] != true {
        return Ok(());
    }
    dirs(&root, ROOT)?;
    let _registry_lock = publication_lock(&root)?;
    let canonical_target = std::fs::canonicalize(target)
        .map_err(|e| e.to_string())?
        .to_string_lossy()
        .into_owned();
    let existing = read(&root, REGISTRY)?;
    let mut registry = match &existing {
        Some(bytes) => serde_json::from_slice::<Value>(bytes).map_err(|_| "invalid registry")?,
        None => {
            json!({"kind":"agentic-workspace/session-logging-registry/v1","salt":random()?,"sessions":{},"logical_sessions":{},"updated_at":now(),"local_only":true,"authoritative":false})
        }
    };
    if registry["kind"] != "agentic-workspace/session-logging-registry/v1"
        || registry["salt"]
            .as_str()
            .is_none_or(|v| v.is_empty() || v.len() > 128)
        || !registry["sessions"].is_object()
        || !registry["logical_sessions"].is_object()
    {
        return Err("unknown registry".into());
    }
    if existing.is_some() {
        admit_registry(&canonical_target, &registry)?;
    }
    let key = hash(
        format!(
            "{}\0{}",
            registry["salt"].as_str().unwrap(),
            trim_identity(&identity)
        )
        .as_bytes(),
    );
    let logical = format!("logical-{}", &key[..24]);
    let stream = format!("{ROOT}/logical-sessions/{logical}/events.jsonl");
    let session = if registry["sessions"][&key].is_null() {
        let parent = related_identity(
            registry["salt"].as_str().unwrap(),
            "AW_SESSION_LOG_PARENT_LOGICAL_IDENTITY",
            "logical",
        );
        let correlation = related_identity(
            registry["salt"].as_str().unwrap(),
            "AW_SESSION_LOG_CORRELATION_ID",
            "correlation",
        );
        let physical = format!("native-{}", random()?);
        let folder = format!(".agentic-workspace/local/logs/aw-session-{physical}");
        let log = format!("{folder}/session.md");
        let session = json!({"kind":"agentic-workspace/session-logging-record/v1","session_id":physical,"created_at":now(),"log_path":log,"logical_session_id":logical,"parent_logical_session_id":parent,"correlation_id":correlation,"prior_session_id":"","event_stream_path":stream});
        registry["sessions"][&key] = session.clone();
        registry["logical_sessions"][&key] = json!({"kind":"agentic-workspace/logical-session-record/v1","logical_session_id":logical,"parent_logical_session_id":parent,"correlation_id":correlation,"event_stream_path":stream,"sessions":[session],"created_at":now()});
        publish_registry(
            &root,
            &canonical_target,
            existing.as_deref(),
            &mut registry,
            &session,
        )?;
        session
    } else {
        let session = &registry["sessions"][&key];
        if session["kind"] != "agentic-workspace/session-logging-record/v1"
            || session["logical_session_id"] != logical
            || session["event_stream_path"] != stream
        {
            return Err("logical identity registration unavailable".into());
        }
        let physical = session["session_id"]
            .as_str()
            .ok_or("physical identity unavailable")?;
        if !physical
            .bytes()
            .all(|v| v.is_ascii_alphanumeric() || v == b'-')
        {
            return Err("invalid physical identity".into());
        }
        if session["log_path"]
            != format!(".agentic-workspace/local/logs/aw-session-{physical}/session.md")
        {
            return Err("invalid session path".into());
        }
        if read(&root, session["log_path"].as_str().unwrap())?.is_none() {
            return Err("session source absent".into());
        }
        session.clone()
    };
    drop(_registry_lock);
    let folder = Path::new(&stream).parent().unwrap().to_str().unwrap();
    dirs(&root, folder)?;
    let _stream_lock = lock(&root, format!("{folder}/.events.lock"))?;
    let bytes = read(&root, &stream)?.unwrap_or_default();
    if !bytes.is_empty() && !bytes.ends_with(b"\n") {
        return Err("torn event stream".into());
    }
    let mut sequence = 0u64;
    for line in bytes.split(|v| *v == b'\n').filter(|v| !v.is_empty()) {
        let event: Value = serde_json::from_slice(line).map_err(|_| "invalid stream")?;
        if event["kind"] != "agentic-workspace/session-log-event/v1"
            || event["logical_session_id"] != logical
        {
            return Err("unknown stream".into());
        }
        let next = event["sequence"].as_u64().ok_or("invalid sequence")?;
        if next <= sequence {
            return Err("non-monotonic stream".into());
        }
        sequence = next;
    }
    let result_measure = match result {
        Ok(value) => measure(value)?,
        Err(_) => (0, hash(b"")),
    };
    let input_measure = measure(request)?;
    let next_sequence = sequence.checked_add(1).ok_or("sequence bound")?;
    let timestamp = now();
    let id = format!("native-{}", random()?);
    let normalized_target = match policy["path_mode"].as_str() {
        Some("redacted") => "<target>".to_owned(),
        Some("repo-relative") => ".".to_owned(),
        _ => std::fs::canonicalize(target)
            .map_err(|e| e.to_string())?
            .display()
            .to_string(),
    };
    let entry = json!({"id":id,"timestamp":timestamp,"duration_ms":elapsed.as_millis().min(u64::MAX as u128) as u64,"command":format!("agentic-workspace {operation}"),"argv":[],"target":normalized_target,"exit_status":if result.is_ok(){0}else{2},"exit_class":if result.is_ok(){"success"}else{"failure"},"origin":{"classification":"unknown","source":"native-transport"},"output_bytes":result_measure.0,"output_digest":result_measure.1,"request_bytes":input_measure.0,"request_sha256":input_measure.1,"storage_mode":"metadata-only","omissions":["argv","task","operation arguments","result body","stdout/stderr","caller origin","process interruption before completion","unadmitted historical registry"],"path_mode":policy["path_mode"]});
    let event = json!({"kind":"agentic-workspace/session-log-event/v1","schema_version":1,"event_id":id,"event_type":"command.completed","timestamp":timestamp,"sequence":next_sequence,"logical_session_id":logical,"physical_session_id":session["session_id"],"parent_logical_session_id":session["parent_logical_session_id"],"correlation_id":session["correlation_id"],"payload":{"entry":entry},"local_only":true,"authoritative":false});
    let mut line = serde_json::to_vec(&event).unwrap();
    line.push(b'\n');
    if line.len() > 8192 || bytes.len() + line.len() > LIMIT as usize {
        return Err("event capture bound".into());
    }
    safe(&root, &stream)?;
    root.open_with(&stream, OpenOptions::new().append(true).create(true))
        .and_then(|mut f| f.write_all(&line))
        .map_err(|e| e.to_string())
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn registration_child() {
        let Ok(target) = std::env::var("AW_TEST_REGISTRATION_TARGET") else {
            return;
        };
        capture(
            &json!({"start":{"target":target}}),
            &Ok(json!({"status":"direct"})),
            std::time::Duration::ZERO,
        );
    }
    #[test]
    fn registration_process_interruption_preserves_exact_publication() {
        for (stage, incumbent) in [
            ("admitted", false),
            ("published", false),
            ("admitted", true),
            ("published", true),
        ] {
            let repo = std::env::temp_dir().join(format!("aw-log-custody-{}", random().unwrap()));
            std::fs::create_dir(&repo).unwrap();
            std::fs::create_dir(repo.as_path().join(".agentic-workspace")).unwrap();
            std::fs::write(
                repo.as_path().join(".agentic-workspace/config.local.toml"),
                "schema_version=1\n[session_logging]\nenabled=true\npath_mode=\"redacted\"\n",
            )
            .unwrap();
            let run = |crash: &str, identity: &str| {
                std::process::Command::new(std::env::current_exe().unwrap())
                    .args([
                        "--exact",
                        "maintainer_logging::tests::registration_child",
                        "--nocapture",
                    ])
                    .env("AW_TEST_REGISTRATION_TARGET", repo.as_path())
                    .env("AW_TEST_REGISTRATION_CRASH", crash)
                    .env("AW_SESSION_LOGICAL_IDENTITY", identity)
                    .env_remove("AW_SESSION_LOGGING_DISABLE")
                    .output()
                    .unwrap()
            };
            if incumbent {
                assert!(run("", "incumbent").status.success());
            }
            let path = repo.as_path().join(REGISTRY);
            let prior = std::fs::read(&path).ok();
            assert_eq!(run(stage, "current-test-identity").status.code(), Some(73));
            let before = std::fs::read(&path).ok();
            assert!(run("", "current-test-identity").status.success());
            if stage == "admitted" {
                assert!(
                    std::fs::read(&path).ok() == prior,
                    "an unknown prepublication attempt cannot be retried"
                );
            } else {
                assert_eq!(std::fs::read(&path).unwrap(), before.unwrap());
                let registry: Value =
                    serde_json::from_slice(&std::fs::read(path).unwrap()).unwrap();
                let committed = registry[CUSTODY]["custody"]["committed"]["path"]
                    .as_str()
                    .unwrap();
                assert!(
                    repo.as_path().join(committed).exists(),
                    "exact published outcome finishes its commit"
                );
                let stream = registry["sessions"]
                    .as_object()
                    .unwrap()
                    .values()
                    .next()
                    .unwrap()["event_stream_path"]
                    .as_str()
                    .unwrap();
                assert_eq!(
                    std::fs::read_to_string(repo.as_path().join(stream))
                        .unwrap()
                        .lines()
                        .count(),
                    1
                );
            }
        }
    }
}
