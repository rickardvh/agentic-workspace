//! Presentation and immutable transport over native owners, never an authority.
use crate::{CoreError, digest, native_frontier::Resolution, native_public};
use serde::Deserialize;
use serde_json::{Value, json};

const CARRIAGE: &str = "agentic-workspace/operating-carriage/v1";

/// Diagnostics follow the explicitly carried target even on failed admission;
/// this is no more authoritative than the ordinary caller-supplied target.
pub(crate) fn carried_target(input: &Value) -> Option<&str> {
    ["request", "invocation"].iter().find_map(|field| {
        (input[*field]["kind"] == CARRIAGE)
            .then(|| input[*field]["context"]["target"].as_str())
            .flatten()
    })
}

fn error(message: &str) -> CoreError {
    CoreError::new(format!(
        "{message}; recover with fresh start using explicit target/task/changed context"
    ))
}

#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct Carriage {
    kind: String,
    context: Value,
    envelopes: Vec<Value>,
}

/// Caller-local presentation assertions, deliberately removed before owner work.
#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct SourceAvailability {
    reference: String,
    revision: String,
    extent: String,
    content_revision: Option<String>,
    selector: Option<String>,
}

pub(crate) fn source_material(
    reference: &Value,
    bytes: &[u8],
    text: &str,
    selector: Option<&str>,
) -> Value {
    json!({"reference":reference,"revision":crate::native_intent::hash(bytes),
        "revision_scheme":"sha256-raw-bytes", "extent":if selector.is_some(){"exact-fragment"}else{"whole-source"},
        "selector":selector,"content_revision":crate::native_intent::hash(text.as_bytes())})
}

impl SourceAvailability {
    fn matches(&self, material: &Value) -> bool {
        if material["reference"] != self.reference || material["revision"] != self.revision {
            return false;
        }
        match self.extent.as_str() {
            "whole-source" => {
                self.selector.is_none()
                    && self
                        .content_revision
                        .as_ref()
                        .is_none_or(|r| r == &self.revision)
                    && matches!(
                        material["extent"].as_str(),
                        Some("whole-source" | "exact-fragment")
                    )
            }
            "exact-fragment" => {
                material["extent"] == "exact-fragment"
                    && self
                        .selector
                        .as_ref()
                        .is_some_and(|s| material["selector"] == *s)
                    && self
                        .content_revision
                        .as_ref()
                        .is_some_and(|r| material["content_revision"] == *r)
            }
            _ => false,
        }
    }
}

fn reference(context: &Value, selector: &str, envelope: &Value) -> Result<String, CoreError> {
    let hash = digest(
        &json!({"kind":CARRIAGE,"context":context,"selector":selector,"envelope":envelope}),
    )?;
    if envelope["kind"] == "agentic-workspace/lazy-owner-detail/v1" {
        Ok(format!(
            "detail:{}:{hash}",
            selector.strip_prefix('/').unwrap_or(selector)
        ))
    } else if selector.starts_with("request:") {
        Ok(format!(
            "request:{}:{hash}",
            selector.split(':').nth(1).unwrap()
        ))
    } else {
        Ok(hash)
    }
}

fn entry(context: &Value, selector: &str, envelope: &Value) -> Result<Value, CoreError> {
    Ok(
        json!({"reference":reference(context, selector, envelope)?,"selector":selector,"envelope":envelope}),
    )
}

fn entries(full: &Value, context: &Value) -> Result<Vec<Value>, CoreError> {
    let mut result = Vec::new();
    for selector in [
        "/decision_packet/primary_action",
        "/decision_packet/decision_request",
    ] {
        if let Some(value) = full.pointer(selector).filter(|v| v.is_object()) {
            result.push(entry(context, selector, value)?);
        }
    }
    for (index, question) in full["decision_packet"]["pending_consequences"]["decisions"]
        .as_array()
        .into_iter()
        .flatten()
        .enumerate()
    {
        if question != &full["decision_packet"]["decision_request"]
            && question["response_request"].is_object()
        {
            result.push(entry(
                context,
                &format!("/decision_packet/pending_consequences/decisions/{index}"),
                question,
            )?);
        }
    }
    if let Some(proposal) = full.pointer("/verification/claim_review/proposal") {
        let descriptor =
            json!({"kind":"agentic-workspace/lazy-owner-detail/v1","revision":digest(proposal)?});
        result.push(entry(
            context,
            "/verification/claim_review/proposal",
            &descriptor,
        )?);
    }
    if full["decision_packet"]["primary_action"].is_null() {
        for (index, action) in full["decision_packet"]["ready_actions"]
            .as_array()
            .into_iter()
            .flatten()
            .enumerate()
        {
            result.push(entry(
                context,
                &format!("/decision_packet/ready_actions/{index}"),
                action,
            )?);
        }
    }
    // Optional owner values are not carried. Bind exact lazy source identities;
    // reentry addresses that owner before any optional detail is constructed.
    for (key, value) in full.as_object().into_iter().flatten() {
        if key.starts_with('_') {
            continue;
        }
        let selector = format!("/{}", key.replace('~', "~0").replace('/', "~1"));
        let revision = match full["_detail_bindings"].get(key) {
            Some(revision) => revision.clone(),
            None => json!(digest(value)?),
        };
        let descriptor =
            json!({"kind":"agentic-workspace/lazy-owner-detail/v1","revision":revision});
        result.push(entry(context, &selector, &descriptor)?);
    }
    Ok(result)
}

fn request_entries(full: &Value, context: &Value) -> Result<Vec<Value>, CoreError> {
    let mut result = Vec::new();
    // Only native-returned request lists participate. Never search caller
    // material, provenance or action arguments for executable envelopes.
    fn request_list(value: &Value, found: &mut Vec<Value>, depth: usize) {
        if depth > 12 || found.len() >= 512 {
            return;
        }
        if let Some(items) = value.as_array() {
            for item in items {
                request_list(item, found, depth + 1);
            }
        } else if value["kind"] == "agentic-workspace/public-request/v1" && !found.contains(value) {
            found.push(value.clone());
        }
    }
    fn requests(value: &Value, found: &mut Vec<Value>, depth: usize) {
        if depth > 12 || found.len() >= 512 {
            return;
        }
        if let Some(object) = value.as_object() {
            for (key, child) in object {
                if key == "requests"
                    || key.ends_with("_requests")
                    || key == "request"
                    || key.ends_with("_request")
                {
                    request_list(child, found, depth + 1);
                } else if !matches!(
                    key.as_str(),
                    "arguments"
                        | "carriage"
                        | "creation_provenance"
                        | "update_provenance"
                        | "capability_contract"
                        | "decision_packet"
                ) {
                    requests(child, found, depth + 1);
                }
            }
        }
    }
    for (owner, value) in full.as_object().into_iter().flatten() {
        if owner.starts_with('_')
            || matches!(owner.as_str(), "capability_contract" | "decision_packet")
        {
            continue;
        }
        let mut found = Vec::new();
        requests(value, &mut found, 0);
        if owner == "setup_context" {
            // Selected native setup choices are row records, not request lists.
            // Index only their advertised request slots; do not widen discovery
            // into arbitrary arrays, caller material or nested choice metadata.
            for choice in value["choices"].as_array().into_iter().flatten().take(512) {
                for (key, request) in choice.as_object().into_iter().flatten() {
                    if key == "request" || key.ends_with("_request") {
                        request_list(request, &mut found, 1);
                    }
                }
            }
        }
        for request in found {
            if request["task_identity"] != full["current_work"] {
                continue;
            }
            let selector = format!("request:{owner}:{}", digest(&request)?);
            result.push(entry(context, &selector, &request)?);
        }
    }
    Ok(result)
}

// Route restrictions to existing public owner material. This is discovery,
// never an assertion that a request satisfies the restriction. In particular,
// an absent owner route cannot be replaced by a policy override or guessed key.
fn consequence_recovery(full: &Value, context: &Value) -> Result<Vec<Value>, CoreError> {
    fn has_request(value: &Value, owner: &str) -> bool {
        if value["kind"] == "agentic-workspace/public-request/v1" {
            return value["owner"] == owner;
        }
        match value {
            Value::Array(values) => values.iter().any(|v| has_request(v, owner)),
            Value::Object(values) => values.values().any(|v| has_request(v, owner)),
            _ => false,
        }
    }
    let mut recoveries = Vec::new();
    let requests = request_entries(full, context)?;
    for blocker in full["decision_packet"]["blockers"]
        .as_array()
        .into_iter()
        .flatten()
    {
        let requested = blocker["recovery"]
            .as_str()
            .and_then(|r| r.strip_prefix("public-request:"));
        let owner = requested
            .and_then(|kind| {
                requests
                    .iter()
                    .find(|r| r["envelope"]["request_kind"] == kind)
            })
            .and_then(|r| r["envelope"]["owner"].as_str())
            .or_else(|| {
                blocker["recovery"]
                    .as_str()
                    .and_then(|r| r.strip_prefix("public-owner:"))
            })
            .or_else(|| blocker["owner"].as_str());
        let Some(owner) = owner else { continue };
        let consequences = json!([{
            "consequence_id":blocker["consequence_id"], "affects":blocker["affects"]
        }]);
        let mut routes = Vec::new();
        if let Some(kind) = requested {
            for selected in &requests {
                if selected["envelope"]["owner"] == owner
                    && selected["envelope"]["request_kind"] == kind
                {
                    routes.push(json!({"selector":selected["selector"],
                        "reference":selected["reference"], "request_kind":kind}));
                }
            }
        }
        // Without a consequence-specific owner nomination, expose a bounded
        // selection step, never claim an arbitrary same-owner request is recovery.
        if requested.is_none() {
            for (key, value) in full.as_object().into_iter().flatten() {
                if matches!(
                    key.as_str(),
                    "decision_packet" | "capability_contract" | "decision_sources"
                ) {
                    continue;
                }
                if has_request(value, owner) {
                    let selector = format!("/{}", key.replace('~', "~0").replace('/', "~1"));
                    let selected = entries(full, context)?
                        .into_iter()
                        .find(|e| e["selector"] == selector)
                        .unwrap();
                    routes.push(json!({"selector":selector,"reference":selected["reference"]}));
                }
            }
            if routes.is_empty() {
                let mut selectors = vec![
                    "/decision_packet/primary_action".to_owned(),
                    "/decision_packet/decision_request".to_owned(),
                ];
                if full["decision_packet"]["primary_action"].is_null() {
                    selectors.extend(
                        (0..full["decision_packet"]["ready_actions"]
                            .as_array()
                            .map_or(0, Vec::len))
                            .map(|index| format!("/decision_packet/ready_actions/{index}")),
                    );
                }
                for selector in selectors {
                    let Some(envelope) = full.pointer(&selector).filter(|v| v.is_object()) else {
                        continue;
                    };
                    if (action_selector(&selector) && envelope["source_owner"] == owner)
                        || (selector == "/decision_packet/decision_request"
                            && envelope["owner"] == owner)
                    {
                        routes.push(json!({"selector":selector,"reference":reference(context, &selector, envelope)?}));
                    }
                }
            }
        }
        recoveries.push(json!({"owner":owner,"consequences":consequences,
            "status":if routes.is_empty(){"public-owner-route-unavailable"}else{"current-owner-route"},
            "selection":if requested.is_some() {json!({"status":"owner-nominated"})}
                else if !routes.is_empty() {json!({"status":"required",
                    "question":format!("Which current {owner} request addresses this restriction: {}?", blocker["message"].as_str().unwrap_or("unknown")),
                    "boundary":"Select only a request whose stated scope addresses this consequence. If none does, report the bounded resolution gap; same owner identity alone is insufficient."})}
                else {Value::Null},
            "routes":routes,
            "authority":"Discovery only; restrictions remain until the current owner admits their resolution."}));
    }
    Ok(recoveries)
}

