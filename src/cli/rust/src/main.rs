use serde_json::{Value, json};
mod setup;
#[cfg(not(unix))]
use std::io::Write;
use std::{
    collections::BTreeSet,
    env, fs,
    io::{self, IsTerminal, Read, Seek},
    path::{Path, PathBuf},
    process::{Command, Stdio},
};

#[derive(Clone, Copy, PartialEq, Eq)]
enum OutputFormat {
    Json,
    Text,
    Yaml,
}

impl OutputFormat {
    fn core_args(self) -> &'static [&'static str] {
        if self == Self::Yaml {
            &["--cli-yaml"]
        } else {
            &[]
        }
    }

    fn named(value: &str) -> Option<Self> {
        match value {
            "json" => Some(Self::Json),
            "text" => Some(Self::Text),
            "yaml" => Some(Self::Yaml),
            _ => None,
        }
    }

    fn select(args: &[String], preference: Option<&str>, terminal: bool) -> Result<Self, String> {
        // Select the error renderer before validating argv. The command parser
        // still owns option validation, including missing and duplicate flags.
        for (index, arg) in args.iter().enumerate().skip(1) {
            let value = if arg == "--format" {
                args.get(index + 1).map(String::as_str)
            } else if let Some(value) = arg.strip_prefix("--format=") {
                Some(value)
            } else {
                continue;
            };
            return Ok(value.and_then(Self::named).unwrap_or(Self::Json));
        }
        if let Some(value) = preference.filter(|value| !value.is_empty()) {
            return match Self::named(value) {
                Some(format @ (Self::Json | Self::Yaml)) => Ok(format),
                _ => Err("AGENTIC_WORKSPACE_OUTPUT_FORMAT must be json or yaml".into()),
            };
        }
        Ok(if args.first().is_some_and(|name| name == "setup") {
            Self::Text
        } else if terminal {
            Self::Yaml
        } else {
            Self::Json
        })
    }
}

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
    material: Option<Value>,
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
        if field == "delivered"
            && supplied
                .iter()
                .any(|value| value.trim_start().starts_with('['))
        {
            return Err(
                "--delivered takes individual receipt values. Use --delivered RECEIPT1 --delivered RECEIPT2 with the returned values, or put the array in the delivered field of a JSON --input envelope."
                    .into(),
            );
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
    let format = values.remove("format");
    if args[0] != "setup"
        && (format == Some(json!("text"))
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
    if args[0] == "start"
        && matches!(
            values.get("reference").and_then(Value::as_str),
            Some("semantic-routes/select/v1" | "semantic-routes/discover/v1")
        )
    {
        return Err(
            "--reference received a semantic route request kind. Use the returned detail_refs[\"/semantic_routes\"] as --reference and find the matching object in value.requests. Edit only arguments, then send the complete request as JSON to start --input - with the original --target, --task and any --changed values. Omit --reference and --answer on that submission."
                .into(),
        );
    }
    let observation = values.remove("observation");
    let need = values.remove("need");
    let source = values.remove("source");
    let revision = values.remove("source_revision");
    let coverage = values.remove("coverage");
    let material = if observation.is_some() || need.is_some() {
        if args[0] != "start" || (observation.is_some() && need.is_some()) {
            return Err("start accepts one of --observation or --need".into());
        }
        let (kind, summary) = if let Some(summary) = observation {
            ("observation", summary)
        } else {
            ("need", need.unwrap())
        };
        let mut origin = json!({"producer":"cli-caller",
            "reference":source.unwrap_or_else(|| json!("unknown")),
            "coverage":coverage.unwrap_or_else(|| json!("unknown"))});
        if let Some(revision) = revision {
            origin["revision"] = revision;
        }
        Some(json!({"id":"cli-material","kind":kind,"summary":summary,"source":origin}))
    } else {
        if source.is_some() || revision.is_some() || coverage.is_some() {
            return Err(
                "--source, --source-revision and --coverage require --observation or --need".into(),
            );
        }
        None
    };
    Ok(Some(Parsed {
        command: args[0].clone(),
        values: Value::Object(values),
        input_path,
        explicit: seen,
        material,
    }))
}

fn carry_input(contract: &Value, parsed: &mut Parsed, mut input: Value) -> Result<(), String> {
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
                && ((input.get("kind").is_none() && input.get("target").is_some())
                    || input.get("material").is_some()
                    || input.get("maintenance").is_some()
                    || input.get("available_sources").is_some()
                    || input.get("delivered").is_some())))
    {
        if parsed.command == "invoke" && input["reference"].as_str().is_none() {
            require_invoke_context(|field| input.get(field).is_some())?;
        }
        // A new selector and semantic answer can accompany unchanged reentry.
        // Existing fields remain exact assertions, never argv overrides.
        for (key, value) in parsed.values.as_object().unwrap() {
            if !parsed.explicit.contains(key) {
                continue;
            }
            if parsed.command == "start"
                && matches!(key.as_str(), "reference" | "answer")
                && input.get(key).is_none()
            {
                input[key] = value.clone();
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
        if parsed.command == "invoke" && parsed.values.get("reference").is_none() {
            require_invoke_context(|field| parsed.explicit.contains(field))?;
        }
        parsed.values[field] = input;
    }
    if let Some(mut material) = parsed.material.take() {
        if parsed.values["task"]
            .as_str()
            .is_none_or(|s| s.trim().is_empty())
        {
            return Err(
                "material needs the current task through --task or returned reentry in --input"
                    .into(),
            );
        }
        let items = parsed
            .values
            .as_object_mut()
            .unwrap()
            .entry("material")
            .or_insert_with(|| json!([]))
            .as_array_mut()
            .ok_or("material in the input envelope must be an array")?;
        // Identity is disposable transport, never a semantic or authority claim.
        // Preserve all previously carried material, including dependency bindings.
        let mut suffix = 1;
        while items.iter().any(|item| item["id"] == material["id"]) {
            suffix += 1;
            material["id"] = json!(format!("cli-material-{suffix}"));
        }
        items.push(material);
    }
    Ok(())
}

fn require_invoke_context(present: impl Fn(&str) -> bool) -> Result<(), String> {
    let missing: Vec<_> = ["target", "task", "changed"]
        .into_iter()
        .filter(|field| !present(field))
        .collect();
    if missing.is_empty() {
        return Ok(());
    }
    Err(format!(
        "invoke requires exact work context; missing {}. Use a complete invocation envelope, --input <carriage> --reference <action-reference>, or the bare action with original --target, --task and --changed flags; use an envelope or carriage for an empty changed scope",
        missing.join(", ")
    ))
}

fn run(args: &[String], format: OutputFormat) -> Result<(), (&'static str, String)> {
    let contract = declaration();
    let Some(mut parsed) = parse(&contract, args).map_err(|error| ("invalid-cli-input", error))?
    else {
        println!("{}", help(&contract));
        return Ok(());
    };
    if parsed.command == "setup" {
        return setup::run(parsed, format).map_err(|error| ("setup", error));
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
    // The colocated core owns the operation and formats its own response in the
    // same process, so selecting YAML has no effect on signal handling.
    let core = paired_core().map_err(|error| ("core-location", error.to_string()))?;
    forward(&core, &json!({parsed.command: parsed.values}), format)
}

fn paired_core() -> io::Result<PathBuf> {
    Ok(env::current_exe()?.with_file_name(if cfg!(windows) {
        "agentic-workspace-core.exe"
    } else {
        "agentic-workspace-core"
    }))
}

fn core_input(payload: &Value) -> Result<fs::File, (&'static str, String)> {
    // Anonymous regular input avoids pipe-capacity deadlock and argv exposure.
    let mut input = tempfile::tempfile().map_err(|error| ("core-input", error.to_string()))?;
    serde_json::to_writer(&mut input, payload)
        .map_err(|error| ("core-input", error.to_string()))?;
    input
        .rewind()
        .map_err(|error| ("core-input", error.to_string()))?;
    Ok(input)
}

#[cfg(unix)]
fn forward(
    core: &Path,
    payload: &Value,
    format: OutputFormat,
) -> Result<(), (&'static str, String)> {
    use std::os::unix::process::CommandExt;
    let input = core_input(payload)?;
    // exec keeps the same process identity and signal lifetime as the core.
    let error = Command::new(core)
        .args(format.core_args())
        .stdin(Stdio::from(input))
        .exec();
    Err((
        "core-unavailable",
        format!("colocated core {}: {error}", core.display()),
    ))
}

#[cfg(windows)]
fn wrap_core(mut command: Command) -> process_wrap::std::CommandWrap {
    use process_wrap::std::{CommandWrap, JobObject};
    use std::os::windows::process::CommandExt;
    command.creation_flags(0x08000000);
    let mut wrapped = CommandWrap::from(command);
    wrapped.wrap(JobObject);
    wrapped
}

#[cfg(not(unix))]
fn forward(
    core: &Path,
    payload: &Value,
    format: OutputFormat,
) -> Result<(), (&'static str, String)> {
    let mut command = Command::new(core);
    command
        .args(format.core_args())
        .stdin(Stdio::piped())
        .stdout(Stdio::inherit())
        .stderr(Stdio::inherit());
    #[cfg(windows)]
    let mut command = wrap_core(command);
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

fn render_yaml(value: &Value) -> String {
    // Setup reports and CLI input errors already exist as values in this
    // process. The render-only mode never dispatches an AW operation.
    let render = || -> Option<String> {
        let mut command = Command::new(paired_core().ok()?);
        command
            .arg("--render-yaml")
            .stdin(core_input(value).ok()?)
            .stderr(Stdio::null());
        #[cfg(windows)]
        {
            use std::os::windows::process::CommandExt;
            command.creation_flags(0x08000000);
        }
        let result = command.output().ok()?;
        result
            .status
            .success()
            .then(|| String::from_utf8(result.stdout).ok())
            .flatten()
    };
    // A missing pair must still leave a parseable receipt or diagnostic.
    // Compact JSON is valid YAML flow syntax.
    render().unwrap_or_else(|| format!("{value}\n"))
}

fn report_error(format: OutputFormat, code: &str, message: &str) -> ! {
    let value = json!({"error": {"code": code, "message": message}});
    if format == OutputFormat::Yaml {
        eprint!("{}", render_yaml(&value));
    } else {
        eprintln!("{value}");
    }
    std::process::exit(2);
}

fn main() {
    let args = env::args_os()
        .skip(1)
        .map(|arg| arg.into_string())
        .collect::<Result<Vec<_>, _>>()
        .unwrap_or_else(|_| {
            report_error(
                OutputFormat::Json,
                "invalid-cli-input",
                "arguments must be UTF-8",
            )
        });
    let preference = env::var("AGENTIC_WORKSPACE_OUTPUT_FORMAT").ok();
    let format = if args.is_empty() || args.iter().any(|argument| argument == "--help") {
        OutputFormat::Json
    } else {
        OutputFormat::select(
            &args,
            preference.as_deref(),
            io::stdout().is_terminal() && io::stderr().is_terminal(),
        )
        .unwrap_or_else(|message| report_error(OutputFormat::Json, "invalid-cli-input", &message))
    };
    if let Err((code, message)) = run(&args, format) {
        report_error(format, code, &message);
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    fn args(items: &[&str]) -> Vec<String> {
        items.iter().map(|item| (*item).to_owned()).collect()
    }

    #[test]
    fn output_format_precedence_preserves_pipes_and_setup() {
        let select = |argv, preference, terminal| {
            OutputFormat::select(&args(argv), preference, terminal).unwrap()
        };
        assert!(select(&["start"], None, true) == OutputFormat::Yaml);
        assert!(select(&["start"], None, false) == OutputFormat::Json);
        assert!(select(&["setup"], None, true) == OutputFormat::Text);
        assert!(select(&["start"], Some("json"), true) == OutputFormat::Json);
        assert!(select(&["start"], Some("yaml"), false) == OutputFormat::Yaml);
        assert!(select(&["start", "--format", "json"], Some("yaml"), true) == OutputFormat::Json);
        assert!(select(&["start", "--format=yaml"], Some("invalid"), false) == OutputFormat::Yaml);
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

        // A complete work context needs no dummy request or material field.
        // File transport must preserve it exactly, including optional selection.
        let contract = declaration();
        for context in [
            json!({"target":".","task":"bounded task"}),
            json!({"target":".","task":"bounded task","reference":"owner:request:planning:planning/create/v1","projection":"carried"}),
        ] {
            let mut file = parse(&contract, &args(&["start", "--input", "-"]))
                .unwrap()
                .unwrap();
            carry_input(&contract, &mut file, context.clone()).unwrap();
            assert_eq!(file.values, context);
            let mut conflicting = parse(
                &contract,
                &args(&["start", "--input", "-", "--task", "different"]),
            )
            .unwrap()
            .unwrap();
            assert!(carry_input(&contract, &mut conflicting, context).is_err());
        }
        let request = json!({"kind":"agentic-workspace/public-request/v1","owner":"planning"});
        let mut bare = parse(&contract, &args(&["start", "--input", "-"]))
            .unwrap()
            .unwrap();
        carry_input(&contract, &mut bare, request.clone()).unwrap();
        assert_eq!(bare.values["request"], request);
    }

    #[test]
    fn bare_invocations_require_explicit_work_context() {
        let contract = declaration();
        let action = json!({"kind":"agentic-workspace/operation-invocation/v1"});
        for context in [
            args(&[]),
            args(&["--target", ".", "--task", "bounded task"]),
            args(&["--target", ".", "--changed", "a"]),
            args(&["--task", "bounded task", "--changed", "a"]),
        ] {
            let mut arguments = args(&["invoke", "--input", "-"]);
            arguments.extend(context);
            let mut parsed = parse(&contract, &arguments).unwrap().unwrap();
            assert!(carry_input(&contract, &mut parsed, action.clone()).is_err());
            assert!(parsed.values.get("invocation").is_none());
        }
        let mut parsed = parse(
            &contract,
            &args(&[
                "invoke",
                "--input",
                "-",
                "--target",
                ".",
                "--task",
                "bounded task",
                "--changed",
                "a",
                "b",
            ]),
        )
        .unwrap()
        .unwrap();
        carry_input(&contract, &mut parsed, action.clone()).unwrap();
        assert_eq!(
            parsed.values,
            json!({"target":".","task":"bounded task","changed":["a","b"],"invocation":action})
        );

        let envelope = json!({"target":".","task":"bounded task","changed":[],"invocation":action});
        for missing in ["target", "task", "changed"] {
            let mut incomplete = envelope.clone();
            incomplete.as_object_mut().unwrap().remove(missing);
            let mut parsed = parse(&contract, &args(&["invoke", "--input", "-"]))
                .unwrap()
                .unwrap();
            assert!(carry_input(&contract, &mut parsed, incomplete).is_err());
            assert!(parsed.values.get("invocation").is_none());
        }
        let mut parsed = parse(&contract, &args(&["invoke", "--input", "-"]))
            .unwrap()
            .unwrap();
        carry_input(&contract, &mut parsed, envelope.clone()).unwrap();
        assert_eq!(parsed.values, envelope);

        let mut parsed = parse(
            &contract,
            &args(&["invoke", "--input", "-", "--reference", "exact-action-ref"]),
        )
        .unwrap()
        .unwrap();
        let carriage = json!({"kind":"agentic-workspace/operating-carriage/v1","context":{"target":".","task":"bounded task","changed":[]}});
        carry_input(&contract, &mut parsed, carriage.clone()).unwrap();
        assert_eq!(
            parsed.values,
            json!({"reference":"exact-action-ref","invocation":carriage})
        );
    }

    #[test]
    fn rejects_hidden_authority_and_invalid_transport_inputs() {
        for arguments in [
            args(&["invoke"]),
            args(&["start", "--relevant", "true"]),
            args(&["start", "--target", ".", "--target", "other"]),
            args(&["start", "--format", "text"]),
            args(&["start", "--changed"]),
            args(&["start", "--observation", "fact", "--need", "prerequisite"]),
            args(&["start", "--source", "a.txt"]),
            args(&["start", "--need", "prerequisite", "--coverage", "complete"]),
            args(&["invoke", "--input", "-", "--observation", "fact"]),
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
