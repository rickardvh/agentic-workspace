//! Read-only payload target admission from the artifact's own shipped bytes.
//! Provenance labels alone confer neither freshness nor mutation custody.
use crate::{CoreError, digest};
use cap_std::{ambient_authority, fs::Dir};
use serde_json::{Value, json};
use sha2::{Digest, Sha256};
use std::path::Path;

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub(crate) enum Materialization {
    PackageVerbatim,
    HostComposed,
    TargetDerived,
}

include!(concat!(env!("OUT_DIR"), "/payload.rs"));
const PROVENANCE: &str = ".agentic-workspace/payload-provenance.json";
const CAPABILITIES: &[&str] = &["installed-state-sync-v2"];

/// The artifact, not caller-supplied filenames or provenance labels, defines
/// which package files Configuration can refresh. Domain/local state is absent.
pub(crate) fn paths() -> Vec<&'static str> {
    PAYLOAD
        .iter()
        .map(|(path, _, _)| *path)
        .chain([PROVENANCE])
        .collect()
}

/// Version-independent identity of declared host surfaces and their seed bytes.
pub(crate) fn identity() -> &'static str {
    PAYLOAD_REVISION
}

pub(crate) fn shipped(path: &str) -> Result<Vec<u8>, CoreError> {
    if path != PROVENANCE {
        return seed(path, Materialization::PackageVerbatim);
    }
    let product: toml::Value = toml::from_str(include_str!("../../../pyproject.toml"))
        .map_err(|e| CoreError::new(e.to_string()))?;
    let version = product["project"]["version"].as_str().unwrap();
    let value = json!({"kind":"agentic-workspace/payload-provenance/v1",
        "payload_schema":"agentic-workspace/payload/v1",
        "managed_revision":identity(),
        "payload_capabilities":CAPABILITIES,
        "payload_files":PAYLOAD.iter().map(|(path,_,_)| *path).collect::<Vec<_>>(),
        "release_identity":{"package":"agentic-workspace","version":version},
        "rule":"Artifact-derived payload identity; native admission also checks every shipped byte. No domain-state or completion authority."});
    let mut bytes = serde_json::to_vec_pretty(&value).map_err(|e| CoreError::new(e.to_string()))?;
    bytes.push(b'\n');
    Ok(bytes)
}

pub(crate) fn materialization(path: &str) -> Result<Materialization, CoreError> {
    if path == PROVENANCE {
        return Ok(Materialization::PackageVerbatim);
    }
    PAYLOAD
        .iter()
        .find(|(p, _, _)| *p == path)
        .map(|(_, mode, _)| *mode)
        .ok_or_else(|| CoreError::new("source is not in the artifact's payload declaration"))
}

/// Seed bytes require the caller's exact materializer, never generic copy authority.
pub(crate) fn seed(path: &str, expected: Materialization) -> Result<Vec<u8>, CoreError> {
    #[cfg(test)]
    crate::native_frontier::built("payload-seed");
    if let Some((_, mode, bytes)) = PAYLOAD.iter().find(|(p, _, _)| *p == path) {
        if *mode != expected {
            return Err(CoreError::new(
                "host surface requires its declared materializer, not package copying",
            ));
        }
        return text(bytes)
            .map(String::into_bytes)
            .ok_or_else(|| CoreError::new("shipped payload is not UTF-8"));
    }
    Err(CoreError::new(
        "source is not in the artifact's payload declaration",
    ))
}

fn text(bytes: &[u8]) -> Option<String> {
    std::str::from_utf8(bytes)
        .ok()
        .map(|s| s.replace("\r\n", "\n"))
}

/// Configuration's host-specific postimage; ordinary files remain exact payload bytes.
pub(crate) fn desired(target: &Path, path: &str) -> Result<Vec<u8>, CoreError> {
    use crate::native_ownership::{LEDGER, PROFILE};
    let mode = materialization(path)?;
    if mode == Materialization::PackageVerbatim {
        return shipped(path);
    }
    let root = Dir::open_ambient_dir(target, ambient_authority())
        .map_err(|e| CoreError::new(e.to_string()))?;
    let before = crate::native_planning::read(&root, LEDGER)?;
    let before = before
        .as_deref()
        .map(std::str::from_utf8)
        .transpose()
        .map_err(|e| CoreError::new(e.to_string()))?;
    let ledger = crate::native_ownership::compose(
        before,
        &crate::native_adoption::ownership_baseline(target)?,
    )?;
    if mode == Materialization::HostComposed {
        return Ok(ledger.into_bytes());
    }
    // A separately requested profile refresh binds to the ledger currently on disk.
    // Adoption instead projects its resulting ledger in the same bounded effect.
    let rendered = crate::native_ownership::profile(target, before.unwrap_or(&ledger))?;
    let current_profile = crate::native_planning::read(&root, PROFILE)?;
    crate::native_ownership::admit_profile(
        current_profile
            .as_deref()
            .map(std::str::from_utf8)
            .transpose()
            .map_err(|e| CoreError::new(e.to_string()))?,
    )?;
    if let Some(current) = current_profile
        && std::str::from_utf8(&current)
            .ok()
            .is_some_and(|s| crate::native_ownership::profile_matches(s, &rendered))
    {
        return Ok(current);
    }
    Ok(rendered.into_bytes())
}

