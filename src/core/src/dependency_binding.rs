//! Mechanical dependency identity only. Owners admit the accepted basis and
//! interpret equality; this module cannot grant semantic or effect authority.
use crate::CoreError;
use cap_std::fs::Dir;
use serde::{Deserialize, Serialize};
use serde_json::Value;
use sha2::{Digest, Sha256};
use std::io::Read;

// Source identity has a separate budget from small configuration/inline readers.
// Stream at most 32 MiB per regular declared source; never deliver these bytes.
pub(crate) const MAX_OBSERVATION_BYTES: u64 = 32 * 1024 * 1024;

pub(crate) fn observe_raw(
    root: &Dir,
    reference: &str,
    budget: u64,
) -> Result<Option<(String, u64)>, CoreError> {
    observe_raw_with_limit(root, reference, MAX_OBSERVATION_BYTES.min(budget))
}

// Proof subjects retain their existing streaming size policy; small-source
// owners use observe_raw's separate per-file/resolution budgets above.
pub(crate) fn observe_raw_with_limit(
    root: &Dir,
    reference: &str,
    limit: u64,
) -> Result<Option<(String, u64)>, CoreError> {
    let over_budget = || {
        CoreError::new(if limit < MAX_OBSERVATION_BYTES {
            "source-observation-exceeds-128-mib-resolution-bound"
        } else {
            "source-observation-exceeds-32-mib-bound"
        })
    };
    crate::decision_source::relative(reference)?;
    let check = || -> Result<Option<cap_std::fs::Metadata>, CoreError> {
        let mut prefix = std::path::PathBuf::new();
        let mut last = None;
        let mut parts = reference.split('/').peekable();
        while let Some(part) = parts.next() {
            prefix.push(part);
            let metadata = match root.symlink_metadata(&prefix) {
                Ok(metadata) => metadata,
                Err(error) if error.kind() == std::io::ErrorKind::NotFound => return Ok(None),
                Err(_) => return Err(CoreError::new("source-observation-unreadable")),
            };
            #[cfg(windows)]
            let linked = {
                use cap_std::fs::MetadataExt;
                metadata.file_attributes() & 0x400 != 0
            };
            #[cfg(not(windows))]
            let linked = metadata.is_symlink();
            if linked {
                return Err(CoreError::new("source-observation-linked"));
            }
            if parts.peek().is_some() && !metadata.is_dir() {
                return Err(CoreError::new("source-observation-not-directory"));
            }
            last = Some(metadata);
        }
        Ok(last)
    };
    let Some(before) = check()? else {
        if check()?.is_some() {
            return Err(CoreError::new("source-observation-changed-during-read"));
        }
        return Ok(None);
    };
    if !before.is_file() {
        return Err(CoreError::new("source-observation-not-regular"));
    }
    if before.len() > limit {
        return Err(over_budget());
    }
    let mut file = root
        .open(reference)
        .map_err(|_| CoreError::new("source-observation-unreadable"))?;
    let same = |a: &cap_std::fs::Metadata, b: &cap_std::fs::Metadata| {
        let same = a.is_file()
            && b.is_file()
            && a.len() == b.len()
            && a.modified().ok() == b.modified().ok()
            && a.created().ok() == b.created().ok();
        #[cfg(unix)]
        {
            use cap_std::fs::MetadataExt;
            same && a.dev() == b.dev() && a.ino() == b.ino()
        }
        #[cfg(not(unix))]
        {
            same
        }
    };
    let opened = file
        .metadata()
        .map_err(|_| CoreError::new("source-observation-unreadable"))?;
    if !same(&before, &opened) {
        return Err(CoreError::new("source-observation-changed-during-read"));
    }
    let mut hash = Sha256::new();
    let mut size = 0;
    let mut buffer = [0; 64 * 1024];
    while size <= limit {
        let remaining = (limit - size + 1).min(buffer.len() as u64) as usize;
        let count = file
            .read(&mut buffer[..remaining])
            .map_err(|_| CoreError::new("source-observation-unreadable"))?;
        if count == 0 {
            break;
        }
        size += count as u64;
        hash.update(&buffer[..count]);
    }
    if size > limit {
        return Err(over_budget());
    }
    let after = file
        .metadata()
        .map_err(|_| CoreError::new("source-observation-unreadable"))?;
    if size != before.len()
        || !same(&before, &after)
        || check()?.is_none_or(|current| !same(&before, &current))
    {
        return Err(CoreError::new("source-observation-changed-during-read"));
    }
    Ok(Some((format!("sha256:{:x}", hash.finalize()), size)))
}

