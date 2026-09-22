//! Pre-state reader compatibility: observations are host facts, not public grants.
use crate::CoreError;
use serde_json::{Value, json};
use sha2::{Digest, Sha256};
use std::path::Path;

const CONTRACT: &str = include_str!("../contracts/schemas/runtime_compatibility.schema.json");

// Preserve the established Python sorted, ensure_ascii JSON identity, including
// default separator spaces. Identity material contains no floating point values.
fn trim(value: &str) -> &str {
    value.trim_matches(|c: char| c.is_whitespace() || ('\u{1c}'..='\u{1f}').contains(&c))
}

fn identity(value: &Value) -> Result<String, CoreError> {
    let compact = crate::proof_subject::compact_json(value)?;
    let (mut quoted, mut escaped) = (false, false);
    let mut encoded = String::new();
    for c in compact.chars() {
        encoded.push(c);
        if escaped {
            escaped = false;
            continue;
        }
        if quoted && c == '\\' {
            escaped = true;
            continue;
        }
        if c == '"' {
            quoted = !quoted;
        }
        if !quoted && matches!(c, ',' | ':') {
            encoded.push(' ');
        }
    }
    Ok(format!("sha256:{:x}", Sha256::digest(encoded.as_bytes())))
}

pub fn view(input: Value) -> Result<Value, CoreError> {
    let schema: Value = serde_json::from_str(CONTRACT).expect("checked schema");
    crate::schema_validator(&schema, "runtime compatibility")?
        .validate(&input)
        .map_err(|e| {
            CoreError::new(format!(
                "invalid runtime observation at {}",
                e.instance_path()
            ))
        })?;
    let mut errors: Vec<Value> = input["source_errors"].as_array().unwrap().clone();
    for (key, source_schema) in [
        (
            "repo_config",
            include_str!("../contracts/schemas/workspace_config.schema.json"),
        ),
        (
            "local_config",
            include_str!("../contracts/schemas/workspace_local_override.schema.json"),
        ),
    ] {
        if let Err(error) = crate::native_config::validate_source(&input[key], source_schema) {
            errors.push(json!(format!("{key}: {error}")));
        }
    }
    let observed = &input["observed_runtime"];
    let invocation = [&input["local_config"], &input["repo_config"]]
        .iter()
        .filter_map(|c| c["workspace"]["cli_invoke"].as_str())
        .map(trim)
        .find(|s| !s.is_empty())
        .unwrap_or("agentic-workspace");
    let expected = json!({"source":"current-configuration-contract"});
    let admitted = errors.is_empty();
    let mut result = json!({"kind":if admitted {"agentic-workspace/runtime-compatibility-admission/v1"}else{"agentic-workspace/runtime-compatibility-incompatibility/v1"},
        "status":if admitted{"admitted"}else{"blocked"}, "identity_digest":identity(&json!({"expected":expected,"observed":observed,"target":input["target"]}))?,
        "target":input["target"],"observed_runtime":observed,"expected_repository":expected,"configured_invocation":invocation,
        "managed_state_interpreted":false,"rule":if admitted{"Compatibility is admitted before generated handlers, session logging, Planning, or Workspace state are loaded."}else{"An incompatible reader fails before any decision-shaped repository state is interpreted."}});
    if !admitted {
        let checks = ["configuration_source_shape"];
        result.as_object_mut().unwrap().extend(json!({"failure_class":"runtime-repository-contract-incompatible","failed_checks":checks,"contract_errors":errors,"recovery_command":invocation,
            "unavailable_effects":["owner-selection","implementation-permission","mutation-guidance","proof-and-closeout-authority","completion-claims"],"completion_boundary":"repository-managed-state-not-admitted"}).as_object().unwrap().clone());
    }
    Ok(result)
}

pub(crate) fn native(target: &Path) -> Result<Value, CoreError> {
    let root = cap_std::fs::Dir::open_ambient_dir(target, cap_std::ambient_authority())
        .map_err(|e| CoreError::new(e.to_string()))?;
    let declaration: Value = serde_json::from_str(CONTRACT).expect("checked schema");
    let mut errors = Vec::new();
    let mut read = |path: &str, schema: &str| match crate::native_config::load(&root, path, schema)
    {
        Ok(Some((value, _))) => (value, true),
        Ok(None) => (json!({}), false),
        Err(e) => {
            errors.push(format!("{path}: {e}"));
            (json!({}), true)
        }
    };
    let (repo, present) = read(
        ".agentic-workspace/config.toml",
        include_str!("../contracts/schemas/workspace_config.schema.json"),
    );
    let (local, _) = read(
        ".agentic-workspace/config.local.toml",
        include_str!("../contracts/schemas/workspace_local_override.schema.json"),
    );
    let product: toml::Value =
        toml::from_str(include_str!("../../../pyproject.toml")).expect("product manifest");
    let target_text = target.to_string_lossy();
    let target_text = if let Some(unc) = target_text.strip_prefix(r"\\?\UNC\") {
        format!(r"\\{unc}")
    } else {
        target_text
            .strip_prefix(r"\\?\")
            .unwrap_or(&target_text)
            .to_owned()
    };
    view(
        json!({"target":target_text,"config_present":present,"repo_config":repo,"local_config":local,"source_errors":errors,
        "observed_runtime":{"package":"agentic-workspace","version":product["project"]["version"].as_str().expect("product version"),"reader_epoch":declaration["x-runtime-reader"]["reader_epoch"],"reader_capabilities":declaration["x-runtime-reader"]["reader_capabilities"]}}),
    )
}

#[cfg(test)]
mod tests {
    use super::*;
    fn observation() -> Value {
        json!({"target":"repo", "config_present":true,"repo_config":{},"local_config":{},"source_errors":[],"observed_runtime":{"package":"agentic-workspace","version":"0.51.0","reader_epoch":1,"reader_capabilities":["pre-state-runtime-compatibility-v1"]}})
    }
    #[test]
    fn only_current_configuration_is_admitted_before_state() {
        let input = observation();
        assert_eq!(view(input.clone()).unwrap()["status"], "admitted");
        let mut old = input.clone();
        old["repo_config"]["cli_compatibility"] = json!({"minimum_reader_epoch":2});
        let blocked = view(old).unwrap();
        assert_eq!(blocked["status"], "blocked");
        assert_eq!(blocked["managed_state_interpreted"], false);
        let mut unknown = input;
        unknown["public_authority"] = json!(true);
        assert!(view(unknown).is_err());
    }
}
