//! Replacement semantics over independently admitted host/source-owner facts.
//! The execution configuration is opaque: the host owns which parameters it
//! can enforce. Public intention cannot supply the admission or host facts.
use crate::CoreError;
use serde::Deserialize;
use serde_json::{Value, json};
use sha2::{Digest, Sha256};

#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct OutcomeEvidence {
    admitted: Option<bool>,
    target_executed: Option<bool>,
    context_sufficient: Option<bool>,
    transport_sufficient: Option<bool>,
    worker_succeeded: Option<bool>,
    changed_intent: Option<bool>,
    mixed: Option<bool>,
    censored: Option<bool>,
    repo_owned: Option<bool>,
    failure_stage: Option<String>,
    stage: Option<String>,
    slice_id: Option<String>,
    semantic_revision: Option<String>,
    task_class: Option<String>,
    assignment_id: Option<String>,
    assignment_revision: Option<String>,
    run_id: Option<String>,
    target: Option<String>,
    source_owner: Option<String>,
}

/// Admitted owner facts, never inferred from a worker's success text or token count.
/// Unknown is distinct from an observed insufficiency and grants no ranking effect.
pub fn attribute_outcome(value: Value) -> Result<Value, CoreError> {
    let item: OutcomeEvidence = serde_json::from_value(value)
        .map_err(|error| CoreError::new(format!("invalid-outcome-evidence: {error}")))?;
    let stage = item
        .failure_stage
        .as_deref()
        .filter(|s| !s.is_empty())
        .or(item.stage.as_deref())
        .unwrap_or("");
    let responsibility = if item.admitted != Some(true) {
        "censored"
    } else if item.mixed == Some(true) || item.censored == Some(true) {
        "mixed-or-unknown"
    } else if item.changed_intent == Some(true) {
        "changed-human-intent"
    } else if matches!(stage, "planning" | "decomposition" | "task-specification") {
        "planning-decomposition"
    } else if item.context_sufficient == Some(false)
        || matches!(stage, "context" | "context-selection")
    {
        "context-selection"
    } else if item.transport_sufficient == Some(false)
        || matches!(stage, "transport" | "context-inflation")
    {
        "transport-context-inflation"
    } else if item.worker_succeeded == Some(true)
        && matches!(stage, "return" | "admission" | "integration")
    {
        "return-admission-integration"
    } else if item.worker_succeeded == Some(true)
        && matches!(stage, "proof" | "validation" | "review")
    {
        "proof-validation-review"
    } else if matches!(stage, "environment" | "tooling") {
        "environment-tooling"
    } else if item.target_executed == Some(true)
        && item.context_sufficient == Some(true)
        && item.transport_sufficient == Some(true)
        && (matches!(stage, "target" | "target-execution" | "execution")
            || (stage.is_empty() && item.worker_succeeded == Some(true)))
    {
        "target-execution"
    } else {
        "mixed-or-unknown"
    };
    let target_authoritative = responsibility == "target-execution";
    let repo_friction = item.repo_owned == Some(true)
        && matches!(
            responsibility,
            "context-selection" | "proof-validation-review" | "planning-decomposition"
        );
    Ok(json!({
        "kind":"agentic-workspace/orchestration-outcome-attribution/v1",
        "status":if matches!(responsibility, "mixed-or-unknown" | "censored") {"non-authoritative"} else {"attributed"},
        "responsibility":responsibility,
        "semantic_identity":{"slice_id":item.slice_id,"semantic_revision":item.semantic_revision,"task_class":item.task_class},
        "attempt_identity":{"assignment_id":item.assignment_id,"assignment_revision":item.assignment_revision,"run_id":item.run_id,"target":item.target},
        "routing_effect":{
            "target_evidence_allowed":target_authoritative,
            "target_evidence_owner":if target_authoritative {Some("target-outcome-evidence")} else {None},
            "source_owner_adaptation_pressure":repo_friction,
            "source_owner":if repo_friction {item.source_owner} else {None},
        },
        "hard_gates_remain_prior":true,"raw_trajectory_retained":false,
    }))
}

/// Source-owned feasibility is checked before any economic comparison. The
/// adapter owns parameter meanings; core binds their exact admitted identity.
#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct Configurations {
    work: Value,
    required_result_classes: Vec<String>,
    required_proof_classes: Vec<String>,
    independent_context: bool,
    #[serde(default)]
    required_execution_guarantees: Vec<String>,
    candidates: Vec<ExecutionCandidate>,
    selection: Option<ConfigurationSelection>,
}

#[derive(Deserialize, serde::Serialize)]
#[serde(deny_unknown_fields)]
struct ExecutionCandidate {
    id: String,
    target: String,
    transport: String,
    capability_revision: String,
    current: bool,
    authorized: bool,
    safe: bool,
    constructible: bool,
    result_classes: Vec<String>,
    proof_classes: Vec<String>,
    independent_context: bool,
    concurrency_available: bool,
    #[serde(default)]
    execution_guarantees: Vec<String>,
    execution: Value,
}

