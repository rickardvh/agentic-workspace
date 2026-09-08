//! Source-owned assurance guidance and selected profile obligations.
//! Assessment changes neither proof sufficiency nor reviewer authority.
use crate::{CoreError, digest};
use serde_json::{Value, json};
use std::collections::BTreeSet;

pub(crate) fn declaration() -> Value {
    let all: Value = serde_json::from_str(include_str!(
        "../../../src/agentic_workspace/contracts/schemas/source_decision_input.schema.json"
    ))
    .expect("checked schema");
    let mut shape = all["$defs"]["verification_strategy_request"].clone();
    shape["$schema"] = all["$schema"].clone();
    json!({"kind":"verification/strategy/v1","result_kind":"agentic-workspace/verification-strategy/v1","input_schema":shape})
}
pub(crate) fn policy(config: &Value) -> Result<Value, CoreError> {
    let assurance = &config["assurance"];
    let fields = [
        "default_level",
        "agent_may_escalate",
        "agent_may_deescalate",
        "proof_profiles",
    ];
    let configured = fields.iter().any(|field| assurance.get(field).is_some());
    let mut policy = json!({"configured":configured,"baseline":assurance["default_level"].as_str().unwrap_or("low"),"agent_may_escalate":assurance["agent_may_escalate"].as_bool().unwrap_or(true),"agent_may_deescalate":assurance["agent_may_deescalate"].as_bool().unwrap_or(false),"profiles":assurance["proof_profiles"].as_object().cloned().unwrap_or_default()});
    policy["revision"] = json!(digest(&policy)?);
    Ok(policy)
}
fn strings(value: &Value) -> Vec<String> {
    value
        .as_array()
        .into_iter()
        .flatten()
        .filter_map(Value::as_str)
        .map(str::to_owned)
        .collect()
}
fn rank(level: &str) -> usize {
    ["low", "medium", "high", "critical"]
        .iter()
        .position(|v| *v == level)
        .unwrap_or(0)
}

