use serde_json::Value;
use std::{
    fs,
    path::PathBuf,
    process::Command,
    time::{SystemTime, UNIX_EPOCH},
};

struct Target(PathBuf);
impl Target {
    fn empty() -> Self {
        let path = std::env::temp_dir().join(format!(
            "aw-native-cli-{}-{}",
            std::process::id(),
            SystemTime::now()
                .duration_since(UNIX_EPOCH)
                .unwrap()
                .as_nanos()
        ));
        fs::create_dir(&path).unwrap();
        Self(path)
    }
}
impl Drop for Target {
    fn drop(&mut self) {
        fs::remove_dir_all(&self.0).unwrap();
    }
}

#[test]
fn empty_target_is_direct_without_python_or_node() {
    let target = Target::empty();
    let result = Command::new(env!("CARGO_BIN_EXE_agentic-workspace"))
        .args(["start", "--target"])
        .arg(&target.0)
        .args(["--task", "Inspect this empty workspace", "--format", "json"])
        .env_clear()
        .env("PATH", "")
        .output()
        .unwrap();
    assert!(
        result.status.success(),
        "{}",
        String::from_utf8_lossy(&result.stderr)
    );
    let decision: Value = serde_json::from_slice(&result.stdout).unwrap();
    assert_eq!(decision["decision_packet"]["status"], "direct");
    assert_eq!(fs::read_dir(&target.0).unwrap().count(), 0);
}

#[test]
fn actual_registry_selection_is_current_then_stale_without_language_runtimes() {
    let target = Target::empty();
    let registry = target.0.join("tools/skills/REGISTRY.json");
    fs::create_dir_all(registry.parent().unwrap()).unwrap();
    let text = include_str!("../../../tools/skills/REGISTRY.json");
    fs::write(&registry, text).unwrap();
    let start = |input: Option<&PathBuf>| {
        let mut command = Command::new(env!("CARGO_BIN_EXE_agentic-workspace"));
        command
            .args(["start", "--target"])
            .arg(&target.0)
            .args(["--task", "Inspect the repository boundaries"])
            .env_clear()
            .env("PATH", "");
        if let Some(input) = input {
            command.arg("--input").arg(input);
        }
        let result = command.output().unwrap();
        assert!(
            result.status.success(),
            "{}",
            String::from_utf8_lossy(&result.stderr)
        );
        serde_json::from_slice::<Value>(&result.stdout).unwrap()
    };
    let discovered = start(None);
    assert_eq!(discovered["decision_packet"]["status"], "direct");
    let mut request = discovered["semantic_routes"]["requests"][1].clone();
    request["arguments"] =
        serde_json::json!({"posture":"selected","routes":["workspace/ownership/audit"]});
    let input = target.0.join("request.json");
    fs::write(&input, serde_json::to_vec(&request).unwrap()).unwrap();
    let current = start(Some(&input));
    assert_eq!(current["semantic_routes"]["status"], "current");
    assert_eq!(
        current["decision_packet"]["semantic_task_routes"]["status"],
        "current"
    );
    assert_eq!(
        current["decision_packet"]["semantic_task_routes"]["authority_effect"],
        "applicability-only"
    );
    fs::write(&registry, format!("{text}\n")).unwrap();
    let stale = start(Some(&input));
    assert_eq!(stale["semantic_routes"]["status"], "stale");
    assert_eq!(
        stale["decision_packet"]["semantic_task_routes"]["status"],
        "stale"
    );
    assert!(!target.0.join(".agentic-workspace").exists());
}

#[test]
fn transport_rejects_private_flags_without_any_runtime() {
    let result = Command::new(env!("CARGO_BIN_EXE_agentic-workspace"))
        .args(["start", "--admitted-revision", "caller-owned"])
        .env_clear()
        .env("PATH", "")
        .output()
        .unwrap();
    assert_eq!(result.status.code(), Some(2));
    assert!(result.stdout.is_empty());
    let error: Value = serde_json::from_slice(&result.stderr).unwrap();
    assert_eq!(error["error"]["code"], "invalid-cli-input");
}
