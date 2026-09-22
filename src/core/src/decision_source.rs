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
    io::{BufRead, BufReader, Read, Write},
    process::{Command, Stdio},
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
pub(crate) fn relative(path: &str) -> Result<(), CoreError> {
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
/// Directory-valued archive inputs accept one optional trailing separator.
/// Validate before use and return the same confined identity to every consumer;
/// exact file references and changed paths continue to use `relative` directly.
pub(crate) fn archive_relative<'a>(path: &'a str, field: &str) -> Result<&'a str, CoreError> {
    let canonical = path.strip_suffix('/').unwrap_or(path);
    relative(canonical).map_err(|_| {
        error(format!(
            "{field} requires a confined repository-relative archive directory with at most one trailing slash"
        ))
    })?;
    Ok(canonical)
}

fn admitted_blobs(
    input: &Input,
    candidates: &[&[u8]],
) -> Result<Vec<(String, Vec<u8>)>, CoreError> {
    let mut child = Command::new("git")
        .arg("-C")
        .arg(&input.target)
        .args(["cat-file", "--batch"])
        .env("GIT_LITERAL_PATHSPECS", "1")
        .stdin(Stdio::piped())
        .stdout(Stdio::piped())
        .stderr(Stdio::null())
        .spawn()
        .map_err(error)?;
    let result = (|| {
        let mut request = child.stdin.take().unwrap();
        let mut response = BufReader::new(child.stdout.take().unwrap());
        let mut blobs = Vec::with_capacity(candidates.len());
        for candidate in candidates {
            let spec = std::str::from_utf8(candidate).map_err(error)?;
            let (_, path) = spec
                .split_once(':')
                .ok_or_else(|| error("invalid decision source identity"))?;
            relative(path)?;
            writeln!(request, "{spec}").map_err(error)?;
            request.flush().map_err(error)?;
            let mut header = Vec::new();
            response
                .by_ref()
                .take(128)
                .read_until(b'\n', &mut header)
                .map_err(error)?;
            let fields: Vec<_> = std::str::from_utf8(&header)
                .map_err(error)?
                .split_whitespace()
                .collect();
            if header.last() != Some(&b'\n') || fields.len() != 3 || fields[1] != "blob" {
                return Err(error(
                    "admitted decision blob unavailable; reconcile admission",
                ));
            }
            let size = fields[2].parse::<usize>().map_err(error)?;
            if size > 262144 {
                return Err(error("decision source exceeds bounded read"));
            }
            let mut bytes = vec![0; size];
            response.read_exact(&mut bytes).map_err(error)?;
            let mut delimiter = [0];
            response.read_exact(&mut delimiter).map_err(error)?;
            if delimiter[0] != b'\n' {
                return Err(error("invalid admitted decision blob boundary"));
            }
            blobs.push((path.to_owned(), bytes));
        }
        Ok(blobs)
    })();
    if result.is_err() {
        let _ = child.kill();
    }
    let status = child.wait().map_err(error)?;
    if !status.success() && result.is_ok() {
        return Err(error(
            "admitted decision snapshot unavailable; preserve source and reconcile",
        ));
    }
    result
}
pub(crate) fn hash(bytes: &[u8]) -> String {
    format!(
        "sha256:{:x}",
        Sha256::digest(
            String::from_utf8_lossy(bytes)
                .replace("\r\n", "\n")
                .as_bytes()
        )
    )
}
pub(crate) const MAX_SOURCE_BYTES: usize = 262144;
pub(crate) fn read(root: &Dir, path: &str) -> Result<Vec<u8>, CoreError> {
    let bytes = read_bytes(root, path)?;
    std::str::from_utf8(&bytes).map_err(error)?;
    Ok(bytes)
}
fn read_bytes(root: &Dir, path: &str) -> Result<Vec<u8>, CoreError> {
    relative(path)?;
    let mut bytes = Vec::new();
    root.open(path)
        .map_err(error)?
        .take((MAX_SOURCE_BYTES + 1) as u64)
        .read_to_end(&mut bytes)
        .map_err(error)?;
    if bytes.len() > MAX_SOURCE_BYTES {
        return Err(error("decision source exceeds bounded read"));
    }
    Ok(bytes)
}
fn read_repository_source(root: &Dir, path: &str) -> Result<Vec<u8>, CoreError> {
    repository_metadata(root, path)?;
    read(root, path)
}
fn repository_metadata(root: &Dir, path: &str) -> Result<cap_std::fs::Metadata, CoreError> {
    relative(path)?;
    let mut current = std::path::PathBuf::new();
    for part in path.split('/') {
        current.push(part);
        let metadata = root.symlink_metadata(&current).map_err(error)?;
        #[cfg(windows)]
        let linked = {
            use cap_std::fs::MetadataExt;
            metadata.file_attributes() & 0x400 != 0
        };
        #[cfg(not(windows))]
        let linked = metadata.is_symlink();
        if linked {
            return Err(error(format!(
                "linked decision source {path} is not admitted; reconcile exact provenance"
            )));
        }
    }
    root.symlink_metadata(path).map_err(error)
}
pub(crate) fn record(bytes: &[u8], path: &str, owner: &str) -> Result<Value, CoreError> {
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

/// Working bytes can reveal a missing admission, never supply one. Inspect only
/// the configured destination, with the same confinement as admitted sources.
fn destination_only(
    input: &Input,
    archive: &str,
    routes: &[Value],
    required: &[Value],
    publications: &[Value],
) -> Result<Value, CoreError> {
    let missing = |source: &str| {
        error(format!(
            "assurance.decision_record_revision is missing for {source} (destination {archive}); only the repository/source owner can admit an exact archive Git commit"
        ))
    };
    if !required.is_empty() {
        return Err(missing(archive));
    }
    let root = Dir::open_ambient_dir(&input.target, ambient_authority()).map_err(error)?;
    match root.symlink_metadata(archive) {
        Err(e) if e.kind() == std::io::ErrorKind::NotFound => {
            return Ok(empty_context(&input.applicable_scope));
        }
        Err(e) => return Err(error(e)),
        Ok(_) => {}
    }
    let mut pending = vec![archive.to_owned()];
    let mut observed = 0usize;
    let mut bytes_read = 0usize;
    while let Some(path) = pending.pop() {
        observed += 1;
        if observed > 4096 {
            return Err(error(
                "decision destination discovery exceeds bounded observation",
            ));
        }
        let metadata = repository_metadata(&root, &path)?;
        if metadata.is_dir() {
            for entry in root.read_dir(&path).map_err(error)? {
                let name = entry.map_err(error)?.file_name();
                let name = name
                    .to_str()
                    .ok_or_else(|| error("decision source path is not UTF-8"))?;
                let child = format!("{path}/{name}");
                relative(&child)?;
                pending.push(child);
                if pending.len() + observed > 4096 {
                    return Err(error(
                        "decision destination discovery exceeds bounded observation",
                    ));
                }
            }
            continue;
        }
        if !metadata.is_file() {
            return Err(error("decision destination contains a non-regular source"));
        }
        let bytes = read_bytes(&root, &path)?;
        bytes_read += bytes.len();
        if bytes_read > MAX_SOURCE_BYTES * 64 {
            return Err(error("decision destination discovery exceeds bounded read"));
        }
        if !bytes
            .windows(b"```aw-decision".len())
            .any(|w| w == b"```aw-decision")
        {
            continue;
        }
        // A current native publication has independently checked custody. It
        // remains source-owned without being converted into archive admission.
        if publications
            .iter()
            .any(|source| source["reference"] == path && source["revision"] == hash(&bytes))
        {
            continue;
        }
        let normalized = record(&bytes, &path, "repository").map_err(|_| missing(&path))?;
        if normalized["scope"]
            .as_array()
            .unwrap()
            .iter()
            .any(|s| input.applicable_scope.iter().any(|p| s == p))
            || normalized["semantic_routes"]
                .as_array()
                .is_some_and(|declared| declared.iter().any(|route| routes.contains(route)))
        {
            return Err(missing(&path));
        }
    }
    Ok(empty_context(&input.applicable_scope))
}

fn load(
    input: &Input,
    owner: &str,
    routes: &[Value],
    required: &[Value],
    publications: &[Value],
) -> Result<Value, CoreError> {
    let field = if owner == "repository" {
        "assurance.decision_record_target (decision source archive)"
    } else {
        "assurance.decision_record_fallback.archive (decision source fallback.archive)"
    };
    let archive = archive_relative(&input.archive, field)?;
    let revision_field = if owner == "repository" {
        "assurance.decision_record_revision"
    } else {
        "assurance.decision_record_fallback.admitted_revision"
    };
    if owner == "repository" && input.admitted_revision.is_empty() {
        return destination_only(input, archive, routes, required, publications);
    }
    if input.admitted_revision.len() != 40
        || !input
            .admitted_revision
            .bytes()
            .all(|c| c.is_ascii_hexdigit())
    {
        return Err(error(format!(
            "repository decision provenance for {archive} requires an independently admitted exact Git commit in {revision_field}; only the source owner can admit it"
        )));
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
        archive.to_owned(),
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
        return Err(error(format!(
            "decision source selection failed for {archive}; the repository/source owner must reconcile {revision_field} with an available exact archive Git commit"
        )));
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
    for (path, bytes) in admitted_blobs(input, &candidates)? {
        let normalized = record(&bytes, &path, owner)?;
        let id = normalized["id"].as_str().unwrap().to_owned();
        if available
            .insert(id, (normalized, bytes, path.to_owned()))
            .is_some()
        {
            return Err(error("duplicate decision identity in admitted archive"));
        }
    }
    let mut selected = BTreeSet::new();
    for ancestor in required {
        let record = &available
            .get(ancestor["id"].as_str().unwrap())
            .ok_or_else(|| {
                error("Required supersession ancestor is absent from the admitted archive")
            })?
            .0;
        if record["material_revision"] != ancestor["material_revision"]
            || record["source"] != ancestor["source"]
        {
            return Err(error(
                "Required supersession ancestor differs from its bound source admission",
            ));
        }
    }
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
    pending.extend(
        required
            .iter()
            .map(|record| record["id"].as_str().unwrap().to_owned()),
    );
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
        if hash(&read_repository_source(&root, &path)?) != hash(&bytes) {
            return Err(error(format!(
                "stale decision source {path}; the repository/source owner must reconcile exact provenance and {revision_field} before contribution"
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
            if let Ok(bytes) = read_repository_source(&root, reference) {
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
    let (input, route_view) = resolve(value)?;
    let mut result = compile_value(input)?;
    if let Some(view) = route_view {
        result["semantic_route_result"] = view;
    }
    Ok(result)
}

/// Preserve the owner input for one final composition with other current owners.
pub(crate) fn resolve(value: Value) -> Result<(Value, Option<Value>), CoreError> {
    resolve_with_native(value, None)
}

pub(crate) fn resolve_with_native(
    value: Value,
    native_fallback: Option<Value>,
) -> Result<(Value, Option<Value>), CoreError> {
    resolve_with_publications(value, native_fallback, None)
}
pub(crate) fn resolve_with_publications(
    value: Value,
    native_fallback: Option<Value>,
    repository_publications: Option<Value>,
) -> Result<(Value, Option<Value>), CoreError> {
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
    let finish = |context: Option<Value>| -> Result<(Value, Option<Value>), CoreError> {
        let mut value = json!({"contributions":[], "intent":intent});
        if let Some(context) = context {
            value["decision_context"] = context;
        }
        Ok((value, route_view.clone()))
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
            native_fallback
                .as_ref()
                .and_then(|v| v["required_records"].as_array())
                .map(Vec::as_slice)
                .unwrap_or(&[]),
            &[],
        )?
    } else {
        empty_context(&input.applicable_scope)
    };
    if let Some(native) = native_fallback {
        for field in ["records", "admissions", "current_dependencies"] {
            for row in native[field].as_array().into_iter().flatten() {
                let rows = fallback[field].as_array_mut().unwrap();
                if !rows.contains(row) {
                    rows.push(row.clone());
                }
            }
        }
    }
    let has_residue = !fallback["records"].as_array().unwrap().is_empty();
    let native_configured = !input.archive.is_empty();
    let mut native = if native_configured {
        match load(
            &input,
            "repository",
            &selected,
            repository_publications
                .as_ref()
                .and_then(|v| v["required_records"].as_array())
                .map(Vec::as_slice)
                .unwrap_or(&[]),
            repository_publications
                .as_ref()
                .and_then(|v| v["publication_sources"].as_array())
                .map(Vec::as_slice)
                .unwrap_or(&[]),
        ) {
            Ok(context) => context,
            // A failed destination cannot hide already admitted useful fallback.
            // The existing reconciliation contract exposes the pending owner.
            Err(_) if has_residue => empty_context(&input.applicable_scope),
            Err(e) => return Err(e),
        }
    } else {
        empty_context(&input.applicable_scope)
    };
    if let Some(published) = repository_publications {
        for field in ["records", "admissions", "current_dependencies"] {
            for row in published[field].as_array().into_iter().flatten() {
                let rows = native[field].as_array_mut().unwrap();
                if !rows.contains(row) {
                    rows.push(row.clone());
                }
            }
        }
    }
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

const READ_KIND: &str = "decision-continuity/read-current-source/v1";
const READ_OWNER: &str = "decision-continuity";
/// Retrieval adapts existing admitted identity; it creates no authority or state.
pub(crate) fn read_contract() -> Result<Value, CoreError> {
    let canonical: Value = serde_json::from_str(include_str!(
        "../contracts/schemas/source_decision_input.schema.json"
    ))
    .map_err(error)?;
    let mut shape = canonical["$defs"]["decision_source_read_request"].clone();
    shape["$schema"] = canonical["$schema"].clone();
    shape["$defs"] = json!({"decision_admission":canonical["$defs"]["decision_admission"],"decision_reference":canonical["$defs"]["decision_reference"]});
    let declaration = json!({"kind":READ_KIND,"result_kind":"agentic-workspace/decision-source-read-result/v1","input_schema":shape});
    let mut contract = json!({"kind":"agentic-workspace/capability-contract/v1","revision":"pending","owners":[{"owner":READ_OWNER,"revision":crate::digest(&declaration)?,"requests":[declaration]}]});
    contract["restriction_authorities"] = json!([{"owner":READ_OWNER,"affects":["task"]}]);
    contract["revision"] = json!(crate::digest(&contract)?);
    Ok(contract)
}
/// Only the existing selected closure can be read. The continuity projection
/// owns currentness and supersession; reading historical rationale does not.
pub(crate) fn public_read(
    target: &std::path::Path,
    context: &Value,
    decision: &Value,
    work: &Value,
    contract: &Value,
    request: Option<&Value>,
) -> Result<Value, CoreError> {
    let revision =
        crate::digest(&json!({"context":context,"projection":decision["decision_context"]}))?;
    let owner = contract["owners"]
        .as_array()
        .into_iter()
        .flatten()
        .find(|o| o["owner"] == READ_OWNER)
        .ok_or_else(|| error("decision read owner missing"))?;
    let selected: Vec<_> = context["admissions"]
        .as_array()
        .into_iter()
        .flatten()
        .filter(|admission| {
            matches!(
                admission["source"]["owner"].as_str(),
                Some("repository" | "memory")
            ) && decision["decision_context"]["states"]
                .as_array()
                .into_iter()
                .flatten()
                .any(|state| {
                    state["id"] == admission["id"]
                        && state["material_revision"] == admission["material_revision"]
                        && state["source"] == admission["source"]
                })
        })
        .cloned()
        .collect();
    let requests:Vec<_>=selected.iter().map(|admission| json!({"kind":"agentic-workspace/public-request/v1","id":format!("decision/read:{}",admission["id"].as_str().unwrap()),"owner":READ_OWNER,"owner_revision":owner["revision"],"source_revision":revision,"capability_revision":contract["revision"],"task_identity":work,"request_kind":READ_KIND,"arguments":admission})).collect();
    let mut result = json!({"requests":requests,"source_revision":revision});
    if let Some(request) = request {
        crate::prepare_request_value(
            json!({"request":request,"current_work":work,"capability_contract":contract}),
        )?;
        if request["owner"] != READ_OWNER
            || request["source_revision"] != revision
            || !selected.contains(&request["arguments"])
        {
            return Err(error(
                "decision source read is stale or outside the current selected scope",
            ));
        }
        let source = &request["arguments"]["source"];
        let path = source["reference"]
            .as_str()
            .ok_or_else(|| error("decision source reference missing"))?;
        let root = Dir::open_ambient_dir(target, ambient_authority()).map_err(error)?;
        let bytes = read_repository_source(&root, path)?;
        if hash(&bytes) != source["revision"] {
            return Err(error(
                "decision source changed during read; reconcile current owner",
            ));
        }
        // Validate only the bounded already-observed dependencies, not the archive.
        for dependency in context["current_dependencies"]
            .as_array()
            .into_iter()
            .flatten()
            .filter(|d| d["owner"] == "repository")
        {
            let reference = dependency["reference"]
                .as_str()
                .ok_or_else(|| error("decision dependency reference missing"))?;
            if hash(&read_repository_source(&root, reference)?) != dependency["revision"] {
                return Err(error(
                    "decision dependency changed during read; reconcile current owner",
                ));
            }
        }
        let state = decision["decision_context"]["states"]
            .as_array()
            .into_iter()
            .flatten()
            .find(|state| state["id"] == request["arguments"]["id"])
            .ok_or_else(|| error("decision scope changed during read"))?;
        result["response"] = json!({"kind":"agentic-workspace/decision-source-read-result/v1","status":"read","source":source,"decision_state":state,"body":std::str::from_utf8(&bytes).map_err(error)?,"authority_effect":"no-new-authority"});
    }
    Ok(result)
}

#[cfg(test)]
mod path_tests {
    use super::*;

    #[test]
    fn archive_directories_preserve_exact_source_confinement() {
        for path in ["docs/adr", ".agentic-workspace/memory/repo/decisions"] {
            assert_eq!(archive_relative(path, "archive").unwrap(), path);
            assert_eq!(
                archive_relative(&format!("{path}/"), "archive").unwrap(),
                path
            );
            assert!(relative(path).is_ok());
            assert!(relative(&format!("{path}/")).is_err());
        }
        for path in [
            "",
            "/",
            "/docs/adr",
            "//host/archive",
            concat!("C:", "/docs/adr"),
            "C:adr",
            "docs\\adr",
            "docs/../adr",
            "./adr",
            "docs/./adr",
            "docs//adr",
            "docs/adr//",
            ".git/objects",
            "docs/.git/objects",
            "docs/\0adr",
            "docs/\nadr",
        ] {
            assert!(relative(path).is_err(), "exact source accepted {path:?}");
            let error = archive_relative(path, "assurance.decision_record_target").unwrap_err();
            assert!(
                error
                    .to_string()
                    .contains("assurance.decision_record_target")
            );
            if !path.is_empty() {
                assert!(archive_relative(&format!("{path}/"), "archive").is_err());
            }
        }
    }
}