#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct ConfigurationSelection {
    revision: String,
    candidate: String,
}

pub fn configurations(value: Value) -> Result<Value, CoreError> {
    let input: Configurations =
        serde_json::from_value(value.clone()).map_err(|e| CoreError::new(e.to_string()))?;
    if !nonempty(&input.work["id"]) || !nonempty(&input.work["revision"]) {
        return Ok(blocked("assignment-work-identity-required"));
    }
    if input.required_execution_guarantees.len() > 32
        || input
            .required_execution_guarantees
            .iter()
            .any(|value| value.is_empty() || value.len() > 128)
    {
        return Ok(blocked("assignment-execution-guarantees-invalid"));
    }
    let mut seen = std::collections::BTreeSet::new();
    let mut rows = Vec::new();
    for mut candidate in input.candidates {
        if candidate.id.is_empty()
            || !seen.insert(candidate.id.clone())
            || candidate.target.is_empty()
            || candidate.transport.is_empty()
            || candidate.capability_revision.is_empty()
            || candidate.execution_guarantees.len() > 32
            || candidate
                .execution_guarantees
                .iter()
                .any(|value| value.is_empty() || value.len() > 128)
            || !candidate.execution.is_object()
        {
            return Ok(blocked("assignment-configuration-identity-invalid"));
        }
        // Comparable configuration facts exclude work/attempt and opaque lineage
        // references. Adapter parameters stay opaque and are only fingerprinted.
        let mut comparable_execution = candidate.execution.clone();
        let fields = comparable_execution.as_object_mut().unwrap();
        for key in [
            "comparison_context",
            "semantic_work",
            "source_revision",
            "authority_revision",
        ] {
            fields.remove(key);
        }
        if let Some(continuity) = fields.get_mut("continuity").and_then(Value::as_object_mut) {
            for key in ["reference", "semantic_scope", "lineage_revision"] {
                continuity.remove(key);
            }
        }
        let comparison = hash(&json!({
            "target":candidate.target,"transport":candidate.transport,
            "capability_revision":candidate.capability_revision,
            "execution":comparable_execution,
        }));
        candidate.execution["comparison_context"] = json!(comparison);
        let mut reasons = Vec::new();
        for (allowed, reason) in [
            (candidate.current, "capability-not-current"),
            (
                input
                    .required_execution_guarantees
                    .iter()
                    .all(|value| candidate.execution_guarantees.contains(value)),
                "required-execution-guarantee-unavailable",
            ),
            (candidate.authorized, "transport-not-authorized"),
            (candidate.safe, "independent-safety-ceiling"),
            (candidate.constructible, "execution-return-unconstructible"),
            (
                candidate.concurrency_available,
                "exclusive-lineage-unavailable",
            ),
            (
                !input.independent_context || candidate.independent_context,
                "independent-context-required",
            ),
            (
                input
                    .required_result_classes
                    .iter()
                    .all(|v| candidate.result_classes.contains(v)),
                "result-class-unavailable",
            ),
            (
                input
                    .required_proof_classes
                    .iter()
                    .all(|v| candidate.proof_classes.contains(v)),
                "proof-class-unavailable",
            ),
        ] {
            if !allowed {
                reasons.push(reason);
            }
        }
        rows.push(
            json!({"configuration":candidate,"eligible":reasons.is_empty(),"reasons":reasons}),
        );
    }
    // Selected topology, opaque parameters, readiness and semantic requirements
    // all participate. A choice cannot survive a material change or another work.
    let revision = hash(&json!({"work":input.work,"requirements":{
        "results":input.required_result_classes,"proof":input.required_proof_classes,
        "independent_context":input.independent_context,
        "execution_guarantees":input.required_execution_guarantees},"candidates":rows}));
    let selected = if let Some(selection) = input.selection {
        if selection.revision != revision {
            return Ok(blocked("assignment-configuration-choice-stale"));
        }
        let row = rows
            .iter()
            .find(|v| v["configuration"]["id"] == selection.candidate);
        match row {
            Some(row) if row["eligible"] == true => row["configuration"].clone(),
            _ => return Ok(blocked("assignment-configuration-choice-ineligible")),
        }
    } else {
        Value::Null
    };
    Ok(
        json!({"kind":"agentic-workspace/execution-configurations/v1","revision":revision,
        "candidates":rows,"selected":selected,"selection_authority":"acting-orchestrator",
        "claim_boundary":"feasibility only; no launch, proof or completion authority"}),
    )
}

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

