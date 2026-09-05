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
    let result = if request
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
        agentic_workspace_core::compile_value(request)
    };
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
