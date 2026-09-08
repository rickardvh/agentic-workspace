//! Read canonical configuration as source-owned policy, never as mutation custody.
//! Unsupported current controls remain visible at their affected owner boundary.
use crate::{CoreError, digest};
use cap_std::{ambient_authority, fs::Dir};
use serde_json::{Value, json};
use sha2::{Digest, Sha256};
use std::{io::Read, path::Path};

const SHARED: &str = ".agentic-workspace/config.toml";
const LOCAL: &str = ".agentic-workspace/config.local.toml";

pub(crate) fn load(
    root: &Dir,
    path: &str,
    schema: &str,
) -> Result<Option<(Value, String)>, String> {
    let mut current = std::path::PathBuf::new();
    for part in path.split('/') {
        current.push(part);
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
                    return Err("configuration source cannot traverse links".into());
                }
            }
            Err(error) if error.kind() == std::io::ErrorKind::NotFound => return Ok(None),
            Err(error) => return Err(error.to_string()),
        }
    }
    let mut bytes = Vec::new();
    root.open(path)
        .map_err(|e| e.to_string())?
        .take(1_048_577)
        .read_to_end(&mut bytes)
        .map_err(|e| e.to_string())?;
    if bytes.len() > 1_048_576 {
        return Err("configuration source exceeds bounded read".into());
    }
    let revision = format!("sha256:{:x}", Sha256::digest(&bytes));
    let text = std::str::from_utf8(&bytes).map_err(|e| e.to_string())?;
    let parsed: toml::Value = toml::from_str(text.trim_start_matches('\u{feff}'))
        .map_err(|_| "invalid TOML; inspect the source locally".to_owned())?;
    let value = serde_json::to_value(parsed).map_err(|e| e.to_string())?;
    let schema: Value = serde_json::from_str(schema).map_err(|e| e.to_string())?;
    crate::schema_validator(&schema, "native configuration")
        .map_err(|e| e.to_string())?
        .validate(&value)
        .map_err(|e| format!("invalid configuration at {}", e.instance_path()))?;
    Ok(Some((value, revision)))
}

fn present(value: &Value) -> bool {
    match value {
        Value::Null => false,
        Value::Object(values) => values.values().any(present),
        Value::Array(values) => !values.is_empty(),
        _ => true,
    }
}

fn residual(source: &str, field: &str, value: &Value) -> Value {
    // These existing controls describe rendering or replaceable methods. Keep
    // their current source meaning without turning persistence into authority.
    let advisory = if field == "workspace.optimization_bias" {
        Some("advisory-rendering-preference")
    } else if field.starts_with("workflow_obligations.")
        && value["force"] == "recommended"
        && value.as_object().is_some_and(|fields| {
            fields.keys().all(|key| {
                matches!(
                    key.as_str(),
                    "summary" | "stage" | "force" | "scope_tags" | "commands" | "review_hint"
                )
            })
        })
    {
        Some("recommended-stage-method")
    } else {
        None
    };
    if let Some(disposition) = advisory {
        return json!({"source":source,"field":field,"owner":"workspace-config",
            "value_revision":digest(value).expect("JSON value hashes"),"value":value,
            "affects":[],"reason":disposition,"authority":"advisory",
            "applicability":"agent-judgment-required","satisfaction":"not-evidence"});
    }
    let owner = match field.split('.').next().unwrap_or("") {
        "assurance" => "verification",
        "delegation" | "delegation_targets" | "handoff" => "assignment-delegation",
        "local_memory" => "memory",
        "session_logging" => "maintainer-diagnostics",
        _ => "workspace-config",
    };
    let affects = match owner {
        "verification" => vec!["claim:complete"],
        "assignment-delegation" => vec![
            "effect:implementation",
            "effect:delegation",
            "claim:complete",
        ],
        "maintainer-diagnostics" => vec!["effect:session-logging"],
        _ => vec!["task"],
    };
    json!({"source":source, "field":field, "owner":owner,
        "value_revision":digest(value).expect("JSON value hashes"),
        "affects":affects, "reason":"current-control-requires-native-owner"})
}

