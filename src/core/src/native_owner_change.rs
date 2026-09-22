//! Optional nomination context on an existing owner's request. No operation,
//! publication, permission, scheduler or retained pressure belongs here.
use crate::{CoreError, digest};
use cap_std::{ambient_authority, fs::Dir};
use serde_json::{Value, json};
use std::path::Path;

pub(crate) fn schema() -> Value {
    let text = json!({"type":"string","minLength":1,"maxLength":2048});
    json!({"type":"object","additionalProperties":false,"properties":{
        "origin":{"enum":["trusted-correction","owner-friction","repo-opportunity"]},
        "concern":{"enum":["package","repository"]},
        "disposition":{"enum":["change","already-owned","report","no-action"]},
        "scope":{"enum":["current-work","proactive"]},
        "reason":text,"expected_effect":text,"validation":text,"supersession":text,
        "evidence":{"type":"array","maxItems":8,"items":{"type":"object","additionalProperties":false,
            "properties":{"reference":text,"revision":text},"required":["reference","revision"]}}},
        "required":["origin","concern","disposition","scope","reason","expected_effect","validation","supersession","evidence"]})
}

/// Return a non-mutating disposition, or leave admission with the destination.
/// Exact owner postimage equality proves already-owned; names never do.
pub(crate) fn disposition(
    target: &Path,
    config: &Value,
    args: &Value,
    already_owned: bool,
) -> Result<Option<Value>, CoreError> {
    let Some(nomination) = args.get("nomination") else {
        return Ok(None);
    };
    let root = Dir::open_ambient_dir(target, ambient_authority())
        .map_err(|e| CoreError::new(e.to_string()))?;
    let evidence = nomination["evidence"]
        .as_array()
        .ok_or_else(|| CoreError::new("nomination evidence missing"))?;
    if nomination["origin"] != "trusted-correction" && evidence.is_empty() {
        return Err(CoreError::new(
            "friction/opportunity requires bounded current evidence",
        ));
    }
    for item in evidence {
        let source = item["reference"]
            .as_str()
            .ok_or_else(|| CoreError::new("nomination source missing"))?;
        let bytes = crate::native_planning::read(&root, source)?
            .ok_or_else(|| CoreError::new("nomination evidence source missing"))?;
        if crate::decision_source::hash(&bytes) != item["revision"] {
            return Err(CoreError::new(
                "nomination evidence changed; resolve current owner proposal",
            ));
        }
    }
    let wanted = nomination["disposition"].as_str().unwrap();
    if wanted == "already-owned" && !already_owned {
        return Err(CoreError::new(
            "already-owned requires the current owner's exact semantic postimage",
        ));
    }
    let status = if already_owned {
        Some("already-owned")
    } else if matches!(wanted, "report" | "no-action") {
        Some(wanted)
    } else if nomination["origin"] == "repo-opportunity" {
        let latitude = config["improvement_latitude"]
            .as_str()
            .unwrap_or("conservative");
        if nomination["concern"] == "package" {
            Some("report-to-package-owner")
        } else if !matches!(latitude, "conservative" | "proactive")
            || (nomination["scope"] == "proactive" && latitude != "proactive")
        {
            Some("report")
        } else {
            None
        }
    } else {
        None
    };
    let revision = digest(nomination)?;
    Ok(status.map(|status|json!({"status":status,"nomination_revision":revision,
        "claim_boundary":"Nomination/disposition only; destination authority, publication, recovery and Verification remain unchanged.","retained":false})))
}
