use serde_json::{Value, json};
mod setup;
#[cfg(not(unix))]
use std::io::Write;
use std::{
    collections::BTreeSet,
    env, fs,
    io::{self, Read},
    process::{Command, Stdio},
};

fn declaration() -> Value {
    serde_json::from_str::<Value>(include_str!(
        "../../../core/contracts/source_decision_contract.json"
    ))
    .expect("checked public declaration")["native_cli"]
        .clone()
}

fn help(contract: &Value) -> String {
    let mut lines = vec![format!(
        "Usage: {} <command> [options]",
        contract["executable"].as_str().unwrap()
    )];
    for command in contract["commands"].as_array().unwrap() {
        lines.push(format!(
            "  {}  {}",
            command["name"].as_str().unwrap(),
            command["description"].as_str().unwrap()
        ));
    }
    for option in contract["options"].as_array().unwrap() {
        lines.push(format!(
            "  {}  {}",
            option["flag"].as_str().unwrap(),
            option["description"].as_str().unwrap()
        ));
    }
    lines.push(format!(
        "  {}  Show this help",
        contract["help_flag"].as_str().unwrap()
    ));
    lines.join("\n")
}

struct Parsed {
    command: String,
    values: Value,
    input_path: Option<String>,
    explicit: BTreeSet<String>,
    format: String,
}

fn parse(contract: &Value, args: &[String]) -> Result<Option<Parsed>, String> {
    let help_flag = contract["help_flag"].as_str().unwrap();
    if args.is_empty() || args == [help_flag] {
        return Ok(None);
    }
    let command = contract["commands"]
        .as_array()
        .unwrap()
        .iter()
        .find(|command| command["name"].as_str() == Some(args[0].as_str()))
        .ok_or_else(|| format!("unknown command: {}", args[0]))?;
    let options = contract["options"].as_array().unwrap();
    let mut values = serde_json::Map::new();
    for option in options {
        if let Some(default) = option.get("default") {
            values.insert(
                option["field"].as_str().unwrap().to_owned(),
                default.clone(),
            );
        }
    }
    let mut seen = BTreeSet::new();
    let mut index = 1;
    while index < args.len() {
        if args[index] == help_flag {
            return Ok(None);
        }
        let (flag, attached) = args[index]
            .split_once('=')
            .map_or((args[index].as_str(), None), |(flag, value)| {
                (flag, Some(value))
            });
        let option = options
            .iter()
            .find(|option| option["flag"].as_str() == Some(flag))
            .ok_or_else(|| format!("unknown option or positional argument: {}", args[index]))?;
        let field = option["field"].as_str().unwrap();
        let multiple = option["multiple"].as_bool().unwrap_or(false);
        if !seen.insert(field.to_owned()) && !multiple {
            return Err(format!("{flag} may be supplied only once"));
        }
        index += 1;
        if option["boolean"] == true {
            if attached.is_some() {
                return Err(format!("{flag} does not take a value"));
            }
            values.insert(field.to_owned(), json!(true));
            continue;
        }
        let mut supplied = Vec::new();
        if let Some(value) = attached {
            supplied.push(value.to_owned());
        } else {
            while index < args.len() && (!args[index].starts_with('-') || args[index] == "-") {
                supplied.push(args[index].clone());
                index += 1;
                if !multiple {
                    break;
                }
            }
        }
        if supplied.is_empty() {
            return Err(format!("{flag} requires a value"));
        }
        if let Some(choices) = option["choices"].as_array()
            && supplied
                .iter()
                .any(|value| !choices.contains(&json!(value)))
        {
            return Err(format!("{flag} must be one of {choices:?}"));
        }
        if multiple {
            values
                .entry(field.to_owned())
                .or_insert_with(|| json!([]))
                .as_array_mut()
                .unwrap()
                .extend(supplied.into_iter().map(Value::String));
        } else {
            values.insert(field.to_owned(), json!(supplied[0]));
        }
    }
    let input_path = values
        .remove("input")
        .and_then(|value| value.as_str().map(str::to_owned));
    if command["input_required"] == true && input_path.is_none() {
        return Err("--input is required for this command".to_owned());
    }
    let format = values
        .remove("format")
        .and_then(|v| v.as_str().map(str::to_owned))
        .unwrap_or_else(|| "json".into());
    if args[0] != "setup"
        && (format != "json"
            || ["yes", "dry_run", "recover"]
                .iter()
                .any(|key| seen.contains(*key)))
    {
        return Err("text output, --yes, --dry-run and --recover are setup-only".into());
    }
    if values.contains_key("reference") {
        // Absent context must stay absent when carrying exact work. Explicit
        // context remains in the request for Rust's equality check.
        for field in ["target", "task", "changed"] {
            if !seen.contains(field) && !(field == "changed" && values[field] != json!([])) {
                values.remove(field);
            }
        }
    }
    if let Some(answer) = values.get_mut("answer") {
        *answer = serde_json::from_str(answer.as_str().unwrap())
            .map_err(|_| "--answer must be JSON".to_owned())?;
    }
    Ok(Some(Parsed {
        command: args[0].clone(),
        values: Value::Object(values),
        input_path,
        explicit: seen,
        format,
    }))
}

