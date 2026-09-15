//! Read canonical configuration as source-owned policy, never as mutation custody.
//! Unsupported current controls remain visible at their affected owner boundary.
use crate::{CoreError, digest};
use cap_std::{ambient_authority, fs::Dir};
use serde_json::{Value, json};
use sha2::{Digest, Sha256};
use std::{io::Read, path::Path};

const SHARED: &str = ".agentic-workspace/config.toml";
const LOCAL: &str = ".agentic-workspace/config.local.toml";
pub(crate) const MAX_SOURCE_BYTES: usize = 1_048_576;

/// Every present source uses the same closed current grammar.
pub(crate) fn validate_source(value: &Value, schema: &str) -> Result<(), String> {
    let schema: Value = serde_json::from_str(schema).map_err(|e| e.to_string())?;
    crate::schema_validator(&schema, "native configuration")
        .map_err(|e| e.to_string())?
        .validate(value)
        .map_err(|e| format!("invalid configuration at {}", e.instance_path()))
}

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
        .take((MAX_SOURCE_BYTES + 1) as u64)
        .read_to_end(&mut bytes)
        .map_err(|e| e.to_string())?;
    if bytes.len() > MAX_SOURCE_BYTES {
        return Err("configuration source exceeds bounded read".into());
    }
    let revision = format!("sha256:{:x}", Sha256::digest(&bytes));
    let text = std::str::from_utf8(&bytes).map_err(|e| e.to_string())?;
    let parsed: toml::Value = toml::from_str(text.trim_start_matches('\u{feff}'))
        .map_err(|_| "invalid TOML; inspect the source locally".to_owned())?;
    let value = serde_json::to_value(parsed).map_err(|e| e.to_string())?;
    validate_source(&value, schema)?;
    Ok(Some((value, revision)))
}

/// Explicit repo enablement gates availability, never task relevance.
pub(crate) fn module_enabled(configuration: &Value, owner: &str) -> bool {
    configuration["modules"]
        .as_array()
        .is_none_or(|modules| modules.iter().any(|module| module == owner))
}

/// Shared transport/projection only: each owner supplies its own source anchors
/// and restriction scopes. Bytes are observed without interpreting domain state.
pub(crate) fn disabled_owner(
    target: &Path,
    owner: &str,
    paths: &[&str],
    affects: &[&str],
) -> Result<Value, CoreError> {
    let root = Dir::open_ambient_dir(target, ambient_authority())
        .map_err(|e| CoreError::new(e.to_string()))?;
    let mut sources = Vec::new();
    for path in paths {
        match crate::native_verification::read(&root, path) {
            Ok(None) => (),
            Ok(Some(bytes)) => sources.push(json!({"reference":path,"revision":format!("sha256:{:x}",Sha256::digest(bytes)),"status":"present-uninterpreted"})),
            Err(reason) => sources.push(json!({"reference":path,"status":"unavailable-uninterpreted","reason":reason.to_string()})),
        }
    }
    let revision = digest(&json!({"owner":owner,"availability":"disabled","sources":sources}))?;
    let blockers = if sources.is_empty() {
        json!([])
    } else {
        json!([{"code":"disabled-owner-source-reconciliation-required",
        "message":"The owner is disabled but recognized sources remain. Preserve them; source presence does not establish live custody, retirement or transfer. Responsible-owner reconciliation remains unresolved.","affects":affects}])
    };
    let mut contract = json!({"kind":"agentic-workspace/capability-contract/v1","revision":"pending",
        "owners":[{"owner":owner,"revision":"disabled-source-observation/v1"}],
        "restriction_authorities":if sources.is_empty(){json!([])}else{json!([{"owner":owner,"affects":affects}])}});
    contract["revision"] = json!(digest(&contract)?);
    Ok(
        json!({"status":"disabled","source_revision":revision,"sources":sources,"requests":[],"planning_input":null,
        "capability_contract":contract,"contribution":{"owner":owner,"revision":revision,"blockers":blockers,"settled":sources.is_empty()},
        "claim_boundary":"Disabled availability supplies no operations, judgment, custody transfer or proof."}),
    )
}

