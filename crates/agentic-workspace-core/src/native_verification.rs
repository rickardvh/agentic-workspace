//! Current Verification source and evidence visibility. This reader does not
//! authenticate producers, publish receipts, execute checks, or grant claims.
use crate::{CoreError, digest, prepare_request_value};
use cap_std::{ambient_authority, fs::Dir};
use serde_json::{Value, json};
use sha2::{Digest, Sha256};
use std::{io::Read, path::Path};

const MANIFEST: &str = ".agentic-workspace/verification/manifest.toml";
const RECEIPTS: &str = ".agentic-workspace/proof/receipts";

pub(crate) fn read(root: &Dir, path: &str) -> Result<Option<Vec<u8>>, String> {
    if path.is_empty()
        || path.contains('\\')
        || path
            .split('/')
            .any(|v| matches!(v, "" | "." | "..") || v.contains(':'))
    {
        return Err("source path is not repository-relative".into());
    }
    let mut prefix = std::path::PathBuf::new();
    for part in path.split('/') {
        prefix.push(part);
        match root.symlink_metadata(&prefix) {
            Ok(meta) => {
                #[cfg(windows)]
                let linked = {
                    use cap_std::fs::MetadataExt;
                    meta.file_attributes() & 0x400 != 0
                };
                #[cfg(not(windows))]
                let linked = meta.is_symlink();
                if linked {
                    return Err("Verification source cannot traverse links".into());
                }
            }
            Err(e) if e.kind() == std::io::ErrorKind::NotFound => return Ok(None),
            Err(_) => return Err("Verification source is unreadable".into()),
        }
    }
    let mut bytes = Vec::new();
    root.open(path)
        .map_err(|_| "Verification source is unreadable")?
        .take(1_048_577)
        .read_to_end(&mut bytes)
        .map_err(|_| "Verification source is unreadable")?;
    if bytes.len() > 1_048_576 {
        return Err("Verification source exceeds bounded read".into());
    }
    Ok(Some(bytes))
}

fn sha(bytes: &[u8]) -> String {
    format!("{:x}", Sha256::digest(bytes))
}

fn bounded_git_output(
    command: &mut std::process::Command,
    budget: std::time::Duration,
) -> Result<(std::process::ExitStatus, Vec<u8>), String> {
    use std::process::Stdio;
    let deadline = std::time::Instant::now() + budget;
    let mut child = command
        .stdin(Stdio::null())
        .stdout(Stdio::piped())
        .stderr(Stdio::null())
        .spawn()
        .map_err(|_| "git-observation-unavailable")?;
    let stdout = child.stdout.take().expect("piped stdout");
    let (sender, receiver) = std::sync::mpsc::sync_channel(1);
    std::thread::spawn(move || {
        let mut bytes = Vec::new();
        let result = stdout.take(4097).read_to_end(&mut bytes).map(|_| bytes);
        let _ = sender.send(result);
    });
    let result = loop {
        if std::time::Instant::now() >= deadline {
            break Err("git-observation-timeout".into());
        }
        match child.try_wait() {
            Ok(Some(status)) => {
                break match receiver
                    .recv_timeout(deadline.saturating_duration_since(std::time::Instant::now()))
                {
                    Ok(Ok(bytes)) if bytes.len() <= 4096 => Ok((status, bytes)),
                    Ok(Ok(_)) => Err("git-observation-output-exceeds-bound".into()),
                    Ok(Err(_)) => Err("git-observation-read-failed".into()),
                    Err(_) => Err("git-observation-timeout".into()),
                };
            }
            Err(_) => break Err("git-observation-process-state-unavailable".into()),
            Ok(None) => std::thread::sleep(
                std::time::Duration::from_millis(10)
                    .min(deadline.saturating_duration_since(std::time::Instant::now())),
            ),
        }
    };
    if result.is_err() {
        let _ = child.kill();
        let _ = child.wait();
    }
    result
}

