//! Dependency-scoped proof identity. Runtime observations belong to the host
//! producer; building or comparing a subject does not authenticate evidence.
use crate::CoreError;
use cap_std::{ambient_authority, fs::Dir};
use serde_json::{Value, json};
use sha2::{Digest, Sha256};
use std::{collections::BTreeSet, io::Read, path::Path};

const KIND: &str = "agentic-workspace/proof-subject/v1";
const PREFIXES: [&str; 3] = [
    ".agentic-workspace/proof/receipts/",
    ".agentic-workspace/proof/manifests/",
    ".agentic-workspace/planning/closeout-evidence/",
];
fn trim(value: &str) -> &str {
    value.trim_matches(|c: char| c.is_whitespace() || ('\u{1c}'..='\u{1f}').contains(&c))
}
fn normalized(value: &str) -> String {
    trim(&value.replace('\\', "/")).into()
}
fn normalized_set(values: &[String]) -> BTreeSet<String> {
    values
        .iter()
        .map(|v| normalized(v))
        .filter(|s| !s.is_empty())
        .collect()
}

pub fn dependency_role(path: &str, explicit: &[String]) -> Value {
    let path = normalized(path);
    if normalized_set(explicit).contains(&path) {
        return json!({"path":path,"owner":"claim","role":"semantic-input","reason":"explicit-claim-dependency"});
    }
    let owner = if path.starts_with(PREFIXES[0]) {
        "canonical-proof-receipt-publication"
    } else if path.starts_with(PREFIXES[2]) {
        "planning-closeout-evidence-publication"
    } else {
        "claim"
    };
    let output = PREFIXES.iter().any(|prefix| path.starts_with(prefix));
    json!({"path":path,"owner":owner,"role":if output {"evidence-output"} else {"semantic-input"},
        "reason":if output {"proof-owned-publication-output"} else {"declared-proof-subject-input"}})
}

fn file_digest(root: Option<&Dir>, path: &str) -> Option<String> {
    let root = root?;
    if path.is_empty()
        || path.contains(':')
        || path.split('/').any(|p| matches!(p, "" | "." | ".."))
    {
        return None;
    }
    let mut prefix = std::path::PathBuf::new();
    for part in path.split('/') {
        prefix.push(part);
        let metadata = root.symlink_metadata(&prefix).ok()?;
        #[cfg(windows)]
        let linked = {
            use cap_std::fs::MetadataExt;
            metadata.file_attributes() & 0x400 != 0
        };
        #[cfg(not(windows))]
        let linked = metadata.is_symlink();
        if linked {
            return None;
        }
    }
    let mut file = root.open(path).ok()?;
    let mut hash = Sha256::new();
    let mut buffer = [0_u8; 65536];
    loop {
        let count = file.read(&mut buffer).ok()?;
        if count == 0 {
            break;
        }
        hash.update(&buffer[..count]);
    }
    Some(format!("{:x}", hash.finalize()))
}

pub(crate) fn compact_json(value: &Value) -> Result<String, CoreError> {
    match value {
        Value::Number(number)
            if number.is_f64()
                && (number.to_string().contains(['e', 'E'])
                    || number
                        .as_f64()
                        .is_none_or(|v| v != 0.0 && !(0.0001..1e16).contains(&v.abs()))) =>
        {
            return Err(CoreError::new(
                "proof identity numeric encoding compatibility is unproven",
            ));
        }
        Value::Array(values) => {
            for value in values {
                compact_json(value)?;
            }
        }
        Value::Object(values) => {
            for value in values.values() {
                compact_json(value)?;
            }
        }
        _ => (),
    }
    let encoded = serde_json::to_string(value).map_err(|e| CoreError::new(e.to_string()))?;
    // Python's legacy ensure_ascii compact encoding also escapes DEL. JSON
    // serialization already escaped controls, quotes and literal backslashes.
    let mut ascii = String::new();
    for ch in encoded.chars() {
        if ch >= '\u{7f}' {
            for unit in ch.encode_utf16(&mut [0; 2]) {
                ascii.push_str(&format!("\\u{unit:04x}"));
            }
        } else {
            ascii.push(ch);
        }
    }
    Ok(ascii)
}