/// Fields here are existing owner contracts, not a new authoring surface.
/// The native facade consumes admission selectors and constraints; it must retain
/// `contribution` until the named residual owners genuinely supply their effects.
pub fn view(target: &Path) -> Result<Value, CoreError> {
    let root = Dir::open_ambient_dir(target, ambient_authority())
        .map_err(|e| CoreError::new(e.to_string()))?;
    let mut sources = vec![];
    let mut residuals = vec![];
    let mut blockers = vec![];
    let mut shared = json!({});
    let mut local = json!({});
    for (path, schema, destination) in [
        (
            SHARED,
            include_str!(
                "../../../src/agentic_workspace/contracts/schemas/workspace_config.schema.json"
            ),
            &mut shared,
        ),
        (
            LOCAL,
            include_str!(
                "../../../src/agentic_workspace/contracts/schemas/workspace_local_override.schema.json"
            ),
            &mut local,
        ),
    ] {
        match load(&root, path, schema) {
            Ok(Some((value, revision))) => {
                sources.push(json!({"reference":path,"revision":revision,"status":"current"}));
                *destination = value;
            }
            Ok(None) => (),
            Err(reason) => {
                sources.push(json!({"reference":path,"status":"invalid","reason":reason}));
                blockers.push(json!({"code":format!("invalid-config:{path}"),
                    "message":format!("Preserve {path}; its current configuration cannot be admitted: {reason}"),
                    "affects":["task"]}));
            }
        }
    }
    for (source, value) in [(SHARED, &shared), (LOCAL, &local)] {
        for (section, content) in value.as_object().into_iter().flatten() {
            if section == "schema_version" {
                continue;
            }
            let entries = content
                .as_object()
                .map(|v| {
                    v.iter()
                        .map(|(key, value)| (format!("{section}.{key}"), value))
                        .collect::<Vec<_>>()
                })
                .unwrap_or_else(|| vec![(section.clone(), content)]);
            for (field, value) in entries {
                let consumed =
                    matches!(field.as_str(), "workspace.enabled" | "workspace.cli_invoke")
                        || (source == SHARED
                            && matches!(
                                field.as_str(),
                                "cli_compatibility.minimum_reader_epoch"
                                    | "cli_compatibility.required_reader_capabilities"
                                    | "assurance.decision_record_target"
                                    | "assurance.decision_record_revision"
                                    | "assurance.instruction_revision"
                                    | "assurance.requirements"
                            ))
                        || (source == LOCAL
                            && matches!(
                                field.as_str(),
                                "safety.safe_to_auto_run_commands"
                                    | "safety.requires_human_verification_on_pr"
                            ));
                if !consumed && present(value) {
                    residuals.push(residual(source, &field, value));
                }
            }
        }
    }
    for item in &residuals {
        if item["affects"].as_array().is_some_and(Vec::is_empty) {
            continue;
        }
        blockers.push(json!({"code":format!("native-config-owner:{}:{}", item["source"].as_str().unwrap(),item["field"].as_str().unwrap()),
            "message":format!("{} [{}] remains owned by {}; consume that current owner before the affected behavior.",item["source"],item["field"],item["owner"]),
            "affects":item["affects"]}));
    }
    let enabled = local["workspace"]["enabled"]
        .as_bool()
        .or_else(|| shared["workspace"]["enabled"].as_bool())
        .unwrap_or(true);
    let cli_invoke = local["workspace"]["cli_invoke"]
        .as_str()
        .or_else(|| shared["workspace"]["cli_invoke"].as_str());
    let safe = local["safety"]["safe_to_auto_run_commands"].as_bool();
    let human_review = local["safety"]["requires_human_verification_on_pr"]
        .as_bool()
        .unwrap_or(false);
    if !enabled {
        blockers.push(json!({"code":"workspace-disabled","message":"Current workspace configuration disables ordinary operation; diagnostics and owner recovery remain available.","affects":["task"]}));
    }
    if safe == Some(false) {
        blockers.push(json!({"code":"local-command-safety-ceiling","message":"Local safety forbids automatic configured command execution.","affects":["effect:execute-command"]}));
    }
    if human_review {
        blockers.push(json!({"code":"local-human-review-required","message":"PR/review closeout requires current human verification.","affects":["claim:pr-complete"]}));
    }
    let revision = digest(&json!({"sources":sources,"residuals":residuals}))?;
    // Restriction targets come only from the owner mappings above, never from
    // config-authored effect names. A ceiling grants no operation, effect or claim.
    let affects = blockers
        .iter()
        .flat_map(|blocker| blocker["affects"].as_array().into_iter().flatten())
        .filter_map(Value::as_str)
        .collect::<std::collections::BTreeSet<_>>();
    let restrictions = if affects.is_empty() {
        json!([])
    } else {
        json!([{"owner":"workspace","affects":affects}])
    };
    let mut capability_contract = json!({"kind":"agentic-workspace/capability-contract/v1",
        "revision":"pending", "owners":[{"owner":"workspace","revision":"native-configuration-source/v1"}],
        "restriction_authorities":restrictions});
    capability_contract["revision"] = json!(digest(&capability_contract)?);
    Ok(
        json!({"kind":"agentic-workspace/native-configuration-view/v1", "revision":revision,
        "sources":sources,"residuals":residuals,"enabled":enabled,"cli_invoke":cli_invoke,
        "capability_contract":capability_contract,
        "modules":shared["modules"]["enabled"],
        "assignment_requirements":{"configured":local["delegation_targets"].as_object().is_some_and(|targets|!targets.is_empty()),
            "required_execution_guarantees":local["delegation"]["required_execution_guarantees"].as_array().cloned().unwrap_or_default()},
        "admissions":{"instruction_revision":shared["assurance"]["instruction_revision"],
            "decision_record_target":shared["assurance"]["decision_record_target"],
            "decision_record_revision":shared["assurance"]["decision_record_revision"]},
        "safety":{"safe_to_auto_run_commands":safe,"requires_human_verification_on_pr":human_review,
            "automatic_execution_permitted":false},
        "contribution":{"owner":"workspace","revision":revision,"blockers":blockers}}),
    )
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::{
        fs,
        path::PathBuf,
        time::{SystemTime, UNIX_EPOCH},
    };

    struct Repo(PathBuf);
    impl Repo {
        fn new() -> Self {
            let path = std::env::temp_dir().join(format!(
                "aw-native-config-{}-{}",
                std::process::id(),
                SystemTime::now()
                    .duration_since(UNIX_EPOCH)
                    .unwrap()
                    .as_nanos()
            ));
            fs::create_dir(&path).unwrap();
            Self(path)
        }
        fn write(&self, source: &str, value: &str) {
            fs::create_dir_all(self.0.join(".agentic-workspace")).unwrap();
            fs::write(self.0.join(source), value).unwrap();
        }
    }
    impl Drop for Repo {
        fn drop(&mut self) {
            fs::remove_dir_all(&self.0).unwrap();
        }
    }

    #[test]
    fn absent_empty_and_unrelated_files_remain_quiet() {
        let repo = Repo::new();
        assert!(
            view(&repo.0).unwrap()["contribution"]["blockers"]
                .as_array()
                .unwrap()
                .is_empty()
        );
        repo.write(".agentic-workspace/unrelated.txt", "unrelated history");
        repo.write(SHARED, "schema_version = 1\n[modules]\nenabled = []\n");
        repo.write(LOCAL, "schema_version = 1\n");
        let result = view(&repo.0).unwrap();
        assert!(result["residuals"].as_array().unwrap().is_empty());
        assert!(
            result["contribution"]["blockers"]
                .as_array()
                .unwrap()
                .is_empty()
        );
    }

    #[test]
    fn shared_admission_cannot_be_shadowed_by_local_input() {
        let repo = Repo::new();
        let revision = "a".repeat(40);
        repo.write(
            SHARED,
            &format!("schema_version=1\n[assurance]\ninstruction_revision='{revision}'\n"),
        );
        repo.write(
            LOCAL,
            &format!(
                "schema_version=1\n[assurance]\ninstruction_revision='{}'\n",
                "b".repeat(40)
            ),
        );
        let result = view(&repo.0).unwrap();
        assert_eq!(result["admissions"]["instruction_revision"], revision);
        assert_eq!(result["sources"][1]["status"], "invalid");
        assert!(
            !result["contribution"]["blockers"]
                .as_array()
                .unwrap()
                .is_empty()
        );
    }

    #[test]
    fn native_source_admission_selectors_are_consumed() {
        let repo = Repo::new();
        let revision = "a".repeat(40);
        repo.write(SHARED, &format!("schema_version=1\n[assurance]\ndecision_record_target='docs/decisions'\ndecision_record_revision='{revision}'\ninstruction_revision='{revision}'\n"));
        let result = view(&repo.0).unwrap();
        assert_eq!(
            result["admissions"]["decision_record_target"],
            "docs/decisions"
        );
        assert_eq!(result["admissions"]["decision_record_revision"], revision);
        let residuals = result["residuals"].as_array().unwrap();
        assert!(residuals.is_empty());
        assert_eq!(result["admissions"]["instruction_revision"], revision);
    }

    #[test]
    fn local_automation_does_not_widen_independent_safety() {
        let repo = Repo::new();
        repo.write(LOCAL, "schema_version=1\n[safety]\nsafe_to_auto_run_commands=false\n[delegation]\ntransport_authority='automatic'\n");
        let result = view(&repo.0).unwrap();
        assert_eq!(result["safety"]["safe_to_auto_run_commands"], false);
        assert_eq!(result["safety"]["automatic_execution_permitted"], false);
        assert!(
            result["contribution"]["blockers"]
                .as_array()
                .unwrap()
                .iter()
                .any(|v| v["code"] == "local-command-safety-ceiling")
        );
        assert!(
            result["residuals"]
                .as_array()
                .unwrap()
                .iter()
                .any(|v| v["field"] == "delegation.transport_authority")
        );
    }

    #[test]
    fn malformed_source_is_preserved_and_cannot_disappear() {
        let repo = Repo::new();
        repo.write(SHARED, "schema_version = [invalid secret-value");
        let result = view(&repo.0).unwrap();
        assert_eq!(result["sources"][0]["status"], "invalid");
        assert!(!result.to_string().contains("secret-value"));
        assert_eq!(
            fs::read_to_string(repo.0.join(SHARED)).unwrap(),
            "schema_version = [invalid secret-value"
        );
        assert_eq!(
            result["contribution"]["blockers"][0]["affects"],
            json!(["task"])
        );
    }

    #[test]
    fn supported_overrides_and_source_currentness_are_exact() {
        let repo = Repo::new();
        repo.write(
            SHARED,
            "schema_version=1\n[workspace]\nenabled=false\ncli_invoke='shared-command'\n",
        );
        repo.write(
            LOCAL,
            "schema_version=1\n[workspace]\nenabled=true\ncli_invoke='local-command'\n",
        );
        let first = view(&repo.0).unwrap();
        assert_eq!(first["enabled"], true);
        assert_eq!(first["cli_invoke"], "local-command");
        repo.write(
            LOCAL,
            "schema_version=1\n[workspace]\nenabled=false\ncli_invoke='local-command'\n",
        );
        let second = view(&repo.0).unwrap();
        assert_eq!(second["enabled"], false);
        assert!(
            second["contribution"]["blockers"]
                .as_array()
                .unwrap()
                .iter()
                .any(|v| v["code"] == "workspace-disabled")
        );
        assert_ne!(first["revision"], second["revision"]);
    }

    #[test]
    fn unsupported_shared_proof_remains_binding_despite_local_preferences() {
        let repo = Repo::new();
        repo.write(
            SHARED,
            "schema_version=1\n[assurance]\nstrict_closeout=true\n",
        );
        repo.write(
            LOCAL,
            "schema_version=1\n[safety]\nrequires_human_verification_on_pr=false\n",
        );
        let result = view(&repo.0).unwrap();
        let residual = &result["residuals"][0];
        assert_eq!(residual["source"], SHARED);
        assert_eq!(residual["field"], "assurance.strict_closeout");
        assert_eq!(residual["affects"], json!(["claim:complete"]));
    }

    #[test]
    fn final_compiler_accepts_config_ceilings_without_execution_grants() {
        let repo = Repo::new();
        repo.write(
            SHARED,
            "schema_version=1\n[assurance]\nstrict_closeout=true\n",
        );
        repo.write(
            LOCAL,
            "schema_version=1\n[safety]\nsafe_to_auto_run_commands=false\n",
        );
        let result = view(&repo.0).unwrap();
        let contract = &result["capability_contract"];
        assert!(contract["claim_authorities"].is_null());
        for field in ["effects", "operations", "requests"] {
            assert!(contract["owners"][0][field].is_null());
        }
        let decision = crate::compile_value(json!({"capability_contract":contract,
            "contributions":[result["contribution"]],"intent":{}}))
        .unwrap();
        assert_eq!(decision["blockers"].as_array().unwrap().len(), 2);
        assert!(decision["primary_action"].is_null());
        assert!(
            decision["claim_boundary"]["allowed"]
                .as_array()
                .unwrap()
                .is_empty()
        );

        repo.write(SHARED, "broken");
        let invalid = view(&repo.0).unwrap();
        let decision =
            crate::compile_value(json!({"capability_contract":invalid["capability_contract"],
            "contributions":[invalid["contribution"]],"intent":{}}))
            .unwrap();
        assert_eq!(decision["status"], "blocked");
    }
}
