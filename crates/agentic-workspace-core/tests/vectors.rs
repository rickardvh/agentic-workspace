use serde_json::Value;
use std::fs;
use std::path::PathBuf;

fn vectors() -> Value {
    let path =
        PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("../../tests/vectors/source_decision.json");
    serde_json::from_str(&fs::read_to_string(path).expect("shared vectors are readable"))
        .expect("shared vectors are valid JSON")
}

fn selected<'a>(mut value: &'a Value, path: &str) -> &'a Value {
    for part in path.split('.') {
        value = if let Ok(index) = part.parse::<usize>() {
            &value[index]
        } else {
            &value[part]
        };
    }
    value
}

#[test]
fn shared_success_vectors_match() {
    for case in vectors()["cases"].as_array().expect("cases are an array") {
        let decision = agentic_workspace_core::compile_value(case["input"].clone())
            .unwrap_or_else(|error| panic!("{}: {error}", case["id"]));
        for (path, expected) in case["expect"].as_object().expect("expect is an object") {
            assert_eq!(
                selected(&decision, path),
                expected,
                "{}: {path}",
                case["id"]
            );
        }
    }
}

#[test]
fn shared_error_vectors_fail_closed() {
    for case in vectors()["error_cases"]
        .as_array()
        .expect("error cases are an array")
    {
        let error = agentic_workspace_core::compile_value(case["input"].clone())
            .expect_err("case must fail");
        assert!(
            error.to_string().contains(
                case["error_contains"]
                    .as_str()
                    .expect("error fragment is text")
            ),
            "{}: {error}",
            case["id"]
        );
    }
}

#[test]
fn normalized_source_permutations_are_stable() {
    for case in vectors()["equivalent_inputs"]
        .as_array()
        .expect("equivalent inputs are an array")
    {
        let decisions = case["inputs"]
            .as_array()
            .expect("inputs are an array")
            .iter()
            .map(|input| {
                agentic_workspace_core::compile_value(input.clone()).expect("permutation compiles")
            })
            .collect::<Vec<_>>();
        assert!(
            decisions.windows(2).all(|pair| pair[0] == pair[1]),
            "{}",
            case["id"]
        );
    }
}
