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
    #[serde(default)]
    archive: String,
    #[serde(default)]
    admitted_revision: String,
    applicable_scope: Vec<String>,
    fallback: Option<Snapshot>,
    semantic_routes: Option<Value>,
}
#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct Snapshot {
    archive: String,
    admitted_revision: String,
}
fn empty_context(scope: &[String]) -> Value {
    json!({"records":[], "admissions":[], "current_dependencies":[], "applicable_scope":scope})
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
fn record(bytes: &[u8], path: &str, owner: &str) -> Result<Value, CoreError> {
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
    value["source"] = json!({"owner":owner, "reference":path, "revision":hash(bytes)});
    value["rationale_reference"] = json!(path);
    continuity::normalize(value)
}

fn load(input: &Input, owner: &str, routes: &[Value]) -> Result<Value, CoreError> {
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
        return Ok(empty_context(&input.applicable_scope));
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
        let bytes = git(input, &["show".into(), spec.into()])?;
        if bytes.len() > 262144 {
            return Err(error("decision source exceeds bounded read"));
        }
        let normalized = record(&bytes, path, owner)?;
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
                || record["semantic_routes"]
                    .as_array()
                    .is_some_and(|declared| declared.iter().any(|id| routes.contains(id)))
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
        dependencies.insert(format!("{owner}:{path}"), normalized["source"].clone());
        records.push(normalized);
    }
    Ok(json!({"records":records, "admissions":admissions,
        "current_dependencies":dependencies.into_values().collect::<Vec<_>>(),
        "applicable_scope":input.applicable_scope
    }))
}

/// Trusted source-owner input. Native and fallback admissions are independent;
/// a record cannot choose its owner or assert that another owner has its value.
pub fn view(value: Value) -> Result<Value, CoreError> {
    let input: Input = serde_json::from_value(value).map_err(error)?;
    let (route_view, intent) = if let Some(routes) = &input.semantic_routes {
        let (view, intent) = crate::semantic_routes::resolve(routes.clone())?;
        (Some(view), intent)
    } else {
        (None, json!({}))
    };
    let selected = route_view
        .as_ref()
        .and_then(|v| v["decision"]["semantic_task_routes"]["routes"].as_array())
        .cloned()
        .unwrap_or_default();
    let finish = |context: Option<Value>| -> Result<Value, CoreError> {
        let mut value = json!({"contributions":[], "intent":intent});
        if let Some(context) = context {
            value["decision_context"] = context;
        }
        let mut result = compile_value(value)?;
        if let Some(view) = &route_view {
            result["semantic_route_result"] = view.clone();
        }
        Ok(result)
    };
    if input.applicable_scope.is_empty() && selected.is_empty() {
        return finish(None);
    }
    let mut fallback = if let Some(source) = &input.fallback {
        load(
            &Input {
                target: input.target.clone(),
                archive: source.archive.clone(),
                admitted_revision: source.admitted_revision.clone(),
                applicable_scope: input.applicable_scope.clone(),
                fallback: None,
                semantic_routes: None,
            },
            "memory",
            &selected,
        )?
    } else {
        empty_context(&input.applicable_scope)
    };
    let has_residue = !fallback["records"].as_array().unwrap().is_empty();
    let native_configured = !input.archive.is_empty();
    let native = if native_configured {
        match load(&input, "repository", &selected) {
            Ok(context) => context,
            // A failed destination cannot hide already admitted useful fallback.
            // The existing reconciliation contract exposes the pending owner.
            Err(_) if has_residue => empty_context(&input.applicable_scope),
            Err(e) => return Err(e),
        }
    } else {
        empty_context(&input.applicable_scope)
    };
    if !has_residue {
        return finish(Some(native));
    }
    let residue: Vec<_> = fallback["records"]
        .as_array()
        .unwrap()
        .iter()
        .map(|r| r["id"].clone())
        .collect();
    let destinations = if native_configured {
        native["admissions"].clone()
    } else {
        fallback["admissions"].clone()
    };
    // Keep the fallback semantic value until the preferred owner admits that
    // exact value. A same-ID/different-revision destination is not promotion.
    for key in ["records", "admissions"] {
        let rows = fallback[key].as_array_mut().unwrap();
        for row in native[key].as_array().unwrap() {
            if !rows.iter().any(|existing| existing["id"] == row["id"]) {
                rows.push(row.clone());
            }
        }
    }
    let mut current = BTreeMap::new();
    for row in fallback["current_dependencies"]
        .as_array()
        .unwrap()
        .iter()
        .chain(native["current_dependencies"].as_array().unwrap())
    {
        let key = (
            row["owner"].as_str().unwrap().to_owned(),
            row["reference"].as_str().unwrap().to_owned(),
        );
        if current
            .insert(key, row.clone())
            .is_some_and(|prior| prior != *row)
        {
            return Err(error(
                "source dependency changed during owner reconciliation",
            ));
        }
    }
    fallback["current_dependencies"] = json!(current.into_values().collect::<Vec<_>>());
    fallback["reconciliation"] = json!({"residue":residue, "native_owner":if native_configured {Some("repository")} else {None}, "fallback_owner":"memory", "destinations":destinations, "dismissals":[]});
    finish(Some(fallback))
}