fn reconcile_restriction_routes(value: &mut Value, recovery: &[Value]) {
    fn visit(value: &mut Value, recovery: &[Value]) {
        match value {
            Value::Array(items) => {
                for item in items {
                    visit(item, recovery);
                }
            }
            Value::Object(object) => {
                let nominated = object
                    .get("recovery")
                    .and_then(Value::as_str)
                    .is_some_and(|r| {
                        r.starts_with("public-request:") || r.starts_with("public-owner:")
                    });
                if (object
                    .get("resolution")
                    .is_some_and(|r| r == "owner-resolution-unavailable")
                    || nominated)
                    && let Some(id) = object.get("consequence_id").filter(|id| id.is_string())
                    && let Some(route) = recovery.iter().find(|r| {
                        r["consequences"]
                            .as_array()
                            .is_some_and(|items| items.iter().any(|c| &c["consequence_id"] == id))
                    })
                {
                    object.insert(
                        "resolution".into(),
                        json!(if route["status"] == "current-owner-route" {
                            "current-owner-route"
                        } else {
                            "owner-resolution-unavailable"
                        }),
                    );
                }
                for (key, child) in object {
                    if !matches!(key.as_str(), "arguments" | "source_requests" | "carriage") {
                        visit(child, recovery);
                    }
                }
            }
            _ => (),
        }
    }
    visit(value, recovery);
}

fn same_pending_action(pending: &Value, invocation: &Value) -> bool {
    if pending == invocation {
        return true;
    }
    if invocation["kind"] != "agentic-workspace/operation-invocation/v1" {
        return false;
    }
    let Some(mut proposal) = invocation.as_object().cloned() else {
        return false;
    };
    // Native preparation adds the invocation kind and renames these custody
    // fields. Reverse only that mapping for exact presentation comparison;
    // distinct scope, sources, arguments or unknown material must remain visible.
    proposal.remove("kind");
    for (prepared, pending) in [
        ("expected_dependency_revision", "dependency_revision"),
        ("idempotency_key", "logical_effect_id"),
    ] {
        let Some(value) = proposal.remove(prepared) else {
            return false;
        };
        proposal.insert(pending.to_owned(), value);
    }
    pending == &Value::Object(proposal)
}

fn compact(full: &Value, context: &Value, carried: bool) -> Result<Value, CoreError> {
    if !full["decision_packet"].is_object() {
        return Ok(full.clone()); // Compatibility/recovery is already bounded.
    }
    let mut packet = full["decision_packet"].clone();
    let object = packet.as_object_mut().unwrap();
    for key in ["operation_revisions", "owner_states", "capability_revision"] {
        object.remove(key);
    }
    if !full["decision_packet"]["primary_action"].is_null() {
        object.remove("ready_actions"); // Only the duplicate single action.
    }
    // Blockers appear once. Peer actions and questions remain visible: selection
    // never erases a competing restriction or unresolved judgment.
    if let Some(pending) = packet["pending_consequences"].as_object_mut() {
        pending.remove("blockers");
    }
    let mut refs = serde_json::Map::new();
    for item in entries(full, context)? {
        let selector = item["selector"].as_str().unwrap();
        if selector.starts_with("request:") {
            continue;
        }
        refs.insert(selector.to_owned(), item["reference"].clone());
        if carried && action_selector(selector) {
            // Effect-bearing arguments stay visible until owners expose a
            // separate decision-bearing summary. Only validation is carried.
            let mut action = item["envelope"].clone();
            if let Some(object) = action.as_object_mut() {
                for field in [
                    "source_requests",
                    "expected_dependency_revision",
                    "capability_revision",
                    "owner_revision",
                    "input_revision",
                    "idempotency_key",
                ] {
                    object.remove(field);
                }
                object.insert("reference".into(), item["reference"].clone());
                object.insert(
                    "kind".into(),
                    json!("agentic-workspace/carried-action-view/v1"),
                );
                object.insert("transport".into(), json!("use-exact-carried-envelope"));
            }
            *packet
                .pointer_mut(selector.strip_prefix("/decision_packet").unwrap())
                .unwrap() = action;
        }
        if decision_selector(selector) {
            let question = packet
                .pointer_mut(selector.strip_prefix("/decision_packet").unwrap())
                .unwrap();
            question["reference"] = item["reference"].clone();
            if !carried {
                continue;
            }
            // All owner-provided material remains decision-visible. Only the
            // immutable public-request identity is removed from model output.
            question["request_material"] = question["response_request"]["arguments"].clone();
            question.as_object_mut().unwrap().remove("response_request");
            question["reference"] = item["reference"].clone();
            if question["choices"]
                .as_array()
                .is_some_and(|v| !v.is_empty())
            {
                // The public answer helper accepts exactly one returned choice.
                // The full request schema mostly describes immutable material;
                // it remains in exact detail and participates in admission.
                question.as_object_mut().unwrap().remove("response_schema");
                question["answer_input"] = json!("one returned choice id");
            }
        }
    }
    // Prepared actions already appear above. Remove their raw proposal copies,
    // retaining every unadmitted or materially different peer. Compare against
    // native envelopes before carried presentation replaces them with views.
    let admitted = std::iter::once(&full["decision_packet"]["primary_action"])
        .chain(
            full["decision_packet"]["ready_actions"]
                .as_array()
                .into_iter()
                .flatten(),
        )
        .filter(|action| !action.is_null())
        .collect::<Vec<_>>();
    if let Some(values) = packet["pending_consequences"]["actions"].as_array_mut() {
        values.retain(|value| {
            !admitted
                .iter()
                .any(|action| same_pending_action(value, action))
        });
    }
    if let Some(values) = packet["pending_consequences"]["decisions"].as_array_mut() {
        values.retain(|value| value != &full["decision_packet"]["decision_request"]);
    }
    let proposal_reference = refs.get("/verification/claim_review/proposal").cloned();
    if let Some(reference) = proposal_reference {
        let detail = json!({"reference":reference,
            "use":"Read the exact proposal only when a source, obligation or evidence detail is needed to judge this claim. The whole binding remains currentness-checked on answer."});
        if packet["decision_request"]["id"] == "verification-claim-review" {
            packet["decision_request"]["material"]["proposal_detail"] = detail.clone();
        }
        for question in packet["pending_consequences"]["decisions"]
            .as_array_mut()
            .into_iter()
            .flatten()
        {
            if question["id"] == "verification-claim-review" {
                question["material"]["proposal_detail"] = detail.clone();
            }
        }
    }
    let mut result = json!({"decision_packet":packet,"detail_refs":refs,
        "reentry":context,
        "detail_rule":"Exact optional detail: send its reference with the same explicit work context, or use carried/full projection. References grant no authority and are freshly reobserved."});
    if let Some(assignment) = assignment_question(full, context)? {
        result["assignment_context"] = assignment;
    }
    if full["setup_context"].is_object() {
        fn references(value: &mut Value, entries: &[Value]) {
            if value["kind"] == "agentic-workspace/public-request/v1" {
                if let Some(entry) = entries.iter().find(|e| e["envelope"] == *value) {
                    *value = json!({"reference":entry["reference"],"answer_shape":value["arguments"],
                        "use":"Send current reentry with this reference and only the bounded semantic answer. Selection grants no effect authority."});
                }
            } else if let Some(object) = value.as_object_mut() {
                for child in object.values_mut() {
                    references(child, entries);
                }
            } else if let Some(array) = value.as_array_mut() {
                for child in array {
                    references(child, entries);
                }
            }
        }
        let mut setup = full["setup_context"].clone();
        references(&mut setup, &request_entries(full, context)?);
        result["setup_context"] = setup;
    }
    if full["planning"]["selected_owner"].is_object() {
        let mut planning = json!({"status":full["planning"]["status"],
            "owner_ref":full["planning"]["selected_owner"]["ref"],
            "authority":"Current Planning continuation only; assignment, evidence and completion remain separate."});
        if let Some(request) = request_entries(full, context)?
            .iter()
            .find(|r| r["envelope"]["request_kind"] == crate::native_planning_update::KIND)
        {
            planning["next_step"] = json!({"reference":request["reference"],
                "question":"What durable intent, scope, progress, remaining work or next action changed? Supply only those semantic fields; Planning preserves and validates the complete current record.",
                "answer_shape":{"material":{"next_action":"<changed next action, or other changed material fields>"}},
                "use":"Use current reentry with this reference and the semantic answer. Unchanged record fields and current owner identity are supplied by Planning."});
        }
        result["planning_context"] = planning;
    }
    let verification = &full["verification"];
    let claim = &verification["claim_review"];
    if claim["status"] == "not-requested"
        && verification["evidence"]
            .as_array()
            .is_some_and(|evidence| !evidence.is_empty())
    {
        let request = &claim["request"];
        let selector = format!("request:verification:{}", digest(request)?);
        let evidence: Vec<_> = verification["evidence"]
            .as_array()
            .unwrap()
            .iter()
            .map(|entry| {
                json!({"reference":entry["reference"],
                    "status":entry["runtime_admission"]["status"],
                    "gaps":entry["runtime_admission"]["gaps"],
                    "freshness":entry["evidence_freshness"],
                    "checked_scope":entry["checked_scope"],
                    "proof_sufficient":entry["receipt_admission"]["proof_sufficient"]})
            })
            .collect();
        result["verification_context"] = json!({
            "evidence":evidence,
            "authority":"Current evidence for semantic consideration only; source, required proof and independent review remain binding.",
            "next_step":{
                "reference":reference(context, &selector, request)?,
                "question":"Does the current evidence support the requested result? Judge sufficiency and give the reason; Verification carries the selected evidence into the bounded claim proposal.",
                "answer_shape":{"disposition":"<satisfied or insufficient>","reason":"<judgment against the requested result and current evidence>"},
                "use":"Use current reentry with this exact reference and only the semantic answer. Inspect the resulting bounded claim question before confirming; evidence presence and a passed command alone do not grant completion."}});
    }
    if let Some(advice) = full["memory"].get("advisory_context") {
        result["advisory_context"] = advice.clone();
    }
    let candidates = &full["memory"]["candidates"];
    if candidates["selected"]
        .as_array()
        .is_some_and(|s| !s.is_empty())
        || candidates["publication_request"].is_object()
        || candidates["completion_prepared"] == true
    {
        let mut budget = 16384usize;
        let observations = candidates["selected"].as_array().into_iter().flatten().map(|row| {
            let size = serde_json::to_vec(row).unwrap().len();
            if size <= budget.min(4096) { budget -= size; row.clone() }
            else { json!({"id":row["observation"]["id"],"status":"selected-detail-deferred","currentness":row["currentness"]}) }
        }).collect::<Vec<_>>();
        result["candidate_context"] = json!({"observations":observations,
            "reference":result["detail_refs"]["/memory"],"next":"Compare scopes and current sources. Use the returned next_step only when justified; defer or deliberate discard may be sufficient. Publication and candidate subtraction remain separate effects.",
            "authority":"Unconfirmed local evidence for consideration; no current-state, policy or task-custody authority."});
        if candidates["completion_prepared"] == true {
            if let Some(action) = entries(full, context)?.into_iter().find(|entry| {
                action_selector(entry["selector"].as_str().unwrap())
                    && entry["envelope"]["source_owner"] == "memory"
                    && entry["envelope"]["operation_id"] == crate::native_memory_candidates::OP
                    && entry["envelope"]["arguments"]["request"]["arguments"]["operation"]
                        == "complete"
            }) {
                result["candidate_context"]["next"] = json!(
                    "Publication is committed. Inspect and invoke the separately prepared cleanup action to subtract only the absorbed candidates."
                );
                result["candidate_context"]["next_step"] = json!({"operation":"complete",
                    "reference":action["reference"],"transport":"invoke",
                    "validation":"current-publication-and-candidates",
                    "use":"Publication custody, source/dependency validity and the exact candidate state have already been rechecked for this cleanup action. Inspect the action and invoke this reference with this continuation's context/carriage; no Memory or activity reread is needed to reconstruct confirmation. Changed work or source still requires fresh resolution and is rechecked before subtraction."});
            }
        } else {
            let request = if candidates["publication_request"].is_object() {
                Some(&candidates["publication_request"])
            } else {
                candidates["requests"]
                    .as_array()
                    .into_iter()
                    .flatten()
                    .find(|r| r["arguments"]["operation"] == "consolidate")
            };
            if let Some(request) = request {
                let selector = format!("request:memory:{}", digest(request)?);
                result["candidate_context"]["next_step"] = json!({
                "operation":if request["request_kind"] == "memory/capture-advisory/v1" {"publish"} else {"consolidate"},
                "reference":reference(context, &selector, request)?,
                "answer_shape":if request["request_kind"] == "memory/capture-advisory/v1" { json!({}) } else {
                    json!({"advisory_material":{"id":"<bounded identity>","lesson":"<supported reusable conclusion>","rationale":"<future value>","dependency_paths":["<current validity source>"],"routes_from":["<deliberate path cue>"],"semantic_routes":["<existing activity cue>"]}})
                },
                "use":if request["request_kind"] == "memory/capture-advisory/v1" {
                    "Use this exact reference with current context/carriage and an empty object answer to submit the filled material for the publisher's confirmation question."
                } else {
                    "Use this exact reference with current context/carriage and the small answer shape. Choose routes_from or semantic_routes deliberately; candidate origins are already carried. An optional authored origin must include producer, reference and coverage (bounded, partial or unknown). Defer or justified discard may be sufficient."
                }});
                if let Some(question) = candidates.get("next") {
                    result["candidate_context"]["judgment"] = question.clone();
                }
            }
        }
    }
    if let Some(maintenance) = context.get("maintenance") {
        result["reentry"]["maintenance"] = maintenance.clone();
    }
    if let Some(material) = full.get("material") {
        result["material"] = material.clone();
    }
    if let Some(activation) = full.get("activation") {
        result["activation"] = activation.clone();
    }
    let retention = &full["memory"]["terminal_retention"];
    if matches!(
        retention["status"].as_str(),
        Some("judgment-required" | "recovery-required")
    ) {
        result["memory_retention"] = json!({
            "status":retention["status"],
            "candidate_count":retention["sources"].as_object().map_or(0, |s| s.len()),
            "reference":result["detail_refs"]["/memory"],
            "authority":"Current Memory disposition required; discovery grants no deletion authority."
        });
    }
    let retention = &full["planning"]["terminal_retention"];
    if matches!(
        retention["status"].as_str(),
        Some("judgment-required" | "recovery-required")
    ) {
        result["planning_retention"] = json!({
            "status":retention["status"],
            "candidate_count":retention["sources"].as_object().map_or(0, |s| s.len()),
            "reference":result["detail_refs"]["/planning"],
            "authority":"Current Planning disposition required; discovery grants no deletion authority."
        });
    }
    let retention = &full["verification"]["retention"];
    if matches!(
        retention["status"].as_str(),
        Some("judgment-required" | "recovery-required")
    ) {
        result["proof_retention"] = json!({"status":retention["status"],"candidate_count":retention["sources"].as_object().map_or(0,|s|s.len()) + retention["repository_transfers"].as_object().map_or(0,|s|s.len()),"reference":result["detail_refs"]["/verification"],"authority":"Current Verification disposition required; discovery grants no deletion or proof authority."});
    }
    let recovery = consequence_recovery(full, context)?;
    if !recovery.is_empty() {
        reconcile_restriction_routes(&mut result, &recovery);
        result["consequence_recovery"] = json!(recovery);
    }
    // A selected leaf already establishes which procedure is useful. Keep its
    // exact refs visible so compact consumers need no discovery/detail hop.
    // Bodies stay lazy and these source observations grant no effect authority.
    if full["decision_packet"]["semantic_task_routes"]["status"] == "current"
        && full["decision_packet"]["semantic_task_routes"]["posture"] == "selected"
        && let Some(sources) = full["semantic_routes"]["discovery"]["detail"]["sources"].as_array()
    {
        result["procedure_refs"] = json!(sources);
    }
    Ok(result)
}

