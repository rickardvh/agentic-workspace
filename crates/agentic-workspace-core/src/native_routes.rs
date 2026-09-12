//! Native source admission for the existing canonical skill route declarations.
//! This loads vocabulary only. The acting agent still selects applicability.
use crate::{
    CoreError,
    decision_source::{hash, read},
    route_ids,
};
use cap_std::{ambient_authority, fs::Dir};
use serde_json::{Value, json};
use std::{
    collections::{BTreeMap, BTreeSet},
    io::ErrorKind,
    path::Path,
};

fn error(message: impl ToString) -> CoreError {
    CoreError::new(message.to_string())
}

fn linked(metadata: &cap_std::fs::Metadata) -> bool {
    metadata.file_type().is_symlink() || {
        #[cfg(windows)]
        {
            use cap_std::fs::MetadataExt;
            metadata.file_attributes() & 0x400 != 0
        }
        #[cfg(not(windows))]
        {
            false
        }
    }
}

fn admit_registry(
    root: &Dir,
    components: &[&str],
    paths: &mut BTreeSet<String>,
) -> Result<(), CoreError> {
    let direct = *components.last().expect("registry source has a path");
    for component in components {
        match root.symlink_metadata(component) {
            Ok(metadata) if linked(&metadata) => {
                return Err(error(format!(
                    "route registry source refuses symlink {component}"
                )));
            }
            Ok(metadata) if *component == direct => {
                if !metadata.is_file() {
                    return Err(error(format!(
                        "route registry is not a regular file: {direct}"
                    )));
                }
                paths.insert(direct.to_owned());
            }
            Ok(metadata) if !metadata.is_dir() => {
                return Err(error(format!(
                    "route registry source parent is not a directory: {component}"
                )));
            }
            Ok(_) => {}
            Err(failure) if failure.kind() == ErrorKind::NotFound => return Ok(()),
            Err(failure) => {
                return Err(error(format!(
                    "route registry source {component}: {failure}"
                )));
            }
        }
    }
    Ok(())
}

fn admit_required_registry(root: &Dir, path: &str) -> Result<(), CoreError> {
    crate::decision_source::relative(path)?;
    let parts: Vec<_> = path.split('/').collect();
    if parts.len() > 64 {
        return Err(error("route registry source exceeds 64 path levels"));
    }
    let parents: Vec<_> = (1..=parts.len()).map(|n| parts[..n].join("/")).collect();
    let components: Vec<_> = parents.iter().map(String::as_str).collect();
    let mut admitted = BTreeSet::new();
    admit_registry(root, &components, &mut admitted)?;
    if !admitted.contains(path) {
        return Err(error(format!(
            "required route registry unavailable: {path}"
        )));
    }
    Ok(())
}

