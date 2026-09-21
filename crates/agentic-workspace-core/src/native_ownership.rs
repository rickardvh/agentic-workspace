//! Portable package facts composed with repository-owned declarations.
//! Only authenticated prior package facts may authorize a changed package value.
use crate::CoreError;
use serde_json::{Value, json};
use std::{
    collections::BTreeSet,
    io::Write,
    path::Path,
    process::{Command, Stdio},
};

pub(crate) const LEDGER: &str = ".agentic-workspace/OWNERSHIP.toml";
pub(crate) const PROFILE: &str = ".agentic-workspace/READING.json";

fn err(e: impl ToString) -> CoreError {
    CoreError::new(e.to_string())
}

pub(crate) fn baseline() -> Value {
    parse(&baseline_text()).expect("portable ownership contract")
}

fn baseline_text() -> String {
    String::from_utf8(
        crate::native_payload::seed(LEDGER, crate::native_payload::Materialization::HostComposed)
            .expect("declared ownership materializer"),
    )
    .expect("portable ownership UTF-8")
}

pub(crate) fn has_host_meaning(text: &str) -> bool {
    parse(text).map_or(true, |value| value != baseline())
}

pub(crate) fn parse(text: &str) -> Result<Value, CoreError> {
    let value: toml::Value = toml::from_str(text).map_err(err)?;
    let value = serde_json::to_value(value).map_err(err)?;
    let schema: Value = serde_json::from_str(include_str!(
        "../../../src/agentic_workspace/contracts/schemas/ownership_ledger.schema.json"
    ))
    .map_err(err)?;
    crate::schema_validator(&schema, "ownership ledger")?
        .validate(&value)
        .map_err(err)?;
    if value["schema_version"] != 1
        || value
            .as_object()
            .unwrap()
            .keys()
            .any(|k| schema["properties"].get(k).is_none())
    {
        return Err(err(
            "unknown ownership contract; preserve and reconcile its source",
        ));
    }
    for (section, key) in [
        ("module_roots", "module"),
        ("managed_surfaces", "path"),
        ("fences", "name"),
        ("authority_surfaces", "concern"),
        ("subsystems", "id"),
    ] {
        let mut seen = BTreeSet::new();
        for row in value[section].as_array().into_iter().flatten() {
            if !seen.insert(row[key].as_str().unwrap()) {
                return Err(err(format!(
                    "duplicate ownership identity in {section}; preserve"
                )));
            }
        }
    }
    Ok(value)
}

// Package facts are a positive declaration, not a denylist of source-repo rows.
// Host-only keys/rows stay intact. Conflicting values require exact prior custody.
fn row_identity(path: &str) -> Option<&'static str> {
    match path {
        "/module_roots" => Some("module"),
        "/managed_surfaces" => Some("path"),
        "/fences" => Some("name"),
        "/authority_surfaces" => Some("concern"),
        "/subsystems" => Some("id"),
        _ => None,
    }
}

// Retired facts no longer constrain the host. Remove only unchanged old facts;
// preserve host additions and edited retired declarations as host-owned meaning.
fn retire_value(host: &mut Value, prior: &Value, path: &str) -> bool {
    if host == prior {
        return true;
    }
    if let (Some(h), Some(p)) = (host.as_object_mut(), prior.as_object()) {
        h.retain(|key, value| {
            p.get(key)
                .is_none_or(|old| !retire_value(value, old, &format!("{path}/{key}")))
        });
        return h.is_empty();
    }
    if let Some(key) = row_identity(path)
        && let Some(rows) = host.as_array_mut()
    {
        rows.retain(|row| {
            !prior
                .as_array()
                .into_iter()
                .flatten()
                .any(|old| old[key] == row[key] && old == row)
        });
        return rows.is_empty();
    }
    false
}