fn assignment_question(full: &Value, context: &Value) -> Result<Option<Value>, CoreError> {
    let requirements = &full["task_requirements"];
    if requirements["status"].is_null() || requirements["status"] == "not-applicable" {
        return Ok(None);
    }
    let assessment = &requirements["assignment"]["result"];
    let mut result = json!({"status":requirements["implementation_admission"]["status"],
        "local_continuation_allowed":requirements["implementation_admission"]["local_continuation_allowed"],
        "comparison_status":assessment["status"],
        "determination":assessment["determination"],
        "authority":"Current Assignment admission only; proof, review and task completion remain separate."});
    let (kind, question, answer) = if requirements["status"] != "resolved" {
        result["target_scope_questions"] = requirements["target_scope_questions"].clone();
        result["source_work"] = requirements["source_work"].clone();
        (
            "assignment/judge-task-requirements/v1",
            "What result and proof does this work require, and which configured task restrictions apply? Source identities and constraints are already supplied by the owner.",
            json!({"role":"executor","required_result_classes":["<required result class, e.g. unapplied-patch>"],"required_proof_classes":[],"target_scope":{}}),
        )
    } else if matches!(
        assessment["status"].as_str(),
        Some("assessment-required" | "unresolved-assessment")
    ) && assessment["alternatives"]
        .as_array()
        .is_some_and(|a| !a.is_empty())
    {
        result["requirements"] = requirements["result"]["requirements"].clone();
        result["alternatives"] = assessment["alternatives"].clone();
        result["unresolved_alternatives"] = assessment["unresolved_alternatives"].clone();
        result["execution_gaps"] = requirements["execution_configurations"]["gaps"].clone();
        (
            "assignment/assess-best-fit/v1",
            "Which current alternative best fits the required outcome? Compare capability, preparation, coupling and repair cost using the supplied evidence and standing preferences; loaded context alone does not settle the choice. Keep real uncertainty explicit.",
            json!({"alternative":"<returned alternative id>","reason":"<material comparative tradeoff>","uncertainties":[]}),
        )
    } else if matches!(
        assessment["status"].as_str(),
        Some("assigned-current-target" | "assigned-nonlocal-handoff-required")
    ) {
        result["selected"] =
            json!({"id":assessment["selected"]["id"],"target":assessment["selected"]["target"]});
        return Ok(Some(result));
    } else {
        result["requirements"] = requirements["result"]["requirements"].clone();
        result["unresolved_alternatives"] = assessment["unresolved_alternatives"].clone();
        result["execution_gaps"] = requirements["execution_configurations"]["gaps"].clone();
        result["ineligible_configurations"] = json!(requirements["execution_configurations"]["configurations"]["candidates"]
            .as_array().into_iter().flatten().filter(|r| r["eligible"] != true)
            .map(|r| json!({"id":r["configuration"]["id"],"reasons":r["reasons"],
                "result_classes":r["configuration"]["result_classes"],"proof_classes":r["configuration"]["proof_classes"]})).collect::<Vec<_>>());
        (
            "assignment/judge-task-requirements/v1",
            "No currently admitted comparison can settle this work. Inspect the current requirements and capability gaps. Correct only a mis-stated requirement or unresolved task restriction; retain real requirements and use the owner's recovery when capability is missing. No local fallback is authorized.",
            json!({"required_result_classes":"<the actual required classes>","required_proof_classes":"<the actual required proof classes>","target_scope":{}}),
        )
    };
    let requests = request_entries(full, context)?;
    if let Some(request) = requests
        .iter()
        .find(|r| r["envelope"]["request_kind"] == kind)
    {
        result["next_step"] = json!({"reference":request["reference"],"question":question,
            "answer_shape":answer,
            "use":"Send the fields of reentry unchanged at the top level, plus reference and answer containing only the requested fields. Optional carriage is equivalent. The owner reobserves current sources and preserves earlier answers; no request identities or handoff envelopes need inspection."});
    }
    Ok(Some(result))
}

fn action_selector(selector: &str) -> bool {
    selector == "/decision_packet/primary_action"
        || selector
            .strip_prefix("/decision_packet/ready_actions/")
            .is_some_and(|index| {
                index
                    .parse::<usize>()
                    .is_ok_and(|value| value.to_string() == index)
            })
}

fn decision_selector(selector: &str) -> bool {
    selector == "/decision_packet/decision_request"
        || selector
            .strip_prefix("/decision_packet/pending_consequences/decisions/")
            .is_some_and(|index| index.parse::<usize>().is_ok_and(|v| v.to_string() == index))
}

fn normalize_context(mut value: Value) -> Result<Value, CoreError> {
    if !value.is_object() {
        return Err(error("expected operating input object"));
    }
    let target = value["target"]
        .as_str()
        .ok_or_else(|| error("target missing"))?;
    value["target"] = json!(std::fs::canonicalize(target).map_err(|e| error(&e.to_string()))?);
    if value.get("task").is_none() {
        value["task"] = json!("");
    }
    if value.get("changed").is_none() {
        value["changed"] = json!([]);
    }
    value.as_object_mut().unwrap().remove("invocation");
    if value["request"].is_null() {
        value.as_object_mut().unwrap().remove("request");
    }
    Ok(value)
}

fn select_entry(full: &Value, context: &Value, selected: &Value) -> Result<Value, CoreError> {
    let candidates = if selected.as_str().is_some_and(|s| s.starts_with("request:")) {
        request_entries(full, context)?
    } else {
        entries(full, context)?
    };
    let mut matches: Vec<_> = candidates
        .into_iter()
        .filter(|entry| entry["reference"] == *selected)
        .collect();
    if matches.len() != 1 {
        return Err(error("unknown, ambiguous, or stale operating reference"));
    }
    let selected_entry = matches.remove(0);
    let selector = selected_entry["selector"]
        .as_str()
        .ok_or_else(|| error("invalid selector"))?;
    if json!(reference(context, selector, &selected_entry["envelope"])?) != *selected {
        return Err(error("altered operating reference"));
    }
    Ok(selected_entry)
}

