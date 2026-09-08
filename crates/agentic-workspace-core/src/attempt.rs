use crate::{CoreError, admit_invocation_value, digest, operation_result_value};
use serde::{Deserialize, Serialize};
use serde_json::{Value, json};

const KIND: &str = "agentic-workspace/effect-attempt/v1";

#[derive(Deserialize, Serialize)]
#[serde(deny_unknown_fields)]
struct Record {
    kind: String,
    attempt_id: String,
    invocation: Value,
    outcome: Option<Value>,
    record_revision: String,
}

fn attempt_id(invocation: &Value) -> Result<String, CoreError> {
    let effect = invocation["idempotency_key"]
        .as_str()
        .filter(|s| !s.is_empty())
        .ok_or_else(|| CoreError::new("attempt requires logical effect identity"))?;
    // No automatic second attempt exists. Uncertainty requires owner recovery.
    Ok(format!(
        "attempt:{}",
        digest(&json!({"effect": effect, "attempt": 1}))?
    ))
}

fn revision(record: &Record) -> Result<String, CoreError> {
    digest(
        &json!({"kind": record.kind, "attempt_id": record.attempt_id,
        "invocation": record.invocation, "outcome": record.outcome}),
    )
}

fn read_record(value: Value) -> Result<Record, CoreError> {
    let record: Record =
        serde_json::from_value(value).map_err(|e| CoreError::new(e.to_string()))?;
    if record.kind != KIND
        || record.attempt_id != attempt_id(&record.invocation)?
        || record.record_revision != revision(&record)?
    {
        return Err(CoreError::new(
            "retained attempt identity or content is invalid",
        ));
    }
    if let Some(outcome) = &record.outcome {
        operation_result_value(
            json!({"invocation": record.invocation, "outcome": outcome, "decision": null}),
        )?;
    }
    Ok(record)
}

/// The host supplies custody-proven retained evidence and serializes installation
/// of a newly returned record before starting its exact effect.
pub fn admit(value: Value) -> Result<Value, CoreError> {
    #[derive(Deserialize)]
    #[serde(deny_unknown_fields)]
    struct Input {
        decision: Value,
        invocation: Value,
        record: Option<Value>,
    }
    let input: Input = serde_json::from_value(value).map_err(|e| CoreError::new(e.to_string()))?;
    let record = input.record.map(read_record).transpose()?;
    admit_invocation_value(
        json!({"decision": input.decision, "invocation": input.invocation,
        "previous_invocation": record.as_ref().map(|record| &record.invocation)}),
    )?;
    let disposition = match &record {
        None => "execute",
        Some(record) if record.outcome.is_some() => "replay",
        Some(_) => "uncertain",
    };
    let record = match record {
        Some(record) => record,
        None => {
            let mut record = Record {
                kind: KIND.to_owned(),
                attempt_id: attempt_id(&input.invocation)?,
                invocation: input.invocation,
                outcome: None,
                record_revision: String::new(),
            };
            record.record_revision = revision(&record)?;
            record
        }
    };
    Ok(
        json!({"kind": "agentic-workspace/attempt-admission/v1", "disposition": disposition,
        "logical_effect_id": record.invocation["idempotency_key"], "attempt_id": record.attempt_id,
        "owner": record.invocation["source_owner"], "effects": record.invocation["effects"], "record": record}),
    )
}

/// Commit only a validated owner outcome to the exact retained attempt.
/// This function neither starts effects nor claims custody of supplied records.
pub fn commit(value: Value) -> Result<Value, CoreError> {
    #[derive(Deserialize)]
    #[serde(deny_unknown_fields)]
    struct Input {
        record: Value,
        outcome: Value,
    }
    let input: Input = serde_json::from_value(value).map_err(|e| CoreError::new(e.to_string()))?;
    let mut record = read_record(input.record)?;
    operation_result_value(
        json!({"invocation": record.invocation, "outcome": input.outcome, "decision": null}),
    )?;
    if record
        .outcome
        .as_ref()
        .is_some_and(|outcome| *outcome != input.outcome)
    {
        return Err(CoreError::new(
            "committed attempt cannot change its outcome",
        ));
    }
    record.outcome = Some(input.outcome);
    record.record_revision = revision(&record)?;
    Ok(serde_json::to_value(record).expect("record serializes"))
}
