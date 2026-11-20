fn main() {
    use agentic_workspace_core::transport;
    match std::env::args_os()
        .nth(1)
        .as_deref()
        .and_then(|arg| arg.to_str())
    {
        Some("--cli-yaml") => transport::run_yaml_stdio(false),
        Some("--render-yaml") => transport::run_yaml_stdio(true),
        _ => transport::run_stdio(),
    }
}