pub(crate) fn view(target: &Path, policy: &Value) -> Result<Value, CoreError> {
    let configured = policy["target_release"]
        .as_str()
        .is_some_and(|s| !s.is_empty())
        || policy["minimum_capabilities"]
            .as_array()
            .is_some_and(|v| !v.is_empty());
    if !configured {
        return Ok(json!({"status":"not-configured","blockers":[]}));
    }
    let root = Dir::open_ambient_dir(target, ambient_authority())
        .map_err(|e| CoreError::new(e.to_string()))?;
    let product: toml::Value =
        toml::from_str(include_str!("../../../pyproject.toml")).expect("product manifest");
    let version = product["project"]["version"]
        .as_str()
        .expect("product version");
    let requested = policy["target_release"].as_str().unwrap_or(version);
    let expected = if requested == "source-current" {
        version
    } else {
        requested
    };
    let mut observations = Vec::new();
    let mut gaps = Vec::new();
    let mut read = |reference: &str| match crate::native_planning::read(&root, reference) {
        Ok(Some(bytes)) => {
            observations.push(
                json!({"path":reference,"revision":format!("sha256:{:x}",Sha256::digest(&bytes))}),
            );
            Some(bytes)
        }
        Ok(None) => {
            observations.push(json!({"path":reference,"status":"missing"}));
            None
        }
        Err(_) => {
            observations.push(json!({"path":reference,"status":"unreadable-or-unconfined"}));
            None
        }
    };
    let provenance = read(PROVENANCE)
        .and_then(|b| serde_json::from_slice::<Value>(&b).ok())
        .unwrap_or(Value::Null);
    if provenance["kind"] != "agentic-workspace/payload-provenance/v1"
        || provenance["payload_schema"] != "agentic-workspace/payload/v1"
        || provenance["release_identity"]["package"] != "agentic-workspace"
        || provenance["release_identity"]["version"] != expected
        || expected != version
    {
        gaps.push(json!({"path":PROVENANCE,"reason":"release-identity-unproven"}));
    }
    for capability in policy["minimum_capabilities"]
        .as_array()
        .into_iter()
        .flatten()
    {
        if !CAPABILITIES.iter().any(|known| capability == known)
            || !provenance["payload_capabilities"]
                .as_array()
                .is_some_and(|caps| caps.contains(capability))
        {
            gaps.push(json!({"path":PROVENANCE,"reason":"required-payload-capability-unproven","capability":capability}));
        }
    }
    for (reference, _, _) in PAYLOAD {
        let bytes = read(reference);
        let expected_bytes = desired(target, reference).ok();
        if expected_bytes.is_none()
            || bytes.as_deref().and_then(text) != expected_bytes.as_deref().and_then(text)
            || !provenance["payload_files"]
                .as_array()
                .is_some_and(|files| files.iter().any(|p| p == reference))
        {
            gaps.push(
                json!({"path":reference,"reason":"installed-payload-differs-from-native-artifact"}),
            );
        }
    }
    let satisfied = gaps.is_empty();
    let affects = match policy["policy"].as_str().unwrap_or("advisory") {
        "required-before-work" => json!(["task"]),
        "required-before-claim" => json!([
            "claim:complete",
            "claim:claim-slice-complete",
            "claim:claim-work-complete",
            "claim:pr-complete"
        ]),
        _ => json!([]),
    };
    let blockers = if !satisfied && affects.as_array().is_some_and(|v| !v.is_empty()) {
        json!([{"code":"native-payload-target-unproven","message":"Current installed payload does not match the declared target and the native artifact's shipped bytes. Preserve the source and reconcile through its package owner; provenance labels cannot waive this gate.","affects":affects}])
    } else {
        json!([])
    };
    Ok(
        json!({"status":if satisfied{"satisfied"}else{"unresolved"},"revision":digest(&json!({"policy":policy,"observations":observations,"gaps":gaps}))?,"policy":policy,"current_policy":{"target_release":policy["target_release"].as_str().unwrap_or("source-current"),"minimum_capabilities":policy["minimum_capabilities"].as_array().cloned().unwrap_or_default(),"policy":policy["policy"].as_str().unwrap_or("advisory")},"artifact_version":version,"observations":observations,"gaps":gaps,"blockers":blockers,"authority":"read-only target conformance; no mutation, proof or completion custody"}),
    )
}
