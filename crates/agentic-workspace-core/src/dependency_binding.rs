//! Mechanical dependency identity only. Owners admit the accepted basis and
//! interpret equality; this module cannot grant semantic or effect authority.
use crate::CoreError;
use cap_std::fs::Dir;
use serde::{Deserialize, Serialize};
use serde_json::Value;
use sha2::{Digest, Sha256};

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
    let (status, revision) = match read(root, identity) {
        Ok(Some(bytes)) => match revision(&bytes, scheme) {
            Ok(revision) => (Currentness::Current, Some(revision)),
            Err(_) => (Currentness::Unavailable, None),
        },
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
