//! Failure-isolated native transport diagnostics. Never a semantic input.
use crate::CoreError;
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
const LOCAL_SCHEMA: &str =
    include_str!("../contracts/schemas/workspace_local_override.schema.json");
const LIMIT: u64 = 1_048_576;

pub fn policy(input: Value) -> Result<Value, CoreError> {
    let declaration: Value = serde_json::from_str(include_str!(
        "../contracts/schemas/source_decision_input.schema.json"
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
    let mode = settings["path_mode"].as_str().unwrap_or("absolute");
    let detail = settings["detail"].as_str().unwrap_or("full");
    Ok(
        json!({"enabled":settings["enabled"] == true && input["disable_override"] != "1", "path_mode":mode, "detail":detail}),
    )
}
pub(crate) fn effective_policy(target: &Path) -> Result<Value, CoreError> {
    let local = crate::native_assignment_policy::load(target)?.effective;
    policy(
        json!({"local":local,"disable_override":std::env::var("AW_SESSION_LOGGING_DISABLE").unwrap_or_default()}),
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

fn configuration_snapshot(effective: &Value) -> Value {
    let mut snapshot = json!({});
    // Ambient configuration is not command I/O. Retain only typed, closed
    // operating choices; paths, commands, extensible names and owner settings
    // may contain credentials even when their keys do not look sensitive.
    for (section, fields) in [
        ("workspace", &["enabled", "upstream_dogfooding"][..]),
        (
            "assurance",
            &[
                "agent_may_escalate",
                "agent_may_deescalate",
                "strict_closeout",
            ][..],
        ),
    ] {
        for field in fields {
            if let Some(value) = effective[section][*field].as_bool() {
                snapshot[section][*field] = json!(value);
            }
        }
    }
    let choices: &[(&str, &str, &[&str])] = &[
        (
            "workspace",
            "workflow_artifact_profile",
            &["repo-owned", "gemini"],
        ),
        (
            "workspace",
            "improvement_latitude",
            &["none", "reporting", "conservative", "proactive"],
        ),
        (
            "assurance",
            "default_level",
            &["low", "medium", "high", "critical"],
        ),
        (
            "payload",
            "policy",
            &["advisory", "required-before-claim", "required-before-work"],
        ),
        ("session_logging", "detail", &["full", "metadata"]),
        (
            "session_logging",
            "path_mode",
            &["absolute", "repo-relative", "redacted"],
        ),
        (
            "clarification",
            "mode",
            &["ask-first", "suggest", "auto-continue"],
        ),
        (
            "delegation",
            "assignment_policy",
            &["local-preferred", "best-fit-advisory", "required-best-fit"],
        ),
        (
            "delegation",
            "transport_authority",
            &["manual", "automatic"],
        ),
        (
            "delegation",
            "human_override_policy",
            &[
                "explicit-only",
                "allowed-with-recorded-reason",
                "disallowed",
            ],
        ),
    ];
    for (section, field, allowed) in choices {
        if let Some(value) = effective[*section][*field]
            .as_str()
            .filter(|value| allowed.contains(value))
        {
            snapshot[*section][*field] = json!(value);
        }
    }
    if let Some(value) = effective["session_logging"]["enabled"].as_bool() {
        snapshot["session_logging"]["enabled"] = json!(value);
    }
    if let Some(enabled) = effective["modules"]["enabled"].as_array() {
        snapshot["modules"]["enabled"] = Value::Array(
            enabled
                .iter()
                .filter(|value| {
                    value
                        .as_str()
                        .is_some_and(|name| ["planning", "memory", "verification"].contains(&name))
                })
                .cloned()
                .collect(),
        );
    }
    snapshot
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
        b"# Native maintainer diagnostics\n\nCanonical events declare capture detail and reference recoverable local I/O artifacts. Export through the maintained diagnostic reader.\n",
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
/// Return only a bounded transport advisory after observing capture. It is never
/// an owner contribution, request identity, effect input or retained decision.
/// Each invocation replaces this observation: no warning stream or episode ledger.
pub fn capture(
    request: &Value,
    result: &Result<Value, CoreError>,
    elapsed: std::time::Duration,
) -> Option<Value> {
    capture_transport(request, None, result, elapsed)
}

/// Native stdin and emitted JSON are captured at the same boundary as delivery.
/// The successful advisory is added only after its referenced body was retained.
pub fn capture_transport(
    request: &Value,
    raw_input: Option<&str>,
    result: &Result<Value, CoreError>,
    elapsed: std::time::Duration,
) -> Option<Value> {
    let mut requested = false;
    match capture_inner(request, raw_input, result, elapsed, &mut requested) {
        Ok(posture) => posture,
        Err(_) if requested => Some(json!({"status":"capture-failed","authoritative":false})),
        Err(_) => None,
    }
}
fn capture_inner(
    request: &Value,
    raw_input: Option<&str>,
    result: &Result<Value, CoreError>,
    elapsed: std::time::Duration,
    requested: &mut bool,
) -> Result<Option<Value>, String> {
    if std::env::var("AW_SESSION_LOGGING_DISABLE").ok().as_deref() == Some("1") {
        return Ok(None);
    }
    let Some(object) = request.as_object().filter(|v| v.len() == 1) else {
        return Ok(None);
    };
    let (operation, input) = object.iter().next().unwrap();
    if !matches!(operation.as_str(), "start" | "invoke") {
        return Ok(None);
    }
    let target = if input.get("reference").is_some() {
        crate::operating::carried_target(input).ok_or("carried target unavailable")?
    } else {
        input["target"].as_str().unwrap_or(".")
    };
    let root = Dir::open_ambient_dir(target, ambient_authority()).map_err(|e| e.to_string())?;
    let local =
        crate::native_assignment_policy::load(Path::new(target)).map_err(|e| e.to_string())?;
    let policy = policy(json!({"local":local.effective,"disable_override":""}))
        .map_err(|e| e.to_string())?;
    if policy["enabled"] != true {
        return Ok(None);
    }
    *requested = true;
    let identity = std::env::var("AW_SESSION_LOGICAL_IDENTITY").unwrap_or_default();
    if trim_identity(&identity).is_empty() || identity.len() > 8192 {
        return Ok(Some(
            json!({"status":"identity-unavailable","requirement":"AW_SESSION_LOGICAL_IDENTITY","authoritative":false}),
        ));
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
    let advisory = json!({"status":"capturing","detail":policy["detail"],"authoritative":false});
    let delivered = match result {
        Ok(value) => attach_capture(value.clone(), advisory.clone()),
        Err(error) => error_payload(
            "invalid-source-decision",
            &error.to_string(),
            Some(advisory.clone()),
        ),
    };
    let response_text = format!(
        "{}\n",
        serde_json::to_string(&delivered).map_err(|e| e.to_string())?
    );
    let result_measure = (response_text.len() as u64, hash(response_text.as_bytes()));
    let canonical_input;
    let input_text = match raw_input {
        Some(input) => input,
        None => {
            canonical_input = serde_json::to_string(request).map_err(|e| e.to_string())?;
            &canonical_input
        }
    };
    let input_measure = (input_text.len() as u64, hash(input_text.as_bytes()));
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
    let mut entry = json!({"id":id,"timestamp":timestamp,"duration_ms":elapsed.as_millis().min(u64::MAX as u128) as u64,"command":format!("agentic-workspace {operation}"),"argv":[],"target":normalized_target,"exit_status":if result.is_ok(){0}else{2},"exit_class":if result.is_ok(){"success"}else{"failure"},"origin":{"classification":"unknown","source":"native-transport"},"output_bytes":result_measure.0,"output_digest":result_measure.1,"request_bytes":input_measure.0,"request_sha256":input_measure.1,"storage_mode":"metadata-only","detail":policy["detail"],"omissions":["host CLI argv before native envelope","caller origin","process interruption before completion","transport delivery failure after capture","unadmitted historical registry"],"path_mode":policy["path_mode"]});
    if policy["detail"] == "full" {
        // Reuse the physical session's existing recoverable artifact namespace.
        // Registry/events remain bounded; body length never degrades to a digest.
        let artifact_folder = format!(
            "{}/artifacts",
            Path::new(session["log_path"].as_str().unwrap())
                .parent()
                .unwrap()
                .to_str()
                .unwrap()
        );
        dirs(&root, &artifact_folder)?;
        let path = format!("{artifact_folder}/{id}.json");
        let shared_config = match crate::native_config::load(
            &root,
            ".agentic-workspace/config.toml",
            include_str!("../contracts/schemas/workspace_config.schema.json"),
        ) {
            Ok(Some((config, revision))) => {
                json!({"status":"current","revision":revision,"configuration":config})
            }
            Ok(None) => json!({"status":"absent","configuration":{}}),
            Err(error) => json!({"status":"unavailable","reason":error}),
        };
        let effective =
            crate::assignment_policy::merge(&shared_config["configuration"], &local.effective);
        let snapshot = configuration_snapshot(&effective);
        let local_sources: Vec<Value> = local.sources.iter().map(|source| {
            json!({"role":if source["status"] == "current-shared-local-source" {"shared-local"} else {"repository-local"},
                "status":source["status"],"revision":source["revision"]})
        }).collect();
        let configuration = json!({
            "effective_logging_policy":policy,
            "effective_configuration":snapshot,
            "repository_source":{"reference":".agentic-workspace/config.toml","status":shared_config["status"],"revision":shared_config["revision"]},
            "local_sources":local_sources,
            "local_source_revision":local.revision,
            "runtime":{"package_version":env!("CARGO_PKG_VERSION"),"bundled_payload_revision":crate::native_payload::identity(),"logging_schema_sha256":hash(LOCAL_SCHEMA.as_bytes())},
            "boundary":"Native request envelope and delivered stdout/stderr; no arbitrary environment or host conversation.",
            "configuration_boundary":"Closed operating choices and source/runtime identities; arbitrary settings, paths, commands, extensible names and diagnostic reasons omitted.",
            "authoritative":false
        });
        let normalize = |text: &str| {
            normalize_paths(
                text,
                &canonical_target,
                policy["path_mode"].as_str().unwrap(),
            )
        };
        let (stdout, stderr) = if result.is_ok() {
            (normalize(&response_text), String::new())
        } else {
            (String::new(), normalize(&response_text))
        };
        let artifact = json!({
            "kind":"agentic-workspace/session-command-io/v1",
            "request":normalize(input_text),"stdout":stdout,"stderr":stderr,
            "configuration":normalize(&serde_json::to_string(&configuration).map_err(|e|e.to_string())?),
            "path_mode":policy["path_mode"],"local_only":true,"authoritative":false
        });
        let body = serde_json::to_vec(&artifact).map_err(|e| e.to_string())?;
        create(&root, &path, &body)?;
        entry["artifact"] = json!({"path":path,"bytes":body.len(),"sha256":hash(&body),"storage_mode":"raw-local-artifact"});
        entry["storage_mode"] = json!("raw-local-artifact");
        entry["content_transform"] = json!(if policy["path_mode"] == "absolute" {
            "none"
        } else {
            "known-local-paths"
        });
    } else {
        entry["omissions"].as_array_mut().unwrap().extend([
            json!("request body"),
            json!("result body"),
            json!("stdout/stderr"),
            json!("configuration prelude"),
        ]);
    }
    if let Ok(value) = result {
        // Transport success is distinct from admitted effect and continuation.
        // Record only bounded status tags, never owner material or diagnostics.
        if value["effect_outcome"]["status"].is_string() {
            entry["effect_status"] = value["effect_outcome"]["status"].clone();
            entry["continuation_status"] = value["continuation"]["status"].clone();
        }
    }
    let event = json!({"kind":"agentic-workspace/session-log-event/v1","schema_version":1,"event_id":id,"event_type":"command.completed","timestamp":timestamp,"sequence":next_sequence,"logical_session_id":logical,"physical_session_id":session["session_id"],"parent_logical_session_id":session["parent_logical_session_id"],"correlation_id":session["correlation_id"],"payload":{"entry":entry},"local_only":true,"authoritative":false});
    let mut line = serde_json::to_vec(&event).unwrap();
    line.push(b'\n');
    if line.len() > 8192 || bytes.len() + line.len() > LIMIT as usize {
        return Err("event capture bound".into());
    }
    safe(&root, &stream)?;
    root.open_with(&stream, OpenOptions::new().append(true).create(true))
        .and_then(|mut f| f.write_all(&line))
        .map_err(|e| e.to_string())?;
    Ok(Some(advisory))
}

pub(crate) fn attach_capture(mut decision: Value, capture: Value) -> Value {
    // Advisory belongs only to the displayed view, never immutable carriage.
    if let Some(view) = decision.get_mut("view").filter(|v| v.is_object()) {
        view["session_capture"] = capture;
    } else {
        decision["session_capture"] = capture;
    }
    decision
}
pub(crate) fn error_payload(code: &str, message: &str, capture: Option<Value>) -> Value {
    let mut payload = json!({"error":{"code":code,"message":message}});
    if let Some(capture) = capture {
        payload["session_capture"] = capture;
    }
    payload
}
fn normalize_paths(text: &str, target: &str, mode: &str) -> String {
    if mode == "absolute" {
        return text.to_owned();
    }
    let mut replacements = vec![(
        target.to_owned(),
        if mode == "repo-relative" {
            "."
        } else {
            "<target>"
        }
        .to_owned(),
    )];
    // Extended Windows canonical paths and ordinary caller spelling are equal.
    if let Some(ordinary) = target.strip_prefix(r"\\?\") {
        replacements.push((ordinary.to_owned(), replacements[0].1.clone()));
    }
    if let Ok(home) = std::env::var(if cfg!(windows) { "USERPROFILE" } else { "HOME" }) {
        replacements.push((home, "<home>".into()));
    }
    if let Some(paths) = std::env::var_os("AW_SESSION_LOG_REDACT_PATHS") {
        for (index, path) in std::env::split_paths(&paths).enumerate() {
            replacements.push((
                path.to_string_lossy().into_owned(),
                format!("<local-path-{}>", index + 1),
            ));
        }
    }
    let mut expanded = Vec::new();
    for (path, replacement) in replacements {
        for spelling in [
            path.clone(),
            path.replace('\\', "/"),
            path.replace('\\', "\\\\"),
        ] {
            if !spelling.is_empty() {
                expanded.push((spelling, replacement.clone()));
            }
        }
    }
    expanded.sort_by_key(|(path, _)| std::cmp::Reverse(path.len()));
    let mut normalized = text.to_owned();
    for (path, replacement) in expanded {
        normalized = normalized.replace(&path, &replacement);
    }
    normalized
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
                "[session_logging]\nenabled=true\npath_mode=\"redacted\"\n",
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