fn resolve_owner_reference(
    full: &Value,
    context: &Value,
    identity: &Value,
) -> Result<Value, CoreError> {
    #[derive(Deserialize)]
    #[serde(deny_unknown_fields)]
    struct Identity {
        kind: String,
        owner: String,
        id: String,
    }
    let wanted: Identity = serde_json::from_value(identity.clone())
        .map_err(|_| error("owner identity requires only kind, owner and id"))?;
    if !matches!(wanted.kind.as_str(), "request" | "action" | "question")
        || wanted.owner.is_empty()
        || wanted.id.is_empty()
        || wanted.owner.len() > 128
        || wanted.id.len() > 1024
    {
        return Err(error("invalid public owner identity"));
    }
    let mut matches = Vec::new();
    let candidates = if wanted.kind == "request" {
        request_entries(full, context)?
    } else {
        entries(full, context)?
    };
    for item in candidates {
        let selector = item["selector"].as_str().unwrap();
        let envelope = &item["envelope"];
        let candidate = match wanted.kind.as_str() {
            "request" if selector.starts_with("request:") => {
                envelope["owner"] == wanted.owner && envelope["id"] == wanted.id
            }
            "action" if action_selector(selector) => {
                envelope["source_owner"] == wanted.owner && envelope["operation_id"] == wanted.id
            }
            "question" if decision_selector(selector) => {
                envelope["response_request"]["owner"] == wanted.owner
                    && envelope["response_request"]["id"] == wanted.id
            }
            _ => false,
        };
        if candidate && !matches.iter().any(|m: &Value| m["envelope"] == *envelope) {
            matches.push(item);
        }
    }
    if matches.len() != 1 {
        return Ok(
            json!({"identity":identity,"status":if matches.is_empty(){"missing"}else{"ambiguous"},"authority_effect":"none"}),
        );
    }
    let selected = matches.remove(0);
    let mut result = json!({"identity":identity,"status":"current","reference":selected["reference"],"value":selected["envelope"],"reentry":context,
        "authority_effect":"none","continuation":"Use the exact reference through the existing owner answer/invoke path; a request template still requires its owner's requested input. Resolution never executes or retries."});
    if wanted.kind == "request" {
        attach_request_answer(&mut result, full, context, &selected);
        result["procedure"] = json!({
            "reference":".agentic-workspace/skills/workspace-startup/references/owners.md",
            "use":"Answer a simple choice directly. For substantial structured material, read this procedure and write UTF-8 JSON as data; submit it through start --input while retaining prior work-bound answers."
        });
        result["answer_input"] = json!(
            "Object of requested argument fields, merged into the template under normal owner validation. Reuse the same work context or carriage; do not copy immutable request identity."
        );
    }
    Ok(result)
}

/// Discovery returns the same complete answer context as ordinary compact
/// questions. The schema comes from this exact request's responsible owner;
/// presentation neither fills a judgment nor alters request/source admission.
fn attach_request_answer(result: &mut Value, full: &Value, context: &Value, selected: &Value) {
    let request = &selected["envelope"];
    result["reentry"] = context.clone();
    let mut step = json!({"reference":selected["reference"],"answer_shape":request["arguments"],
        "use":"Send the returned reentry unchanged, plus this exact reference and an answer containing the requested argument fields. The discovery identity is for lookup only; do not answer it or put this presentation in request. Owners revalidate the answer and current sources before offering any effect."});
    if let Some(declaration) = std::iter::once(&full["capability_contract"])
        .chain(
            full.as_object()
                .into_iter()
                .flat_map(|object| object.values())
                .filter_map(|value| value.get("capability_contract")),
        )
        .filter(|contract| contract["revision"] == request["capability_revision"])
        .flat_map(|contract| contract["owners"].as_array().into_iter().flatten())
        .filter(|owner| owner["owner"] == request["owner"])
        .flat_map(|owner| owner["requests"].as_array().into_iter().flatten())
        .find(|declaration| declaration["kind"] == request["request_kind"])
    {
        step["answer_schema"] = declaration["input_schema"].clone();
    }
    result["next_step"] = step;
}

fn use_selected(
    context: Value,
    current: Value,
    selected_entry: Value,
    answer: Option<Value>,
    invoking: bool,
    projection: &Value,
    detail: Option<Option<&str>>,
) -> Result<Value, CoreError> {
    let selector = selected_entry["selector"]
        .as_str()
        .ok_or_else(|| error("invalid selector"))?;
    let selected = selected_entry["reference"].clone();
    let lazy = selected_entry["envelope"]["kind"] == "agentic-workspace/lazy-owner-detail/v1";
    if if lazy || selector.starts_with("request:") {
        select_entry(&current, &context, &selected).ok().as_ref() != Some(&selected_entry)
    } else {
        current.pointer(selector) != Some(&selected_entry["envelope"])
    } {
        return Err(error("operating reference stale or not owner-issued"));
    }
    if invoking {
        if !action_selector(selector) || answer.is_some() {
            return Err(error(
                "invoke requires an exact owner-issued action reference without answer",
            ));
        }
        let mut execution = context;
        execution.as_object_mut().unwrap().remove("request");
        execution["invocation"] = selected_entry["envelope"].clone();
        // Native admission reobserves the execution snapshot; the reference is
        // only immutable transport and never a grant.
        return Ok(project_invocation(
            native_public::invoke_selected(execution, &resolution(projection, detail)),
            projection,
            detail,
        ));
    }
    if (decision_selector(selector) && answer.is_some())
        || (selector.starts_with("request:") && answer.is_some())
    {
        let answer = answer.ok_or_else(|| error("bounded answer required"))?;
        let answered = if selector.starts_with("request:") {
            let supplied = answer
                .as_object()
                .ok_or_else(|| error("owner request answer must be an arguments object"))?;
            let mut request = selected_entry["envelope"].clone();
            let arguments = request["arguments"]
                .as_object_mut()
                .ok_or_else(|| error("owner request arguments must be an object"))?;
            // Only argument material is caller-authored. Exact request identity,
            // revisions and task binding stay owner-issued; the normal owner
            // schema and currentness path validates the resulting proposal.
            arguments.extend(supplied.clone());
            request
        } else {
            if selected_entry["envelope"]["response_request"]["arguments"]
                .get("answer")
                .is_some()
            {
                return Err(error(
                    "owner already supplied answer; immutable material cannot be replaced",
                ));
            }
            crate::answer_decision_value(json!({
                "decision":current["decision_packet"],
                "question":selected_entry["envelope"]["consequence_id"],
                "answer":answer,
                "capability_contract":current["capability_contract"]
            }))?["request"]
                .clone()
        };
        let mut next = context;
        let mut requests = match next.get("request").filter(|v| !v.is_null()) {
            Some(Value::Array(items)) => items.clone(),
            Some(item) => vec![item.clone()],
            None => vec![],
        };
        requests.retain(|request| {
            native_public::owner_request_key(request) != native_public::owner_request_key(&answered)
        });
        let verification_transition = matches!(
            answered["request_kind"].as_str(),
            Some("verification/assurance-applicability/v1" | "verification/strategy/v1")
        );
        requests.push(answered);
        next["request"] = json!(requests);
        next["projection"] = projection.clone();
        return match operate_selected(next.clone(), false, detail) {
            Err(failure) if verification_transition && failure.2.is_some() => {
                // Reject the stale envelopes, retaining the newly admitted
                // Verification answer and unaffected peer answers. No previous
                // Assignment choice is replayed as current authority.
                let source = failure.2.unwrap();
                next["request"].as_array_mut().unwrap().retain(|r| {
                    r["owner"] != "assignment"
                        || (matches!(source, crate::AssignmentSourceChange::Comparison)
                            && r["request_kind"] == "assignment/judge-task-requirements/v1")
                });
                let mut recovered = operate_selected(next, false, detail)?;
                let view = if projection == "carried" {
                    &mut recovered["view"]
                } else {
                    &mut recovered
                };
                view["assignment_context"]["recovery"] = json!({
                    "status":"stale-assignment-rejected",
                    "affected_judgment":match source {crate::AssignmentSourceChange::Requirements=>"assignment/judge-task-requirements/v1",crate::AssignmentSourceChange::Comparison=>"assignment/assess-best-fit/v1"},
                    "reason":failure.to_string(),
                    "continuation":"Answer the current Assignment next_step. Verification and unaffected peer answers are carried; discarded Assignment envelopes grant no selection or implementation authority."});
                Ok(recovered)
            }
            result => result,
        };
    }
    if answer.is_some() || action_selector(selector) {
        return Err(error(
            "detail selection does not accept answers or invoke actions",
        ));
    }
    let mut result = json!({"reference":selected,"selector":selector,"value":if lazy {current.pointer(selector).cloned().unwrap_or(Value::Null)} else {selected_entry["envelope"].clone()},"currentness":"reobserved","authority":"detail-only"});
    // Detail identities remain bound to the owner's source observation. Report
    // restriction routes from that same current surface after validating it.
    let recovery = consequence_recovery(&current, &context)?;
    reconcile_restriction_routes(&mut result["value"], &recovery);
    if selector.starts_with("request:") {
        attach_request_answer(&mut result, &current, &context, &selected_entry);
    }
    Ok(result)
}

/// Shared by JSON and all thin consumers. References and the optional carrier
/// are disposable; native owners reconstruct and revalidate every selection.
pub fn start(value: Value) -> Result<Value, CoreError> {
    operate(value, false)
}

pub fn invoke(value: Value) -> Result<Value, CoreError> {
    match operate(value.clone(), true) {
        Ok(result) => Ok(result),
        Err(failure) => {
            let mut context = value.clone();
            if value["invocation"]["kind"] == CARRIAGE {
                context = value["invocation"]["context"].clone();
                if context.is_object() {
                    for field in ["target", "task", "changed"] {
                        if let Some(supplied) = value.get(field) {
                            context[field] = supplied.clone();
                        }
                    }
                }
            }
            Ok(native_public::rejected_invocation(
                &context,
                &failure.to_string(),
            ))
        }
    }
}

