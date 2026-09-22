//! Assignment-specific text deltas. Baselines come from the sealed owner packet,
//! never from worker-authored preimages or the checkout's cumulative dirty state.
use crate::{CoreError, digest};
use serde_json::{Value, json};
use std::collections::BTreeSet;

const MAX_BYTES: usize = 262144;
pub(crate) const REQUEST: &str = "assignment/integrate-patch/v1";
pub(crate) const OP: &str = "assignment.integrate-patch";

pub(crate) fn declaration() -> Value {
    json!({"kind":REQUEST,"result_kind":"agentic-workspace/patch-integration/v1","input_schema":{"$schema":"https://json-schema.org/draft/2020-12/schema","type":"object","additionalProperties":false,"required":["proposal_revision"],"properties":{"proposal_revision":{"type":"string"}}}})
}
pub(crate) fn operation() -> Value {
    json!({"id":OP,"semantic_revision":"native-patch-integration-v1","input_schema":{"$schema":"https://json-schema.org/draft/2020-12/schema","type":"object","additionalProperties":false,"required":["target","proposal"],"properties":{"target":{"type":"string"},"proposal":{"type":"object"}}},"effects":["implementation"],"reads":["assignment"],"result_kind":"agentic-workspace/patch-integration/v1"})
}

pub(crate) fn result_schema() -> Value {
    let path = json!({"type":"string","minLength":1,"maxLength":256});
    let revision = json!({"type":"string","pattern":"^sha256:[a-f0-9]{64}$"});
    json!({"type":"object","additionalProperties":false,"required":["kind","status","delta_revision","changed_paths","execution_custody","postimages","proof_authority","completion_authority"],"properties":{"kind":{"const":"agentic-workspace/patch-integration/v1"},"status":{"const":"integrated"},"delta_revision":revision,"changed_paths":{"type":"array","maxItems":8,"uniqueItems":true,"items":path},"execution_custody":{"type":"object"},"postimages":{"type":"array","maxItems":8,"items":{"type":"object","additionalProperties":false,"required":["path","revision"],"properties":{"path":path,"revision":revision}}},"proof_authority":{"const":false},"completion_authority":{"const":false}}})
}

fn marker(source: &str) -> Result<String, CoreError> {
    Ok(format!(
        ".agentic-workspace/local/patch-integrations/{}.json",
        &digest(&json!(source))?[7..]
    ))
}

fn outcome(invocation: &Value) -> Value {
    let proposal = &invocation["arguments"]["proposal"];
    json!({"status":"applied","effects":["implementation"],"value":{"kind":"agentic-workspace/patch-integration/v1","status":"integrated","delta_revision":proposal["delta_revision"],"changed_paths":proposal["files"].as_array().into_iter().flatten().map(|f| f["path"].clone()).collect::<Vec<_>>(),"execution_custody":proposal["execution_custody"],"postimages":proposal["files"].as_array().into_iter().flatten().map(|f| json!({"path":f["path"],"revision":crate::native_intent::hash(f["after"].as_str().unwrap().as_bytes())})).collect::<Vec<_>>(),"proof_authority":false,"completion_authority":false}})
}

fn retained(target: &std::path::Path, source: &str) -> Result<Option<Value>, CoreError> {
    let root =
        cap_std::fs::Dir::open_ambient_dir(target, cap_std::ambient_authority()).map_err(error)?;
    let Some(bytes) = crate::native_verification::read(&root, &marker(source)?).map_err(error)?
    else {
        return Ok(None);
    };
    let mut held: Value = serde_json::from_slice(&bytes).map_err(error)?;
    let prepared = crate::attempt_store::prepare_commit(
        &target.to_string_lossy(),
        held["custody"].clone(),
        held["outcome"].clone(),
    )?;
    if prepared["record"]["invocation"] != held["invocation"]
        || held["invocation"]["source_owner"] != "assignment"
        || held["invocation"]["operation_id"] != OP
        || held["outcome"] != outcome(&held["invocation"])
    {
        return Err(error(
            "patch recovery lacks exact producer custody; preserved",
        ));
    }
    if crate::native_verification::read(
        &root,
        prepared["custody"]["committed"]["path"].as_str().unwrap(),
    )
    .map_err(error)?
    .is_some()
    {
        crate::attempt_store::inspect_committed(
            &target.to_string_lossy(),
            prepared["custody"].clone(),
        )?;
        held["custody"] = prepared["custody"].clone();
    }
    Ok(Some(held))
}

