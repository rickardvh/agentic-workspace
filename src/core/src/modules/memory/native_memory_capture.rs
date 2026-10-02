//! Exact domain-answer or policy-delegated decisions in the existing archives.
//! Publication custody and deciding authority are checked separately. This is
//! not identity authentication, a trust-pin writer, or generic archive custody.
use crate::{CoreError, digest};
use cap_std::{
    ambient_authority,
    fs::{Dir, OpenOptions},
};
use serde_json::{Value, json};
use std::{io::Write, path::Path};

pub(crate) const ADVISORY_CAPTURE: &str = "memory/capture-advisory/v1";
pub(crate) const ADVISORY_RECOVER: &str = "memory/recover-advisory/v1";
pub(crate) const CAPTURE: &str = "memory/capture-decision/v1";
pub(crate) const RECOVER: &str = "memory/recover-decision/v1";
pub(crate) const REPOSITORY_CAPTURE: &str = "decision-continuity/capture-decision/v1";
pub(crate) const REPOSITORY_RECOVER: &str = "decision-continuity/recover-decision/v1";
const SEMANTICS: &str = "memory-bounded-domain-decision-v2";
const EFFECT: &str = "memory-state";
const DEFAULT_ARCHIVE: &str = ".agentic-workspace/memory/repo/decisions";
const MANIFEST: &str = ".agentic-workspace/memory/repo/manifest.toml";

/// These are the two existing durable owners, not a caller-selectable registry.
#[derive(Clone, Copy, PartialEq, Eq)]
pub(crate) enum Destination {
    Memory,
    Advisory,
    Repository,
}
impl Destination {
    fn owner(self) -> &'static str {
        match self {
            Self::Memory | Self::Advisory => "memory",
            Self::Repository => "decision-continuity",
        }
    }
    fn record_owner(self) -> &'static str {
        match self {
            Self::Memory | Self::Advisory => "memory",
            Self::Repository => "repository",
        }
    }
    fn effect(self) -> &'static str {
        match self {
            Self::Memory | Self::Advisory => EFFECT,
            Self::Repository => "decision-source",
        }
    }
    fn capture(self) -> &'static str {
        match self {
            Self::Memory => CAPTURE,
            Self::Advisory => ADVISORY_CAPTURE,
            Self::Repository => REPOSITORY_CAPTURE,
        }
    }
    fn recover(self) -> &'static str {
        match self {
            Self::Memory => RECOVER,
            Self::Advisory => ADVISORY_RECOVER,
            Self::Repository => REPOSITORY_RECOVER,
        }
    }
    fn answer(self) -> &'static str {
        if self == Self::Advisory {
            "confirm-retention"
        } else {
            "confirm-decision"
        }
    }
    fn operation(self, recover: bool) -> String {
        if self == Self::Advisory {
            return format!(
                "memory.{}-advisory",
                if recover { "recover" } else { "capture" }
            );
        }
        format!(
            "{}.{}-decision",
            self.owner(),
            if recover { "recover" } else { "capture" }
        )
    }
    fn semantics(self) -> &'static str {
        match self {
            Self::Memory => SEMANTICS,
            Self::Advisory => "memory-bounded-advisory-v1",
            Self::Repository => "repository-bounded-domain-decision-v2",
        }
    }
    fn result_kind(self) -> &'static str {
        match self {
            Self::Memory => "agentic-memory/decision-publication/v1",
            Self::Advisory => "agentic-memory/advisory-publication/v1",
            Self::Repository => "agentic-workspace/repository-decision-publication/v1",
        }
    }
    fn from_binding(binding: &Value) -> Result<Self, CoreError> {
        match binding["durable_owner"].as_str() {
            None | Some("memory") => Ok(Self::Memory),
            Some("repository") => Ok(Self::Repository),
            Some("advisory") => Ok(Self::Advisory),
            _ => Err(err("unknown durable decision owner")),
        }
    }
}
fn err(e: impl ToString) -> CoreError {
    CoreError::new(e.to_string())
}
fn read(root: &Dir, path: &str) -> Result<Option<Vec<u8>>, CoreError> {
    crate::native_planning::read(root, path)
}
fn archive(config: &Value, destination: Destination) -> Result<String, CoreError> {
    if destination == Destination::Advisory {
        return Ok(".agentic-workspace/memory/repo/domains".into());
    }
    if destination == Destination::Repository {
        let path = config["admissions"]["decision_record_target"]
            .as_str()
            .ok_or_else(|| err("repository decision owner is not configured"))?;
        let path =
            crate::decision_source::archive_relative(path, "assurance.decision_record_target")?;
        if path == ".agentic-workspace" || path.starts_with(".agentic-workspace/") {
            return Err(err(
                "assurance.decision_record_target requires the independently owned repository destination",
            ));
        }
        return Ok(path.to_owned());
    }
    let path = config["admissions"]["decision_record_fallback"]["archive"]
        .as_str()
        .unwrap_or(DEFAULT_ARCHIVE);
    let path = crate::decision_source::archive_relative(
        path,
        "assurance.decision_record_fallback.archive",
    )?;
    if !path.starts_with(".agentic-workspace/memory/repo/") {
        return Err(err(
            "assurance.decision_record_fallback.archive: Fallback capture requires the existing Memory archive owner",
        ));
    }
    Ok(path.to_owned())
}
fn source(config: &Value, id: &str, destination: Destination) -> Result<String, CoreError> {
    Ok(format!(
        "{}/native-{}.md",
        archive(config, destination)?,
        &digest(&json!(id))?[7..]
    ))
}
fn marker(source: &str) -> Result<String, CoreError> {
    Ok(format!(
        ".agentic-workspace/local/effects/decision-{}.prepared.json",
        &digest(&json!(source))?[7..]
    ))
}
fn require_new_identity(
    root: &Dir,
    archive: &str,
    id: &Value,
    destination: Destination,
) -> Result<(), CoreError> {
    let entries = match root.read_dir(archive) {
        Ok(entries) => entries,
        Err(e) if e.kind() == std::io::ErrorKind::NotFound => return Ok(()),
        Err(e) => return Err(err(e)),
    };
    let mut count = 0;
    for entry in entries {
        let name = entry
            .map_err(err)?
            .file_name()
            .into_string()
            .map_err(|_| err("decision source name must be UTF-8"))?;
        if !name.ends_with(".md") {
            continue;
        }
        count += 1;
        if count > 64 {
            return Err(err("decision archive exceeds bounded identity discovery"));
        }
        let path = format!("{archive}/{name}");
        let bytes =
            read(root, &path)?.ok_or_else(|| err("decision identity source disappeared"))?;
        if !std::str::from_utf8(&bytes)
            .map_err(err)?
            .contains("```aw-decision")
        {
            continue;
        }
        let record = crate::decision_source::record(&bytes, &path, destination.record_owner())?;
        if record["id"] == *id {
            return Err(err(
                "decision identity already exists in the canonical archive; preserve it and use explicit supersession",
            ));
        }
    }
    Ok(())
}
pub(crate) fn extend_owner(owner: &mut Value) -> Result<(), CoreError> {
    extend_destination(owner, Destination::Memory)?;
    extend_destination(owner, Destination::Advisory)
}
pub(crate) fn extend_destination(
    owner: &mut Value,
    destination: Destination,
) -> Result<(), CoreError> {
    let text = json!({"type":"string","minLength":1,"maxLength":8192});
    let strings = json!({"type":"array","maxItems":32,"uniqueItems":true,"items":text});
    let mut material = json!({"type":"object","additionalProperties":false,"properties":{
        "id":{"type":"string","minLength":1,"maxLength":256},"decision":text,"consequence":text,
        "rationale":text,"alternatives":strings,"dependency_paths":strings,
        "supersedes":{"type":"array","maxItems":16,"items":{"type":"object","additionalProperties":false,
            "properties":{"id":text,"material_revision":text,"scope":strings},"required":["id","material_revision","scope"]}}},
        "required":["id","decision","consequence","rationale","alternatives","dependency_paths","supersedes"]});
    if destination == Destination::Advisory {
        material = json!({"type":"object","additionalProperties":false,"properties":{"id":{"type":"string","minLength":1,"maxLength":256},"lesson":text,"rationale":text,"dependency_paths":strings},"required":["id","lesson","rationale","dependency_paths"]});
        material["properties"]["routes_from"] = strings.clone();
        material["properties"]["semantic_routes"] = strings.clone();
        material["properties"]["origin"] = json!({"type":"object","additionalProperties":false,
            "properties":{"producer":text,"reference":text,"revision":text,"coverage":{"enum":["bounded","partial","unknown"]}},
            "required":["producer","reference","coverage"]});
        material["properties"]["origins"] =
            json!({"type":"array","maxItems":16,"items":material["properties"]["origin"]});
    }
    let mut args = json!({"$schema":"https://json-schema.org/draft/2020-12/schema","type":"object","additionalProperties":false,
        "properties":{"material":material,"disposition":{"enum":["retain","no-retention"]},"answer":{"enum":[destination.answer(),"defer"]},"proposal_revision":text},"required":["material"]});
    if destination == Destination::Advisory {
        args["properties"]["candidate_evidence_requests"] =
            json!({"type":"array","maxItems":8,"items":{"type":"object"}});
        args["properties"]["revise_source"] = text.clone();
        args["properties"]["source_revision"] = text.clone();
        args["properties"]["validity_review"] = text.clone();
        args["properties"]["candidate_ids"] = json!({"type":"array","minItems":1,"maxItems":16,"uniqueItems":true,
            "items":{"type":"string","minLength":1,"maxLength":72}});
    }
    let recovery = json!({"$schema":"https://json-schema.org/draft/2020-12/schema","type":"object","additionalProperties":false,
        "properties":{"source":text,"record_revision":text},"required":["source","record_revision"]});
    owner["domains"] = json!([destination.owner()]);
    owner["effects"] = json!([{"id":destination.effect(),"domain":destination.owner()}]);
    if !owner["operations"].is_array() {
        owner["operations"] = json!([]);
    }
    for id in [destination.operation(false), destination.operation(true)] {
        owner["operations"].as_array_mut().unwrap().push(json!({"id":id,"semantic_revision":destination.semantics(),
            "input_schema":{"$schema":"https://json-schema.org/draft/2020-12/schema","type":"object","additionalProperties":false,
                "properties":{"target":{"type":"string"},"request":{"type":"object"},"binding":{"type":"object"},"post_revision":{"type":"string"},"recovery_paths":{"type":"array","items":{"type":"string"}}},
                "required":["target","request","binding","post_revision"]},"result_kind":destination.result_kind(),"effects":[destination.effect()],"reads":[destination.owner()]}));
    }
    owner["requests"].as_array_mut().unwrap().extend([
        json!({"kind":destination.capture(),"result_kind":"agentic-memory/decision-proposal/v1","input_schema":args}),
        json!({"kind":destination.recover(),"result_kind":destination.result_kind(),"input_schema":recovery})]);
    if destination == Destination::Advisory {
        owner["requests"]
            .as_array_mut()
            .unwrap()
            .push(crate::native_memory_learning::declaration());
    }
    owner["revision"] = json!(digest(&json!([
        owner["requests"],
        owner["operations"],
        "exact-policy-delegation-v1"
    ]))?);
    Ok(())
}
fn dependencies(root: &Dir, paths: &Value) -> Result<Value, CoreError> {
    let mut result = json!({});
    for path in paths.as_array().into_iter().flatten() {
        let path = path
            .as_str()
            .ok_or_else(|| err("Decision dependency must be an exact path"))?;
        let bytes = read(root, path)?.ok_or_else(|| err("Decision dependency is missing"))?;
        result[path] = json!(crate::decision_source::hash(&bytes));
    }
    Ok(result)
}

