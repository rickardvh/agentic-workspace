//! Confined bounded source enumeration shared by native disposition owners.
//! Directory capabilities are opened once per walk, not once per descendant.
use crate::CoreError;
use cap_std::fs::Dir;
use std::{collections::BTreeMap, io::Read};
fn err(e: impl ToString) -> CoreError {
    CoreError::new(e.to_string())
}

pub(crate) fn files(
    root: &Dir,
    path: &str,
    output: &mut BTreeMap<String, Vec<u8>>,
) -> Result<(), CoreError> {
    let mut prefix = String::new();
    for part in path.split('/') {
        if !prefix.is_empty() {
            prefix.push('/');
        }
        prefix.push_str(part);
        match root.symlink_metadata(&prefix) {
            Ok(m) if crate::native_routes::linked(&m) => {
                return Err(err("Retention preserves linked sources"));
            }
            Err(e) if e.kind() == std::io::ErrorKind::NotFound => return Ok(()),
            Err(e) => return Err(err(e)),
            _ => {}
        }
    }
    let directory = root.open_dir(path).map_err(err)?;
    let mut total = output.values().map(Vec::len).sum::<usize>();
    walk(&directory, path, output, &mut total)
}
fn walk(
    directory: &Dir,
    path: &str,
    output: &mut BTreeMap<String, Vec<u8>>,
    total: &mut usize,
) -> Result<(), CoreError> {
    if path.split('/').count() > 32 {
        return Err(err("Retention depth bound exceeded; preserved"));
    }
    for entry in directory.entries().map_err(err)? {
        let entry = entry.map_err(err)?;
        let name = entry
            .file_name()
            .into_string()
            .map_err(|_| err("Non-UTF8 retention source preserved"))?;
        if matches!(name.as_str(), "__pycache__" | ".pytest_cache") {
            continue;
        }
        let child = format!("{path}/{name}");
        let metadata = directory.symlink_metadata(&name).map_err(err)?;
        if crate::native_routes::linked(&metadata) {
            return Err(err("Retention preserves linked sources"));
        }
        if metadata.is_dir() {
            let nested = directory.open_dir(&name).map_err(err)?;
            walk(&nested, &child, output, total)?;
        } else if metadata.is_file() {
            if metadata.len() == 0 && child.ends_with(".lock") {
                continue;
            }
            if output.len() >= 4096
                || *total as u64 + metadata.len() > 64 * 1024 * 1024
                || metadata.len() > crate::decision_source::MAX_SOURCE_BYTES as u64
            {
                return Err(err("Retention source bound exceeded; preserved"));
            }
            let file = directory.open(&name).map_err(err)?;
            if !file.metadata().map_err(err)?.is_file() {
                return Err(err("Retention preserves non-file sources"));
            }
            let mut bytes = Vec::new();
            file.take(crate::decision_source::MAX_SOURCE_BYTES as u64 + 1)
                .read_to_end(&mut bytes)
                .map_err(err)?;
            if bytes.len() > crate::decision_source::MAX_SOURCE_BYTES
                || *total + bytes.len() > 64 * 1024 * 1024
            {
                return Err(err("Retention source grew beyond bound; preserved"));
            }
            *total += bytes.len();
            output.insert(child, bytes);
        } else {
            return Err(err("Retention preserves non-file sources"));
        }
    }
    Ok(())
}
