//! Current owner declarations, not historical provenance, define enclave hygiene.
use crate::{CoreError, digest};
use cap_std::fs::Dir;
use serde_json::{Value, json};
use std::{collections::BTreeMap, io::Read};

include!(concat!(env!("OUT_DIR"), "/module_support.rs"));

fn err(e: impl ToString) -> CoreError {
    CoreError::new(e.to_string())
}

pub(crate) fn declarations(contract: &Value) -> Result<Vec<Value>, CoreError> {
    let mut owners = vec![contract["enclave"].clone()];
    owners.extend([
        crate::native_planning::enclave(),
        crate::native_memory::enclave(),
        crate::native_verification::enclave(),
    ]);
    let mut rows = Vec::new();
    for owner in owners {
        for row in owner["declarations"]
            .as_array()
            .ok_or_else(|| err("missing enclave declarations"))?
        {
            let mut row = row.clone();
            row["owner"] = owner["owner"].clone();
            rows.push(row);
        }
    }
    for path in crate::native_payload::paths() {
        rows.push(json!({"path":path,"scope":"exact","owner":"workspace","class":"managed-support","lifetime":"current-version"}));
    }
    validate(&rows)?;
    Ok(rows)
}

fn covers(row: &Value, path: &str) -> bool {
    let reference = row["path"].as_str().unwrap();
    path == reference || (row["scope"] == "subtree" && path.starts_with(&format!("{reference}/")))
}

fn validate(rows: &[Value]) -> Result<(), CoreError> {
    for (index, row) in rows.iter().enumerate() {
        let path = row["path"]
            .as_str()
            .ok_or_else(|| err("enclave path missing"))?;
        if !path.starts_with(".agentic-workspace/")
            || path.contains(['\\', ':'])
            || path.split('/').any(|p| matches!(p, "" | "." | ".."))
            || !["exact", "subtree"].contains(&row["scope"].as_str().unwrap_or(""))
            || ![
                "managed-support",
                "mutable-state",
                "customization",
                "local-only",
            ]
            .contains(&row["class"].as_str().unwrap_or(""))
            || row["owner"].as_str().unwrap_or("").is_empty()
            || row["lifetime"].as_str().unwrap_or("").is_empty()
        {
            return Err(err(
                "invalid current enclave owner/class/lifetime declaration",
            ));
        }
        for other in &rows[..index] {
            if covers(other, path) || covers(row, other["path"].as_str().unwrap()) {
                return Err(err(format!("ambiguous enclave ownership: {path}")));
            }
        }
    }
    Ok(())
}

fn linked(metadata: &cap_std::fs::Metadata) -> bool {
    #[cfg(windows)]
    {
        use cap_std::fs::MetadataExt;
        metadata.file_attributes() & 0x400 != 0
    }
    #[cfg(not(windows))]
    {
        metadata.is_symlink()
    }
}

// Fingerprint opaque regular bytes and link identity without parsing or following.
pub(crate) fn identity(root: &Dir, path: &str) -> Result<Value, CoreError> {
    let metadata = match root.symlink_metadata(path) {
        Ok(m) => m,
        Err(e) if e.kind() == std::io::ErrorKind::NotFound => return Ok(Value::Null),
        Err(e) => return Err(err(e)),
    };
    if linked(&metadata) {
        #[cfg(windows)]
        let directory = {
            use cap_std::fs::MetadataExt;
            metadata.file_attributes() & 0x10 != 0
        };
        #[cfg(not(windows))]
        let directory = false;
        return Ok(
            json!({"kind":"link","target":root.read_link_contents(path).map_err(err)?.to_str().ok_or_else(|| err("non-UTF8 enclave link"))?,"directory":directory}),
        );
    }
    if metadata.is_dir() {
        return Ok(json!({"kind":"directory"}));
    }
    if !metadata.is_file() || metadata.len() > 1024 * 1024 {
        return Err(err(format!(
            "{path}: enclave inventory requires a bounded regular file or link"
        )));
    }
    let mut bytes = Vec::new();
    root.open(path)
        .map_err(err)?
        .take(1024 * 1024 + 1)
        .read_to_end(&mut bytes)
        .map_err(err)?;
    if bytes.len() > 1024 * 1024 {
        return Err(err("enclave file exceeded inventory bound"));
    }
    Ok(json!({"kind":"file","revision":crate::native_intent::hash(&bytes)}))
}