pub(crate) fn fingerprint(value: &Value) -> Result<String, CoreError> {
    Ok(format!(
        "{:x}",
        Sha256::digest(compact_json(value)?.as_bytes())
    ))
}

#[allow(clippy::too_many_arguments)]
pub fn build(
    target: &Path,
    changed_paths: &[String],
    command: &str,
    claim_classes: Option<&[String]>,
    effect_scope: Option<&[String]>,
    semantic_input_paths: &[String],
    runtime: &Value,
) -> Result<Value, CoreError> {
    if !runtime.is_object() || runtime.as_object().is_none_or(|v| v.is_empty()) {
        return Err(CoreError::new("proof runtime observations are required"));
    }
    let default_claims = vec!["executable-validation".into()];
    let claims: BTreeSet<_> = claim_classes
        .filter(|v| !v.is_empty())
        .unwrap_or(&default_claims)
        .iter()
        .map(|s| trim(s).to_owned())
        .filter(|s| !s.is_empty())
        .collect();
    let paths = normalized_set(changed_paths);
    let roles: Vec<_> = paths
        .iter()
        .map(|path| dependency_role(path, semantic_input_paths))
        .collect();
    let semantic: Vec<String> = roles
        .iter()
        .filter(|v| v["role"] == "semantic-input")
        .map(|v| v["path"].as_str().unwrap().to_owned())
        .collect();
    let outputs: Vec<_> = roles
        .iter()
        .filter(|v| v["role"] == "evidence-output")
        .cloned()
        .collect();
    let root = Dir::open_ambient_dir(target, ambient_authority()).ok();
    let mut sources = vec![];
    let mut unavailable = vec![];
    for path in &semantic {
        match file_digest(root.as_ref(), path) {
            Some(hash) => sources.push(json!({"path":path,"sha256":hash})),
            None => unavailable.push(path.clone()),
        }
    }
    let manual = !claims.is_empty()
        && claims
            .iter()
            .all(|v| matches!(v.as_str(), "manual-review" | "documentation-review"));
    let complete = (!sources.is_empty() && unavailable.is_empty())
        || (semantic.is_empty() && manual && effect_scope.is_some_and(|v| !v.is_empty()));
    let effects: BTreeSet<_> =
        normalized_set(effect_scope.filter(|v| !v.is_empty()).unwrap_or(&semantic))
            .into_iter()
            .filter(|p| dependency_role(p, semantic_input_paths)["role"] == "semantic-input")
            .collect();
    let mut value = json!({"claim_classes":claims,"effect_scope":effects,"source_inputs":sources,
        "command_sha256":format!("{:x}",Sha256::digest(trim(command).as_bytes())),"runtime":runtime,
        "identity_complete":complete,"unavailable_inputs":unavailable});
    let hash = fingerprint(&value)?;
    let object = value.as_object_mut().unwrap();
    object.extend(json!({"kind":KIND,"id":format!("proof-subject:{}",&hash[..20]),"fingerprint":hash,"dependency_roles":roles,
        "evidence_outputs":outputs,"dependency_scope":"declared-path-and-command","fallback":if complete {"not-required"} else {"whole-state-required"},
        "rule":"Only declared semantic inputs participate in proof freshness; proof-owned publication outputs are diagnostic unless this claim explicitly declares them as semantic inputs."}).as_object().unwrap().clone());
    Ok(value)
}

