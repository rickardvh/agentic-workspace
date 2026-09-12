//! Read-only selection of the existing Memory manifest. Observing source bytes
//! establishes identity, not factual freshness or permission to promote a note.
use crate::{CoreError, decision_source, instruction_applicability};
use cap_std::{ambient_authority, fs::Dir};
use serde_json::{Value, json};
use std::{
    collections::BTreeSet,
    path::{Path, PathBuf},
};

const MANIFEST: &str = ".agentic-workspace/memory/repo/manifest.toml";
const HOME: &str = ".agentic-workspace/memory/repo/";

fn error(message: impl ToString) -> CoreError {
    CoreError::new(format!("Memory source: {}", message.to_string()))
}

fn confined(root: &Dir, path: &str) -> Result<bool, CoreError> {
    decision_source::relative(path)?;
    let mut current = PathBuf::new();
    for component in path.split('/') {
        current.push(component);
        match root.symlink_metadata(&current) {
            Ok(metadata) => {
                #[cfg(windows)]
                let linked = {
                    use cap_std::fs::MetadataExt;
                    metadata.file_attributes() & 0x400 != 0
                };
                #[cfg(not(windows))]
                let linked = metadata.is_symlink();
                if linked {
                    return Err(error(format!("{path}: linked source is not admitted")));
                }
            }
            Err(e) if e.kind() == std::io::ErrorKind::NotFound => return Ok(false),
            Err(e) => return Err(error(format!("{path}: {e}"))),
        }
    }
    Ok(true)
}

fn strings(value: Option<&Value>, field: &str) -> Result<Vec<String>, CoreError> {
    let Some(value) = value else {
        return Ok(Vec::new());
    };
    let rows = value
        .as_array()
        .ok_or_else(|| error(format!("{field} must be an array")))?;
    if rows.len() > 64 {
        return Err(error(format!("{field} exceeds 64 entries")));
    }
    rows.iter()
        .map(|row| {
            row.as_str()
                .filter(|s| !s.is_empty())
                .map(str::to_owned)
                .ok_or_else(|| error(format!("{field} requires nonempty strings")))
        })
        .collect()
}

fn path_patterns(value: Option<&Value>, field: &str) -> Result<Vec<String>, CoreError> {
    let rows = strings(value, field)?;
    for row in &rows {
        decision_source::relative(row)?;
    }
    Ok(rows)
}

/// The public owner must first validate this reference against its freshly
/// selected resources. This helper additionally checks manifest membership and
/// exact observed bytes; possession of a path/revision grants no authority.
pub(crate) fn read_selected(
    target: &Path,
    reference: &str,
    expected_revision: &str,
) -> Result<Value, CoreError> {
    if !reference.starts_with(HOME) || !reference.ends_with(".md") {
        return Err(error("read requires a declared Memory note"));
    }
    let root = Dir::open_ambient_dir(target, ambient_authority()).map_err(error)?;
    if !confined(&root, MANIFEST)? || !confined(&root, reference)? {
        return Err(error(
            "selected source is missing; resolve current Memory again",
        ));
    }
    let manifest_bytes = decision_source::read(&root, MANIFEST)?;
    let manifest: toml::Value = std::str::from_utf8(&manifest_bytes)
        .map_err(error)?
        .parse()
        .map_err(error)?;
    let note = manifest
        .get("notes")
        .and_then(|notes| notes.get(reference))
        .and_then(toml::Value::as_table)
        .ok_or_else(|| error("note is no longer declared by the current manifest"))?;
    if note
        .get("canonical_home")
        .and_then(toml::Value::as_str)
        .is_some_and(|home| home != reference)
    {
        return Err(error(
            "selected note changed canonical owner; reconcile source",
        ));
    }
    let bytes = decision_source::read(&root, reference)?;
    let revision = decision_source::hash(&bytes);
    if revision != expected_revision {
        return Err(error(
            "selected note revision changed; resolve current Memory again",
        ));
    }
    Ok(json!({"source":{"reference":reference,"revision":revision},
        "body":std::str::from_utf8(&bytes).map_err(error)?,"authority_effect":"advisory-only",
        "currentness":{"status":"review-required","reason":"source-identity-is-not-factual-currentness"}}))
}