fn authenticate_review(root: &Dir, target: &Path, reference: &str) -> Value {
    let rejected =
        |reason: &str| json!({"status":"unadmitted","reason":reason,"authority_effect":"none"});
    let Some(id) = reference.strip_prefix("independent-review-host-result:") else {
        return rejected("invalid-host-result-reference");
    };
    if id.is_empty()
        || !id
            .bytes()
            .all(|b| b.is_ascii_alphanumeric() || b == b'-' || b == b'_')
    {
        return rejected("invalid-host-result-reference");
    }
    let directory = ".agentic-workspace/local/independent-review-host-results";
    let parse =
        |path: &str| -> Option<Value> { serde_json::from_slice(&read(root, path).ok()??).ok() };
    let Some(index) = parse(&format!("{directory}/index.json")) else {
        return rejected("host-result-index-unavailable");
    };
    if index["kind"] != "agentic-workspace/independent-review-host-result-index/v1" {
        return rejected("host-result-index-invalid");
    }
    let entry = &index["results"][id];
    if !entry.is_object() {
        return rejected("host-result-not-indexed");
    }
    let default_path = format!("{id}.json");
    let path = entry["path"].as_str().unwrap_or(&default_path);
    if path.starts_with('.') || path.contains(['/', '\\', ':']) {
        return rejected("host-result-index-path-invalid");
    }
    let Some(host) = parse(&format!("{directory}/{path}")) else {
        return rejected("host-result-unavailable");
    };
    if let Some(expected) = entry["host_result_digest"]
        .as_str()
        .filter(|s| !s.is_empty())
    {
        let Ok(encoded) = crate::proof_subject::compact_json(&host) else {
            return rejected("host-result-encoding-unproven");
        };
        if sha(encoded.as_bytes()) != expected {
            return rejected("host-result-index-digest-mismatch");
        }
    }
    // Git is optional host observation glue, never a product semantic fallback.
    // Missing Git on a repository cannot be mistaken for a path-only identity.
    let mut command = std::process::Command::new("git");
    #[cfg(windows)]
    {
        use std::os::windows::process::CommandExt;
        command.creation_flags(0x08000000);
    }
    command.args([
        "-C",
        &target.to_string_lossy(),
        "config",
        "--get",
        "remote.origin.url",
    ]);
    let observed = bounded_git_output(&mut command, std::time::Duration::from_secs(2));
    let remote = match observed {
        Ok((status, bytes)) if status.success() => {
            String::from_utf8_lossy(&bytes).trim().replace('\\', "/")
        }
        Ok((status, _)) if status.code() == Some(1) => String::new(),
        Err(reason)
            if reason == "git-observation-timeout"
                || reason == "git-observation-output-exceeds-bound" =>
        {
            return rejected(&reason);
        }
        _ if target.ancestors().any(|path| path.join(".git").exists()) => {
            return rejected("current-workspace-identity-observation-unavailable");
        }
        _ => String::new(),
    };
    let workspace = if remote.is_empty() {
        let observed = target.to_string_lossy();
        let path = if let Some(unc) = observed.strip_prefix(r"\\?\UNC\") {
            format!(r"\\{unc}")
        } else {
            observed
                .strip_prefix(r"\\?\")
                .unwrap_or(&observed)
                .to_owned()
        };
        format!("workspace:path:{path}")
    } else {
        let remote = remote.strip_suffix(".git").unwrap_or(&remote);
        let normalized = if let Some((host, path)) =
            remote.strip_prefix("git@").and_then(|v| v.split_once(':'))
        {
            format!("https://{host}/{path}")
        } else {
            remote.to_owned()
        };
        format!(
            "workspace:git:{}",
            normalized.trim_end_matches('/').to_lowercase()
        )
    };
    let Ok(now) = std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH) else {
        return rejected("current-host-clock-unavailable");
    };
    let verdict = match crate::review_authentication::view(
        json!({"host_result_ref":reference,"host_result":host,"workspace_ref":workspace,"now_unix_micros":now.as_micros() as i64,"public_keys":null}),
    ) {
        Ok(value) if value["status"] == "admitted" => value,
        _ => return rejected("release-pinned-host-authentication-rejected"),
    };
    json!({"status":"authenticated","verdict":verdict,"authority_effect":"host-result-authentication-only",
        "remaining_gaps":["current-assignment-and-proof-subject-admission-required","current-strategy-and-runtime-evidence-required"],
        "claim_boundary":"Authentic signed host result does not itself establish current independent review or satisfy a claim."})
}

// Verification and instruction sources consume the same path selector semantics.
pub(crate) fn matches(pattern: &str, path: &str) -> bool {
    crate::instruction_applicability::matches(pattern, path)
}

// Historical publication transport uses Python json.dumps(sort_keys=True,
// ensure_ascii=True), including spaces. This is compatibility encoding, not
// another semantic identity. Exponent/large float representations fail closed.
fn publication_json(value: &Value) -> Result<String, &'static str> {
    Ok(match value {
        Value::Null => "null".into(),
        Value::Bool(value) => value.to_string(),
        Value::Number(value) => {
            let text = value.to_string();
            if value.is_f64()
                && (text.contains(['e', 'E'])
                    || value
                        .as_f64()
                        .is_none_or(|v| v != 0.0 && !(0.0001..1e16).contains(&v.abs())))
            {
                return Err("publication-number-encoding-compatibility-unproven");
            }
            text
        }
        Value::String(value) => {
            let mut text = String::from("\"");
            for ch in value.chars() {
                match ch {
                    '"' => text.push_str("\\\""),
                    '\\' => text.push_str("\\\\"),
                    '\n' => text.push_str("\\n"),
                    '\r' => text.push_str("\\r"),
                    '\t' => text.push_str("\\t"),
                    '\u{8}' => text.push_str("\\b"),
                    '\u{c}' => text.push_str("\\f"),
                    c if !(' '..='~').contains(&c) => {
                        for unit in c.encode_utf16(&mut [0; 2]) {
                            text.push_str(&format!("\\u{unit:04x}"));
                        }
                    }
                    c => text.push(c),
                }
            }
            text.push('"');
            text
        }
        Value::Array(items) => format!(
            "[{}]",
            items
                .iter()
                .map(publication_json)
                .collect::<Result<Vec<_>, _>>()?
                .join(", ")
        ),
        Value::Object(items) => {
            let mut keys: Vec<_> = items.keys().collect();
            keys.sort();
            format!(
                "{{{}}}",
                keys.into_iter()
                    .map(|key| Ok(format!(
                        "{}: {}",
                        publication_json(&json!(key))?,
                        publication_json(&items[key])?
                    )))
                    .collect::<Result<Vec<_>, &'static str>>()?
                    .join(", ")
            )
        }
    })
}

