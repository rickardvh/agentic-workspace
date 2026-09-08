//! Pre-state reader compatibility: observations are host facts, not public grants.
use crate::CoreError;
use serde_json::{Value, json};
use sha2::{Digest, Sha256};
use std::{collections::BTreeSet, path::Path};

const CONTRACT: &str = include_str!(
    "../../../src/agentic_workspace/contracts/schemas/runtime_compatibility.schema.json"
);

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
    let expectation = &input["repo_config"]["cli_compatibility"];
    let raw_epoch = &expectation["minimum_reader_epoch"];
    let epoch = raw_epoch.as_u64().filter(|v| *v > 0).unwrap_or(0);
    let mut errors: Vec<Value> = input["source_errors"].as_array().unwrap().clone();
    if input["repo_config"].get("cli_compatibility").is_some() && !expectation.is_object() {
        errors.push(json!("cli_compatibility must be a table"));
    }
    if !raw_epoch.is_null() && epoch == 0 {
        errors.push(json!("minimum_reader_epoch must be a positive integer"));
    }
    let raw_caps = &expectation["required_reader_capabilities"];
    if expectation.get("required_reader_capabilities").is_some() && !raw_caps.is_array() {
        errors.push(json!("required_reader_capabilities must be a list"));
    }
    if raw_caps.as_array().is_some_and(|values| {
        values
            .iter()
            .any(|v| v.as_str().is_none_or(|s| trim(s).is_empty()))
    }) {
        errors.push(json!(
            "required_reader_capabilities entries must be non-empty strings"
        ));
    }
    let caps: BTreeSet<_> = raw_caps
        .as_array()
        .into_iter()
        .flatten()
        .filter_map(Value::as_str)
        .map(trim)
        .filter(|s| !s.is_empty())
        .collect();
    let observed = &input["observed_runtime"];
    let missing: Vec<_> = caps
        .iter()
        .filter(|cap| {
            !observed["reader_capabilities"]
                .as_array()
                .unwrap()
                .iter()
                .any(|v| v.as_str() == Some(cap))
        })
        .collect();
    let supported = epoch <= observed["reader_epoch"].as_u64().unwrap();
    let invocation = [&input["local_config"], &input["repo_config"]]
        .iter()
        .filter_map(|c| c["workspace"]["cli_invoke"].as_str())
        .map(trim)
        .find(|s| !s.is_empty())
        .unwrap_or("agentic-workspace");
    let raw_contract = &expectation["contract_schema"];
    if expectation.get("contract_schema").is_some()
        && raw_contract.as_str().is_none_or(|s| trim(s).is_empty())
    {
        errors.push(json!("contract_schema must be a non-empty string"));
    }
    let supported_contract = schema["x-runtime-reader"]["contract_schema"]
        .as_str()
        .expect("reader contract");
    let contract = raw_contract
        .as_str()
        .filter(|s| !s.is_empty())
        .unwrap_or(supported_contract);
    let expected = json!({"contract_schema":contract,"minimum_reader_epoch":epoch,"required_reader_capabilities":caps,
        "source":if input["config_present"] == true { ".agentic-workspace/config.toml [cli_compatibility]" } else { "repository-default" }});
    let admitted =
        supported && contract == supported_contract && missing.is_empty() && errors.is_empty();
    let mut result = json!({"kind":if admitted {"agentic-workspace/runtime-compatibility-admission/v1"}else{"agentic-workspace/runtime-compatibility-incompatibility/v1"},
        "status":if admitted{"admitted"}else{"blocked"}, "identity_digest":identity(&json!({"expected":expected,"observed":observed,"target":input["target"]}))?,
        "target":input["target"],"observed_runtime":observed,"expected_repository":expected,"configured_invocation":invocation,
        "managed_state_interpreted":false,"rule":if admitted{"Compatibility is admitted before generated handlers, session logging, Planning, or Workspace state are loaded."}else{"An incompatible reader fails before any decision-shaped repository state is interpreted."}});
    if !admitted {
        let mut checks = Vec::new();
        if contract != supported_contract {
            checks.push("contract_schema");
        }
        if !supported {
            checks.push("minimum_reader_epoch");
        }
        if !missing.is_empty() {
            checks.push("required_reader_capabilities");
        }
        if !errors.is_empty() {
            checks.push("compatibility_contract_shape");
        }
        result.as_object_mut().unwrap().extend(json!({"failure_class":"runtime-repository-contract-incompatible","failed_checks":checks,"missing_reader_capabilities":missing,"contract_errors":errors,"recovery_command":invocation,
            "unavailable_effects":["owner-selection","implementation-permission","mutation-guidance","proof-and-closeout-authority","completion-claims"],"completion_boundary":"repository-managed-state-not-admitted"}).as_object().unwrap().clone());
    }
    Ok(result)
}

pub(crate) fn native(target: &Path) -> Result<Value, CoreError> {
    let root = cap_std::fs::Dir::open_ambient_dir(target, cap_std::ambient_authority())
        .map_err(|e| CoreError::new(e.to_string()))?;
    let declaration: Value = serde_json::from_str(CONTRACT).expect("checked schema");
    let mut source_schema = declaration["properties"]["repo_config"].clone();
    source_schema["$schema"] = declaration["$schema"].clone();
    let source_schema = source_schema.to_string();
    let mut errors = Vec::new();
    let mut read = |path: &str| match crate::native_config::load(&root, path, &source_schema) {
        Ok(Some((value, _))) => (value, true),
        Ok(None) => (json!({}), false),
        Err(e) => {
            errors.push(format!("{path}: {e}"));
            (json!({}), true)
        }
    };
    let (repo, present) = read(".agentic-workspace/config.toml");
    let (local, _) = read(".agentic-workspace/config.local.toml");
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
    fn compatibility_is_reader_specific_and_never_state_authority() {
        let mut input = observation();
        input["repo_config"]["cli_compatibility"] =
            json!({"minimum_reader_epoch":2,"required_reader_capabilities":["future"]});
        let blocked = view(input.clone()).unwrap();
        assert_eq!(
            blocked["failed_checks"],
            json!(["minimum_reader_epoch", "required_reader_capabilities"])
        );
        assert_eq!(blocked["managed_state_interpreted"], false);
        input["observed_runtime"]["reader_epoch"] = json!(2);
        input["observed_runtime"]["reader_capabilities"] = json!(["future"]);
        assert_eq!(view(input).unwrap()["status"], "admitted");
    }
    #[test]
    fn malformed_expectations_and_observations_do_not_grant() {
        for value in [json!(0), json!(-1), json!(true), json!(1.5), json!("2")] {
            let mut input = observation();
            input["repo_config"]["cli_compatibility"]["minimum_reader_epoch"] = value;
            assert_eq!(view(input).unwrap()["status"], "blocked");
        }
        let mut input = observation();
        input["public_authority"] = json!(true);
        assert!(view(input).is_err());
    }
}
