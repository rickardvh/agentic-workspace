use aw_independent_owner_fixture as fixture;
fn main() {
    // Fixture authoring helper, outside the native public product surface.
    if let Some(owner) = std::env::args().nth(1) {
        println!(
            "{}",
            toml::to_string(&fixture::configuration(&owner)).unwrap()
        );
        return;
    }
    agentic_workspace_core::transport::run_stdio();
}
