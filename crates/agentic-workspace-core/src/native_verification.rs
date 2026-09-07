//! Current Verification source and evidence visibility. This reader does not
//! authenticate producers, publish receipts, execute checks, or grant claims.
use crate::{CoreError, digest, prepare_request_value};
use cap_std::{ambient_authority, fs::Dir};
use serde_json::{Value, json};
use sha2::{Digest, Sha256};
use std::{io::Read, path::Path};

const MANIFEST: &str = ".agentic-workspace/verification/manifest.toml";
const RECEIPTS: &str = ".agentic-workspace/proof/receipts";

fn read(root: &Dir, path: &str) -> Result<Option<Vec<u8>>, String> {
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
    let mut identity = serde_json::Map::new();
    for field in ["command", "result", "changed_paths", "proof_subject"] {
        identity.insert(field.into(), receipt[field].clone());
    }
    identity.insert(
        "target_context".into(),
        receipt.get("target_context").cloned().unwrap_or(json!({})),
    );
    identity.insert(
        "proof_commands".into(),
        receipt.get("proof_commands").cloned().unwrap_or(json!([])),
    );
    for field in [
        "task_claim_judgment",
        "assignment_proof_obligation",
        "assignment_proof_binding",
        "assignment_closeout_lineage",
    ] {
        if let Some(value) = receipt.get(field) {
            identity.insert(field.into(), value.clone());
        }
    }
    let rendered = match publication_json(&Value::Object(identity)) {
        Ok(text) => text,
        Err(reason) => return rejected(reason),
    };
    let expected = sha(rendered.as_bytes());
    if &expected[..16] != id || receipt["publication_id"] != id {
        return rejected("publication-content-identity-mismatch");
    }
    json!({"status":"admitted","reason":"current-indexed-owner-publication","authority_effect":"publication-only"})
}

fn receipt_view(
    root: &Dir,
    reference: &str,
    task: &str,
    changed: &[String],
    work_ref: &Value,
    work_revision: &Value,
) -> Value {
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
    let judgment = crate::task_judgment::view(json!({
        "action":"classify", "task":task, "changed_paths":changed, "work_ref":work_ref, "work_revision":work_revision,
        "observations":[{"receipt":receipt, "publication_current":publication["status"] == "admitted",
            "proof_sufficient":admission["proof_sufficient"] == true, "evidence_freshness":"unproven"}],
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
    gaps.extend(
        [
            "proof-runtime-compatibility-unproven",
            "current-strategy-coverage-unproven",
        ]
        .map(str::to_owned),
    );
    json!({"reference":reference,"status":"unadmitted","publication_admission":publication,"receipt_admission":admission,
        "task_judgment":judgment,"evidence_freshness":"unproven","strategy_coverage":"unproven","independent_review":"not-established-by-publication",
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
        "input_schema":arguments_schema}]);
    let owner_revision = digest(&requests)?;
    let mut contract = json!({"kind":"agentic-workspace/capability-contract/v1","revision":"pending",
        "owners":[{"owner":"verification","revision":owner_revision,"requests":requests}],
        "restriction_authorities":[{"owner":"verification","affects":["claim:complete"]}]});
    contract["revision"] = json!(digest(&contract)?);
    let template = json!({"kind":"agentic-workspace/public-request/v1","id":"verification/claim/v1","owner":"verification",
        "owner_revision":owner_revision,"source_revision":source_revision,"capability_revision":contract["revision"],
        "task_identity":current_work,"request_kind":"verification/claim/v1","arguments":{"claim_class":"slice_complete","evidence_refs":[]}});
    let mut evidence = Vec::new();
    let mut requested = false;
    if let Some(request) = request {
        prepare_request_value(
            json!({"request":request,"current_work":request["task_identity"],"capability_contract":contract}),
        )?;
        if request["owner"] != "verification" {
            return Err(CoreError::new("Verification request names another owner"));
        }
        requested = true;
        if request["task_identity"] != *current_work
            || request["source_revision"] != source_revision
        {
            gaps.push("verification-request-stale".into());
        } else if let Some(refs) = request["arguments"]["evidence_refs"].as_array() {
            evidence.extend(
                refs.iter()
                    .filter_map(Value::as_str)
                    .map(|r| receipt_view(&root, r, task, changed, &work_ref, &work_revision)),
            );
        }
    }
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
        "admitted_automated_evidence":[],"candidate_evidence":evidence,"known_uncertainty":gaps,
        "required_authority":"Use each selected protocol's review_owner and authority_refs; authenticate any independent producer through the existing Verification owner.",
        "judgment_ingress":"Existing Verification receipt admission; this read-only native view does not admit returned judgments.",
        "returned_judgment_requirements":["exact claim and current work/subject","current strategy and evidence references","judgment and unresolved reasons","required producer authority and independence"]}));
    let blockers = if applicable {
        json!([{"code":"verification-evidence-unresolved","message":"Current Verification obligations require admitted task-bound evidence and judgment.","affects":["claim:complete"]}])
    } else {
        json!([])
    };
    Ok(
        json!({"kind":"agentic-workspace/native-verification-view/v1","status":if applicable {"unresolved"} else {"not-applicable"},
        "source":{"reference":MANIFEST,"revision":source_revision,"manifest_revision":manifest_revision},"strategy":strategy,"strategy_revision":strategy_revision,
        "requests":[template],"capability_contract":contract,"evidence":evidence,"evidence_gaps":gaps,"selector_gaps":selector_gaps,
        "applicability_boundary":"Existing manifest path selectors only; task-marker and other configured owner applicability require current owner judgment, not native prose inference.",
        "judgment_request":packet,"contribution":{"owner":"verification","revision":source_revision,"blockers":blockers},
        "authority_effect":"read-only-no-claim-grants"}),
    )
}

#[cfg(test)]
mod tests {
    use super::*;
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
            &reference,
            "Current fixture task",
            &["a.txt".into()],
            &json!("planning:current"),
            &json!("semantic-one"),
        );
        assert_eq!(result["publication_admission"]["status"], "admitted");
        assert_eq!(result["status"], "unadmitted");
        assert_eq!(result["evidence_freshness"], "unproven");
        assert_eq!(result["task_judgment"]["matched_judgment_count"], 0); // Former Planning judgment has no exact task binding.
        assert_eq!(result["task_judgment"]["current_judgment_count"], 0);
        assert_eq!(result["strategy_coverage"], "unproven");
        let unrelated = receipt_view(
            &root,
            &reference,
            "Current fixture task",
            &["a.txt".into()],
            &json!("other-task"),
            &json!("semantic-one"),
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
            &reference,
            "Current fixture task",
            &["a.txt".into()],
            &json!("planning:current"),
            &json!("semantic-one"),
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