/// Admit one current acting-orchestrator comparison after owner feasibility.
/// The judgment cannot create capability facts or erase unresolved alternatives.
pub fn comparative_assessment(input: Value) -> Result<Value, CoreError> {
    let revision = hash(
        &json!({"work":input["work"],"policy":input["policy"],"requirements":input["requirements"],"execution":input["execution"]}),
    );
    let execution = &input["execution"];
    let rows = execution["configurations"]["candidates"]
        .as_array()
        .cloned()
        .unwrap_or_default();
    let mut alternatives = Vec::new();
    for row in &rows {
        if row["eligible"] == true {
            alternatives.push(json!({"id":row["configuration"]["id"],"target":row["configuration"]["target"],"status":"eligible-configuration"}));
        }
    }
    let mut unresolved = Vec::new();
    for observation in execution["unavailable_adapters"]
        .as_array()
        .into_iter()
        .flatten()
    {
        unresolved.push(observation.clone());
    }
    for manual in execution["manual_targets"].as_array().into_iter().flatten() {
        if manual["source_policy_eligible"] == true
            && !alternatives.iter().any(|a| a["target"] == manual["target"])
        {
            unresolved.push(manual.clone());
        }
    }
    for item in &unresolved {
        let id = format!(
            "unresolved-target:{}",
            item["target"].as_str().unwrap_or("unknown")
        );
        if !alternatives.iter().any(|a| a["id"] == id) {
            alternatives.push(json!({"id":id,"target":item["target"],"status":"unresolved-target","gap":"current-execution-or-handoff-owner-required"}));
        }
    }
    let judgment = &input["judgment"];
    if !judgment.is_null() {
        let schema: Value = serde_json::from_str(include_str!(
            "../../../src/agentic_workspace/contracts/schemas/source_decision_input.schema.json"
        ))
        .expect("schema");
        let mut shape = schema["$defs"]["assignment_comparative_judgment"].clone();
        shape["$schema"] = schema["$schema"].clone();
        crate::schema_validator(&shape, "assignment comparative judgment")?
            .validate(judgment)
            .map_err(|e| CoreError::new(e.to_string()))?;
    }

    let mut selected = Value::Null;
    if !judgment.is_null() {
        if judgment["revision"] != revision {
            return Err(CoreError::new(
                "assignment comparative judgment stale; current work, policy, requirements or candidates changed",
            ));
        }
        selected = alternatives
            .iter()
            .find(|a| a["id"] == judgment["alternative"])
            .cloned()
            .ok_or_else(|| {
                CoreError::new("assignment comparative alternative is not currently admitted")
            })?;
        if let Some(row) = rows
            .iter()
            .find(|r| r["configuration"]["id"] == selected["id"] && r["eligible"] == true)
        {
            selected["configuration"] = row["configuration"].clone();
        }
        let prior = &execution["configurations"]["selected"];
        if !prior.is_null() && prior["id"] != selected["id"] {
            return Err(CoreError::new(
                "assignment comparison conflicts with current execution configuration choice",
            ));
        }
        if judgment["reason"]
            .as_str()
            .is_none_or(|s| s.trim().is_empty())
        {
            return Err(CoreError::new("assignment comparative reason required"));
        }
    }
    let binding = input["policy"]["binding"] == true;
    let ready = input["requirements"]["status"] == "resolved"
        && input["policy"]["enforceable"] == true
        && execution["gaps"].as_array().is_some_and(Vec::is_empty)
        && unresolved.is_empty();
    // Comparative uncertainty is retained with the exact judgment, not a
    // universal veto requiring false certainty. Unresolved capability, policy
    // and task requirements above remain hard admission boundaries.
    let local = selected["configuration"]["transport"] == "internal"
        && selected["target"] == input["policy"]["current_profile"]["name"];
    if !judgment.is_null() && input["policy"]["assignment_policy"] == "local-preferred" && !local {
        return Err(CoreError::new(
            "assignment comparison cannot override current local-preferred policy",
        ));
    }
    let status = if judgment.is_null() {
        "assessment-required"
    } else if !ready || selected["status"] == "unresolved-target" {
        "unresolved-assessment"
    } else if local {
        "assigned-current-target"
    } else {
        "assigned-nonlocal-handoff-required"
    };
    let assigned = matches!(
        status,
        "assigned-current-target" | "assigned-nonlocal-handoff-required"
    );
    Ok(
        json!({"kind":"agentic-workspace/assignment-decision/v1","revision":revision,"status":status,"alternatives":alternatives,"unresolved_alternatives":unresolved,
        "selected":selected,"judgment":judgment,"binding":binding,"local_assignment_satisfied":assigned&&local,
        "assignment_identity":if assigned{json!({"work":input["work"],"requirements_revision":input["requirements"]["revision"],"policy_revision":input["policy"]["revision"],"configuration_revision":execution["configurations"]["revision"],"assignment_decision_revision":hash(&json!({"assessment_revision":revision,"judgment":judgment,"selected":selected})),"selected":selected})}else{Value::Null},
        "claim_boundary":"Current comparative judgment only; no dispatch, sealed handoff, evidence, completion or override authority."}),
    )
}