// Revision changes one existing ordinary note. Governing material still uses
// its deciding owner; neither a matching file name nor prose admits authority.
fn revision_manifest(
    root: &Dir,
    source: &str,
    dependencies: &Value,
    applicability: &Value,
    reviewed: bool,
) -> Result<(Value, String), CoreError> {
    crate::decision_source::relative(source)?;
    if !source.starts_with(".agentic-workspace/memory/repo/") {
        return Err(err("Revision requires the existing Memory source owner"));
    }
    let bytes = read(root, MANIFEST)?.ok_or_else(|| err("Declared advice is missing"))?;
    let text = std::str::from_utf8(&bytes).map_err(err)?;
    if text.contains("\r\n") && text.replace("\r\n", "").contains('\n') {
        return Err(err(
            "Mixed manifest line endings require source-owner repair",
        ));
    }
    let normalized = text.replace("\r\n", "\n");
    let mut document = normalized.parse::<toml_edit::DocumentMut>().map_err(err)?;
    let manifest = serde_json::to_value(toml::from_str::<toml::Value>(&normalized).map_err(err)?)
        .map_err(err)?;
    crate::native_memory::validate_manifest(&manifest)?;
    let old = &manifest["notes"][source];
    if old["note_type"] != "domain" || old["native_decision"] == true {
        return Err(err(
            "Only declared ordinary domain advice can be revised here",
        ));
    }
    if old["dependencies"] != *dependencies && !reviewed {
        return Err(err(
            "Dependency baseline changed; supply a deliberate validity_review before renewing reliance",
        ));
    }
    if document.to_string() != normalized {
        return Err(err("Manifest cannot preserve unrelated source"));
    }
    // Mutate only this declaration; preserve identity, dispositions and unrelated
    // entries/comments. The original exact manifest preimage remains bound.
    for (key, value) in [
        ("dependencies", dependencies),
        ("routes_from", &applicability["routes_from"]),
        ("semantic_routes", &applicability["semantic_routes"]),
    ] {
        let rendered = toml_edit::ser::to_document(&json!({(key):value})).map_err(err)?;
        document["notes"][source][key] = rendered[key].clone();
    }
    let rendered = document.to_string();
    Ok((
        json!(crate::native_intent::hash(&bytes)),
        if text.contains("\r\n") {
            rendered.replace('\n', "\r\n")
        } else {
            rendered
        },
    ))
}

fn receipt_sources(target: &Path, record: &Value) -> Result<Value, CoreError> {
    let prepared = crate::attempt_store::prepare_commit(
        target.to_str().unwrap(),
        record["custody"].clone(),
        record["outcome"].clone(),
    )?;
    Ok(json!([
        record["custody"]["attempt"],
        prepared["custody"]["committed"]
    ]))
}
fn cleanup_pending(root: &Dir, binding: &Value) -> Result<bool, CoreError> {
    for reference in binding["retire_receipts"].as_array().into_iter().flatten() {
        if read(root, reference["path"].as_str().unwrap())?.is_some() {
            return Ok(true);
        }
    }
    Ok(false)
}
fn cleanup_receipts(root: &Dir, target: &Path, binding: &Value) -> Result<(), CoreError> {
    for reference in binding["retire_receipts"].as_array().into_iter().flatten() {
        let reference: crate::attempt_store::Evidence =
            serde_json::from_value(reference.clone()).map_err(err)?;
        if read(root, &reference.path)?.is_some() {
            crate::attempt_store::read_source(target.to_str().unwrap(), &reference)?;
            root.remove_file(&reference.path).map_err(err)?;
        }
    }
    Ok(())
}

