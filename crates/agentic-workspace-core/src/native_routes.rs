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

fn discover(
    root: &Dir,
    directory: &str,
    paths: &mut BTreeSet<String>,
    depth: usize,
    remaining: &mut usize,
) -> Result<(), CoreError> {
    if depth > 64 {
        return Err(error(
            "route registry discovery exceeds 64 directory levels",
        ));
    }
    let metadata = match root.symlink_metadata(directory) {
        Ok(metadata) => metadata,
        Err(error) if error.kind() == ErrorKind::NotFound => return Ok(()),
        Err(failure) => {
            return Err(error(format!(
                "route registry directory {directory}: {failure}"
            )));
        }
    };
    if linked(&metadata) {
        return Err(error(format!(
            "route registry discovery refuses symlink directory {directory}"
        )));
    }
    if !metadata.is_dir() {
        return Err(error(format!(
            "route registry directory is not a directory: {directory}"
        )));
    }
    for entry in root.read_dir(directory).map_err(error)? {
        *remaining = remaining
            .checked_sub(1)
            .ok_or_else(|| error("route registry discovery exceeds its bounded entry budget"))?;
        let entry = entry.map_err(error)?;
        let name = entry
            .file_name()
            .into_string()
            .map_err(|_| error("route registry path must be UTF-8"))?;
        let path = format!("{directory}/{name}");
        let metadata = root.symlink_metadata(&path).map_err(error)?;
        if linked(&metadata) {
            return Err(error(format!(
                "route registry discovery refuses symlink {path}"
            )));
        }
        if metadata.is_dir() {
            discover(root, &path, paths, depth + 1, remaining)?;
        } else if name == "REGISTRY.json" && directory.ends_with("/skills") {
            if !metadata.is_file() {
                return Err(error(format!(
                    "route registry is not a regular file: {path}"
                )));
            }
            paths.insert(path);
        }
    }
    Ok(())
}

/// Match semantic_route_catalogue's current tools and workspace registry owners.
/// Invalid declarations never degrade into an apparently empty current source.
fn catalogue(target: &Path, exact_detail: Option<&str>) -> Result<Value, CoreError> {
    let root = Dir::open_ambient_dir(target, ambient_authority()).map_err(error)?;
    let mut paths = BTreeSet::new();
    // Check each parent without following links before admitting the direct source.
    let direct = "tools/skills/REGISTRY.json";
    for component in ["tools", "tools/skills", direct] {
        match root.symlink_metadata(component) {
            Ok(metadata) if linked(&metadata) => {
                return Err(error(format!(
                    "route registry source refuses symlink {component}"
                )));
            }
            Ok(metadata) if component == direct => {
                if !metadata.is_file() {
                    return Err(error("route registry is not a regular file"));
                }
                paths.insert(direct.to_owned());
            }
            Ok(_) => {}
            Err(error) if error.kind() == ErrorKind::NotFound => break,
            Err(failure) => {
                return Err(error(format!(
                    "route registry source {component}: {failure}"
                )));
            }
        }
    }
    discover(&root, ".agentic-workspace", &mut paths, 0, &mut 16_384)?;
    let mut declarations = BTreeMap::<String, Value>::new();
    let mut material = Vec::new();
    for path in paths {
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
        let skills = match object.get("skills") {
            None => &[][..],
            Some(value) => value
                .as_array()
                .ok_or_else(|| error(format!("invalid skills list in route registry {path}")))?
                .as_slice(),
        };
        material.push(format!("{path}\0{}", hash(text.as_bytes())));
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
                entry["sources"]
                    .as_array_mut()
                    .unwrap()
                    .push(json!({"source_ref":path,"skill_id":skill_id}));
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
        json!({"revision":hash(material.join("\n").as_bytes()), "routes":declarations.into_values().collect::<Vec<_>>()}),
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
        "source_revision":catalogue["revision"],"route_count":rows.len(),"routes":rows,"full_catalogue_emitted":!exact.is_empty(),"diagnostics":[],"authority_effect":"applicability-only"}),
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
    fn no_signal_and_lost_source_have_distinct_current_revisions() {
        let target = Target::new();
        let empty = source(&target.0).unwrap();
        assert_eq!(empty["routes"], json!([]));
        target.write(
            ".agentic-workspace/module/skills/REGISTRY.json",
            r#"{"skills":[{"id":"example","semantic_routes":["design/public"]}]}"#,
        );
        let present = source(&target.0).unwrap();
        assert_eq!(present["routes"], json!(["design/public"]));
        assert_ne!(empty["revision"], present["revision"]);
        fs::remove_file(
            target
                .0
                .join(".agentic-workspace/module/skills/REGISTRY.json"),
        )
        .unwrap();
        assert_eq!(source(&target.0).unwrap(), empty);
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

    #[cfg(unix)]
    #[test]
    fn registry_discovery_does_not_follow_symlinks() {
        let target = Target::new();
        let outside = Target::new();
        outside.write(
            "skills/REGISTRY.json",
            r#"{"skills":[{"semantic_routes":["design/external"]}]}"#,
        );
        fs::create_dir(target.0.join(".agentic-workspace")).unwrap();
        std::os::unix::fs::symlink(&outside.0, target.0.join(".agentic-workspace/linked")).unwrap();
        assert!(source(&target.0).is_err());
    }
    #[test]
    fn registry_discovery_budgets_fail_instead_of_returning_partial_vocabulary() {
        let target = Target::new();
        target.write(
            ".agentic-workspace/skills/REGISTRY.json",
            r#"{"skills":[]}"#,
        );
        let root = Dir::open_ambient_dir(&target.0, ambient_authority()).unwrap();
        assert!(discover(&root, ".agentic-workspace", &mut BTreeSet::new(), 0, &mut 0).is_err());
        assert!(
            discover(
                &root,
                ".agentic-workspace",
                &mut BTreeSet::new(),
                65,
                &mut 16_384
            )
            .is_err()
        );
    }

    #[cfg(windows)]
    #[test]
    fn registry_discovery_refuses_windows_junctions() {
        let target = Target::new();
        let outside = Target::new();
        outside.write(
            "skills/REGISTRY.json",
            r#"{"skills":[{"semantic_routes":["design/external"]}]}"#,
        );
        fs::create_dir(target.0.join(".agentic-workspace")).unwrap();
        let link = target.0.join(".agentic-workspace/linked");
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
        let rejected = source(&target.0);
        fs::remove_dir(link).unwrap();
        assert!(rejected.is_err());
    }
}
