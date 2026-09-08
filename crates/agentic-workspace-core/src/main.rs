use std::io::{self, Read};

fn main() {
    let mut input = String::new();
    if let Err(error) = io::stdin().read_to_string(&mut input) {
        fail("transport-read", &error.to_string());
    }
    let request: serde_json::Value = match serde_json::from_str(&input) {
        Ok(value) => value,
        Err(error) => fail("invalid-json", &error.to_string()),
    };
    let started = std::time::Instant::now();
    let result = if request
        .as_object()
        .is_some_and(|v| v.len() == 1 && v.contains_key("session_logging_policy"))
    {
        agentic_workspace_core::maintainer_logging::policy(
            request["session_logging_policy"].clone(),
        )
    } else if request
        .as_object()
        .is_some_and(|v| v.len() == 1 && v.contains_key("assurance_applicability"))
    {
        agentic_workspace_core::assurance_applicability::view(
            request["assurance_applicability"].clone(),
        )
    } else if request
        .as_object()
        .is_some_and(|v| v.len() == 1 && v.contains_key("assignment_packet"))
    {
        agentic_workspace_core::assignment_packet::view(request["assignment_packet"].clone())
    } else if request
        .as_object()
        .is_some_and(|v| v.len() == 1 && v.contains_key("native_route_discovery"))
    {
        agentic_workspace_core::native_routes::discovery(request["native_route_discovery"].clone())
    } else if request
        .as_object()
        .is_some_and(|v| v.len() == 1 && v.contains_key("review_authentication"))
    {
        agentic_workspace_core::review_authentication::view(
            request["review_authentication"].clone(),
        )
    } else if request
        .as_object()
        .is_some_and(|v| v.len() == 1 && v.contains_key("verification_requirements"))
    {
        agentic_workspace_core::verification_requirements::view(
            request["verification_requirements"].clone(),
        )
    } else if request
        .as_object()
        .is_some_and(|v| v.len() == 1 && v.contains_key("separation_of_duty"))
    {
        agentic_workspace_core::separation_of_duty::view(request["separation_of_duty"].clone())
    } else if request
        .as_object()
        .is_some_and(|v| v.len() == 1 && v.contains_key("runtime_compatibility"))
    {
        agentic_workspace_core::runtime_compatibility::view(
            request["runtime_compatibility"].clone(),
        )
    } else if request
        .as_object()
        .is_some_and(|v| v.len() == 1 && v.contains_key("instruction_applicability"))
    {
        agentic_workspace_core::instruction_applicability::view(
            request["instruction_applicability"].clone(),
        )
    } else if request
        .as_object()
        .is_some_and(|v| v.len() == 1 && v.contains_key("proof_receipt"))
    {
        agentic_workspace_core::proof_receipt::view(request["proof_receipt"].clone())
    } else if request
        .as_object()
        .is_some_and(|v| v.len() == 1 && v.contains_key("task_requirements"))
    {
        agentic_workspace_core::task_requirements::view(request["task_requirements"].clone())
    } else if request
        .as_object()
        .is_some_and(|v| v.len() == 1 && v.contains_key("task_judgment"))
    {
        agentic_workspace_core::task_judgment::view(request["task_judgment"].clone())
    } else if request
        .as_object()
        .is_some_and(|v| v.len() == 1 && v.contains_key("proof_subject"))
    {
        agentic_workspace_core::proof_subject::view(request["proof_subject"].clone())
    } else if request
        .as_object()
        .is_some_and(|v| v.len() == 1 && v.contains_key("direct_task_subject"))
    {
        agentic_workspace_core::direct_task::view(request["direct_task_subject"].clone())
    } else if request
        .as_object()
        .is_some_and(|v| v.len() == 1 && v.contains_key("start"))
    {
        agentic_workspace_core::native_public::start(request["start"].clone())
    } else if request
        .as_object()
        .is_some_and(|v| v.len() == 1 && v.contains_key("invoke"))
    {
        agentic_workspace_core::native_public::invoke(request["invoke"].clone())
    } else if request
        .as_object()
        .is_some_and(|v| v.len() == 1 && v.contains_key("attribute_assignment_outcome"))
    {
        agentic_workspace_core::assignment::attribute_outcome(
            request["attribute_assignment_outcome"].clone(),
        )
    } else if request
        .as_object()
        .is_some_and(|v| v.len() == 1 && v.contains_key("assignment_policy"))
    {
        agentic_workspace_core::assignment_policy::resolve(&request["assignment_policy"])
    } else if request
        .as_object()
        .is_some_and(|v| v.len() == 1 && v.contains_key("local_source_overlay"))
    {
        Ok(agentic_workspace_core::assignment_policy::merge(
            &request["local_source_overlay"]["base"],
            &request["local_source_overlay"]["override"],
        ))
    } else if request
        .as_object()
        .is_some_and(|v| v.len() == 1 && v.contains_key("transport_sources"))
    {
        agentic_workspace_core::transport_source::decode_sources(&request["transport_sources"])
    } else if request
        .as_object()
        .is_some_and(|v| v.len() == 1 && v.contains_key("execution_configurations"))
    {
        agentic_workspace_core::assignment::configurations(
            request["execution_configurations"].clone(),
        )
    } else if request
        .as_object()
        .is_some_and(|v| v.len() == 1 && v.contains_key("replace_assignment"))
    {
        agentic_workspace_core::assignment::replace(request["replace_assignment"].clone())
    } else if request
        .as_object()
        .is_some_and(|v| v.len() == 1 && v.contains_key("admit_assignment_packet"))
    {
        agentic_workspace_core::assignment::admit(request["admit_assignment_packet"].clone())
    } else if request
        .as_object()
        .is_some_and(|v| v.len() == 1 && v.contains_key("instruction_source_admission"))
    {
        agentic_workspace_core::instruction_source::view(
            request["instruction_source_admission"].clone(),
        )
    } else if request
        .as_object()
        .is_some_and(|v| v.len() == 1 && v.contains_key("semantic_route_view"))
    {
        agentic_workspace_core::semantic_routes::view(request["semantic_route_view"].clone())
    } else if request
        .as_object()
        .is_some_and(|item| item.len() == 1 && item.contains_key("repository_decision_view"))
    {
        agentic_workspace_core::decision_source::view(request["repository_decision_view"].clone())
    } else if request
        .as_object()
        .is_some_and(|item| item.len() == 1 && item.contains_key("admission"))
    {
        agentic_workspace_core::admit_invocation_value(request["admission"].clone())
    } else if request
        .as_object()
        .is_some_and(|item| item.len() == 1 && item.contains_key("prepare_request"))
    {
        agentic_workspace_core::prepare_request_value(request["prepare_request"].clone())
    } else if request
        .as_object()
        .is_some_and(|item| item.len() == 1 && item.contains_key("answer_decision"))
    {
        agentic_workspace_core::answer_decision_value(request["answer_decision"].clone())
    } else if request
        .as_object()
        .is_some_and(|item| item.len() == 1 && item.contains_key("operation_result"))
    {
        agentic_workspace_core::operation_result_value(request["operation_result"].clone())
    } else if request
        .as_object()
        .is_some_and(|item| item.len() == 1 && item.contains_key("admit_attempt"))
    {
        agentic_workspace_core::attempt::admit(request["admit_attempt"].clone())
    } else if request
        .as_object()
        .is_some_and(|item| item.len() == 1 && item.contains_key("commit_attempt"))
    {
        agentic_workspace_core::attempt::commit(request["commit_attempt"].clone())
    } else if request
        .as_object()
        .is_some_and(|item| item.len() == 1 && item.contains_key("admit_stored_attempt"))
    {
        agentic_workspace_core::attempt_store::admit(request["admit_stored_attempt"].clone())
    } else if request
        .as_object()
        .is_some_and(|item| item.len() == 1 && item.contains_key("commit_stored_attempt"))
    {
        agentic_workspace_core::attempt_store::commit(request["commit_stored_attempt"].clone())
    } else if request
        .as_object()
        .is_some_and(|item| item.len() == 1 && item.contains_key("planning_view"))
    {
        agentic_workspace_core::planning::view(request["planning_view"].clone())
    } else if request
        .as_object()
        .is_some_and(|item| item.len() == 1 && item.contains_key("reconcile_planning"))
    {
        agentic_workspace_core::planning::reconcile(request["reconcile_planning"].clone())
    } else if request
        .as_object()
        .is_some_and(|item| item.len() == 1 && item.contains_key("normalize_decision_record"))
    {
        agentic_workspace_core::continuity::normalize(request["normalize_decision_record"].clone())
    } else {
        agentic_workspace_core::compile_value(request.clone())
    };
    agentic_workspace_core::maintainer_logging::capture(&request, &result, started.elapsed());
    match result {
        Ok(decision) => println!(
            "{}",
            serde_json::to_string(&decision).expect("decision is JSON serializable")
        ),
        Err(error) => fail("invalid-source-decision", &error.to_string()),
    }
}

fn fail(code: &str, message: &str) -> ! {
    let payload = serde_json::json!({"error": {"code": code, "message": message}});
    eprintln!(
        "{}",
        serde_json::to_string(&payload).expect("error is JSON serializable")
    );
    std::process::exit(2);
}
