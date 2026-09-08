//! Existing four-dimensional policy reduction; host/source admission is separate.
use crate::{CoreError, digest};
use serde_json::{Value, json};
pub fn merge(base: &Value, over: &Value) -> Value {
    let Some(source) = over.as_object() else {
        return over.clone();
    };
    let mut result = base.as_object().cloned().unwrap_or_default();
    for (key, value) in source {
        let old = result.get(key).cloned().unwrap_or(Value::Null);
        result.insert(
            key.clone(),
            if value.is_object() && old.is_object() {
                merge(&old, value)
            } else {
                value.clone()
            },
        );
    }
    json!(result)
}
pub fn resolve(input: &Value) -> Result<Value, CoreError> {
    let policy = &input["policy"];
    let assignment = policy["assignment_policy"]
        .as_str()
        .unwrap_or("local-preferred");
    if !["local-preferred", "best-fit-advisory", "required-best-fit"].contains(&assignment) {
        return Err(CoreError::new("unknown assignment policy"));
    }
    let transport = policy["transport_authority"].as_str();
    if transport.is_some_and(|v| !matches!(v, "manual" | "automatic")) {
        return Err(CoreError::new("unknown transport authority"));
    }
    let mode = transport
        .map(|v| if v == "automatic" { "auto" } else { "manual" })
        .unwrap_or_else(|| policy["mode"].as_str().unwrap_or("suggest"));
    if !["off", "manual", "suggest", "auto"].contains(&mode) {
        return Err(CoreError::new("unknown former delegation mode"));
    }
    let override_policy = policy["human_override_policy"]
        .as_str()
        .unwrap_or("explicit-only");
    if ![
        "explicit-only",
        "allowed-with-recorded-reason",
        "disallowed",
    ]
    .contains(&override_policy)
    {
        return Err(CoreError::new("unknown human override policy"));
    }
    let manual = match transport {
        Some("automatic") => "required-when-no-automatic-method",
        Some("manual") => "allowed",
        _ => policy["manual_transport_policy"]
            .as_str()
            .unwrap_or("allowed"),
    };
    if !["disabled", "allowed", "required-when-no-automatic-method"].contains(&manual) {
        return Err(CoreError::new("unknown manual transport policy"));
    }
    let current = policy["current_target"].as_str();
    let matches: Vec<&Value> = input["profiles"]
        .as_array()
        .into_iter()
        .flatten()
        .filter(|p| {
            current.is_some_and(|id| {
                p["name"] == id
                    || p["target_id"] == id
                    || p["aliases"]
                        .as_array()
                        .is_some_and(|v| v.iter().any(|v| v == id))
            })
        })
        .collect();
    let identities: std::collections::BTreeSet<&str> = matches
        .iter()
        .filter_map(|p| {
            p["target_id"]
                .as_str()
                .filter(|s| !s.is_empty())
                .or_else(|| p["name"].as_str())
        })
        .collect();
    let known = identities.len() == 1;
    let selected = if known {
        matches.first().copied().cloned().unwrap_or(Value::Null)
    } else {
        Value::Null
    };
    let safe = input["safe_to_auto_run_commands"] == true;
    let mut result = json!({"assignment_policy":assignment,"binding":assignment=="required-best-fit","enforceable":assignment!="required-best-fit"||known,"current_target":current,"current_target_status":if known{"known-profile"}else if current.is_some(){"unknown"}else{"not-configured"},"current_profile":if selected.is_null(){Value::Null}else{json!({"name":selected["name"],"target_id":selected["target_id"],"revision":digest(&selected)?})},"transport_authority":transport.unwrap_or(if mode=="auto"{"automatic"}else{"manual"}),"configured_mode":mode,"effective_mode":if mode=="auto"&&!safe{"suggest"}else{mode},"execution_permitted":mode=="auto"&&safe,"safe_to_auto_run_commands":safe,"human_override_policy":override_policy,"manual_transport_policy":manual,"source_boundary":"Canonical fields take precedence over former aliases; assignment never grants transport readiness or safety."});
    result["revision"] = json!(digest(&result)?);
    Ok(result)
}
