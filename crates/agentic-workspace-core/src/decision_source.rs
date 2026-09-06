//! Read-only adapter for a host-admitted repository decision snapshot.
//! The host's exact Git revision admits provenance; neither a working-tree
//! record, its actor strings, nor Git tracking alone supplies that authority.
use crate::{CoreError, compile_value, continuity};
use cap_std::{ambient_authority, fs::Dir};
use serde::Deserialize;
use serde_json::{Value, json};
use sha2::{Digest, Sha256};
use std::{
    collections::{BTreeMap, BTreeSet},
    io::Read,
    process::Command,
};

#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct Input {
    target: String,
    archive: String,
    admitted_revision: String,
    applicable_scope: Vec<String>,
}
fn error(value: impl ToString) -> CoreError {
    CoreError::new(value.to_string())
}
fn relative(path: &str) -> Result<(), CoreError> {
    if path.is_empty()
        || path.contains(['\\', ':', '\0', '\n'])
        || path
            .split('/')
            .any(|part| part.is_empty() || part == "." || part == ".." || part == ".git")
    {
        return Err(error(
            "decision source requires an exact repository-relative path",
        ));
    }
    Ok(())
}
fn git(input: &Input, arguments: &[String]) -> Result<Vec<u8>, CoreError> {
    let output = Command::new("git")
        .arg("-C")
        .arg(&input.target)
        .args(arguments)
        .env("GIT_LITERAL_PATHSPECS", "1")
        .output()
        .map_err(error)?;
    if !output.status.success() {
        return Err(error(
            "admitted decision snapshot unavailable; preserve source and reconcile",
        ));
    }
    Ok(output.stdout)
}
fn hash(bytes: &[u8]) -> String {
    format!(
        "sha256:{:x}",
        Sha256::digest(
            String::from_utf8_lossy(bytes)
                .replace("\r\n", "\n")
                .as_bytes()
        )
    )
}
fn read(root: &Dir, path: &str) -> Result<Vec<u8>, CoreError> {
    relative(path)?;
    let mut bytes = Vec::new();
    root.open(path)
        .map_err(error)?
        .take(262145)
        .read_to_end(&mut bytes)
        .map_err(error)?;
    if bytes.len() > 262144 {
        return Err(error("decision source exceeds bounded read"));
    }
    std::str::from_utf8(&bytes).map_err(error)?;
    Ok(bytes)
}
fn record(bytes: &[u8], path: &str) -> Result<Value, CoreError> {
    let text = std::str::from_utf8(bytes).map_err(error)?;
    let marker = "```aw-decision\n";
    let text = text.replace("\r\n", "\n");
    let (_, rest) = text
        .split_once(marker)
        .ok_or_else(|| error("decision source lacks typed record"))?;
    let (body, tail) = rest
        .split_once("\n```")
        .ok_or_else(|| error("unclosed decision record"))?;
    if tail.contains(marker) {
        return Err(error("multiple decision records in one source"));
    }
    let mut value: Value = serde_json::from_str(body).map_err(error)?;
    if value.get("source").is_some() || value.get("rationale_reference").is_some() {
        return Err(error("source identity belongs to the repository adapter"));
    }
    value["source"] = json!({"owner":"repository", "reference":path, "revision":hash(bytes)});
    value["rationale_reference"] = json!(path);
    continuity::normalize(value)
}

