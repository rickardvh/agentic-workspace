//! Authentication against owner-supplied key custody. The pure host-fact seam
//! is not a public trust-registration surface and never grants a task claim.
use crate::{CoreError, proof_subject};
use base64::{Engine, engine::general_purpose::STANDARD};
use rsa::{BigUint, Pkcs1v15Sign, RsaPublicKey};
use serde_json::{Value, json};
use sha2::{Digest, Sha256};

pub(crate) fn release_keys() -> Value {
    serde_json::from_str(include_str!(
        "../../../src/agentic_workspace/contracts/independent_review_host_keys.json"
    ))
    .expect("release-pinned keys")
}

pub(crate) fn declaration() -> Value {
    let schema: Value = serde_json::from_str(include_str!(
        "../../../src/agentic_workspace/contracts/schemas/review_authentication.schema.json"
    ))
    .expect("checked schema");
    let mut arguments = schema["$defs"]["native_arguments"].clone();
    arguments["$schema"] = schema["$schema"].clone();
    json!({"kind":"verification/authenticate-host-review/v1","result_kind":"agentic-workspace/independent-review-host-authentication/v1","input_schema":arguments})
}

fn text(value: &Value) -> &str {
    value.as_str().unwrap_or("")
}
fn timestamp(value: &Value) -> Option<i64> {
    chrono::DateTime::parse_from_rfc3339(&text(value).trim().replacen(' ', "T", 1))
        .ok()
        .map(|v| v.timestamp_micros())
}

fn signature_valid(signature: &Value, payload: &Value, key: &Value) -> bool {
    let Some(modulus) = BigUint::parse_bytes(text(&key["n"]).as_bytes(), 16) else {
        return false;
    };
    let Some(exponent) = key["e"].as_u64().or_else(|| text(&key["e"]).parse().ok()) else {
        return false;
    };
    let Ok(public) = RsaPublicKey::new(modulus, BigUint::from(exponent)) else {
        return false;
    };
    let Ok(signature) = STANDARD.decode(text(signature)) else {
        return false;
    };
    let Ok(encoded) = proof_subject::compact_json(payload) else {
        return false;
    };
    public
        .verify(
            Pkcs1v15Sign::new::<Sha256>(),
            &Sha256::digest(encoded.as_bytes()),
            &signature,
        )
        .is_ok()
}

pub fn view(input: Value) -> Result<Value, CoreError> {
    let schema: Value = serde_json::from_str(include_str!(
        "../../../src/agentic_workspace/contracts/schemas/review_authentication.schema.json"
    ))
    .expect("checked schema");
    crate::schema_validator(&schema, "review authentication")?
        .validate(&input)
        .map_err(|e| CoreError::new(format!("invalid review authentication input: {e}")))?;
    let host = &input["host_result"];
    let admission = &host["host_admission"];
    let payload = &admission["signed_payload"];
    let key_id = text(&admission["key_id"]).trim();
    let pinned;
    let keys = if input["public_keys"].is_null() {
        pinned = release_keys();
        &pinned
    } else {
        &input["public_keys"]
    };
    let key = &keys[key_id];
    let rejected = || Ok(json!({}));
    if admission["kind"] != "agentic-workspace/independent-review-host-result-admission/v1"
        || admission["status"] != "current"
        || admission["algorithm"] != "RS256"
        || key_id.is_empty()
        || key["status"] != "current"
        || key["algorithm"] != "RS256"
        || key["authority"] != "pinned-host-runtime"
        || text(&key["producer"]) != text(&host["custody"]["producer"])
        || text(&key["trusted_channel"]) != text(&host["custody"]["trusted_channel"])
        || text(&key["issuer"]) != text(&payload["issuer"])
    {
        return rejected();
    }
    let workspace = text(&input["workspace_ref"]);
    if !text(&key["workspace_ref"]).is_empty() && text(&key["workspace_ref"]) != workspace {
        return rejected();
    }
    let now = input["now_unix_micros"].as_i64().unwrap();
    let not_before = timestamp(&key["not_before"]);
    let key_expiry = timestamp(&key["expires_at"]);
    for (field, parsed) in [("not_before", not_before), ("expires_at", key_expiry)] {
        let value = &key[field];
        let absent = value.is_null() || value.as_str().is_some_and(|text| text.trim().is_empty());
        if !absent && parsed.is_none() {
            return rejected();
        }
    }
    if not_before.is_some_and(|v| now < v)
        || key_expiry.is_some_and(|v| now >= v)
        || !text(&key["revoked_at"]).trim().is_empty()
        || !text(&key["superseded_by"]).trim().is_empty()
        || !signature_valid(&admission["signature"], payload, key)
        || payload["kind"]
            != "agentic-workspace/independent-review-host-result-admission-payload/v1"
    {
        return rejected();
    }
    let (Some(issued), Some(expiry)) = (
        timestamp(&payload["issued_at"]),
        timestamp(&payload["expires_at"]),
    ) else {
        return rejected();
    };
    if expiry <= issued
        || not_before.is_some_and(|v| issued < v)
        || key_expiry.is_some_and(|v| expiry > v)
    {
        return rejected();
    }
    let mut body = host.clone();
    for field in [
        "host_admission",
        "host_admission_ref",
        "host_admission_verdict",
    ] {
        body.as_object_mut().unwrap().remove(field);
    }
    let encoded = proof_subject::compact_json(&body)?;
    let expected = json!({"host_result_ref":input["host_result_ref"], "host_result_body_digest":format!("{:x}",Sha256::digest(encoded.as_bytes())),
        "producer":text(&host["custody"]["producer"]),"trusted_channel":text(&host["custody"]["trusted_channel"]),
        "audience":"agentic-workspace.independent-review","workspace_ref":workspace,"operation":"assignment.admit.independent-review",
        "assignment_revision":text(&host["review_result"]["assignment_revision"]),"proof_subject_revision":text(&host["review_result"]["proof_subject_revision"]),
        "key_revision":text(&key["key_revision"])});
    for (field, value) in expected.as_object().unwrap() {
        if text(&payload[field]) != text(value) {
            return rejected();
        }
    }
    let mut result = json!({"kind":"agentic-workspace/independent-review-host-result-verdict/v1","status":"admitted","authority":"host-adapter-resolver",
        "verifier_revision":if text(&key["key_revision"]).is_empty(){key_id}else{text(&key["key_revision"])},"nonce":text(&payload["nonce"]),
        "issued_at":text(&payload["issued_at"]),"expires_at":text(&payload["expires_at"]),"revoked_at":text(&payload["revoked_at"]),
        "superseded_by":text(&payload["superseded_by"]),"registry_authority":text(&key["authority"])});
    result
        .as_object_mut()
        .unwrap()
        .extend(expected.as_object().unwrap().clone());
    Ok(result)
}
