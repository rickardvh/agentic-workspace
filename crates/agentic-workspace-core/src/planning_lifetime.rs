//! Fixed Planning lifetime paths, classified by the current semantic owner.
//! Unknown legacy meaning is retained. Classification is never inferred from prose.
use serde_json::{Value, json};
use std::path::Path;
use std::process::Command;

pub(crate) const FIELD: &str = "material_lifetimes";
pub(crate) const PROPOSAL: &str = "integration_proposal";
const PATHS: &[(&str, &str)] = &[
    ("next_action", "/next_action"),
    ("external_posture", "/relationships/external_posture"),
    ("continuation_frontier", "/continuation/frontier"),
];

/// Preserve every field except the exact paths explicitly classified as volatile.
/// This does not grant custody or validate the physical source/postimage.
pub(crate) fn durable(body: &Value) -> Value {
    let mut result = body.clone();
    for (key, pointer) in PATHS {
        if body[FIELD][*key] != "observation" {
            continue;
        }
        // The former execplan schema requires next_action, so its neutral
        // representation remains an empty string. Optional slots are absent.
        if *key == "next_action" {
            result["next_action"] = json!("");
        } else {
            let (parent, field) = pointer.rsplit_once('/').unwrap();
            if let Some(object) = result.pointer_mut(parent).and_then(Value::as_object_mut) {
                object.remove(field);
            }
        }
    }
    result
}

/// Current target observation only. It cannot grant proof or terminal authority.
/// No observation, target HEAD, receipt or external tracker mirror is persisted.
pub(crate) fn integration(target: &Path, reference: &str, body: &Value) -> Value {
    let Some(proposal) = body.get(PROPOSAL) else {
        return json!({"status":"absent"});
    };
    let mut result = json!({"status":"unavailable","proposal":proposal,
        "proof_authority":false,"completion_authority":false,
        "owner_lifecycle":"requires-explicit-current-owner-disposition"});
    let deadline = std::time::Instant::now() + std::time::Duration::from_secs(2);
    let git = |args: &[&str]| -> Option<Vec<u8>> {
        let mut command = Command::new("git");
        command
            .arg("--no-pager")
            .arg("-C")
            .arg(target)
            .args(args)
            .env("GIT_TERMINAL_PROMPT", "0")
            .env("GIT_OPTIONAL_LOCKS", "0");
        let (status, bytes) = crate::native_verification::bounded_git_output_with_limit(
            &mut command,
            deadline.saturating_duration_since(std::time::Instant::now()),
            crate::decision_source::MAX_SOURCE_BYTES,
        )
        .ok()?;
        status.success().then_some(bytes)
    };
    let text = |args: &[&str]| -> Option<String> {
        String::from_utf8(git(args)?)
            .ok()
            .map(|s| s.trim().to_owned())
    };
    if text(&["rev-parse", "--is-inside-work-tree"]).as_deref() != Some("true") {
        return result;
    }
    let Some(branch) = text(&["symbolic-ref", "--quiet", "HEAD"]) else {
        result["status"] = json!("detached-target-unproven");
        return result;
    };
    let Some(head) = text(&["rev-parse", "--verify", "HEAD"]) else {
        return result;
    };
    if ![40, 64].contains(&head.len()) || !head.bytes().all(|b| b.is_ascii_hexdigit()) {
        return result;
    }
    result["observed_ref"] = json!(branch);
    result["observed_head"] = json!(head);
    if proposal["target_ref"] != branch {
        result["status"] = json!("awaiting-target");
        return result;
    }
    // Resolve the immutable observed commit, not HEAD again, and bound the blob
    // before reading it. Matching a branch name alone does not prove inclusion.
    let object = format!("{head}:{reference}");
    let Some(size) = text(&["cat-file", "-s", &object]).and_then(|s| s.parse::<usize>().ok())
    else {
        result["status"] = json!("owner-not-integrated");
        return result;
    };
    if size > crate::decision_source::MAX_SOURCE_BYTES {
        result["status"] = json!("owner-not-integrated");
        return result;
    }
    let Some(committed) = git(&["cat-file", "blob", &object]) else {
        return result;
    };
    let exact = cap_std::fs::Dir::open_ambient_dir(target, cap_std::ambient_authority())
        .ok()
        .and_then(|root| {
            crate::native_planning::read(&root, reference)
                .ok()
                .flatten()
        });
    if exact.as_ref() != Some(&committed)
        || serde_json::from_slice::<Value>(&committed).ok().as_ref() != Some(body)
    {
        result["status"] = json!("owner-not-integrated");
        return result;
    }
    if text(&["symbolic-ref", "--quiet", "HEAD"]).as_ref() != Some(&branch)
        || text(&["rev-parse", "--verify", "HEAD"]).as_ref() != Some(&head)
    {
        result["status"] = json!("target-moved-during-observation");
        return result;
    }
    result["status"] = json!("integration-observed");
    result
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn classification_preserves_unknown_and_durable_custody() {
        let legacy = json!({"next_action":"finish required proof","relationships":{"external_posture":{"head":"old"},"returned":{"result":{"sealed":"receipt"}},"integration_pending":{"result":"pending"}},"continuation":{"frontier":"accepted semantic result","residual":"unresolved intent"}});
        assert_eq!(durable(&legacy), legacy);
        let mut classified = legacy.clone();
        classified[FIELD] = json!({"next_action":"durable","external_posture":"observation","continuation_frontier":"durable"});
        let output = durable(&classified);
        assert!(output["relationships"].get("external_posture").is_none());
        assert_eq!(output["next_action"], legacy["next_action"]);
        assert_eq!(output["continuation"], legacy["continuation"]);
        assert_eq!(
            output["relationships"]["returned"],
            legacy["relationships"]["returned"]
        );
        assert_eq!(
            output["relationships"]["integration_pending"],
            legacy["relationships"]["integration_pending"]
        );
    }
}