fn compose_value(
    host: &mut Value,
    package: &Value,
    prior: &Value,
    path: &str,
) -> Result<(), CoreError> {
    if host.is_null() {
        *host = package.clone();
        return Ok(());
    }
    if host == package {
        return Ok(());
    }
    if let (Some(h), Some(p)) = (host.as_object_mut(), package.as_object()) {
        for (key, old) in prior.as_object().into_iter().flatten() {
            if !p.contains_key(key)
                && let Some(current) = h.get_mut(key)
                && retire_value(current, old, &format!("{path}/{key}"))
            {
                h.remove(key);
            }
        }
        for (key, value) in p {
            compose_value(
                h.entry(key).or_insert(Value::Null),
                value,
                &prior[key],
                &format!("{path}/{key}"),
            )?;
        }
        return Ok(());
    }
    if let Some(key) = row_identity(path) {
        let rows = host
            .as_array_mut()
            .ok_or_else(|| err("ownership rows must be an array"))?;
        for old in prior.as_array().into_iter().flatten() {
            if !package
                .as_array()
                .unwrap()
                .iter()
                .any(|row| row[key] == old[key])
                && let Some(index) = rows.iter().position(|row| row[key] == old[key])
                && rows[index] == *old
            {
                rows.remove(index);
            }
        }
        for row in package.as_array().unwrap() {
            let old = prior
                .as_array()
                .and_then(|rows| rows.iter().find(|old| old[key] == row[key]))
                .unwrap_or(&Value::Null);
            if let Some(current) = rows.iter_mut().find(|current| current[key] == row[key]) {
                compose_value(current, row, old, &format!("{path}/{}", row[key]))?;
            } else {
                rows.push(row.clone());
            }
        }
        return Ok(());
    }
    if !prior.is_null() && host == prior {
        *host = package.clone();
        return Ok(());
    }
    Err(err(format!(
        "conflicting package ownership fact at {path}; preserve and reconcile its source"
    )))
}

pub(crate) fn compose(before: Option<&str>, prior: &Value) -> Result<String, CoreError> {
    let package = baseline();
    let Some(before) = before else {
        return Ok(baseline_text());
    };
    let original = parse(before)?;
    let mut resulting = original.clone();
    compose_value(&mut resulting, &package, prior, "")?;
    if resulting == original {
        return Ok(before.to_owned());
    }
    let rendered = toml::to_string_pretty(&resulting).map_err(err)?;
    parse(&rendered)?;
    Ok(rendered)
}

pub(crate) fn profile(target: &Path, ledger: &str) -> Result<String, CoreError> {
    let parsed = parse(ledger)?;
    let mut profile: Value = serde_json::from_slice(&crate::native_payload::seed(
        PROFILE,
        crate::native_payload::Materialization::TargetDerived,
    )?)
    .map_err(err)?;
    // Project the proposed bytes through the target path's Git clean semantics.
    // The ledger need not have been written or staged; custody remains raw bytes.
    profile["source"]["git_blob_sha1"] = json!(git_blob_identity(target, ledger.as_bytes())?);
    profile["entries"] = json!(
        parsed["authority_surfaces"]
            .as_array()
            .into_iter()
            .flatten()
            .filter_map(|row| {
                row["read"].as_object().map(|read| {
                    let mut entry = read.clone();
                    entry.insert("concern".into(), row["concern"].clone());
                    entry.insert("owner".into(), row["owner"].clone());
                    Value::Object(entry)
                })
            })
            .collect::<Vec<_>>()
    );
    Ok(format!(
        "{}\n",
        serde_json::to_string_pretty(&profile).map_err(err)?
    ))
}

/// Read-only build-time binding; ordinary adoption uses the same producer.
pub(crate) fn render_profile(input: Value) -> Result<Value, CoreError> {
    #[derive(serde::Deserialize)]
    #[serde(deny_unknown_fields)]
    struct Input {
        target: String,
        ledger: String,
    }
    let input: Input = serde_json::from_value(input).map_err(err)?;
    Ok(json!({"text": profile(Path::new(&input.target), &input.ledger)?}))
}

fn git_blob_identity(target: &Path, bytes: &[u8]) -> Result<String, CoreError> {
    let repository = Command::new("git")
        .arg("-C")
        .arg(target)
        .args(["rev-parse", "--git-dir"])
        .output()
        .map_err(err)?;
    if !repository.status.success() {
        return Err(err(
            "Git repository identity unavailable for ownership read profile",
        ));
    }
    // Path-aware hashing can launch repository-configured filter commands.
    // Observation has no callback authority: only Git's built-in conversions
    // are available here, regardless of whether a selected driver is required.
    let attributes = Command::new("git")
        .arg("-C")
        .arg(target)
        .args(["check-attr", "-z", "filter", "--", LEDGER])
        .output()
        .map_err(err)?;
    let fields: Vec<_> = attributes.stdout.split(|b| *b == 0).collect();
    if !attributes.status.success()
        || fields.len() != 4
        || fields[0] != LEDGER.as_bytes()
        || fields[1] != b"filter"
        || !fields[3].is_empty()
    {
        return Err(err(
            "Git filter attributes unavailable for ownership read profile",
        ));
    }
    if !matches!(fields[2], b"unspecified" | b"unset") {
        return Err(err(
            "Git identity unavailable: ownership read profile cannot execute a selected filter",
        ));
    }
    // check-attr spells both its state and a literal driver named "unset" or
    // "unspecified" alike. Do not let those names hide executable callbacks.
    let state = std::str::from_utf8(fields[2]).map_err(err)?;
    let reserved_driver = Command::new("git")
        .arg("-C")
        .arg(target)
        .args([
            "config",
            "--get-regexp",
            &format!("^filter\\.{state}\\.(clean|process)$"),
        ])
        .output()
        .map_err(err)?;
    if reserved_driver.status.code() != Some(1) {
        return Err(err(
            "Git identity unavailable: ownership read profile cannot execute a selected filter",
        ));
    }
    let mut child = Command::new("git")
        .arg("-C")
        .arg(target)
        .args(["hash-object", "--stdin", &format!("--path={LEDGER}")])
        .stdin(Stdio::piped())
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .spawn()
        .map_err(err)?;
    let written = child.stdin.take().unwrap().write_all(bytes);
    let output = child.wait_with_output().map_err(err)?;
    written.map_err(err)?;
    let identity = String::from_utf8(output.stdout).map_err(err)?;
    let identity = identity.trim();
    if !output.status.success()
        || identity.len() != 40
        || !identity.bytes().all(|b| b.is_ascii_hexdigit())
    {
        return Err(err(
            "Git SHA-1 blob identity unavailable for ownership read profile",
        ));
    }
    Ok(identity.to_owned())
}

