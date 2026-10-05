//! Exact public owner carriage over the existing resource primitive. No sequence
//! or skill identity lives here; proposal and effect remain separate operations.
use crate::{CoreError, digest};
use serde_json::{Value, json};
use std::path::Path;

pub(crate) const OWNER: &str = "workspace-resources";
const REQUEST: &str = "resources/propose/v1";
const OPERATIONS: &[&str] = &[
    "scratch-create",
    "scratch-remove",
    "scratch-prune",
    "scratch-retain",
    "scratch-release",
    "worktree-create",
    "worktree-remove",
];

pub(crate) fn operation(id: &Value) -> bool {
    OPERATIONS
        .iter()
        .any(|name| id == &format!("workspace.resources.{name}"))
}

fn revision() -> Result<String, CoreError> {
    digest(&json!([
        include_str!("native_resource_owner.rs"),
        include_str!("native_resources.rs")
    ]))
}

pub(crate) fn contract() -> Result<Value, CoreError> {
    let shape = json!({"$schema":"https://json-schema.org/draft/2020-12/schema",
        "type":"object","required":["request"],"additionalProperties":false,
        "properties":{"request":crate::native_resources::request_schema()}});
    let operations: Vec<_> = OPERATIONS.iter().map(|name| json!({
        "id":format!("workspace.resources.{name}"),"semantic_revision":"resource-owner-v1",
        "input_schema":{"$schema":"https://json-schema.org/draft/2020-12/schema","type":"object",
            "required":["target","task","changed","request"],"additionalProperties":false,
            "properties":{"target":{"type":"string"},"task":{"type":"string"},
                "changed":{"type":"array","items":{"type":"string"}},"request":{"type":"object"}}},
        "result_kind":"agentic-workspace/resource-result/v1","effects":["task-resource"],"reads":[OWNER]
    })).collect();
    let rev = revision()?;
    Ok(
        json!({"kind":"agentic-workspace/capability-contract/v1","revision":rev,
        "owners":[{"owner":OWNER,"revision":rev,"domains":[OWNER],
            "effects":[{"id":"task-resource","domain":OWNER}],"operations":operations,
            "requests":[{"kind":REQUEST,"input_schema":shape,"result_kind":"agentic-workspace/resource-proposal/v1"}]}],
        "restriction_authorities":[{"owner":OWNER,"affects":["effect:task-resource"]}]}),
    )
}

pub(crate) fn view(
    target: &Path,
    task: &str,
    changed: &[String],
    work: &Value,
    contract: &Value,
    request: Option<&Value>,
    planning_request: Option<&Value>,
) -> Result<Value, CoreError> {
    let rev = revision()?;
    let template = json!({"kind":"agentic-workspace/public-request/v1","id":REQUEST,
        "owner":OWNER,"owner_revision":rev,"source_revision":rev,"capability_revision":contract["revision"],
        "task_identity":work,"request_kind":REQUEST,"arguments":{"request":{"operation":"audit"}}});
    let mut result = json!({"requests":[template],"status":"unselected",
        "contribution":{"owner":OWNER,"revision":rev,"relevant":request.is_some(),"actions":[]}});
    let Some(request) = request else {
        return Ok(result);
    };
    crate::prepare_request_value(
        json!({"request":request,"current_work":work,"capability_contract":contract}),
    )?;
    if request["id"] != REQUEST || request["source_revision"] != rev {
        return Err(CoreError::new(
            "resource request identity or source is stale",
        ));
    }
    let mut args = request["arguments"]["request"].clone();
    if args["operation"] == "worktree-create"
        && let Some(planning_request) = planning_request
    {
        if args
            .get("planning_request")
            .is_some_and(|r| r != planning_request)
        {
            return Err(CoreError::new(
                "resource Planning relation differs from current work; reobserve",
            ));
        }
        args["planning_request"] = planning_request.clone();
    }
    if args.get("expected_revision").is_some() {
        return Err(CoreError::new(
            "resource proposal cannot execute; invoke the exact returned action",
        ));
    }
    let proposal = crate::native_resources::view(
        json!({"target":target,"task":task,"changed":changed,"request":args}),
    )?;
    result["status"] = json!("observed");
    result["contribution"]["revision"] = json!(digest(&proposal)?);
    result["contribution"]["blockers"] = json!(proposal["blockers"].as_array().into_iter().flatten().map(|message|
        json!({"code":"resource-owner-unresolved","message":message,"affects":["effect:task-resource"]})).collect::<Vec<_>>());
    if proposal["action"].is_object() {
        result["contribution"]["actions"] = json!([{
            "operation_id":format!("workspace.resources.{}",args["operation"].as_str().unwrap_or("")),
            "dependency_revision":proposal["revision"],"arguments":proposal["action"],
            "effects":["task-resource"],"source_requests":[request]}]);
    }
    result["proposal"] = proposal;
    Ok(result)
}

pub(crate) fn execute(invocation: &Value) -> Result<Value, CoreError> {
    let result = crate::native_resources::view(invocation["arguments"].clone())?;
    if result["effect_outcome"] != "committed" {
        return Err(CoreError::new(
            "resource effect not established; preserve exact proposal and reobserve",
        ));
    }
    let mut value = json!({"kind":"agentic-workspace/resource-result/v1",
        "operation":result["operation"],"path":result["path"],
        "authority":"The exact owner effect is established. Resource custody does not authorize cleanup; every later effect requires fresh admission."});
    if let Some(state) = result.get("resource") {
        value["resource"] = state.clone();
    }
    if let Some(environment) = result.get("build_environment") {
        value["build_environment"] = environment.clone();
    }
    if let Some(outputs) = result.get("disposable_outputs") {
        value["disposable_outputs"] = outputs.clone();
    }
    if matches!(
        result["operation"].as_str(),
        Some("scratch-create" | "worktree-create")
    ) {
        // This is semantic input to the existing owner, not a new handle or
        // cleanup capability. The owner will reobserve policy and custody.
        value["next_step"] = json!({"reference":"owner:request:workspace-resources:resources/propose/v1",
            "answer_shape":{"request":{"operation":if result["operation"] == "scratch-create" {"scratch-retain"} else {"worktree-remove"},
                "path":invocation["arguments"]["request"]["path"]}},
            "operations":if result["operation"] == "scratch-create" {json!(["scratch-retain","scratch-release","scratch-remove"])} else {json!(["worktree-remove"])},
            "use":"Use this resource path now, or select this read-only owner reference with the returned continuation reentry. Answer with the desired listed operation and this path; retention/release also requires a reason. Selection never repeats creation or authorizes removal. Full resource diagnostics are available through this same owner."});
    }
    Ok(
        json!({"outcome":{"status":if result["kind"] == "agentic-workspace/resource-result/v1" {&result["status"]} else {&result["operation_result"]["status"]},
        "effects":if result["kind"] == "agentic-workspace/resource-result/v1" {&result["effects"]} else {&result["operation_result"]["effects"]},"value":value},"post_effect_changed_paths":[]}),
    )
}
