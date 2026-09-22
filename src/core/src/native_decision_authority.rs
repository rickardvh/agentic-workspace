//! Exact source-owned delegations for bounded semantic choices; never effect or review custody.
use serde_json::{Value, json};
use std::collections::BTreeSet;

pub(crate) fn delegated(config: &Value, owner: &str, paths: &[String]) -> Option<Value> {
    if paths.is_empty() || paths.len() > 32 {
        return None;
    }
    let expected: BTreeSet<_> = paths.iter().cloned().collect();
    for path in &expected {
        crate::decision_source::relative(path).ok()?;
    }
    config["admissions"]["decision_delegations"].as_array()?.iter().find_map(|grant| {
        if grant["owner"] != owner { return None; }
        let mut actual = BTreeSet::new();
        for path in grant["scope"].as_array()? {
            let path=path.as_str()?.strip_prefix("path:")?;
            if path.contains(['*','?','[',']']) { return None; }
            crate::decision_source::relative(path).ok()?;
            if !actual.insert(path.to_owned()) { return None; }
        }
        (actual==expected).then(||json!({"kind":"exact-policy-delegated-decision","grant":grant,"policy_revision":config["revision"],"source":".agentic-workspace/config.toml#assurance.decision_delegations","identity_authentication":"not-claimed","independent_review":false}))
    })
}