pub(crate) fn inventory(root: &Dir, rows: &[Value]) -> Result<Value, CoreError> {
    validate(rows)?;
    let mut entries = BTreeMap::new();
    entries.insert(".agentic-workspace".into(), json!({"owner":"workspace","class":"managed-support","lifetime":"current-version","scope":"container"}));
    // Opaque declarations do not change when an effect creates local custody.
    for row in rows.iter().filter(|r| r["scope"] == "subtree") {
        entries.insert(row["path"].as_str().unwrap().into(), row.clone());
    }
    let mut removals = BTreeMap::new();
    let mut count = 0;
    fn walk(
        root: &Dir,
        path: &str,
        rows: &[Value],
        entries: &mut BTreeMap<String, Value>,
        removals: &mut BTreeMap<String, Value>,
        count: &mut usize,
        depth: usize,
    ) -> Result<(), CoreError> {
        *count += 1;
        if *count > 8192 || depth > 32 {
            return Err(err("enclave inventory exceeds bounded path/depth limit"));
        }
        let observed = identity(root, path)?;
        if observed.is_null() {
            return Ok(());
        }
        let matched = rows.iter().find(|r| covers(r, path));
        let directory = observed["kind"] == "directory";
        let container = directory
            && rows
                .iter()
                .any(|r| r["path"].as_str().unwrap().starts_with(&format!("{path}/")));
        if let Some(row) = matched {
            entries.insert(path.into(), row.clone());
            // Explicit owner subtrees are opaque. Their descendants share this
            // declaration, avoiding an unbounded scan of durable/local records.
            if row["scope"] == "subtree" {
                return Ok(());
            }
            if directory {
                return Err(err(format!(
                    "{path}: exact file declaration names a directory"
                )));
            }
        } else if container {
            entries.insert(path.into(), json!({"owner":"workspace","class":"managed-support","lifetime":"current-version","scope":"container"}));
        } else {
            entries.insert(path.into(), json!({"class":"unknown-residue"}));
            removals.insert(path.into(), observed.clone());
        }
        if directory {
            let mut children = Vec::new();
            for entry in root.read_dir(path).map_err(err)? {
                if children.len() >= 8192 {
                    return Err(err("enclave directory exceeds inventory bound"));
                }
                let entry = entry.map_err(err)?;
                children.push(
                    entry
                        .file_name()
                        .into_string()
                        .map_err(|_| err("non-UTF8 enclave path"))?,
                );
            }
            children.sort();
            for name in children {
                walk(
                    root,
                    &format!("{path}/{name}"),
                    rows,
                    entries,
                    removals,
                    count,
                    depth + 1,
                )?;
            }
        }
        Ok(())
    }
    let enclave = root.symlink_metadata(".agentic-workspace");
    match enclave {
        Ok(m) if linked(&m) || !m.is_dir() => {
            return Err(err("enclave root must be an unlinked directory"));
        }
        Err(e) if e.kind() == std::io::ErrorKind::NotFound => {}
        Err(e) => return Err(err(e)),
        Ok(_) => walk(
            root,
            ".agentic-workspace",
            rows,
            &mut entries,
            &mut removals,
            &mut count,
            0,
        )?,
    }
    Ok(
        json!({"status":if removals.is_empty(){"current"}else{"dirty"},"declaration_revision":digest(&json!(rows))?,"entries":entries,"removals":removals}),
    )
}

pub(crate) fn remove(
    root: &Dir,
    path: &str,
    expected: &Value,
    recovery: bool,
) -> Result<(), CoreError> {
    // Check every ancestor before inspecting the exact leaf. Never traverse a
    // link/junction even when its target would still be inside the repository.
    let mut ancestor = String::new();
    let parts: Vec<_> = path.split('/').collect();
    if parts.first() != Some(&".agentic-workspace")
        || parts.len() < 2
        || parts.iter().any(|p| matches!(*p, "" | "." | ".."))
    {
        return Err(err("invalid enclave removal path"));
    }
    for part in &parts[..parts.len() - 1] {
        if !ancestor.is_empty() {
            ancestor.push('/');
        }
        ancestor.push_str(part);
        match root.symlink_metadata(&ancestor) {
            Ok(m) if !linked(&m) && m.is_dir() => {}
            Err(e) if recovery && e.kind() == std::io::ErrorKind::NotFound => return Ok(()),
            _ => return Err(err("enclave removal ancestor changed")),
        }
    }
    let current = identity(root, path)?;
    if recovery && current.is_null() {
        return Ok(());
    }
    if current != *expected {
        return Err(err(format!(
            "{path}: enclave residue changed before removal"
        )));
    }
    if current["kind"] == "directory" || current["directory"] == true {
        root.remove_dir(path).map_err(err)?;
    } else {
        root.remove_file(path).map_err(err)?;
    }
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn current_declarations_reject_ambiguous_or_unconfined_ownership() {
        let row = json!({"path":".agentic-workspace/custom","scope":"subtree","owner":"repo","class":"customization","lifetime":"repository"});
        assert!(validate(&[row.clone()]).is_ok());
        let mut child = row.clone();
        child["path"] = json!(".agentic-workspace/custom/child");
        assert!(validate(&[row.clone(), child]).is_err());
        let mut outside = row;
        outside["path"] = json!("outside");
        assert!(validate(&[outside]).is_err());
    }
}