/// Read current owner selectors and independent safety constraints.
pub fn view(target: &Path) -> Result<Value, CoreError> {
    let root = Dir::open_ambient_dir(target, ambient_authority())
        .map_err(|e| CoreError::new(e.to_string()))?;
    let mut sources = vec![];
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
    let payload = crate::native_payload::view(target, &shared["payload"])?;
    blockers.extend(
        payload["blockers"]
            .as_array()
            .into_iter()
            .flatten()
            .cloned(),
    );
    let assignment_source = crate::native_assignment_policy::load(target);
    let mut assignment_policy = Value::Null;
    match assignment_source {
        Ok(observed)=>{
            local=observed.effective;
            assignment_policy=observed.policy;
            assignment_policy["source_revision"]=json!(observed.revision);
            for source in observed.sources {if !sources.iter().any(|s|s["reference"]==source["reference"]){sources.push(source);}}

        },
        Err(error)=>blockers.push(json!({"code":"assignment-policy-source-unresolved","message":error.to_string(),"affects":["effect:implementation"]})),
    }
    if shared["modules"]["enabled"]
        .as_array()
        .is_some_and(|modules| !modules.iter().any(|m| m == "verification"))
        && [
            "default_level",
            "strict_closeout",
            "agent_may_escalate",
            "agent_may_deescalate",
        ]
        .iter()
        .any(|key| !shared["assurance"][*key].is_null())
    {
        blockers.push(json!({"code":"verification-policy-owner-disabled",
            "message":"Shared proof policy requires its Verification owner. Enable that owner before claiming completion.",
            "affects":["claim:complete"]}));
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
    let artifact_profile = crate::native_planning::artifact_profile(
        target,
        &shared["workspace"]["workflow_artifact_profile"],
    )?;
    blockers.extend(
        artifact_profile["blockers"]
            .as_array()
            .into_iter()
            .flatten()
            .cloned(),
    );
    // Work-class posture has its own selected dependency in task requirements.
    // Keep byte revisions visible, but do not globally invalidate unrelated work.
    let mut configuration_sources = sources.clone();
    let mut configuration_shared = shared.clone();
    if let Some(fields) = configuration_shared.as_object_mut() {
        fields.remove("execution_posture");
    }
    for source in &mut configuration_sources {
        if source["reference"] == SHARED && source["status"] == "current" {
            source["revision"] = json!(digest(&configuration_shared)?);
        }
    }
    let revision = digest(
        &json!({"sources":configuration_sources,"artifact_profile":artifact_profile,"payload":payload}),
    )?;
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
        "revision":"pending", "owners":[{"owner":"workspace","revision":revision}],
        "restriction_authorities":restrictions});
    capability_contract["revision"] = json!(digest(&capability_contract)?);
    Ok(
        json!({"kind":"agentic-workspace/native-configuration-view/v1", "revision":revision,
        "sources":sources,"artifact_profile":artifact_profile,"payload":payload,"enabled":enabled,"cli_invoke":cli_invoke,
        "capability_contract":capability_contract,
        "clarification":local["clarification"],"agent_instructions_file":shared["workspace"]["agent_instructions_file"],"modules":shared["modules"]["enabled"],"independent_admissions":shared["modules"]["independent"],"system_intent":shared["system_intent"],
        "improvement_latitude":shared["workspace"]["improvement_latitude"],"execution_posture":shared["execution_posture"],"assignment_policy":assignment_policy,"assignment_requirements":{"configured":local["delegation_targets"].as_object().is_some_and(|targets|!targets.is_empty()) || shared["delegation_targets"].as_object().is_some_and(|targets|!targets.is_empty()),
            "required_execution_guarantees":local["delegation"]["required_execution_guarantees"].as_array().cloned().unwrap_or_default()},
        "admissions":{"instruction_revision":shared["assurance"]["instruction_revision"],
            "decision_record_target":shared["assurance"]["decision_record_target"],
            "decision_record_revision":shared["assurance"]["decision_record_revision"],
            "decision_record_fallback":shared["assurance"]["decision_record_fallback"],
            "decision_delegations":shared["assurance"]["decision_delegations"]},
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
        repo.write(SHARED, "[modules]\nenabled = []\n");
        repo.write(LOCAL, "");
        let result = view(&repo.0).unwrap();
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
            &format!("[assurance]\ninstruction_revision='{revision}'\n"),
        );
        repo.write(
            LOCAL,
            &format!("[assurance]\ninstruction_revision='{}'\n", "b".repeat(40)),
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
        repo.write(SHARED, &format!("[assurance]\ndecision_record_target='docs/decisions'\ndecision_record_revision='{revision}'\ninstruction_revision='{revision}'\n"));
        let result = view(&repo.0).unwrap();
        assert_eq!(
            result["admissions"]["decision_record_target"],
            "docs/decisions"
        );
        assert_eq!(result["admissions"]["decision_record_revision"], revision);
        assert_eq!(result["admissions"]["instruction_revision"], revision);
    }

    #[test]
    fn local_automation_does_not_widen_independent_safety() {
        let repo = Repo::new();
        repo.write(LOCAL, "[safety]\nsafe_to_auto_run_commands=false\n[delegation]\ntransport_authority='automatic'\n");
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
        assert_eq!(
            result["assignment_policy"]["transport_authority"],
            "automatic"
        );
        assert_eq!(result["assignment_policy"]["execution_permitted"], false);
        assert_eq!(result["assignment_policy"]["effective_mode"], "suggest");
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
    fn old_and_unknown_configuration_is_rejected_without_fallback() {
        let repo = Repo::new();
        for text in [
            "schema_version=1",
            "schema_version=2",
            "[workspace]\nmaintainer_mode=true",
            "[cli_compatibility]\nminimum_reader_epoch=1",
            "unknown_policy=true",
        ] {
            repo.write(SHARED, text);
            let result = view(&repo.0).unwrap();
            assert_eq!(result["sources"][0]["status"], "invalid");
            assert_eq!(fs::read_to_string(repo.0.join(SHARED)).unwrap(), text);
        }
    }

    #[test]
    fn current_transport_predicates_preserve_variant_requirements() {
        let schema = include_str!(
            "../../../src/agentic_workspace/contracts/schemas/workspace_local_override.schema.json"
        );
        for (transport, valid) in [
            (
                json!({"kind":"native","adapter":"selected-owner","parameters":{}}),
                true,
            ),
            (json!({"kind":"native","adapter":"selected-owner"}), false),
            (json!({"kind":"process","command":["worker"]}), true),
            (json!({"kind":"process"}), false),
            (json!({"kind":"manual","command":["worker"]}), false),
            (
                json!({"kind":"process","command":["worker"],"parameters":{}}),
                false,
            ),
        ] {
            let value = json!({"delegation_targets":{"worker":{"transports":[transport]}}});
            assert_eq!(validate_source(&value, schema).is_ok(), valid, "{value}");
        }
    }

    #[test]
    fn supported_overrides_and_source_currentness_are_exact() {
        let repo = Repo::new();
        repo.write(
            SHARED,
            "[workspace]\nenabled=false\ncli_invoke='shared-command'\n",
        );
        repo.write(
            LOCAL,
            "[workspace]\nenabled=true\ncli_invoke='local-command'\n",
        );
        let first = view(&repo.0).unwrap();
        assert_eq!(first["enabled"], true);
        assert_eq!(first["cli_invoke"], "local-command");
        repo.write(
            LOCAL,
            "[workspace]\nenabled=false\ncli_invoke='local-command'\n",
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
    fn strict_closeout_remains_unresolved_without_verification() {
        let repo = Repo::new();
        repo.write(
            SHARED,
            "[assurance]\nstrict_closeout=true\n[modules]\nenabled=[\"memory\"]\n",
        );
        let result = view(&repo.0).unwrap();
        assert!(
            result["contribution"]["blockers"]
                .as_array()
                .unwrap()
                .iter()
                .any(|row| row["code"] == "verification-policy-owner-disabled")
        );
        assert!(validate_source(&json!({"assurance":{"strict_closeout":false}}), include_str!("../../../src/agentic_workspace/contracts/schemas/workspace_local_override.schema.json")).is_err());
    }

    #[test]
    fn final_compiler_accepts_config_ceilings_without_execution_grants() {
        let repo = Repo::new();
        repo.write(
            SHARED,
            "[assurance]\nclassification_owner=\"config-native\"\n",
        );
        repo.write(LOCAL, "[safety]\nsafe_to_auto_run_commands=false\n");
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
