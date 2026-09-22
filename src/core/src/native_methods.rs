//! Internal bindings for existing native task-shaped consumers. Skill names and
//! routing remain in the one canonical skill registry; this table binds code.
use crate::{CoreError, digest};
use serde_json::{Value, json};

struct Binding {
    command: &'static str,
    implementation: &'static [u8],
    run: fn(Value) -> Result<Value, CoreError>,
}
const BINDINGS: &[Binding] = &[Binding {
    command: "resources",
    implementation: include_bytes!("native_resources.rs"),
    run: crate::native_resources::view,
}];

pub(crate) fn dispatch(input: &Value) -> Option<Result<Value, CoreError>> {
    let object = input.as_object().filter(|v| v.len() == 1)?;
    BINDINGS.iter().find_map(|binding| {
        object
            .get(binding.command)
            .map(|value| (binding.run)(value.clone()))
    })
}
pub(crate) fn descriptor(command: &str) -> Result<Value, CoreError> {
    let binding = BINDINGS
        .iter()
        .find(|b| b.command == command)
        .ok_or_else(|| CoreError::new("unsupported native executable command"))?;
    let contract: Value =
        serde_json::from_str(include_str!("../contracts/source_decision_contract.json"))
            .expect("checked command contract");
    let declaration = contract["native_cli"]["commands"]
        .as_array()
        .unwrap()
        .iter()
        .find(|row| row["name"] == command)
        .ok_or_else(|| CoreError::new("native method declaration unavailable"))?;
    Ok(
        json!({"command":command,"implementation_revision":digest(&json!(binding.implementation))?,"binding_revision":digest(&json!(include_bytes!("native_methods.rs").as_slice()))?,"contract_revision":digest(declaration)?}),
    )
}