/// Cleanup of provisional evidence needs a confirmed current native publication,
/// not merely a source hash copied by the caller. This is publication-only proof.
pub(crate) fn confirmed_publication(
    target: &Path,
    source: &str,
    revision: &Value,
) -> Result<Value, CoreError> {
    let root = Dir::open_ambient_dir(target, ambient_authority()).map_err(err)?;
    let record =
        retained(target, source)?.ok_or_else(|| err("No native publication confirmation"))?;
    let binding = &record["invocation"]["arguments"]["binding"];
    if Destination::from_binding(binding)? != Destination::Advisory
        || !committed(&root, target, &record)?
        || !declaration_current(&root, binding)?
        || read(&root, source)?.is_none_or(|b| json!(crate::native_intent::hash(&b)) != *revision)
        || record["invocation"]["arguments"]["post_revision"] != *revision
        || dependencies(
            &root,
            &json!(
                binding["dependencies"]
                    .as_object()
                    .unwrap()
                    .keys()
                    .collect::<Vec<_>>()
            ),
        )? != binding["dependencies"]
    {
        return Err(err(
            "Publication or its validity source changed; preserve provisional evidence",
        ));
    }
    Ok(
        json!({"source":source,"revision":revision,"confirmation":digest(&record)?,"authority":"publication-only"}),
    )
}
fn advisory_applicability(material: &Value, scope: &[String]) -> Result<Value, CoreError> {
    let explicit =
        material.get("routes_from").is_some() || material.get("semantic_routes").is_some();
    let paths = if explicit {
        material["routes_from"]
            .as_array()
            .cloned()
            .unwrap_or_default()
    } else {
        scope
            .iter()
            .filter_map(|s| s.strip_prefix("path:"))
            .map(|s| json!(s))
            .collect()
    };
    let routes = material["semantic_routes"]
        .as_array()
        .cloned()
        .unwrap_or_default();
    for path in &paths {
        let path = path
            .as_str()
            .ok_or_else(|| err("Advisory path cue must be a string"))?;
        crate::decision_source::relative(path)?;
        if ["*", "**", "**/*"].contains(&path) {
            return Err(err(
                "Choose a scoped future activity/path; blanket repository advice is not a default",
            ));
        }
    }
    for route in &routes {
        let route = route
            .as_str()
            .ok_or_else(|| err("Advisory activity cue must be a string"))?;
        crate::route_ids(
            vec![route.strip_suffix("/**").unwrap_or(route).to_owned()],
            "advisory semantic_routes",
        )?;
    }
    Ok(json!({"routes_from":paths,"semantic_routes":routes}))
}
fn manifest_postimage(
    root: &Dir,
    source: &str,
    scope: &[String],
    advisory_dependencies: Option<&Value>,
    applicability: Option<&Value>,
) -> Result<(Value, String), CoreError> {
    let before = read(root, MANIFEST)?;
    let text = std::str::from_utf8(before.as_deref().unwrap_or(b"version=1\n")).map_err(err)?;
    let crlf = text.contains("\r\n");
    if crlf && text.replace("\r\n", "").contains('\n') {
        return Err(err(
            "Mixed manifest line endings require source-owner repair",
        ));
    }
    let normalized = text.replace("\r\n", "\n");
    crate::native_memory::validate_manifest(
        &serde_json::to_value(toml::from_str::<toml::Value>(&normalized).map_err(err)?)
            .map_err(err)?,
    )?;
    let mut document = normalized.parse::<toml_edit::DocumentMut>().map_err(err)?;
    if document
        .get("version")
        .and_then(toml_edit::Item::as_integer)
        != Some(1)
    {
        return Err(err("Unsupported Memory manifest; source preserved"));
    }
    if document.to_string() != normalized {
        return Err(err("Manifest rendering cannot preserve unrelated source"));
    }
    let had_notes = document.contains_key("notes");
    if !had_notes {
        document["notes"] = toml_edit::Item::Table(toml_edit::Table::new());
    }
    let notes = document["notes"]
        .as_table_mut()
        .ok_or_else(|| err("Unsupported Memory notes representation"))?;
    if notes.contains_key(source) {
        return Err(err("Decision manifest destination already exists"));
    }
    let mut entry = json!({"native_decision":true,"decision_scope":scope,
        "routes_from":scope.iter().filter_map(|s|s.strip_prefix("path:")).collect::<Vec<_>>()});
    if let Some(dependencies) = advisory_dependencies {
        entry = json!({"note_type":"domain","routes_from":scope.iter().filter_map(|s|s.strip_prefix("path:")).collect::<Vec<_>>(),"dependencies":dependencies});
        if let Some(cues) = applicability {
            entry["routes_from"] = cues["routes_from"].clone();
            entry["semantic_routes"] = cues["semantic_routes"].clone();
        }
    }
    let entry = toml_edit::ser::to_document(&entry).map_err(err)?;
    notes.insert(source, toml_edit::Item::Table(entry.as_table().clone()));
    let rendered = document.to_string();
    document["notes"].as_table_mut().unwrap().remove(source);
    if !had_notes {
        document.remove("notes");
    }
    if document.to_string() != normalized {
        return Err(err("Manifest update cannot preserve unrelated bytes"));
    }
    Ok((
        before
            .as_ref()
            .map(|b| json!(crate::native_intent::hash(b)))
            .unwrap_or(Value::Null),
        if crlf {
            rendered.replace('\n', "\r\n")
        } else {
            rendered
        },
    ))
}
fn manifest_current(root: &Dir, binding: &Value, allow_before: bool) -> Result<bool, CoreError> {
    if Destination::from_binding(binding)? == Destination::Repository {
        return declaration_current(root, binding);
    }
    let current = read(root, MANIFEST)?
        .map(|b| json!(crate::native_intent::hash(&b)))
        .unwrap_or(Value::Null);
    Ok(current
        == crate::native_intent::hash(binding["manifest_postimage"].as_str().unwrap().as_bytes())
        || allow_before && current == binding["manifest_before"])
}
fn declaration_current(root: &Dir, binding: &Value) -> Result<bool, CoreError> {
    if Destination::from_binding(binding)? == Destination::Repository {
        let source = binding["repository_convention"]["reference"]
            .as_str()
            .ok_or_else(|| err("repository convention binding missing"))?;
        return Ok(read(root, source)?
            .map(|b| json!(crate::decision_source::hash(&b)))
            .unwrap_or(Value::Null)
            == binding["repository_convention"]["revision"]);
    }
    let Some(bytes) = read(root, MANIFEST)? else {
        return Ok(false);
    };
    let current: toml::Value = match std::str::from_utf8(&bytes)
        .ok()
        .and_then(|s| toml::from_str(s).ok())
    {
        Some(value) => value,
        None => return Ok(false),
    };
    let expected: toml::Value =
        toml::from_str(binding["manifest_postimage"].as_str().unwrap()).map_err(err)?;
    let source = binding["source"].as_str().unwrap();
    let row = current.get("notes").and_then(|v| v.get(source));
    Ok(expected["notes"][source]
        .as_table()
        .unwrap()
        .iter()
        .all(|(k, v)| row.and_then(|r| r.get(k)) == Some(v)))
}
fn publish_manifest(root: &Dir, binding: &Value) -> Result<(), CoreError> {
    if Destination::from_binding(binding)? == Destination::Repository {
        return if declaration_current(root, binding)? {
            Ok(())
        } else {
            Err(err("repository convention changed before publication"))
        };
    }
    if !manifest_current(root, binding, true)? {
        return Err(err("Memory manifest changed before publication/recovery"));
    }
    if manifest_current(root, binding, false)? {
        return Ok(());
    }
    let bytes = binding["manifest_postimage"].as_str().unwrap().as_bytes();
    let temporary = format!("{MANIFEST}.{}.tmp", &digest(binding)?[7..]);
    if let Some(prior) = read(root, &temporary)? {
        if prior != bytes {
            return Err(err("Unowned manifest temporary preserved"));
        }
    } else {
        let mut f = root
            .open_with(&temporary, OpenOptions::new().write(true).create_new(true))
            .map_err(err)?;
        if let Ok(metadata) = root.metadata(MANIFEST) {
            f.set_permissions(metadata.permissions()).map_err(err)?;
        }
        f.write_all(bytes).map_err(err)?;
        f.sync_all().map_err(err)?;
    }
    if !manifest_current(root, binding, true)? {
        return Err(err("Manifest drift before publication"));
    }
    if binding["manifest_before"].is_null() {
        root.hard_link(&temporary, root, MANIFEST).map_err(err)?;
        root.remove_file(&temporary).map_err(err)?;
    } else {
        root.rename(&temporary, root, MANIFEST).map_err(err)?;
    }
    Ok(())
}
// Per-decision subject stays in owner provenance, never standing Configuration.
// Standing policy delegates only an exact owner/path set, not an actor label.
fn delegation_subject(
    target: &Path,
    material: &Value,
    binding: &Value,
) -> Result<Value, CoreError> {
    let subject = json!({"kind":"exact-material-decision-scope/v1","target":target,
        "owner":Destination::from_binding(binding)?.owner(),"semantics":binding["semantics"],
        "material":material,"work":binding["work"],"scope":binding["scope"],
        "dependencies":binding["dependencies"],"source":binding["source"],"before":binding["before"],
        "manifest_before":binding["manifest_before"],"manifest_postimage":binding["manifest_postimage"],
        "repository_convention":binding["repository_convention"],"superseded_sources":binding["superseded_sources"],
        "disposition":binding["disposition"].as_str().unwrap_or("retain")});
    Ok(json!({"revision":digest(&subject)?,"subject":subject}))
}
fn grant_matches(grant: &Value, subject: &Value) -> bool {
    let Some(fields) = grant.as_object() else {
        return false;
    };
    if fields.len() != 2 || !fields.contains_key("owner") || !fields.contains_key("scope") {
        return false;
    }
    let expected_owner = if subject["subject"]["owner"] == "memory" {
        "memory"
    } else {
        "repository"
    };
    let Some(paths) = grant["scope"].as_array() else {
        return false;
    };
    let Some(expected) = subject["subject"]["scope"].as_array() else {
        return false;
    };
    let canonical = |paths: &[Value]| -> Option<std::collections::BTreeSet<String>> {
        let mut result = std::collections::BTreeSet::new();
        for path in paths {
            let path = path.as_str()?.strip_prefix("path:")?;
            if path.contains(['*', '?', '[', ']']) {
                return None;
            }
            crate::decision_source::relative(path).ok()?;
            if !result.insert(path.to_owned()) {
                return None;
            }
        }
        Some(result)
    };
    !paths.is_empty()
        && paths.len() <= 32
        && grant["owner"] == expected_owner
        && canonical(paths).is_some_and(|paths| Some(paths) == canonical(expected))
}
fn delegated(config: &Value, subject: &Value) -> Option<Value> {
    config["admissions"]["decision_delegations"]
        .as_array()?
        .iter()
        .find(|grant| grant_matches(grant, subject))
        .cloned()
}
fn delegated_basis(subject: &Value, binding: &Value, grant: &Value) -> Value {
    json!({"kind":"exact-policy-delegated-decision","subject_revision":subject["revision"],
        "grant":grant,
        "policy_revision":binding["policy_revision"],"capability_revision":binding["capability_revision"],
        "source":".agentic-workspace/config.toml#assurance.decision_delegations",
        "identity_authentication":"not-claimed"})
}
fn material_bytes(material: &Value, binding: &Value) -> Result<Vec<u8>, CoreError> {
    let destination = Destination::from_binding(binding)?;
    if destination == Destination::Advisory {
        let lesson = material["lesson"]
            .as_str()
            .ok_or_else(|| err("advisory lesson missing"))?;
        if lesson.contains("```aw-decision")
            || material["rationale"]
                .as_str()
                .unwrap()
                .contains("```aw-decision")
        {
            return Err(err("advisory capture cannot introduce a decision record"));
        }
        let origin = material.get("origins").or_else(||material.get("origin")).map(|o|format!("\n\nEvidence origin (caller-asserted, not authenticated): `{}`. Historical source identity does not establish current runtime availability.\n",serde_json::to_string(o).unwrap())).unwrap_or_default();
        return Ok(format!("# Advisory knowledge\n\n{}\n\n## Future value\n\n{}{}\n\nMaterial authorship is unattributed. Retention was admitted through the current owner request; this note grants no decision, policy, proof or completion authority.\n", lesson, material["rationale"].as_str().unwrap(),origin).into_bytes());
    }
    let basis = digest(&json!([binding["semantics"], material, binding]))?;
    let historical_human = matches!(
        binding["semantics"].as_str(),
        Some("memory-bounded-human-decision-v1" | "repository-bounded-human-decision-v1")
    );
    let agent = binding.get("decision_authority").is_some();
    let reference = json!({"owner":if agent {"policy-delegated-decision"} else if historical_human {"bounded-human-answer"} else {"bounded-domain-answer"},"reference":basis,"revision":basis});
    let provenance = if agent {
        "Deciding provenance is an exact current repository-policy delegation for this owner-computed material subject. The acting agent is not identified or authenticated. Publication alone does not admit this consequence."
    } else if historical_human {
        "Deciding provenance is an exact bounded human answer, not cryptographically authenticated identity. Publication alone does not admit this consequence."
    } else {
        "Deciding provenance is an exact bounded domain answer under the current task and owner contract. The acting agent is not authenticated. Publication alone does not admit this consequence."
    };
    let record = json!({"id":material["id"],"decision":material["decision"],"consequence":material["consequence"],
        "authors":[{"kind":"unattributed","id":format!("request-material:{}",digest(material)?)}],"contributors":[],
        "authority":{"actor":{"kind":if historical_human && !agent {"human"} else {"agent"},"id":if agent {format!("policy-delegation:{basis}")} else {format!("bounded-answer:{basis}")}},"basis":[reference]},
        "scope":binding["scope"],"dependencies":binding["dependencies"].as_object().unwrap().iter().map(|(p,r)|json!({"owner":"repository","reference":p,"revision":r})).collect::<Vec<_>>(),
        "context":[],"supersedes":material["supersedes"]});
    let mut text = format!(
        "# Fallback decision\n\nMaterial supplied through an AW owner request. {provenance}\n\n{}\n\nRejected alternatives / trade-offs:\n{}\n\n```aw-decision\n{}\n```\n",
        material["rationale"].as_str().unwrap(),
        serde_json::to_string(&material["alternatives"]).map_err(err)?,
        serde_json::to_string_pretty(&record).map_err(err)?
    );
    if destination == Destination::Repository {
        text = format!(
            "# Repository decision\n\n## Decision\n\n{}\n\n## Consequence\n\n{}\n\n## Rationale and alternatives\n\n{}\n\n{}\n\n## Provenance\n\nMaterial authorship is unattributed. {}\n\n```aw-decision\n{}\n```\n",
            material["decision"].as_str().unwrap(),
            material["consequence"].as_str().unwrap(),
            material["rationale"].as_str().unwrap(),
            serde_json::to_string(&material["alternatives"]).map_err(err)?,
            if agent || !historical_human {
                provenance
            } else {
                "The deciding basis is the exact bounded human answer to the owner-issued proposal, not authenticated human identity. Publication is separate from deciding authority."
            },
            serde_json::to_string_pretty(&record).map_err(err)?
        );
    }
    if text.len() > 262144 {
        return Err(err("Decision exceeds bounded source size"));
    }
    crate::decision_source::record(
        text.as_bytes(),
        binding["source"].as_str().unwrap(),
        destination.record_owner(),
    )?;
    Ok(text.into_bytes())
}
fn proposal(material: &Value, binding: &Value, post: &str) -> Result<String, CoreError> {
    digest(
        &json!({"semantics":binding["semantics"],"material":material,"binding":binding,"post_revision":post}),
    )
}
fn outcome(invocation: &Value) -> Value {
    let kind = if invocation["arguments"]["binding"]["durable_owner"] == "advisory" {
        Destination::Advisory.result_kind()
    } else if invocation["source_owner"] == "decision-continuity" {
        Destination::Repository.result_kind()
    } else {
        Destination::Memory.result_kind()
    };
    json!({"status":"applied","effects":invocation["effects"],"value":{"kind":kind,
        "source":invocation["arguments"]["binding"]["source"],"post_revision":invocation["arguments"]["post_revision"],
        "authority_effect":"publication-only","continuing_custody":false,"completion_authority":false}})
}
// An immutable publication attempt is necessary but insufficient. Reconstruct
// the exact owner proposal and bounded answer before admitting deciding basis.
fn retained(target: &Path, source: &str) -> Result<Option<Value>, CoreError> {
    let root = Dir::open_ambient_dir(target, ambient_authority()).map_err(err)?;
    let Some(raw) = read(&root, &marker(source)?)? else {
        return Ok(None);
    };
    let record: Value = serde_json::from_slice(&raw).map_err(err)?;
    let i = &record["invocation"];
    let args = &i["arguments"];
    let request = &args["request"];
    let binding = &args["binding"];
    let destination = Destination::from_binding(binding)?;
    let attempt = crate::attempt_store::read_source(
        target.to_str().unwrap(),
        &serde_json::from_value(record["custody"]["attempt"].clone()).map_err(err)?,
    )?;
    if attempt["invocation"] != *i
        || i["operation_id"] != destination.operation(false)
        || i["source_owner"] != destination.owner()
        || args["target"] != target.to_str().unwrap()
        || binding["source"] != source
        || !(binding["semantics"] == destination.semantics()
            || (destination == Destination::Memory
                && binding["semantics"] == "memory-bounded-human-decision-v1")
            || (destination == Destination::Repository
                && binding["semantics"] == "repository-bounded-human-decision-v1"))
        || request["request_kind"] != destination.capture()
        || request["task_identity"] != binding["work"]
        || request["capability_revision"] != binding["capability_revision"]
        || (binding.get("decision_authority").is_none()
            && request["arguments"]["answer"] != destination.answer())
        || record["outcome"] != outcome(i)
    {
        return Err(err("Decision publication lacks its exact deciding basis"));
    }
    let mut owner = json!({"requests":[]});
    extend_destination(&mut owner, destination)?;
    let schema = &owner["requests"][0]["input_schema"];
    crate::schema_validator(schema, "retained decision answer")?
        .validate(&request["arguments"])
        .map_err(err)?;
    if !binding["scope"].as_array().is_some_and(|rows| {
        (destination == Destination::Advisory || !rows.is_empty())
            && rows.iter().all(Value::is_string)
    }) || !binding["dependencies"]
        .as_object()
        .is_some_and(|rows| rows.values().all(Value::is_string))
        || !binding["manifest_postimage"].is_string()
        || !binding["policy_revision"].is_string()
    {
        return Err(err("Malformed decision binding; no admission"));
    }
    let bytes = material_bytes(&request["arguments"]["material"], binding)?;
    let post = crate::native_intent::hash(&bytes);
    let exact_basis = if let Some(authority) = binding.get("decision_authority") {
        let subject = delegation_subject(target, &request["arguments"]["material"], binding)?;
        grant_matches(&authority["grant"], &subject)
            && *authority == delegated_basis(&subject, binding, &authority["grant"])
            && request["id"] == destination.capture()
            && request["arguments"].get("answer").is_none()
            && request["arguments"].get("proposal_revision").is_none()
    } else {
        request["arguments"]["proposal_revision"]
            == proposal(&request["arguments"]["material"], binding, &post)?
    };
    if args["post_revision"] != post || !exact_basis {
        return Err(err(
            "Decision answer does not bind the complete proposal/postimage",
        ));
    }
    crate::attempt_store::prepare_commit(
        target.to_str().unwrap(),
        record["custody"].clone(),
        record["outcome"].clone(),
    )?;
    Ok(Some(record))
}
fn committed(root: &Dir, target: &Path, record: &Value) -> Result<bool, CoreError> {
    let prepared = crate::attempt_store::prepare_commit(
        target.to_str().unwrap(),
        record["custody"].clone(),
        record["outcome"].clone(),
    )?;
    let Some(raw) = read(
        root,
        prepared["custody"]["committed"]["path"].as_str().unwrap(),
    )?
    else {
        return Ok(false);
    };
    let expected = serde_json::from_value(prepared["custody"]["committed"].clone()).map_err(err)?;
    let result = crate::attempt_store::read_source(target.to_str().unwrap(), &expected)?;
    let _ = raw;
    Ok(result["outcome"] == record["outcome"])
}