/// `route` must be the current semantic-route owner's result, never caller facts.
/// The reader emits advisory resources only; no contribution grants authority.
fn diagnostic(reference: &str, code: &str, message: impl ToString) -> Value {
    json!({"source":reference,"code":code,"diagnostic":message.to_string(),"authority_effect":"advisory-only"})
}

pub(crate) fn resolve(
    target: &Path,
    changed: &[String],
    route: &Value,
) -> Result<Value, CoreError> {
    for path in changed {
        decision_source::relative(path)?;
    }
    if route["status"] == "current" && route["posture"] == "selected" {
        crate::route_ids(
            strings(route.get("routes"), "selected routes")?,
            "selected routes",
        )?;
    }
    Ok(match resolve_sources(target, changed, route) {
        Ok(view) => view,
        Err(problem) => {
            json!({"kind":"agentic-memory/source-selection/v1","status":"reconciliation-required",
            "authority_effect":"advisory-only","selected_notes":[],
            "diagnostics":[diagnostic(MANIFEST,"source-observation-unavailable",problem)]})
        }
    })
}

fn resolve_sources(target: &Path, changed: &[String], route: &Value) -> Result<Value, CoreError> {
    let selected_routes = if route["status"] == "current" && route["posture"] == "selected" {
        crate::route_ids(
            strings(route.get("routes"), "selected routes")?,
            "selected routes",
        )?
    } else {
        Vec::new()
    };
    let empty = |status: &str| {
        json!({"kind":"agentic-memory/source-selection/v1", "status":status,
        "authority_effect":"advisory-only", "selected_notes":[], "diagnostics":[]})
    };
    if changed.is_empty() && selected_routes.is_empty() {
        return Ok(empty("no-match"));
    }
    for path in changed {
        decision_source::relative(path)?;
    }
    let root = Dir::open_ambient_dir(target, ambient_authority()).map_err(error)?;
    if !confined(&root, MANIFEST)? {
        return Ok(empty("absent"));
    }
    let bytes = decision_source::read(&root, MANIFEST)?;
    let parsed: toml::Value = std::str::from_utf8(&bytes)
        .map_err(error)?
        .parse()
        .map_err(error)?;
    let manifest = serde_json::to_value(parsed).map_err(error)?;
    let notes = match manifest.get("notes") {
        None => return Ok(empty("no-match")),
        Some(value) => value
            .as_object()
            .ok_or_else(|| error("manifest notes must be a table"))?,
    };
    if notes.len() > 128 {
        return Err(error(
            "manifest exceeds 128 notes; select a bounded owner source",
        ));
    }
    let mut selected = Vec::new();
    let mut diagnostics = Vec::new();
    for (reference, raw) in notes {
        let note = (|| -> Result<Option<Value>, CoreError> {
            if !reference.starts_with(HOME) || !reference.ends_with(".md") {
                return Err(error(format!(
                    "{reference}: note must remain in its existing Memory owner"
                )));
            }
            decision_source::relative(reference)?;
            let metadata = raw
                .as_object()
                .ok_or_else(|| error(format!("{reference}: note metadata must be a table")))?;
            let paths = path_patterns(metadata.get("routes_from"), "routes_from")?;
            let routes = strings(metadata.get("semantic_routes"), "semantic_routes")?;
            for selector in &routes {
                crate::route_ids(
                    vec![selector.strip_suffix("/**").unwrap_or(selector).to_owned()],
                    "semantic_routes",
                )?;
            }
            if metadata.get("routing_only") == Some(&json!(true))
                || metadata.get("note_type") == Some(&json!("routing"))
                || metadata.get("task_relevance") == Some(&json!("review-only"))
            {
                return Ok(None);
            }
            let matched_paths: BTreeSet<_> = changed
                .iter()
                .filter(|p| {
                    paths
                        .iter()
                        .any(|g| instruction_applicability::matches(g, p))
                })
                .cloned()
                .collect();
            let matched_routes: Vec<_> = routes
                .iter()
                .filter(|selector| {
                    selected_routes.iter().any(|route| {
                        selector
                            .strip_suffix("/**")
                            .map_or(selector.as_str() == route, |prefix| {
                                route == prefix || route.starts_with(&format!("{prefix}/"))
                            })
                    })
                })
                .cloned()
                .collect();
            if matched_paths.is_empty() && matched_routes.is_empty() {
                return Ok(None);
            }
            if selected.len() == 12 {
                return Err(error(
                    "more than 12 relevant notes; narrow the current work scope",
                ));
            }
            let stale_when = path_patterns(metadata.get("stale_when"), "stale_when")?;
            let superseded_by = strings(metadata.get("superseded_by"), "superseded_by")?;
            let contradicted_by = strings(metadata.get("contradicted_by"), "contradicted_by")?;
            let canonical = metadata
                .get("canonical_home")
                .and_then(Value::as_str)
                .unwrap_or(reference);
            if canonical != reference {
                return Err(error(format!(
                    "{reference}: canonical home differs; reconcile through the existing owner"
                )));
            }
            let changed_dependencies: BTreeSet<_> = changed
                .iter()
                .filter(|p| {
                    stale_when
                        .iter()
                        .any(|g| instruction_applicability::matches(g, p))
                })
                .cloned()
                .collect();
            let observed = if confined(&root, reference)? {
                Some(decision_source::hash(&decision_source::read(
                    &root, reference,
                )?))
            } else {
                None
            };
            let reason = if observed.is_none() {
                "selected-source-missing"
            } else if !changed_dependencies.is_empty() {
                "stale-when-matched"
            } else if !superseded_by.is_empty() || !contradicted_by.is_empty() {
                "declared-currentness-reconciliation"
            } else if metadata.contains_key("disposition") {
                "disposition-needs-current-admission"
            } else {
                "no-admitted-currentness-baseline"
            };
            Ok(Some(
                json!({"source":{"reference":reference,"revision":observed},
            "metadata":{"note_type":metadata.get("note_type"),"canonical_home":canonical,
                "routes_from":paths,"semantic_routes":routes,"stale_when":stale_when,
                "last_confirmed":metadata.get("last_confirmed"),"valid_until":metadata.get("valid_until"),
                "superseded_by":superseded_by,"contradicted_by":contradicted_by},
            "matched_paths":matched_paths,"matched_routes":matched_routes,
            "currentness":{"status":"review-required","reason":reason,"changed_dependencies":changed_dependencies},
            "authority_effect":"advisory-only"}),
            ))
        })();
        match note {
            Ok(Some(note)) => selected.push(note),
            Ok(None) => {}
            Err(problem) => diagnostics.push(diagnostic(
                reference,
                "note-reconciliation-required",
                problem,
            )),
        }
    }
    if let Some(facts) = manifest.get("durable_facts").and_then(Value::as_object) {
        for (id, fact) in facts.iter().take(128) {
            let note_ref = fact["note_ref"].as_str().unwrap_or("");
            let reference = note_ref.split('#').next().unwrap_or("");
            if selected
                .iter()
                .any(|note| note["source"]["reference"] == reference)
            {
                let mut row = diagnostic(
                    &format!("{MANIFEST}#durable_facts.{id}"),
                    "native-fact-owner-unresolved",
                    "Structured fact projection and stronger-owner promotion are not admitted by this native reader; preserve the referenced advisory source.",
                );
                row["note_ref"] = json!(note_ref);
                row["owner"] = fact["owner"].clone();
                row["promotion_target"] = fact["promotion_target"].clone();
                diagnostics.push(row);
            }
        }
    }
    if selected.is_empty() && diagnostics.is_empty() {
        return Ok(empty("no-match"));
    }
    Ok(
        json!({"kind":"agentic-memory/source-selection/v1","status":if diagnostics.is_empty(){"review-required"}else{"reconciliation-required"},
        "authority_effect":"advisory-only", "manifest":{"reference":MANIFEST,"revision":decision_source::hash(&bytes)},
        "selected_notes":selected,"diagnostics":diagnostics}),
    )
}

