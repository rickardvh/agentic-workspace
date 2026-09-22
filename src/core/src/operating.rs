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
    fn requests(value: &Value, found: &mut Vec<Value>, depth: usize) {
        if depth > 12 || found.len() >= 512 {
            return;
        }
        if let Some(object) = value.as_object() {
            for (key, child) in object {
                if key == "requests" || key.ends_with("_requests") {
                    for request in child.as_array().into_iter().flatten() {
                        if request["kind"] == "agentic-workspace/public-request/v1"
                            && !found.contains(request)
                        {
                            found.push(request.clone());
                        }
                    }
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
    let mut owners = std::collections::BTreeMap::<String, Vec<Value>>::new();
    for blocker in full["decision_packet"]["blockers"]
        .as_array()
        .into_iter()
        .flatten()
    {
        let owner = blocker["recovery"]
            .as_str()
            .and_then(|r| r.strip_prefix("public-owner:"))
            .or_else(|| blocker["owner"].as_str());
        if let Some(owner) = owner {
            owners.entry(owner.to_owned()).or_default().push(json!({
                "consequence_id":blocker["consequence_id"], "affects":blocker["affects"]
            }));
        }
    }
    owners.into_iter().map(|(owner, consequences)| {
        let mut routes = Vec::new();
        for (key, value) in full.as_object().into_iter().flatten() {
            if matches!(key.as_str(), "decision_packet" | "capability_contract" | "decision_sources") {
                continue;
            }
            if has_request(value, &owner) {
                let selector = format!("/{}", key.replace('~', "~0").replace('/', "~1"));
                let selected = entries(full, context)?.into_iter().find(|e| e["selector"] == selector).unwrap();
                routes.push(json!({"selector":selector,"reference":selected["reference"]}));
            }
        }
        if routes.is_empty() {
            let mut selectors = vec!["/decision_packet/primary_action".to_owned(),
                "/decision_packet/decision_request".to_owned()];
            if full["decision_packet"]["primary_action"].is_null() {
                selectors.extend((0..full["decision_packet"]["ready_actions"].as_array().map_or(0, Vec::len))
                    .map(|index| format!("/decision_packet/ready_actions/{index}")));
            }
            for selector in selectors {
                let Some(envelope) = full.pointer(&selector).filter(|v| v.is_object()) else { continue };
                if (action_selector(&selector) && envelope["source_owner"] == owner)
                    || (selector == "/decision_packet/decision_request" && envelope["owner"] == owner)
                {
                    routes.push(json!({"selector":selector,"reference":reference(context, &selector, envelope)?}));
                }
            }
        }
        Ok(json!({"owner":owner,"consequences":consequences,
            "status":if routes.is_empty(){"public-owner-route-unavailable"}else{"current-owner-route"},
            "routes":routes,
            "authority":"Discovery only; restrictions remain until the current owner admits their resolution."}))
    }).collect()
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
    let mut result = json!({"decision_packet":packet,"detail_refs":refs,
        "reentry":{"target":context["target"],"task":context["task"],"changed":context["changed"]},
        "detail_rule":"Exact optional detail: send its reference with the same explicit work context, or use carried/full projection. References grant no authority and are freshly reobserved."});
    if let Some(advice) = full["memory"].get("advisory_context") {
        result["advisory_context"] = advice.clone();
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
        result["proof_retention"] = json!({"status":retention["status"],"candidate_count":retention["sources"].as_object().map_or(0,|s|s.len()),"reference":result["detail_refs"]["/verification"],"authority":"Current Verification disposition required; discovery grants no deletion or proof authority."});
    }
    let recovery = consequence_recovery(full, context)?;
    if !recovery.is_empty() {
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
            "question" if selector == "/decision_packet/decision_request" => {
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
    Ok(
        json!({"identity":identity,"status":"current","reference":selected["reference"],"value":selected["envelope"],
        "authority_effect":"none","continuation":"Use the exact reference through the existing owner answer/invoke path; a request template still requires its owner's requested input. Resolution never executes or retries."}),
    )
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
        return operate_selected(next, false, detail);
    }
    if answer.is_some() || action_selector(selector) {
        return Err(error(
            "detail selection does not accept answers or invoke actions",
        ));
    }
    Ok(
        json!({"reference":selected,"selector":selector,"value":if lazy {current.pointer(selector).cloned().unwrap_or(Value::Null)} else {selected_entry["envelope"].clone()},"currentness":"reobserved","authority":"detail-only"}),
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
    let mut result = operate_current(value, invoking, detail)?;
    apply_delivery(&mut result, &delivered)?;
    if let Some(continuation) = result
        .get_mut("continuation")
        .and_then(|c| c.get_mut("result"))
    {
        apply_delivery(continuation, &delivered)?;
    }
    Ok(result)
}

fn apply_delivery(result: &mut Value, delivered: &[String]) -> Result<(), CoreError> {
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
            } else if owner == "startup-adapter" {
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
                // A delivery token is not worth retaining for tiny prose.
                if !row[field].as_str().is_some_and(|s| s.len() > 256) {
                    continue;
                }
                let reference = digest(
                    &json!({"producer":delivery_producer(),"work":work,"owner":owner,"source":row}),
                )?;
                refs.push(reference.clone());
                if delivered.contains(&reference) {
                    row.as_object_mut().unwrap().remove(field);
                    row["delivery"] = json!({"reference":reference,"status":"already-delivered","authority":"presentation-only; no semantic satisfaction"});
                }
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
                if carried_context.get(key) != Some(normalized_target.as_ref().unwrap_or(supplied))
                {
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
        return Ok(project_invocation(
            native_public::invoke_selected(value, &resolution(&projection, detail)),
            &projection,
            detail,
        ));
    }
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
        match if projection == "full" && detail.is_some() {
            Ok(full)
        } else {
            project_start(full, context, projection)
        } {
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
    fn public_owner_identity_resolves_exact_requests_without_rebinding() {
        let root = temp_root("owner-reference");
        let mut context = json!({"target":root,"task":"inspect a current owner"});
        context["reference"] = json!("owner:request:semantic-routes:semantic-routes/discover/v1");
        let resolved = start(context.clone()).unwrap();
        assert_eq!(resolved["status"], "current");
        assert_eq!(resolved["value"]["owner"], "semantic-routes");
        assert_eq!(resolved["authority_effect"], "none");
        context["reference"] = resolved["reference"].clone();
        let exact = start(context.clone()).unwrap();
        assert_eq!(exact["value"], resolved["value"]);
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
    fn delivery_tokens_bind_work_and_source_without_discharging_restrictions() {
        let original = json!({"decision_packet":{
            "semantic_task_routes":{"task_identity":{"id":"work-a"}},
            "status":"blocked","primary_action":null,
            "blockers":[{"code":"reconcile","affects":["claim:complete"]}],
            "claim_boundary":{"blocked":["complete"]},
            "material":{"startup-adapter":{"text":"policy".repeat(60)},
                "scoped-instructions":[{"guidance":"instruction".repeat(40)}]}}});
        let mut first = original.clone();
        apply_delivery(&mut first, &[]).unwrap();
        let refs: Vec<String> = first["delivery_refs"]
            .as_array()
            .unwrap()
            .iter()
            .map(|r| r.as_str().unwrap().to_owned())
            .collect();
        let mut repeated = original.clone();
        apply_delivery(&mut repeated, &refs).unwrap();
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
        apply_delivery(&mut forged, &["forged".into()]).unwrap();
        assert_eq!(
            forged["decision_packet"]["material"],
            original["decision_packet"]["material"]
        );
        for pointer in [
            "/decision_packet/semantic_task_routes/task_identity/id",
            "/decision_packet/material/startup-adapter/text",
        ] {
            let mut changed = original.clone();
            *changed.pointer_mut(pointer).unwrap() = json!("new work or source".repeat(40));
            apply_delivery(&mut changed, &refs).unwrap();
            assert!(
                changed["decision_packet"]["material"]["startup-adapter"]
                    .get("text")
                    .is_some()
            );
        }
    }
}
