//! Human interaction composed over Configuration's exact adoption protocol.
//! This module never reads or writes repository files itself.
use serde_json::{Value, json};
use std::{
    env,
    io::{self, IsTerminal, Write},
    process::{Command, Stdio},
};

fn call(context: &Value, request: Option<Value>, invocation: bool) -> Result<Value, String> {
    let mut input = context.clone();
    if let Some(request) = request {
        input[if invocation { "invocation" } else { "request" }] = request;
    }
    let core = env::current_exe()
        .map_err(|e| e.to_string())?
        .with_file_name(if cfg!(windows) {
            "agentic-workspace-core.exe"
        } else {
            "agentic-workspace-core"
        });
    let mut command = Command::new(core);
    command
        .stdin(Stdio::piped())
        .stdout(Stdio::piped())
        .stderr(Stdio::piped());
    #[cfg(windows)]
    {
        use std::os::windows::process::CommandExt;
        command.creation_flags(0x08000000);
    }
    let mut child = command.spawn().map_err(|e| e.to_string())?;
    let payload = json!({if invocation { "invoke" } else { "start" }:input});
    child
        .stdin
        .take()
        .unwrap()
        .write_all(payload.to_string().as_bytes())
        .map_err(|e| e.to_string())?;
    let result = child.wait_with_output().map_err(|e| e.to_string())?;
    if !result.status.success() {
        return Err(String::from_utf8_lossy(&result.stderr).into_owned());
    }
    serde_json::from_slice(&result.stdout).map_err(|e| e.to_string())
}

fn report(state: &Value, status: &str) -> Value {
    let mut created = Vec::new();
    let mut updated = Vec::new();
    let mut removed = Vec::new();
    if let Some(updates) = state["updates"].as_object() {
        for (path, change) in updates {
            if change["after"].is_null() {
                removed.push(path);
            } else if change["before"].is_null() {
                created.push(path);
            } else {
                updated.push(path);
            }
        }
    }
    json!({"status":status,"created":created,"updated":updated,"removed":removed,"preserved":state["preserved"],"conflicts":state["blockers"],"next":"Give your agent an ordinary task in this repository; AGENTS.md points to the installed startup skill."})
}

fn render(value: &Value, json_output: bool) {
    if json_output {
        println!("{}", serde_json::to_string_pretty(value).unwrap());
        return;
    }
    println!(
        "Repository setup: {}",
        value["status"].as_str().unwrap_or("unknown")
    );
    println!(
        "AW files live in .agentic-workspace/; AGENTS.md contains a pointer to the startup skill."
    );
    for key in ["created", "updated", "removed", "preserved"] {
        println!("  {key}: {}", value[key].as_array().map_or(0, Vec::len));
    }
    if let Some(paths) = value["removed"].as_array() {
        for path in paths {
            println!("  Remove: {}", path.as_str().unwrap_or("unknown"));
        }
    }
    if value["status"] == "authorization-required" {
        println!("Surrounding AGENTS.md prose and independently owned state are preserved.");
        println!(
            "For the exact file list: setup --dry-run --format json (with the same --target)."
        );
    }
    if let Some(conflicts) = value["conflicts"].as_array() {
        for conflict in conflicts {
            println!(
                "  Conflict: {}",
                conflict.as_str().unwrap_or("unrecognised owner conflict")
            );
        }
    }
    if value["status"] == "applied" || value["status"] == "already-current" {
        println!("{}", value["next"].as_str().unwrap());
    }
}

fn policy_blockers(current: &Value, disabled_maintenance: bool) -> Vec<Value> {
    current["decision_packet"]["blockers"]
        .as_array()
        .into_iter()
        .flatten()
        .filter(|b| {
            (!disabled_maintenance || b["code"] != "workspace-disabled")
                && b["affects"].as_array().is_some_and(|scopes| {
                    scopes
                        .iter()
                        .any(|s| s == "task" || s == "effect:configuration-source")
                })
        })
        .cloned()
        .collect()
}