#[derive(Clone, Copy, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "kebab-case")]
pub(crate) enum Scheme {
    RawBytes,
    UniversalNewlineUtf8,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub(crate) struct Observation {
    pub identity: String,
    pub scheme: Scheme,
    pub revision: Option<String>,
    pub status: Currentness,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "kebab-case")]
pub(crate) enum Currentness {
    Current,
    Changed,
    Missing,
    Unavailable,
    Unassessed,
}

pub(crate) fn revision(bytes: &[u8], scheme: Scheme) -> Result<String, CoreError> {
    match scheme {
        Scheme::RawBytes => Ok(format!("sha256:{:x}", Sha256::digest(bytes))),
        Scheme::UniversalNewlineUtf8 => {
            let text = std::str::from_utf8(bytes).map_err(|e| CoreError::new(e.to_string()))?;
            Ok(crate::decision_source::hash(
                text.replace("\r\n", "\n").replace('\r', "\n").as_bytes(),
            ))
        }
    }
}

pub(crate) fn read(root: &Dir, reference: &str) -> Result<Option<Vec<u8>>, CoreError> {
    crate::native_verification::read(root, reference).map_err(CoreError::new)
}

pub(crate) fn observe(root: &Dir, identity: &str, scheme: Scheme) -> Observation {
    let observation = match scheme {
        Scheme::RawBytes => observe_raw(root, identity, MAX_OBSERVATION_BYTES)
            .map(|value| value.map(|(revision, _)| revision)),
        Scheme::UniversalNewlineUtf8 => read(root, identity)
            .and_then(|value| value.map(|bytes| revision(&bytes, scheme)).transpose()),
    };
    let (status, revision) = match observation {
        Ok(Some(revision)) => (Currentness::Current, Some(revision)),
        Ok(None) => (Currentness::Missing, None),
        Err(_) => (Currentness::Unavailable, None),
    };
    Observation {
        identity: identity.into(),
        scheme,
        revision,
        status,
    }
}

/// A conclusion may be an interpretation, a proof claim or a subject group.
/// Identity and declaration ordering are supplied by its owner, never inferred
/// from paths or normalised away. No second persistent representation is needed.
pub(crate) struct Basis<'a> {
    pub conclusion: &'a Value,
    pub dependencies: &'a [Observation],
}

pub(crate) struct Comparison {
    pub status: Currentness,
    pub changed: Vec<String>,
    pub membership_changed: bool,
}