fn carry_input(contract: &Value, parsed: &mut Parsed, input: Value) -> Result<(), String> {
    let command = contract["commands"]
        .as_array()
        .unwrap()
        .iter()
        .find(|command| command["name"] == parsed.command)
        .unwrap();
    let field = command["input_field"].as_str().unwrap();
    if command["accepts_input_envelope"] == true
        && (input.get(field).is_some()
            || (parsed.command == "start"
                && (input.get("material").is_some()
                    || input.get("maintenance").is_some()
                    || input.get("available_sources").is_some()
                    || input.get("delivered").is_some())))
    {
        // Preserve the exact owner envelope. Explicit argv is an assertion,
        // never an override; absent defaults must not replace bound context.
        for (key, value) in parsed.values.as_object().unwrap() {
            if !parsed.explicit.contains(key) {
                continue;
            }
            let same = if key == "target" {
                match (value.as_str(), input[key].as_str()) {
                    (Some(left), Some(right)) => {
                        match (fs::canonicalize(left), fs::canonicalize(right)) {
                            (Ok(left), Ok(right)) => left == right,
                            _ => false,
                        }
                    }
                    _ => false,
                }
            } else {
                value == &input[key]
            };
            if !same {
                return Err(format!(
                    "explicit {key} conflicts with the exact input envelope"
                ));
            }
        }
        parsed.values = input;
    } else {
        parsed.values[field] = input;
    }
    Ok(())
}

fn run() -> Result<(), (&'static str, String)> {
    let contract = declaration();
    let args = env::args_os()
        .skip(1)
        .map(|argument| {
            argument
                .into_string()
                .map_err(|_| ("invalid-cli-input", "arguments must be UTF-8".to_owned()))
        })
        .collect::<Result<Vec<_>, _>>()?;
    let Some(mut parsed) = parse(&contract, &args).map_err(|error| ("invalid-cli-input", error))?
    else {
        println!("{}", help(&contract));
        return Ok(());
    };
    if parsed.command == "setup" {
        return setup::run(parsed).map_err(|error| ("setup", error));
    }
    let input = if let Some(path) = &parsed.input_path {
        let text = if path == "-" {
            let mut text = String::new();
            io::stdin()
                .read_to_string(&mut text)
                .map_err(|error| ("input-read", error.to_string()))?;
            text
        } else {
            fs::read_to_string(path).map_err(|error| ("input-read", error.to_string()))?
        };
        serde_json::from_str(&text).map_err(|error| ("invalid-json", error.to_string()))?
    } else {
        Value::Null
    };
    carry_input(&contract, &mut parsed, input).map_err(|error| ("invalid-cli-input", error))?;
    // The CLI owns only argv/JSON transport. Every semantic operation runs in
    // the same colocated executable used by the JSON/Python/Node adapters.
    let executable = env::current_exe().map_err(|error| ("core-location", error.to_string()))?;
    let core = executable.with_file_name(if cfg!(windows) {
        "agentic-workspace-core.exe"
    } else {
        "agentic-workspace-core"
    });
    forward(&core, &json!({parsed.command: parsed.values}))
}