/// A result judgment permits use of that result, but a current exact proposal
/// and the ordinary implementation restrictions still decide each write.
pub(crate) fn view(
    target: &std::path::Path,
    work: &Value,
    admission: &Value,
    submitted: &[Value],
    contract: &Value,
    executing: bool,
) -> Result<Value, CoreError> {
    let request = submitted.iter().find(|r| r["request_kind"] == REQUEST);
    if admission["result_use_allowed"] != true || admission["delta"].is_null() {
        if request.is_some() {
            return Err(error(
                "current admitted patch result required before integration",
            ));
        }
        return Ok(json!({"status":"not-ready","requests":[],"action":null}));
    }
    let root =
        cap_std::fs::Dir::open_ambient_dir(target, cap_std::ambient_authority()).map_err(error)?;
    let held = request
        .map(|r| retained(target, r["source_revision"].as_str().unwrap_or("")))
        .transpose()?
        .flatten();
    let mut files = Vec::new();
    for file in admission["delta"]["files"].as_array().unwrap() {
        let path = file["path"].as_str().unwrap();
        let bytes = crate::native_verification::read(&root, path)
            .map_err(error)?
            .ok_or_else(|| error("patch target disappeared; source preserved"))?;
        let current = std::str::from_utf8(&bytes).map_err(error)?;
        let after = match merge(
            file["before"].as_str().unwrap(),
            file["after"].as_str().unwrap(),
            current,
        ) {
            Ok(value) => value,
            Err(e) if request.is_none() => {
                return Ok(
                    json!({"status":"repair-required","reason":e.to_string(),"requests":[],"action":null}),
                );
            }
            Err(e) => return Err(e),
        };
        let before = if let Some(held) = &held {
            let retained = held["invocation"]["arguments"]["proposal"]["files"]
                .as_array()
                .and_then(|v| v.iter().find(|f| f["path"] == path))
                .ok_or_else(|| error("patch recovery subject changed"))?;
            if retained["after"] != after
                || (retained["before"] != current && retained["after"] != current)
                || (!held["custody"]["committed"].is_null() && retained["after"] != current)
            {
                return Err(error(
                    "patch recovery target differs from exact before/postimage; preserved",
                ));
            }
            retained["before"]
                .as_str()
                .ok_or_else(|| error("patch recovery before image missing"))?
                .to_owned()
        } else {
            current.to_owned()
        };
        files.push(json!({"path":path,"before":before,"after":after}));
    }
    let proposal = json!({"delta_revision":admission["delta"]["revision"],"execution_custody":admission["execution_custody"],"files":files});
    let source = digest(
        &json!({"work":work,"admission":admission["source_revision"],"judgment":admission["judgment"],"proposal":proposal}),
    )?;
    let owner = contract["owners"]
        .as_array()
        .unwrap()
        .iter()
        .find(|o| o["owner"] == "assignment")
        .unwrap();
    let template = json!({"kind":"agentic-workspace/public-request/v1","id":REQUEST,"owner":"assignment","owner_revision":owner["revision"],"source_revision":source,"capability_revision":contract["revision"],"task_identity":work,"request_kind":REQUEST,"arguments":{"proposal_revision":digest(&proposal)?}});
    if let Some(request) = request {
        crate::prepare_request_value(
            json!({"request":request,"current_work":work,"capability_contract":contract}),
        )?;
        if *request != template {
            return Err(error("patch integration proposal or authority changed"));
        }
        let completed = held
            .as_ref()
            .filter(|h| !h["custody"]["committed"].is_null());
        if let Some(held) = completed
            && !executing
        {
            return Ok(
                json!({"status":"integrated","proposal":proposal,"requests":[],"action":null,"result":held["outcome"]["value"],"custody":held["custody"]}),
            );
        }
        Ok(
            json!({"status":"integration-ready","proposal":proposal,"requests":[],"action":{"operation_id":OP,"dependency_revision":source,"arguments":{"target":target,"proposal":proposal},"effects":["implementation"],"source_requests":submitted}}),
        )
    } else {
        let mut requests = submitted.to_vec();
        requests.push(template);
        Ok(
            json!({"status":"proposal-ready","proposal":proposal,"requests":[requests],"action":null}),
        )
    }
}