pub(crate) fn view(
    policy: &Value,
    assurance: &Value,
    planning: Option<&Value>,
    assessment: Option<&Value>,
) -> Result<Value, CoreError> {
    let baseline = policy["baseline"].as_str().unwrap();
    let mut level = baseline;
    let mut selected = BTreeSet::<String>::new();
    let mut required = BTreeSet::<String>::new();
    let mut recommended = BTreeSet::<String>::new();
    let mut gaps = Vec::<String>::new();
    if let Some(assessment) = assessment {
        crate::schema_validator(
            &declaration()["input_schema"],
            "Verification strategy assessment",
        )?
        .validate(assessment)
        .map_err(|e| CoreError::new(format!("invalid Verification strategy assessment: {e}")))?;
        level = assessment["level"].as_str().unwrap();
        if rank(level) > rank(baseline) && policy["agent_may_escalate"] != true {
            gaps.push("assurance-escalation-not-authorized".into());
        }
        if rank(level) < rank(baseline) && policy["agent_may_deescalate"] != true {
            gaps.push("assurance-deescalation-not-authorized".into());
        }
        selected.extend(strings(&assessment["profile_ids"]));
    }
    for row in assurance["requirements"].as_array().into_iter().flatten() {
        let profile = row["source_requirement"]["proof_profile"]
            .as_str()
            .unwrap_or("");
        if profile.is_empty() || row["status"] == "not-applicable" {
            continue;
        }
        if row["status"] == "unresolved" {
            gaps.push(format!(
                "profile-applicability-unresolved:{}",
                row["id"].as_str().unwrap_or("")
            ));
        } else if matches!(
            row["force"].as_str(),
            Some("blocking" | "required-before-closeout")
        ) {
            required.insert(profile.into());
        } else {
            recommended.insert(profile.into());
        }
    }
    selected.extend(required.iter().cloned());
    // The current native subject alone cannot assert an absent former Planning
    // profile selection. The Planning owner must supply that semantic projection.
    if planning.is_some()
        && policy["profiles"]
            .as_object()
            .is_some_and(|profiles| !profiles.is_empty())
    {
        gaps.push("planning-assurance-profile-projection-unavailable".into());
    }
    let mut routes = serde_json::Map::new();
    let mut profiles = Vec::new();
    let mut disallowed = BTreeSet::new();
    let mut obligations = Vec::new();
    let mut invalid = false;
    for id in selected {
        let Some(profile) = policy["profiles"].get(&id) else {
            gaps.push(format!("selected-proof-profile-unavailable:{id}"));
            invalid = true;
            continue;
        };
        if profile.as_object().is_some_and(|fields| {
            fields.keys().any(|key| {
                !matches!(
                    key.as_str(),
                    "required_commands"
                        | "optional_commands"
                        | "disallowed_commands"
                        | "review_aids"
                )
            })
        }) {
            gaps.push(format!("selected-proof-profile-unknown-fields:{id}"));
            invalid = true;
        }
        let required_commands = strings(&profile["required_commands"]);
        let optional = strings(&profile["optional_commands"]);
        let denied = strings(&profile["disallowed_commands"]);
        let combined: Vec<&String> = required_commands
            .iter()
            .chain(&optional)
            .chain(&denied)
            .collect();
        if combined.iter().collect::<BTreeSet<_>>().len() != combined.len() {
            gaps.push(format!("proof-profile-command-role-conflict:{id}"));
            invalid = true;
        }
        disallowed.extend(denied.clone());
        let revision = digest(profile)?;
        let source_ref = format!(".agentic-workspace/config.toml#assurance.proof_profiles.{id}");
        profiles.push(json!({"id":id,"source_ref":source_ref,"source_revision":revision,"selected_by":if required.contains(&id){"binding-requirement"}else{"agent-assessment"},"required_count":required_commands.len(),"optional_count":optional.len(),"disallowed_count":denied.len(),"evidence_status":"not-established-by-selection"}));
        if !required_commands.is_empty() {
            obligations.push(json!({"profile_id":id,"required_commands":required_commands,"source_ref":source_ref,"source_revision":revision,"status":"current-proof-evidence-required"}));
        }
        let mut route = profile.clone();
        route["commands"] = json!(
            required_commands
                .iter()
                .chain(&optional)
                .collect::<Vec<_>>()
        );
        route["source_kind"] = json!("config-proof-profile");
        route["source_ref"] = json!(source_ref);
        route["source_revision"] = json!(revision);
        routes.insert(format!("profile:{id}"), route);
    }
    for row in &obligations {
        if strings(&row["required_commands"])
            .iter()
            .any(|cmd| disallowed.contains(cmd))
        {
            gaps.push(format!(
                "selected-profile-required-command-disallowed:{}",
                row["profile_id"].as_str().unwrap()
            ));
            invalid = true;
        }
    }
    let denied_level = gaps.iter().any(|gap| gap.starts_with("assurance-"));
    if denied_level {
        level = baseline;
    }
    let available: Vec<Value> = policy["profiles"].as_object().into_iter().flatten().take(32).map(|(id,profile)|json!({"id":id,"revision":digest(profile).expect("source JSON hashes")})).collect();
    Ok(
        json!({"kind":"agentic-workspace/verification-strategy/v1","configured":policy["configured"],"source_revision":policy["revision"],"baseline_level":baseline,"effective_level":level,"level_status":if denied_level{"rejected"}else if assessment.is_some(){"agent-assessed"}else{"source-default-guidance"},"assessment":assessment,"available_profiles":available,"omitted_profile_count":policy["profiles"].as_object().map_or(0,|p|p.len().saturating_sub(32)),"selected_profiles":profiles,"recommended_profiles":recommended,"obligations":obligations,"disallowed_commands":disallowed,"routes":routes,"execution_blocked":invalid||denied_level,"gaps":gaps,"authority_boundary":"Guidance/profile selection does not waive source requirements or establish proof, task judgment, review or completion."}),
    )
}
pub(crate) fn public_view(view: &Value) -> Value {
    let mut result = view.clone();
    result.as_object_mut().unwrap().remove("routes");
    result
}