pub(crate) fn view_for(
    target: &Path,
    work: &Value,
    scope: &[String],
    config: &Value,
    contract: &Value,
    context: (Destination, &Value),
    request: Option<&Value>,
) -> Result<Value, CoreError> {
    view_for_selected(
        target, work, scope, config, contract, context, request, None,
    )
}

#[allow(clippy::too_many_arguments)]
pub(crate) fn view_for_selected(
    target: &Path,
    work: &Value,
    scope: &[String],
    config: &Value,
    contract: &Value,
    context: (Destination, &Value),
    request: Option<&Value>,
    selection: Option<&Value>,
) -> Result<Value, CoreError> {
    let (destination, context) = context;
    let owner = contract["owners"]
        .as_array()
        .unwrap()
        .iter()
        .find(|o| o["owner"] == destination.owner())
        .unwrap();
    let revision = digest(&json!([
        config["revision"],
        work,
        scope,
        destination.semantics()
    ]))?;
    let template = |kind: &str, args: Value| {
        json!({"kind":"agentic-workspace/public-request/v1","id":kind,"owner":destination.owner(),"owner_revision":owner["revision"],
        "source_revision":revision,"capability_revision":contract["revision"],"task_identity":work,"request_kind":kind,"arguments":args})
    };
    let mut view = json!({"status":"available","requests":[],"contribution":{"owner":destination.owner(),"revision":revision,"actions":[]},
        "agent_authority":"exact-domain-answer-under-current-task-authority"});
    if destination == Destination::Memory
        && let Some(stronger) = config["admissions"]["decision_record_target"]
            .as_str()
            .filter(|s| !s.is_empty())
    {
        view["status"] = json!("stronger-owner-required");
        view["destination"] = json!(stronger);
        view["gap"] = json!("repository-decision-owner-capture-request-unavailable");
        if request.is_some() {
            return Err(err(
                "Configured repository decision owner must be used; competing fallback capture is forbidden",
            ));
        }
        return Ok(view);
    }
    if scope.is_empty() && destination != Destination::Advisory {
        view["status"] = json!("exact-decision-scope-required");
        if request.is_some() {
            return Err(err(
                "Fallback decision requires exact current changed-path scope",
            ));
        }
        return Ok(view);
    }
    view["requests"] = json!([template(
        destination.capture(),
        json!({"material":{"id":"<deliberate-decision-id>","decision":"<deliberate decision>","consequence":"<bounded future consequence>",
        "rationale":"<rationale>","alternatives":[],"dependency_paths":[],"supersedes":[]}})
    )]);
    if destination == Destination::Advisory {
        view["requests"][0]["arguments"]["material"] = json!({"id":"<deliberate-note-id>","lesson":"<bounded advisory knowledge>","rationale":"<future decision value>","dependency_paths":[]});
    }
    let Some(request) = request else {
        let root = Dir::open_ambient_dir(target, ambient_authority()).map_err(err)?;
        let archive = archive(config, destination)?;
        if read(&root, &format!("{archive}/.confinement-check")).is_err() {
            view["status"] = json!("capture-source-reconciliation-required");
            view["requests"] = json!([]);
            return Ok(view);
        }
        let mut candidates = Vec::new();
        if let Ok(entries) = root.read_dir(&archive) {
            for entry in entries {
                let name = entry
                    .map_err(err)?
                    .file_name()
                    .to_string_lossy()
                    .to_string();
                if name.starts_with("native-") && name.ends_with(".md") {
                    candidates.push(format!("{archive}/{name}"));
                }
            }
        }
        if destination == Destination::Repository {
            candidates.extend(repository_sources(&root, &archive, scope)?);
        }
        candidates.sort();
        candidates.dedup();
        {
            let mut count = 0;
            for source in candidates {
                let hint = read(&root, &marker(&source)?)?
                    .and_then(|b| serde_json::from_slice::<Value>(&b).ok());
                if !hint.as_ref().is_some_and(|r| {
                    let binding = &r["invocation"]["arguments"]["binding"];
                    binding["scope"]
                        .as_array()
                        .is_some_and(|rows| rows.iter().any(|s| scope.iter().any(|p| s == p)))
                        || destination == Destination::Advisory
                            && binding["work"] == *work
                            && binding["scope"] == json!(scope)
                }) {
                    continue;
                }
                if let Some(record) = retained(target, &source)? {
                    count += 1;
                    if count > 64 {
                        return Err(err(
                            "Relevant native decision recovery exceeds bounded selection",
                        ));
                    }
                    let b = &record["invocation"]["arguments"]["binding"];
                    let published = committed(&root, target, &record)?;
                    if published && !declaration_current(&root, b)? {
                        view["contribution"]["blockers"] = json!([{"code":"decision-declaration-currentness-lost","message":"The exact declared decision source/scope changed; preserve source and reconcile its bounded answer.","affects":["task"]}]);
                    } else if (!published || cleanup_pending(&root, b)?)
                        && b["work"] == *work
                        && b["scope"] == json!(scope)
                    {
                        let retry = if read(&root, &source)?.is_none()
                            || read(&root, &source)?.is_some_and(|bytes| {
                                b["source_before"] == crate::native_intent::hash(&bytes)
                            }) {
                            record["invocation"]["arguments"]["request"].clone()
                        } else {
                            template(
                                destination.recover(),
                                json!({"source":source,"record_revision":digest(&record)?}),
                            )
                        };
                        view["requests"].as_array_mut().unwrap().push(retry);
                    }
                }
            }
        }
        let recoveries: Vec<_> = view["requests"]
            .as_array()
            .into_iter()
            .flatten()
            .filter(|r| r["request_kind"] == destination.recover())
            .collect();
        if recoveries.len() == 1 {
            return match view_for_selected(
                target,
                work,
                scope,
                config,
                contract,
                (destination, context),
                Some(recoveries[0]),
                selection,
            ) {
                Ok(mut current) => {
                    // Eager action preparation must preserve the exact recovery
                    // request for callers that select owner requests explicitly.
                    current["requests"]
                        .as_array_mut()
                        .unwrap()
                        .push(recoveries[0].clone());
                    Ok(current)
                }
                Err(problem) => {
                    view["contribution"]["blockers"] = json!([{"code":"memory-publication-recovery-unresolved","message":problem.to_string(),"affects":[format!("effect:{}",destination.effect())]}]);
                    Ok(view)
                }
            };
        }
        return Ok(view);
    };
    crate::prepare_request_value(
        json!({"request":request,"current_work":work,"capability_contract":contract}),
    )?;
    if request["source_revision"] != revision
        || request["owner"] != destination.owner()
        || ![destination.capture(), destination.recover()]
            .iter()
            .any(|kind| request["request_kind"] == *kind)
    {
        return Err(err(
            "Fallback decision request is stale; resolve current work/policy/scope",
        ));
    }
    let root = Dir::open_ambient_dir(target, ambient_authority()).map_err(err)?;
    let args = &request["arguments"];
    if destination == Destination::Advisory && args["disposition"] == "no-retention" {
        view["status"] = json!("not-retained");
        return Ok(view);
    }
    let mut recovery_paths = Vec::new();
    // An interrupted exact attempt keeps its original binding. Reconstructing a
    // revision after its journal/source changed would create another proposal.
    if request["request_kind"] == destination.capture() {
        let named = args["revise_source"]
            .as_str()
            .map(str::to_owned)
            .unwrap_or(source(
                config,
                args["material"]["id"].as_str().unwrap(),
                destination,
            )?);
        if let Some(record) = retained(target, &named)?
            && record["invocation"]["arguments"]["request"] == *request
            && !committed(&root, target, &record)?
        {
            let original = &record["invocation"]["arguments"];
            let b = &original["binding"];
            let current = read(&root, &named)?
                .map(|bytes| json!(crate::native_intent::hash(&bytes)))
                .unwrap_or(Value::Null);
            if b["work"] != *work
                || b["scope"] != json!(scope)
                || b["policy_revision"] != config["revision"]
                || b["capability_revision"] != contract["revision"]
                || !manifest_current(&root, b, true)?
                || (current != original["post_revision"] && current != b["source_before"])
                || dependencies(
                    &root,
                    &json!(
                        b["dependencies"]
                            .as_object()
                            .unwrap()
                            .keys()
                            .collect::<Vec<_>>()
                    ),
                )? != b["dependencies"]
            {
                return Err(err(
                    "Interrupted publication source changed; preserve exact attempt",
                ));
            }
            view["status"] = json!("write-ready");
            view["contribution"]["actions"] = json!([{"operation_id":destination.operation(false),"dependency_revision":digest(&json!([b,request,original["post_revision"]]))?,
                "arguments":original,"effects":[destination.effect()],"source_requests":[request]}]);
            return Ok(view);
        }
    }
    let (binding, post, operation) = if request["request_kind"] == destination.recover() {
        let source = args["source"].as_str().unwrap();
        let record =
            retained(target, source)?.ok_or_else(|| err("Decision recovery evidence missing"))?;
        recovery_paths = crate::attempt_store::write_paths(&record["invocation"])?;
        let binding = &record["invocation"]["arguments"]["binding"];
        let post = record["invocation"]["arguments"]["post_revision"]
            .as_str()
            .unwrap();
        if args["record_revision"] != digest(&record)?
            || Destination::from_binding(binding)? != destination
            || binding
                .get("decision_context_revision")
                .is_some_and(|revision| digest(context).is_ok_and(|current| *revision != current))
            || binding["work"] != *work
            || binding["scope"] != json!(scope)
            || binding["policy_revision"] != config["revision"]
            || binding["capability_revision"] != contract["revision"]
            || (binding.get("decision_authority").is_some()
                && delegated(
                    config,
                    &delegation_subject(
                        target,
                        &record["invocation"]["arguments"]["request"]["arguments"]["material"],
                        binding,
                    )?,
                )
                .is_none())
            || (committed(&root, target, &record)? && !cleanup_pending(&root, binding)?)
            || !manifest_current(&root, binding, true)?
            || read(&root, source)?.is_none_or(|b| crate::native_intent::hash(&b) != post)
            || dependencies(
                &root,
                &json!(
                    binding["dependencies"]
                        .as_object()
                        .unwrap()
                        .keys()
                        .collect::<Vec<_>>()
                ),
            )? != binding["dependencies"]
        {
            return Err(err(
                "Decision recovery is stale, consumed, or lacks current dependencies",
            ));
        }
        (
            binding.clone(),
            post.to_owned(),
            destination.operation(true),
        )
    } else {
        let material = &args["material"];
        if destination == Destination::Advisory && args["disposition"] != "no-retention" {
            let cues = advisory_applicability(material, scope)?;
            if cues["routes_from"].as_array().unwrap().is_empty()
                && cues["semantic_routes"].as_array().unwrap().is_empty()
            {
                view["status"] = json!("future-applicability-required");
                view["missing_judgment"] = json!({"question":"Under which existing activity or scoped path would this lesson change a later action? Supply routes_from or semantic_routes, or keep the observation provisional.","material":material});
                view["requests"][0]["arguments"] = args.clone();
                return Ok(view);
            }
        }
        if args["disposition"] != "no-retention"
            && context["records"]
                .as_array()
                .is_some_and(|records| records.len() >= 64)
        {
            return Err(err(
                "Relevant decision closure is at its bounded capacity; preserve source and narrow the proposed decision scope",
            ));
        }
        let revising = destination == Destination::Advisory && args["revise_source"].is_string();
        let source = if revising {
            args["revise_source"].as_str().unwrap().to_owned()
        } else {
            source(config, material["id"].as_str().unwrap(), destination)?
        };
        let source_before = if revising {
            crate::decision_source::relative(&source)?;
            let bytes = read(&root, &source)?.ok_or_else(|| err("Revision source is missing"))?;
            if args["source_revision"] != crate::native_intent::hash(&bytes)
                && args["source_revision"] != crate::decision_source::hash(&bytes)
            {
                return Err(err(
                    "Revision source changed; reread its exact current meaning",
                ));
            }
            if std::str::from_utf8(&bytes)
                .map_err(err)?
                .contains("```aw-decision")
            {
                return Err(err("Governing material requires its deciding owner"));
            }
            json!(crate::native_intent::hash(&bytes))
        } else {
            Value::Null
        };
        if !revising && args["disposition"] != "no-retention" && read(&root, &source)?.is_some() {
            if destination == Destination::Advisory
                && let Some(record) = retained(target, &source)?
                && confirmed_publication(
                    target,
                    &source,
                    &record["invocation"]["arguments"]["post_revision"],
                )
                .is_ok()
                && record["invocation"]["arguments"]["request"]["arguments"]["material"]
                    == *material
            {
                view["status"] = json!("unchanged");
                return Ok(view);
            }
            return Err(err(
                "Decision destination collision; existing source preserved",
            ));
        }
        if !revising && args["disposition"] != "no-retention" {
            require_new_identity(
                &root,
                &archive(config, destination)?,
                &material["id"],
                destination,
            )?;
        }
        for old in material["supersedes"].as_array().into_iter().flatten() {
            if !context["admissions"]
                .as_array()
                .into_iter()
                .flatten()
                .any(|a| a["id"] == old["id"] && a["material_revision"] == old["material_revision"])
            {
                return Err(err(
                    "Supersession requires an exact currently admitted former decision",
                ));
            }
        }
        let applicability = if destination == Destination::Advisory {
            Some(advisory_applicability(material, scope)?)
        } else {
            None
        };
        let (manifest_before, manifest_postimage) =
            if destination != Destination::Repository && args["disposition"] != "no-retention" {
                if revising {
                    revision_manifest(
                        &root,
                        &source,
                        &dependencies(&root, &material["dependency_paths"])?,
                        applicability.as_ref().unwrap(),
                        args["validity_review"]
                            .as_str()
                            .is_some_and(|s| !s.trim().is_empty()),
                    )?
                } else {
                    manifest_postimage(
                        &root,
                        &source,
                        scope,
                        (destination == Destination::Advisory)
                            .then_some(&dependencies(&root, &material["dependency_paths"])?),
                        applicability.as_ref(),
                    )?
                }
            } else {
                (Value::Null, String::new())
            };
        let mut binding = json!({"semantics":destination.semantics(),"source":source,"before":null,"work":work,"scope":scope,
            "manifest_before":manifest_before,"manifest_postimage":manifest_postimage,
            "policy_revision":config["revision"],"capability_revision":contract["revision"],"decision_context_revision":digest(context)?,
            "dependencies":dependencies(&root,&material["dependency_paths"])?,
            "superseded_sources":material["supersedes"].as_array().into_iter().flatten().map(|old| context["admissions"].as_array().unwrap().iter().find(|a| a["id"] == old["id"] && a["material_revision"] == old["material_revision"]).unwrap().clone()).collect::<Vec<_>>()});
        if destination == Destination::Advisory {
            binding["durable_owner"] = json!("advisory");
            binding["applicability"] = advisory_applicability(material, scope)?;
            if let Some(ids) = args.get("candidate_ids") {
                binding["candidate_ids"] = ids.clone();
            }
            if let Some(selection) = selection {
                binding["route_request"] = selection.clone();
            }
            if revising {
                binding["source_before"] = source_before;
                if let Some(record) = retained(target, &source)? {
                    if !committed(&root, target, &record)?
                        || cleanup_pending(&root, &record["invocation"]["arguments"]["binding"])?
                    {
                        return Err(err("Finish existing publication recovery before revision"));
                    }
                    if record["invocation"]["arguments"]["request"]["arguments"]["material"]["id"]
                        != material["id"]
                    {
                        return Err(err("Revision must preserve retained note identity"));
                    }
                    binding["marker_before"] = json!(crate::native_intent::hash(
                        &read(&root, &marker(&source)?)?.unwrap()
                    ));
                    binding["retire_receipts"] = receipt_sources(target, &record)?;
                }
            }
        }
        if destination == Destination::Repository {
            let convention = format!("{}/README.md", archive(config, destination)?);
            binding["durable_owner"] = json!("repository");
            binding["repository_convention"] = json!({"reference":convention,"revision":read(&root, &convention)?.map(|b|json!(crate::decision_source::hash(&b))).unwrap_or(Value::Null)});
        }
        if let Some(disposition) = args.get("disposition") {
            binding["disposition"] = disposition.clone();
        }
        let subject = delegation_subject(target, material, &binding)?;
        view["delegation_subject"] = subject.clone();
        let grant = delegated(config, &subject);
        let agent = args.get("answer").is_none() && grant.is_some();
        if agent {
            if request["id"] != destination.capture() || args.get("proposal_revision").is_some() {
                return Err(err(
                    "Delegated decision must use the exact issued material request",
                ));
            }
            binding["decision_authority"] =
                delegated_basis(&subject, &binding, grant.as_ref().unwrap());
            view["agent_authority"] = json!("exact-current-policy-delegation");
        }
        let bytes = material_bytes(material, &binding)?;
        if revising
            && read(&root, &source)?.as_deref() == Some(bytes.as_slice())
            && declaration_current(&root, &binding)?
        {
            view["status"] = json!("unchanged");
            return Ok(view);
        }
        let post = crate::native_intent::hash(&bytes);
        let proposal = proposal(material, &binding, &post)?;
        let mut answer = args.clone();
        answer.as_object_mut().unwrap().remove("answer");
        answer["proposal_revision"] = json!(proposal);
        let decisions = json!([{"id":"material-decision-disposition","question":if destination == Destination::Advisory {"Retain this exact bounded advisory knowledge? It grants no governing authority."} else {"Confirm this exact decision and disposition? Publication alone grants no deciding authority."},
            "material":{"binding":binding,"postimage":std::str::from_utf8(&bytes).map_err(err)?,"post_revision":post,
                "disposition":args["disposition"].as_str().unwrap_or("retain"),"publishes_source":args["disposition"] != "no-retention"},
            "response_request":{"request_kind":destination.capture(),"arguments":answer},"choices":[{"id":destination.answer(),"label":if destination == Destination::Advisory {"Retain this exact advisory knowledge"} else {"Confirm this exact bounded decision"}},{"id":"defer","label":"Defer without publication"}],"affects":["task",format!("effect:{}",destination.effect())]}]);

        if args["answer"].is_null() && !agent {
            if request["id"] != destination.capture() {
                return Err(err(
                    "decision material must use the issued material request",
                ));
            }
            view["status"] = json!("domain-decision-required");
            view["proposal"] = json!({"binding":binding,"postimage":std::str::from_utf8(&bytes).map_err(err)?,"post_revision":post,"proposal_revision":proposal,
                "disposition":args["disposition"].as_str().unwrap_or("retain"),"publishes_source":args["disposition"] != "no-retention",
                "authority_basis":"exact-bounded-domain-answer; no authenticated identity claim"});
            view["contribution"]["decisions"] = decisions;
            return Ok(view);
        }
        if !agent && args["proposal_revision"] != proposal {
            return Err(err(
                "Human answer is stale or does not bind this exact decision proposal",
            ));
        }
        if !agent {
            let compiled = crate::compile_value(
                json!({"intent":{"current_work":work},"capability_contract":contract,
            "contributions":[{"owner":destination.owner(),"revision":revision,"decisions":decisions}]}),
            )?;
            let mut exact =
                compiled["pending_consequences"]["decisions"][0]["response_request"].clone();
            exact["arguments"]["answer"] = args["answer"].clone();
            if exact != *request {
                return Err(err(
                    "answer differs from the exact owner-issued bounded request",
                ));
            }
            if args["answer"] == "defer" {
                view["status"] = json!("deferred");
                return Ok(view);
            }
        }
        if agent {
            view["proposal"] = json!({"binding":binding,"postimage":std::str::from_utf8(&bytes).map_err(err)?,
                "post_revision":post,"proposal_revision":proposal,"authority_basis":binding["decision_authority"]});
        }
        if args["disposition"] == "no-retention" {
            view["status"] = json!("no-retention");
            view["response"] = json!({"kind":"agentic-workspace/decision-disposition/v1","disposition":"no-retention",
                "proposal_revision":proposal,"authority_basis":if agent {binding["decision_authority"].clone()} else {json!({"kind":"exact-bounded-domain-answer","request_revision":digest(request)?,"identity_authentication":"not-claimed"})},"durable_state_created":false,"completion_authority":false});
            return Ok(view);
        }
        if !revising
            && let Some(record) = retained(target, &source)?
            && committed(&root, target, &record)?
        {
            return Err(err("This decision authorization was already consumed"));
        }
        (binding, post, destination.operation(false))
    };
    view["status"] = json!("write-ready");
    view["contribution"]["actions"] = json!([{"operation_id":operation,"dependency_revision":digest(&json!([binding,request,post]))?,
        "arguments":{"target":target,"request":request,"binding":binding,"post_revision":post,"recovery_paths":recovery_paths},"effects":[destination.effect()],"source_requests":[request]}]);
    Ok(view)
}