pub(crate) fn execute(
    target: &std::path::Path,
    decision: &Value,
    invocation: &Value,
    mut revalidate: impl FnMut() -> Result<(), CoreError>,
) -> Result<Value, CoreError> {
    use cap_std::fs::OpenOptions;
    use std::io::Write;
    let root =
        cap_std::fs::Dir::open_ambient_dir(target, cap_std::ambient_authority()).map_err(error)?;
    let lock_path = ".agentic-workspace/local/effects/patch-integration.lock";
    crate::native_verification::read(&root, lock_path).map_err(error)?;
    root.create_dir_all(".agentic-workspace/local/effects")
        .map_err(error)?;
    crate::native_verification::read(&root, lock_path).map_err(error)?;
    let lock = root
        .open_with(
            lock_path,
            OpenOptions::new().read(true).write(true).create(true),
        )
        .map_err(error)?
        .into_std();
    if lock.metadata().map_err(error)?.len() != 0 {
        return Err(error("unrecognized patch integration lock preserved"));
    }
    lock.try_lock().map_err(error)?;
    revalidate()?;
    let request = invocation["source_requests"]
        .as_array()
        .and_then(|v| v.iter().find(|r| r["request_kind"] == REQUEST))
        .ok_or_else(|| error("exact integration request missing"))?;
    let source = request["source_revision"]
        .as_str()
        .ok_or_else(|| error("integration source revision missing"))?;
    let held = retained(target, source)?;
    let out = outcome(invocation);
    let envelope = serde_json::to_vec(&json!({"invocation":invocation,"outcome":out}))
        .map_err(error)?
        .len()
        + 3 * serde_json::to_vec(&target).map_err(error)?.len()
        + 16384;
    if envelope > crate::native_verification::MAX_SOURCE_BYTES {
        return Err(error(
            "complete patch recovery carrier exceeds its bounded reader",
        ));
    }
    if held
        .as_ref()
        .is_some_and(|h| h["invocation"] != *invocation)
    {
        return Err(error("patch integration custody collision; preserved"));
    }
    let admission = crate::attempt_store::admit(
        json!({"target":target,"decision":decision,"invocation":invocation,"custody":held.as_ref().map(|h| &h["custody"])}),
    )?;
    if admission["disposition"] == "replay" {
        return Ok(
            json!({"outcome":admission["record"]["outcome"],"custody":admission["custody"],
                "post_effect_changed_paths":admission["record"]["outcome"]["value"]["changed_paths"]}),
        );
    }
    if admission["disposition"] != "execute"
        && !(admission["disposition"] == "uncertain" && held.is_some())
    {
        return Err(error("patch integration requires exact recovery"));
    }
    if held.is_none() {
        let path = marker(source)?;
        root.create_dir_all(std::path::Path::new(&path).parent().unwrap())
            .map_err(error)?;
        let carrier = serde_json::to_vec(
            &json!({"invocation":invocation,"custody":admission["custody"],"outcome":out}),
        )
        .map_err(error)?;
        if carrier.len() > crate::native_verification::MAX_SOURCE_BYTES {
            return Err(error("patch recovery carrier exceeds reader bound"));
        }
        let mut f = root
            .open_with(&path, OpenOptions::new().write(true).create_new(true))
            .map_err(error)?;
        f.write_all(&carrier).map_err(error)?;
        f.sync_all().map_err(error)?;
    }
    for file in invocation["arguments"]["proposal"]["files"]
        .as_array()
        .unwrap()
    {
        let path = file["path"].as_str().unwrap();
        let before = file["before"].as_str().unwrap().as_bytes();
        let after = file["after"].as_str().unwrap().as_bytes();
        let current = crate::native_verification::read(&root, path)
            .map_err(error)?
            .ok_or_else(|| error("patch target disappeared"))?;
        if current == after {
            continue;
        }
        if current != before {
            return Err(error("patch target changed before publication; preserved"));
        }
        let temporary = format!("{path}.{}.tmp", &digest(invocation)?[7..]);
        if let Some(bytes) = crate::native_verification::read(&root, &temporary).map_err(error)? {
            if held.is_none() || bytes != after {
                return Err(error("unowned patch temporary preserved"));
            }
        } else {
            let mut f = root
                .open_with(&temporary, OpenOptions::new().write(true).create_new(true))
                .map_err(error)?;
            f.set_permissions(root.metadata(path).map_err(error)?.permissions())
                .map_err(error)?;
            f.write_all(after).map_err(error)?;
            f.sync_all().map_err(error)?;
        }
        revalidate()?;
        if crate::native_verification::read(&root, path)
            .map_err(error)?
            .as_deref()
            != Some(before)
        {
            return Err(error("patch target changed at publication; preserved"));
        }
        root.rename(&temporary, &root, path).map_err(error)?;
    }
    revalidate()?;
    for file in invocation["arguments"]["proposal"]["files"]
        .as_array()
        .unwrap()
    {
        if crate::native_verification::read(&root, file["path"].as_str().unwrap())
            .map_err(error)?
            .as_deref()
            != Some(file["after"].as_str().unwrap().as_bytes())
        {
            return Err(error(
                "patch postimage changed before completion; preserved",
            ));
        }
    }
    let committed = crate::attempt_store::commit(
        json!({"target":target,"custody":admission["custody"],"outcome":out}),
    )?;
    Ok(json!({"outcome":out,"custody":committed["custody"],
        "post_effect_changed_paths":out["value"]["changed_paths"]}))
}

