//! Presentation and immutable transport over native owners, never an authority.
use crate::{CoreError, digest, native_public};
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

fn reference(context: &Value, selector: &str, envelope: &Value) -> Result<String, CoreError> {
    digest(&json!({"kind":CARRIAGE,"context":context,"selector":selector,"envelope":envelope}))
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
    // Exact top-level selectors expose optional detail without a catalogue of
    // every nested schema/procedure. Their bytes remain in this local carrier.
    for (key, value) in full.as_object().into_iter().flatten() {
        let selector = format!("/{}", key.replace('~', "~0").replace('/', "~1"));
        result.push(entry(context, &selector, value)?);
    }
    Ok(result)
}

fn compact(full: &Value, context: &Value, carried: bool) -> Result<Value, CoreError> {
    if !full["decision_packet"].is_object() {
        return Ok(full.clone()); // Compatibility/recovery is already bounded.
    }
    let mut packet = full["decision_packet"].clone();
    let object = packet.as_object_mut().unwrap();
    for key in [
        "operation_revisions",
        "owner_states",
        "capability_revision",
        "ready_actions",
    ] {
        object.remove(key);
    }
    // Blockers appear once. Peer actions and questions remain visible: selection
    // never erases a competing restriction or unresolved judgment.
    if let Some(pending) = packet["pending_consequences"].as_object_mut() {
        pending.remove("blockers");
    }
    let mut refs = serde_json::Map::new();
    for item in entries(full, context)? {
        let selector = item["selector"].as_str().unwrap();
        refs.insert(selector.to_owned(), item["reference"].clone());
        if carried && selector == "/decision_packet/primary_action" {
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
            packet["primary_action"] = action;
        }
        if carried && selector == "/decision_packet/decision_request" {
            let question = &mut packet["decision_request"];
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
    // The selected question/action already appears above; retain other peers.
    for (field, selected) in [
        ("actions", "primary_action"),
        ("decisions", "decision_request"),
    ] {
        let selected = &full["decision_packet"][selected];
        if let Some(values) = packet["pending_consequences"][field].as_array_mut() {
            values.retain(|value| value != selected);
        }
    }
    Ok(json!({"decision_packet":packet,"detail_refs":refs,
        "reentry":{"target":context["target"],"task":context["task"],"changed":context["changed"]},
        "detail_rule":"Exact optional detail: use carried reference, or fresh start with projection full. Carriage grants no authority."}))
}

/// Shared by JSON and all thin consumers. The optional carrier is disposable;
/// native owners reconstruct and revalidate every selected envelope.
pub fn start(value: Value) -> Result<Value, CoreError> {
    operate(value, false)
}

pub fn invoke(value: Value) -> Result<Value, CoreError> {
    operate(value, true)
}

fn operate(mut value: Value, invoking: bool) -> Result<Value, CoreError> {
    let object = value
        .as_object_mut()
        .ok_or_else(|| error("expected operating input object"))?;
    let projection = object.remove("projection").unwrap_or(json!("compact"));
    if ![json!("compact"), json!("full"), json!("carried")].contains(&projection) {
        return Err(error("unknown operating projection"));
    }
    let selected = object.remove("reference");
    let answer = object.remove("answer");
    let field = if invoking { "invocation" } else { "request" };
    if let Some(selected) = selected {
        let carrier: Carriage = serde_json::from_value(
            object
                .remove(field)
                .ok_or_else(|| error("carriage missing"))?,
        )
        .map_err(|_| error("invalid carriage"))?;
        if carrier.kind != CARRIAGE {
            return Err(error("unknown carriage kind"));
        }
        let context = carrier
            .context
            .as_object()
            .ok_or_else(|| error("invalid carried context"))?;
        if context
            .keys()
            .any(|key| !["target", "task", "changed", "request"].contains(&key.as_str()))
        {
            return Err(error("unknown carried context field"));
        }
        // Explicit context is either identical or rejected, never silently
        // treated as a task switch. A new work context requires fresh start.
        for (key, supplied) in object.iter() {
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
            if context.get(key) != Some(normalized_target.as_ref().unwrap_or(supplied)) {
                return Err(error("carriage work context changed"));
            }
        }
        let matches: Vec<_> = carrier
            .envelopes
            .iter()
            .filter(|entry| entry["reference"] == selected)
            .collect();
        if matches.len() != 1 {
            return Err(error("unknown or ambiguous carried reference"));
        }
        let selected_entry = matches[0];
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
        if invoking {
            if selector != "/decision_packet/primary_action" || answer.is_some() {
                return Err(error(
                    "invoke requires an exact carried action without answer",
                ));
            }
            let mut execution = carrier.context.clone();
            execution.as_object_mut().unwrap().remove("request");
            execution["invocation"] = selected_entry["envelope"].clone();
            // Existing native admission reobserves the execution snapshot and
            // preserves replay/recovery; a carriage digest is not a grant.
            return native_public::invoke(execution);
        }
        let current = native_public::start(carrier.context.clone())?;
        if current.pointer(selector) != Some(&selected_entry["envelope"]) {
            return Err(error("carried reference stale or not owner-issued"));
        }
        if selector == "/decision_packet/decision_request" {
            let answer = answer.ok_or_else(|| error("bounded answer required"))?;
            if selected_entry["envelope"]["response_request"]["arguments"]
                .get("answer")
                .is_some()
            {
                return Err(error(
                    "owner already supplied answer; immutable material cannot be replaced",
                ));
            }
            let answered =
                crate::answer_decision_value(json!({"decision":current["decision_packet"],
                "question":selected_entry["envelope"]["consequence_id"],"answer":answer,
                "capability_contract":current["capability_contract"]}))?["request"]
                    .clone();
            let mut next = carrier.context.clone();
            let mut requests = match next.get("request").filter(|v| !v.is_null()) {
                Some(Value::Array(items)) => items.clone(),
                Some(item) => vec![item.clone()],
                None => vec![],
            };
            requests.retain(|request| {
                !(request["owner"] == answered["owner"]
                    && request["request_kind"] == answered["request_kind"])
            });
            requests.push(answered);
            next["request"] = json!(requests);
            next["projection"] = projection;
            return operate(next, false);
        }
        if answer.is_some() || selector == "/decision_packet/primary_action" {
            return Err(error(
                "detail selection does not accept answers or invoke actions",
            ));
        }
        return Ok(
            json!({"reference":selected,"selector":selector,"value":selected_entry["envelope"],"currentness":"reobserved","authority":"detail-only"}),
        );
    }
    if answer.is_some() {
        return Err(error("answer requires exact carried reference"));
    }
    if invoking {
        return native_public::invoke(value);
    }
    let full = native_public::start(value.clone())?;
    if projection == "full" {
        return Ok(full);
    }
    // Canonicalize target and defaults once so unchanged context is portable
    // between processes without relying on the next process working directory.
    value["target"] = json!(
        std::fs::canonicalize(
            value["target"]
                .as_str()
                .ok_or_else(|| error("target missing"))?
        )
        .map_err(|e| error(&e.to_string()))?
    );
    if value.get("task").is_none() {
        value["task"] = json!("");
    }
    if value.get("changed").is_none() {
        value["changed"] = json!([]);
    }
    value.as_object_mut().unwrap().remove("invocation");
    let view = compact(&full, &value, projection == "carried")?;
    if projection == "carried" {
        return Ok(
            json!({"view":view,"carriage":{"kind":CARRIAGE,"context":value,"envelopes":entries(&full, &value)?}}),
        );
    }
    Ok(view)
}

#[cfg(test)]
mod tests {
    use super::*;

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
    fn compact_preserves_peer_restrictions_claims_and_unknown_material() {
        let selected = json!({"operation_id":"independent.write","effects":["owned-write"],
            "arguments":{"destination":"exact","baseline":"current","new_owner_material":{"stop":"preserve-foreign"}},
            "authority":{"scope":"exact"},"source_requests":[],"expected_dependency_revision":"revision"});
        let peer = json!({"operation_id":"peer.recover","effects":["peer-effect"],"recovery":"exact-path"});
        let question = json!({"id":"peer-judgment","question":"Which current source?","material":{"sources":["a","b"]}});
        let blockers = json!([{"code":"review-required","affects":["claim:complete"],"recovery":"independent-review"},
            {"code":"foreign-write-forbidden","affects":["effect:foreign-write"]}]);
        let full = json!({"capability_contract":{"large_optional_schema":"detail"},
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
    }
}
