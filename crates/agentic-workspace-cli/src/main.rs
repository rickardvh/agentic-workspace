use serde_json::{Value, json};
use std::{
    collections::BTreeSet,
    env, fs,
    io::{self, Read},
};

fn declaration() -> Value {
    serde_json::from_str::<Value>(include_str!(
        "../../../src/agentic_workspace/contracts/source_decision_contract.json"
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
        if !multiple && !seen.insert(field.to_owned()) {
            return Err(format!("{flag} may be supplied only once"));
        }
        index += 1;
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
    values.remove("format");
    Ok(Some(Parsed {
        command: args[0].clone(),
        values: Value::Object(values),
        input_path,
    }))
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
    let command = contract["commands"]
        .as_array()
        .unwrap()
        .iter()
        .find(|command| command["name"] == parsed.command)
        .unwrap();
    parsed.values[command["input_field"].as_str().unwrap()] = input;
    let result = match parsed.command.as_str() {
        "start" => agentic_workspace_core::native_public::start(parsed.values),
        "invoke" => agentic_workspace_core::native_public::invoke(parsed.values),
        _ => unreachable!("command declaration and adapter dispatch must agree"),
    }
    .map_err(|error| ("owner-rejected", error.to_string()))?;
    println!(
        "{}",
        serde_json::to_string(&result).expect("owner result is JSON")
    );
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