pub(crate) fn execute(
    target: &Path,
    decision: &Value,
    invocation: &Value,
    mut revalidate: impl FnMut() -> Result<(), CoreError>,
) -> Result<Value, CoreError> {
    let mut result = execute_checked(target, decision, invocation, &mut revalidate, &mut |_| {
        Ok(())
    })?;
    result["post_effect_changed_paths"] = json!([result["outcome"]["value"]["source"]]);
    Ok(result)
}

pub(crate) fn write_scope(action: &Value) -> Result<Vec<String>, CoreError> {
    let binding = &action["arguments"]["binding"];
    let destination = Destination::from_binding(binding)?;
    let source = binding["source"]
        .as_str()
        .ok_or_else(|| err("decision source missing"))?;
    let mut paths =
        crate::attempt_store::write_paths(&json!({"idempotency_key":action["logical_effect_id"]}))?;
    paths.extend(
        action["arguments"]["recovery_paths"]
            .as_array()
            .into_iter()
            .flatten()
            .filter_map(Value::as_str)
            .map(str::to_owned),
    );
    paths.extend([
        source.to_owned(),
        format!("{source}.*.tmp"),
        marker(source)?,
        format!("{}.tmp", marker(source)?),
        format!(
            ".agentic-workspace/local/effects/{}.lock",
            destination.owner()
        ),
    ]);
    paths.extend(
        binding["retire_receipts"]
            .as_array()
            .into_iter()
            .flatten()
            .filter_map(|r| r["path"].as_str())
            .map(str::to_owned),
    );
    if destination != Destination::Repository {
        paths.extend([MANIFEST.to_owned(), format!("{MANIFEST}.*.tmp")]);
    }
    Ok(paths)
}
fn execute_checked(
    target: &Path,
    decision: &Value,
    invocation: &Value,
    revalidate: &mut dyn FnMut() -> Result<(), CoreError>,
    observe: &mut dyn FnMut(&str) -> Result<(), CoreError>,
) -> Result<Value, CoreError> {
    let destination = Destination::from_binding(&invocation["arguments"]["binding"])?;
    let raw = serde_json::to_vec(
        &json!({"invocation":invocation,"custody":null,"outcome":outcome(invocation)}),
    )
    .map_err(err)?;
    let custody_budget = 8192 + 4 * serde_json::to_vec(&target).map_err(err)?.len();
    if raw.len().saturating_add(custody_budget) > crate::decision_source::MAX_SOURCE_BYTES {
        return Err(err(
            "decision publication carrier exceeds bounded recovery size; narrow the material",
        ));
    }
    let root = Dir::open_ambient_dir(target, ambient_authority()).map_err(err)?;
    let lock_path = format!(
        ".agentic-workspace/local/effects/{}.lock",
        destination.owner()
    );
    read(&root, &lock_path)?;
    root.create_dir_all(".agentic-workspace/local/effects")
        .map_err(err)?;
    read(&root, &lock_path)?;
    let lock = root
        .open_with(
            &lock_path,
            OpenOptions::new().read(true).write(true).create(true),
        )
        .map_err(err)?
        .into_std();
    if lock.metadata().map_err(err)?.len() != 0 {
        return Err(err("Unknown Memory lock preserved"));
    }
    lock.try_lock().map_err(err)?;
    revalidate()?;
    let args = &invocation["arguments"];
    let source = args["binding"]["source"].as_str().unwrap();
    let prior = retained(target, source)?;
    if invocation["operation_id"] == destination.operation(true) {
        let record = prior.ok_or_else(|| err("Decision recovery missing"))?;
        if destination == Destination::Advisory {
            publish_manifest(&root, &args["binding"])?;
            let done = if committed(&root, target, &record)? {
                crate::attempt_store::prepare_commit(
                    target.to_str().unwrap(),
                    record["custody"].clone(),
                    record["outcome"].clone(),
                )?
            } else {
                crate::attempt_store::commit(
                    json!({"target":target,"custody":record["custody"],"outcome":record["outcome"]}),
                )?
            };
            cleanup_receipts(&root, target, &args["binding"])?;
            return Ok(json!({"outcome":record["outcome"],"custody":done["custody"]}));
        }
        let admitted = crate::attempt_store::admit(
            json!({"target":target,"decision":decision,"invocation":invocation}),
        )?;
        revalidate()?;
        publish_manifest(&root, &args["binding"])?;
        crate::attempt_store::commit(
            json!({"target":target,"custody":record["custody"],"outcome":record["outcome"]}),
        )?;
        let out = outcome(invocation);
        let done = crate::attempt_store::commit(
            json!({"target":target,"custody":admitted["custody"],"outcome":out}),
        )?;
        return Ok(json!({"outcome":out,"custody":done["custody"]}));
    }
    let replacing = prior
        .as_ref()
        .is_some_and(|r| r["invocation"] != *invocation)
        && args["binding"]["marker_before"].is_string()
        && read(&root, &marker(source)?)?
            .is_some_and(|b| args["binding"]["marker_before"] == crate::native_intent::hash(&b));
    if prior
        .as_ref()
        .is_some_and(|r| r["invocation"] != *invocation)
        && !replacing
    {
        return Err(err("Decision attempt collision preserved"));
    }
    let bytes = material_bytes(&args["request"]["arguments"]["material"], &args["binding"])?;
    if crate::native_intent::hash(&bytes) != args["post_revision"] {
        return Err(err("Decision postimage changed"));
    }
    let temporary = format!("{source}.{}.tmp", &digest(invocation)?[7..]);
    if prior.is_none() && read(&root, &temporary)?.is_some() {
        return Err(err("Unowned decision temporary preserved"));
    }
    let manifest_temporary = format!("{MANIFEST}.{}.tmp", &digest(&args["binding"])?[7..]);
    if destination == Destination::Memory
        && prior.is_none()
        && read(&root, &manifest_temporary)?.is_some()
    {
        return Err(err("Unowned manifest temporary preserved"));
    }
    read(&root, source)?;
    let parent = source.rsplit_once('/').unwrap().0;
    root.create_dir_all(parent).map_err(err)?;
    read(&root, source)?;
    let admitted = crate::attempt_store::admit(
        json!({"target":target,"decision":decision,"invocation":invocation,"custody":prior.as_ref().filter(|_| !replacing).map(|r|&r["custody"])}),
    )?;
    let out = outcome(invocation);
    let record = json!({"invocation":invocation,"custody":admitted["custody"],"outcome":out});
    let raw = serde_json::to_vec(&record).map_err(err)?;
    if raw.len() > crate::decision_source::MAX_SOURCE_BYTES {
        return Err(err(
            "decision publication carrier exceeds bounded recovery size",
        ));
    }
    if replacing {
        let temporary = format!("{}.tmp", marker(source)?);
        if let Some(old) = read(&root, &temporary)? {
            if old != raw {
                return Err(err("Unknown revision journal temporary preserved"));
            }
        } else {
            let mut f = root
                .open_with(&temporary, OpenOptions::new().write(true).create_new(true))
                .map_err(err)?;
            f.write_all(&raw).map_err(err)?;
            f.sync_all().map_err(err)?;
        }
        if read(&root, &marker(source)?)?
            .is_none_or(|b| args["binding"]["marker_before"] != crate::native_intent::hash(&b))
        {
            return Err(err("Publication marker changed before revision"));
        }
        root.rename(&temporary, &root, marker(source)?)
            .map_err(err)?;
    } else if prior.is_none() {
        let mut f = root
            .open_with(
                marker(source)?,
                OpenOptions::new().write(true).create_new(true),
            )
            .map_err(err)?;
        f.write_all(&raw).map_err(err)?;
        f.sync_all().map_err(err)?;
    }
    observe("prepared")?;
    if let Some(existing) = read(&root, &temporary)? {
        if existing != bytes {
            return Err(err("Unknown decision temporary preserved"));
        }
    } else {
        let mut f = root
            .open_with(&temporary, OpenOptions::new().write(true).create_new(true))
            .map_err(err)?;
        if args["binding"]["source_before"].is_string() {
            f.set_permissions(root.metadata(source).map_err(err)?.permissions())
                .map_err(err)?;
        }
        f.write_all(&bytes).map_err(err)?;
        f.sync_all().map_err(err)?;
    }
    revalidate()?;
    // Atomic no-clobber publication. Neither a race nor recovery can overwrite
    // an externally created destination; the prepared source remains recoverable.
    let existing = read(&root, source)?
        .map(|b| json!(crate::native_intent::hash(&b)))
        .unwrap_or(Value::Null);
    if existing == args["post_revision"] {
        root.remove_file(&temporary).map_err(err)?;
    } else if args["binding"]["source_before"].is_string() {
        if existing != args["binding"]["source_before"] {
            return Err(err("Advice changed before revision publication"));
        }
        root.rename(&temporary, &root, source).map_err(err)?;
    } else {
        root.hard_link(&temporary, &root, source).map_err(err)?;
        root.remove_file(&temporary).map_err(err)?;
    }
    observe("source-published")?;
    publish_manifest(&root, &args["binding"])?;
    observe("manifest-published")?;
    let done = crate::attempt_store::commit(
        json!({"target":target,"custody":admitted["custody"],"outcome":out}),
    )?;
    observe("committed")?;
    cleanup_receipts(&root, target, &args["binding"])?;
    Ok(json!({"outcome":out,"custody":done["custody"]}))
}

