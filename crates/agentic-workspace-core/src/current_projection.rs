//! Bounded owner-local operational projections. Referenced custody remains authoritative.
use crate::{CoreError, native_planning};
use cap_std::fs::{Dir, OpenOptions};
use serde_json::Value;
use std::{io::Write, path::Path};

pub(crate) fn read(root: &Dir, path: &str) -> Result<Option<Value>, CoreError> {
    native_planning::read(root, path)?
        .map(|bytes| serde_json::from_slice(&bytes).map_err(|e| CoreError::new(e.to_string())))
        .transpose()
}

// Call only under the owning effect lock. An interrupted temporary is reusable
// only for the identical projection; conflicting material remains explicit.
pub(crate) fn write(root: &Dir, path: &str, value: &Value) -> Result<(), CoreError> {
    let err = |e: std::io::Error| CoreError::new(e.to_string());
    let bytes = serde_json::to_vec(value).map_err(|e| CoreError::new(e.to_string()))?;
    if bytes.len() > crate::decision_source::MAX_SOURCE_BYTES {
        return Err(CoreError::new(
            "current owner projection exceeds bounded size",
        ));
    }
    let temporary = format!("{path}.tmp");
    native_planning::read(root, path)?;
    let existing = native_planning::read(root, &temporary)?;
    root.create_dir_all(Path::new(path).parent().unwrap())
        .map_err(err)?;
    if let Some(existing) = existing {
        if existing != bytes {
            return Err(CoreError::new(
                "conflicting current projection temporary preserved",
            ));
        }
    } else {
        let mut file = root
            .open_with(&temporary, OpenOptions::new().write(true).create_new(true))
            .map_err(err)?;
        file.write_all(&bytes).map_err(err)?;
        file.sync_all().map_err(err)?;
    }
    root.rename(&temporary, root, path).map_err(err)
}