fn error(value: impl ToString) -> CoreError {
    CoreError::new(value.to_string())
}

pub(crate) fn concrete(path: &str) -> Result<(), CoreError> {
    crate::decision_source::relative(path)?;
    if path.split('/').next().is_some_and(|p| {
        p.eq_ignore_ascii_case(".agentic-workspace") || p.eq_ignore_ascii_case(".git")
    }) {
        return Err(error(
            "AW-owned sources and custody require their dedicated owner operation",
        ));
    }
    if path.len() > 256
        || path.contains(['*', '?', '[', ']', '\r', '\t'])
        || path.split('/').any(|p| p.ends_with(['.', ' ']))
    {
        return Err(error(
            "patch subjects require concrete relative paths, not selectors",
        ));
    }
    Ok(())
}

pub(crate) fn concrete_source(target: &std::path::Path, path: &str) -> Result<(), CoreError> {
    concrete(path)?;
    let root = target.canonicalize().map_err(error)?;
    let resolved = target.join(path).canonicalize().map_err(error)?;
    let relative = resolved
        .strip_prefix(&root)
        .map_err(|_| error("mutation source escapes target"))?;
    let normalized = relative.to_string_lossy().replace('\\', "/");
    if if cfg!(windows) {
        !normalized.eq_ignore_ascii_case(path)
    } else {
        normalized != path
    } {
        return Err(error(
            "mutation paths must name their canonical relative source",
        ));
    }
    if relative.components().next().is_some_and(|part| {
        let name = part.as_os_str().to_string_lossy();
        name.eq_ignore_ascii_case(".agentic-workspace") || name.eq_ignore_ascii_case(".git")
    }) {
        return Err(error(
            "aliased AW source requires its dedicated owner operation",
        ));
    }
    Ok(())
}

fn normalize(text: &str) -> Result<String, CoreError> {
    if text.len() > MAX_BYTES || text.contains('\0') {
        return Err(error("patch text exceeds the bounded UTF-8 text contract"));
    }
    let normalized = text.replace("\r\n", "\n");
    if normalized.contains('\r') {
        return Err(error(
            "bare carriage returns are outside the patch text contract",
        ));
    }
    Ok(normalized)
}

/// Strict positional application: diffy's tolerant search must not relocate a
/// worker's hunk to some other matching occurrence in the captured source.
fn apply_exact(base: &str, patch: &diffy::Patch<'_, str>) -> Result<String, CoreError> {
    let lines: Vec<_> = base.split_inclusive('\n').collect();
    let mut position = 0;
    let mut output = String::new();
    for hunk in patch.hunks() {
        let old = hunk.old_range();
        let start = if old.is_empty() {
            old.start()
        } else {
            old.start()
                .checked_sub(1)
                .ok_or_else(|| error("invalid patch line zero"))?
        };
        if start < position || start > lines.len() {
            return Err(error("patch hunks overlap or exceed the captured baseline"));
        }
        output.extend(lines[position..start].iter().copied());
        let new = hunk.new_range();
        let expected_new = if new.is_empty() {
            new.start()
        } else {
            new.start()
                .checked_sub(1)
                .ok_or_else(|| error("invalid new patch line zero"))?
        };
        if output.split_inclusive('\n').count() != expected_new {
            return Err(error(
                "patch new hunk position differs from its exact delta",
            ));
        }
        position = start;
        for line in hunk.lines() {
            match line {
                diffy::Line::Context(text) | diffy::Line::Delete(text) => {
                    if lines.get(position) != Some(text) {
                        return Err(error("patch hunk differs from the exact captured baseline"));
                    }
                    position += 1;
                    if matches!(line, diffy::Line::Context(_)) {
                        output.push_str(text);
                    }
                }
                diffy::Line::Insert(text) => output.push_str(text),
            }
        }
        if output.len() > MAX_BYTES {
            return Err(error("patch postimage exceeds the text bound"));
        }
    }
    output.extend(lines[position..].iter().copied());
    if output.len() > MAX_BYTES {
        return Err(error("patch postimage exceeds the text bound"));
    }
    Ok(output)
}

