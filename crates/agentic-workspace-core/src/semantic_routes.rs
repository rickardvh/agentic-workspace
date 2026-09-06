//! Read-only public route requests. Hosts admit declarations and current work;
//! clients choose only a branch or applicability posture and declared leaves.
use crate::{
    CoreError, CurrentWorkIdentity, SemanticRouteSource, compile_value, digest,
    normalize_semantic_routes, prepare_request_value,
};
use serde::Deserialize;
use serde_json::{Value, json};
use std::collections::BTreeSet;

#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct Input {
    current_work: CurrentWorkIdentity,
    source: SemanticRouteSource,
    request: Option<Value>,
}

pub fn view(value: Value) -> Result<Value, CoreError> {
    resolve(value).map(|(view, _)| view)
}

pub(crate) fn resolve(value: Value) -> Result<(Value, Value), CoreError> {
    let input: Input = serde_json::from_value(value).map_err(|e| CoreError::new(e.to_string()))?;
    let mut intent = json!({"current_work":input.current_work, "semantic_route_source":{
        "revision":input.source.revision, "routes":input.source.routes}});
    normalize_semantic_routes(&mut intent)?;
    let source = intent["semantic_route_source"].clone();
    let work = intent["current_work"].clone();
    intent
        .as_object_mut()
        .unwrap()
        .remove("semantic_task_routes");
    let schema: Value = serde_json::from_str(include_str!(
        "../../../src/agentic_workspace/contracts/schemas/source_decision_input.schema.json"
    ))
    .expect("checked schema");
    let mut requests = Vec::new();
    for (kind, definition) in [
        ("semantic-routes/discover/v1", "semantic_route_discovery"),
        ("semantic-routes/select/v1", "semantic_route_choice"),
    ] {
        let mut shape = schema["$defs"][definition].clone();
        shape["$schema"] = json!("https://json-schema.org/draft/2020-12/schema");
        shape["$defs"] = json!({"route_id":schema["$defs"]["route_id"]});
        requests.push(json!({"kind":kind, "result_kind":"agentic-workspace/semantic-route-result/v1", "input_schema":shape}));
    }
    let owner_revision = digest(&json!(requests))?;
    let mut contract = json!({"kind":"agentic-workspace/capability-contract/v1", "revision":"pending", "owners":[{
        "owner":"semantic-routes", "revision":owner_revision, "requests":requests}]});
    contract["revision"] = json!(digest(&contract)?);
    let mut templates = Vec::new();
    for (kind, arguments) in [
        ("semantic-routes/discover/v1", json!({"parent":""})),
        (
            "semantic-routes/select/v1",
            json!({"posture":"unresolved", "routes":[]}),
        ),
    ] {
        templates.push(json!({"kind":"agentic-workspace/public-request/v1", "id":kind,
            "owner":"semantic-routes", "owner_revision":owner_revision, "source_revision":source["revision"],
            "capability_revision":contract["revision"], "task_identity":work, "request_kind":kind, "arguments":arguments}));
    }
    let mut parent = String::new();
    let mut after = String::new();
    let mut request_identity = Value::Null;
    let mut stale = false;
    let mut contributions = Vec::new();
    if let Some(request) = input.request {
        // The generic request validator checks all public fields and declared
        // arguments. Historical task binding is checked below against the host.
        let prepared = prepare_request_value(
            json!({"request":request, "current_work":request["task_identity"], "capability_contract":contract}),
        )?;
        if request["owner"] != "semantic-routes" {
            return Err(CoreError::new("route request names another owner"));
        }
        request_identity = prepared["identity"].clone();
        stale =
            request["task_identity"] != work || request["source_revision"] != source["revision"];
        if request["request_kind"] == "semantic-routes/select/v1" {
            intent["semantic_task_routes"] = json!({"posture":request["arguments"]["posture"], "routes":request["arguments"]["routes"],
                "task_identity":request["task_identity"], "source_revision":request["source_revision"],
                "provenance":"agent-selected", "authority_effect":"applicability-only"});
            let fact = normalize_semantic_routes(&mut intent)?.expect("route source supplied");
            stale |= fact["status"] != "current";
            // Preserve the received selection for the single final compile's
            // currentness verdict rather than relabeling it as current.
            intent["semantic_task_routes"] = json!({"posture":request["arguments"]["posture"], "routes":request["arguments"]["routes"],
                "task_identity":request["task_identity"], "source_revision":request["source_revision"],
                "provenance":"agent-selected", "authority_effect":"applicability-only"});
        } else if !stale {
            parent = request["arguments"]["parent"].as_str().unwrap().to_owned();
            after = request["arguments"]["after"]
                .as_str()
                .unwrap_or("")
                .to_owned();
        }
        if !stale {
            intent["public_request"] = prepared["request"].clone();
            contributions.push(json!({"owner":"semantic-routes", "revision":source["revision"], "settled":true,
                "request_response":{"request_identity":request_identity,"status":"settled","consequence_ids":[]}}));
        }
    }
    let prefix = if parent.is_empty() {
        String::new()
    } else {
        format!("{parent}/")
    };
    let children: BTreeSet<_> = input
        .source
        .routes
        .iter()
        .filter_map(|route| {
            route
                .strip_prefix(&prefix)
                .and_then(|suffix| suffix.split('/').next())
                .map(|child| format!("{prefix}{child}"))
        })
        .collect();
    let remaining: Vec<_> = children.into_iter().filter(|id| id > &after).collect();
    let truncated = remaining.len() > 16;
    let children: Vec<_> = remaining
        .into_iter()
        .take(16)
        .map(|id| json!({"leaf":input.source.routes.contains(&id), "id":id}))
        .collect();
    let next_after = if truncated {
        children.last().map(|child| child["id"].clone())
    } else {
        None
    };
    let decision = compile_value(
        json!({"contributions":contributions, "intent":intent.clone(), "capability_contract":contract}),
    )?;
    intent.as_object_mut().unwrap().remove("public_request");
    Ok((
        json!({"kind":"agentic-workspace/semantic-route-result/v1", "status":if stale {"stale"} else {"current"},
        "request_identity":request_identity, "decision":decision, "requests":templates, "capability_contract":contract,
        "discovery":{"parent":parent,"children":children,"next_after":next_after}, "authority_effect":"applicability-only"}),
        intent,
    ))
}