pub(crate) fn compare(current: Basis<'_>, accepted: Option<Basis<'_>>) -> Comparison {
    let Some(accepted) = accepted else {
        return Comparison {
            status: Currentness::Unassessed,
            changed: current
                .dependencies
                .iter()
                .map(|o| o.identity.clone())
                .collect(),
            membership_changed: true,
        };
    };
    let mut changed = Vec::new();
    let mut status = Currentness::Current;
    for observation in current.dependencies {
        let matching: Vec<_> = accepted
            .dependencies
            .iter()
            .filter(|o| o.identity == observation.identity)
            .collect();
        if observation.status != Currentness::Current
            || matching.len() != 1
            || matching[0] != observation
        {
            changed.push(observation.identity.clone());
            status = match observation.status {
                Currentness::Missing | Currentness::Unavailable => observation.status,
                _ if status == Currentness::Current => Currentness::Changed,
                _ => status,
            };
        }
    }
    for observation in accepted.dependencies {
        if !current
            .dependencies
            .iter()
            .any(|o| o.identity == observation.identity)
        {
            changed.push(observation.identity.clone());
        }
    }
    let membership_changed = current.dependencies.len() != accepted.dependencies.len()
        || current
            .dependencies
            .iter()
            .map(|o| &o.identity)
            .collect::<Vec<_>>()
            != accepted
                .dependencies
                .iter()
                .map(|o| &o.identity)
                .collect::<Vec<_>>();
    if status == Currentness::Current
        && (membership_changed || !changed.is_empty() || current.conclusion != accepted.conclusion)
    {
        status = Currentness::Changed;
    }
    Comparison {
        status,
        changed,
        membership_changed,
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn streamed_identity_is_exact_confined_and_separate_from_content_limits() {
        let temp = std::env::temp_dir().join(format!(
            "aw-streamed-source-{}-{}",
            std::process::id(),
            std::time::SystemTime::now()
                .duration_since(std::time::UNIX_EPOCH)
                .unwrap()
                .as_nanos()
        ));
        std::fs::create_dir(&temp).unwrap();
        let root = Dir::open_ambient_dir(&temp, cap_std::ambient_authority()).unwrap();
        let content = vec![b'x'; 1_048_577];
        root.write("contract", &content).unwrap();
        assert!(
            read(&root, "contract").is_err(),
            "inline/configuration limits stay unchanged"
        );
        assert_eq!(
            observe_raw(&root, "contract", MAX_OBSERVATION_BYTES).unwrap(),
            Some((
                revision(&content, Scheme::RawBytes).unwrap(),
                content.len() as u64
            ))
        );
        assert_eq!(
            observe(&root, "contract", Scheme::RawBytes).status,
            Currentness::Current
        );
        assert!(
            observe_raw(&root, "contract", 1024)
                .unwrap_err()
                .to_string()
                .contains("resolution-bound")
        );
        root.create("too-large")
            .unwrap()
            .set_len(MAX_OBSERVATION_BYTES + 1)
            .unwrap();
        assert!(
            observe_raw(&root, "too-large", MAX_OBSERVATION_BYTES)
                .unwrap_err()
                .to_string()
                .contains("32-mib")
        );
        assert_eq!(
            observe_raw(&root, "missing", MAX_OBSERVATION_BYTES).unwrap(),
            None
        );
        root.create_dir("directory").unwrap();
        assert!(observe_raw(&root, "directory", MAX_OBSERVATION_BYTES).is_err());
        assert!(observe_raw(&root, "../escape", MAX_OBSERVATION_BYTES).is_err());
        #[cfg(unix)]
        {
            std::os::unix::fs::symlink("contract", temp.join("linked")).unwrap();
            assert!(
                observe_raw(&root, "linked", MAX_OBSERVATION_BYTES)
                    .unwrap_err()
                    .to_string()
                    .contains("linked")
            );
        }
        drop(root);
        std::fs::remove_dir_all(temp).unwrap();
    }

    #[test]
    fn raw_revision_preserves_crlf_and_non_utf8_bytes() {
        for bytes in [b"a\r\nb\r\n".as_slice(), &[0xff, 0xfe]] {
            assert_eq!(
                revision(bytes, Scheme::RawBytes).unwrap(),
                format!("sha256:{:x}", Sha256::digest(bytes))
            );
        }
        assert_ne!(
            revision(b"a\r\nb\r\n", Scheme::RawBytes).unwrap(),
            revision(b"a\nb\n", Scheme::RawBytes).unwrap()
        );
    }

    #[test]
    fn exact_basis_preserves_scheme_membership_and_unknowns() {
        let observation = Observation {
            identity: "input".into(),
            scheme: Scheme::RawBytes,
            revision: Some(revision(b"a\r\nb\r", Scheme::RawBytes).unwrap()),
            status: Currentness::Current,
        };
        let original = vec![observation];
        fn basis(deps: &[Observation]) -> Basis<'_> {
            Basis {
                conclusion: &Value::Null,
                dependencies: deps,
            }
        }
        assert_eq!(
            compare(basis(&original), None).status,
            Currentness::Unassessed
        );
        assert_eq!(
            compare(basis(&original), Some(basis(&original))).status,
            Currentness::Current
        );
        let mut changed = original.clone();
        changed[0].scheme = Scheme::UniversalNewlineUtf8;
        assert_eq!(
            compare(basis(&changed), Some(basis(&original))).status,
            Currentness::Changed
        );
        for status in [Currentness::Missing, Currentness::Unavailable] {
            changed[0].status = status;
            changed[0].revision = None;
            assert_eq!(
                compare(basis(&changed), Some(basis(&changed))).status,
                status
            );
        }
        let duplicate = vec![original[0].clone(), original[0].clone()];
        assert_eq!(
            compare(basis(&original), Some(basis(&duplicate))).changed,
            ["input"]
        );
        assert!(compare(basis(&[]), Some(basis(&original))).membership_changed);
        assert_eq!(
            revision(b"a\r\nb\r", Scheme::UniversalNewlineUtf8).unwrap(),
            revision(b"a\nb\n", Scheme::RawBytes).unwrap()
        );
        assert_ne!(
            revision(b"a\r\nb\r", Scheme::RawBytes).unwrap(),
            revision(b"a\nb\n", Scheme::RawBytes).unwrap()
        );
        assert!(revision(&[255], Scheme::UniversalNewlineUtf8).is_err());
    }
}