/// The public patch format is a JSON array of per-file unified deltas. Each
/// element names one concrete baseline input and contains exactly one diff.
/// This avoids ambiguous splitting when removed source lines resemble headers.
pub(crate) fn delta(packet: &Value, returned: &Value) -> Result<Value, CoreError> {
    let encoded = returned["patch"]
        .as_str()
        .ok_or_else(|| error("patch text required"))?;
    if encoded.len() > MAX_BYTES {
        return Err(error("patch return exceeds the bounded transport"));
    }
    let patches: Value = serde_json::from_str(encoded).map_err(error)?;
    let patches = patches
        .as_array()
        .filter(|v| v.len() <= 8)
        .ok_or_else(|| error("patch must contain at most eight file deltas"))?;
    let mutation_paths = &packet["assignment_identity"]["mutation_paths"];
    let capsule = &packet["assignment_identity"]["input_capsule"];
    let mut paths = BTreeSet::new();
    let mut aliases = BTreeSet::new();
    let mut files = Vec::new();
    let mut total = 0;
    for item in patches {
        if item
            .as_object()
            .is_none_or(|v| v.len() != 2 || !v.contains_key("path") || !v.contains_key("diff"))
        {
            return Err(error("each file delta contains only path and diff"));
        }
        let path = item["path"]
            .as_str()
            .ok_or_else(|| error("patch path required"))?;
        concrete(path)?;
        let alias = if cfg!(windows) {
            path.to_lowercase()
        } else {
            path.to_owned()
        };
        if !aliases.insert(alias) {
            return Err(error("patch subjects alias the same concrete path"));
        }
        if !paths.insert(path.to_owned())
            || !mutation_paths
                .as_array()
                .is_some_and(|v| v.iter().any(|p| p == path))
            || !packet["scope"].as_array().is_some_and(|v| {
                v.iter()
                    .filter_map(Value::as_str)
                    .any(|p| crate::native_verification::matches(p, path))
            })
        {
            return Err(error(
                "patch path is duplicate or outside the sealed concrete mutation scope",
            ));
        }
        let baseline = capsule
            .as_array()
            .and_then(|v| v.iter().find(|i| i["reference"] == path))
            .ok_or_else(|| error("patch lacks owner-captured baseline"))?;
        let before = baseline["content"]
            .as_str()
            .ok_or_else(|| error("patch baseline must be captured UTF-8 text"))?;
        let normalized = normalize(before)?;
        let diff = normalize(
            item["diff"]
                .as_str()
                .ok_or_else(|| error("unified file diff required"))?,
        )?;
        let patch = diffy::Patch::from_str(&diff).map_err(error)?;
        if patch.to_string() != diff
            || patch.original() != Some("original")
            || patch.modified() != Some("modified")
            || patch.hunks().is_empty()
        {
            return Err(error(
                "file diff requires canonical original/modified headers, complete hunks, and no trailing material",
            ));
        }
        let after = apply_exact(&normalized, &patch)?;
        if after == normalized {
            return Err(error(
                "patch must describe an actual assignment-specific change",
            ));
        }
        total += before.len() + after.len();
        if total > MAX_BYTES {
            return Err(error("combined patch subject exceeds the text bound"));
        }
        files.push(json!({"path":path,"baseline_revision":baseline["revision"],"before":before,"after":after}));
    }
    let declared: BTreeSet<_> = returned["changed_paths"]
        .as_array()
        .ok_or_else(|| error("concrete changed paths required"))?
        .iter()
        .map(|v| {
            v.as_str()
                .map(str::to_owned)
                .ok_or_else(|| error("changed path must be text"))
        })
        .collect::<Result<_, _>>()?;
    if declared != paths || returned["changed_paths"].as_array().unwrap().len() != paths.len() {
        return Err(error("changed paths differ from the exact file deltas"));
    }
    files.sort_by(|a, b| a["path"].as_str().cmp(&b["path"].as_str()));
    Ok(
        json!({"kind":"agentic-workspace/assignment-delta/v1","revision":digest(&json!({"assignment":packet["assignment_revision"],"files":files}))?,"files":files,"changed_paths":paths,"proof_authority":false,"completion_authority":false}),
    )
}

