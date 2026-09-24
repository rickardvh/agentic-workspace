//! Disposable current-situation input. Producer labels are claims, never authority.
use crate::{CoreError, decision_source, digest};
use cap_std::{ambient_authority, fs::Dir};
use serde::Deserialize;
use serde_json::{Value, json};
use std::{collections::BTreeSet, path::Path};

#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct Material {
    id: String,
    kind: String,
    summary: String,
    source: Source,
    #[serde(default)]
    dependencies: Vec<Dependency>,
    work: Option<Value>,
}
#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct Source {
    producer: String,
    reference: String,
    revision: Option<String>,
    coverage: String,
}
#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct Dependency {
    reference: String,
    revision: String,
}

pub(crate) fn view(target: &Path, work: &Value, input: &[Value]) -> Result<Value, CoreError> {
    if input.len() > 16 || serde_json::to_vec(input).unwrap().len() > 65536 {
        return Err(CoreError::new("current material exceeds bounded ingress"));
    }
    let mut ids = BTreeSet::new();
    let mut rows = Vec::new();
    for value in input {
        let item: Material = serde_json::from_value(value.clone())
            .map_err(|_| CoreError::new("invalid current material shape"))?;
        if item.id.is_empty()
            || item.id.len() > 128
            || !ids.insert(item.id.clone())
            || !["observation", "need"].contains(&item.kind.as_str())
            || item.summary.trim().is_empty()
            || item.summary.len() > 8192
            || item.source.producer.is_empty()
            || item.source.producer.len() > 256
            || item.source.reference.is_empty()
            || item.source.reference.len() > 2048
            || !["bounded", "partial", "unknown"].contains(&item.source.coverage.as_str())
            || item
                .source
                .revision
                .as_ref()
                .is_some_and(|s| s.is_empty() || s.len() > 256)
            || item.dependencies.len() > 16
        {
            return Err(CoreError::new("invalid bounded current material fields"));
        }
        if item.work.as_ref().is_some_and(|w| w != work) {
            return Err(CoreError::new(
                "current material work changed; reobserve material",
            ));
        }
        for dependency in &item.dependencies {
            let root = Dir::open_ambient_dir(target, ambient_authority())
                .map_err(|e| CoreError::new(e.to_string()))?;
            let bytes = decision_source::read(&root, &dependency.reference)?;
            if decision_source::hash(&bytes) != dependency.revision {
                return Err(CoreError::new(
                    "current material dependency changed; reobserve material",
                ));
            }
        }
        let mut bound = value.clone();
        bound["work"] = work.clone();
        rows.push(json!({"material":bound,"revision":digest(&bound)?,
            "trust":"caller-asserted", "currentness":if item.dependencies.is_empty(){"unverified"}else{"dependencies-current"},
            "authority":"none; source labels and current bytes do not establish truth, policy, permission or proof"}));
    }
    Ok(
        json!({"kind":"agentic-workspace/current-material/v1","items":rows,
        "retention":"none; explicitly carry material or use an existing receiving owner"}),
    )
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn bounded_source_neutral_material_preserves_authority_and_dependency_scope() {
        let target = std::env::temp_dir().join(format!("aw-material-{}", std::process::id()));
        std::fs::create_dir_all(&target).unwrap();
        std::fs::write(target.join("source.txt"), "observed").unwrap();
        let work = json!({"kind":"current-work","id":"work"});
        for producer in ["user", "tool", "external-review", "independent-sensor"] {
            let item = json!({"id":"fact","kind":"observation","summary":"Current bounded material",
                "source":{"producer":producer,"reference":"opaque:source","coverage":"partial"},
                "dependencies":[{"reference":"source.txt","revision":decision_source::hash(b"observed")}]});
            let current = view(&target, &work, std::slice::from_ref(&item)).unwrap();
            assert_eq!(current["items"][0]["trust"], "caller-asserted");
            let bound = current["items"][0]["material"].clone();
            assert!(view(&target, &json!({"id":"other"}), &[bound]).is_err());
            std::fs::write(target.join("unrelated.txt"), "unrelated").unwrap();
            assert_eq!(
                view(&target, &work, std::slice::from_ref(&item)).unwrap(),
                current
            );
            let mut forged = item.clone();
            forged["source"]["authority"] = json!("human");
            assert!(view(&target, &work, &[forged]).is_err());
            let mut need = item.clone();
            need["kind"] = json!("need");
            assert!(view(&target, &work, &[need]).is_ok());
            std::fs::write(target.join("source.txt"), "changed").unwrap();
            assert!(view(&target, &work, std::slice::from_ref(&item)).is_err());
            std::fs::write(target.join("source.txt"), "observed").unwrap();
            assert!(view(&target, &work, &vec![item; 17]).is_err());
        }
        std::fs::remove_dir_all(target).unwrap();
    }
}