/// Selected native sources join the existing continuity context. No scan or
/// retained artifact is needed for work without an exact decision scope.
fn repository_sources(
    root: &Dir,
    archive: &str,
    scope: &[String],
) -> Result<Vec<String>, CoreError> {
    let mut sources = Vec::new();
    let overlaps = |rows: &Value| {
        rows.as_array()
            .is_some_and(|rows| rows.iter().any(|s| scope.iter().any(|p| s == p)))
    };
    let canonical_name = |name: &str, prefix: &str, suffix: &str| {
        name.strip_prefix(prefix)
            .and_then(|s| s.strip_suffix(suffix))
            .is_some_and(|s| s.len() == 64 && s.bytes().all(|b| b.is_ascii_hexdigit()))
    };
    // Source scope is only a selection hint. A selected source must still have
    // exact admitted custody below, including when its carrier is malformed.
    if let Ok(entries) = root.read_dir(archive) {
        let mut observed = 0;
        for entry in entries {
            let name = entry
                .map_err(err)?
                .file_name()
                .to_string_lossy()
                .to_string();
            if !canonical_name(&name, "native-", ".md") {
                continue;
            }
            observed += 1;
            if observed > 4096 {
                return Err(err("decision source discovery exceeds bounded observation"));
            }
            let source = format!("{archive}/{name}");
            if let Some(record) = read(root, &source)?.and_then(|bytes| {
                crate::decision_source::record(&bytes, &source, "repository").ok()
            }) && overlaps(&record["scope"])
            {
                sources.push(source);
            }
        }
    }
    // Existing publication carriers retain custody if their repository
    // source disappears. This is not a second archive or decision index.
    if let Ok(entries) = root.read_dir(".agentic-workspace/local/effects") {
        let mut observed = 0;
        for entry in entries {
            let name = entry
                .map_err(err)?
                .file_name()
                .to_string_lossy()
                .to_string();
            if !canonical_name(&name, "decision-", ".prepared.json") {
                continue;
            }
            observed += 1;
            if observed > 4096 {
                return Err(err(
                    "decision publication discovery exceeds bounded observation",
                ));
            }
            let path = format!(".agentic-workspace/local/effects/{name}");
            let Ok(Some(bytes)) = read(root, &path) else {
                continue;
            };
            // Unknown residue cannot select an owner or scope. Preserve it;
            // the source-specific path above still rejects damaged relevant custody.
            let Ok(record) = serde_json::from_slice::<Value>(&bytes) else {
                continue;
            };
            let binding = &record["invocation"]["arguments"]["binding"];
            if binding["durable_owner"] == "repository"
                && binding["source"]
                    .as_str()
                    .is_some_and(|s| s.starts_with(&format!("{archive}/native-")))
                && overlaps(&binding["scope"])
            {
                sources.push(binding["source"].as_str().unwrap().to_owned());
            }
        }
    }
    sources.sort();
    sources.dedup();
    Ok(sources)
}

