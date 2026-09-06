//! Host-admitted instruction bindings. Markdown declares; the independently
//! selected immutable repository snapshot admits those exact binding scopes.
use crate::{
    CoreError,
    decision_source::{hash, read, relative},
};
use cap_std::{ambient_authority, fs::Dir};
use serde::Deserialize;
use serde_json::{Value, json};
use std::{collections::BTreeSet, process::Command};

#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct Input {
    target: String,
    admitted_revision: Option<String>,
    sources: Vec<Source>,
}

#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct Source {
    reference: String,
    revision: String,
}

fn bindings(bytes: &[u8]) -> Option<(Vec<Value>, Vec<String>)> {
    let text = std::str::from_utf8(bytes).ok()?;
    let mut lines = text.lines();
    if lines.next()? != "---" {
        return Some((vec![], vec![]));
    }
    let mut field = "";
    let mut seen = BTreeSet::new();
    let mut checks = vec![];
    let mut protect = vec![];
    for line in lines {
        if line == "---" {
            return Some((checks, protect));
        }
        let value = line.trim();
        if value.is_empty() || value.starts_with('#') {
            continue;
        }
        let values = if !line.starts_with([' ', '-']) && value.contains(':') {
            let (key, rest) = value.split_once(':')?;
            field = key.trim();
            if !["paths", "routes", "read", "use", "checks", "protect"].contains(&field)
                || !seen.insert(field)
            {
                return None;
            }
            let rest = rest.trim();
            if rest.is_empty() {
                continue;
            }
            rest.strip_prefix('[')?
                .strip_suffix(']')?
                .split(',')
                .map(str::trim)
                .filter(|v| !v.is_empty())
                .map(|v| (v.trim_matches(['\'', '"']), false))
                .collect::<Vec<_>>()
        } else {
            vec![(value.strip_prefix('-')?.trim(), true)]
        };
        for (value, block) in values {
            if value.is_empty() {
                return None;
            }
            if field == "checks" {
                if let Some(command) = value.strip_prefix("run:").filter(|_| block) {
                    let command = command.trim();
                    if command.is_empty() {
                        return None;
                    }
                    checks.push(json!({"run":command}));
                } else {
                    checks.push(json!(value.trim_matches(['\'', '"'])));
                }
            }
            if field == "protect" {
                let value = value.trim_matches(['\'', '"']);
                if value.starts_with(['/', '~'])
                    || value.contains(['\\', ':'])
                    || value.split('/').any(|p| p == "..")
                {
                    return None;
                }
                protect.push(value.to_owned());
            }
        }
    }
    None
}

pub fn view(value: Value) -> Result<Value, CoreError> {
    let input: Input = serde_json::from_value(value).map_err(|e| CoreError::new(e.to_string()))?;
    if input.sources.len() > 64 {
        return Err(CoreError::new("select at most 64 instruction sources"));
    }
    let revision = input.admitted_revision.unwrap_or_default();
    if !revision.is_empty()
        && (revision.len() != 40 || !revision.bytes().all(|b| b.is_ascii_hexdigit()))
    {
        return Err(CoreError::new(
            "instruction admission requires an exact Git commit",
        ));
    }
    let mut results = vec![];
    let snapshot_available = if !revision.is_empty() {
        let object = Command::new("git")
            .arg("-C")
            .arg(&input.target)
            .args(["cat-file", "-t", &revision])
            .output()
            .map_err(|e| CoreError::new(e.to_string()))?;
        object.status.success() && object.stdout == b"commit\n"
    } else {
        false
    };
    let mut seen = BTreeSet::new();
    for observed in input.sources {
        let source = observed.reference;
        if !crate::sha256_revision(&observed.revision) {
            return Err(CoreError::new(
                "instruction source requires an observed sha256 revision",
            ));
        }
        relative(&source)?;
        if !source.starts_with(".agentic-workspace/instructions/")
            || !source.ends_with(".md")
            || !seen.insert(source.clone())
        {
            return Err(CoreError::new(
                "instruction source must be a unique exact scoped Markdown path",
            ));
        }
        let mut row = json!({"source":{"reference":source}, "status":"unadmitted", "checks":[], "protect":[], "authority":{"effects":[],"target_patterns":[]}});
        if !revision.is_empty() && !snapshot_available {
            row["status"] = json!("unavailable");
        }
        if snapshot_available {
            let snapshot = Command::new("git")
                .arg("-C")
                .arg(&input.target)
                .args(["show", &format!("{revision}:{source}")])
                .env("GIT_LITERAL_PATHSPECS", "1")
                .output()
                .map_err(|e| CoreError::new(e.to_string()))?;
            if snapshot.status.success() && snapshot.stdout.len() <= 262144 {
                let root = Dir::open_ambient_dir(&input.target, ambient_authority())
                    .map_err(|e| CoreError::new(e.to_string()))?;
                row["source"]["revision"] = json!(hash(&snapshot.stdout));
                row["source"]["owner"] = json!("repository");
                row["admitted_revision"] = json!(revision);
                row["status"] = json!("stale");
                let regular = root
                    .symlink_metadata(&source)
                    .is_ok_and(|m| m.is_file() && !m.is_symlink());
                if regular
                    && observed.revision == hash(&snapshot.stdout)
                    && read(&root, &source)
                        .is_ok_and(|bytes| hash(&bytes) == hash(&snapshot.stdout))
                {
                    if let Some((checks, protect)) = bindings(&snapshot.stdout) {
                        let hard_checks = checks
                            .iter()
                            .any(|c| !c.as_str().is_some_and(|s| s.starts_with("requirement:")));
                        let mut effects = vec![];
                        let mut targets = vec![];
                        if hard_checks {
                            effects.push("require");
                            targets.push("claim:complete".to_owned());
                        }
                        if !protect.is_empty() {
                            effects.push("restrict");
                            targets.extend(protect.iter().map(|p| format!("effect:write:{p}")));
                        }
                        row["status"] = json!("current");
                        row["checks"] = json!(checks);
                        row["protect"] = json!(protect);
                        row["authority"] = json!({"effects":effects,"target_patterns":targets});
                    } else {
                        row["status"] = json!("invalid");
                    }
                }
            }
        }
        results.push(row);
    }
    Ok(json!({"kind":"agentic-workspace/instruction-source-admission/v1","sources":results}))
}
