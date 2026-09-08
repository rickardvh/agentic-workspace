use std::{env, fs, path::PathBuf};

fn main() {
    let root = PathBuf::from(env::var("CARGO_MANIFEST_DIR").unwrap()).join("../..");
    let manifest = root.join("src/agentic_workspace/contracts/workspace_surfaces.json");
    println!("cargo:rerun-if-changed={}", manifest.display());
    let value: serde_json::Value = serde_json::from_slice(&fs::read(manifest).unwrap()).unwrap();
    let mut generated = String::from("const PAYLOAD: &[(&str, &[u8])] = &[\n");
    for reference in value["payload_files"].as_array().expect("payload manifest") {
        let reference = reference.as_str().expect("payload path");
        assert!(
            reference.starts_with(".agentic-workspace/")
                && !reference.split('/').any(|part| part == "..")
        );
        let source = root
            .join("src/agentic_workspace/_payload")
            .join(reference)
            .canonicalize()
            .expect("shipped payload source");
        println!("cargo:rerun-if-changed={}", source.display());
        generated.push_str(&format!(
            "({reference:?}, include_bytes!({:?})),\n",
            source.to_str().unwrap()
        ));
    }
    generated.push_str("];\n");
    fs::write(
        PathBuf::from(env::var("OUT_DIR").unwrap()).join("payload.rs"),
        generated,
    )
    .unwrap();
}
