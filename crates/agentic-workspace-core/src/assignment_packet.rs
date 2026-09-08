//! Canonical worker projection and packet integrity shared with retained adapters.
use crate::CoreError;
use serde_json::{Value, json};
use sha2::{Digest, Sha256};
fn text(v: &Value) -> String {
    v.as_str().unwrap_or("").trim().to_owned()
}
fn list(v: &Value) -> Value {
    json!(v.as_array().cloned().unwrap_or_default())
}
fn object(v: &Value) -> Value {
    json!(v.as_object().cloned().unwrap_or_default())
}
pub fn worker_context(packet: &Value) -> Value {
    let i = &packet["assignment_identity"];
    let mut context = json!({"kind":"agentic-workspace/assignment-worker-context/v1",
    "assignment":{"id":text(&packet["assignment_id"]),"revision":if text(&packet["assignment_revision"]).is_empty(){text(&i["revision"])}else{text(&packet["assignment_revision"])},"run_id":text(&packet["run_id"]),"target":if text(&packet["target"]).is_empty(){text(&i["target"])}else{text(&packet["target"])}},
    "intent":{"outcome":text(&i["human_intent"]),"task_class":text(&i["task_class"]),"role":text(&i["role"])},
    "scope":{"class":text(&i["scope_class"]),"allowed_paths":list(&i["allowed_paths"])},
    "effects":{"allowed":list(&i["allowed_effects"]),"prohibited":list(&i["prohibited_effects"])},
    "inputs":{"required":list(&i["required_inputs"]),"read_first":list(&i["read_first"]),"lazy_expansion_rule":"Read only these exact references first; request or resolve deeper context only when the assignment requires it."},
    "proof":{"obligation_id":text(&i["proof_obligation_id"]),"obligation_revision":text(&i["proof_obligation_revision"]),"worker_authority":false},
    "stop_conditions":list(&i["stop_conditions"]),"authority":{"semantic_source":"canonical-assignment-identity","claim_authority":object(&i["claim_authority"]),"scope_widening_allowed":false},"return_contract":object(&packet["return_contract"])});
    if !i["input_capsule"].is_null() {
        context["inputs"]["capsule"] = i["input_capsule"].clone();
    }
    if !i["task_requirements"].is_null() {
        context["inputs"]["task_requirements"] = i["task_requirements"].clone();
    }
    context
}
pub fn integrity(packet: &Value) -> Result<String, CoreError> {
    let mut subject = packet.clone();
    if !subject.is_object() {
        return Err(CoreError::new("assignment packet must be an object"));
    }
    subject["packet_integrity"] = json!("");
    for pointer in [
        "/return_contract/required_identity",
        "/worker_context/return_contract/required_identity",
    ] {
        if let Some(value) = subject.pointer_mut(pointer).filter(|v| v.is_object()) {
            value["packet_integrity"] = json!("");
        }
    }
    // Former TS/replacement packets used the same normalized object with UTF-8
    // string values. Recognize only its exact existing checksum; this supplies
    // no source custody or authority, and altered bytes cannot retain the seal.
    let legacy = format!(
        "sha256:{:x}",
        Sha256::digest(serde_json::to_vec(&subject).map_err(|e| CoreError::new(e.to_string()))?)
    );
    if packet["packet_integrity"] == legacy {
        return Ok(legacy);
    }
    Ok(format!(
        "sha256:{:x}",
        Sha256::digest(crate::proof_subject::compact_json(&subject)?.as_bytes())
    ))
}
pub fn seal(packet: &Value) -> Result<Value, CoreError> {
    let mut sealed = packet.clone();
    if !sealed.is_object() {
        return Err(CoreError::new("assignment packet must be an object"));
    }
    let mut contract = object(&sealed["return_contract"]);
    let mut fields = contract["required_fields"]
        .as_array()
        .cloned()
        .unwrap_or_default();
    for field in ["assignment_id", "packet_integrity", "result_delivery"] {
        if !fields.contains(&json!(field)) {
            fields.push(json!(field));
        }
    }
    contract["required_fields"] = json!(fields);
    contract["required_identity"] = json!({"assignment_id":sealed["assignment_id"],"assignment_revision":sealed["assignment_revision"],"run_id":sealed["run_id"],"target":sealed["target"],"packet_integrity":""});
    sealed["return_contract"] = contract;
    sealed["packet_integrity"] = json!("");
    sealed["worker_context"] = worker_context(&sealed);
    let hash = integrity(&sealed)?;
    sealed["packet_integrity"] = json!(hash);
    sealed["return_contract"]["required_identity"]["packet_integrity"] = json!(hash);
    sealed["worker_context"] = worker_context(&sealed);
    if integrity(&sealed)? != hash {
        return Err(CoreError::new(
            "assignment packet integrity did not stabilize",
        ));
    }
    Ok(sealed)
}
pub fn view(input: Value) -> Result<Value, CoreError> {
    match input["action"].as_str() {
        Some("seal") => seal(&input["packet"]),
        Some("integrity") => Ok(json!({"integrity":integrity(&input["packet"])?})),
        Some("worker-context") => Ok(worker_context(&input["packet"])),
        _ => Err(CoreError::new("unknown assignment packet projection")),
    }
}
