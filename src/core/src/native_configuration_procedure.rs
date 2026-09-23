//! Selected Configuration consequence projection over fresh responsible owners.
//! This adds no source writer, applicability rule, evidence or completion grant.
use crate::CoreError;
use serde_json::{Value, json};
use std::path::Path;

pub(crate) const READ: &str = "configuration/observe-behavior/v1";
pub(crate) fn declaration() -> Value {
    json!({"kind":READ,"result_kind":"agentic-workspace/configuration-behavior/v1","input_schema":{"$schema":"https://json-schema.org/draft/2020-12/schema","type":"object","additionalProperties":false,"required":["concern"],"properties":{"concern":{"enum":["instructions","diagnostics","assignment","modules","invocation","preferences"]}}}})
}
pub(crate) fn concern(key: &str) -> Option<&'static str> {
    match key {
        "workspace.agent_instructions_file" => Some("instructions"),
        "session_logging.enabled" | "session_logging.path_mode" => Some("diagnostics"),
        "modules.enabled" | "modules.independent" => Some("modules"),
        "workspace.cli_invoke" | "workspace.enabled" => Some("invocation"),
        "clarification.mode" | "workspace.improvement_latitude" => Some("preferences"),
        _ => None,
    }
}
pub(crate) fn observe(target: &Path, concern: &str, current: &Value) -> Result<Value, CoreError> {
    let config = &current["configuration"];
    let observation = match concern {
        "instructions" => {
            json!({"owner":"startup-adapter","selected_source":config["agent_instructions_file"],"current":current["startup_adapter"]})
        }
        "diagnostics" => {
            json!({"owner":"session-logging","effective_policy":crate::maintainer_logging::effective_policy(target)?,"capture_boundary":"Transport reports actual capture separately. Effective enablement is not a successful diagnostic write."})
        }
        "assignment" => {
            json!({"owner":"assignment","current":current["task_requirements"]["assignment"],"requirements":current["task_requirements"],"policy":config["assignment_policy"],"configured_requirements":config["assignment_requirements"],"write_boundary":{"status":"unavailable","source":".agentic-workspace/config.local.toml","reason":"Required execution guarantees and target declarations are outside the current Configuration writer. Use their human/source owner; do not broaden a returned editable choice."}})
        }
        "modules" => {
            json!({"owner":"selected-module-owners","enabled":config["modules"],"memory":current["memory"],"planning":current["planning"],"verification":current["verification"],"independent":current["independent_owners"],"write_boundary":"Configuration controls only its declared module choices. Module manifests and state require their existing owner operations; unavailable writers remain explicit gaps."})
        }
        "invocation" => {
            json!({"owner":"configuration","enabled":config["enabled"],"cli_invoke":config["cli_invoke"],"runtime":current["runtime_compatibility"],"boundary":"A saved invocation string does not prove that another executable can be launched."})
        }
        "preferences" => {
            json!({"owner":"configuration","clarification":config["clarification"],"improvement_latitude":config["improvement_latitude"],"boundary":"Advisory procedure preferences never answer required owner decisions or authorize effects."})
        }
        _ => return Err(CoreError::new("unsupported Configuration behavior concern")),
    };
    Ok(
        json!({"kind":"agentic-workspace/configuration-behavior/v1","status":"observed","concern":concern,"work":current["current_work"],"configuration_revision":config["revision"],"observation":observation,"setup_settlement":crate::native_configuration_assessment::settlement(concern),"remaining_restrictions":current["decision_packet"]["blockers"],"remaining_judgment":"Determine whether the established consumer behavior satisfies the requested human outcome; source publication alone does not.","completion_authority":false}),
    )
}
pub(crate) fn attach(target: &Path, invocation: &Value, result: &mut Value) {
    if invocation["source_owner"] != "configuration" {
        return;
    }
    let key = invocation["arguments"]["request"]["arguments"]["key"]
        .as_str()
        .unwrap_or("");
    let Some(concern) = concern(key) else {
        return;
    };
    let observed = if result["continuation_status"] == "current" {
        observe(target, concern, &result["continuation"]["result"])
    } else {
        Err(CoreError::new(
            "fresh affected-owner continuation unavailable",
        ))
    };
    result["configuration_behavior"] = match observed {
        Ok(observed) => observed,
        Err(e) => {
            json!({"kind":"agentic-workspace/configuration-behavior/v1","status":"unavailable","concern":concern,"reason":e.to_string(),"retry_effect":false,"completion_authority":false})
        }
    };
}
