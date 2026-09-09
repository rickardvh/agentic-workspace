//! Host-admitted instruction bindings. Markdown declares; the independently
//! selected immutable repository snapshot admits those exact binding scopes.
use crate::{
    CoreError,
    decision_source::{hash, read, relative},
};
use cap_std::{ambient_authority, fs::Dir};
use serde::Deserialize;
use serde_json::{Value, json};
use std::{
    collections::BTreeSet,
    path::{Path, PathBuf},
    process::Command,
};

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

fn metadata(bytes: &[u8], result: &mut Value) -> Option<String> {
    let text = std::str::from_utf8(bytes).ok()?;
    let mut lines = text.lines();
    if lines.next()? != "---" {
        return Some(text.trim().to_owned());
    }
    let mut field = "";
    let mut seen = BTreeSet::new();
    while let Some(line) = lines.next() {
        if line == "---" {
            return Some(lines.collect::<Vec<_>>().join("\n").trim().to_owned());
        }
        let value = line.trim();
        if value.is_empty() || value.starts_with('#') {
            continue;
        }
        let values = if !line.starts_with([' ', '-']) && value.contains(':') {
            let (key, rest) = value.split_once(':')?;
            field = key.trim();
            if ![
                "paths",
                "routes",
                "read",
                "reconcile",
                "use",
                "checks",
                "protect",
            ]
            .contains(&field)
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
            if value.trim_matches(['\'', '"']).is_empty() {
                return None;
            }
            if field == "checks" {
                if let Some(command) = value.strip_prefix("run:").filter(|_| block) {
                    let command = command.trim();
                    if command.is_empty() {
                        return None;
                    }
                    result[field].as_array_mut()?.push(json!({"run":command}));
                } else {
                    result[field]
                        .as_array_mut()?
                        .push(json!(value.trim_matches(['\'', '"'])));
                }
                continue;
            }
            let value = value.trim_matches(['\'', '"']);
            if value.is_empty() {
                return None;
            }
            if matches!(field, "paths" | "read" | "reconcile" | "protect")
                && (value.starts_with(['/', '~'])
                    || value.contains(['\\', ':'])
                    || value.split('/').any(|p| p == ".."))
            {
                return None;
            }
            if field == "reconcile"
                && (relative(value).is_err() || value.contains(['*', '?', '[', ']']))
            {
                return None;
            }
            if field == "routes" {
                let route = value.strip_suffix("/**").unwrap_or(value);
                crate::route_ids(vec![route.to_owned()], "instruction routes").ok()?;
            }
            result.get_mut(field)?.as_array_mut()?.push(json!(value));
        }
    }
    None
}

fn parsed(bytes: &[u8], include_body: bool) -> Value {
    let mut fields =
        json!({"paths":[],"routes":[],"read":[],"reconcile":[],"use":[],"checks":[],"protect":[]});
    let body = metadata(bytes, &mut fields);
    json!({"metadata":fields,"valid":body.is_some(),"diagnostic":if body.is_some(){""}else{"invalid or unterminated scoped instruction metadata; preserve source and reconcile"},"has_guidance":body.as_ref().is_some_and(|b|!b.is_empty()),"body":if include_body{body.unwrap_or_default()}else{String::new()}})
}

fn confined(root: &Dir, path: &str) -> Result<bool, CoreError> {
    relative(path)?;
    let mut current = PathBuf::new();
    for part in path.split('/') {
        current.push(part);
        match root.symlink_metadata(&current) {
            Ok(meta) => {
                #[cfg(windows)]
                let linked = {
                    use cap_std::fs::MetadataExt;
                    meta.file_attributes() & 0x400 != 0
                };
                #[cfg(not(windows))]
                let linked = meta.is_symlink();
                if linked {
                    return Err(CoreError::new(format!(
                        "instruction source {path}: linked source is not admitted"
                    )));
                }
            }
            Err(e) if e.kind() == std::io::ErrorKind::NotFound => return Ok(false),
            Err(e) => return Err(CoreError::new(format!("instruction source {path}: {e}"))),
        }
    }
    Ok(true)
}