fn operate(value: Value, invoking: bool) -> Result<Value, CoreError> {
    operate_selected(value, invoking, None)
}
fn resolution(projection: &Value, detail: Option<Option<&str>>) -> Resolution {
    match detail {
        Some(owner) => Resolution::Frontier(owner.map(str::to_owned)),
        None if projection == "full" => Resolution::Full,
        None => Resolution::Frontier(None),
    }
}
fn selected_owner(reference: &Value) -> Option<&str> {
    let text = reference.as_str()?;
    text.strip_prefix("detail:")
        .or_else(|| text.strip_prefix("request:"))?
        .split(':')
        .next()
        .and_then(|owner| owner.split('/').next())
}
fn operate_selected(
    mut value: Value,
    invoking: bool,
    detail: Option<Option<&str>>,
) -> Result<Value, CoreError> {
    let delivered = value.as_object_mut().and_then(|v| v.remove("delivered"));
    let delivered: Vec<String> = serde_json::from_value(delivered.unwrap_or(json!([])))
        .map_err(|_| error("delivered must be an array of exact source delivery refs"))?;
    if delivered.len() > 256 {
        return Err(error("source delivery refs exceed bounded carriage"));
    }
    let available = value
        .as_object_mut()
        .and_then(|v| v.remove("available_sources"));
    let available: Vec<SourceAvailability> = serde_json::from_value(available.unwrap_or(json!([])))
        .map_err(|_| {
            error("available_sources must contain exact source identity and extent assertions")
        })?;
    if available.len() > 256
        || available.iter().any(|s| {
            s.reference.len() > 4096
                || s.revision.len() > 128
                || s.extent.len() > 64
                || s.selector.as_ref().is_some_and(|v| v.len() > 256)
                || s.content_revision.as_ref().is_some_and(|v| v.len() > 128)
        })
    {
        return Err(error(
            "source availability exceeds bounded presentation input",
        ));
    }
    let mut result = operate_current(value, invoking, detail)?;
    apply_delivery(&mut result, &delivered, &available)?;
    if let Some(continuation) = result
        .get_mut("continuation")
        .and_then(|c| c.get_mut("result"))
    {
        apply_delivery(continuation, &delivered, &available)?;
    }
    Ok(result)
}

fn apply_delivery(
    result: &mut Value,
    delivered: &[String],
    available: &[SourceAvailability],
) -> Result<(), CoreError> {
    // Delivery is caller-local presentation state only. All owner resolution,
    // restriction, action admission and reference checks have already occurred.
    let view = if result.get("view").is_some() {
        &mut result["view"]
    } else {
        result
    };
    let work = view["decision_packet"]["semantic_task_routes"]["task_identity"].clone();
    let mut refs = Vec::new();
    if let Some(material) = view
        .get_mut("decision_packet")
        .and_then(|p| p.get_mut("material"))
        .and_then(Value::as_object_mut)
    {
        for (owner, value) in material {
            let rows: Vec<&mut Value> = if owner == "scoped-instructions" {
                value
                    .as_array_mut()
                    .map(|v| v.iter_mut().collect())
                    .unwrap_or_default()
            } else if owner == "startup-adapter" || owner == "system-intent" {
                vec![value]
            } else {
                continue;
            };
            for row in rows {
                let field = if owner == "scoped-instructions" {
                    "guidance"
                } else {
                    "text"
                };
                if !row.is_object() {
                    continue;
                }
                let has_text = row[field].as_str().is_some_and(|s| !s.is_empty());
                if !has_text {
                    row["delivery"] = json!({"status":"needed","extent":"reference-only",
                        "authority":"presentation-only; no semantic satisfaction"});
                    continue;
                }
                let reference = digest(
                    &json!({"producer":delivery_producer(),"work":work,"owner":owner,"source":row}),
                )?;
                // Small required text still arrives without a selector hop.
                if row[field].as_str().unwrap().len() > 256 {
                    refs.push(reference.clone());
                }
                let held = available.iter().any(|s| s.matches(&row["source_material"]));
                let repeated = delivered.contains(&reference);
                if repeated || held {
                    row.as_object_mut().unwrap().remove(field);
                }
                row["delivery"] = json!({"reference":reference,
                    "status":if held {"caller-held"} else if repeated {"already-delivered"} else {"included"},
                    "extent":row["source_material"].get("extent").cloned().unwrap_or(json!("unknown")),
                    "authority":"presentation-only; no semantic satisfaction"});
            }
        }
    }
    if !refs.is_empty() {
        view["delivery_refs"] = json!(refs);
    }
    Ok(())
}

fn delivery_producer() -> &'static str {
    static REVISION: std::sync::LazyLock<String> = std::sync::LazyLock::new(|| {
        digest(&json!({"contract":"source-delivery/v1", "implementation":include_str!("operating.rs")})).unwrap()
    });
    &REVISION
}

fn operate_current(
    mut value: Value,
    invoking: bool,
    detail: Option<Option<&str>>,
) -> Result<Value, CoreError> {
    let (projection, selected, answer) = {
        let object = value
            .as_object_mut()
            .ok_or_else(|| error("expected operating input object"))?;
        (
            object.remove("projection").unwrap_or(json!("compact")),
            object.remove("reference"),
            object.remove("answer"),
        )
    };
    if ![json!("compact"), json!("full"), json!("carried")].contains(&projection) {
        return Err(error("unknown operating projection"));
    }
    let field = if invoking { "invocation" } else { "request" };
    if let Some(mut selected) = selected {
        if let Some(identity) = selected.as_str().and_then(|s| s.strip_prefix("owner:")) {
            let parts: Vec<_> = identity.splitn(3, ':').collect();
            if parts.len() != 3 {
                return Err(error("owner identity requires kind, owner and id"));
            }
            selected = json!({"kind":parts[0],"owner":parts[1],"id":parts[2]});
        }
        if value[field]["kind"] == CARRIAGE {
            let carrier: Carriage = serde_json::from_value(
                value
                    .as_object_mut()
                    .unwrap()
                    .remove(field)
                    .ok_or_else(|| error("carriage missing"))?,
            )
            .map_err(|_| error("invalid carriage"))?;
            if carrier.kind != CARRIAGE {
                return Err(error("unknown carriage kind"));
            }
            let carried_context = carrier
                .context
                .as_object()
                .ok_or_else(|| error("invalid carried context"))?;
            if carried_context.keys().any(|key| {
                ![
                    "target",
                    "task",
                    "changed",
                    "request",
                    "material",
                    "maintenance",
                ]
                .contains(&key.as_str())
            }) {
                return Err(error("unknown carried context field"));
            }
            // Explicit context is either identical or rejected, never silently
            // treated as a task switch. A new work context requires fresh start.
            for (key, supplied) in value.as_object().unwrap() {
                let normalized_target = if key == "target" {
                    Some(json!(
                        std::fs::canonicalize(
                            supplied.as_str().ok_or_else(|| error("invalid target"))?
                        )
                        .map_err(|e| error(&e.to_string()))?
                    ))
                } else {
                    None
                };
                if carried_context.get(key) != Some(normalized_target.as_ref().unwrap_or(supplied))
                {
                    return Err(error("carriage work context changed"));
                }
            }
            // Optional requests are lazy, not copied into every carrier. Resolve
            // them against the carried work (including prior answers), exactly
            // as explicit-context request references are freshly resolved.
            if selected.is_object() || selected.as_str().is_some_and(|s| s.starts_with("request:"))
            {
                if invoking {
                    return Err(error("owner request references do not invoke effects"));
                }
                let current = native_public::start_selected(
                    carrier.context.clone(),
                    &if selected.is_object() {
                        Resolution::Full
                    } else {
                        Resolution::Frontier(selected_owner(&selected).map(str::to_owned))
                    },
                )?;
                if selected.is_object() {
                    if answer.is_some() {
                        return Err(error(
                            "stable owner identity must first resolve an exact reference",
                        ));
                    }
                    return resolve_owner_reference(&current, &carrier.context, &selected);
                }
                let selected_entry = select_entry(&current, &carrier.context, &selected)?;
                return use_selected(
                    carrier.context,
                    current,
                    selected_entry,
                    answer,
                    false,
                    &projection,
                    detail,
                );
            }
            let matches: Vec<_> = carrier
                .envelopes
                .iter()
                .filter(|entry| entry["reference"] == selected)
                .collect();
            if matches.len() != 1 {
                return Err(error("unknown or ambiguous carried reference"));
            }
            let selected_entry = matches[0].clone();
            let selector = selected_entry["selector"]
                .as_str()
                .ok_or_else(|| error("invalid selector"))?;
            if json!(reference(
                &carrier.context,
                selector,
                &selected_entry["envelope"]
            )?) != selected
            {
                return Err(error("altered carried envelope"));
            }
            // Exact carried invocations belong to native effect admission, which
            // also owns committed replay and uncertain-effect recovery. A fresh
            // pre-effect start may no longer return the original action after
            // it committed; do not replace that disposition with a lookup error.
            if invoking {
                if !action_selector(selector) || answer.is_some() {
                    return Err(error(
                        "invoke requires an exact carried action without answer",
                    ));
                }
                let mut execution = carrier.context;
                execution.as_object_mut().unwrap().remove("request");
                execution["invocation"] = selected_entry["envelope"].clone();
                return Ok(project_invocation(
                    native_public::invoke_selected(execution, &resolution(&projection, detail)),
                    &projection,
                    detail,
                ));
            }
            let current = native_public::start_selected(
                carrier.context.clone(),
                &Resolution::Frontier(
                    selected_owner(&selected)
                        .or(detail.flatten())
                        .map(str::to_owned),
                ),
            )?;
            return use_selected(
                carrier.context,
                current,
                selected_entry,
                answer,
                invoking,
                &projection,
                detail,
            );
        }

        // A compact reference is enough when the client can supply the same
        // explicit work context. Re-resolve it now; no hidden carrier/session
        // state and no caller-reconstructed immutable envelope are trusted.
        if invoking && value.get("invocation").is_some_and(|v| !v.is_null()) {
            return Err(error(
                "reference invocation accepts work context, not a caller-built invocation",
            ));
        }
        let context = normalize_context(value)?;
        let current = native_public::start_selected(
            context.clone(),
            &if selected.is_object() {
                Resolution::Full
            } else {
                Resolution::Frontier(
                    selected_owner(&selected)
                        .or(detail.flatten())
                        .map(str::to_owned),
                )
            },
        )?;
        if selected.is_object() {
            if invoking || answer.is_some() {
                return Err(error(
                    "stable owner identity must first resolve an exact reference",
                ));
            }
            return resolve_owner_reference(&current, &context, &selected);
        }
        let selected_entry = select_entry(&current, &context, &selected)?;
        return use_selected(
            context,
            current,
            selected_entry,
            answer,
            invoking,
            &projection,
            detail,
        );
    }
    if answer.is_some() {
        return Err(error("answer requires exact operating reference"));
    }
    if invoking {
        // A returned reentry can carry the same answered requests already
        // bound into its exact action. Subtract only that duplicate cache;
        // contradictory requests remain invalid. Native effect admission still
        // revalidates every action source request, dependency and restriction.
        if value["invocation"]["kind"] == "agentic-workspace/operation-invocation/v1"
            && let Some(request) = value.get("request").filter(|request| !request.is_null())
        {
            let requests = if request.is_array() {
                request.clone()
            } else {
                json!([request])
            };
            if value["invocation"]["source_requests"] == requests {
                value.as_object_mut().unwrap().remove("request");
            }
        }
        return Ok(project_invocation(
            native_public::invoke_selected(value, &resolution(&projection, detail)),
            &projection,
            detail,
        ));
    }
    // Resolve owner identities and their projected references from the same
    // canonical work context, including when the caller used a relative path.
    let value = normalize_context(value)?;
    let full = native_public::start_selected(value.clone(), &resolution(&projection, detail))?;
    if projection == "full" && detail.is_some() {
        Ok(full)
    } else {
        project_start(full, value, &projection)
    }
}