pub(super) fn run(parsed: super::Parsed) -> Result<(), String> {
    for key in &parsed.explicit {
        if !["target", "format", "yes", "dry_run", "recover"].contains(&key.as_str()) {
            return Err(format!("setup does not accept {key}"));
        }
    }
    let json_output = parsed.explicit.contains("format") && parsed.format == "json";
    let yes = parsed.values["yes"] == true;
    let dry = parsed.values["dry_run"] == true;
    if yes && dry {
        return Err("--yes and --dry-run cannot be combined".into());
    }
    let context = json!({"target":parsed.values["target"],"task":"Set up Agentic Workspace in this repository","maintenance":"configuration","projection":"full"});
    let initial = call(&context, None, false)?;
    let request = &initial["configuration_write"]["repository_adoption_request"];
    if request.is_null() {
        return Err(
            "Repository adoption is unavailable; inspect the current Configuration owner.".into(),
        );
    }
    let discovered = call(&context, Some(request.clone()), false)?;
    let owner = &discovered["configuration_write"];
    let pending = !owner["repository_adoption"]["pending"].is_null();
    if pending && parsed.values["recover"] != true {
        render(
            &report(&owner["repository_adoption"], "recovery-required"),
            json_output,
        );
        return Err("An interrupted setup is preserved. Run setup --recover to inspect and authorise its exact recovery.".into());
    }
    if !pending && parsed.values["recover"] == true {
        return Err("No interrupted setup to recover.".into());
    }
    let request = if pending {
        owner["recovery_requests"]
            .as_array()
            .and_then(|a| a.first())
    } else {
        owner["adoption_requests"]
            .as_array()
            .and_then(|a| a.iter().find(|r| r["arguments"]["mode"] == "adopt"))
    };
    let request = request.ok_or_else(|| {
        format!(
            "Setup unavailable: {}. Run from the Git working-tree root; preserve existing content.",
            owner["status"]
        )
    })?;
    let proposed = call(&context, Some(request.clone()), false)?;
    let owner = &proposed["configuration_write"];
    let status = owner["status"].as_str().unwrap_or("unavailable");
    let decision = proposed["decision_packet"]["pending_consequences"]["decisions"]
        .as_array()
        .and_then(|a| {
            a.iter()
                .find(|d| d["id"] == "repository-adoption-authorization")
        });
    let state = decision.map_or(&owner["repository_adoption"], |d| &d["material"]);
    let mut summary = report(state, status);
    if status == "already-current" {
        render(&summary, json_output);
        return Ok(());
    }
    let mode = if state["mode"] == "recover" {
        &state["pending"]["invocation"]["arguments"]["request"]["arguments"]["mode"]
    } else {
        &state["mode"]
    };
    let blockers = policy_blockers(
        &proposed,
        matches!(mode.as_str(), Some("adopt" | "reconcile-payload")),
    );
    if !blockers.is_empty() {
        summary["status"] = json!("policy-blocked");
        summary["policy_blockers"] = json!(blockers);
        summary["recovery"] = proposed["consequence_recovery"].clone();
        render(&summary, json_output);
        return Err(format!(
            "Setup is blocked by current owner restrictions: {}",
            summary["policy_blockers"]
        ));
    }
    if decision.is_none() {
        render(&summary, json_output);
        return Err("Setup is blocked; resolve the reported conflict without overwriting preserved content.".into());
    }
    if dry {
        render(&summary, json_output);
        return Ok(());
    }
    if !yes {
        render(&summary, json_output);
        if json_output || !io::stdin().is_terminal() {
            return Err(
                "No changes made. Use --yes to authorise this bounded setup, or run interactively."
                    .into(),
            );
        }
        print!("Apply these repository changes? [y/N] ");
        io::stdout().flush().map_err(|e| e.to_string())?;
        let mut answer = String::new();
        io::stdin()
            .read_line(&mut answer)
            .map_err(|e| e.to_string())?;
        if !["y", "yes"].contains(&answer.trim().to_ascii_lowercase().as_str()) {
            println!("No changes made.");
            return Ok(());
        }
    } else if !json_output {
        render(&summary, false);
    }
    // Approval is carried on this exact proposal. Re-observation must not silently
    // authorise a different footprint after a concurrent edit.
    let mut answer = decision.unwrap()["response_request"].clone();
    answer["arguments"]["answer"] = json!("authorize-write");
    let authorised = call(&context, Some(answer), false)?;
    let action = authorised["decision_packet"]["ready_actions"].as_array()
        .and_then(|a| a.iter().find(|a| a["operation_id"] == "configuration.repository-adoption"))
        .ok_or_else(|| {
            // An admitted maintenance action already narrows disablement to
            // unrelated effects. Any remaining task restriction is real policy.
            let blockers = policy_blockers(&authorised, false);
            if blockers.is_empty() {
                "The exact setup proposal is no longer actionable. Re-run setup to inspect current changes.".to_owned()
            } else {
                format!("Setup is blocked by current owner restrictions: {}", json!(blockers))
            }
        })?;
    let result = call(&context, Some(action.clone()), true)?;
    summary["status"] = result["status"].clone();
    summary["effect_outcome"] = result["effect_outcome"].clone();
    summary["custody"] = result["custody"].clone();
    render(&summary, json_output);
    if result["effect_outcome"]["status"] != "committed" {
        return Err(format!(
            "Setup did not commit: {}. Preserve custody and re-run setup to inspect recovery.",
            result["error"]
        ));
    }
    Ok(())
}
