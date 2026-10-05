//! Selected Configuration consequence projection over fresh responsible owners.
//! This adds no source writer, applicability rule, evidence or completion grant.
use crate::CoreError;
use serde_json::{Value, json};
use std::path::Path;

pub(crate) const READ: &str = "configuration/observe-behavior/v1";
pub(crate) const JOB: &str = "configuration/setup-job/v1";
pub(crate) const ASSESS: &str = "configuration/assess-concern/v1";
pub(crate) fn job_declarations() -> Vec<Value> {
    let concerns = json!({"enum":["instructions","diagnostics","assignment","modules","invocation","preferences"]});
    vec![
        json!({"kind":JOB,"result_kind":"agentic-workspace/setup-job/v1","input_schema":{"$schema":"https://json-schema.org/draft/2020-12/schema","type":"object","additionalProperties":false,"required":["job"],"properties":{
            "job":{"enum":["refresh-payload","expose-skill","expose-plugin","configure-behavior","assess-setup","remove-adoption"]},
            "concern":concerns,"scope":{"enum":["repository","machine-local"]},"key":{"type":"string","maxLength":128},
            "choice":{"type":"string","minLength":1,"maxLength":4096}},
            "allOf":[{"if":{"properties":{"job":{"enum":["configure-behavior","assess-setup"]}}},"then":{"required":["concern"]}}]}}),
        json!({"kind":ASSESS,"result_kind":"agentic-workspace/setup-job/v1","input_schema":{"$schema":"https://json-schema.org/draft/2020-12/schema","type":"object","additionalProperties":false,"required":["concern","judgment","reason"],"properties":{
            "concern":concerns,"scope":{"enum":["repository","machine-local"]},
            "judgment":{"enum":["working","handled-by-owner","excluded","not-relevant","pending","deferred","blocked","unavailable"]},
            "reason":{"type":"string","minLength":1,"maxLength":4096},"resume":{"type":"string","minLength":1,"maxLength":4096},
            "dependencies":{"type":"array","maxItems":64,"uniqueItems":true,"items":{"type":"string","maxLength":4096}}}}}),
    ]
}

/// Mechanical postimage preparation stays with Configuration. The caller only
/// supplies a bounded semantic judgment; existing publication admission remains.
pub(crate) fn assessment_proposal(
    target: &Path,
    task: &str,
    request: &Value,
    current: &Value,
) -> Result<Option<Value>, CoreError> {
    if request["request_kind"] != ASSESS {
        return Ok(None);
    }
    let args = &request["arguments"];
    let concern = args["concern"].as_str().unwrap();
    let scope = args["scope"].as_str().unwrap_or("repository");
    let assessment = &current["configuration_write"]["setup_assessment"];
    let mut proposed = assessment["record_request"].clone();
    if !proposed.is_object() {
        return Ok(None);
    }
    let status = match args["judgment"].as_str().unwrap() {
        "working" => "effective",
        "handled-by-owner" => "owner-managed",
        "not-relevant" => "irrelevant",
        other => other,
    };
    let mut row =
        json!({"subject":concern,"concern":concern,"status":status,"reason":args["reason"]});
    if status == "effective" {
        let witness = crate::native_configuration_assessment::consumer_witness(
            target, concern, scope, current,
        )?;
        if witness.is_null() {
            return Err(CoreError::new(format!(
                "Cannot record 'working' for {concern}: no current consumer observation is available. Use an unfinished judgment with the exact owner and next action, or handled-by-owner where supported."
            )));
        }
        row["observation"] = witness;
    } else if status == "owner-managed" {
        if crate::native_configuration_assessment::settlement(concern)["terminal_disposition"]
            != "owner-managed"
        {
            return Err(CoreError::new(
                "This concern requires an actual consumer observation or an unfinished judgment",
            ));
        }
    } else if matches!(status, "pending" | "deferred" | "blocked" | "unavailable") {
        let resume = args["resume"]
            .as_str()
            .filter(|s| !s.trim().is_empty())
            .ok_or_else(|| {
                CoreError::new("Unfinished setup needs its exact owner and next action")
            })?;
        row["resume"] = json!(resume);
    }
    let value = &mut proposed["arguments"]["value"];
    let mut rows = value["dispositions"]
        .as_array()
        .cloned()
        .unwrap_or_default();
    rows.retain(|prior| prior["concern"] != concern && prior["subject"] != concern);
    rows.push(row);
    value["dispositions"] = json!(rows);
    value["coverage"] = json!(format!(
        "Bounded current {concern} consideration: {}. Other retained dispositions remain subject to current consumer validation.",
        args["reason"].as_str().unwrap()
    ));
    if value["dispositions"].as_array().unwrap().iter().any(|r| {
        matches!(
            r["status"].as_str(),
            Some("pending" | "deferred" | "blocked" | "unavailable")
        )
    }) {
        let next = value["dispositions"]
            .as_array()
            .unwrap()
            .iter()
            .find(|r| {
                matches!(
                    r["status"].as_str(),
                    Some("pending" | "deferred" | "blocked" | "unavailable")
                )
            })
            .unwrap()["resume"]
            .clone();
        value["continuation"] = json!({"task":task,"next_action":next});
    } else {
        value["continuation"] = Value::Null;
    }
    if value["source_reassessment"].is_object() {
        value["source_reassessment"]["reason"] = args["reason"].clone();
    }
    Ok(Some(proposed))
}