fn project_invocation(
    mut result: Value,
    projection: &Value,
    detail: Option<Option<&str>>,
) -> Value {
    if result["continuation"]["status"] == "current" {
        let full = result["continuation"]["result"].take();
        let context = result["continuation"]["context"].clone();
        match consequence_recovery(&full, &context).and_then(|recovery| {
            let projected = if projection == "full" && detail.is_some() {
                let mut full = full;
                reconcile_restriction_routes(&mut full, &recovery);
                if !recovery.is_empty() {
                    full["consequence_recovery"] = json!(recovery);
                }
                full
            } else {
                project_start(full, context, projection)?
            };
            Ok((projected, recovery))
        }) {
            Ok((projected, recovery)) => {
                // Effect summaries were observed before operating projection.
                // Reconcile only the exact current consequence identities;
                // discovering a route never settles the restriction.
                reconcile_restriction_routes(&mut result, &recovery);
                result["continuation"]["result"] = projected;
            }
            Err(failure) => {
                result["continuation_status"] = json!("unavailable");
                result["next_decision"] = Value::Null;
                result["continuation"]["status"] = json!("unavailable");
                result["continuation"]["diagnostic"] = json!(failure.to_string());
            }
        }
    }
    if projection != "full" {
        result.as_object_mut().unwrap().remove("next_decision");
    }
    result
}

