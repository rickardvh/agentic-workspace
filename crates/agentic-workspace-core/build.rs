use sha2::{Digest, Sha256};
use std::{collections::BTreeSet, env, fs, path::PathBuf};

fn main() {
    let root = PathBuf::from(env::var("CARGO_MANIFEST_DIR").unwrap()).join("../..");
    let manifest = root.join("src/agentic_workspace/contracts/workspace_surfaces.json");
    println!("cargo:rerun-if-changed={}", manifest.display());
    let value: serde_json::Value = serde_json::from_slice(&fs::read(manifest).unwrap()).unwrap();
    let portable: BTreeSet<_> = value["derivation"]["portable_sources"]
        .as_array()
        .expect("explicit portable source boundary")
        .iter()
        .map(|v| v.as_str().unwrap())
        .collect();
    let source_only: BTreeSet<_> = value["derivation"]["source_only_inputs"]
        .as_array()
        .expect("source-only input boundary")
        .iter()
        .map(|v| v.as_str().unwrap())
        .collect();
    assert!(
        portable.is_disjoint(&source_only),
        "source-only policy cannot be a portable input"
    );
    for path in portable.union(&source_only) {
        assert!(
            !path.contains(['\\', ':'])
                && path.split('/').all(|part| !matches!(part, "" | "." | "..")),
            "portable sources require canonical repository-relative paths"
        );
    }
    let surfaces = value["surfaces"].as_array().expect("host surfaces");
    assert_eq!(
        surfaces.len(),
        value["payload_files"].as_array().unwrap().len()
    );
    let mut identity = Sha256::new();
    identity.update(serde_json::to_vec(&value).unwrap());
    let mut seen = BTreeSet::new();
    let mut generated = String::from("const PAYLOAD: &[(&str, Materialization, &[u8])] = &[\n");
    for reference in value["payload_files"].as_array().expect("payload manifest") {
        let reference = reference.as_str().expect("payload path");
        assert!(seen.insert(reference), "duplicate public host surface");
        let rows: Vec<_> = surfaces
            .iter()
            .filter(|row| row["path"] == reference)
            .collect();
        assert_eq!(
            rows.len(),
            1,
            "every host surface needs exactly one materialization"
        );
        let material = &rows[0]["materialization"];
        let mode = match material["mode"]
            .as_str()
            .expect("host materialization mode")
        {
            "package-verbatim" => {
                assert_eq!(material.as_object().unwrap().len(), 2);
                assert!(
                    !matches!(
                        reference,
                        ".agentic-workspace/OWNERSHIP.toml" | ".agentic-workspace/READING.json"
                    ),
                    "composite and derived surfaces cannot be copied"
                );
                "PackageVerbatim"
            }
            "host-composed" => {
                assert_eq!(material.as_object().unwrap().len(), 3);
                assert_eq!(reference, ".agentic-workspace/OWNERSHIP.toml");
                assert_eq!(material["composer"], "ownership-v1");
                "HostComposed"
            }
            "target-derived" => {
                assert_eq!(material.as_object().unwrap().len(), 3);
                assert_eq!(reference, ".agentic-workspace/READING.json");
                assert_eq!(material["input"], ".agentic-workspace/OWNERSHIP.toml");
                assert_eq!(material["renderer"], "ownership-read-profile-v1");
                assert!(
                    surfaces.iter().any(|row| row["path"] == material["input"]
                        && row["materialization"]["mode"] == "host-composed"),
                    "derived dependency must be a declared host composition"
                );
                "TargetDerived"
            }
            _ => panic!("unsupported public host materialization"),
        };
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
        if mode != "TargetDerived" {
            let input = material["source"]
                .as_str()
                .expect("portable semantic input");
            assert!(
                portable.contains(input),
                "host input must have explicit portable promotion"
            );
            let input = root.join(input).canonicalize().expect("portable input");
            assert!(
                input.starts_with(root.canonicalize().unwrap()),
                "portable input escapes producer root"
            );
            assert!(
                !source_only.iter().any(|reference| {
                    let source = root.join(reference);
                    source
                        .canonicalize()
                        .unwrap_or_else(|_| root.canonicalize().unwrap().join(reference))
                        == input
                }),
                "portable input aliases source-only policy"
            );
            println!("cargo:rerun-if-changed={}", input.display());
            assert_eq!(
                fs::read_to_string(&source).unwrap().replace("\r\n", "\n"),
                fs::read_to_string(input).unwrap().replace("\r\n", "\n"),
                "stale portable package seed; regenerate agent interface"
            );
        }
        identity.update(reference.as_bytes());
        identity.update(mode.as_bytes());
        identity.update(
            fs::read_to_string(&source)
                .unwrap()
                .replace("\r\n", "\n")
                .as_bytes(),
        );
        generated.push_str(&format!(
            "({reference:?}, Materialization::{mode}, include_bytes!({:?})),\n",
            source.to_str().unwrap()
        ));
    }
    generated.push_str("];\n");
    generated.push_str(&format!(
        "const PAYLOAD_REVISION: &str = \"sha256:{:x}\";\n",
        identity.finalize()
    ));
    fs::write(
        PathBuf::from(env::var("OUT_DIR").unwrap()).join("payload.rs"),
        generated,
    )
    .unwrap();
}
