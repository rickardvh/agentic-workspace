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
    let _registry_lock = lock(&root, format!("{ROOT}/.sessions.lock"))?;
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
    let session = if existing.is_none() {
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
        dirs(&root, &folder)?;
        create(&root,&log,b"# Native maintainer diagnostics\n\nCanonical events contain bounded metadata only; no task, argv or result bodies.\n")?;
        create(&root,&format!("{folder}/index.json"),serde_json::to_string(&json!({"kind":"agentic-workspace/session-log-index/v2","session_id":physical,"log_path":log,"entries":[],"notes":[],"records":{},"local_only":true,"authoritative":false})).unwrap().as_bytes())?;
        registry["sessions"][&key] = session.clone();
        registry["logical_sessions"][&key] = json!({"kind":"agentic-workspace/logical-session-record/v1","logical_session_id":logical,"parent_logical_session_id":parent,"correlation_id":correlation,"event_stream_path":stream,"sessions":[session],"created_at":now()});
        create(
            &root,
            REGISTRY,
            serde_json::to_string(&registry).unwrap().as_bytes(),
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
    let entry = json!({"id":id,"timestamp":timestamp,"duration_ms":elapsed.as_millis().min(u64::MAX as u128) as u64,"command":format!("agentic-workspace {operation}"),"argv":[],"target":normalized_target,"exit_status":if result.is_ok(){0}else{2},"exit_class":if result.is_ok(){"success"}else{"failure"},"origin":{"classification":"unknown","source":"native-transport"},"output_bytes":result_measure.0,"output_digest":result_measure.1,"request_bytes":input_measure.0,"request_sha256":input_measure.1,"storage_mode":"metadata-only","omissions":["argv","task","operation arguments","result body","stdout/stderr","caller origin","process interruption before completion","unregistered logical identities"],"path_mode":policy["path_mode"]});
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