pub(crate) fn context(target: &Path, config: &Value, scope: &[String]) -> Result<Value, CoreError> {
    context_for(target, config, scope, Destination::Memory)
}
pub(crate) fn context_for(
    target: &Path,
    config: &Value,
    scope: &[String],
    destination: Destination,
) -> Result<Value, CoreError> {
    let mut result = json!({"records":[],"admissions":[],"current_dependencies":[],"required_records":[],"publication_sources":[],"applicable_scope":scope});
    if scope.is_empty()
        || (destination == Destination::Memory
            && !crate::native_config::module_enabled(config, "memory"))
    {
        return Ok(result);
    }
    let root = Dir::open_ambient_dir(target, ambient_authority()).map_err(err)?;
    let archive = archive(config, destination)?;
    let mut pending: Vec<String> = if destination == Destination::Repository {
        repository_sources(&root, &archive, scope)?
    } else {
        let Ok(Some(manifest)) = read(&root, MANIFEST) else {
            return Ok(result);
        };
        let Some(manifest): Option<toml::Value> = std::str::from_utf8(&manifest)
            .ok()
            .and_then(|s| toml::from_str(s).ok())
        else {
            // Advisory source errors are already exposed by Memory. Only an exact
            // native declaration/retained answer can introduce a governing blocker.
            return Ok(result);
        };
        let entries = manifest.get("notes").and_then(toml::Value::as_table);
        entries
            .into_iter()
            .flatten()
            .filter(|(_, entry)| {
                entry.get("native_decision").and_then(toml::Value::as_bool) == Some(true)
                    && entry
                        .get("decision_scope")
                        .and_then(toml::Value::as_array)
                        .is_some_and(|rows| {
                            rows.iter()
                                .any(|s| s.as_str().is_some_and(|s| scope.iter().any(|p| p == s)))
                        })
            })
            .map(|(source, _)| source.clone())
            .collect()
    };
    let mut selected = std::collections::BTreeSet::new();
    while let Some(source) = pending.pop() {
        if !selected.insert(source.clone()) {
            continue;
        }
        if selected.len() > 64 {
            return Err(err(
                "Relevant native decision supersession closure exceeds bounded selection",
            ));
        }
        if !source.starts_with(&format!("{archive}/native-")) {
            return Err(err(
                "Native decision declaration is outside current fallback archive",
            ));
        }
        let record = retained(target, &source)?.ok_or_else(|| {
            if destination == Destination::Repository
                && config["admissions"]["decision_record_revision"]
                    .as_str()
                    .is_none_or(str::is_empty)
            {
                err(format!(
                    "assurance.decision_record_revision is missing for {source} (destination {archive}); only the repository/source owner can admit an exact archive Git commit; native decision lacks bounded answer"
                ))
            } else {
                err("Native decision lacks bounded answer; source remains advisory")
            }
        })?;
        let args = &record["invocation"]["arguments"];
        let binding = &args["binding"];
        if Destination::from_binding(binding)? != destination {
            return Err(err("decision publication belongs to another durable owner"));
        }
        if !declaration_current(&root, binding)? {
            return Err(err(
                "Decision declaration changed; reconcile exact source/scope",
            ));
        }
        // Exact retained attempt custody identifies publication bytes, including
        // the temporary file observed by the pre-publication revalidation. This
        // does not admit an uncommitted decision as governing context.
        if destination == Destination::Repository {
            let temporary = format!("{source}.{}.tmp", &digest(&record["invocation"])?[7..]);
            for reference in [&source, &temporary] {
                result["publication_sources"]
                    .as_array_mut()
                    .unwrap()
                    .push(json!({"reference":reference,"revision":args["post_revision"]}));
            }
        }
        if !committed(&root, target, &record)? {
            continue;
        }
        let bytes = read(&root, &source)?.ok_or_else(|| {
            err("Native decision source disappeared; preserve declaration and reconcile")
        })?;
        let normalized =
            crate::decision_source::record(&bytes, &source, destination.record_owner())?;
        if crate::native_intent::hash(&bytes) != args["post_revision"] {
            return Err(err(
                "Native decision source changed; reconcile bounded answer",
            ));
        }
        for ancestor in normalized["supersedes"].as_array().unwrap() {
            let admission = binding["superseded_sources"]
                .as_array()
                .into_iter()
                .flatten()
                .find(|a| {
                    a["id"] == ancestor["id"]
                        && a["material_revision"] == ancestor["material_revision"]
                })
                .ok_or_else(|| err("Supersession lacks its bound source admission"))?;
            let reference = admission["source"]["reference"]
                .as_str()
                .ok_or_else(|| err("Supersession source locator is missing"))?;
            if reference == self::source(config, ancestor["id"].as_str().unwrap(), destination)?
                && retained(target, reference)?.is_some()
            {
                pending.push(reference.to_owned());
            } else {
                result["required_records"]
                    .as_array_mut()
                    .unwrap()
                    .push(admission.clone());
            }
        }
        result["admissions"].as_array_mut().unwrap().push(json!({"id":normalized["id"],"material_revision":normalized["material_revision"],"source":normalized["source"],"rationale_reference":source}));
        for dependency in normalized["authority"]["basis"]
            .as_array()
            .unwrap()
            .iter()
            .chain(normalized["dependencies"].as_array().unwrap())
            .chain(std::iter::once(&normalized["source"]))
        {
            // Retain admitted history when policy or facts drift, but do not
            // invent current authority. Continuity suppresses stale consequences
            // and permits a new exact decision to supersede the former record.
            if matches!(
                dependency["owner"].as_str(),
                Some(
                    "bounded-human-answer" | "bounded-domain-answer" | "policy-delegated-decision"
                )
            ) && (binding["policy_revision"] != config["revision"]
                || (dependency["owner"] == "policy-delegated-decision"
                    && delegated(
                        config,
                        &delegation_subject(
                            target,
                            &record["invocation"]["arguments"]["request"]["arguments"]["material"],
                            binding,
                        )?,
                    )
                    .is_none()))
            {
                continue;
            }
            if dependency["owner"] == "repository"
                && read(&root, dependency["reference"].as_str().unwrap())?
                    .is_none_or(|b| crate::decision_source::hash(&b) != dependency["revision"])
            {
                continue;
            }
            if !result["current_dependencies"]
                .as_array()
                .unwrap()
                .contains(dependency)
            {
                result["current_dependencies"]
                    .as_array_mut()
                    .unwrap()
                    .push(dependency.clone());
            }
        }
        result["records"].as_array_mut().unwrap().push(normalized);
    }
    Ok(result)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn historical_human_material_keeps_its_provenance() {
        let material = json!({"id":"fixture:history","decision":"Keep the boundary",
            "consequence":"Preserve scope", "rationale":"A durable fixture choice",
            "alternatives":[], "supersedes":[]});
        for (destination, old) in [
            (Destination::Memory, "memory-bounded-human-decision-v1"),
            (
                Destination::Repository,
                "repository-bounded-human-decision-v1",
            ),
        ] {
            let mut binding = json!({"semantics":old,"source":"docs/decision.md",
                "scope":["path:src/a.rs"],"dependencies":{}});
            let historical = material_bytes(&material, &binding).unwrap();
            let record = crate::decision_source::record(
                &historical,
                "docs/decision.md",
                destination.record_owner(),
            )
            .unwrap();
            assert_eq!(record["authority"]["actor"]["kind"], "human");
            assert_eq!(
                record["authority"]["basis"][0]["owner"],
                "bounded-human-answer"
            );
            binding["semantics"] = json!(destination.semantics());
            let current = material_bytes(&material, &binding).unwrap();
            let record = crate::decision_source::record(
                &current,
                "docs/decision.md",
                destination.record_owner(),
            )
            .unwrap();
            assert_eq!(record["authority"]["actor"]["kind"], "agent");
            assert_eq!(
                record["authority"]["basis"][0]["owner"],
                "bounded-domain-answer"
            );
            binding["semantics"] = json!(old);
            assert_eq!(material_bytes(&material, &binding).unwrap(), historical);
        }
    }

    #[test]
    fn standing_delegation_rejects_patterns_even_without_schema_validation() {
        for owner in ["memory", "repository"] {
            let subject = |scope: Value| json!({"subject":{"owner":owner,"scope":scope}});
            let concrete = json!(["path:src/a.rs", "path:src/b.rs"]);
            let grant = json!({"owner":owner,"scope":concrete});
            assert!(grant_matches(
                &grant,
                &subject(json!(["path:src/b.rs", "path:src/a.rs"]))
            ));
            for pattern in [
                "path:src/*.rs",
                "path:src/?.rs",
                "path:src/[ab].rs",
                "path:src/a[.rs",
                "path:src/a].rs",
            ] {
                let scope = json!([pattern]);
                let wildcard_grant = json!({"owner":owner,"scope":scope});
                assert!(!grant_matches(&wildcard_grant, &subject(scope.clone())));
                assert!(!grant_matches(&wildcard_grant, &subject(concrete.clone())));
                assert!(!grant_matches(&grant, &subject(scope)));
            }
        }
    }

    #[test]
    fn advisory_revision_preserves_identity_recovers_and_bounds_receipts() {
        let target = std::env::temp_dir().join(format!(
            "aw-advice-revision-{}-{}",
            std::process::id(),
            std::time::SystemTime::now()
                .duration_since(std::time::UNIX_EPOCH)
                .unwrap()
                .as_nanos()
        ));
        std::fs::create_dir_all(&target).unwrap();
        std::fs::write(
            target.join("policy.md"),
            "Use the configured shared service.",
        )
        .unwrap();
        let target = std::fs::canonicalize(target).unwrap();
        let input = json!({"target":target,"task":"Improve fixture setup advice"});
        let start = |request: Value| {
            let mut i = input.clone();
            i["request"] = request;
            crate::native_public::start(i).unwrap()
        };
        let mut material = json!({"id":"fixture:setup","lesson":"Check current service status before provisioning.","rationale":"An earlier running observation avoided duplicate setup.","dependency_paths":["policy.md"],"routes_from":["tests/fixture/**"],"origin":{"producer":"acting-agent","reference":"fixture:first-observation","coverage":"bounded"}});
        let request_for = |material: &Value, source: Option<&str>| {
            let initial = start(Value::Null);
            let mut r = initial["memory"]["advisory_capture"]["requests"][0].clone();
            r["arguments"]["material"] = material.clone();
            if let Some(source) = source {
                r["arguments"]["revise_source"] = json!(source);
                r["arguments"]["source_revision"] = json!(crate::native_intent::hash(
                    &std::fs::read(target.join(source)).unwrap()
                ));
            }
            r
        };
        let ready = |request: Value| {
            let proposal = start(request);
            let mut answer =
                proposal["decision_packet"]["decision_request"]["response_request"].clone();
            answer["arguments"]["answer"] = json!("confirm-retention");
            start(answer)
        };
        let original = ready(request_for(&material, None));
        let published=crate::native_public::invoke_checked(json!({"target":target,"task":input["task"],"invocation":original["decision_packet"]["primary_action"]})).unwrap();
        let source = published["value"]["source"].as_str().unwrap();
        let root = Dir::open_ambient_dir(&target, ambient_authority()).unwrap();
        let old_body = std::fs::read(target.join(source)).unwrap();
        let unchanged = request_for(&material, Some(source));
        assert_eq!(
            start(unchanged)["memory"]["advisory_capture"]["status"],
            "unchanged"
        );
        for (n, stage) in [
            "prepared",
            "source-published",
            "manifest-published",
            "committed",
        ]
        .into_iter()
        .enumerate()
        {
            material["lesson"] = json!(format!(
                "Read policy.md, check current service status, and reuse the shared fixture; correction {n}."
            ));
            material["origin"]["reference"] = json!(format!("fixture:repair-{n}"));
            let request = request_for(&material, Some(source));
            let revised = ready(request.clone());
            let action = &revised["decision_packet"]["primary_action"];
            assert!(
                execute_checked(
                    &target,
                    &revised["decision_packet"],
                    action,
                    &mut || Ok(()),
                    &mut |s| if s == stage {
                        Err(err("lost publication reply"))
                    } else {
                        Ok(())
                    }
                )
                .is_err()
            );
            if stage == "prepared" {
                let resumed = start(action["arguments"]["request"].clone());
                assert_eq!(resumed["decision_packet"]["primary_action"], *action);
                crate::native_public::invoke_checked(json!({"target":target,"task":input["task"],"invocation":resumed["decision_packet"]["primary_action"]})).unwrap();
            } else {
                let record = retained(&target, source).unwrap().unwrap();
                let initial = start(Value::Null);
                let recovery = initial["memory"]["advisory_capture"]["requests"]
                    .as_array()
                    .unwrap()
                    .iter()
                    .find(|r| r["request_kind"] == ADVISORY_RECOVER)
                    .unwrap()
                    .clone();
                assert_eq!(
                    recovery["arguments"]["record_revision"],
                    digest(&record).unwrap()
                );
                let recovered = start(recovery);
                crate::native_public::invoke_checked(json!({"target":target,"task":input["task"],"invocation":recovered["decision_packet"]["primary_action"]})).unwrap();
            }
            let record = retained(&target, source).unwrap().unwrap();
            assert!(committed(&root, &target, &record).unwrap());
            assert!(
                !cleanup_pending(&root, &record["invocation"]["arguments"]["binding"]).unwrap()
            );
            assert_eq!(
                std::fs::read_dir(target.join(".agentic-workspace/local/effects"))
                    .unwrap()
                    .count(),
                4,
                "one current journal, attempt/result and shared lock, independent of correction count"
            );
            assert_eq!(
                std::fs::read_dir(target.join(".agentic-workspace/memory/repo/domains"))
                    .unwrap()
                    .count(),
                1
            );
            assert_eq!(
                start(request_for(&material, Some(source)))["memory"]["advisory_capture"]["status"],
                "unchanged"
            );
            assert!(
                !std::fs::read_to_string(target.join(source))
                    .unwrap()
                    .contains("fixture:first-observation")
            );
        }
        assert_ne!(std::fs::read(target.join(source)).unwrap(), old_body);
        let stale = request_for(&material, Some(source));
        std::fs::write(target.join(source), "External source drift").unwrap();
        let mut invalid = input.clone();
        invalid["request"] = stale;
        assert!(crate::native_public::start(invalid).is_err());
        let drifted = std::fs::read(target.join(source)).unwrap();
        std::fs::write(
            target.join("policy.md"),
            "Use a dedicated isolated service.",
        )
        .unwrap();
        let renewal = request_for(&material, Some(source));
        let mut invalid = input.clone();
        invalid["request"] = renewal.clone();
        assert!(
            crate::native_public::start(invalid).is_err(),
            "baseline cannot silently renew"
        );
        assert_eq!(std::fs::read(target.join(source)).unwrap(), drifted);
        // Review is an explicit bounded judgment, never automatic dependency refresh.
        let mut renewal = renewal;
        renewal["arguments"]["validity_review"] =
            json!("Read changed policy; rewrite advice for its new dedicated-service scope.");
        renewal["arguments"]["material"]["lesson"] = json!(
            "Provision the dedicated isolated service after checking current policy and status."
        );
        let reviewed = ready(renewal);
        crate::native_public::invoke_checked(json!({"target":target,"task":input["task"],"invocation":reviewed["decision_packet"]["primary_action"]})).unwrap();
        assert_eq!(
            std::fs::read_dir(target.join(".agentic-workspace/local/effects"))
                .unwrap()
                .count(),
            4
        );
        drop(root);
        std::fs::remove_dir_all(target).unwrap();
    }
    #[test]
    fn no_edit_advisory_authoring_reaches_future_activity_with_distinct_validity() {
        let target = std::env::temp_dir().join(format!(
            "aw-activity-advice-{}-{}",
            std::process::id(),
            std::time::SystemTime::now()
                .duration_since(std::time::UNIX_EPOCH)
                .unwrap()
                .as_nanos()
        ));
        std::fs::create_dir_all(target.join("tools/skills")).unwrap();
        std::fs::write(
            target.join("tools/skills/REGISTRY.json"),
            serde_json::to_vec(
                &json!({"skills":[{"id":"checks","semantic_routes":["repository/checks"]}]}),
            )
            .unwrap(),
        )
        .unwrap();
        std::fs::write(target.join("service-policy.md"),"Use the configured shared fixture service; check its current status before provisioning.").unwrap();
        std::fs::write(target.join("service-status.txt"), "running").unwrap();
        let context = json!({"target":target,"task":"Investigate fixture setup after redundant provisioning"});
        let start = |request: Value| {
            let mut input = context.clone();
            input["request"] = request;
            crate::native_public::start(input).unwrap()
        };
        let initial = start(Value::Null);
        assert_eq!(
            initial["memory"]["capture"]["status"],
            "exact-decision-scope-required"
        );
        let mut request = initial["memory"]["advisory_capture"]["requests"][0].clone();
        request["arguments"]["material"] = json!({"id":"fixture:shared-service","lesson":"Consult service-policy.md and check current service status before provisioning another fixture instance.",
            "rationale":"The earlier investigation found a running shared service after redundant provisioning wasted setup work.","dependency_paths":["service-policy.md"],
            "origin":{"producer":"acting-agent","reference":"fixture:redundant-provisioning","coverage":"bounded"}});
        assert_eq!(
            start(request.clone())["memory"]["advisory_capture"]["status"],
            "future-applicability-required"
        );
        request["arguments"]["material"]["semantic_routes"] = json!(["repository/checks"]);
        request["arguments"]["material"]["routes_from"] = json!(["tests/fixture/**"]);
        let proposal = start(request);
        assert_eq!(
            proposal["memory"]["advisory_capture"]["proposal"]["binding"]["scope"],
            json!([])
        );
        let mut answer =
            proposal["decision_packet"]["decision_request"]["response_request"].clone();
        answer["arguments"]["answer"] = json!("confirm-retention");
        let ready = start(answer.clone());
        let mut forged = answer;
        forged["arguments"]["material"]["semantic_routes"] = json!(["repository/other"]);
        assert!(
            crate::native_public::start(
                json!({"target":target,"task":context["task"],"request":forged})
            )
            .is_err()
        );
        let action = &ready["decision_packet"]["primary_action"];
        let result = crate::native_public::invoke_checked(
            json!({"target":target,"task":context["task"],"invocation":action}),
        )
        .unwrap();
        assert_eq!(result["effect_outcome"]["status"], "committed");
        let source = result["value"]["source"].as_str().unwrap();
        let manifest: toml::Value =
            toml::from_str(&std::fs::read_to_string(target.join(MANIFEST)).unwrap()).unwrap();
        assert_eq!(
            manifest["notes"][source]["semantic_routes"][0].as_str(),
            Some("repository/checks")
        );
        assert_eq!(
            manifest["notes"][source]["routes_from"][0].as_str(),
            Some("tests/fixture/**")
        );
        let fresh_context = json!({"target":target,"task":"Prepare fixture checks without edits"});
        let fresh = crate::native_public::start(fresh_context.clone()).unwrap();
        let mut route = fresh["semantic_routes"]["requests"]
            .as_array()
            .unwrap()
            .iter()
            .find(|r| r["request_kind"] == "semantic-routes/select/v1")
            .unwrap()
            .clone();
        route["arguments"] = json!({"posture":"selected","routes":["repository/checks"]});
        let mut routed = fresh_context;
        routed["request"] = route;
        let recalled = crate::native_public::start(routed.clone()).unwrap();
        assert!(
            recalled["memory"]["advisory_context"][0]["body"]
                .as_str()
                .unwrap()
                .contains("check current service status")
        );
        assert!(
            recalled["memory"]["advisory_context"][0]["body"]
                .as_str()
                .unwrap()
                .contains("caller-asserted")
        );
        // Live state changes don't make the earlier running observation current.
        std::fs::write(target.join("service-status.txt"), "stopped").unwrap();
        assert_eq!(
            crate::native_public::start(routed.clone()).unwrap()["memory"]["advisory_context"],
            recalled["memory"]["advisory_context"]
        );
        let unrelated=crate::native_public::start(json!({"target":target,"task":"Inspect unrelated documentation","changed":["docs/other.md"]})).unwrap();
        assert!(
            unrelated["memory"]["selected_notes"]
                .as_array()
                .unwrap()
                .is_empty()
        );
        assert!(unrelated["memory"].get("advisory_context").is_none());
        std::fs::write(
            target.join("service-policy.md"),
            "Policy changed; original advice requires review.",
        )
        .unwrap();
        let drift = crate::native_public::start(routed).unwrap();
        assert!(
            drift["memory"]["selected_notes"]
                .as_array()
                .unwrap()
                .is_empty()
        );
        assert!(
            drift["memory"]["diagnostics"]
                .to_string()
                .contains("dependency changed")
        );
        std::fs::remove_dir_all(target).unwrap();
    }
    #[test]
    fn bounded_answer_publication_recovers_each_interruption() {
        for (stage, agent, advisory) in ["prepared", "source-published", "manifest-published"]
            .into_iter()
            .flat_map(|stage| {
                [false, true]
                    .into_iter()
                    .flat_map(move |agent| [false, true].map(|advisory| (stage, agent, advisory)))
            })
        {
            let target = std::env::temp_dir().join(format!(
                "aw-decision-{}-{}",
                std::process::id(),
                std::time::SystemTime::now()
                    .duration_since(std::time::UNIX_EPOCH)
                    .unwrap()
                    .as_nanos()
            ));
            std::fs::create_dir_all(&target).unwrap();
            let target = std::fs::canonicalize(target).unwrap();
            let input = json!({"target":target,"task":"Exact fixture human decision","changed":if advisory && !agent {json!([])} else {json!(["src/a.rs"])}});
            let start = |request: Option<Value>| {
                let mut v = input.clone();
                v["request"] = request.unwrap_or(Value::Null);
                crate::native_public::start(v).unwrap()
            };
            let section = if advisory {
                "advisory_capture"
            } else {
                "capture"
            };
            let mut request = start(None)["memory"][section]["requests"][0].clone();
            request["arguments"]["material"] = json!({"id":"fixture:recovery","decision":"A deliberate fixture decision","consequence":"Preserve the fixture boundary","rationale":"Test interruption only; no actual repository decision.","alternatives":[],"dependency_paths":[],"supersedes":[]});
            if advisory {
                request["arguments"]["material"] = json!({"id":"fixture:advisory-recovery","lesson":"Retain a bounded fixture observation","rationale":"Recovery fixture, no governing authority","dependency_paths":[]});
                if !agent {
                    request["arguments"]["material"]["semantic_routes"] = json!(["fixture/checks"]);
                    request["arguments"]["material"]["routes_from"] = json!(["tests/fixture.rs"]);
                }
            }
            let proposed = start(Some(request.clone()));
            let policy = target.join(".agentic-workspace/config.toml");
            let policy_bytes = "[assurance]\ndecision_delegations=[{owner=\"memory\",scope=[\"path:src/a.rs\"]}]\n";
            let answer = if agent {
                std::fs::create_dir_all(policy.parent().unwrap()).unwrap();
                std::fs::write(&policy, policy_bytes).unwrap();
                let mut current = start(None)["memory"][section]["requests"][0].clone();
                current["arguments"] = request["arguments"].clone();
                current
            } else {
                let mut current =
                    proposed["decision_packet"]["decision_request"]["response_request"].clone();
                current["arguments"]["answer"] = json!(if advisory {
                    "confirm-retention"
                } else {
                    "confirm-decision"
                });
                current
            };
            let ready = start(Some(answer.clone()));
            let action = &ready["decision_packet"]["primary_action"];
            let revalidate = || {
                let current = start(Some(answer.clone()));
                crate::admit_invocation_value(
                    json!({"decision":current["decision_packet"],"invocation":action}),
                )?;
                Ok(())
            };
            let interrupted = execute_checked(
                &target,
                &ready["decision_packet"],
                action,
                &mut { revalidate },
                &mut |point| {
                    if point == stage {
                        Err(err("fixture interruption"))
                    } else {
                        Ok(())
                    }
                },
            );
            assert!(
                interrupted
                    .unwrap_err()
                    .to_string()
                    .contains("fixture interruption")
            );
            let fresh = start(None);
            assert!(
                fresh["decision_packet"]["decision_context"]["states"]
                    .as_array()
                    .is_none_or(Vec::is_empty)
            );
            let next = if stage == "prepared" {
                action.clone()
            } else {
                fresh["decision_packet"]["primary_action"].clone()
            };
            assert!(next.is_object(), "{fresh}");
            let mut invoke = input.clone();
            invoke["invocation"] = next;
            if agent {
                std::fs::write(&policy, "").unwrap();
                assert!(crate::native_public::invoke_checked(invoke.clone()).is_err());
                std::fs::write(&policy, policy_bytes).unwrap();
            }
            crate::native_public::invoke_checked(invoke).unwrap();
            assert_eq!(
                if advisory {
                    if !agent {
                        crate::native_public::start(json!({"target":target,"task":"Fresh relevant fixture consumer","changed":["tests/fixture.rs"]})).unwrap()["memory"]["selected_notes"].clone()
                    } else { start(None)["memory"]["selected_notes"].clone() }
                } else {
                    start(None)["decision_packet"]["decision_context"]["states"].clone()
                }
                .as_array()
                .unwrap()
                .len(),
                1
            );
            // Only this test-created directory is removed.
            std::fs::remove_dir_all(target).unwrap();
        }
    }
}