pub(crate) fn choice_subject(choice: &Value) -> Value {
    [
        &choice["subject"],
        &choice["setting"],
        &choice["request"]["arguments"]["source"],
        &choice["request"]["request_kind"],
    ]
    .into_iter()
    .find(|value| value.is_string())
    .cloned()
    .unwrap_or(Value::Null)
}

pub(crate) fn choice_request(choice: &Value) -> &Value {
    [
        "recovery_request",
        "request",
        "expose_request",
        "remove_request",
    ]
    .into_iter()
    .map(|key| &choice[key])
    .find(|request| request.is_object())
    .unwrap_or(&choice["request"])
}

pub(crate) fn setup_view(current: &Value) -> Result<Value, CoreError> {
    let configuration = &current["configuration_write"];
    let selected = &configuration["selected_setup_job"];
    if !selected.is_object() {
        let mut needed = Vec::new();
        if configuration["managed_refresh"]["required"] == true {
            needed.push(json!({"job":"refresh-payload","reason":"Managed package files changed; existing setup choices stay in place."}));
        }
        if configuration["setup_assessment"]["assessment_due"] == true {
            needed.push(json!({"job":"assess-setup","reason":"A relevant setup source changed; consider only the affected concern."}));
        }
        return Ok(if needed.is_empty() {
            Value::Null
        } else {
            json!({"needed":needed,"request":configuration["setup_job_request"],"readiness_authority":"The responsible consumer owner still establishes readiness."})
        });
    }
    let job = selected["job"].as_str().unwrap();
    let mut choices = Vec::new();
    match job {
        "refresh-payload" => {
            for row in configuration["payload_choices"]
                .as_array()
                .into_iter()
                .flatten()
            {
                if row["status"] != "current" || row["recovery_request"].is_object() {
                    choices.push(json!({"subject":row["source"],"status":row["status"],"request":if row["recovery_request"].is_object(){&row["recovery_request"]}else{&row["request"]},"gap":row["reason"]}));
                }
            }
        }
        "expose-skill" | "expose-plugin" => {
            let key = if job == "expose-skill" {
                "skill_exposure"
            } else {
                "plugin_exposure"
            };
            choices.extend(configuration[key].as_array().into_iter().flatten().map(|r| json!({
                "subject":if job=="expose-skill" {&r["state"]["name"]}else{&r["state"]["host"]},
                "status":if job=="expose-skill" {&r["state"]["observed"]["status"]}else{&r["state"]["status"]},
                "gap":r["state"]["gap"],"expose_request":r["expose_request"],
                "remove_request":r["remove_request"],"recovery_request":r["recovery_request"]})));
        }
        "remove-adoption" => {
            choices.extend(configuration["adoption_requests"].as_array().into_iter().flatten().filter(|r|r["arguments"]["mode"] == "remove").map(|r|json!({"request":r,"effect":"Remove only the owned repository footprint; preserve custom and domain state."})));
            choices.extend(
                configuration["recovery_requests"]
                    .as_array()
                    .into_iter()
                    .flatten()
                    .map(|r| json!({"request":r,"effect":"Recover the exact prior effect."})),
            );
        }
        "configure-behavior" => {
            let choice = &configuration["selected_choice"];
            if choice["edit_request"].is_object() {
                choices.push(json!({"setting":choice["key"],"value":choice["value"],
                    "value_schema":choice["schema"],"request":choice["edit_request"],
                    "question":"What value should this setting have? Answer only value; Configuration retains its exact source and key and asks for write authorization before effects."}));
            } else {
                choices.extend(
                    configuration["choice_requests"]
                        .as_array()
                        .into_iter()
                        .flatten()
                        .map(|r| json!({"setting":r["arguments"]["key"],"request":r})),
                );
            }
        }
        "assess-setup" => {
            choices.push(json!({"request":configuration["concern_assessment_request"],"question":"What changed for this concern, what actually works, and what owner or action remains? Configuration supplies source bindings and consumer observations."}));
        }
        _ => {}
    }
    if let Some(wanted) = selected["choice"].as_str() {
        choices.retain(|choice| choice_subject(choice) == wanted);
        if choices.len() != 1 {
            return Err(CoreError::new(
                "Setup choice is not uniquely available in the current selected job; reobserve the job.",
            ));
        }
    }
    let concern = selected["concern"].as_str();
    let consumer = concern.map(|c| consumer_view(c,current)).unwrap_or(json!({"status":"not-checked","message":"Package and exposure effects establish their exact footprint; capability behavior needs its consumer's evidence."}));
    let mut result = json!({"job":job,"concern":selected["concern"],"scope":selected["scope"],
        "status":configuration["status"],"choices":choices,"consumer_verification":consumer,
        "consideration_complete":configuration["setup_assessment"]["review_complete"],
        "readiness_authority":"This setup consideration certifies no Assignment, module, launch or machine readiness."});
    if choices.len() > 1 {
        result["selection_request"] = configuration["setup_job_request"].clone();
    }
    Ok(result)
}

