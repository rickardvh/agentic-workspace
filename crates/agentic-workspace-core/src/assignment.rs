//! Replacement semantics over independently admitted host/source-owner facts.
//! The execution configuration is opaque: the host owns which parameters it
//! can enforce. Public intention cannot supply the admission or host facts.
use crate::CoreError;
use serde::Deserialize;
use serde_json::{Value, json};
use sha2::{Digest, Sha256};

#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct Input {
    current: Value,
    work: Value,
    source: Value,
    admission: Option<Value>,
    eligibility: Option<Value>,
    execution: Value,
    request: Request,
}
#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct Request {
    assignment_revision: String,
    target: String,
    transport: String,
}
fn hash(value: &Value) -> String {
    format!(
        "sha256:{:x}",
        Sha256::digest(serde_json::to_vec(value).unwrap())
    )
}
fn blocked(reason: &str) -> Value {
    json!({"status":"blocked", "reason_code":reason, "implementation_allowed":false, "silent_local_fallback_allowed":false})
}
fn nonempty(v: &Value) -> bool {
    v.as_str().is_some_and(|s| !s.is_empty())
}
pub fn replace(value: Value) -> Result<Value, CoreError> {
    let input: Input = serde_json::from_value(value).map_err(|e| CoreError::new(e.to_string()))?;
    let Some(admission) = input.admission else {
        return Ok(blocked("assignment-override-authority-unavailable"));
    };
    let current = &input.current;
    let mut previous_subject = current.clone();
    if !previous_subject.is_object() {
        return Ok(blocked("assignment-not-current"));
    }
    previous_subject["packet_integrity"] = json!("");
    for field in ["return_contract", "worker_context"] {
        let contract = if field == "worker_context" {
            previous_subject
                .get_mut(field)
                .and_then(|v| v.get_mut("return_contract"))
        } else {
            previous_subject.get_mut(field)
        };
        if let Some(identity) = contract.and_then(|v| v.get_mut("required_identity")) {
            if !identity.is_object() {
                return Ok(blocked("assignment-return-contract-unavailable"));
            }
            identity["packet_integrity"] = json!("");
        }
    }
    // Existing packets use the host canonical JSON's ASCII escape form.
    let encoded = serde_json::to_string(&previous_subject).unwrap();
    let mut ascii = String::new();
    for c in encoded.chars() {
        if c.is_ascii() {
            ascii.push(c);
        } else {
            for unit in c.encode_utf16(&mut [0; 2]) {
                ascii.push_str(&format!("\\u{unit:04x}"));
            }
        }
    }
    let old_seal = if current.get("replacement").is_some() {
        hash(&previous_subject)
    } else {
        format!("sha256:{:x}", Sha256::digest(ascii.as_bytes()))
    };
    if admission["packet_integrity"] != current["packet_integrity"]
        || current["packet_integrity"] != old_seal
    {
        return Ok(blocked("assignment-override-packet-mismatch"));
    }

    if !current.is_object()
        || !nonempty(&current["assignment_id"])
        || !nonempty(&current["assignment_revision"])
    {
        return Ok(blocked("assignment-not-current"));
    }
    if admission["assignment_id"] != current["assignment_id"]
        || admission["assignment_revision"] != current["assignment_revision"]
        || admission["work"] != input.work
        || input.work["id"] != current["assignment_identity"]["slice_id"]
        || input.work["revision"] != current["assignment_identity"]["plan_revision"]
        || !nonempty(&input.work["revision"])
        || !nonempty(&input.work["id"])
    {
        return Ok(blocked("assignment-override-stale-work"));
    }
    if !nonempty(&input.source["reference"])
        || !nonempty(&input.source["revision"])
        || admission["source"] != input.source
    {
        return Ok(blocked("assignment-override-stale-source"));
    }
    if !input.execution.is_object()
        || admission["execution"] != input.execution
        || !nonempty(&input.execution["target"])
        || !nonempty(&input.execution["target_identity_ref"])
        || !nonempty(&input.execution["target_revision"])
        || !input.execution["adapter"].is_object()
        || !matches!(
            input.execution["transport"].as_str(),
            Some("internal" | "manual" | "cli" | "api")
        )
    {
        return Ok(blocked("assignment-replacement-configuration-mismatch"));
    }
    if input.request.assignment_revision != current["assignment_revision"]
        || input.request.target != input.execution["target"]
        || input.request.transport != input.execution["transport"]
    {
        return Ok(blocked("assignment-replacement-intention-mismatch"));
    }
    let Some(eligibility) = input.eligibility else {
        return Ok(blocked("assignment-replacement-eligibility-unavailable"));
    };
    if eligibility["owner"] != "assignment"
        || eligibility["eligible"] != true
        || eligibility["work"] != input.work
        || eligibility["execution"] != input.execution
        || eligibility["packet_integrity"] != current["packet_integrity"]
    {
        return Ok(blocked("assignment-replacement-ineligible"));
    }
    let revision = hash(
        &json!({"previous":current["assignment_revision"],"work":input.work,"source":input.source,"execution":input.execution,"eligibility":eligibility}),
    );
    let run = format!("replacement-{}", revision.trim_start_matches("sha256:"));
    // Preserve only the assignment's bounded semantic subject. Execution and
    // return identities are constructed afresh, never relabelled on an old seal.
    let mut identity = current["assignment_identity"].clone();
    if !identity.is_object() {
        return Ok(blocked("assignment-not-current"));
    }
    identity["target"] = input.execution["target"].clone();
    identity["target_identity_ref"] = input.execution["target_identity_ref"].clone();
    identity["target_revision"] = input.execution["target_revision"].clone();
    identity["dispatch_adapter"] = input.execution["adapter"].clone();
    identity["handoff_run_id"] = json!(run);
    identity["revision"] = json!(revision);
    identity["assignment_decision_revision"] = json!(revision);
    identity["proof_obligation_revision"] = json!(revision);
    let manual = input.execution["transport"] == "manual";
    identity["gate_status"] = json!(if manual {
        "handoff-required"
    } else {
        "dispatch-required"
    });
    identity["required_next_action"] = json!(if manual {
        "export-assigned-target"
    } else {
        "dispatch-assigned-target"
    });
    let required = json!({"assignment_id":current["assignment_id"],"assignment_revision":revision,"run_id":run,"target":input.execution["target"],"packet_integrity":""});
    let mut contract = current["return_contract"].clone();
    if !contract.is_object() {
        return Ok(blocked("assignment-return-contract-unavailable"));
    }
    contract["required_identity"] = required;
    let mut fields = contract["required_fields"]
        .as_array()
        .cloned()
        .unwrap_or_default();
    for field in [
        "assignment_id",
        "assignment_revision",
        "run_id",
        "target",
        "packet_integrity",
        "result_delivery",
    ] {
        if !fields.contains(&json!(field)) {
            fields.push(json!(field));
        }
    }
    contract["required_fields"] = json!(fields);
    let mut packet = json!({
        "kind":"agentic-workspace/assignment-export-packet/v1", "assignment_id":current["assignment_id"],
        "assignment_revision":revision, "run_id":run, "target":input.execution["target"], "transport":input.execution["transport"],
        "scope":identity["allowed_paths"], "assignment_identity":identity, "return_contract":contract,
        "authority_refs":current["authority_refs"],
        "replacement":{"previous_run_id":current["run_id"],"previous_revision":current["assignment_revision"],"work":input.work,"source":input.source,"execution":input.execution,"eligibility":eligibility},
        "dispatch_contract":{"transport":input.execution["transport"],"adapter_authority":"execution-only","semantic_authority":"assignment_identity","dispatch_input":"this exact packet","silent_local_fallback_allowed":false},
        "packet_integrity":""
    });
    let seal = hash(&packet);
    packet["packet_integrity"] = json!(seal);
    packet["return_contract"]["required_identity"]["packet_integrity"] = json!(seal);
    let proof = json!({
        "kind":"agentic-workspace/assignment-structural-proof-receipt/v1",
        "result":"passed", "verified_by":"aw", "assignment_id":packet["assignment_id"],
        "assignment_revision":revision,"assignment_decision_revision":revision,
        "mutation_baseline":packet["assignment_identity"]["mutation_baseline"],
        "packet_integrity":seal,"execution_configuration":input.execution,
        "eligibility_revision":hash(&eligibility),
        "claim_boundary":"current assignment identity, source admission and hard eligibility only; task proof and completion remain unproved"
    });
    Ok(
        json!({"status":"replaced","packet":packet,"structural_proof_receipt":proof,"implementation_allowed":false,"silent_local_fallback_allowed":false}),
    )
}