fn publication_admission(root: &Dir, id: &str, receipt: &Value) -> Value {
    let rejected = |reason: &str| json!({"status":"rejected","reason":reason});
    let index = read(root, &format!("{RECEIPTS}/index.json"))
        .ok()
        .flatten()
        .and_then(|bytes| {
            serde_json::from_slice::<Value>(
                bytes.strip_prefix(&[0xef, 0xbb, 0xbf]).unwrap_or(&bytes),
            )
            .ok()
        });
    let Some(index) = index else {
        return rejected("publication-index-unavailable-or-invalid");
    };
    let entry = &index["receipts"][id];
    if index["kind"] != "agentic-workspace/trusted-producer-receipt-index/v1" || !entry.is_object()
    {
        return rejected("publication-not-indexed");
    }
    if entry["path"] != format!("{id}.json") {
        return rejected("publication-index-path-mismatch");
    }
    let superseded = match &entry["superseded_by"] {
        Value::Null => false,
        Value::Bool(value) => *value,
        Value::Number(value) => value.as_f64() != Some(0.0),
        Value::String(value) => !value.is_empty(),
        Value::Array(value) => !value.is_empty(),
        Value::Object(value) => !value.is_empty(),
    };
    if (!entry["status"].is_null() && !entry["status"].is_string())
        || !matches!(
            entry["status"].as_str().unwrap_or("current"),
            "current" | "fresh" | "accepted"
        )
        || superseded
    {
        return rejected("publication-stale-or-superseded");
    }
    if entry["producer_class"] != "aw-proof"
        || receipt["producer_class"] != "aw-proof"
        || receipt["receipt_id"] != id
        || entry["revision"] != receipt["revision"]
        || entry["source_ref"] != receipt["source_ref"]
    {
        return rejected("publication-owner-index-mismatch");
    }
    if receipt["kind"] != "agentic-workspace/proof-receipt/v1" {
        return rejected("publication-contract-invalid");
    }
    let expected = match publication_identity(receipt) {
        Ok(value) => value,
        Err(error) => return rejected(&error.to_string()),
    };
    if &expected[..16] != id || receipt["publication_id"] != id {
        return rejected("publication-content-identity-mismatch");
    }
    json!({"status":"admitted","reason":"current-indexed-owner-publication","authority_effect":"publication-only"})
}

pub(crate) fn publication_identity(receipt: &Value) -> Result<String, CoreError> {
    let identity = crate::proof_receipt::publication_identity(receipt);
    let rendered = publication_json(&identity).map_err(CoreError::new)?;
    Ok(sha(rendered.as_bytes())[..16].to_owned())
}

fn receipt_view(
    root: &Dir,
    target: &Path,
    strategy: &Value,
    reference: &str,
    task: &str,
    changed: &[String],
    work: &Value,
) -> Value {
    let work_ref = &work["id"];
    let work_revision = &work["revision"];
    let mut gaps = Vec::<String>::new();
    let id = reference.strip_prefix("proof://receipts/").unwrap_or("");
    if id.is_empty()
        || !id
            .chars()
            .all(|c| c.is_ascii_alphanumeric() || matches!(c, '-' | '_' | '.'))
    {
        return json!({"reference":reference,"status":"unadmitted","gaps":["invalid-receipt-reference"]});
    }
    let receipt = match read(root, &format!("{RECEIPTS}/{id}.json")) {
        Ok(Some(bytes)) => serde_json::from_slice::<Value>(
            bytes.strip_prefix(&[0xef, 0xbb, 0xbf]).unwrap_or(&bytes),
        )
        .ok(),
        _ => None,
    };
    let Some(receipt) = receipt else {
        return json!({"reference":reference,"status":"unadmitted","gaps":["receipt-unavailable-or-invalid"]});
    };
    let publication = publication_admission(root, id, &receipt);
    let timestamp_valid = receipt["recorded_at"]
        .as_str()
        .and_then(|value| value.parse::<toml::value::Datetime>().ok())
        .is_some_and(|value| {
            value.date.is_some() && value.time.is_some() && value.offset.is_some()
        });
    let binding = crate::proof_receipt::assignment_binding(&receipt).ok();
    let admission = crate::proof_receipt::admit(&receipt, timestamp_valid, binding.as_deref());
    if admission["admitted"] != true {
        gaps.push(
            admission["reason"]
                .as_str()
                .unwrap_or("receipt-shape-unadmitted")
                .into(),
        );
    } else if admission["proof_sufficient"] != true {
        gaps.push("receipt-result-does-not-satisfy-proof".into());
    }
    if publication["status"] != "admitted" {
        gaps.push(
            publication["reason"]
                .as_str()
                .unwrap_or("publication-unadmitted")
                .into(),
        );
    }
    if receipt["kind"] != "agentic-workspace/proof-receipt/v1" {
        gaps.push("receipt-contract-invalid".into());
    }
    let freshness_started = std::time::Instant::now();
    let mut freshness = crate::native_proof::freshness(target,task,changed,&json!({"id":work_ref,"revision":work_revision}),strategy,&receipt)
        .unwrap_or_else(|error| json!({"status":"unproven","strategy_coverage":"unproven","reason":error.to_string()}));
    let mut detail = json!({"status":"not-required"});
    if receipt["proof_subject"]["runtime"]["implementation"] == "native-aw-proof" {
        let artifact = &receipt["execution_artifact"];
        let current = publication["status"] == "admitted"
            && artifact["path"].as_str().is_some_and(|path| {
                path.starts_with(".agentic-workspace/local/proof-receipts/runs/native-")
                    && path.ends_with("/run.json.command.json")
                    && read(root, path)
                        .ok()
                        .flatten()
                        .is_some_and(|bytes| artifact["sha256"] == sha(&bytes))
            });
        detail = json!({"status":if current {"current"} else {"unavailable-or-stale"},"artifact":artifact});
        if !current {
            freshness["status"] = json!("unproven");
            gaps.push("native-proof-detail-unavailable-or-stale".into());
        }
    }
    freshness["validation_duration_us"] = json!(freshness_started.elapsed().as_micros());
    let judgment = crate::task_judgment::view(json!({
        "action":"classify", "task":task, "changed_paths":changed, "work_ref":work_ref, "work_revision":work_revision,
        "observations":[{"receipt":receipt, "publication_current":publication["status"] == "admitted",
            "proof_sufficient":admission["proof_sufficient"] == true, "evidence_freshness":freshness["status"]}],
        "manual_required":false,"manual_status":"", "independent_required":false,"independent_status":""
    }));
    let judgment = match judgment {
        Ok(value) => value,
        Err(error) => {
            json!({"status":"unresolved", "classifications":[{"reasons":[error.to_string()]}]})
        }
    };
    gaps.extend(
        judgment["classifications"][0]["reasons"]
            .as_array()
            .into_iter()
            .flatten()
            .filter_map(Value::as_str)
            .map(str::to_owned),
    );
    let subject = &receipt["proof_subject"];
    if subject["kind"] != "agentic-workspace/proof-subject/v1"
        || subject["identity_complete"] != true
    {
        gaps.push("proof-subject-incomplete".into());
    }
    if let Some(inputs) = subject["source_inputs"].as_array() {
        for input in inputs {
            let current = input["path"]
                .as_str()
                .and_then(|path| read(root, path).ok().flatten());
            if current.as_ref().map(|bytes| sha(bytes))
                != input["sha256"].as_str().map(str::to_owned)
            {
                gaps.push("proof-semantic-input-stale-or-unavailable".into());
                break;
            }
        }
    } else {
        gaps.push("proof-semantic-inputs-unavailable".into());
    }
    // A current indexed publication still does not establish its runtime,
    // strategy coverage, or independent judgment producer.
    if freshness["status"] != "reusable" {
        gaps.push("proof-runtime-compatibility-unproven".into());
        gaps.push("current-strategy-coverage-unproven".into());
    } else {
        gaps.push("nested-tool-runtime-unobserved".into());
    }
    json!({"reference":reference,"status":"unadmitted","publication_admission":publication,"receipt_admission":admission,
        "task_judgment":judgment,"detail":detail,"runtime_admission":freshness,"evidence_freshness":freshness["status"],"strategy_coverage":freshness["strategy_coverage"],"independent_review":"not-established-by-publication",
        "proof_subject":subject["id"],"gaps":gaps})
}

