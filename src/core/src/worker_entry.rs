//! Disposable worker presentation over canonical Assignment custody. No launch,
//! source admission, telemetry storage, or replacement Assignment identity.
use crate::{CoreError, assignment_packet, digest};
use serde_json::{Value, json};

const MATERIAL: &[&str] = &[
    "changed_paths",
    "patch",
    "summary",
    "stop_conditions_hit",
    "result_delivery",
];

fn reference(packet: &Value, index: usize) -> Result<String, CoreError> {
    digest(&json!({"packet":packet["packet_integrity"],"input":index}))
}

pub(crate) fn view(input: &Value) -> Result<Value, CoreError> {
    let packet = &input["packet"];
    if packet["packet_integrity"]
        .as_str()
        .is_none_or(str::is_empty)
        || assignment_packet::integrity(packet)? != packet["packet_integrity"]
    {
        return Err(CoreError::new(
            "worker carriage missing or changed; re-export from the current Assignment owner without repeating a launch",
        ));
    }
    let capsule = packet["assignment_identity"]["input_capsule"].as_array();
    if capsule.is_none_or(|items| {
        items.len() > 8
            || items.iter().any(|item| {
                !item.is_object()
                    || !item["reference"].is_string()
                    || !item["revision"].is_string()
                    || !item["content"].is_string()
            })
    }) {
        return Err(CoreError::new(
            "worker packet requires at most eight exact captured inputs",
        ));
    }
    match input["action"].as_str() {
        Some("entry") => {
            let mut view = assignment_packet::worker_context(packet);
            view["kind"] = json!("agentic-workspace/assignment-worker-entry/v1");
            // Keep every restriction and requirement; only immutable protocol
            // and captured input bodies are candidates for machine carriage.
            view["return_contract"]
                .as_object_mut()
                .unwrap()
                .remove("required_identity");
            view["return_contract"]
                .as_object_mut()
                .unwrap()
                .remove("reentry");
            view["return_contract"]["required_fields"] = json!(MATERIAL);
            view["return_contract"]["submission"] = json!(
                "Supply only new material to worker action return with the original packet held by the host; the owner revalidates exact currentness at returned re-entry."
            );
            let mut budget = 8192usize;
            let mut inputs = Vec::new();
            for (index, item) in capsule.into_iter().flatten().enumerate() {
                let mut projected = item.clone();
                let bytes = item["content"].as_str().unwrap_or("").len();
                projected["detail_ref"] = json!(reference(packet, index)?);
                if bytes > 2048 || bytes > budget {
                    projected.as_object_mut().unwrap().remove("content");
                    projected["delivery"] = json!("required-lazy");
                } else {
                    budget -= bytes;
                    projected["delivery"] = json!("inline");
                }
                inputs.push(projected);
            }
            view["inputs"]["capsule"] = json!(inputs);
            view["inputs"]["lazy_expansion_rule"] = json!(
                "Read every required input before working; use worker action expand with its exact detail_ref and the same packet for required-lazy bodies. Missing carriage: stop and re-export from the current owner. Captured bytes are not live source admission."
            );
            let burden = json!({
                "legacy_context_bytes":{"status":"known","value":serde_json::to_vec(&packet["worker_context"]).unwrap().len()},
                "entry_context_bytes":{"status":"known","value":serde_json::to_vec(&view).unwrap().len()},
                "machine_packet_bytes":{"status":"known","value":serde_json::to_vec(packet).unwrap().len()},
                "host_skill_context_bytes":{"status":"unknown"},
                "semantic_turns":{"status":"unknown"},"user_steering":{"status":"unknown"},
                "protocol_repair":{"status":"unknown"},"elapsed_ms":{"status":"unknown"},
                "persistent_writes":{"status":"known","value":0}
            });
            Ok(
                json!({"view":view,"burden":burden,"claim_boundary":"Packet integrity detects alteration, not owner admission or reviewer authentication. Reconstruct disposable carriage through current Assignment/Planning owners; never infer a launch outcome."}),
            )
        }
        Some("expand") => {
            for (index, item) in capsule.into_iter().flatten().enumerate() {
                if input["reference"] == reference(packet, index)? {
                    return Ok(
                        json!({"input":item,"claim_boundary":"Exact captured input only; current source is revalidated by the return owner."}),
                    );
                }
            }
            Err(CoreError::new("unknown worker input reference"))
        }
        Some("return") => {
            let material = input["material"]
                .as_object()
                .ok_or_else(|| CoreError::new("worker return requires new material"))?;
            if material.keys().any(|key| !MATERIAL.contains(&key.as_str())) {
                return Err(CoreError::new(
                    "worker material cannot replace immutable identity or grant authority",
                ));
            }
            let mut returned = packet["return_contract"]["required_identity"].clone();
            let fields = returned
                .as_object_mut()
                .ok_or_else(|| CoreError::new("worker packet has no return identity"))?;
            fields.extend(material.clone());
            returned["kind"] = packet["return_contract"]["kind"].clone();
            if returned["result_delivery"].is_null() {
                returned["result_delivery"] =
                    packet["return_contract"]["result_delivery"]["default"].clone();
            }
            let mut reentry = packet["return_contract"]["reentry"].clone();
            let requests = reentry["request"]
                .as_array_mut()
                .ok_or_else(|| CoreError::new("worker packet has no owner return re-entry"))?;
            let matching = requests
                .iter()
                .filter(|r| {
                    r["owner"] == "assignment"
                        && matches!(
                            r["request_kind"].as_str(),
                            Some(
                                "assignment/observe-readonly-return/v1"
                                    | "assignment/observe-patch-return/v1"
                            )
                        )
                })
                .count();
            if matching != 1 {
                return Err(CoreError::new(
                    "worker packet must have one exact supported owner return request",
                ));
            }
            for request in requests {
                if request["owner"] == "assignment"
                    && matches!(
                        request["request_kind"].as_str(),
                        Some(
                            "assignment/observe-readonly-return/v1"
                                | "assignment/observe-patch-return/v1"
                        )
                    )
                {
                    request["arguments"]["returned"] = returned.clone();
                }
            }
            Ok(
                json!({"reentry":reentry,"claim_boundary":"Assembled unproven return only. Resolve re-entry at the current repository target; its owner rejects stale, forged, out-of-scope or malformed results before observation."}),
            )
        }
        _ => Err(CoreError::new("unknown worker entry action")),
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn captured_input_delivery_is_bounded_and_identity_is_machine_carried() {
        let mut raw = json!({"assignment_id":"a","assignment_revision":"r","run_id":"run","target":"expert",
            "assignment_identity":{"input_capsule":[{"reference":"rule","revision":"one","content":"read first"},{"reference":"large","revision":"two","content":"x".repeat(8193)}]},
            "return_contract":{"kind":"agentic-workspace/delegated-return/v1","result_delivery":{"default":"unapplied-patch"},
                "reentry":{"task":"work","changed":[],"request":[{"owner":"assignment","request_kind":"assignment/observe-readonly-return/v1","arguments":{"returned":null}}]}}});
        let packet = assignment_packet::seal(&raw).unwrap();
        let entry = view(&json!({"action":"entry","packet":packet})).unwrap();
        let inputs = &entry["view"]["inputs"]["capsule"];
        assert_eq!(inputs[0]["content"], "read first");
        assert!(inputs[1]["content"].is_null());
        assert_eq!(inputs[1]["delivery"], "required-lazy");
        let detail =
            view(&json!({"action":"expand","packet":packet,"reference":inputs[1]["detail_ref"]}))
                .unwrap();
        assert_eq!(
            detail["input"],
            raw["assignment_identity"]["input_capsule"][1]
        );
        let material =
            json!({"summary":"finding","patch":"","changed_paths":[],"stop_conditions_hit":[]});
        let result = view(&json!({"action":"return","packet":packet,"material":material})).unwrap();
        let returned = &result["reentry"]["request"][0]["arguments"]["returned"];
        assert_eq!(returned["packet_integrity"], packet["packet_integrity"]);
        assert_eq!(returned["summary"], material["summary"]);
        assert!(view(&json!({"action":"return","packet":packet,"material":{"assignment_revision":"other"}})).is_err());
        let mut damaged = packet.clone();
        damaged["assignment_identity"]["input_capsule"][0]["content"] = json!("different");
        assert!(view(&json!({"action":"entry","packet":damaged})).is_err());
        raw["assignment_identity"]["input_capsule"][0]["content"] = json!("new current input");
        let fresh = assignment_packet::seal(&raw).unwrap();
        assert!(
            view(&json!({"action":"expand","packet":fresh,"reference":inputs[1]["detail_ref"]}))
                .is_err()
        );
        assert!(view(&json!({"action":"entry"})).is_err());
        raw["assignment_identity"]["input_capsule"] = json!(["malformed"]);
        assert!(
            view(&json!({"action":"entry","packet":assignment_packet::seal(&raw).unwrap()}))
                .is_err()
        );
    }
}