#[cfg(unix)]
fn forward(core: &std::path::Path, payload: &Value) -> Result<(), (&'static str, String)> {
    use std::io::{Seek, SeekFrom};
    use std::os::unix::process::CommandExt;
    // Anonymous regular input avoids pipe-capacity deadlock and argv exposure.
    // exec keeps the same process identity and signal lifetime as the core.
    let mut input = tempfile::tempfile().map_err(|error| ("core-input", error.to_string()))?;
    serde_json::to_writer(&mut input, payload)
        .map_err(|error| ("core-input", error.to_string()))?;
    input
        .seek(SeekFrom::Start(0))
        .map_err(|error| ("core-input", error.to_string()))?;
    let error = Command::new(core).stdin(Stdio::from(input)).exec();
    Err((
        "core-unavailable",
        format!("colocated core {}: {error}", core.display()),
    ))
}

#[cfg(not(unix))]
fn forward(core: &std::path::Path, payload: &Value) -> Result<(), (&'static str, String)> {
    let mut command = Command::new(core);
    command
        .stdin(Stdio::piped())
        .stdout(Stdio::inherit())
        .stderr(Stdio::inherit());
    #[cfg(windows)]
    {
        use std::os::windows::process::CommandExt;
        command.creation_flags(0x08000000);
    }
    #[cfg(windows)]
    let mut command = {
        use process_wrap::std::{CommandWrap, JobObject};
        let mut wrapped = CommandWrap::from(command);
        wrapped.wrap(JobObject);
        wrapped
    };
    let mut child = command.spawn().map_err(|error| {
        (
            "core-unavailable",
            format!("colocated core {}: {error}", core.display()),
        )
    })?;
    #[cfg(windows)]
    let stdin = child.stdin().take();
    #[cfg(not(windows))]
    let stdin = child.stdin.take();
    let write = stdin.expect("piped core input").write_all(
        serde_json::to_string(payload)
            .expect("parsed request is JSON")
            .as_bytes(),
    );
    if let Err(error) = write {
        let _ = child.kill();
        let _ = child.wait();
        return Err(("core-input", error.to_string()));
    }
    let status = child.wait().map_err(|error| {
        let _ = child.kill();
        let _ = child.wait();
        ("core-wait", error.to_string())
    })?;
    if !status.success() {
        std::process::exit(status.code().unwrap_or(2));
    }
    Ok(())
}

fn main() {
    if let Err((code, message)) = run() {
        eprintln!("{}", json!({"error": {"code": code, "message": message}}));
        std::process::exit(2);
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    fn args(items: &[&str]) -> Vec<String> {
        items.iter().map(|item| (*item).to_owned()).collect()
    }

    #[test]
    fn public_defaults_and_repeated_changed_paths() {
        let parsed = parse(
            &declaration(),
            &args(&[
                "start",
                "--changed",
                "a",
                "b",
                "--changed=c",
                "--task",
                "bounded task",
            ]),
        )
        .unwrap()
        .unwrap();
        assert_eq!(
            parsed.values,
            json!({"target":".", "task":"bounded task", "changed":["a","b","c"]})
        );
        assert!(parsed.input_path.is_none());
    }

    #[test]
    fn rejects_hidden_authority_and_invalid_transport_inputs() {
        for arguments in [
            args(&["invoke"]),
            args(&["start", "--relevant", "true"]),
            args(&["start", "--target", ".", "--target", "other"]),
            args(&["start", "--format", "yaml"]),
            args(&["start", "--changed"]),
            args(&["planning_view"]),
        ] {
            assert!(parse(&declaration(), &arguments).is_err(), "{arguments:?}");
        }
        let parsed = parse(&declaration(), &args(&["invoke", "--input", "-"]))
            .unwrap()
            .unwrap();
        assert_eq!(parsed.input_path.as_deref(), Some("-"));
    }

    #[test]
    fn help_is_derived_from_canonical_commands_and_flags() {
        let contract = declaration();
        let rendered = help(&contract);
        for declaration in contract["commands"].as_array().unwrap() {
            assert!(rendered.contains(declaration["name"].as_str().unwrap()));
        }
        for declaration in contract["options"].as_array().unwrap() {
            assert!(rendered.contains(declaration["flag"].as_str().unwrap()));
        }
    }
}
