use std::io::{self, Read};

pub fn run_stdio() {
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
        .is_some_and(|v| v.len() == 1 && v.contains_key("resources"))
    {
        crate::native_resources::view(request["resources"].clone())
    } else if request
        .as_object()
        .is_some_and(|v| v.len() == 1 && v.contains_key("session_logging_policy"))
    {
        crate::maintainer_logging::policy(request["session_logging_policy"].clone())
    } else if request
        .as_object()
        .is_some_and(|v| v.len() == 1 && v.contains_key("assurance_applicability"))
    {
        crate::assurance_applicability::view(request["assurance_applicability"].clone())
    } else if request
        .as_object()
        .is_some_and(|v| v.len() == 1 && v.contains_key("assignment_packet"))
    {
        crate::assignment_packet::view(request["assignment_packet"].clone())
    } else if request
        .as_object()
        .is_some_and(|v| v.len() == 1 && v.contains_key("native_route_discovery"))
    {
        crate::native_routes::discovery(request["native_route_discovery"].clone())
    } else if request
        .as_object()
        .is_some_and(|v| v.len() == 1 && v.contains_key("review_authentication"))
    {
        crate::review_authentication::view(request["review_authentication"].clone())
    } else if request
        .as_object()
        .is_some_and(|v| v.len() == 1 && v.contains_key("verification_requirements"))
    {
        crate::verification_requirements::view(request["verification_requirements"].clone())
    } else if request
        .as_object()
        .is_some_and(|v| v.len() == 1 && v.contains_key("separation_of_duty"))
    {
        crate::separation_of_duty::view(request["separation_of_duty"].clone())
    } else if request
        .as_object()
        .is_some_and(|v| v.len() == 1 && v.contains_key("runtime_compatibility"))
    {
        crate::runtime_compatibility::view(request["runtime_compatibility"].clone())
    } else if request
        .as_object()
        .is_some_and(|v| v.len() == 1 && v.contains_key("instruction_applicability"))
    {
        crate::instruction_applicability::view(request["instruction_applicability"].clone())
    } else if request
        .as_object()
        .is_some_and(|v| v.len() == 1 && v.contains_key("proof_receipt"))
    {
        crate::proof_receipt::view(request["proof_receipt"].clone())
    } else if request
        .as_object()
        .is_some_and(|v| v.len() == 1 && v.contains_key("task_requirements"))
    {
        crate::task_requirements::view(request["task_requirements"].clone())
    } else if request
        .as_object()
        .is_some_and(|v| v.len() == 1 && v.contains_key("task_judgment"))
    {
        crate::task_judgment::view(request["task_judgment"].clone())
    } else if request
        .as_object()
        .is_some_and(|v| v.len() == 1 && v.contains_key("proof_subject"))
    {
        crate::proof_subject::view(request["proof_subject"].clone())
    } else if request
        .as_object()
        .is_some_and(|v| v.len() == 1 && v.contains_key("direct_task_subject"))
    {
        crate::direct_task::view(request["direct_task_subject"].clone())
    } else if request
        .as_object()
        .is_some_and(|v| v.len() == 1 && v.contains_key("start"))
    {
        crate::operating::start(request["start"].clone())
    } else if request
        .as_object()
        .is_some_and(|v| v.len() == 1 && v.contains_key("invoke"))
    {
        crate::operating::invoke(request["invoke"].clone())
    } else if request
        .as_object()
        .is_some_and(|v| v.len() == 1 && v.contains_key("attribute_assignment_outcome"))
    {
        crate::assignment::attribute_outcome(request["attribute_assignment_outcome"].clone())
    } else if request
        .as_object()
        .is_some_and(|v| v.len() == 1 && v.contains_key("assignment_policy"))
    {
        crate::assignment_policy::resolve(&request["assignment_policy"])
    } else if request
        .as_object()
        .is_some_and(|v| v.len() == 1 && v.contains_key("local_source_overlay"))
    {
        Ok(crate::assignment_policy::merge(
            &request["local_source_overlay"]["base"],
            &request["local_source_overlay"]["override"],
        ))
    } else if request
        .as_object()
        .is_some_and(|v| v.len() == 1 && v.contains_key("transport_sources"))
    {
        crate::transport_source::decode_sources(&request["transport_sources"])
    } else if request
        .as_object()
        .is_some_and(|v| v.len() == 1 && v.contains_key("execution_configurations"))
    {
        crate::assignment::configurations(request["execution_configurations"].clone())
    } else if request
        .as_object()
        .is_some_and(|v| v.len() == 1 && v.contains_key("replace_assignment"))
    {
        crate::assignment::replace(request["replace_assignment"].clone())
    } else if request
        .as_object()
        .is_some_and(|v| v.len() == 1 && v.contains_key("admit_assignment_packet"))
    {
        crate::assignment::admit(request["admit_assignment_packet"].clone())
    } else if request
        .as_object()
        .is_some_and(|v| v.len() == 1 && v.contains_key("instruction_source_admission"))
    {
        crate::instruction_source::view(request["instruction_source_admission"].clone())
    } else if request
        .as_object()
        .is_some_and(|v| v.len() == 1 && v.contains_key("semantic_route_view"))
    {
        crate::semantic_routes::view(request["semantic_route_view"].clone())
    } else if request
        .as_object()
        .is_some_and(|item| item.len() == 1 && item.contains_key("repository_decision_view"))
    {
        crate::decision_source::view(request["repository_decision_view"].clone())
    } else if request
        .as_object()
        .is_some_and(|item| item.len() == 1 && item.contains_key("admission"))
    {
        crate::admit_invocation_value(request["admission"].clone())
    } else if request
        .as_object()
        .is_some_and(|item| item.len() == 1 && item.contains_key("prepare_request"))
    {
        crate::prepare_request_value(request["prepare_request"].clone())
    } else if request
        .as_object()
        .is_some_and(|item| item.len() == 1 && item.contains_key("answer_decision"))
    {
        crate::answer_decision_value(request["answer_decision"].clone())
    } else if request
        .as_object()
        .is_some_and(|item| item.len() == 1 && item.contains_key("operation_result"))
    {
        crate::operation_result_value(request["operation_result"].clone())
    } else if request
        .as_object()
        .is_some_and(|item| item.len() == 1 && item.contains_key("admit_attempt"))
    {
        crate::attempt::admit(request["admit_attempt"].clone())
    } else if request
        .as_object()
        .is_some_and(|item| item.len() == 1 && item.contains_key("commit_attempt"))
    {
        crate::attempt::commit(request["commit_attempt"].clone())
    } else if request
        .as_object()
        .is_some_and(|item| item.len() == 1 && item.contains_key("admit_stored_attempt"))
    {
        crate::attempt_store::admit(request["admit_stored_attempt"].clone())
    } else if request
        .as_object()
        .is_some_and(|item| item.len() == 1 && item.contains_key("commit_stored_attempt"))
    {
        crate::attempt_store::commit(request["commit_stored_attempt"].clone())
    } else if request
        .as_object()
        .is_some_and(|item| item.len() == 1 && item.contains_key("planning_view"))
    {
        crate::planning::view(request["planning_view"].clone())
    } else if request
        .as_object()
        .is_some_and(|item| item.len() == 1 && item.contains_key("reconcile_planning"))
    {
        crate::planning::reconcile(request["reconcile_planning"].clone())
    } else if request
        .as_object()
        .is_some_and(|item| item.len() == 1 && item.contains_key("normalize_decision_record"))
    {
        crate::continuity::normalize(request["normalize_decision_record"].clone())
    } else {
        crate::compile_value(request.clone())
    };
    crate::maintainer_logging::capture(&request, &result, started.elapsed());
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
