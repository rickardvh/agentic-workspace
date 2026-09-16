//! Private selection of optional detail, not a source of owner authority.
//! Every resolution still composes current mandatory owner contributions.
#[derive(Clone, Default)]
pub(crate) enum Resolution {
    #[default]
    Full,
    Frontier(Option<String>),
}
impl Resolution {
    pub(crate) fn detail(&self, owner: &str) -> bool {
        match self {
            Self::Full => true,
            Self::Frontier(selected) => selected.as_deref() == Some(owner),
        }
    }
}

#[cfg(test)]
thread_local! {
    static BUILT: std::cell::RefCell<Vec<&'static str>> = const { std::cell::RefCell::new(Vec::new()) };
}
#[cfg(test)]
pub(crate) fn built(branch: &'static str) {
    BUILT.with(|v| v.borrow_mut().push(branch));
}
#[cfg(test)]
mod tests {
    use super::*;
    use serde_json::{Value, json};
    fn observe(context: Value, resolution: Resolution) -> (Value, Vec<&'static str>) {
        BUILT.with(|v| v.borrow_mut().clear());
        let value = crate::native_public::start_selected(context, &resolution).unwrap();
        let work = BUILT.with(|v| v.borrow().clone());
        (value, work)
    }
    #[test]
    fn optional_builders_are_bypassed_and_selected_proof_keeps_exact_authority() {
        let root = std::env::temp_dir().join(format!(
            "aw-frontier-{}-{}",
            std::process::id(),
            std::time::SystemTime::now()
                .duration_since(std::time::UNIX_EPOCH)
                .unwrap()
                .as_nanos()
        ));
        std::fs::create_dir_all(root.join(".agentic-workspace/verification")).unwrap();
        std::fs::write(
            root.join(".agentic-workspace/config.toml"),
            "[workspace]\ncli_invoke='agentic-workspace'\n",
        )
        .unwrap();
        std::fs::write(root.join("a.txt"), "subject").unwrap();
        let context = json!({"target":root,"task":"Prove selected work","changed":["a.txt"]});
        for (path, bytes) in [
            (
                ".agentic-workspace/skills/REGISTRY.json",
                include_str!("../../../.agentic-workspace/skills/REGISTRY.json"),
            ),
            (
                ".agentic-workspace/skills/workspace-proof-selection/SKILL.md",
                include_str!(
                    "../../../.agentic-workspace/skills/workspace-proof-selection/SKILL.md"
                ),
            ),
        ] {
            let path = root.join(path);
            std::fs::create_dir_all(path.parent().unwrap()).unwrap();
            std::fs::write(path, bytes).unwrap();
        }
        for count in [1, 128] {
            let commands: Vec<String> = (0..count).map(|i| format!("echo check-{i}")).collect();
            std::fs::write(root.join(".agentic-workspace/verification/manifest.toml"), format!("schema_version='agentic-workspace/verification-manifest/v1'\n[proof_routes]\n[protocols.example]\napplies_to_paths=['a.txt']\ncommands={}\n",serde_json::to_string(&commands).unwrap())).unwrap();
            let (full, full_work) = observe(context.clone(), Resolution::Full);
            let (frontier, frontier_work) = observe(context.clone(), Resolution::Frontier(None));
            assert_eq!(frontier["decision_packet"], full["decision_packet"]);
            assert_eq!(frontier["_detail_bindings"], full["_detail_bindings"]);
            assert_eq!(frontier_work, vec!["verification-contribution"]);
            assert_eq!(
                full_work.iter().filter(|v| **v == "proof-choice").count(),
                count
            );
            assert_eq!(
                full_work.iter().filter(|v| **v == "proof-report").count(),
                count
            );
            assert_eq!(
                full_work
                    .iter()
                    .filter(|v| **v == "verification-contribution")
                    .count(),
                1
            );
            assert!(full_work.contains(&"configuration-fields"));
            let request = full["verification"]["execution_requests"][0].clone();
            let selected = {
                let mut value = context.clone();
                value["request"] = request;
                value
            };
            let (selected_full, _) = observe(selected.clone(), Resolution::Full);
            let (selected_proof, proof_work) =
                observe(selected, Resolution::Frontier(Some("proof".into())));
            assert_eq!(
                selected_full["decision_packet"],
                selected_proof["decision_packet"]
            );
            assert_eq!(proof_work, vec!["verification-contribution"]);
            assert!(!selected_proof["decision_packet"]["primary_action"].is_null());
            let (_, config_work) = observe(
                context.clone(),
                Resolution::Frontier(Some("configuration_write".into())),
            );
            assert!(config_work.contains(&"configuration-fields"));
            assert!(!config_work.contains(&"proof-choice"));
            {
                BUILT.with(|v| v.borrow_mut().clear());
                let effect = crate::native_public::invoke_selected(
                    json!({"target":root,"task":context["task"],"changed":context["changed"],"invocation":selected_proof["decision_packet"]["primary_action"]}),
                    &Resolution::Frontier(None),
                );
                assert_eq!(effect["effect_outcome"]["status"], "committed", "{effect}");
                assert_eq!(effect["continuation_status"], "current");
                let work = BUILT.with(|v| v.borrow().clone());
                let boundary = work
                    .iter()
                    .position(|v| *v == "post-effect-continuation")
                    .unwrap();
                assert_eq!(&work[boundary + 1..], &["verification-contribution"]);
                let mut claim =
                    effect["continuation"]["result"]["verification"]["requests"][0].clone();
                claim["arguments"]["evidence_refs"] =
                    json!([effect["value"]["publication"]["reference"]]);
                let mut admitted_context = context.clone();
                admitted_context["request"] = claim;
                let (admitted, admission_work) =
                    observe(admitted_context.clone(), Resolution::Frontier(None));
                assert_eq!(admission_work, vec!["verification-contribution"]);
                assert_eq!(
                    admitted["verification"]["evidence"][0]["checked_scope"]["claim"],
                    "selected-command-passed"
                );
                let (full_admitted, _) = observe(admitted_context.clone(), Resolution::Full);
                assert_eq!(
                    admitted["decision_packet"],
                    full_admitted["decision_packet"]
                );
                let (_, selected_admission_work) =
                    observe(admitted_context, Resolution::Frontier(Some("proof".into())));
                assert_eq!(selected_admission_work, vec!["verification-contribution"]);
                if count == 128 {
                    BUILT.with(|v| v.borrow_mut().clear());
                    let composed = crate::native_proof_procedure::view(json!({"target":root,"task":context["task"],"changed":context["changed"],"request":{"operation":"execute","request":full["verification"]["execution_requests"][0]}})).unwrap();
                    assert_eq!(
                        composed["proof"]["evidence"][0]["checked_scope"]["claim"],
                        "selected-command-passed",
                        "{composed}"
                    );
                    let work = BUILT.with(|v| v.borrow().clone());
                    let boundary = work
                        .iter()
                        .position(|v| *v == "post-effect-continuation")
                        .unwrap();
                    assert!(
                        work[boundary + 1..]
                            .iter()
                            .all(|v| *v == "verification-contribution"),
                        "{work:?}"
                    );
                    assert_eq!(work[boundary + 1..].len(), 2);
                }
            }
            eprintln!(
                "frontier-work commands={count} full_build_events={} compact_build_events={} selected_proof_build_events={}",
                full_work.len(),
                frontier_work.len(),
                proof_work.len()
            );
        }
        // Observe actual construction, not merely the absence of rendered text.
        std::fs::remove_file(root.join(".agentic-workspace/verification/manifest.toml")).unwrap();
        let reference = ".agentic-workspace/memory/repo/domains/advice.md";
        std::fs::create_dir_all(root.join(".agentic-workspace/memory/repo/domains")).unwrap();
        std::fs::write(root.join(".agentic-workspace/memory/repo/manifest.toml"), format!("version=1\n[notes.\"{reference}\"]\nroutes_from=['a.txt']\nsummary='Bounded selected advice'\n")).unwrap();
        // Exercise UTF-8 and CRLF across streaming chunk boundaries, including
        // a large single line that must never become a compact body buffer.
        for body in [
            "Small selected advice".to_owned(),
            format!(
                "{}\u{00e9}\r\n{}\r",
                "x".repeat(8191),
                "detail".repeat(2000)
            ),
            format!("{}\r\nend", "x".repeat(8191)),
        ] {
            std::fs::write(root.join(reference), body.as_bytes()).unwrap();
            let (compact, compact_work) = observe(context.clone(), Resolution::Frontier(None));
            let row = &compact["memory"]["advisory_context"][0];
            assert_eq!(
                row["source"]["revision"],
                crate::decision_source::hash(body.as_bytes())
            );
            if body.len() > 4096 {
                assert_eq!(row["status"], "selected-detail-deferred");
                assert!(!compact_work.contains(&"memory-body"));
            } else {
                assert_eq!(row["body"], body);
                assert_eq!(
                    compact_work.iter().filter(|v| **v == "memory-body").count(),
                    1
                );
            }
            for selected in ["memory", "proof"] {
                let (expanded, built) =
                    observe(context.clone(), Resolution::Frontier(Some(selected.into())));
                assert_eq!(expanded["memory"]["advisory_context"][0]["body"], body);
                assert_eq!(built.iter().filter(|v| **v == "memory-body").count(), 1);
                assert_eq!(expanded["decision_packet"], compact["decision_packet"]);
                assert_eq!(expanded["_detail_bindings"], compact["_detail_bindings"]);
            }
            std::fs::write(root.join(reference), "Changed after selection").unwrap();
            assert!(
                crate::native_memory::read_selected(
                    &root,
                    reference,
                    row["source"]["revision"].as_str().unwrap()
                )
                .is_err()
            );
        }
        for invalid_bytes in [
            [vec![b'x'; 8191], vec![0xff]].concat(),
            [vec![b'x'; 8191], vec![0xc3]].concat(),
            vec![b'x'; crate::decision_source::MAX_SOURCE_BYTES + 1],
        ] {
            std::fs::write(root.join(reference), invalid_bytes).unwrap();
            let (invalid, built) = observe(context.clone(), Resolution::Frontier(None));
            assert_eq!(invalid["memory"]["status"], "reconciliation-required");
            assert!(!built.contains(&"memory-body"));
        }
        std::fs::remove_dir_all(root).unwrap();
    }
}