pub fn compare(stored: &Value, current: &Value, minimum_rerun: &str) -> Value {
    let fingerprint_present = |subject: &Value| {
        subject["fingerprint"].as_str().is_some_and(|v| {
            v.len() == 64
                && v.bytes()
                    .all(|c| c.is_ascii_digit() || (b'a'..=b'f').contains(&c))
        })
    };
    let (status, reason) = if stored["kind"] != KIND || current["kind"] != KIND {
        ("unverifiable", "proof-subject-kind-mismatch")
    } else if stored["identity_complete"] != true
        || current["identity_complete"] != true
        || !fingerprint_present(stored)
        || !fingerprint_present(current)
    {
        ("unverifiable", "incomplete-subject-identity")
    } else if stored["claim_classes"] != current["claim_classes"] {
        ("incompatible", "claim-class-changed")
    } else if stored["fingerprint"] == current["fingerprint"] {
        ("reusable", "subject-fingerprint-match")
    } else {
        let paths = |subject: &Value| -> BTreeSet<String> {
            subject["source_inputs"]
                .as_array()
                .into_iter()
                .flatten()
                .filter_map(|v| v["path"].as_str().map(str::to_owned))
                .collect()
        };
        if paths(stored).is_disjoint(&paths(current)) {
            ("partially-reusable", "independent-subject-scope")
        } else {
            ("stale", "dependency-input-changed")
        }
    };
    json!({"status":status,"reasons":[reason],"minimum_rerun_command":if status == "reusable" {""} else {minimum_rerun}})
}