pub(crate) fn project_start(
    mut full: Value,
    value: Value,
    projection: &Value,
) -> Result<Value, CoreError> {
    let context = normalize_context(value.clone())?;
    let mut nominations = Vec::new();
    for source in full["semantic_routes"]["discovery"]["detail"]["sources"]
        .as_array()
        .into_iter()
        .flatten()
    {
        let selected = &source["procedure"]["resource"]["selected"];
        if let Some(text) = selected["text"].as_str() {
            let lines: Vec<_> = text.lines().collect();
            let starts: Vec<_> = lines
                .iter()
                .enumerate()
                .filter(|(_, line)| **line == "```agentic-owner-reference")
                .map(|(i, _)| i)
                .collect();
            if starts.is_empty() {
                continue;
            }
            let resolve = || -> Result<Value, CoreError> {
                if starts.len() != 1 {
                    return Err(error("ambiguous owner-reference declaration"));
                }
                let start = starts[0] + 1;
                let end = lines[start..]
                    .iter()
                    .position(|line| *line == "```")
                    .map(|i| i + start)
                    .ok_or_else(|| error("owner-reference fence is not closed"))?;
                let identity: Value = serde_json::from_str(&lines[start..end].join("\n"))
                    .map_err(|_| error("invalid owner-reference declaration"))?;
                // Optional owner detail may have been suppressed in compact
                // startup. Reobserve it on this explicit nomination only.
                if projection != "full" {
                    let current =
                        native_public::start_selected(context.clone(), &Resolution::Full)?;
                    let still_selected =
                        current["semantic_routes"]["discovery"]["detail"]["sources"]
                            .as_array()
                            .into_iter()
                            .flatten()
                            .any(|candidate| {
                                candidate["procedure"]["resource"]["selected"] == *selected
                            });
                    if !still_selected {
                        return Err(error(
                            "procedure nomination source changed during resolution",
                        ));
                    }
                    resolve_owner_reference(&current, &context, &identity)
                } else {
                    resolve_owner_reference(&full, &context, &identity)
                }
            };
            nominations.push(json!({"source":selected["reference"],"source_revision":selected["revision"],
                "owner_reference":resolve().unwrap_or_else(|e|json!({"status":"unavailable","reason":e.to_string()})),
                "continuation":"Yield to the exact owner reference. No automatic effect, replay or traversal is authorized."}));
        }
    }
    if !nominations.is_empty() {
        full["procedure_continuation"] = json!(nominations);
    }
    if projection == "full" {
        let context = normalize_context(value)?;
        let recovery = consequence_recovery(&full, &context)?;
        if !recovery.is_empty() {
            reconcile_restriction_routes(&mut full, &recovery);
            full["consequence_recovery"] = json!(recovery);
        }
        if let Some(object) = full.as_object_mut() {
            object.remove("_detail_bindings");
        }
        return Ok(full);
    }
    let value = normalize_context(value)?;
    let mut view = compact(&full, &value, projection == "carried")?;
    if let Some(nominations) = full.get("procedure_continuation") {
        view["procedure_continuation"] = nominations.clone();
    }
    if projection == "carried" {
        return Ok(
            json!({"view":view,"carriage":{"kind":CARRIAGE,"context":value,"envelopes":entries(&full, &value)?.into_iter().filter(|e|!e["selector"].as_str().unwrap().starts_with("request:")).collect::<Vec<_>>()}}),
        );
    }
    Ok(view)
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::path::PathBuf;

    fn temp_root(label: &str) -> PathBuf {
        let root = std::env::temp_dir().join(format!(
            "aw-operating-{label}-{}-{}",
            std::process::id(),
            std::time::SystemTime::now()
                .duration_since(std::time::UNIX_EPOCH)
                .unwrap()
                .as_nanos()
        ));
        std::fs::create_dir(&root).unwrap();
        root
    }

    #[test]
    fn compact_reference_reobserves_detail_without_carriage() {
        let root = temp_root("reference-detail");
        let context = json!({"target":root,"task":"inspect current work","changed":[]});
        let view = start(context.clone()).unwrap();
        assert!(view.get("consequence_recovery").is_none());
        let selected = view["detail_refs"]["/current_work"].clone();
        assert!(selected.is_string());

        let detail = start(json!({
            "target":context["target"],
            "task":context["task"],
            "changed":context["changed"],
            "reference":selected
        }))
        .unwrap();
        assert_eq!(detail["selector"], "/current_work");
        assert_eq!(detail["currentness"], "reobserved");
        assert_eq!(detail["authority"], "detail-only");

        let stale = start(json!({
            "target":context["target"],
            "task":"different work",
            "changed":context["changed"],
            "reference":selected
        }));
        assert!(stale.is_err());
        std::fs::remove_dir_all(root).unwrap();
    }

    #[test]
    fn carried_route_selection_replaces_completed_discovery() {
        let root = temp_root("route-carriage");
        std::fs::create_dir_all(root.join("tools/skills/checks")).unwrap();
        std::fs::write(root.join("tools/skills/REGISTRY.json"),
            r#"{"skills":[{"id":"checks","path":"checks/SKILL.md","semantic_routes":["repository/checks"]}]}"#).unwrap();
        std::fs::write(
            root.join("tools/skills/checks/SKILL.md"),
            "Inspect current test prerequisites.",
        )
        .unwrap();
        let first =
            start(json!({"target":root,"task":"Prepare repository checks","projection":"carried"}))
                .unwrap();
        let discovery = start(json!({"request":first["carriage"],"reference":"owner:request:semantic-routes:semantic-routes/discover/v1"})).unwrap();
        let discovered = start(json!({"request":first["carriage"],"reference":discovery["reference"],"answer":{"parent":"repository"},"projection":"carried"})).unwrap();
        let choice = start(json!({"request":discovered["carriage"],"reference":"owner:request:semantic-routes:semantic-routes/select/v1"})).unwrap();
        let selected = start(json!({"request":discovered["carriage"],"reference":choice["reference"],"answer":{"posture":"selected","routes":["repository/checks"]},"projection":"carried"})).unwrap();
        assert_eq!(
            selected["view"]["decision_packet"]["semantic_task_routes"]["status"],
            "current"
        );
        assert_eq!(
            selected["view"]["decision_packet"]["semantic_task_routes"]["routes"],
            json!(["repository/checks"])
        );
        assert_eq!(
            selected["carriage"]["context"]["request"]
                .as_array()
                .unwrap()
                .iter()
                .filter(|r| r["owner"] == "semantic-routes")
                .count(),
            1
        );
        assert!(!root.join(".agentic-workspace/local").exists());
        std::fs::remove_dir_all(root).unwrap();
    }

    #[test]
    fn selected_setup_choices_bind_only_native_request_slots() {
        let work = json!({"kind":"current-work", "id":"bounded-work"});
        let request = json!({"kind":"agentic-workspace/public-request/v1", "owner":"configuration",
            "request_kind":"configuration/edit-source/v1", "task_identity":work,
            "arguments":{"source":"managed.md", "key":"package.payload", "value":"current-artifact"}});
        let mut foreign = request.clone();
        foreign["arguments"]["source"] = json!("caller-material.md");
        let full = json!({"current_work":work,
            "setup_context":{"choices":[{"request":request,"subject":"managed.md",
                "arguments":{"request":foreign}, "material":[{"request":foreign}],
                "metadata":{"request":foreign}}]},
            "material":[{"request":foreign}],
            "configuration_write":{"arguments":{"requests":[foreign]},
                "creation_provenance":{"request":foreign}, "other_array":[{"request":foreign}]}});
        let found = request_entries(&full, &json!({"target":"fixture", "task":"bounded"})).unwrap();
        assert_eq!(found.len(), 1);
        assert_eq!(found[0]["envelope"], request);
        assert!(
            found[0]["reference"]
                .as_str()
                .unwrap()
                .starts_with("request:setup_context:")
        );
        let mut different_work = full;
        different_work["current_work"]["id"] = json!("another-work");
        assert!(
            request_entries(
                &different_work,
                &json!({"target":"fixture", "task":"bounded"})
            )
            .unwrap()
            .is_empty()
        );
    }
    #[test]
    fn public_owner_identity_resolves_exact_requests_without_rebinding() {
        let root = temp_root("owner-reference");
        let mut context = json!({"target":root,"task":"inspect a current owner"});
        context["reference"] = json!("owner:request:semantic-routes:semantic-routes/discover/v1");
        let resolved = start(context.clone()).unwrap();
        assert_eq!(resolved["status"], "current");
        assert_eq!(resolved["value"]["owner"], "semantic-routes");
        assert_eq!(resolved["authority_effect"], "none");
        assert_eq!(resolved["reentry"]["task"], context["task"]);
        assert_eq!(resolved["reentry"]["changed"], json!([]));
        assert_eq!(resolved["next_step"]["reference"], resolved["reference"]);
        assert_eq!(
            resolved["next_step"]["answer_shape"],
            resolved["value"]["arguments"]
        );
        assert_eq!(
            resolved["procedure"]["reference"],
            ".agentic-workspace/skills/workspace-startup/references/owners.md"
        );
        context["reference"] = resolved["reference"].clone();
        let exact = start(context.clone()).unwrap();
        assert_eq!(exact["value"], resolved["value"]);
        assert_eq!(exact["reentry"], resolved["reentry"]);
        let mut answered = resolved["reentry"].clone();
        answered["reference"] = resolved["next_step"]["reference"].clone();
        answered["answer"] = json!({"parent":""});
        let next = start(answered).unwrap();
        assert_eq!(next["reentry"]["request"][0]["arguments"]["parent"], "");
        std::fs::create_dir_all(root.join("tools/skills")).unwrap();
        std::fs::write(
            root.join("tools/skills/REGISTRY.json"),
            r#"{"skills":[{"id":"new","semantic_routes":["new/route"]}]}"#,
        )
        .unwrap();
        assert!(start(context.clone()).is_err());
        let mut rebound = context.clone();
        rebound["reference"] = json!("owner:request:semantic-routes:semantic-routes/discover/v1");
        assert_ne!(start(rebound).unwrap()["reference"], resolved["reference"]);
        context["task"] = json!("another task");
        assert!(start(context).is_err());
        let result=invoke(json!({"target":root,"task":"inspect a current owner","reference":"owner:action:any:any"})).unwrap();
        assert_eq!(result["effect_outcome"]["status"], "rejected-before-effect");
        assert!(!root.join(".agentic-workspace/local").exists());
        std::fs::remove_dir_all(root).unwrap();
    }

    #[test]
    fn owner_nomination_yields_without_execution_and_preserves_ambiguity() {
        let root = temp_root("fragment-owner");
        let work = json!({"kind":"current-work","id":"test"});
        let request = json!({"kind":"agentic-workspace/public-request/v1","owner":"example","id":"example/read","task_identity":work,"arguments":{"selection":"first"}});
        let identity = json!({"kind":"request","owner":"example","id":"example/read"});
        let context = json!({"target":root,"task":"inspect nominated owner"});
        let mut full = json!({"current_work":work,"example":{"requests":[request]},"decision_packet":{},
            "semantic_routes":{"discovery":{"detail":{"sources":[{"procedure":{"resource":{"selected":{"reference":"fragment.md","revision":"current","text":format!("Inspect current owner.\n```agentic-owner-reference\n{identity}\n```\n")}}}}]}}}});
        let result = project_start(full.clone(), context.clone(), &json!("full")).unwrap();
        assert_eq!(
            result["procedure_continuation"][0]["owner_reference"]["value"],
            request
        );
        assert_eq!(
            result["procedure_continuation"][0]["owner_reference"]["status"],
            "current"
        );
        assert!(result["decision_packet"]["primary_action"].is_null());
        // Assignment returns prerequisite bundles in its request list. Their
        // leaf requests remain discoverable, but request arguments are data.
        full["example"]["requests"] = json!([[request.clone()]]);
        assert_eq!(
            resolve_owner_reference(&full, &context, &identity).unwrap()["value"],
            request
        );
        let mut injected = request.clone();
        injected["id"] = json!("example/injected");
        full["example"]["requests"][0][0]["arguments"]["requests"] = json!([injected]);
        assert_eq!(
            resolve_owner_reference(
                &full,
                &context,
                &json!({"kind":"request","owner":"example","id":"example/injected"})
            )
            .unwrap()["status"],
            "missing"
        );
        full["example"]["requests"] = json!([[request.clone()]]);
        let mut peer = request.clone();
        peer["arguments"]["selection"] = json!("second");
        full["example"]["requests"]
            .as_array_mut()
            .unwrap()
            .push(peer);
        assert_eq!(
            resolve_owner_reference(&full, &context, &identity).unwrap()["status"],
            "ambiguous"
        );
        let missing = json!({"kind":"request","owner":"missing","id":"missing"});
        assert_eq!(
            resolve_owner_reference(&full, &context, &missing).unwrap()["status"],
            "missing"
        );
        let mut altered = identity;
        altered["arguments"] = json!({"injected":"effect"});
        assert!(resolve_owner_reference(&full, &context, &altered).is_err());
        std::fs::remove_dir_all(root).unwrap();
    }

    #[test]
    fn multiple_ready_actions_remain_exactly_constructible_without_detail() {
        let vectors: Value =
            serde_json::from_str(include_str!("../../../tests/vectors/source_decision.json"))
                .unwrap();
        let input = vectors["cases"]
            .as_array()
            .unwrap()
            .iter()
            .find(|case| case["id"] == "two-independent-ready-actions")
            .unwrap()["input"]
            .clone();
        let decision = crate::compile_value(input.clone()).unwrap();
        assert!(decision["primary_action"].is_null());
        assert_eq!(decision["ready_actions"].as_array().unwrap().len(), 2);
        let full = json!({"decision_packet":decision});
        let context =
            json!({"target":"fixture","task":"two exact independent effects","changed":[]});
        let envelopes = entries(&full, &context).unwrap();
        let mut drift = input;
        drift["capability_contract"]["owners"][1]["operations"][0]["reads"] = json!(["a"]);
        let stale = crate::compile_value(drift).unwrap();
        for carried in [false, true] {
            let view = compact(&full, &context, carried).unwrap();
            let packet = &view["decision_packet"];
            assert_eq!(packet["status"], decision["status"]);
            assert_eq!(packet["claim_boundary"], decision["claim_boundary"]);
            assert_eq!(packet["blockers"], decision["blockers"]);
            for (index, action) in packet["ready_actions"]
                .as_array()
                .unwrap()
                .iter()
                .enumerate()
            {
                let exact = if carried {
                    let entry = envelopes
                        .iter()
                        .find(|e| e["reference"] == action["reference"])
                        .unwrap();
                    assert!(action_selector(entry["selector"].as_str().unwrap()));
                    assert_eq!(action["effects"], entry["envelope"]["effects"]);
                    assert_eq!(action["authority"], entry["envelope"]["authority"]);
                    assert_eq!(action["arguments"], entry["envelope"]["arguments"]);
                    &entry["envelope"]
                } else {
                    action
                };
                assert_eq!(exact, &decision["ready_actions"][index]);
                assert_eq!(
                    crate::admit_invocation_value(json!({"decision":decision,"invocation":exact}))
                        .unwrap()["disposition"],
                    "execute"
                );
                assert!(
                    crate::admit_invocation_value(json!({"decision":stale,"invocation":exact}))
                        .is_err()
                );
                let mut altered = exact.clone();
                altered["arguments"] = json!({"widen":true});
                assert!(
                    crate::admit_invocation_value(
                        json!({"decision":decision,"invocation":altered})
                    )
                    .is_err()
                );
            }
        }
    }

    #[test]
    fn owner_operating_material_is_current_identity_bound_and_not_a_grant() {
        let input = json!({"contributions":[{"owner":"independent-context","revision":"current",
            "material":{"read_first":"exact-source","restriction":"retain-foreign"}},
            {"owner":"irrelevant","revision":"other","relevant":false,"material":{"large":"absent"}}]});
        let decision = crate::compile_value(input.clone()).unwrap();
        assert_eq!(
            decision["material"],
            json!({"independent-context":{"read_first":"exact-source","restriction":"retain-foreign"}})
        );
        assert!(decision["primary_action"].is_null());
        let mut changed = input;
        changed["contributions"][0]["material"]["restriction"] = json!("changed-current-guidance");
        let next = crate::compile_value(changed).unwrap();
        assert_ne!(decision["decision_id"], next["decision_id"]);
        assert_eq!(decision["claim_boundary"], next["claim_boundary"]);
    }

    #[test]
    fn restriction_routes_select_owner_nomination_and_keep_unavailable_scope() {
        let root = temp_root("restriction-routes");
        let work = json!({"kind":"current-work","id":"fixture"});
        let context = json!({"target":std::fs::canonicalize(&root).unwrap(),"task":"bounded", "changed":["a"],
            "maintenance":{"kind":"fixture"}, "request":[{"prior":"answer"}]});
        let request = |kind: &str| {
            json!({"kind":"agentic-workspace/public-request/v1",
            "owner":"sample", "request_kind":kind, "task_identity":work, "arguments":{}})
        };
        let blocker = |id: &str| {
            json!({"consequence_id":id,"owner":"sample",
            "message":"Admit current evidence", "affects":["claim:complete"],
            "resolution":"owner-resolution-unavailable"})
        };
        let mut nominated = blocker("nominated");
        nominated["owner"] = json!("another-owner");
        nominated["recovery"] = json!("public-request:sample/evidence");
        let mut full = json!({"current_work":work,
            "sample":{"requests":[request("sample/unrelated"),request("sample/evidence")]},
            "decision_packet":{"blockers":[nominated,blocker("selection")],"primary_action":null}});
        full["decision_packet"]["claim_boundary"] = json!({"allowed":[],"blocked":["complete"]});
        full["configuration_behavior"] = json!({"remaining_restrictions":[blocker("selection"),blocker("different-consequence")]});
        let effect = json!({"effect_outcome":{"status":"committed"},"continuation_status":"current",
            "continuation":{"status":"current","result":full,"context":context},
            "configuration_behavior":full["configuration_behavior"],
            "setup_result":{"remaining_gaps":[blocker("selection"),blocker("different-consequence")],"effect":"committed"}});
        for projection in ["compact", "carried", "full"] {
            for detail in [None, Some(Some("configuration"))] {
                let result = project_invocation(effect.clone(), &json!(projection), detail);
                assert_eq!(
                    result["configuration_behavior"]["remaining_restrictions"][0]["resolution"],
                    "current-owner-route",
                    "{projection} {detail:?}: {result}"
                );
                assert_eq!(
                    result["setup_result"]["remaining_gaps"][0]["resolution"],
                    "current-owner-route"
                );
                assert_eq!(
                    result["setup_result"]["remaining_gaps"][1]["resolution"],
                    "owner-resolution-unavailable"
                );
                assert_eq!(
                    result["setup_result"]["remaining_gaps"][0]["affects"],
                    json!(["claim:complete"])
                );
                assert_eq!(result["effect_outcome"], effect["effect_outcome"]);
                let current = if projection == "carried" {
                    &result["continuation"]["result"]["view"]
                } else {
                    &result["continuation"]["result"]
                };
                assert_eq!(
                    current["decision_packet"]["claim_boundary"],
                    full["decision_packet"]["claim_boundary"]
                );
            }
        }
        let entry = entries(&full, &context)
            .unwrap()
            .into_iter()
            .find(|e| e["selector"] == "/configuration_behavior")
            .unwrap();
        let detail = use_selected(
            context.clone(),
            full.clone(),
            entry,
            None,
            false,
            &json!("compact"),
            None,
        )
        .unwrap();
        assert_eq!(
            detail["value"]["remaining_restrictions"][0]["resolution"],
            "current-owner-route"
        );
        assert_eq!(
            detail["value"]["remaining_restrictions"][1]["resolution"],
            "owner-resolution-unavailable"
        );
        assert_eq!(detail["authority"], "detail-only");
        let mut unavailable = effect;
        unavailable["continuation"]["status"] = json!("unavailable");
        assert_eq!(
            project_invocation(unavailable.clone(), &json!("compact"), None)["setup_result"],
            unavailable["setup_result"]
        );
        let view = compact(&full, &context, true).unwrap();
        let routes = &view["consequence_recovery"];
        assert_eq!(routes[0]["selection"]["status"], "owner-nominated");
        assert_eq!(routes[0]["owner"], "sample");
        assert_eq!(routes[0]["routes"].as_array().unwrap().len(), 1);
        assert_eq!(routes[0]["routes"][0]["request_kind"], "sample/evidence");
        assert_eq!(routes[1]["selection"]["status"], "required");
        assert_eq!(
            view["decision_packet"]["blockers"][1]["resolution"],
            "current-owner-route"
        );
        let original = routes[0]["routes"][0]["reference"].clone();
        let mut changed = context.clone();
        changed["changed"] = json!(["b"]);
        assert_ne!(
            consequence_recovery(&full, &changed).unwrap()[0]["routes"][0]["reference"],
            original
        );
        full["sample"]["requests"] = json!([]);
        let absent = compact(&full, &context, true).unwrap();
        assert_eq!(
            absent["decision_packet"]["blockers"][0]["resolution"],
            "owner-resolution-unavailable"
        );
        assert_eq!(
            absent["consequence_recovery"][1]["status"],
            "public-owner-route-unavailable"
        );
        assert_eq!(
            absent["decision_packet"]["blockers"][1]["resolution"],
            "owner-resolution-unavailable"
        );
        std::fs::remove_dir_all(root).unwrap();
    }

    #[test]
    fn compact_removes_only_exact_prepared_proposals_and_preserves_peers() {
        let invocation = json!({
            "kind":"agentic-workspace/operation-invocation/v1",
            "operation_id":"owned.write", "operation_revision":"operation-current",
            "source_owner":"owner", "authority":"owner",
            "consequence_id":"effect:owned-write", "effects":["owned-write"],
            "arguments":{"path":"current.txt"}, "source_requests":[],
            "expected_dependency_revision":"dependency-current", "idempotency_key":"logical-current"
        });
        let proposal = json!({
            "operation_id":"owned.write", "operation_revision":"operation-current",
            "source_owner":"owner", "authority":"owner",
            "consequence_id":"effect:owned-write", "effects":["owned-write"],
            "arguments":{"path":"current.txt"}, "source_requests":[],
            "dependency_revision":"dependency-current", "logical_effect_id":"logical-current"
        });
        let mut peers = Vec::new();
        for (field, different) in [
            ("source_owner", json!("another-owner")),
            ("authority", json!("another-authority")),
            ("operation_revision", json!("another-operation")),
            ("logical_effect_id", json!("another-logical-effect")),
            ("dependency_revision", json!("another-dependency")),
            ("consequence_id", json!("effect:another-write")),
            ("arguments", json!({"path":"another.txt"})),
            ("effects", json!(["another-write"])),
            (
                "source_requests",
                json!([{"source":"another-current-source"}]),
            ),
            ("new_owner_material", json!({"stop":"preserve-foreign"})),
        ] {
            let mut peer = proposal.clone();
            peer[field] = different;
            peers.push(peer);
        }
        let blockers =
            json!([{"owner":"peer", "code":"review-required", "affects":["claim:complete"]}]);
        let full = json!({"decision_packet":{
            "status":"actionable", "primary_action":invocation, "ready_actions":[invocation],
            "decision_request":null, "blockers":blockers, "claim_boundary":{"blocked":["complete"]},
            "pending_consequences":{"actions":std::iter::once(proposal.clone()).chain(peers.clone()).collect::<Vec<_>>(),
                "decisions":[], "blockers":blockers}
        }});
        let context = json!({"target":"fixture", "task":"bounded"});
        for carried in [false, true] {
            let view = compact(&full, &context, carried).unwrap();
            assert_eq!(
                view["decision_packet"]["pending_consequences"]["actions"],
                json!(peers)
            );
            assert_eq!(view["decision_packet"]["blockers"], blockers);
            assert_eq!(
                view["decision_packet"]["claim_boundary"],
                full["decision_packet"]["claim_boundary"]
            );
            assert_eq!(
                view["decision_packet"]["primary_action"]["arguments"],
                invocation["arguments"]
            );
        }
        // No current admission means even the matching proposal stays visible.
        let mut unadmitted = full.clone();
        unadmitted["decision_packet"]["primary_action"] = Value::Null;
        unadmitted["decision_packet"]["ready_actions"] = json!([]);
        assert_eq!(
            compact(&unadmitted, &context, false).unwrap()["decision_packet"]["pending_consequences"]
                ["actions"],
            full["decision_packet"]["pending_consequences"]["actions"]
        );

        // Multiple independent ready actions keep their prepared invocations;
        // only their exact raw copies disappear, leaving the unadmitted peers.
        let mut other = invocation.clone();
        other["operation_id"] = json!("other.write");
        let mut other_proposal = proposal;
        other_proposal["operation_id"] = json!("other.write");
        let mut multiple = full;
        multiple["decision_packet"]["primary_action"] = Value::Null;
        multiple["decision_packet"]["ready_actions"] = json!([invocation, other]);
        multiple["decision_packet"]["pending_consequences"]["actions"]
            .as_array_mut()
            .unwrap()
            .push(other_proposal);
        let view = compact(&multiple, &context, false).unwrap();
        assert_eq!(
            view["decision_packet"]["ready_actions"],
            multiple["decision_packet"]["ready_actions"]
        );
        assert_eq!(
            view["decision_packet"]["pending_consequences"]["actions"],
            json!(peers)
        );
    }
    #[test]
    fn compact_preserves_peer_restrictions_claims_and_unknown_material() {
        let selected = json!({"operation_id":"independent.write","source_owner":"action-owner","effects":["owned-write"],
            "arguments":{"destination":"exact","baseline":"current","new_owner_material":{"stop":"preserve-foreign"}},
            "authority":{"scope":"exact"},"source_requests":[],"expected_dependency_revision":"revision"});
        let peer = json!({"operation_id":"peer.recover","effects":["peer-effect"],"recovery":"exact-path"});
        let question = json!({"id":"peer-judgment","question":"Which current source?","material":{"sources":["a","b"]}});
        let blockers = json!([{"code":"review-required","owner":"missing-reviewer","affects":["claim:complete"],"recovery":"independent-review"},
            {"code":"foreign-write-forbidden","owner":"independent-source","affects":["effect:foreign-write"]},
            {"code":"publication-required","owner":"action-owner","affects":["claim:published"]}]);
        let full = json!({"capability_contract":{"large_optional_schema":"detail"},
            "arbitrary_owner_view":{"requests":[{"kind":"agentic-workspace/public-request/v1","owner":"independent-source","arguments":{"source":"current"}}]},
            "decision_packet":{"status":"actionable","primary_action":selected,"decision_request":null,
                "blockers":blockers,"claim_boundary":{"allowed":[],"blocked":["complete"]},
                "pending_consequences":{"actions":[selected,peer],"decisions":[question],"blockers":blockers}}});
        let view = compact(&full, &json!({"target":"fixture","task":"bounded"}), true).unwrap();
        let packet = &view["decision_packet"];
        assert_eq!(packet["blockers"], blockers);
        assert_eq!(
            packet["claim_boundary"],
            full["decision_packet"]["claim_boundary"]
        );
        assert_eq!(packet["primary_action"]["arguments"], selected["arguments"]);
        assert_eq!(packet["primary_action"]["authority"], selected["authority"]);
        assert_eq!(packet["pending_consequences"]["actions"], json!([peer]));
        assert_eq!(
            packet["pending_consequences"]["decisions"],
            json!([question])
        );
        assert!(view.get("capability_contract").is_none());
        let recovery = view["consequence_recovery"].as_array().unwrap();
        let current = recovery
            .iter()
            .find(|r| r["owner"] == "independent-source")
            .unwrap();
        assert_eq!(current["status"], "current-owner-route");
        assert_eq!(current["routes"][0]["selector"], "/arbitrary_owner_view");
        assert_eq!(
            current["routes"][0]["reference"],
            view["detail_refs"]["/arbitrary_owner_view"]
        );
        assert_eq!(
            recovery
                .iter()
                .find(|r| r["owner"] == "missing-reviewer")
                .unwrap()["status"],
            "public-owner-route-unavailable"
        );
        let action_route = recovery
            .iter()
            .find(|r| r["owner"] == "action-owner")
            .unwrap();
        assert_eq!(
            action_route["routes"][0]["selector"],
            "/decision_packet/primary_action"
        );
    }
    #[test]
    fn availability_matches_exact_extent_only_and_does_not_discover_sources() {
        let whole = source_material(&json!("AGENTS.md"), b"whole source", "whole source", None);
        let fragment = source_material(
            &json!("AGENTS.md"),
            b"whole source",
            "source",
            Some("instruction-body"),
        );
        let assertion =
            json!({"reference":"AGENTS.md","revision":whole["revision"],"extent":"whole-source"});
        let a: SourceAvailability = serde_json::from_value(assertion.clone()).unwrap();
        assert!(a.matches(&whole));
        assert!(a.matches(&fragment));
        for (field, value) in [
            ("reference", json!("other.md")),
            ("revision", json!("sha256:wrong")),
            ("extent", json!("summary")),
            ("extent", json!("reference-only")),
            ("extent", json!("unknown")),
            ("extent", json!("exact-fragment")),
            ("content_revision", json!("truncated")),
        ] {
            let mut wrong = assertion.clone();
            wrong[field] = value;
            let a: SourceAvailability = serde_json::from_value(wrong).unwrap();
            assert!(!a.matches(&whole));
            assert!(!a.matches(&fragment));
        }
        let mut exact = assertion;
        exact["extent"] = json!("exact-fragment");
        exact["selector"] = fragment["selector"].clone();
        exact["content_revision"] = fragment["content_revision"].clone();
        let a: SourceAvailability = serde_json::from_value(exact.clone()).unwrap();
        assert!(a.matches(&fragment));
        assert!(!a.matches(&whole));
        assert!(!a.matches(&Value::Null));
        exact["selector"] = json!("other-section");
        assert!(
            !serde_json::from_value::<SourceAvailability>(exact)
                .unwrap()
                .matches(&fragment)
        );
    }

    #[test]
    fn delivery_tokens_bind_work_and_source_without_discharging_restrictions() {
        let original = json!({"decision_packet":{
            "semantic_task_routes":{"task_identity":{"id":"work-a"}},
            "status":"blocked","primary_action":null,
            "blockers":[{"code":"reconcile","affects":["claim:complete"]}],
            "claim_boundary":{"blocked":["complete"]},
            "material":{"startup-adapter":{"text":"policy".repeat(60)},
                "scoped-instructions":[{"guidance":"instruction".repeat(40)}]}}});
        let mut first = original.clone();
        apply_delivery(&mut first, &[], &[]).unwrap();
        let refs: Vec<String> = first["delivery_refs"]
            .as_array()
            .unwrap()
            .iter()
            .map(|r| r.as_str().unwrap().to_owned())
            .collect();
        let mut repeated = original.clone();
        apply_delivery(&mut repeated, &refs, &[]).unwrap();
        for key in ["status", "primary_action", "blockers", "claim_boundary"] {
            assert_eq!(
                repeated["decision_packet"][key],
                original["decision_packet"][key]
            );
        }
        assert!(
            repeated["decision_packet"]["material"]["startup-adapter"]
                .get("text")
                .is_none()
        );
        let mut forged = original.clone();
        apply_delivery(&mut forged, &["forged".into()], &[]).unwrap();
        assert_eq!(
            forged["decision_packet"]["material"],
            first["decision_packet"]["material"]
        );
        for pointer in [
            "/decision_packet/semantic_task_routes/task_identity/id",
            "/decision_packet/material/startup-adapter/text",
        ] {
            let mut changed = original.clone();
            *changed.pointer_mut(pointer).unwrap() = json!("new work or source".repeat(40));
            apply_delivery(&mut changed, &refs, &[]).unwrap();
            assert!(
                changed["decision_packet"]["material"]["startup-adapter"]
                    .get("text")
                    .is_some()
            );
        }
    }
}