pub(crate) fn profile_matches(actual: &str, expected: &str) -> bool {
    // Formatting is not authority; every projected field still must match.
    serde_json::from_str::<Value>(actual)
        .ok()
        .zip(serde_json::from_str::<Value>(expected).ok())
        .is_some_and(|(a, b)| a == b)
}

/// Only the declared generated projection can be regenerated without prior
/// custody. User additions to the envelope are not silently discarded.
pub(crate) fn admit_profile(before: Option<&str>) -> Result<(), CoreError> {
    let Some(before) = before else {
        return Ok(());
    };
    let mut value: Value = serde_json::from_str(before).map_err(err)?;
    let mut template: Value = serde_json::from_slice(&crate::native_payload::seed(
        PROFILE,
        crate::native_payload::Materialization::TargetDerived,
    )?)
    .map_err(err)?;
    if value["source"]["path"] != LEDGER
        || !value["source"]["git_blob_sha1"]
            .as_str()
            .is_some_and(|s| s.len() == 40 && s.bytes().all(|b| b.is_ascii_hexdigit()))
        || value["source"].as_object().map(|o| o.len()) != Some(2)
        || !value["entries"].is_array()
    {
        return Err(err("unknown read profile structure; preserve"));
    }
    for entry in value["entries"].as_array().unwrap() {
        if entry.as_object().map(|o| o.len()) != Some(5)
            || !["concern", "owner", "select"]
                .iter()
                .all(|k| entry[k].is_string())
            || !["refs", "unknown"].iter().all(|k| {
                entry[k]
                    .as_array()
                    .is_some_and(|a| a.iter().all(Value::is_string))
            })
        {
            return Err(err("unknown read profile entry; preserve"));
        }
    }
    for field in ["source", "entries"] {
        value.as_object_mut().unwrap().remove(field);
        template.as_object_mut().unwrap().remove(field);
    }
    if value != template {
        return Err(err("conflicting read profile envelope; preserve"));
    }
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn package_fact_refresh_requires_prior_custody_and_preserves_host_meaning() {
        assert!(crate::native_payload::shipped(LEDGER).is_err());
        assert!(crate::native_payload::shipped(PROFILE).is_err());
        let mut prior = baseline();
        prior["module_roots"][0]["uninstall_policy"] = json!("previous-package-policy");
        let mut host = prior.clone();
        host["subsystems"] = json!([{"id":"backend","paths":["backend/**"],"owns":["requests"],"does_not_own":["frontend"],"proof":["host-test"],"escalate_when":["API changes"]}]);
        let text = toml::to_string_pretty(&host).unwrap();
        assert!(compose(Some(&text), &Value::Null).is_err());
        let resulting = compose(Some(&text), &prior).unwrap();
        let parsed = parse(&resulting).unwrap();
        assert_eq!(parsed["subsystems"], host["subsystems"]);
        assert_eq!(parsed["module_roots"], baseline()["module_roots"]);
        assert_eq!(compose(Some(&resulting), &baseline()).unwrap(), resulting);
        host["module_roots"][0]["path"] = json!("unexpected/");
        assert!(compose(Some(&toml::to_string_pretty(&host).unwrap()), &prior).is_err());
        assert!(
            compose(
                Some("schema_version=1\nunknown_authority=true\n"),
                &Value::Null
            )
            .is_err()
        );
    }
}
