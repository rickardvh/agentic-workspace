//! Separation is a predicate over admitted owner facts, not authentication.
use crate::CoreError;
use serde_json::{Value, json};

fn known(value: &Value) -> Option<&str> {
    value.as_str().map(str::trim).filter(|value| {
        !value.is_empty()
            && !matches!(
                value.to_ascii_lowercase().as_str(),
                "unknown" | "unavailable" | "unspecified" | "none" | "n/a" | "not-applicable"
            )
    })
}

pub fn view(value: Value) -> Result<Value, CoreError> {
    let schema: Value = serde_json::from_str(include_str!(
        "../../../src/agentic_workspace/contracts/schemas/separation_of_duty.schema.json"
    ))
    .expect("checked schema");
    crate::schema_validator(&schema, "review separation")?
        .validate(&value)
        .map_err(|e| CoreError::new(format!("invalid review separation input: {e}")))?;
    let mode = value["required_mode"].as_str().unwrap();
    let kind = "agentic-workspace/separation-of-duty-gate/v1";
    if matches!(mode, "" | "none" | "not-applicable") {
        return Ok(json!({"kind":kind,"status":"not-applicable"}));
    }
    let reviewer = &value["reviewer"];
    if reviewer.is_null() || reviewer.as_object().is_some_and(|v| v.is_empty()) {
        return Ok(json!({"kind":kind,"status":"required","required_mode":mode}));
    }
    let implementer = &value["implementer"];
    let actors = known(&implementer["actor_id"]).zip(known(&reviewer["actor_id"]));
    let same_actor = actors.is_some_and(|(a, b)| a == b);
    let separate_actor = actors.is_some_and(|(a, b)| a != b);
    let fresh_context = reviewer["fresh_context"] == true;
    let distinct_provider = known(&implementer["provider"])
        .zip(known(&reviewer["provider"]))
        .is_some_and(|(a, b)| a != b);
    let human = reviewer["role"] == "human-approver";
    let accepted = match mode {
        "fresh-context" => fresh_context,
        "separate-actor" => separate_actor,
        "distinct-provider" => separate_actor && distinct_provider,
        "human" => human && separate_actor,
        _ => false,
    };
    Ok(
        json!({"kind":kind,"status":if accepted {"satisfied"}else{"blocked"},"required_mode":mode,
        "reviewer_role":reviewer["role"].as_str().unwrap_or(""),
        "independence":{"same_actor":same_actor,"fresh_context":fresh_context,"distinct_provider":distinct_provider,"human":human,
            "actor_identities_known":actors.is_some(),"separate_actor":separate_actor},
        "rule":"Implementer assertions, same-context self-review, and proof reruns never satisfy an independent-review requirement."}),
    )
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn identities_are_required_for_actor_separation() {
        for actor in [Value::Null, json!(""), json!("unknown"), json!(" ")] {
            for mode in ["separate-actor", "distinct-provider", "human"] {
                let value = json!({"required_mode":mode,"implementer":{"actor_id":actor,"provider":"one"},"reviewer":{"actor_id":"reviewer","provider":"two","role":"human-approver"}});
                assert_eq!(view(value).unwrap()["status"], "blocked");
            }
        }
    }
}