/// Current source syntax is advisory input. Only `view` admits snapshot-owned
/// hard bindings; discovery never invents source authority or follows a link.
pub(crate) fn current_document(
    target: &Path,
    reference: &str,
    include_body: bool,
) -> Result<Value, CoreError> {
    let name = reference
        .strip_prefix(".agentic-workspace/instructions/")
        .filter(|s| !s.contains('/') && s.ends_with(".md"))
        .ok_or_else(|| {
            CoreError::new("current instruction must name a direct scoped Markdown source")
        })?;
    if name == ".md" {
        return Err(CoreError::new("instruction identity is empty"));
    }
    let root = Dir::open_ambient_dir(target, ambient_authority())
        .map_err(|e| CoreError::new(e.to_string()))?;
    if !confined(&root, reference)? {
        return Err(CoreError::new(format!(
            "instruction source {reference}: source missing"
        )));
    }
    let bytes = read(&root, reference)?;
    let mut result = parsed(&bytes, include_body);
    result["source"] = json!({"reference":reference,"revision":hash(&bytes)});
    Ok(result)
}

pub(crate) fn current_sources(target: &Path) -> Result<Vec<Value>, CoreError> {
    const DIRECTORY: &str = ".agentic-workspace/instructions";
    let root = Dir::open_ambient_dir(target, ambient_authority())
        .map_err(|e| CoreError::new(e.to_string()))?;
    if !confined(&root, DIRECTORY)? {
        return Ok(vec![]);
    }
    let mut paths = Vec::new();
    for (index, entry) in root
        .read_dir(DIRECTORY)
        .map_err(|e| CoreError::new(e.to_string()))?
        .enumerate()
    {
        if index >= 256 {
            return Err(CoreError::new(
                "instruction directory exceeds bounded discovery (256 entries)",
            ));
        }
        let entry = entry.map_err(|e| CoreError::new(e.to_string()))?;
        let name = entry
            .file_name()
            .into_string()
            .map_err(|_| CoreError::new("instruction filename must be UTF-8"))?;
        if name.ends_with(".md") {
            paths.push(format!("{DIRECTORY}/{name}"));
            if paths.len() > 64 {
                return Err(CoreError::new("select at most 64 instruction sources"));
            }
        }
    }
    paths.sort();
    paths
        .iter()
        .map(|path| current_document(target, path, false))
        .collect()
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
        let mut row = json!({"source":{"reference":source}, "status":"unadmitted", "checks":[], "reconcile":[], "protect":[], "authority":{"effects":[],"target_patterns":[]}});
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
                let regular = confined(&root, &source).unwrap_or(false)
                    && root
                        .symlink_metadata(&source)
                        .is_ok_and(|m| m.is_file() && !m.is_symlink());
                if regular
                    && observed.revision == hash(&snapshot.stdout)
                    && read(&root, &source)
                        .is_ok_and(|bytes| hash(&bytes) == hash(&snapshot.stdout))
                {
                    let parsed = parsed(&snapshot.stdout, false);
                    if parsed["valid"] == true {
                        let checks = parsed["metadata"]["checks"]
                            .as_array()
                            .expect("parser checks");
                        let protect = parsed["metadata"]["protect"]
                            .as_array()
                            .expect("parser protect");
                        let hard_checks = checks
                            .iter()
                            .any(|c| !c.as_str().is_some_and(|s| s.starts_with("requirement:")))
                            || !parsed["metadata"]["reconcile"]
                                .as_array()
                                .unwrap()
                                .is_empty();
                        let mut effects = vec![];
                        let mut targets = vec![];
                        if hard_checks {
                            effects.push("require");
                            targets.push("claim:complete".to_owned());
                        }
                        if !protect.is_empty() {
                            effects.push("restrict");
                            targets.extend(protect.iter().map(|p| {
                                format!("effect:write:{}", p.as_str().expect("parser path"))
                            }));
                        }
                        row["status"] = json!("current");
                        row["checks"] = json!(checks);
                        row["reconcile"] = parsed["metadata"]["reconcile"].clone();
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

#[cfg(test)]
mod tests {
    use super::*;
    use std::{
        fs,
        time::{SystemTime, UNIX_EPOCH},
    };
    struct Target(PathBuf);
    impl Target {
        fn new() -> Self {
            let path = std::env::temp_dir().join(format!(
                "aw-instruction-source-{}-{}",
                std::process::id(),
                SystemTime::now()
                    .duration_since(UNIX_EPOCH)
                    .unwrap()
                    .as_nanos()
            ));
            fs::create_dir(&path).unwrap();
            Self(path)
        }
        fn write(&self, name: &str, body: &str) {
            let path = self.0.join(".agentic-workspace/instructions").join(name);
            fs::create_dir_all(path.parent().unwrap()).unwrap();
            fs::write(path, body).unwrap();
        }
    }
    impl Drop for Target {
        fn drop(&mut self) {
            fs::remove_dir_all(&self.0).unwrap();
        }
    }
    #[test]
    fn instruction_current_reader_preserves_real_metadata_without_authority() {
        let target = Target::new();
        assert!(current_sources(&target.0).unwrap().is_empty());
        target.write(
            "workspace-operating.md",
            include_str!("../../../.agentic-workspace/instructions/workspace-operating.md"),
        );
        target.write(
            "ownership.md",
            include_str!("../../../.agentic-workspace/instructions/workspace-ownership-audit.md"),
        );
        let rows = current_sources(&target.0).unwrap();
        assert_eq!(rows.len(), 2);
        assert_eq!(
            rows[0]["metadata"]["routes"],
            json!(["workspace/ownership/audit"])
        );
        assert_eq!(
            rows[0]["metadata"]["use"],
            json!(["ownership-ledger-check"])
        );
        assert_eq!(rows[0]["body"], "");
        assert_eq!(rows[0]["has_guidance"], true);
        assert!(
            rows.iter()
                .all(|r| r.get("authority").is_none() && r["valid"] == true)
        );
        let reference = rows[1]["source"]["reference"].as_str().unwrap();
        let full = current_document(&target.0, reference, true).unwrap();
        assert_eq!(full["source"], rows[1]["source"]);
        assert!(
            full["body"]
                .as_str()
                .unwrap()
                .contains("Workspace operating guidance")
        );
        assert_eq!(
            full["metadata"]["protect"],
            json!([".agentic-workspace/local/decision-point-intent/73a213e66cd48a33.json"])
        );
        target.write("workspace-operating.md", "New current guidance");
        assert_ne!(
            current_document(&target.0, reference, false).unwrap()["source"],
            full["source"]
        );
    }
    #[test]
    fn instruction_current_reader_rejects_invalid_paths_routes_and_unknown_metadata() {
        for text in [
            "---\npaths: [src/**]\nunknown: [x]\n---\nBody",
            "---\nread: [../secret]\n---",
            "---\nroutes: [task words]\n---",
            "---\npaths: [src/**]\npaths: [docs/**]\n---",
            "---\nuse: ['']\n---",
        ] {
            let result = parsed(text.as_bytes(), true);
            assert_eq!(result["valid"], false, "{text}");
            assert_eq!(result["body"], "");
        }
        let target = Target::new();
        assert!(current_document(&target.0, "SYSTEM_INTENT.md", true).is_err());
        assert!(
            current_document(
                &target.0,
                ".agentic-workspace/instructions/nested/a.md",
                true
            )
            .is_err()
        );
    }
    #[test]
    fn instruction_current_discovery_is_bounded() {
        let target = Target::new();
        for index in 0..65 {
            target.write(&format!("rule-{index}.md"), "advisory");
        }
        assert!(
            current_sources(&target.0)
                .unwrap_err()
                .to_string()
                .contains("at most 64")
        );
    }
}