/// Match semantic_route_catalogue's current explicitly owned registry sources.
/// Invalid declarations never degrade into an apparently empty current source.
fn catalogue(target: &Path, exact_detail: Option<&str>) -> Result<Value, CoreError> {
    let root = Dir::open_ambient_dir(target, ambient_authority()).map_err(error)?;
    let mut paths = BTreeSet::new();
    // These are source-owned registry roots. Unrelated files elsewhere in the
    // workspace never become routing sources merely by being named REGISTRY.json.
    admit_registry(
        &root,
        &["tools", "tools/skills", "tools/skills/REGISTRY.json"],
        &mut paths,
    )?;
    admit_registry(
        &root,
        &[
            ".agentic-workspace",
            ".agentic-workspace/skills",
            ".agentic-workspace/skills/REGISTRY.json",
        ],
        &mut paths,
    )?;
    let mut declarations = BTreeMap::<String, Value>::new();
    let mut material = BTreeMap::new();
    let mut pending = paths.clone();
    while let Some(path) = pending.pop_first() {
        if material.contains_key(&path) {
            continue;
        }
        let bytes = read(&root, &path)
            .map_err(|failure| error(format!("route registry {path}: {failure}")))?;
        let text = std::str::from_utf8(&bytes)
            .map_err(error)?
            .replace("\r\n", "\n")
            .replace('\r', "\n");
        let payload: Value = serde_json::from_str(&text)
            .map_err(|failure| error(format!("invalid route registry {path}: {failure}")))?;
        let object = payload
            .as_object()
            .ok_or_else(|| error(format!("invalid route registry object: {path}")))?;
        if let Some(version) = object.get("schema_version")
            && version != "skill-registry.v1"
        {
            return Err(error(format!("incompatible route registry: {path}")));
        }
        // Extension membership is declared by an already admitted source, never
        // inferred from a module name or physical directory containment.
        if let Some(sources) = object.get("registry_sources") {
            let sources = sources
                .as_array()
                .ok_or_else(|| error(format!("invalid registry_sources in {path}")))?;
            for source in sources {
                let source = source
                    .as_str()
                    .ok_or_else(|| error(format!("invalid registry source in {path}")))?;
                admit_required_registry(&root, source)?;
                if paths.insert(source.to_owned()) {
                    if paths.len() > 256 {
                        return Err(error("route registry source set exceeds 256 sources"));
                    }
                    pending.insert(source.to_owned());
                }
            }
        }
        let skills = match object.get("skills") {
            None => &[][..],
            Some(value) => value
                .as_array()
                .ok_or_else(|| error(format!("invalid skills list in route registry {path}")))?
                .as_slice(),
        };
        material.insert(path.clone(), format!("{path}\0{}", hash(text.as_bytes())));
        for skill in skills {
            let skill = skill
                .as_object()
                .ok_or_else(|| error(format!("invalid skill in route registry {path}")))?;
            let routes = match skill.get("semantic_routes") {
                None => continue,
                Some(value) => value
                    .as_array()
                    .ok_or_else(|| error(format!("invalid semantic_routes list in {path}")))?,
            };
            for route in routes {
                let (id, match_kind) = if let Some(id) = route.as_str() {
                    (id.trim(), "exact")
                } else {
                    let route = route
                        .as_object()
                        .ok_or_else(|| error(format!("invalid semantic route in {path}")))?;
                    let id = route
                        .get("id")
                        .and_then(Value::as_str)
                        .ok_or_else(|| error(format!("semantic route id missing in {path}")))?
                        .trim();
                    let match_kind = match route.get("match") {
                        None | Some(Value::Null) => "exact",
                        Some(value) => value
                            .as_str()
                            .ok_or_else(|| error(format!("invalid route match in {path}")))?
                            .trim(),
                    };
                    let match_kind = if match_kind.is_empty() {
                        "exact"
                    } else {
                        match_kind
                    };
                    (id, match_kind)
                };
                route_ids(vec![id.to_owned()], "skill semantic_routes")?;
                if !matches!(match_kind, "exact" | "subtree") {
                    return Err(error(format!(
                        "invalid route match in {path}: {match_kind}"
                    )));
                }
                let entry = declarations
                    .entry(id.to_owned())
                    .or_insert_with(|| json!({"id":id,"match":match_kind}));
                if entry["match"] != match_kind {
                    return Err(error(format!(
                        "conflicting exact/subtree route declaration: {id}"
                    )));
                }
                if exact_detail != Some(id) {
                    continue;
                }
                if entry.get("capability_bindings").is_none() {
                    entry["description"] = json!(
                        route
                            .get("description")
                            .and_then(Value::as_str)
                            .or_else(|| skill.get("summary").and_then(Value::as_str))
                            .unwrap_or("")
                    );
                    entry["capability_bindings"] = json!([]);
                    entry["sources"] = json!([]);
                }
                let skill_id = skill.get("id").and_then(Value::as_str).unwrap_or("");
                let capability = format!("skill:{skill_id}");
                if !entry["capability_bindings"]
                    .as_array()
                    .unwrap()
                    .iter()
                    .any(|binding| binding["capability"] == capability)
                {
                    entry["capability_bindings"].as_array_mut().unwrap().push(json!({"capability":capability,"priority":route.get("priority").and_then(Value::as_u64).unwrap_or(100)}));
                }
                let mut source = json!({"source_ref":path,"skill_id":skill_id});
                if let Some(procedure) = skill.get("path").and_then(Value::as_str) {
                    crate::decision_source::relative(procedure)?;
                    let reference = match path.rsplit_once('/') {
                        Some((parent, _)) => format!("{parent}/{procedure}"),
                        None => procedure.to_owned(),
                    };
                    source["procedure"] = match crate::native_planning::read(&root, &reference) {
                        Ok(Some(bytes)) => {
                            json!({"reference":reference,"revision":hash(&bytes),"status":"available"})
                        }
                        Ok(None) => {
                            json!({"reference":reference,"status":"unavailable","reason":"declared-procedure-missing"})
                        }
                        Err(problem) => {
                            json!({"reference":reference,"status":"unavailable","reason":problem.to_string()})
                        }
                    };
                } else {
                    source["procedure"] =
                        json!({"status":"unavailable","reason":"procedure-path-undeclared"});
                }
                entry["sources"].as_array_mut().unwrap().push(source);
            }
        }
    }
    for declaration in declarations.values_mut() {
        if declaration.get("capability_bindings").is_none() {
            continue;
        }
        let bindings = declaration["capability_bindings"].as_array_mut().unwrap();
        bindings.sort_by(|left, right| {
            left["priority"]
                .as_u64()
                .cmp(&right["priority"].as_u64())
                .then_with(|| {
                    left["capability"]
                        .as_str()
                        .cmp(&right["capability"].as_str())
                })
        });
        declaration["capabilities"] = json!(
            bindings
                .iter()
                .map(|binding| binding["capability"].clone())
                .collect::<Vec<_>>()
        );
    }
    Ok(
        json!({"revision":hash(material.values().cloned().collect::<Vec<_>>().join("\n").as_bytes()), "sources":paths, "routes":declarations.into_values().collect::<Vec<_>>()}),
    )
}

