//! Deterministic transport declarations; runtime capability remains host-owned.
use crate::CoreError;
use serde_json::{Value, json};
use std::collections::BTreeSet;
pub fn decode(profile: &Value) -> Result<Vec<Value>, CoreError> {
    let mut transports = Vec::new();
    if let Some(raw) = profile.get("transports") {
        let items = raw
            .as_array()
            .filter(|v| !v.is_empty())
            .ok_or_else(|| CoreError::new("transports must be a nonempty array"))?;
        let mut seen = BTreeSet::new();
        for item in items {
            let kind = item["kind"].as_str().unwrap_or("");
            let method = match kind {
                "internal" => "internal",
                "process" => "cli",
                "api" => "api",
                "manual" => "manual",
                "native" => "cli",
                _ => return Err(CoreError::new("unsupported transport kind")),
            };
            let key = if kind == "native" {
                format!("native:{}", item["adapter"].as_str().unwrap_or(""))
            } else {
                method.into()
            };
            if !seen.insert(key) {
                return Err(CoreError::new("duplicate transport method"));
            }
            let fields = item
                .as_object()
                .ok_or_else(|| CoreError::new("transport must be an object"))?;
            if fields.keys().any(|k| {
                !if kind == "native" {
                    ["kind", "adapter", "parameters", "timeout_seconds"].contains(&k.as_str())
                } else {
                    ["kind", "command", "output_mode", "timeout_seconds"].contains(&k.as_str())
                }
            }) {
                return Err(CoreError::new("unknown transport field"));
            }
            let command = item.get("command").cloned().unwrap_or(json!([]));
            let words = command
                .as_array()
                .filter(|v| v.iter().all(|w| w.as_str().is_some_and(|s| !s.is_empty())))
                .ok_or_else(|| CoreError::new("invalid transport command"))?;
            if matches!(kind, "process" | "api") && words.is_empty() {
                return Err(CoreError::new(format!(
                    "command is required for {kind} transport"
                )));
            }
            if matches!(kind, "internal" | "manual") && !words.is_empty() {
                return Err(CoreError::new(format!(
                    "command is not allowed for {kind} transport"
                )));
            }
            if kind == "native"
                && (!item["parameters"].is_object()
                    || !item["adapter"].as_str().is_some_and(|s| !s.is_empty()))
            {
                return Err(CoreError::new(
                    "native adapter identity and parameters required",
                ));
            }
            let timeout = item.get("timeout_seconds").cloned().unwrap_or(json!(1800));
            if !timeout.as_u64().is_some_and(|n| n > 0) {
                return Err(CoreError::new("invalid transport timeout"));
            }
            let output = item.get("output_mode").cloned().unwrap_or(json!("stdout"));
            if !matches!(output.as_str(), Some("stdout" | "json-file")) {
                return Err(CoreError::new("unsupported transport output mode"));
            }
            let mut row = json!({"kind":kind,"method":method,"command":command,"output_mode":output,"timeout_seconds":timeout,"readiness":if kind=="internal"{"runtime-required"}else{"configured"},"source":"canonical-transports"});
            if kind == "native" {
                row["adapter"] = item["adapter"].clone();
                row["parameters"] = item["parameters"].clone();
            }
            transports.push(row);
        }
    } else {
        let methods = profile["execution_methods"]
            .as_array()
            .filter(|v| !v.is_empty())
            .ok_or_else(|| CoreError::new("current or former transport declaration required"))?;
        let command = profile
            .get("dispatch_command")
            .cloned()
            .unwrap_or(json!([]));
        let words = command
            .as_array()
            .filter(|v| v.iter().all(|w| w.as_str().is_some_and(|s| !s.is_empty())))
            .ok_or_else(|| CoreError::new("invalid former dispatch command"))?;
        for method in methods {
            let method = method.as_str().unwrap_or("");
            let kind = match method {
                "internal" => "internal",
                "cli" => "process",
                "api" => "api",
                "manual" => "manual",
                _ => return Err(CoreError::new("invalid former execution method")),
            };
            let configured = matches!(method, "internal" | "manual") || !words.is_empty();
            transports.push(json!({"kind":kind,"method":method,"command":if matches!(method,"cli"|"api"){command.clone()}else{json!([])},"output_mode":profile.get("dispatch_output_mode").cloned().unwrap_or(json!("stdout")),"timeout_seconds":profile.get("dispatch_timeout_seconds").cloned().unwrap_or(json!(1800)),"readiness":if method=="internal"{"runtime-required"}else if configured{"configured"}else{"declared-unconfigured"},"source":"legacy-compatibility-decoder"}));
        }
    }
    Ok(transports)
}

/// Batch declarations through the same decoder; errors stay attached to each
/// source so callers preserve their existing validation order.
pub fn decode_sources(profiles: &Value) -> Result<Value, CoreError> {
    let profiles = profiles
        .as_object()
        .ok_or_else(|| CoreError::new("target sources must be an object"))?;
    let mut result = serde_json::Map::new();
    for (id, profile) in profiles {
        result.insert(
            id.clone(),
            match decode(profile) {
                Ok(rows) => json!({"transports":rows}),
                Err(error) => json!({"error":error.to_string()}),
            },
        );
    }
    Ok(json!({"sources":result}))
}