/// Host-only inputs are supplied by the current-work and Planning owners. A
/// public caller can request a claim judgment, never supply source admission.
pub fn view(
    target: &Path,
    task: &str,
    changed: &[String],
    current_work: &Value,
    planning_subject: Option<&Value>,
    request: Option<Value>,
) -> Result<Value, CoreError> {
    view_with_applicability(
        target,
        task,
        changed,
        current_work,
        planning_subject,
        request,
        ApplicabilityContext {
            facts: &Value::Null,
            request: None,
            contract: None,
            invocation: None,
        },
    )
}

pub(crate) struct ApplicabilityContext<'a> {
    pub facts: &'a Value,
    pub request: Option<Value>,
    pub contract: Option<&'a Value>,
    pub invocation: Option<&'a Value>,
}

pub(crate) fn view_with_applicability(
    target: &Path,
    task: &str,
    changed: &[String],
    current_work: &Value,
    planning_subject: Option<&Value>,
    request: Option<Value>,
    applicability: ApplicabilityContext<'_>,
) -> Result<Value, CoreError> {
    let mut assurance_input = crate::assurance_applicability::native_input(
        target,
        task,
        changed,
        current_work,
        planning_subject,
        applicability.facts,
    )?;
    let root = Dir::open_ambient_dir(target, ambient_authority())
        .map_err(|e| CoreError::new(e.to_string()))?;
    let mut gaps = Vec::<String>::new();
    let (manifest, manifest_revision) = match read(&root, MANIFEST) {
        Ok(Some(bytes)) => {
            let parsed = std::str::from_utf8(&bytes)
                .ok()
                .and_then(|text| {
                    toml::from_str::<toml::Value>(text.trim_start_matches('\u{feff}')).ok()
                })
                .and_then(|value| serde_json::to_value(value).ok());
            let value = parsed.unwrap_or(Value::Null);
            if value["schema_version"] != "agentic-workspace/verification-manifest/v1" {
                gaps.push("verification-manifest-invalid".into());
            }
            (value, sha(&bytes))
        }
        Ok(None) => (Value::Null, "absent".into()),
        Err(reason) => {
            gaps.push(reason);
            (Value::Null, "unreadable".into())
        }
    };
    if !manifest.is_null()
        && (manifest["protocols"].as_object().is_none()
            || manifest["proof_routes"].as_object().is_none())
    {
        gaps.push("verification-manifest-owner-sections-invalid".into());
    }
    let source_revision = digest(&json!({"manifest_revision":manifest_revision,
        "planning_subject":planning_subject.map(|s| json!({"id":s["id"],"revision":s["revision"]}))}))?;
    let mut protocols = serde_json::Map::new();
    let mut selector_gaps = Vec::new();
    if let Some(all) = manifest["protocols"].as_object() {
        for (id, protocol) in all {
            if let Some(patterns) = protocol["applies_to_paths"].as_array() {
                if patterns.iter().any(|p| p.as_str().is_none()) {
                    selector_gaps.push(format!("unsupported-path-selector:{id}"));
                }
                if patterns
                    .iter()
                    .filter_map(Value::as_str)
                    .any(|p| changed.iter().any(|path| matches(p, path)))
                {
                    protocols.insert(id.clone(), protocol.clone());
                }
            } else if !protocol["applies_to_paths"].is_null() {
                gaps.push(format!("invalid-path-selectors:{id}"));
            }
        }
    }
    let mut routes = serde_json::Map::new();
    if let Some(all) = manifest["proof_routes"].as_object() {
        for (id, route) in all {
            if route["protocol_refs"].as_array().is_some_and(|refs| {
                refs.iter()
                    .filter_map(Value::as_str)
                    .any(|r| protocols.contains_key(r))
            }) {
                routes.insert(id.clone(), route.clone());
            }
        }
    }
    let mut scenarios = serde_json::Map::new();
    for item in protocols.values().chain(routes.values()) {
        if let Some(refs) = item["scenario_refs"].as_array() {
            for id in refs.iter().filter_map(Value::as_str) {
                if let Some(scenario) = manifest["scenarios"].get(id) {
                    scenarios.insert(id.to_owned(), scenario.clone());
                } else {
                    gaps.push(format!("referenced-verification-scenario-unavailable:{id}"));
                }
            }
        }
    }
    let strategy = json!({"source":MANIFEST,"protocols":protocols,"proof_routes":routes,"scenarios":scenarios});
    let strategy_revision = digest(&strategy)?;
    let direct_subject = crate::direct_task::subject(task, changed)?;
    let subject = planning_subject.unwrap_or(&direct_subject);
    let work_ref = subject["id"].clone();
    let work_revision = subject["revision"].clone();
    let schema: Value = serde_json::from_str(include_str!(
        "../../../src/agentic_workspace/contracts/schemas/source_decision_input.schema.json"
    ))
    .expect("checked schema");
    let mut arguments_schema = schema["$defs"]["verification_claim_request"].clone();
    arguments_schema["$schema"] = schema["$schema"].clone();
    let requests = json!([{"kind":"verification/claim/v1","result_kind":"agentic-workspace/native-verification-view/v1",
        "input_schema":arguments_schema}, crate::verification_requirements::declaration(), crate::review_authentication::declaration(), crate::assurance_applicability::declaration(), crate::native_proof::declaration(), crate::native_proof::record_declaration()]);
    let owner_revision = digest(&requests)?;
    let mut contract = json!({"kind":"agentic-workspace/capability-contract/v1","revision":"pending",
        "owners":[{"owner":"verification","revision":owner_revision,"requests":requests}],
        "restriction_authorities":[{"owner":"verification","affects":["claim:complete","claim:claim-slice-complete","claim:claim-work-complete","claim:close-parent-lane"]}]});
    contract["owners"][0]["domains"] = json!(["verification"]);
    contract["owners"][0]["effects"] = json!([{"id":"proof-execution","domain":"verification"}]);
    contract["owners"][0]["operations"] = json!([crate::native_proof::operation()]);
    contract["revision"] = json!(digest(&contract)?);
    let admission_contract = applicability.contract.unwrap_or(&contract);
    let template = json!({"kind":"agentic-workspace/public-request/v1","id":"verification/claim/v1","owner":"verification",
        "owner_revision":owner_revision,"source_revision":source_revision,"capability_revision":admission_contract["revision"],
        "task_identity":current_work,"request_kind":"verification/claim/v1","arguments":{"claim_class":"slice_complete","evidence_refs":[]}});
    let mut authentication_request = template.clone();
    authentication_request["id"] = json!("verification/authenticate-host-review/v1");
    authentication_request["request_kind"] = json!("verification/authenticate-host-review/v1");
    authentication_request["arguments"] =
        json!({"host_result_ref":"independent-review-host-result:<current-indexed-ref>"});
    let mut assurance_request = template.clone();
    assurance_request["id"] = json!("verification/assurance-applicability/v1");
    assurance_request["request_kind"] = json!("verification/assurance-applicability/v1");
    assurance_request["source_revision"] = assurance_input["source_revision"].clone();
    assurance_request["arguments"] = json!({"decisions":{}});
    let mut proof_choice = applicability
        .invocation
        .map(|i| i["arguments"]["selection"]["choice"].clone());
    let mut reported_observation = applicability
        .invocation
        .and_then(|i| i["arguments"]["selection"].get("reported_observation"))
        .filter(|v| !v.is_null())
        .cloned();
    let mut authentication = Value::Null;
    let mut evidence = Vec::new();
    let mut requested = false;
    for request in request
        .into_iter()
        .flat_map(|value| value.as_array().cloned().unwrap_or_else(|| vec![value]))
        .chain(applicability.request)
    {
        prepare_request_value(
            json!({"request":request,"current_work":request["task_identity"],"capability_contract":admission_contract}),
        )?;
        if request["owner"] != "verification" {
            return Err(CoreError::new("Verification request names another owner"));
        }
        let claim_request = request["request_kind"] != "verification/assurance-applicability/v1";
        requested |= claim_request;
        if !claim_request {
            assurance_input["judgment"] = json!({"source_revision":request["source_revision"],
                "task_identity":if request["task_identity"]==*current_work {assurance_input["task_identity"].clone()} else {request["task_identity"].clone()},
                "current_work":request["task_identity"],"decisions":request["arguments"]["decisions"]});
        }
        if !claim_request {
            // The shared applicability owner validates its separately bound source.
        } else if request["task_identity"] != *current_work
            || request["source_revision"] != source_revision
        {
            gaps.push("verification-request-stale".into());
        } else if request["request_kind"] == "verification/execute-selected/v1" {
            proof_choice = Some(request["arguments"].clone());
        } else if request["request_kind"] == "verification/record-receipt/v1" {
            proof_choice = Some(
                json!({"route_id":request["arguments"]["route_id"],"command":request["arguments"]["command"]}),
            );
            reported_observation = Some(request["arguments"].clone());
        } else if request["request_kind"] == "verification/authenticate-host-review/v1" {
            authentication = authenticate_review(
                &root,
                target,
                request["arguments"]["host_result_ref"].as_str().unwrap(),
            );
        } else if let Some(refs) = request["arguments"]["evidence_refs"].as_array() {
            evidence.extend(refs.iter().filter_map(Value::as_str).map(|r| {
                receipt_view(
                    &root,
                    target,
                    &strategy,
                    r,
                    task,
                    changed,
                    &json!({"id":work_ref,"revision":work_revision}),
                )
            }));
        }
    }
    let execution = crate::native_proof::select_mode(
        target,
        task,
        changed,
        subject,
        &strategy,
        proof_choice.as_ref(),
        reported_observation.as_ref(),
    )?;
    let execution_actions = crate::native_proof::action(
        target,
        task,
        changed,
        &execution,
        &admission_contract["revision"],
    )?;
    let execution_requests: Vec<Value> = execution["choices"]
        .as_array()
        .into_iter()
        .flatten()
        .map(|choice| {
            let mut request = template.clone();
            request["request_kind"] = json!("verification/execute-selected/v1");
            request["id"] = json!("verification/execute-selected/v1");
            request["arguments"] = choice.clone();
            request
        })
        .collect();
    let mut record_requests: Vec<Value> = execution_requests
        .iter()
        .map(|request| {
            let mut request = request.clone();
            request["request_kind"] = json!("verification/record-receipt/v1");
            request["id"] = json!("verification/record-receipt/v1");
            request["arguments"]["result"] = json!("failed");
            request
        })
        .collect();
    let mut report_request = template.clone();
    report_request["id"] = json!("verification/record-receipt/v1");
    report_request["request_kind"] = json!("verification/record-receipt/v1");
    report_request["arguments"] =
        json!({"route_id":"unresolved","command":"<reported-command>","result":"failed"});
    record_requests.push(report_request);
    let applicable = requested || !protocols.is_empty() || !gaps.is_empty();
    if applicable {
        gaps.extend(selector_gaps.clone());
        gaps.push("current-task-claim-judgment-not-admitted".into());
        if protocols.is_empty() {
            gaps.push("current-task-strategy-requires-owner-judgment".into());
        }
    }
    let packet = applicable.then(|| json!({"task":task,"changed_paths":changed,"claim_class":"slice_complete",
        "task_identity":current_work,"task_claim_identity":direct_subject,"work_ref":work_ref,"work_revision":work_revision,"planning_subject":planning_subject,
        "acceptance_source":{"source":"current-task","requested_outcome":task},
        "strategy":strategy,"strategy_revision":strategy_revision,
        "judgment_required":"Does this exact requested outcome and changed scope satisfy the current claim and applicable strategy?",
        "admitted_automated_evidence":evidence.iter().filter(|item| item["publication_admission"]["status"] == "admitted" && item["receipt_admission"]["proof_sufficient"] == true && item["evidence_freshness"] == "reusable").collect::<Vec<_>>(),"candidate_evidence":evidence,"known_uncertainty":gaps,
        "required_authority":"Use each selected protocol's review_owner and authority_refs; authenticate any independent producer through the existing Verification owner.",
        "judgment_ingress":"Existing Verification receipt admission; this read-only native view does not admit returned judgments.",
        "returned_judgment_requirements":["exact claim and current work/subject","current strategy and evidence references","judgment and unresolved reasons","required producer authority and independence"]}));
    let mut blockers = if applicable {
        json!([{"code":"verification-evidence-unresolved","message":"Current Verification obligations require admitted task-bound evidence and judgment.","affects":["claim:complete"]}])
    } else {
        json!([])
    };
    let assurance = crate::assurance_applicability::view(assurance_input.clone())?;
    let mut decisions = serde_json::Map::new();
    for row in assurance["requirements"].as_array().unwrap() {
        if row["status"] == "unresolved" {
            decisions.insert(row["id"].as_str().unwrap().into(), json!("unresolved"));
        }
        if row["status"] != "not-applicable"
            && matches!(
                row["force"].as_str(),
                Some("blocking" | "required-before-closeout")
            )
        {
            let affects: Vec<String> = row["blocking_claims"]
                .as_array()
                .into_iter()
                .flatten()
                .filter_map(Value::as_str)
                .map(|claim| format!("claim:{claim}"))
                .collect();
            if !affects.is_empty() {
                blockers.as_array_mut().unwrap().push(json!({"code":format!("assurance:{}:{}",row["id"].as_str().unwrap(),row["status"].as_str().unwrap()),
                "message":if row["status"]=="unresolved" {"Current source assurance applicability needs agent judgment; evidence cannot resolve scope."} else {"Current assurance evidence/measurement/review admission remains required; applicability does not prove satisfaction."},"affects":affects}));
            }
        }
    }
    if decisions.is_empty() {
        assurance_request = Value::Null;
    } else {
        assurance_request["arguments"]["decisions"] = json!(decisions);
    }
    let assurance_gaps: Vec<Value> = assurance["requirements"].as_array().unwrap().iter().filter(|row| row["status"]!="not-applicable").map(|row|json!({"requirement_id":row["id"],"status":"owner-evidence-not-admitted","source_requirement":row["source_requirement"],"rule":"Applicability never satisfies evidence, measurement, review, waiver or recommended-method semantics."})).collect();
    Ok(
        json!({"kind":"agentic-workspace/native-verification-view/v1","status":if applicable || !assurance_gaps.is_empty() {"unresolved"} else {"not-applicable"},
        "source":{"reference":MANIFEST,"revision":source_revision,"manifest_revision":manifest_revision},"strategy":strategy,"strategy_revision":strategy_revision,
        "execution":execution,"execution_requests":execution_requests,"record_requests":record_requests,"requests":[template],"assurance_applicability":assurance,"assurance_owner_gaps":assurance_gaps,"assurance_request":assurance_request,"authentication_request":authentication_request,"host_authentication":authentication,"capability_contract":contract,"evidence":evidence,"evidence_gaps":gaps,"selector_gaps":selector_gaps,
        "applicability_boundary":"Existing manifest path selectors only; task-marker and other configured owner applicability require current owner judgment, not native prose inference.",
        "judgment_request":packet,"contribution":{"owner":"verification","revision":source_revision,"blockers":blockers,"actions":execution_actions},
        "authority_effect":"read-only-no-claim-grants"}),
    )
}

