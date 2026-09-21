//! Exact, passive evaluation of an existing aid bundle; never a discovery registry.
use crate::{CoreError, decision_source::hash};
use cap_std::{ambient_authority, fs::Dir};
use serde_json::{Value, json};
use std::{collections::BTreeMap, path::Path};

pub(crate) const PREFIX: &str = "candidate-skills/";

fn error(message: impl ToString) -> CoreError {
    CoreError::new(message.to_string())
}

fn name(value: &str) -> bool {
    !value.is_empty()
        && value.len() <= 64
        && !value.starts_with('-')
        && !value.ends_with('-')
        && !value.contains("--")
        && value
            .bytes()
            .all(|c| c.is_ascii_lowercase() || c.is_ascii_digit() || c == b'-')
}

fn bundle(
    root: &Dir,
    path: &str,
    material: &mut BTreeMap<String, String>,
    size: &mut usize,
    entries: &mut usize,
    depth: usize,
) -> Result<(), CoreError> {
    if depth > 8 {
        return Err(error("candidate bundle exceeds eight directory levels"));
    }
    for entry in root.read_dir(path).map_err(error)? {
        *entries += 1;
        if *entries > 256 {
            return Err(error("candidate bundle exceeds 256 directory entries"));
        }
        let entry = entry.map_err(error)?;
        let child = format!(
            "{path}/{}",
            entry
                .file_name()
                .to_str()
                .ok_or_else(|| error("candidate path is not UTF-8"))?
        );
        let metadata = root.symlink_metadata(&child).map_err(error)?;
        if super::native_routes::linked(&metadata) {
            return Err(error("candidate bundle refuses links"));
        }
        if metadata.is_dir() {
            bundle(root, &child, material, size, entries, depth + 1)?;
        } else if metadata.is_file() {
            if material.len() >= 128 {
                return Err(error("candidate bundle exceeds 128 files"));
            }
            let bytes = crate::native_planning::read(root, &child)?
                .ok_or_else(|| error("candidate material disappeared"))?;
            *size += bytes.len();
            if *size > 4 * 1024 * 1024 {
                return Err(error("candidate bundle exceeds 4 MiB"));
            }
            material.insert(child, hash(&bytes));
        } else {
            return Err(error("candidate material is not a regular file"));
        }
    }
    Ok(())
}

pub(crate) fn detail(
    target: &Path,
    route: &str,
    selected: Option<&Value>,
) -> Result<Value, CoreError> {
    let id = route
        .strip_prefix(PREFIX)
        .filter(|id| name(id))
        .ok_or_else(|| error("candidate selection requires one standard skill name"))?;
    let base = format!(".agentic-workspace/agent-aids/skills/{id}");
    let manifest = format!("{base}/manifest.json");
    let skill = format!("{base}/SKILL.md");
    let root = Dir::open_ambient_dir(target, ambient_authority()).map_err(error)?;
    let resolve = || -> Result<Value, CoreError> {
        // The existing confined reader rejects linked parents as well as files.
        let raw = crate::native_planning::read(&root, &manifest)?
            .ok_or_else(|| error("candidate manifest missing"))?;
        let aid: Value = serde_json::from_slice(&raw).map_err(error)?;
        let schema: Value = serde_json::from_str(include_str!(
            "../../../src/agentic_workspace/contracts/schemas/agent_aid_manifest.schema.json"
        ))
        .unwrap();
        crate::schema_validator(&schema, "candidate skill")?
            .validate(&aid)
            .map_err(error)?;
        if aid["id"] != id
            || aid["type"] != "skill"
            || aid["entrypoint"] != skill
            || !matches!(aid["status"].as_str(), Some("candidate" | "shared"))
            || aid["proof_role"] == "canonical-proof"
        {
            return Err(error(
                "candidate skill identity, entrypoint or lifecycle is unavailable for evaluation",
            ));
        }
        let bytes = crate::native_planning::read(&root, &skill)?
            .ok_or_else(|| error("candidate SKILL.md missing"))?;
        if bytes.len() > 65536 {
            return Err(error("candidate SKILL.md exceeds 64 KiB"));
        }
        let text = std::str::from_utf8(&bytes)
            .map_err(error)?
            .replace("\r\n", "\n");
        let front = text
            .strip_prefix("---\n")
            .and_then(|s| s.split_once("\n---"))
            .ok_or_else(|| error("candidate requires standard YAML frontmatter"))?;
        if !front.1.starts_with('\n') && !front.1.is_empty() {
            return Err(error(
                "candidate frontmatter terminator must occupy its own line",
            ));
        }
        // Preserve YAML key types: JSON conversion can coerce numeric map keys.
        let metadata: serde_yaml_ng::Value = serde_yaml_ng::from_str(front.0).map_err(error)?;
        if metadata["name"].as_str() != Some(id)
            || !metadata["description"]
                .as_str()
                .is_some_and(|s| !s.trim().is_empty() && s.chars().count() <= 1024)
        {
            return Err(error(
                "candidate requires matching standard name and nonempty description (at most 1024 characters)",
            ));
        }
        for field in ["license", "allowed-tools"] {
            if metadata.get(field).is_some_and(|v| !v.is_string()) {
                return Err(error(format!("candidate {field} must be a string")));
            }
        }
        if metadata.get("compatibility").is_some_and(|v| {
            !v.as_str()
                .is_some_and(|s| (1..=500).contains(&s.chars().count()))
        }) {
            return Err(error(
                "candidate compatibility must be a string of 1-500 characters",
            ));
        }
        if metadata.get("metadata").is_some_and(|v| {
            !v.as_mapping()
                .is_some_and(|m| m.iter().all(|(k, v)| k.is_string() && v.is_string()))
        }) {
            return Err(error(
                "candidate metadata must map string keys to string values",
            ));
        }
        let mut material = BTreeMap::new();
        bundle(&root, &base, &mut material, &mut 0, &mut 0, 0)?;
        let mut source = json!({"source_ref":manifest,"skill_id":id,"procedure":{
            "reference":skill,"revision":crate::digest(&material)?,"status":"available",
            "material":material,"authority_effect":"none"}});
        if let Some(resource) = aid.get("procedure_resource") {
            let selection = selected
                .filter(|s| s["source_ref"] == manifest && s["skill_id"] == id)
                .and_then(|s| s["resource"].as_str());
            source["procedure"]["resource"] =
                crate::native_procedure::detail(&root, &source, resource, selection);
        }
        Ok(source)
    };
    let source = resolve().unwrap_or_else(|e| {
        json!({"source_ref":manifest,"skill_id":id,"procedure":{
        "reference":skill,"status":"unavailable","reason":e.to_string(),"authority_effect":"none"}})
    });
    Ok(
        json!({"id":route,"match":"exact","description":"Explicit candidate skill evaluation; no promotion or effect authority.",
        "sources":[source],"capabilities":[format!("skill:{id}")],"capability_bindings":[{"capability":format!("skill:{id}"),"priority":100}]}),
    )
}