pub(crate) fn source(target: &Path) -> Result<Value, CoreError> {
    let catalogue = catalogue(target, None)?;
    Ok(
        json!({"revision":catalogue["revision"],"routes":catalogue["routes"].as_array().unwrap().iter().map(|route|route["id"].clone()).collect::<Vec<_>>()}),
    )
}

/// Public source-owning discovery. No caller-supplied source facts or custody.
pub fn discovery(value: Value) -> Result<Value, CoreError> {
    #[derive(serde::Deserialize)]
    #[serde(deny_unknown_fields)]
    struct Input {
        target: String,
        #[serde(default)]
        parent: String,
        #[serde(default)]
        exact: String,
    }
    let input: Input = serde_json::from_value(value).map_err(error)?;
    let parent = input.parent.trim_matches('/');
    let exact = input.exact.trim_matches('/');
    let catalogue = catalogue(
        Path::new(&input.target),
        if exact.is_empty() { None } else { Some(exact) },
    )?;
    let (level, rows) = if !exact.is_empty() {
        (
            "exact",
            catalogue["routes"]
                .as_array()
                .unwrap()
                .iter()
                .filter(|route| route["id"] == exact)
                .cloned()
                .collect::<Vec<_>>(),
        )
    } else {
        let prefix = if parent.is_empty() {
            String::new()
        } else {
            format!("{parent}/")
        };
        let mut children = BTreeMap::<String, Value>::new();
        for route in catalogue["routes"].as_array().unwrap() {
            let id = route["id"].as_str().unwrap();
            if let Some(suffix) = id.strip_prefix(&prefix) {
                if suffix.is_empty() {
                    continue;
                }
                let child = format!("{}{}", prefix, suffix.split('/').next().unwrap());
                let entry = children
                    .entry(child.clone())
                    .or_insert_with(|| json!({"id":child,"leaf":false,"child_count":0}));
                if id == child {
                    entry["leaf"] = json!(true);
                } else {
                    entry["child_count"] = json!(entry["child_count"].as_u64().unwrap() + 1);
                }
            }
        }
        (
            if parent.is_empty() { "roots" } else { "branch" },
            children.into_values().collect(),
        )
    };
    Ok(
        json!({"kind":"agentic-workspace/semantic-task-route-discovery/v1","operation_id":"instructions.routes","status":"current","level":level,"parent":parent,"exact":exact,
        "source_revision":catalogue["revision"],"sources":catalogue["sources"],"route_count":rows.len(),"routes":rows,"full_catalogue_emitted":!exact.is_empty(),"diagnostics":[],"authority_effect":"applicability-only"}),
    )
}