/// Both dispatch and export consume this exact current packet. This does not
/// authorize the host to launch; manual and automatic transport remain peers.
pub fn admit(value: Value) -> Result<Value, CoreError> {
    let packet = &value["packet"];
    let canonical = &value["canonical"];
    if !packet.is_object()
        || packet != canonical
        || !packet["return_contract"]["required_identity"].is_object()
    {
        return Ok(blocked("assignment-packet-not-current"));
    }
    let mut subject = packet.clone();
    let seal = packet["packet_integrity"].as_str().unwrap_or_default();
    subject["packet_integrity"] = json!("");
    subject["return_contract"]["required_identity"]["packet_integrity"] = json!("");
    if hash(&subject) != seal {
        return Ok(blocked("assignment-packet-integrity-mismatch"));
    }
    if packet["replacement"]["source"] != value["source"] {
        return Ok(blocked("assignment-override-stale-source"));
    }
    if packet["replacement"]["work"] != value["work"] {
        return Ok(blocked("assignment-override-stale-work"));
    }
    if packet["replacement"]["execution"] != value["execution"] {
        return Ok(blocked("assignment-replacement-configuration-mismatch"));
    }
    Ok(
        json!({"status":"current","packet":packet,"implementation_allowed":false,"silent_local_fallback_allowed":false}),
    )
}