/// Public read construction stays owned by Memory; the transport supplies only
/// the selected exact reference, never source admission or factual freshness.
pub(crate) fn public_view(
    target: &Path,
    changed: &[String],
    route: &Value,
    work: &Value,
    request: Option<&Value>,
    full_contract: Option<&Value>,
    capture_available: bool,
) -> Result<Value, CoreError> {
    let mut view = resolve(target, changed, route)?;
    let revision = crate::digest(&view)?;
    let schema = crate::source_schema();
    let mut arguments = schema["$defs"]["memory_note_read_request"].clone();
    arguments["$schema"] = schema["$schema"].clone();
    let declaration = json!({"kind":"memory/read-current-note/v1", "result_kind":"agentic-memory/note-read-result/v1", "input_schema":arguments});
    let owner_revision = crate::digest(&declaration)?;
    let mut contract = json!({"kind":"agentic-workspace/capability-contract/v1", "revision":"pending",
        "owners":[{"owner":"memory", "revision":owner_revision,"requests":[declaration]}]});
    if capture_available
        || view["selected_notes"]
            .as_array()
            .into_iter()
            .flatten()
            .any(|note| note["source"]["revision"].is_string())
    {
        crate::native_memory_write::extend_owner(&mut contract["owners"][0])?;
        contract["restriction_authorities"] =
            json!([{"owner":"memory","affects":["task","effect:memory-state"]}]);
    }
    if capture_available {
        crate::native_memory_capture::extend_owner(&mut contract["owners"][0])?;
        contract["restriction_authorities"] =
            json!([{"owner":"memory","affects":["task","effect:memory-state"]}]);
    }
    let owner_revision = contract["owners"][0]["revision"].clone();
    contract["revision"] = json!(crate::digest(&contract)?);
    let validation = full_contract.unwrap_or(&contract);
    let mut requests = Vec::new();
    for note in view["selected_notes"].as_array().into_iter().flatten() {
        if note["source"]["revision"].is_string() {
            requests.push(json!({"kind":"agentic-workspace/public-request/v1", "id":format!("memory/read:{}",crate::digest(&note["source"])?),
                "owner":"memory", "owner_revision":owner_revision,"source_revision":revision,
                "capability_revision":validation["revision"], "task_identity":work,
                "request_kind":"memory/read-current-note/v1", "arguments":note["source"]}));
        }
    }
    if let Some(request) = request {
        let prepared = crate::prepare_request_value(
            json!({"request":request,"current_work":work,"capability_contract":validation}),
        )?;
        if request["owner"] != "memory" || request["source_revision"] != revision {
            return Err(error(
                "Memory request is stale or names another owner; resolve the current read request",
            ));
        }
        if !requests
            .iter()
            .any(|current| current["arguments"] == request["arguments"])
        {
            return Err(error(
                "Memory read is outside the currently selected source scope",
            ));
        }
        let detail = read_selected(
            target,
            request["arguments"]["reference"].as_str().unwrap(),
            request["arguments"]["revision"].as_str().unwrap(),
        )?;
        // Recheck scope/manifest identity after bounded retrieval as well.
        if crate::digest(&resolve(target, changed, route)?)? != revision {
            return Err(error(
                "Memory source scope changed during read; resolve again",
            ));
        }
        view["response"] = json!({"kind":"agentic-memory/note-read-result/v1", "request_identity":prepared["identity"],
            "status":"read", "detail":detail, "authority_effect":"advisory-only"});
    }
    view["requests"] = json!(requests);
    view["revision"] = json!(revision);
    view["capability_contract"] = contract;
    view["contribution"] = json!({"owner":"memory", "revision":revision,"settled":true,
        "relevant":!view["selected_notes"].as_array().unwrap().is_empty() || !view["diagnostics"].as_array().unwrap().is_empty(),
        "facts":{"advisory_sources":view["selected_notes"],"diagnostics":view["diagnostics"]}});
    Ok(view)
}