/// Read the recognized former applicability fact without transferring its old
/// work identity to the current native task or acquiring custody of its bytes.
pub(crate) fn former_selection(
    target: &Path,
    catalogue: &Value,
) -> Result<(Value, Option<Value>), CoreError> {
    const REFERENCE: &str = ".agentic-workspace/local/current-task-routes.json";
    let root = Dir::open_ambient_dir(target, ambient_authority()).map_err(error)?;
    let mut source = catalogue.clone();
    let mut diagnostic = json!({"reference":REFERENCE,"status":"unresolved",
        "current_task_relation":"unproven","authority_effect":"none","bytes_preserved":true});
    for path in [".agentic-workspace", ".agentic-workspace/local", REFERENCE] {
        match root.symlink_metadata(path) {
            Err(failure) if failure.kind() == ErrorKind::NotFound => return Ok((source, None)),
            Ok(metadata) if !linked(&metadata) && (path != REFERENCE || metadata.is_file()) => {}
            _ => {
                diagnostic["reason"] = json!("former-route-source-unreadable-or-linked");
                source["revision"] =
                    json!(crate::digest(&json!({"catalogue":catalogue["revision"],
                    "former_selection":diagnostic["reason"]}))?);
                return Ok((source, Some(diagnostic)));
            }
        }
    }
    let bytes = match read(&root, REFERENCE) {
        Ok(bytes) => bytes,
        Err(_) => {
            diagnostic["reason"] = json!("former-route-source-unreadable-or-over-limit");
            source["revision"] = json!(crate::digest(&json!({"catalogue":catalogue["revision"],
                "former_selection":diagnostic["reason"]}))?);
            return Ok((source, Some(diagnostic)));
        }
    };
    let revision = hash(&bytes);
    diagnostic["revision"] = json!(revision);
    // The returned ordinary request binds both vocabulary and the exact former
    // candidate. Neither its old ID nor its filename proves current task scope.
    source["revision"] = json!(crate::digest(&json!({"catalogue":catalogue["revision"],
        "former_selection":revision}))?);
    let fact: Value = match serde_json::from_slice(&bytes) {
        Ok(Value::Object(object)) => Value::Object(object),
        _ => {
            diagnostic["reason"] = json!("former-route-source-invalid");
            return Ok((source, Some(diagnostic)));
        }
    };
    let allowed = [
        "kind",
        "posture",
        "routes",
        "task_identity",
        "current_work_id",
        "source_revision",
        "provenance",
        "authority_effect",
    ];
    let routes = fact["routes"].as_array();
    let old_work = fact["current_work_id"].as_str().unwrap_or("");
    let shape_valid = fact
        .as_object()
        .unwrap()
        .keys()
        .all(|key| allowed.contains(&key.as_str()))
        && fact["kind"] == "agentic-workspace/semantic-task-route-fact/v1"
        && fact["provenance"] == "agent-selected"
        && fact["authority_effect"] == "applicability-only"
        && !old_work.is_empty()
        && old_work.len() <= 256
        && fact["task_identity"] == json!({"kind":"current-work","id":old_work})
        && matches!(
            fact["posture"].as_str(),
            Some("selected" | "none" | "unresolved")
        )
        && routes.is_some_and(|routes| routes.iter().all(|route| route.as_str().is_some()));
    if !shape_valid {
        diagnostic["reason"] = json!("former-route-source-invalid-or-unsupported");
        return Ok((source, Some(diagnostic)));
    }
    let routes = routes.unwrap();
    if routes.len() > 16
        || routes
            .iter()
            .any(|route| route.as_str().unwrap().len() > 256)
    {
        diagnostic["reason"] = json!("former-route-selection-exceeds-candidate-bound");
        return Ok((source, Some(diagnostic)));
    }
    if fact["source_revision"] != catalogue["revision"] {
        diagnostic["status"] = json!("stale");
        diagnostic["reason"] = json!("former-route-vocabulary-revision-changed");
        return Ok((source, Some(diagnostic)));
    }
    let declaration: Value = serde_json::from_str(include_str!(
        "../../../src/agentic_workspace/contracts/schemas/source_decision_input.schema.json"
    ))
    .expect("checked schema");
    let shape = json!({"$schema":declaration["$schema"],"$defs":declaration["$defs"],"$ref":"#/$defs/semantic_route_choice"});
    let choice = json!({"posture":fact["posture"],"routes":fact["routes"]});
    if !crate::schema_validator(&shape, "former route candidate")?.is_valid(&choice)
        || routes
            .iter()
            .any(|route| !catalogue["routes"].as_array().unwrap().contains(route))
    {
        diagnostic["reason"] = json!("former-route-selection-invalid");
        return Ok((source, Some(diagnostic)));
    }
    diagnostic["status"] = json!("candidate");
    diagnostic["reason"] = json!("current-vocabulary-requires-current-task-agent-selection");
    diagnostic["posture"] = fact["posture"].clone();
    diagnostic["routes"] = fact["routes"].clone();
    Ok((source, Some(diagnostic)))
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::{
        fs,
        path::PathBuf,
        time::{SystemTime, UNIX_EPOCH},
    };
    struct Target(PathBuf);
    impl Target {
        fn new() -> Self {
            let path = std::env::temp_dir().join(format!(
                "aw-native-routes-{}-{}",
                std::process::id(),
                SystemTime::now()
                    .duration_since(UNIX_EPOCH)
                    .unwrap()
                    .as_nanos()
            ));
            fs::create_dir(&path).unwrap();
            Self(path)
        }
        fn write(&self, path: &str, text: &str) {
            let path = self.0.join(path);
            fs::create_dir_all(path.parent().unwrap()).unwrap();
            fs::write(path, text).unwrap();
        }
    }
    impl Drop for Target {
        fn drop(&mut self) {
            fs::remove_dir_all(&self.0).unwrap();
        }
    }

    #[test]
    fn actual_registry_source_is_read_without_applicability_or_writes() {
        let target = Target::new();
        let text = include_str!("../../../tools/skills/REGISTRY.json");
        target.write("tools/skills/REGISTRY.json", text);
        let result = source(&target.0).unwrap();
        assert!(!result["routes"].as_array().unwrap().is_empty());
        assert_eq!(
            result["revision"],
            hash(format!("tools/skills/REGISTRY.json\0{}", hash(text.as_bytes())).as_bytes())
        );
        assert!(result.get("selection").is_none());
        assert!(!target.0.join(".agentic-workspace").exists());
    }

    #[test]
    fn only_declared_registry_roots_affect_current_revision() {
        let target = Target::new();
        let empty = source(&target.0).unwrap();
        assert_eq!(empty["routes"], json!([]));
        target.write(
            ".agentic-workspace/module/skills/REGISTRY.json",
            r#"{"skills":[{"id":"ignored","semantic_routes":["design/ignored"]}]}"#,
        );
        assert_eq!(source(&target.0).unwrap(), empty);
        target.write(
            ".agentic-workspace/skills/REGISTRY.json",
            r#"{"skills":[{"id":"example","semantic_routes":["design/public"]}]}"#,
        );
        let present = source(&target.0).unwrap();
        assert_eq!(present["routes"], json!(["design/public"]));
        assert_ne!(empty["revision"], present["revision"]);
    }

    #[test]
    fn invalid_registry_and_conflicting_declarations_fail_closed() {
        let target = Target::new();
        for text in [
            "{broken",
            r#"{"skills":false}"#,
            r#"{"skills":[{"semantic_routes":["not-a-leaf"]}]}"#,
            r#"{"skills":[{"semantic_routes":[{"id":"design/public","match":"automatic"}]}]}"#,
            r#"{"skills":[{"semantic_routes":["design/public",{"id":"design/public","match":"subtree"}]}]}"#,
        ] {
            target.write("tools/skills/REGISTRY.json", text);
            assert!(source(&target.0).is_err(), "{text}");
        }
    }

    #[test]
    fn declared_custom_sources_are_current_required_and_explainable() {
        let target = Target::new();
        let registry = "custom/owner/routes.json";
        target.write(
            "tools/skills/REGISTRY.json",
            &json!({"registry_sources":[registry]}).to_string(),
        );
        assert!(
            source(&target.0)
                .unwrap_err()
                .to_string()
                .contains("required route registry unavailable")
        );
        target.write(
            registry,
            r#"{"skills":[{"semantic_routes":["custom/first"]}]}"#,
        );
        let first = source(&target.0).unwrap();
        assert_eq!(first["routes"], json!(["custom/first"]));
        let detail = discovery(json!({"target":target.0,"exact":"custom/first"})).unwrap();
        assert_eq!(
            detail["sources"],
            json!([registry, "tools/skills/REGISTRY.json"])
        );
        target.write(
            registry,
            r#"{"skills":[{"semantic_routes":["custom/second"]}]}"#,
        );
        assert_ne!(first["revision"], source(&target.0).unwrap()["revision"]);
        fs::remove_file(target.0.join(registry)).unwrap();
        assert!(source(&target.0).is_err());
        target.write("tools/skills/REGISTRY.json", "{}");
        assert_eq!(source(&target.0).unwrap()["routes"], json!([]));
        for declaration in [
            json!(["../escape.json"]),
            json!(["/absolute.json"]),
            json!([false]),
            json!(false),
        ] {
            target.write(
                "tools/skills/REGISTRY.json",
                &json!({"registry_sources":declaration}).to_string(),
            );
            assert!(source(&target.0).is_err());
        }
    }

    #[test]
    fn declared_cycles_terminate_and_incompatible_sources_fail_closed() {
        let target = Target::new();
        target.write(
            "tools/skills/REGISTRY.json",
            r#"{"registry_sources":["custom.json"]}"#,
        );
        target.write(
            "custom.json",
            r#"{"registry_sources":["tools/skills/REGISTRY.json"],"skills":[]}"#,
        );
        assert_eq!(source(&target.0).unwrap()["routes"], json!([]));
        target.write("custom.json", r#"{"schema_version":"future-version"}"#);
        assert!(
            source(&target.0)
                .unwrap_err()
                .to_string()
                .contains("incompatible")
        );
    }

    #[test]
    fn unrelated_workspace_volume_and_links_do_not_participate_in_discovery() {
        let target = Target::new();
        target.write(
            ".agentic-workspace/skills/REGISTRY.json",
            r#"{"skills":[{"id":"example","semantic_routes":["design/public"]}]}"#,
        );
        for index in 0..16_500 {
            target.write(
                &format!(".agentic-workspace/local/scratch/{index}.json"),
                "{}",
            );
        }
        target.write(
            ".agentic-workspace/local/scratch/nested/REGISTRY.json",
            r#"{"skills":[{"semantic_routes":["design/foreign"]}]}"#,
        );
        target.write(
            ".agentic-workspace/local/instructions/nested/skills/REGISTRY.json",
            "invalid unrelated registry",
        );
        let result = source(&target.0).unwrap();
        assert_eq!(result["routes"], json!(["design/public"]));
    }

    #[cfg(unix)]
    #[test]
    fn unrelated_symlink_is_not_a_registry_source() {
        let target = Target::new();
        let outside = Target::new();
        outside.write(
            "skills/REGISTRY.json",
            r#"{"skills":[{"semantic_routes":["design/external"]}]}"#,
        );
        fs::create_dir_all(target.0.join(".agentic-workspace/local")).unwrap();
        std::os::unix::fs::symlink(&outside.0, target.0.join(".agentic-workspace/local/linked"))
            .unwrap();
        assert_eq!(source(&target.0).unwrap()["routes"], json!([]));
    }

    #[cfg(windows)]
    #[test]
    fn unrelated_windows_junction_is_not_a_registry_source() {
        let target = Target::new();
        let outside = Target::new();
        outside.write(
            "skills/REGISTRY.json",
            r#"{"skills":[{"semantic_routes":["design/external"]}]}"#,
        );
        fs::create_dir_all(target.0.join(".agentic-workspace/local")).unwrap();
        let link = target.0.join(".agentic-workspace/local/linked");
        let result = std::process::Command::new("cmd")
            .args(["/c", "mklink", "/J"])
            .arg(link.to_string_lossy().replace('/', "\\"))
            .arg(outside.0.to_string_lossy().replace('/', "\\"))
            .output()
            .unwrap();
        assert!(
            result.status.success(),
            "{}",
            String::from_utf8_lossy(&result.stderr)
        );
        assert_eq!(source(&target.0).unwrap()["routes"], json!([]));
        fs::remove_dir(link).unwrap();
    }
}
