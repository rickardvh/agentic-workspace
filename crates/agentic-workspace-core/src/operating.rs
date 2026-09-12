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
        "detail_rule":"Exact optional detail: send its reference with the same explicit work context, or use carried/full projection. References grant no authority and are freshly reobserved."}))
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

fn normalize_context(mut value: Value) -> Result<Value, CoreError> {
    let object = value
        .as_object_mut()
        .ok_or_else(|| error("expected operating input object"))?;
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
    object.remove("invocation");
    if value["request"].is_null() {
        object.remove("request");
    }
    Ok(value)
}

fn select_entry(full: &Value, context: &Value, selected: &Value) -> Result<Value, CoreError> {
    let mut matches: Vec<_> = entries(full, context)?
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
    if json!(reference(
        context,
        selector,
        &selected_entry["envelope"]
    )?) != *selected
    {
        return Err(error("altered operating reference"));
    }
    Ok(selected_entry)
}

fn use_selected(
    context: Value,
    current: Value,
    selected: Value,
    selected_entry: Value,
    answer: Option<Value>,
    invoking: bool,
    projection: &Value,
) -> Result<Value, CoreError> {
    let selector = selected_entry["selector"]
        .as_str()
        .ok_or_else(|| error("invalid selector"))?;
    if current.pointer(selector) != Some(&selected_entry["envelope"]) {
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
            native_public::invoke_operating(execution),
            projection,
        ));
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
        let answered = crate::answer_decision_value(json!({
            "decision":current["decision_packet"],
            "question":selected_entry["envelope"]["consequence_id"],
            "answer":answer,
            "capability_contract":current["capability_contract"]
        }))?["request"]
            .clone();
        let mut next = context;
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
        next["projection"] = projection.clone();
        return operate(next, false);
    }
    if answer.is_some() || action_selector(selector) {
        return Err(error(
            "detail selection does not accept answers or invoke actions",
        ));
    }
    Ok(
        json!({"reference":selected,"selector":selector,"value":selected_entry["envelope"],"currentness":"reobserved","authority":"detail-only"}),
    )
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

fn operate(mut value: Value, invoking: bool) -> Result<Value, CoreError> {
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
    if let Some(selected) = selected {
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
            if carried_context
                .keys()
                .any(|key| !["target", "task", "changed", "request"].contains(&key.as_str()))
            {
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
                if carried_context.get(key) != Some(normalized_target.as_ref().unwrap_or(supplied)) {
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
            let current = native_public::start(carrier.context.clone())?;
            return use_selected(
                carrier.context,
                current,
                selected,
                selected_entry,
                answer,
                invoking,
                &projection,
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
        let current = native_public::start(context.clone())?;
        let selected_entry = select_entry(&current, &context, &selected)?;
        return use_selected(
            context,
            current,
            selected,
            selected_entry,
            answer,
            invoking,
            &projection,
        );
    }
    if answer.is_some() {
        return Err(error("answer requires exact operating reference"));
    }
    if invoking {
        return Ok(project_invocation(
            native_public::invoke_operating(value),
            &projection,
        ));
    }
    let full = native_public::start(value.clone())?;
    project_start(full, value, &projection)
}

fn project_invocation(mut result: Value, projection: &Value) -> Value {
    if result["continuation"]["status"] == "current" {
        let full = result["continuation"]["result"].take();
        let context = result["continuation"]["context"].clone();
        match project_start(full, context, projection) {
            Ok(projected) => result["continuation"]["result"] = projected,
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

fn project_start(full: Value, value: Value, projection: &Value) -> Result<Value, CoreError> {
    if projection == "full" {
        return Ok(full);
    }
    let value = normalize_context(value)?;
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

    use std::path::PathBuf;

    #[test]
    fn compact_reference_reobserves_detail_without_carriage() {
        let root = temp_root("reference-detail");
        let context = json!({"target":root,"task":"inspect current work","changed":[]});
        let view = start(context.clone()).unwrap();
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
