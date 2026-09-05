//! Immutable per-effect admission and result files. Custody is supplied by the
//! trusted host, never reconstructed from recognizable on-disk content.
use crate::{CoreError, attempt};
use cap_std::fs::{Dir, OpenOptions};
use serde::{Deserialize, Serialize};
use serde_json::{Value, json};
use sha2::{Digest, Sha256};
use std::fs;
use std::io::{Read, Write};
use std::path::PathBuf;

const DIRECTORY: &str = ".agentic-workspace/local/effects";

#[derive(Clone, Deserialize, Serialize)]
#[serde(deny_unknown_fields)]
pub(crate) struct Evidence {
    pub(crate) target: String,
    pub(crate) path: String,
    pub(crate) owner: String,
    pub(crate) revision: String,
}

#[derive(Clone, Deserialize, Serialize)]
#[serde(deny_unknown_fields)]
struct Custody {
    attempt: Evidence,
    committed: Option<Evidence>,
}

fn error(e: impl std::fmt::Display) -> CoreError {
    CoreError::new(e.to_string())
}
fn hash(bytes: &[u8]) -> String {
    format!("sha256:{:x}", Sha256::digest(bytes))
}
struct Root {
    path: PathBuf,
    dir: Dir,
}
fn root(target: &str) -> Result<Root, CoreError> {
    let path = fs::canonicalize(target).map_err(error)?;
    let dir = Dir::open_ambient_dir(&path, cap_std::ambient_authority()).map_err(error)?;
    Ok(Root { path, dir })
}
fn bound_root(target: &str, invocation: &Value) -> Result<Root, CoreError> {
    let requested = invocation["arguments"]["target"]
        .as_str()
        .ok_or_else(|| error("stored effect requires an owner-derived target argument"))?;
    let root = root(target)?;
    if fs::canonicalize(requested).map_err(error)? != root.path {
        return Err(error(
            "storage target differs from the exact invocation target",
        ));
    }
    Ok(root)
}
fn checked(root: &Root, relative: &str, create_parents: bool) -> Result<PathBuf, CoreError> {
    let name = relative
        .strip_prefix(&format!("{DIRECTORY}/"))
        .ok_or_else(|| error("invalid effect evidence path"))?;
    let (key, suffix) = name
        .split_once('.')
        .ok_or_else(|| error("invalid effect evidence name"))?;
    if key.len() != 64
        || !key.bytes().all(|b| b.is_ascii_hexdigit())
        || !matches!(suffix, "attempt.json" | "result.json")
    {
        return Err(error("invalid effect evidence name"));
    }
    confined(root, relative, create_parents)
}
fn confined(root: &Root, relative: &str, create_parents: bool) -> Result<PathBuf, CoreError> {
    use std::path::Component;
    let path = std::path::Path::new(relative);
    if relative.is_empty()
        || relative.contains('\\')
        || path
            .components()
            .any(|part| !matches!(part, Component::Normal(_)))
    {
        return Err(error("evidence path must be relative and confined"));
    }
    let name = relative.rsplit('/').next().unwrap_or("");
    let mut current = PathBuf::new();
    for part in relative.split('/') {
        current.push(part);
        match root.dir.symlink_metadata(&current) {
            Ok(metadata) => {
                #[cfg(windows)]
                let link = {
                    use cap_std::fs::MetadataExt;
                    metadata.file_attributes() & 0x400 != 0
                };
                #[cfg(not(windows))]
                let link = metadata.file_type().is_symlink();
                if link {
                    return Err(error("effect evidence cannot traverse links"));
                }
                if part == name && !metadata.is_file() {
                    return Err(error("effect evidence must be a regular file"));
                }
            }
            Err(e) if e.kind() == std::io::ErrorKind::NotFound => {
                if create_parents && part != name {
                    match root.dir.create_dir(&current) {
                        Ok(()) => (),
                        Err(e) if e.kind() == std::io::ErrorKind::AlreadyExists => (),
                        Err(e) => return Err(error(e)),
                    }
                    // All subsequent operations remain relative to the opened
                    // directory capability, including during namespace races.
                    root.dir.open_dir(&current).map_err(error)?;
                }
            }
            Err(e) => return Err(error(e)),
        }
    }
    Ok(current)
}

