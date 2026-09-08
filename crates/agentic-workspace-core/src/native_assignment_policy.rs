//! Actual existing local/shared source selection, no migration store or writes.
use crate::{CoreError, digest};
use cap_std::{ambient_authority, fs::Dir};
use serde_json::{Value, json};
use std::path::Path;
const SCHEMA: &str = include_str!(
    "../../../src/agentic_workspace/contracts/schemas/workspace_local_override.schema.json"
);
pub(crate) struct Source {
    pub effective: Value,
    pub sources: Vec<Value>,
    pub revision: String,
    pub policy: Value,
}
pub(crate) fn load(target: &Path) -> Result<Source, CoreError> {
    let root = Dir::open_ambient_dir(target, ambient_authority())
        .map_err(|e| CoreError::new(e.to_string()))?;
    let current = ".agentic-workspace/config.local.toml";
    let former = "agentic-workspace.local.toml";
    let mut selected = current;
    let mut local = crate::native_config::load(&root, current, SCHEMA).map_err(CoreError::new)?;
    if local.is_none() {
        selected = former;
        local = crate::native_config::load(&root, former, SCHEMA).map_err(CoreError::new)?;
    }
    let mut sources = Vec::new();
    let mut effective = json!({});
    if let Some((value, revision)) = local {
        if let Some(reference) = value["workspace"]["shared_config_path"].as_str() {
            let path = target.join(reference);
            let parent = path
                .parent()
                .ok_or_else(|| CoreError::new("invalid shared local source path"))?;
            let dir = Dir::open_ambient_dir(parent, ambient_authority()).map_err(|e| {
                CoreError::new(format!(
                    "configured shared local source {reference} unavailable: {e}"
                ))
            })?;
            let name = path
                .file_name()
                .and_then(|s| s.to_str())
                .ok_or_else(|| CoreError::new("invalid shared local source name"))?;
            let (shared,revision)=crate::native_config::load(&dir,name,SCHEMA).map_err(CoreError::new)?.ok_or_else(||CoreError::new(format!("configured shared local source {reference} missing; preserve its unresolved intent")))?;
            effective = shared;
            sources.push(json!({"reference":reference,"revision":revision,"status":"current-shared-local-source"}));
        }
        effective = crate::assignment_policy::merge(&effective, &value);
        sources.push(
            json!({"reference":selected,"revision":revision,"status":"current-local-source"}),
        );
        if selected == current && root.symlink_metadata(former).is_ok() {
            sources.push(json!({"reference":former,"status":"superseded-by-current-local-source","rule":"existing canonical source precedence; no legacy bytes modified"}));
        }
    }
    let profiles: Vec<Value> = effective["delegation_targets"]
        .as_object()
        .into_iter()
        .flatten()
        .map(|(name, p)| {
            let mut p = p.clone();
            p["name"] = json!(name);
            p
        })
        .collect();
    let policy = crate::assignment_policy::resolve(
        &json!({"policy":effective["delegation"],"profiles":profiles,"safe_to_auto_run_commands":effective["safety"]["safe_to_auto_run_commands"]}),
    )?;
    let revision = digest(&json!({"sources":sources,"policy":policy}))?;
    Ok(Source {
        effective,
        sources,
        revision,
        policy,
    })
}