pub(crate) fn disabled(target: &std::path::Path) -> Result<Value, CoreError> {
    crate::native_config::disabled_owner(
        target,
        "verification",
        &[
            MANIFEST,
            &format!("{RECEIPTS}/index.json"),
            ".agentic-workspace/local/independent-review-host-results/index.json",
        ],
        &["effect:proof-execution", "claim:complete"],
    )
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    #[ignore = "subprocess fixture for the bounded Git observation test"]
    fn git_probe_slow_fixture() {
        std::thread::sleep(std::time::Duration::from_secs(5));
    }

    #[test]
    fn git_observation_times_out_and_reaps_the_child() {
        let mut command = std::process::Command::new(std::env::current_exe().unwrap());
        command.args([
            "--exact",
            "native_verification::tests::git_probe_slow_fixture",
            "--ignored",
        ]);
        let started = std::time::Instant::now();
        let result = bounded_git_output(&mut command, std::time::Duration::from_millis(30));
        assert_eq!(result.unwrap_err(), "git-observation-timeout");
        assert!(started.elapsed() < std::time::Duration::from_secs(2));
    }
    use std::sync::atomic::{AtomicU64, Ordering};
    static SEQUENCE: AtomicU64 = AtomicU64::new(0);
    struct Repo(std::path::PathBuf);
    impl Repo {
        fn new() -> Self {
            let path = std::env::temp_dir().join(format!(
                "aw-native-verification-{}-{}",
                std::process::id(),
                SEQUENCE.fetch_add(1, Ordering::Relaxed)
            ));
            std::fs::create_dir_all(&path).unwrap();
            Self(path)
        }
        fn write(&self, path: &str, text: &str) {
            let path = self.0.join(path);
            std::fs::create_dir_all(path.parent().unwrap()).unwrap();
            std::fs::write(path, text).unwrap();
        }
    }
    impl Drop for Repo {
        fn drop(&mut self) {
            let _ = std::fs::remove_dir_all(&self.0);
        }
    }
    fn work() -> Value {
        json!({"kind":"current-work","id":"host-current-task-identity"})
    }
    fn get(repo: &Repo, paths: &[&str], request: Option<Value>) -> Value {
        view(
            &repo.0,
            "current exact task",
            &paths.iter().map(|s| (*s).into()).collect::<Vec<_>>(),
            &work(),
            None,
            request,
        )
        .unwrap()
    }
    #[test]
    fn absent_and_unrelated_direct_work_stay_quiet() {
        let repo = Repo::new();
        assert_eq!(get(&repo, &["notes.txt"], None)["status"], "not-applicable");
        repo.write(
            MANIFEST,
            include_str!("../../../.agentic-workspace/verification/manifest.toml"),
        );
        let result = get(&repo, &["unrelated/user-note.txt"], None);
        assert_eq!(result["status"], "not-applicable");
        assert!(result["judgment_request"].is_null());
        assert!(
            result["contribution"]["blockers"]
                .as_array()
                .unwrap()
                .is_empty()
        );
    }
    #[test]
    fn actual_manifest_retains_strategy_authority_and_no_claim_grant() {
        let repo = Repo::new();
        repo.write(
            MANIFEST,
            include_str!("../../../.agentic-workspace/verification/manifest.toml"),
        );
        let result = get(&repo, &["AGENTS.md"], None);
        assert_eq!(result["status"], "unresolved");
        let packet = &result["judgment_request"];
        assert_eq!(packet["task_identity"], work());
        assert_eq!(
            packet["work_ref"],
            crate::direct_task::subject("current exact task", &["AGENTS.md".into()]).unwrap()["id"]
        );
        assert_eq!(packet["work_revision"], packet["work_ref"]);
        assert!(
            packet["strategy"]["protocols"]["aw_context_consistency"]["authority_refs"].is_array()
        );
        assert!(packet["strategy"]["protocols"]["aw_context_consistency"]["stale_when"].is_array());
        assert!(result["capability_contract"]["claim_authorities"].is_null());
        let decision = crate::compile_value(json!({"intent":{},"capability_contract":result["capability_contract"],"contributions":[result["contribution"]]})).unwrap();
        assert!(
            decision["claim_boundary"]["allowed"]
                .as_array()
                .unwrap()
                .is_empty()
        );
    }
    #[test]
    fn public_claim_request_is_exact_and_cannot_supply_authority() {
        let repo = Repo::new();
        let quiet = get(&repo, &[], None);
        let request = quiet["requests"][0].clone();
        assert_eq!(
            get(&repo, &[], Some(request.clone()))["status"],
            "unresolved"
        );
        let mut other = request.clone();
        other["task_identity"]["id"] = json!("other-task");
        assert!(
            get(&repo, &[], Some(other))["evidence_gaps"]
                .as_array()
                .unwrap()
                .contains(&json!("verification-request-stale"))
        );
        let mut forged = request;
        forged["arguments"]["authenticated"] = json!(true);
        assert!(
            view(
                &repo.0,
                "current exact task",
                &[],
                &work(),
                None,
                Some(forged)
            )
            .is_err()
        );
    }
    #[test]
    fn receipt_source_freshness_is_not_producer_or_task_authority() {
        let repo = Repo::new();
        repo.write("a.txt", "one");
        let receipt = json!({"kind":"agentic-workspace/proof-receipt/v1","result":"passed",
            "task_claim_judgment":{"work_ref":"legacy-python-other-task","work_revision":"legacy-revision","claim_class":"slice_complete","status":"sufficient"},
            "proof_subject":{"kind":"agentic-workspace/proof-subject/v1","id":"proof-subject:example","identity_complete":true,
                "source_inputs":[{"path":"a.txt","sha256":sha(b"one")}]}});
        repo.write(&format!("{RECEIPTS}/example.json"), &receipt.to_string());
        let mut request = get(&repo, &["a.txt"], None)["requests"][0].clone();
        request["arguments"]["evidence_refs"] = json!(["proof://receipts/example"]);
        let current = get(&repo, &["a.txt"], Some(request.clone()));
        let gaps = current["evidence"][0]["gaps"].as_array().unwrap();
        assert!(gaps.contains(&json!("task-claim-mismatch-or-missing-identity")));
        assert!(gaps.contains(&json!("publication-index-unavailable-or-invalid")));
        assert!(!gaps.contains(&json!("proof-semantic-input-stale-or-unavailable")));
        repo.write("a.txt", "two");
        let stale = get(&repo, &["a.txt"], Some(request));
        assert!(
            stale["evidence"][0]["gaps"]
                .as_array()
                .unwrap()
                .contains(&json!("proof-semantic-input-stale-or-unavailable"))
        );
        assert_eq!(current["strategy_revision"], stale["strategy_revision"]);
    }
    #[test]
    fn planning_subject_is_preserved_and_material_revision_stales_request() {
        let repo = Repo::new();
        let subject = json!({"id":"planning:current","revision":"semantic-one","state":"returned"});
        let first = view(&repo.0, "task", &[], &work(), Some(&subject), None).unwrap();
        let request = first["requests"][0].clone();
        let mut same = subject.clone();
        same["state"] = json!("integration-pending");
        let same = view(
            &repo.0,
            "task",
            &[],
            &work(),
            Some(&same),
            Some(request.clone()),
        )
        .unwrap();
        assert_eq!(same["judgment_request"]["work_ref"], subject["id"]);
        assert_eq!(
            same["judgment_request"]["work_revision"],
            subject["revision"]
        );
        assert!(
            !same["evidence_gaps"]
                .as_array()
                .unwrap()
                .contains(&json!("verification-request-stale"))
        );
        let mut changed = subject;
        changed["revision"] = json!("semantic-two");
        let stale = view(&repo.0, "task", &[], &work(), Some(&changed), Some(request)).unwrap();
        assert!(
            stale["evidence_gaps"]
                .as_array()
                .unwrap()
                .contains(&json!("verification-request-stale"))
        );
    }
    #[test]
    fn invalid_manifest_cannot_disappear() {
        let repo = Repo::new();
        repo.write(MANIFEST, "not valid TOML");
        assert_eq!(get(&repo, &[], None)["status"], "unresolved");
    }

    #[test]
    fn actual_python_owner_publication_admits_without_granting_evidence() {
        let fixture: Value = serde_json::from_str(include_str!(
            "../../../tests/fixtures/native_verification_publication.json"
        ))
        .unwrap();
        let repo = Repo::new();
        repo.write("a.txt", "one");
        let id = fixture["publication_id"].as_str().unwrap();
        let path = format!("{RECEIPTS}/{id}.json");
        repo.write(&path, &fixture["receipt"].to_string());
        repo.write(
            &format!("{RECEIPTS}/index.json"),
            &fixture["index"].to_string(),
        );
        let root = Dir::open_ambient_dir(&repo.0, ambient_authority()).unwrap();
        let reference = format!("proof://receipts/{id}");
        let result = receipt_view(
            &root,
            &repo.0,
            &Value::Null,
            &reference,
            "Current fixture task",
            &["a.txt".into()],
            &json!({"id":"planning:current","revision":"semantic-one"}),
        );
        assert_eq!(result["publication_admission"]["status"], "admitted");
        assert_eq!(result["status"], "unadmitted");
        assert_eq!(result["evidence_freshness"], "unproven");
        assert_eq!(result["task_judgment"]["matched_judgment_count"], 0); // Former Planning judgment has no exact task binding.
        assert_eq!(result["task_judgment"]["current_judgment_count"], 0);
        assert_eq!(result["strategy_coverage"], "unproven");
        let unrelated = receipt_view(
            &root,
            &repo.0,
            &Value::Null,
            &reference,
            "Current fixture task",
            &["a.txt".into()],
            &json!({"id":"other-task","revision":"semantic-one"}),
        );
        assert_eq!(unrelated["publication_admission"]["status"], "admitted");
        assert!(
            unrelated["gaps"]
                .as_array()
                .unwrap()
                .contains(&json!("task-claim-mismatch-or-missing-identity"))
        );
        repo.write("a.txt", "changed");
        let stale = receipt_view(
            &root,
            &repo.0,
            &Value::Null,
            &reference,
            "Current fixture task",
            &["a.txt".into()],
            &json!({"id":"planning:current","revision":"semantic-one"}),
        );
        assert_eq!(stale["publication_admission"]["status"], "admitted");
        assert!(
            stale["gaps"]
                .as_array()
                .unwrap()
                .contains(&json!("proof-semantic-input-stale-or-unavailable"))
        );
        let mut tampered = fixture["receipt"].clone();
        tampered["result"] = json!("failed");
        repo.write(&path, &tampered.to_string());
        assert_eq!(
            publication_admission(&root, id, &tampered)["reason"],
            "publication-content-identity-mismatch"
        );
        for (field, value, reason) in [
            (
                "revision",
                json!("other"),
                "publication-owner-index-mismatch",
            ),
            (
                "path",
                json!("../other.json"),
                "publication-index-path-mismatch",
            ),
            (
                "superseded_by",
                json!("new-publication"),
                "publication-stale-or-superseded",
            ),
            (
                "superseded_by",
                json!(true),
                "publication-stale-or-superseded",
            ),
            ("status", json!(true), "publication-stale-or-superseded"),
        ] {
            let mut index = fixture["index"].clone();
            index["receipts"][id][field] = value;
            repo.write(&format!("{RECEIPTS}/index.json"), &index.to_string());
            assert_eq!(
                publication_admission(&root, id, &fixture["receipt"])["reason"],
                reason
            );
        }
    }

    #[test]
    fn historical_identity_encoding_is_exact_and_unsupported_numbers_are_gaps() {
        let fixture: Value = serde_json::from_str(include_str!(
            "../../../tests/fixtures/native_verification_publication.json"
        ))
        .unwrap();
        let identity: Value =
            serde_json::from_str(fixture["publication_identity_json"].as_str().unwrap()).unwrap();
        assert_eq!(
            publication_json(&identity).unwrap(),
            fixture["publication_identity_json"].as_str().unwrap()
        );
        assert_eq!(
            publication_json(&json!([0, -12, true, false, null, 1.25, -0.0, "\u{7f}🙂"])).unwrap(),
            "[0, -12, true, false, null, 1.25, -0.0, \"\\u007f\\ud83d\\ude42\"]"
        );
        assert!(publication_json(&json!(1e30)).is_err());
        assert!(publication_json(&json!(0.000001)).is_err());
    }
}