/// Trusted host API, never an ordinary client request or operation argument.
/// One optional Markdown encoding is supported; no archive location is assumed.
pub fn view(value: Value) -> Result<Value, CoreError> {
    let input: Input = serde_json::from_value(value).map_err(error)?;
    if input.applicable_scope.is_empty() {
        return compile_value(json!({"contributions":[], "intent":{}}));
    }
    relative(input.archive.trim_end_matches('/'))?;
    if input.admitted_revision.len() != 40
        || !input
            .admitted_revision
            .bytes()
            .all(|c| c.is_ascii_hexdigit())
    {
        return Err(error(
            "repository decision provenance requires an independently admitted exact Git commit",
        ));
    }
    // Discover only this optional record encoding. Relevance is determined
    // from parsed JSON, never from its textual escaping or task substrings.
    let mut args = vec![
        "grep".into(),
        "-l".into(),
        "-z".into(),
        "-F".into(),
        "-e".into(),
        "```aw-decision".into(),
    ];
    args.extend([
        input.admitted_revision.clone(),
        "--".into(),
        input.archive.clone(),
    ]);
    let found = Command::new("git")
        .arg("-C")
        .arg(&input.target)
        .args(&args)
        .env("GIT_LITERAL_PATHSPECS", "1")
        .output()
        .map_err(error)?;
    if found.status.code() == Some(1) {
        return compile_value(json!({"contributions":[], "intent":{}}));
    }
    if !found.status.success() {
        return Err(error(
            "decision source selection failed; reconcile admission",
        ));
    }
    let candidates: Vec<_> = found
        .stdout
        .split(|b| *b == 0)
        .filter(|p| !p.is_empty())
        .collect();
    if candidates.len() > 64 {
        return Err(error(
            "admitted archive exceeds 64 sources; select a bounded source archive",
        ));
    }
    let root = Dir::open_ambient_dir(&input.target, ambient_authority()).map_err(error)?;
    let mut available = BTreeMap::new();
    let mut admissions = Vec::new();
    let mut dependencies = BTreeMap::new();
    for candidate in candidates {
        let spec = std::str::from_utf8(candidate).map_err(error)?;
        let (_, path) = spec
            .split_once(':')
            .ok_or_else(|| error("invalid decision source identity"))?;
        relative(path)?;
        let bytes = git(&input, &["show".into(), spec.into()])?;
        if bytes.len() > 262144 {
            return Err(error("decision source exceeds bounded read"));
        }
        let normalized = record(&bytes, path)?;
        let id = normalized["id"].as_str().unwrap().to_owned();
        if available
            .insert(id, (normalized, bytes, path.to_owned()))
            .is_some()
        {
            return Err(error("duplicate decision identity in admitted archive"));
        }
    }
    let mut selected = BTreeSet::new();
    let mut pending: Vec<_> = available
        .iter()
        .filter(|(_, (record, _, _))| {
            record["scope"]
                .as_array()
                .unwrap()
                .iter()
                .any(|s| input.applicable_scope.iter().any(|v| s == v))
        })
        .map(|(id, _)| id.clone())
        .collect();
    while let Some(id) = pending.pop() {
        if !selected.insert(id.clone()) {
            continue;
        }
        let (record, _, _) = available
            .get(&id)
            .ok_or_else(|| error("supersession closure is incomplete in admitted archive"))?;
        pending.extend(
            record["supersedes"]
                .as_array()
                .unwrap()
                .iter()
                .map(|r| r["id"].as_str().unwrap().to_owned()),
        );
    }
    let mut records = Vec::new();
    for id in selected {
        let (normalized, bytes, path) = available.remove(&id).unwrap();
        if hash(&read(&root, &path)?) != hash(&bytes) {
            return Err(error(format!(
                "stale decision source {path}; reconcile exact provenance before contribution"
            )));
        }
        for dependency in normalized["authority"]["basis"]
            .as_array()
            .unwrap()
            .iter()
            .chain(normalized["dependencies"].as_array().unwrap())
            .chain(normalized["context"].as_array().unwrap())
        {
            let reference = dependency["reference"].as_str().unwrap();
            // This adapter observes repository bytes only. Other authority
            // providers require their own host adapter, never copied assertions.
            if dependency["owner"] != "repository" {
                continue;
            }
            if let Ok(bytes) = read(&root, reference) {
                dependencies.insert(
                    reference.to_owned(),
                    json!({"owner":"repository", "reference":reference, "revision":hash(&bytes)}),
                );
            }
        }
        admissions.push(json!({"id":normalized["id"], "material_revision":normalized["material_revision"], "source":normalized["source"], "rationale_reference":path}));
        records.push(normalized);
    }
    compile_value(json!({"contributions":[], "intent":{}, "decision_context":{
        "records":records, "admissions":admissions,
        "current_dependencies":dependencies.into_values().collect::<Vec<_>>(),
        "applicable_scope":input.applicable_scope
    }}))
}