/// The trusted source owner supplies this exact evidence; a caller-computed
/// checksum or recognizable path is not admission of source authority.
pub(crate) fn read_source(target: &str, reference: &Evidence) -> Result<Value, CoreError> {
    let root = root(target)?;
    if root.path != fs::canonicalize(&reference.target).map_err(error)? {
        return Err(error("source custody belongs to a different target"));
    }
    let bytes = root
        .dir
        .read(confined(&root, &reference.path, false)?)
        .map_err(error)?;
    if hash(&bytes) != reference.revision {
        return Err(error(
            "former source changed; Planning reconciliation must reopen",
        ));
    }
    serde_json::from_slice(&bytes).map_err(error)
}
fn read(root: &Root, reference: &Evidence) -> Result<Value, CoreError> {
    if root.path.to_string_lossy() != reference.target {
        return Err(error("custody belongs to a different target"));
    }
    let mut bytes = Vec::new();
    root.dir
        .open(checked(root, &reference.path, false)?)
        .map_err(error)?
        .read_to_end(&mut bytes)
        .map_err(error)?;
    if hash(&bytes) != reference.revision {
        return Err(error("effect evidence differs from exact custody"));
    }
    let record: Value = serde_json::from_slice(&bytes).map_err(error)?;
    if record["invocation"]["source_owner"].as_str() != Some(&reference.owner) {
        return Err(error("effect evidence has a different owner"));
    }
    Ok(record)
}
fn create(root: &Root, relative: String, record: &Value) -> Result<Evidence, CoreError> {
    let path = checked(root, &relative, true)?;
    let bytes = serde_json::to_vec(record).map_err(error)?;
    let mut file = root
        .dir
        .open_with(path, OpenOptions::new().write(true).create_new(true))
        .map_err(|e| {
            if e.kind() == std::io::ErrorKind::AlreadyExists {
                error("existing effect evidence requires exact custody; preserved")
            } else {
                error(e)
            }
        })?;
    file.write_all(&bytes).map_err(error)?;
    file.sync_all().map_err(error)?;
    // Directory capabilities may use non-syncable handles (O_PATH on Linux).
    // The store promises process-interruption safety, not directory-entry
    // persistence across power loss; do not fsync this capability handle.
    Ok(Evidence {
        target: root.path.to_string_lossy().into_owned(),
        path: relative,
        owner: record["invocation"]["source_owner"]
            .as_str()
            .ok_or_else(|| error("attempt owner missing"))?
            .to_owned(),
        revision: hash(&bytes),
    })
}
fn names(invocation: &Value) -> Result<(String, String), CoreError> {
    let key = invocation["idempotency_key"]
        .as_str()
        .filter(|s| !s.is_empty())
        .ok_or_else(|| error("logical effect identity missing"))?;
    let digest = hash(key.as_bytes());
    Ok((
        format!("{DIRECTORY}/{}.attempt.json", &digest[7..]),
        format!("{DIRECTORY}/{}.result.json", &digest[7..]),
    ))
}

/// New evidence is atomically acquired only while absent. The caller may start
/// the effect only after receiving execute and retaining the returned custody.
pub fn admit(value: Value) -> Result<Value, CoreError> {
    #[derive(Deserialize)]
    #[serde(deny_unknown_fields)]
    struct Input {
        target: String,
        decision: Value,
        invocation: Value,
        custody: Option<Custody>,
    }
    let input: Input = serde_json::from_value(value).map_err(error)?;
    let (attempt_path, result_path) = names(&input.invocation)?;
    let root = bound_root(&input.target, &input.invocation)?;
    let (record, custody) = if let Some(custody) = input.custody {
        if custody.attempt.path != attempt_path {
            return Err(error("custody belongs to a different effect"));
        }
        let admitted = read(&root, &custody.attempt)?;
        let record = if let Some(committed) = &custody.committed {
            if committed.path != result_path {
                return Err(error("committed custody belongs to a different effect"));
            }
            let record = read(&root, committed)?;
            if record["invocation"] != admitted["invocation"]
                || record["attempt_id"] != admitted["attempt_id"]
            {
                return Err(error("commit belongs to a different attempt"));
            }
            record
        } else {
            admitted
        };
        (Some(record), Some(custody))
    } else {
        (None, None)
    };
    let mut admission = attempt::admit(
        json!({"decision": input.decision, "invocation": input.invocation, "record": record}),
    )?;
    let custody = if let Some(custody) = custody {
        custody
    } else {
        if root
            .dir
            .symlink_metadata(checked(&root, &result_path, false)?)
            .is_ok()
        {
            return Err(error("unowned result evidence exists; preserved"));
        }
        Custody {
            attempt: create(&root, attempt_path, &admission["record"])?,
            committed: None,
        }
    };
    admission["custody"] = serde_json::to_value(custody).map_err(error)?;
    Ok(admission)
}

/// Completion creates a separate immutable result; it never truncates or
/// replaces the admission file, so an interrupted write cannot erase custody.
pub fn commit(value: Value) -> Result<Value, CoreError> {
    #[derive(Deserialize)]
    #[serde(deny_unknown_fields)]
    struct Input {
        target: String,
        custody: Custody,
        outcome: Value,
    }
    let input: Input = serde_json::from_value(value).map_err(error)?;
    let root = root(&input.target)?;
    let admitted = read(&root, &input.custody.attempt)?;
    bound_root(&input.target, &admitted["invocation"])?;
    let (attempt_path, result_path) = names(&admitted["invocation"])?;
    if input.custody.attempt.path != attempt_path {
        return Err(error("custody belongs to a different effect"));
    }
    let record = attempt::commit(json!({"record": admitted, "outcome": input.outcome}))?;
    let committed = if let Some(reference) = input.custody.committed {
        if reference.path != result_path || read(&root, &reference)? != record {
            return Err(error("committed outcome differs"));
        }
        reference
    } else {
        create(&root, result_path, &record)?
    };
    Ok(
        json!({"record": record, "custody": Custody { attempt: input.custody.attempt, committed: Some(committed) }}),
    )
}