fn consumer_view(concern: &str, current: &Value) -> Value {
    let behavior = &current["configuration_behavior"];
    let observation = &behavior["observation"];
    match concern {
        "instructions" if observation["current"]["status"] == "source-context-delivered" => {
            json!({"status":"verified","owner":"startup-adapter","message":"The selected instruction source was delivered.","source":observation["selected_source"]})
        }
        "preferences" if behavior["status"] == "observed" => {
            json!({"status":"verified","owner":"configuration","message":"The selected scope's effective preferences were observed.","scope":behavior["setup_scope"]})
        }
        _ => {
            json!({"status":"owner-check-required","owner":observation["owner"],"message":crate::native_configuration_assessment::settlement(concern)["boundary"],"next_request":current["configuration_write"]["behavior_request"]})
        }
    }
}

pub(crate) fn attach_setup(target: &Path, invocation: &Value, result: &mut Value) {
    if invocation["source_owner"] != "configuration" {
        return;
    }
    let operation = invocation["operation_id"].as_str().unwrap_or("");
    let args = &invocation["arguments"]["request"]["arguments"];
    let key = args["key"].as_str().unwrap_or("");
    let job = match operation {
        crate::native_skill_exposure::OP => "expose-skill",
        crate::native_plugin_exposure::OP => "expose-plugin",
        crate::native_adoption::OP if args["mode"] == "remove" => "remove-adoption",
        crate::native_adoption::OP => "refresh-payload",
        _ if key == crate::native_configuration_assessment::KEY => "assess-setup",
        _ if key == "package.payload" => "refresh-payload",
        _ => "configure-behavior",
    };
    let committed = result["effect_outcome"]["status"] == "committed";
    let current = &result["continuation"]["result"];
    let consumer = if result["continuation_status"] != "current" {
        json!({"status":"unknown","message":"The effect is retained; current consumer observation is unavailable. Use exact reentry or recovery.","retry_effect":false})
    } else if let Some(concern) = concern(key) {
        let mut observed = current.clone();
        observed["configuration_behavior"] =
            observe(target, concern, current).unwrap_or(Value::Null);
        observed["configuration_behavior"]["setup_scope"] = json!(if args["source"]
            == ".agentic-workspace/config.local.toml"
        {
            "machine-local"
        } else {
            "repository"
        });
        consumer_view(concern, &observed)
    } else if job == "assess-setup" {
        let assessment = &current["configuration_write"]["setup_assessment"];
        let rows:Vec<_> = assessment["record"]["dispositions"].as_array().into_iter().flatten().map(|r|{
            json!({"concern":r["concern"],"status":if assessment["review_complete"] == true && matches!(r["status"].as_str(),Some("effective"|"already-effective")){"verified"}else if r["status"] == "owner-managed"{"owner-check-required"}else{"not-established"},
                "message":r["reason"],"next_action":r["resume"]})
        }).collect();
        json!({"status":"consideration-saved","consumers":rows,"message":"Only the listed current consumer observations establish behavior; other owners still establish their readiness."})
    } else {
        json!({"status":"not-checked","message":"The exact owned footprint was changed. Runtime capability behavior has not been certified."})
    };
    let gaps:Vec<_> = current["decision_packet"]["blockers"].as_array().into_iter().flatten()
        .map(|r|json!({"consequence_id":r["consequence_id"],"owner":r["owner"],"message":r["message"],"affects":r["affects"],"resolution":r["resolution"]})).collect();
    result["setup_result"] = json!({"job":job,"effect":if committed{"committed"}else{"not-established"},
        "changed_subject":args.get("source").or_else(||args.get("name")).or_else(||args.get("host")).cloned().unwrap_or(json!("owned repository footprint")),"consumer_verification":consumer,
        "remaining_gaps":gaps,"host_actions":result["value"]["host_actions"],"reentry":result["continuation"]["reentry"],
        "task_completion":"A setup effect supplies no task completion or independent review."});
}
pub(crate) fn declaration() -> Value {
    json!({"kind":READ,"result_kind":"agentic-workspace/configuration-behavior/v1","input_schema":{"$schema":"https://json-schema.org/draft/2020-12/schema","type":"object","additionalProperties":false,"required":["concern"],"properties":{"concern":{"enum":["instructions","diagnostics","assignment","modules","invocation","preferences"]},"scope":{"enum":["repository","machine-local"],"default":"repository"}}}})
}
pub(crate) fn concern(key: &str) -> Option<&'static str> {
    match key {
        "workspace.agent_instructions_file" => Some("instructions"),
        "session_logging.enabled" | "session_logging.detail" | "session_logging.path_mode" => {
            Some("diagnostics")
        }
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
