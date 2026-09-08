//! Existing direct-task semantic identity shared by native and adapter owners.
//! Request transport currentness is intentionally not this semantic subject.
use crate::{CoreError, digest};
use serde_json::{Value, json};
use std::collections::BTreeSet;

pub fn subject(task: &str, paths: &[String]) -> Result<Value, CoreError> {
    // Python str.split() includes these four Unicode separator controls in
    // addition to Unicode White_Space. Preserve the established owner bytes.
    let task = task
        .split(|c: char| c.is_whitespace() || ('\u{1c}'..='\u{1f}').contains(&c))
        .filter(|s| !s.is_empty())
        .collect::<Vec<_>>()
        .join(" ");
    let paths: BTreeSet<_> = paths.iter().collect();
    let revision = format!(
        "direct-task:{}",
        digest(&json!({"task":task,"paths":paths}))?
    );
    Ok(json!({"id":revision,"revision":revision}))
}

pub fn view(value: Value) -> Result<Value, CoreError> {
    let schema: Value = serde_json::from_str(include_str!(
        "../../../src/agentic_workspace/contracts/schemas/source_decision_input.schema.json"
    ))
    .expect("checked schema");
    let mut shape = schema["$defs"]["direct_task_subject_input"].clone();
    shape["$schema"] = schema["$schema"].clone();
    crate::schema_validator(&shape, "direct task subject")?
        .validate(&value)
        .map_err(|e| {
            CoreError::new(format!(
                "invalid direct task subject at {}",
                e.instance_path()
            ))
        })?;
    subject(
        value["task"].as_str().unwrap(),
        &value["paths"]
            .as_array()
            .unwrap()
            .iter()
            .map(|v| v.as_str().unwrap().to_owned())
            .collect::<Vec<_>>(),
    )
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn existing_python_identity_vectors_remain_exact() {
        let vectors: Value = serde_json::from_str(include_str!(
            "../../../tests/fixtures/direct_task_identity.json"
        ))
        .unwrap();
        for vector in vectors.as_array().unwrap() {
            let actual = view(vector["input"].clone()).unwrap();
            assert_eq!(actual["id"], vector["expected"], "{:?}", vector["input"]);
            assert_eq!(actual["revision"], actual["id"]);
        }
    }
    #[test]
    fn caller_authority_fields_are_not_subject_inputs() {
        assert!(view(json!({"task":"x","paths":[],"authenticated":true})).is_err());
    }
}