pub fn view(value: Value) -> Result<Value, CoreError> {
    let schema = crate::source_schema();
    let mut shape = schema["$defs"]["proof_subject_input"].clone();
    shape["$schema"] = schema["$schema"].clone();
    crate::schema_validator(&shape, "proof subject")?
        .validate(&value)
        .map_err(|e| {
            CoreError::new(format!(
                "invalid proof subject input at {}",
                e.instance_path()
            ))
        })?;
    let strings = |field: &str| -> Option<Vec<String>> {
        value[field]
            .as_array()
            .map(|v| v.iter().map(|s| s.as_str().unwrap().to_owned()).collect())
    };
    match value["action"].as_str().unwrap() {
        "classify-many" => {
            let paths = strings("changed_paths").unwrap();
            let mut results = Vec::new();
            for receipt in value["receipts"].as_array().unwrap() {
                let command = trim(receipt["command"].as_str().unwrap_or(""));
                let stored = &receipt["proof_subject"];
                if stored["kind"] != KIND {
                    results.push(json!({"status":"unverifiable","reasons":["legacy-receipt-without-proof-subject"],"minimum_rerun_command":command,
                        "rule":"Legacy receipts remain visible for migration but cannot demonstrate dependency-scoped equivalence."}));
                } else {
                    let current = build(
                        Path::new(value["target"].as_str().unwrap()),
                        &paths,
                        command,
                        None,
                        None,
                        &[],
                        &value["runtime"],
                    )?;
                    results.push(compare(stored, &current, command));
                }
            }
            Ok(json!({"results":results}))
        }
        "dependency-role" => Ok(dependency_role(
            value["path"].as_str().unwrap(),
            &strings("semantic_input_paths").unwrap_or_default(),
        )),
        "compare" => Ok(compare(
            &value["stored"],
            &value["current"],
            value["minimum_rerun_command"].as_str().unwrap_or(""),
        )),
        action => {
            let command = value["command"].as_str().unwrap();
            let stored = &value["receipt"]["proof_subject"];
            if action == "classify" && stored["kind"] != KIND {
                return Ok(
                    json!({"status":"unverifiable","reasons":["legacy-receipt-without-proof-subject"],"minimum_rerun_command":command,
                    "rule":"Legacy receipts remain visible for migration but cannot demonstrate dependency-scoped equivalence."}),
                );
            }
            let subject = build(
                Path::new(value["target"].as_str().unwrap()),
                &strings("changed_paths").unwrap(),
                value["command"].as_str().unwrap(),
                strings("claim_classes").as_deref(),
                strings("effect_scope").as_deref(),
                &strings("semantic_input_paths").unwrap_or_default(),
                &value["runtime"],
            )?;
            Ok(if action == "classify" {
                compare(stored, &subject, command)
            } else {
                subject
            })
        }
    }
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
                "aw-proof-subject-{}-{}",
                std::process::id(),
                SEQUENCE.fetch_add(1, Ordering::Relaxed)
            ));
            std::fs::create_dir_all(&path).unwrap();
            Self(path)
        }
        fn write(&self, path: &str, content: &str) {
            let path = self.0.join(path);
            std::fs::create_dir_all(path.parent().unwrap()).unwrap();
            std::fs::write(path, content).unwrap();
        }
    }
    impl Drop for Repo {
        fn drop(&mut self) {
            let _ = std::fs::remove_dir_all(&self.0);
        }
    }
    #[test]
    fn original_python_subjects_keep_exact_bytes_and_metadata() {
        let vectors: Value = serde_json::from_str(include_str!(
            "../../../tests/fixtures/proof_subject_identity.json"
        ))
        .unwrap();
        for vector in vectors.as_array().unwrap() {
            let repo = Repo::new();
            for (path, content) in vector["files"].as_object().unwrap() {
                repo.write(path, content.as_str().unwrap());
            }
            let mut request = vector["input"].clone();
            request["action"] = json!("build");
            request["target"] = json!(repo.0);
            request["runtime"] = vector["runtime"].clone();
            let actual = view(request).unwrap();
            assert_eq!(actual, vector["expected"]);
            assert_eq!(
                compare(&vector["expected"], &actual, "check")["status"],
                if actual["identity_complete"] == true {
                    "reusable"
                } else {
                    "unverifiable"
                }
            );
        }
    }
    #[test]
    fn outside_paths_do_not_become_semantic_inputs() {
        let repo = Repo::new();
        repo.write("outside.txt", "private");
        std::fs::create_dir_all(repo.0.join("inside")).unwrap();
        let subject = build(
            &repo.0.join("inside"),
            &[
                "../outside.txt".into(),
                repo.0.join("outside.txt").to_string_lossy().into_owned(),
            ],
            "check",
            None,
            None,
            &[],
            &json!({"implementation":"test-host","version":"observed"}),
        )
        .unwrap();
        assert_eq!(subject["identity_complete"], false);
        assert_eq!(subject["source_inputs"], json!([]));
    }
    #[test]
    fn native_runtime_observation_is_not_python_and_material_changes_stale() {
        let repo = Repo::new();
        repo.write("a.txt", "one");
        let first = build(
            &repo.0,
            &["a.txt".into()],
            "check",
            None,
            None,
            &[],
            &json!({"implementation":"native-executable","version":"observed-binary-hash"}),
        )
        .unwrap();
        let second=build(&repo.0,&["a.txt".into()],"check",None,None,&[],&json!({"implementation":"native-executable","version":"different-observed-binary-hash"})).unwrap();
        assert_eq!(first["runtime"]["implementation"], "native-executable");
        assert_eq!(compare(&first, &second, "check")["status"], "stale");
        assert!(build(&repo.0, &[], "check", None, None, &[], &Value::Null).is_err());
    }

    #[test]
    fn malformed_fingerprints_never_create_reusable_subjects() {
        for fingerprint in [
            Value::Null,
            json!(""),
            json!("same"),
            json!("g".repeat(64)),
            json!("a".repeat(63)),
            json!(12),
        ] {
            let subject = json!({"kind":KIND,"identity_complete":true,"claim_classes":["executable-validation"],"fingerprint":fingerprint});
            assert_eq!(
                compare(&subject, &subject, "check")["status"],
                "unverifiable"
            );
        }
        let missing = json!({"kind":KIND,"identity_complete":true,"claim_classes":[]});
        assert_eq!(
            compare(&missing, &missing, "check")["status"],
            "unverifiable"
        );
    }
}