pub(crate) fn disabled(target: &std::path::Path) -> Result<Value, CoreError> {
    crate::native_config::disabled_owner(
        target,
        "memory",
        &[MANIFEST],
        &["effect:memory-state", "claim:complete"],
    )
}

/// Only the repository adapter supplies `owner_input`. Memory can recognize an
/// independently admitted decision containing a whole lesson; it cannot admit
/// that decision or infer that an excerpt absorbed the rest of a note.
pub(crate) fn receiving_admissions(
    target: &Path,
    view: &Value,
    owner_input: &Value,
) -> Result<Value, CoreError> {
    if view["selected_notes"].as_array().is_none_or(Vec::is_empty) {
        return Ok(json!([]));
    }
    let context = &owner_input["decision_context"];
    if context["admissions"].as_array().is_none_or(Vec::is_empty) {
        return Ok(json!([]));
    }
    let projected = crate::compile_value(owner_input.clone())?;
    let root = Dir::open_ambient_dir(target, ambient_authority()).map_err(error)?;
    let manifest: toml::Value = toml::from_str(
        std::str::from_utf8(&decision_source::read(&root, MANIFEST)?).map_err(error)?,
    )
    .map_err(error)?;
    let mut result = Vec::new();
    for note in view["selected_notes"].as_array().into_iter().flatten() {
        let Some(revision) = note["source"]["revision"].as_str() else {
            continue;
        };
        let reference = note["source"]["reference"].as_str().unwrap();
        if !context["records"]
            .as_array()
            .into_iter()
            .flatten()
            .any(|record| {
                record["context"]
                    .as_array()
                    .into_iter()
                    .flatten()
                    .any(|source| {
                        source["owner"] == "repository"
                            && source["reference"] == reference
                            && source["revision"] == revision
                    })
            })
        {
            continue;
        }
        // Receiver discovery remains advisory. An unavailable note cannot veto
        // unrelated direct work; a requested promotion will lack admission.
        let Ok(detail) = read_selected(target, reference, revision) else {
            continue;
        };
        let lesson = detail["body"].as_str().unwrap().trim();
        if lesson.is_empty() {
            continue;
        }
        let mut lessons = vec![(None, lesson.to_owned())];
        for (id, fact) in manifest
            .get("durable_facts")
            .and_then(toml::Value::as_table)
            .into_iter()
            .flatten()
            .take(128)
        {
            if fact
                .get("note_ref")
                .and_then(toml::Value::as_str)
                .is_some_and(|r| r.split('#').next() == Some(reference))
                && fact.get("authority_class").and_then(toml::Value::as_str) == Some("advisory")
                && let Some(summary) = fact
                    .get("summary")
                    .and_then(toml::Value::as_str)
                    .filter(|s| !s.trim().is_empty() && s.len() <= 8192)
            {
                lessons.push((Some(id), summary.trim().to_owned()));
            }
        }
        for (fact, lesson) in lessons {
            for admission in context["admissions"].as_array().into_iter().flatten() {
                if admission["source"]["owner"] != "repository" {
                    continue;
                }
                let current = projected["decision_context"]["states"]
                    .as_array()
                    .into_iter()
                    .flatten()
                    .any(|state| {
                        state["id"] == admission["id"]
                            && state["material_revision"] == admission["material_revision"]
                            && state["source"] == admission["source"]
                            && state["status"] == "current"
                    });
                if !current {
                    continue;
                }
                let absorbed =
                    context["records"]
                        .as_array()
                        .into_iter()
                        .flatten()
                        .any(|record| {
                            record["id"] == admission["id"]
                                && fact.is_none_or(|id| record["id"] == *id)
                                && record["material_revision"] == admission["material_revision"]
                                && record["source"] == admission["source"]
                                && ["decision", "consequence"].iter().any(|field| {
                                    record[*field]
                                        .as_str()
                                        .is_some_and(|text| text.trim() == lesson)
                                })
                                && record["context"].as_array().into_iter().flatten().any(
                                    |source| {
                                        source["owner"] == "repository"
                                            && source["reference"] == reference
                                            && source["revision"] == revision
                                    },
                                )
                        });
                if absorbed {
                    if result.len() == 12 {
                        return Err(error(
                            "more than 12 eligible receivers; narrow the current source scope",
                        ));
                    }
                    let mut candidate = json!({"note":note["source"],"receiving_admission":admission,
                    "authority_effect":"eligible-receiver-only",
                    "disposition_authorized":false,"completion_authority":false});
                    if let Some(fact) = fact {
                        candidate["fact"] = json!(fact);
                    }
                    result.push(candidate);
                }
            }
        }
    }
    Ok(json!(result))
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::fs;
    struct Temp(PathBuf);
    impl Temp {
        fn path(&self) -> &Path {
            &self.0
        }
    }
    impl Drop for Temp {
        fn drop(&mut self) {
            let _ = fs::remove_dir_all(&self.0);
        }
    }
    fn fixture() -> Temp {
        let temp = Temp(std::env::temp_dir().join(format!(
                "aw-native-memory-{}-{}",
                std::process::id(),
                std::time::SystemTime::now()
                    .duration_since(std::time::UNIX_EPOCH)
                    .unwrap()
                    .as_nanos()
            )));
        fs::create_dir_all(temp.path().join(format!("{HOME}decisions"))).unwrap();
        fs::write(
            temp.path().join(MANIFEST),
            format!(
                r#"version=1
[notes."{HOME}decisions/former.md"]
note_type="decision"
authority="canonical"
routes_from=["src/**"]
semantic_routes=["github/pr/review"]
stale_when=["src/owner.rs"]
"#
            ),
        )
        .unwrap();
        fs::write(
            temp.path().join(format!("{HOME}decisions/former.md")),
            "Accepted historical prose; not admitted proof.",
        )
        .unwrap();
        temp
    }
    #[test]
    fn native_memory_preserves_selected_advisory_without_inventing_freshness() {
        let repo = fixture();
        let first = resolve(repo.path(), &["src/new.rs".into()], &Value::Null).unwrap();
        assert_eq!(
            first["selected_notes"][0]["currentness"]["reason"],
            "no-admitted-currentness-baseline"
        );
        assert_eq!(first["authority_effect"], "advisory-only");
        assert!(first["selected_notes"][0].get("body").is_none());
        let reference = format!("{HOME}decisions/former.md");
        let revision = first["selected_notes"][0]["source"]["revision"]
            .as_str()
            .unwrap();
        assert_eq!(
            read_selected(repo.path(), &reference, revision).unwrap()["body"],
            "Accepted historical prose; not admitted proof."
        );
        let stale = resolve(repo.path(), &["src/owner.rs".into()], &Value::Null).unwrap();
        assert_eq!(
            stale["selected_notes"][0]["currentness"]["reason"],
            "stale-when-matched"
        );
        fs::write(
            repo.path().join(format!("{HOME}decisions/former.md")),
            "Changed prose",
        )
        .unwrap();
        let next = resolve(repo.path(), &["src/new.rs".into()], &Value::Null).unwrap();
        assert_ne!(
            first["selected_notes"][0]["source"]["revision"],
            next["selected_notes"][0]["source"]["revision"]
        );
        assert!(read_selected(repo.path(), &reference, revision).is_err());
    }
    #[test]
    fn native_memory_routes_are_current_and_no_signal_does_not_read_sources() {
        let repo = fixture();
        assert_eq!(
            resolve(
                repo.path(),
                &[],
                &json!({"status":"current","posture":"selected","routes":["github/pr/review"]})
            )
            .unwrap()["selected_notes"]
                .as_array()
                .unwrap()
                .len(),
            1
        );
        assert_eq!(
            resolve(
                repo.path(),
                &[],
                &json!({"status":"stale","posture":"selected","routes":["github/pr/review"]})
            )
            .unwrap()["status"],
            "no-match"
        );
        fs::write(repo.path().join(MANIFEST), "invalid[").unwrap();
        assert_eq!(
            resolve(repo.path(), &[], &Value::Null).unwrap()["status"],
            "no-match"
        );
        assert_eq!(
            resolve(repo.path(), &["src/x.rs".into()], &Value::Null).unwrap()["status"],
            "reconciliation-required"
        );
    }
    #[test]
    fn native_memory_missing_selected_note_remains_exact_review_residue() {
        let repo = fixture();
        fs::remove_file(repo.path().join(format!("{HOME}decisions/former.md"))).unwrap();
        let result = resolve(repo.path(), &["src/x.rs".into()], &Value::Null).unwrap();
        assert_eq!(
            result["selected_notes"][0]["currentness"]["reason"],
            "selected-source-missing"
        );
        assert!(result["selected_notes"][0]["source"]["revision"].is_null());
        assert_eq!(
            resolve(repo.path(), &["README.md".into()], &Value::Null).unwrap()["status"],
            "no-match"
        );
    }

    #[test]
    fn native_memory_reads_real_former_decision_as_review_evidence() {
        let repo = fixture();
        let reference = format!("{HOME}decisions/installed-system-consolidation-2026-04-05.md");
        fs::write(
            repo.path().join(MANIFEST),
            include_str!("../../../.agentic-workspace/memory/repo/manifest.toml"),
        )
        .unwrap();
        fs::write(repo.path().join(&reference), include_str!("../../../.agentic-workspace/memory/repo/decisions/installed-system-consolidation-2026-04-05.md")).unwrap();
        let result = resolve(
            repo.path(),
            &["packages/memory/README.md".into()],
            &Value::Null,
        )
        .unwrap();
        let note = result["selected_notes"]
            .as_array()
            .unwrap()
            .iter()
            .find(|row| row["source"]["reference"] == reference)
            .unwrap();
        assert_eq!(note["currentness"]["status"], "review-required");
        let body = read_selected(
            repo.path(),
            &reference,
            note["source"]["revision"].as_str().unwrap(),
        )
        .unwrap();
        assert!(
            body["body"]
                .as_str()
                .unwrap()
                .contains("Root-Owned Installed Systems")
        );
        assert_eq!(body["authority_effect"], "advisory-only");
    }

    #[test]
    fn native_memory_rejects_escape_and_oversized_source() {
        let repo = fixture();
        fs::write(
            repo.path().join(MANIFEST),
            "[notes.\"../escape.md\"]\nroutes_from=['src/**']\n",
        )
        .unwrap();
        assert_eq!(
            resolve(repo.path(), &["src/x.rs".into()], &Value::Null).unwrap()["status"],
            "reconciliation-required"
        );
        fs::write(repo.path().join(MANIFEST), "x".repeat(262145)).unwrap();
        assert_eq!(
            resolve(repo.path(), &["src/x.rs".into()], &Value::Null).unwrap()["status"],
            "reconciliation-required"
        );
    }

    #[cfg(unix)]
    #[test]
    fn native_memory_rejects_linked_selected_source() {
        let repo = fixture();
        let path = repo.path().join(format!("{HOME}decisions/former.md"));
        fs::remove_file(&path).unwrap();
        std::os::unix::fs::symlink(repo.path().join(MANIFEST), &path).unwrap();
        assert_eq!(
            resolve(repo.path(), &["src/x.rs".into()], &Value::Null).unwrap()["status"],
            "reconciliation-required"
        );
    }

    #[test]
    fn native_memory_isolates_bad_notes_and_keeps_exact_fact_residue() {
        let repo = fixture();
        let mut manifest = fs::read_to_string(repo.path().join(MANIFEST)).unwrap();
        manifest.push_str(&format!(
            r#"
[notes."{HOME}decisions/unrelated.md"]
routes_from=["docs/**"]
stale_when=17
[notes."{HOME}decisions/unknown.md"]
routes_from=17
[durable_facts.current]
note_ref="{HOME}decisions/former.md#decision"
owner="planning"
promotion_target="planning-current-owner"
"#
        ));
        fs::write(repo.path().join(MANIFEST), manifest).unwrap();
        let result = resolve(repo.path(), &["src/x.rs".into()], &Value::Null).unwrap();
        assert_eq!(result["selected_notes"].as_array().unwrap().len(), 1);
        let diagnostics = result["diagnostics"].as_array().unwrap();
        assert_eq!(diagnostics.len(), 2);
        assert!(
            diagnostics
                .iter()
                .any(|row| row["source"].as_str().unwrap().ends_with("unknown.md"))
        );
        assert!(
            diagnostics
                .iter()
                .any(|row| row["code"] == "native-fact-owner-unresolved"
                    && row["owner"] == "planning")
        );
        assert!(
            !diagnostics
                .iter()
                .any(|row| row["source"].as_str().unwrap().ends_with("unrelated.md"))
        );
        fs::write(repo.path().join(MANIFEST), "invalid[").unwrap();
        let view = public_view(
            repo.path(),
            &["src/x.rs".into()],
            &Value::Null,
            &json!({"kind":"current-work","id":"work"}),
            None,
            None,
            false,
        )
        .unwrap();
        assert_eq!(view["contribution"]["settled"], true);
        assert_eq!(view["contribution"]["relevant"], true);
        assert_eq!(view["diagnostics"][0]["source"], MANIFEST);
        assert!(view["requests"].as_array().unwrap().is_empty());
    }
}