/// Preserve concurrent non-overlapping edits and the current file's uniform
/// line endings. Conflict markers are never materialized in the checkout.
pub(crate) fn merge(before: &str, after: &str, current: &str) -> Result<String, CoreError> {
    let base = normalize(before)?;
    let ours = normalize(current)?;
    let theirs = normalize(after)?;
    let crlf = current.contains("\r\n");
    if crlf && current.replace("\r\n", "").contains('\n') {
        return Err(error("mixed current line endings require a bounded repair"));
    }
    let merged = diffy::merge(&base, &ours, &theirs)
        .map_err(|_| error("assignment delta overlaps divergent current work"))?;
    let output = if crlf {
        merged.replace('\n', "\r\n")
    } else {
        merged
    };
    if output.len() > MAX_BYTES {
        return Err(error("merged patch postimage exceeds the text bound"));
    }
    Ok(output)
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn delta_rejects_ambiguous_paths_material_and_hunk_positions() {
        let packet = json!({"assignment_revision":"current-assignment","scope":["src/*.txt"],"assignment_identity":{"mutation_paths":["src/main.txt"],"input_capsule":[{"reference":"src/main.txt","revision":"captured","content":"one\ntwo\nthree\n"}]}});
        let diff = "--- original\n+++ modified\n@@ -2 +2 @@\n-two\n+worker\n";
        let returned = |path: &str, text: &str| json!({"changed_paths":[path],"patch":serde_json::to_string(&json!([{"path":path,"diff":text}])).unwrap()});
        let valid = delta(&packet, &returned("src/main.txt", diff)).unwrap();
        assert_eq!(valid["files"][0]["after"], "one\nworker\nthree\n");
        assert_eq!(
            delta(
                &packet,
                &returned("src/main.txt", &diff.replace('\n', "\r\n"))
            )
            .unwrap(),
            valid
        );
        for text in [
            format!("{diff}ignored trailer\n"),
            diff.replace("+2", "+1"),
            diff.replace("-two", "-other"),
            diff.replace("-2", "-1"),
        ] {
            assert!(delta(&packet, &returned("src/main.txt", &text)).is_err());
        }
        for path in [
            "src/*.txt",
            "src/other.txt",
            "../main.txt",
            ".agentic-workspace/config.toml",
            ".GIT/config",
        ] {
            assert!(delta(&packet, &returned(path, diff)).is_err());
        }
        let mut mismatched = returned("src/main.txt", diff);
        mismatched["changed_paths"] = json!(["src/other.txt"]);
        assert!(delta(&packet, &mismatched).is_err());
    }
    #[test]
    fn exact_delta_preserves_disjoint_changes_and_replays() {
        let before = "one\ntwo\nthree\nfour\nfive\nsix\n";
        let after = before.replace("two", "worker");
        let current = before.replace("six", "concurrent");
        let merged = merge(before, &after, &current).unwrap();
        assert!(merged.contains("worker") && merged.contains("concurrent"));
        assert_eq!(merge(before, &after, &merged).unwrap(), merged);
        assert!(merge(before, &after, &before.replace("two", "other")).is_err());
        let crlf = current.replace('\n', "\r\n");
        assert_eq!(
            merge(before, &after, &crlf).unwrap(),
            merged.replace('\n', "\r\n")
        );
    }
    #[test]
    fn positional_hunks_do_not_search_another_matching_occurrence() {
        let patch =
            diffy::Patch::from_str("--- original\n+++ modified\n@@ -1 +1 @@\n-a\n+b\n").unwrap();
        assert_eq!(apply_exact("a\na\n", &patch).unwrap(), "b\na\n");
        assert!(apply_exact("x\na\n", &patch).is_err());
    }
}
