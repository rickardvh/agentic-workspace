//! Owner-local manual carriage. Reported work never impersonates a process run.
use crate::{CoreError, digest};
use cap_std::fs::{Dir, OpenOptions};
use serde_json::{Value, json};
use std::{io::Write, path::Path};

pub(crate) const EXPORT: &str = "delegation/retain-manual/v1";
pub(crate) const REPORT: &str = "delegation/report-manual/v1";
pub(crate) const READ: &str = "delegation/read-manual-result/v1";
pub(crate) const FINISH: &str = "delegation/settle-manual/v1";
pub(crate) const DISPOSE: &str = "delegation/dispose-manual/v1";
pub(crate) const OP: &str = "delegation.record-manual";
const EFFECT: &str = "delegation-carriage";
fn err(e: impl ToString) -> CoreError {
    CoreError::new(e.to_string())
}
fn create_carrier(root: &Dir, path: &str, value: &Value) -> Result<(), CoreError> {
    if let Some(bytes) = crate::native_verification::read(root, path).map_err(err)? {
        if serde_json::from_slice::<Value>(&bytes).map_err(err)? != *value {
            return Err(err(
                "Manual effect carrier differs; preserve it for exact owner recovery.",
            ));
        }
        return Ok(());
    }
    root.create_dir_all(".agentic-workspace/local/delegation-runs")
        .map_err(err)?;
    let mut options = OpenOptions::new();
    options.write(true).create_new(true);
    let mut file = root.open_with(path, &options).map_err(err)?;
    file.write_all(&serde_json::to_vec(value).map_err(err)?)
        .map_err(err)?;
    file.sync_all().map_err(err)
}
fn write_continuation(root: &Dir, path: &str, key: &Value, link: &Value) -> Result<(), CoreError> {
    root.create_dir_all(".agentic-workspace/local/delegation-manual")
        .map_err(err)?;
    let temporary = format!("{path}.{}", digest(key)?.replace(':', "-"));
    let mut options = OpenOptions::new();
    options.write(true).create(true).truncate(true);
    crate::native_verification::read(root, &temporary).map_err(err)?;
    let mut file = root.open_with(&temporary, &options).map_err(err)?;
    file.write_all(&serde_json::to_vec(link).map_err(err)?)
        .map_err(err)?;
    file.sync_all().map_err(err)?;
    drop(file);
    root.rename(&temporary, root, path).map_err(err)
}

pub(crate) fn declarations() -> Vec<Value> {
    let shape = |properties: Value, required: Value| json!({"$schema":"https://json-schema.org/draft/2020-12/schema","type":"object","properties":properties,"required":required,"additionalProperties":false});
    vec![
        json!({"kind":EXPORT,"result_kind":"agentic-workspace/manual-carriage/v1","input_schema":shape(json!({"handoff_revision":{"type":"string"}}),json!(["handoff_revision"]))}),
        json!({"kind":REPORT,"result_kind":"agentic-workspace/manual-carriage/v1","input_schema":shape(json!({"producer_kind":{"enum":["human","agent","unknown"]},"reported_delivery":{"type":"boolean"},"reported_execution":{"type":"boolean"},"provenance":{"type":"string","minLength":1,"maxLength":2048}}),json!(["producer_kind","reported_delivery","reported_execution","provenance"]))}),
        json!({"kind":READ,"result_kind":"agentic-workspace/manual-result-observation/v1","input_schema":shape(json!({"custody":{"type":"object"}}),json!(["custody"]))}),
        json!({"kind":FINISH,"result_kind":"agentic-workspace/manual-carriage/v1","input_schema":shape(json!({"admission_revision":{"type":"string"}}),json!(["admission_revision"]))}),
        json!({"kind":DISPOSE,"result_kind":"agentic-workspace/manual-carriage/v1","input_schema":shape(json!({"custody":{"type":"object"},"reason":{"type":"string","minLength":1,"maxLength":2048}}),json!(["custody","reason"]))}),
    ]
}
pub(crate) fn operation() -> Value {
    json!({"id":OP,"semantic_revision":"manual-carriage-v1","input_schema":{"$schema":"https://json-schema.org/draft/2020-12/schema","type":"object","properties":{"target":{"type":"string"},"packet":{"type":"object"},"stage":{"enum":["exported","reported","admitted-for-use","admitted-partial-observation","repair-required","rejected","disposed"]},"returned":{"type":["object","null"]},"provenance":{"type":["object","null"]},"admission":{"type":["object","null"]}},"required":["target","packet","stage","returned","provenance","admission"],"additionalProperties":false},"effects":[EFFECT],"reads":["delegation"],"result_kind":"agentic-workspace/manual-carriage/v1"})
}
fn pointer(packet: &Value) -> Result<String, CoreError> {
    let reentry = &packet["return_contract"]["reentry"];
    let changed = reentry["changed"]
        .as_array()
        .unwrap()
        .iter()
        .map(|p| p.as_str().unwrap().to_owned())
        .collect::<Vec<_>>();
    let identity = crate::direct_task::subject(reentry["task"].as_str().unwrap(), &changed)?;
    Ok(format!(
        ".agentic-workspace/local/delegation-manual/{}.json",
        digest(&identity)?.replace(':', "-")
    ))
}
fn held(target: &Path, path: &str) -> Result<Option<Value>, CoreError> {
    let root = Dir::open_ambient_dir(target, cap_std::ambient_authority()).map_err(err)?;
    let Some(bytes) = crate::native_verification::read(&root, path).map_err(err)? else {
        return Ok(None);
    };
    let link: Value = serde_json::from_slice(&bytes).map_err(err)?;
    if link["kind"] != "agentic-workspace/manual-continuation/v1" {
        return Err(err(
            "Manual continuation custody unresolved; preserve it for its owner.",
        ));
    }
    let committed_path = link["custody"]["committed"]["path"]
        .as_str()
        .ok_or_else(|| err("Manual continuation has no exact commit identity; preserved."))?;
    let committed = crate::native_verification::read(&root, committed_path)
        .map_err(err)?
        .is_some();
    let record = if committed {
        crate::attempt_store::inspect_committed(&target.to_string_lossy(), link["custody"].clone())?
    } else {
        let terminal = link["terminal"].as_str().ok_or_else(|| {
            err("Manual commit unavailable; preserve its custody for owner recovery.")
        })?;
        let planned: Value = serde_json::from_slice(
            &crate::native_verification::read(&root, terminal)
                .map_err(err)?
                .ok_or_else(|| err("Manual terminal unavailable; preserved."))?,
        )
        .map_err(err)?;
        let prepared = crate::attempt_store::prepare_commit(
            &target.to_string_lossy(),
            link["custody"].clone(),
            planned["outcome"].clone(),
        )?;
        let expected = format!(
            ".agentic-workspace/local/delegation-runs/manual-{}.json.terminal.json",
            digest(&prepared["record"]["invocation"]["idempotency_key"])?.replace(':', "-")
        );
        if terminal != expected || prepared["custody"] != planned["custody"] {
            return Err(err(
                "Manual pending terminal differs from exact owner custody; preserved.",
            ));
        }
        prepared["record"].clone()
    };
    if record["invocation"]["source_owner"] != "delegation"
        || record["invocation"]["operation_id"] != OP
        || record["outcome"]["value"]["packet_revision"] != link["packet_revision"]
    {
        return Err(err(
            "Manual continuation differs from committed owner custody; preserved.",
        ));
    }
    Ok(Some(
        json!({"record":record,"custody":link["custody"],"committed":committed}),
    ))
}
pub(crate) fn continuation(
    target: &Path,
    task: &str,
    changed: &[String],
) -> Result<Value, CoreError> {
    let identity = crate::direct_task::subject(task, changed)?;
    let path = format!(
        ".agentic-workspace/local/delegation-manual/{}.json",
        digest(&identity)?.replace(':', "-")
    );
    let Some(held) = held(target, &path)? else {
        return Ok(Value::Null);
    };
    let invocation = &held["record"]["invocation"];
    if held["committed"] != true {
        return Ok(
            json!({"status":"carriage-recovery-required","custody":held["custody"],"recovery_invocation":invocation,"claim_boundary":"A planned local carriage commit is pending. Revalidate and recover this exact owner invocation; do not repeat external work or use an uncommitted return."}),
        );
    }
    let executed = json!({"outcome":held["record"]["outcome"],"custody":held["custody"]});
    Ok(
        json!({"status":held["record"]["outcome"]["value"]["status"],"custody":held["custody"],"packet_revision":held["record"]["outcome"]["value"]["packet_revision"],
        "reentry":result_reentry(&executed,invocation)?,"packet":invocation["arguments"]["packet"],
        "claim_boundary":"Retained manual carriage only; resolve exact reentry through current owners before use. No observed delivery, execution identity, proof, approval or completion is inferred."}),
    )
}
fn request(kind: &str, args: Value, work: &Value, source: &str, contract: &Value) -> Value {
    let owner = contract["owners"]
        .as_array()
        .unwrap()
        .iter()
        .find(|o| o["owner"] == "delegation")
        .unwrap();
    json!({"kind":"agentic-workspace/public-request/v1","id":kind,"owner":"delegation","owner_revision":owner["revision"],"source_revision":source,"capability_revision":contract["revision"],"task_identity":work,"request_kind":kind,"arguments":args})
}
fn validate(value: &Value, work: &Value, source: &str, contract: &Value) -> Result<(), CoreError> {
    crate::prepare_request_value(
        json!({"request":value,"current_work":work,"capability_contract":contract}),
    )?;
    if value["source_revision"] != source {
        return Err(err(
            "Manual assignment/source changed; recover retained work and resolve current owners before returning.",
        ));
    }
    Ok(())
}
pub(crate) fn view(
    target: &Path,
    work: &Value,
    requirements: &Value,
    handoff: &Value,
    submitted: &[Value],
    contract: &Value,
) -> Result<Value, CoreError> {
    let packet = &handoff["packet"];
    let mut out = json!({"status":"manual-export","requests":[],"observation":null,"observed_invocation":null,"contribution":{"owner":"delegation","revision":digest(packet)?,"settled":true,"actions":[]},"claim_boundary":"Manual preparation/reporting never proves execution identity or supplies proof/approval/completion."});
    let source = digest(&json!([work, packet]))?;
    if !packet.is_object() {
        out["status"] = json!("not-ready");
        return Ok(out);
    }
    let read = submitted.iter().find(|r| r["request_kind"] == READ);
    let returned = &handoff["observation"]["returned"];
    let mut previous = held(target, &pointer(packet)?)?;
    if let Some(disposed) = previous.as_ref().filter(|h| {
        h["record"]["outcome"]["value"]["status"] == "disposed"
            && submitted.iter().any(|r| r["request_kind"] == DISPOSE)
    }) {
        let custody = disposed["record"]["outcome"]["value"]["provenance"]["prior_custody"].clone();
        previous = Some(
            json!({"record":crate::attempt_store::inspect_committed(&target.to_string_lossy(),custody.clone())?,"custody":custody}),
        );
    }
    if let Some(previous) = previous.as_ref().filter(|h| {
        h["record"]["invocation"]["arguments"]["packet"] != *packet
            && matches!(
                h["record"]["outcome"]["value"]["status"].as_str(),
                Some("exported" | "reported" | "admitted-partial-observation")
            )
    }) {
        let disposition_source = digest(&json!([source, previous["custody"]]))?;
        let template = request(
            DISPOSE,
            json!({"custody":previous["custody"],"reason":""}),
            work,
            &disposition_source,
            contract,
        );
        let mut carriage = submitted.to_vec();
        if let Some(value) = submitted.iter().find(|r| r["request_kind"] == DISPOSE) {
            validate(value, work, &disposition_source, contract)?;
            if value["arguments"]["custody"] != previous["custody"]
                || value["arguments"]["reason"]
                    .as_str()
                    .unwrap_or("")
                    .trim()
                    .is_empty()
            {
                return Err(err(
                    "Disposition requires the exact old manual custody and an explicit reason; no external execution is inferred.",
                ));
            }
            out["contribution"]["actions"] = json!([{"operation_id":OP,"dependency_revision":disposition_source,"arguments":{"target":target,"packet":previous["record"]["invocation"]["arguments"]["packet"],"stage":"disposed","returned":previous["record"]["outcome"]["value"]["returned"],"provenance":{"disposition":"preserved-historical-observation","reason":value["arguments"]["reason"],"prior_custody":previous["custody"]},"admission":null},"effects":[EFFECT],"source_requests":submitted}]);
            out["contribution"]["settled"] = json!(false);
        } else {
            carriage.push(template);
            out["requests"] = json!([carriage]);
        }
        out["status"] = json!("prior-manual-disposition-required");
        out["prior_custody"] = previous["custody"].clone();
        out["next_route"] = json!(
            "Disposition the old carriage through this exact request before retaining replacement work. Preserve reported material and unknown external delivery/execution; this does not authorise repeating external work."
        );
        return Ok(out);
    }
    if let Some(r) = read {
        validate(r, work, &source, contract)?;
        let record = crate::attempt_store::inspect_committed(
            &target.to_string_lossy(),
            r["arguments"]["custody"].clone(),
        )?;
        if record["invocation"]["operation_id"] != OP
            || record["invocation"]["arguments"]["packet"] != *packet
            || record["outcome"]["value"]["returned"] != *returned
            || record["outcome"]["value"]["status"] != "reported"
        {
            return Err(err(
                "Reported manual return differs from retained owner custody; recover the original report.",
            ));
        }
        out["status"] = json!("manual-result-observed");
        out["observation"] = json!({"status":"current-reported-observation","assignment_identity":requirements["assignment"]["result"]["assignment_identity"],"returned":returned,"custody":r["arguments"]["custody"],"provenance":record["outcome"]["value"]["provenance"],"context":{"task":packet["return_contract"]["reentry"]["task"],"role":packet["assignment_identity"]["role"],"scope_class":packet["assignment_identity"]["scope_class"],"recipient_kind":if packet["human_eligibility"].is_object(){"human"}else{"agent"},"execution_identity":"unverified-reported"},"claim_boundary":{"proof":false,"independent_review":false,"completion":false}});
        if packet["assignment_identity"]["scope_class"] == "unapplied-patch" {
            out["observation"]["delta"] = crate::native_patch::delta(packet, returned)?;
        }
        out["observation"]["recipient_eligible"] = json!(
            !packet["human_eligibility"].is_object()
                || record["outcome"]["value"]["provenance"]["producer_kind"] == "human"
        );
        return Ok(out);
    }
    let reporting = returned.is_object();
    let kind = if reporting { REPORT } else { EXPORT };
    let args = if reporting {
        json!({"producer_kind":"unknown","reported_delivery":false,"reported_execution":false,"provenance":""})
    } else {
        json!({"handoff_revision":digest(packet)?})
    };
    let mut carriage = submitted.to_vec();
    let supplied = submitted.iter().find(|r| r["request_kind"] == kind);
    let template = request(kind, args, work, &source, contract);
    if let Some(value) = supplied {
        validate(value, work, &source, contract)?;
        if (!reporting && *value != template)
            || (reporting
                && value["arguments"]["provenance"]
                    .as_str()
                    .unwrap_or("")
                    .trim()
                    .is_empty())
        {
            return Err(err(
                "Use the exact manual export or explicitly report the return provenance; no delivery/execution is inferred.",
            ));
        }
        let previous = held(target, &pointer(packet)?)?;
        if previous.as_ref().is_some_and(|h| {
            h["record"]["invocation"]["arguments"]["packet"] == *packet
                && h["record"]["outcome"]["value"]["returned"].is_object()
                && reporting
                && h["record"]["outcome"]["value"]["returned"] != *returned
        }) {
            return Err(err(
                "This manual assignment already has a retained return; recover and disposition it before replacing material.",
            ));
        }
        let action = json!({"operation_id":OP,"dependency_revision":source,"arguments":{"target":target,"packet":packet,"stage":if reporting{"reported"}else{"exported"},"returned":if reporting{returned.clone()}else{Value::Null},"provenance":if reporting{value["arguments"].clone()}else{Value::Null},"admission":null},"effects":[EFFECT],"source_requests":submitted});
        out["contribution"]["actions"] = json!([action]);
        out["contribution"]["settled"] = json!(false);
    } else {
        carriage.push(template);
        out["requests"] = json!([carriage]);
    }
    Ok(out)
}
pub(crate) fn settle(
    target: &Path,
    work: &Value,
    handoff: &Value,
    admission: &Value,
    submitted: &[Value],
    contract: &Value,
) -> Result<Value, CoreError> {
    if !matches!(
        admission["status"].as_str(),
        Some("admitted-for-use" | "admitted-partial-observation" | "repair-required" | "rejected")
    ) {
        return Ok(Value::Null);
    }
    let source = digest(admission)?;
    let template = request(
        FINISH,
        json!({"admission_revision":source}),
        work,
        &source,
        contract,
    );
    let mut carriage = submitted.to_vec();
    carriage.retain(|r| r["request_kind"] != FINISH);
    carriage.push(template.clone());
    if let Some(r) = submitted.iter().find(|r| r["request_kind"] == FINISH) {
        validate(r, work, &source, contract)?;
        if *r != template {
            return Err(err("Manual settlement requires exact current admission."));
        }
    }
    Ok(
        json!({"request":carriage,"action":{"operation_id":OP,"dependency_revision":source,"arguments":{"target":target,"packet":handoff["packet"],"stage":admission["status"],"returned":admission["returned"],"provenance":null,"admission":admission},"effects":[EFFECT],"source_requests":carriage}}),
    )
}
pub(crate) fn result_reentry(executed: &Value, invocation: &Value) -> Result<Value, CoreError> {
    let mut reentry = executed["outcome"]["value"]["reentry"].clone();
    if executed["outcome"]["value"]["status"] == "reported" {
        let template = invocation["source_requests"]
            .as_array()
            .unwrap()
            .iter()
            .find(|r| r["request_kind"] == REPORT)
            .ok_or_else(|| err("Manual report request missing"))?;
        let mut read = template.clone();
        read["id"] = json!(READ);
        read["request_kind"] = json!(READ);
        read["arguments"] = json!({"custody":executed["custody"]});
        reentry["request"]
            .as_array_mut()
            .unwrap()
            .retain(|r| r["request_kind"] != REPORT);
        reentry["request"].as_array_mut().unwrap().push(read);
    }
    Ok(reentry)
}
pub(crate) fn execute(
    target: &Path,
    decision: &Value,
    invocation: &Value,
    mut revalidate: impl FnMut() -> Result<(), CoreError>,
) -> Result<Value, CoreError> {
    let packet = &invocation["arguments"]["packet"];
    let root = Dir::open_ambient_dir(target, cap_std::ambient_authority()).map_err(err)?;
    let path = pointer(packet)?;
    let previous = held(target, &path)?;
    let run = format!(
        ".agentic-workspace/local/delegation-runs/manual-{}.json",
        digest(&invocation["idempotency_key"])?.replace(':', "-")
    );
    let terminal = format!("{run}.terminal.json");
    let carrier = crate::native_verification::read(&root, &run)
        .map_err(err)?
        .map(|bytes| serde_json::from_slice::<Value>(&bytes).map_err(err))
        .transpose()?;
    if carrier
        .as_ref()
        .is_some_and(|c| c["invocation"] != *invocation || !c["custody"].is_object())
    {
        return Err(err(
            "Manual attempt custody differs; preserve the original report.",
        ));
    }
    let mut prior_custody = carrier.as_ref().map(|c| c["custody"].clone()).or_else(|| {
        previous
            .as_ref()
            .filter(|h| h["record"]["invocation"] == *invocation)
            .map(|h| h["custody"].clone())
    });
    if let Some(bytes) = crate::native_verification::read(&root, &terminal).map_err(err)? {
        let planned: Value = serde_json::from_slice(&bytes).map_err(err)?;
        let prepared = crate::attempt_store::prepare_commit(
            &target.to_string_lossy(),
            planned["custody"].clone(),
            planned["outcome"].clone(),
        )?;
        if prepared["record"]["invocation"] != *invocation
            || prepared["custody"] != planned["custody"]
        {
            return Err(err("Manual terminal custody mismatch; preserved."));
        }
        revalidate()?;
        if crate::native_verification::read(
            &root,
            planned["custody"]["committed"]["path"].as_str().unwrap(),
        )
        .map_err(err)?
        .is_none()
        {
            let mut uncommitted = planned["custody"].clone();
            uncommitted["committed"] = Value::Null;
            crate::attempt_store::commit(
                json!({"target":target,"custody":uncommitted,"outcome":planned["outcome"]}),
            )?;
        }
        prior_custody = Some(planned["custody"].clone());
    }
    let admission = crate::attempt_store::admit(
        json!({"target":target,"decision":decision,"invocation":invocation,"custody":prior_custody}),
    )?;
    let committed = if admission["disposition"] == "replay" {
        json!({"record":admission["record"],"custody":admission["custody"]})
    } else {
        if admission["disposition"] != "execute" && carrier.is_none() {
            return Err(err(
                "Manual carriage commit is uncertain; recover its exact custody before any replacement.",
            ));
        }
        create_carrier(
            &root,
            &run,
            &json!({"invocation":invocation,"custody":admission["custody"]}),
        )?;
        revalidate()?;
        let stage = &invocation["arguments"]["stage"];
        let mut reentry = packet["return_contract"]["reentry"].clone();
        if stage == "exported" {
            reentry["request"].as_array_mut().unwrap().retain(|r| {
                !matches!(
                    r["request_kind"].as_str(),
                    Some(
                        "assignment/observe-readonly-return/v1"
                            | "assignment/observe-patch-return/v1"
                    )
                )
            });
        } else {
            for r in reentry["request"].as_array_mut().unwrap() {
                if matches!(
                    r["request_kind"].as_str(),
                    Some(
                        "assignment/observe-readonly-return/v1"
                            | "assignment/observe-patch-return/v1"
                    )
                ) {
                    r["arguments"]["returned"] = invocation["arguments"]["returned"].clone();
                }
            }
        }
        if !matches!(stage.as_str(), Some("exported" | "reported")) {
            reentry = json!({"task":reentry["task"],"changed":reentry["changed"],"request":invocation["source_requests"]});
        }
        let outcome = json!({"status":"applied","effects":[EFFECT],"value":{"kind":"agentic-workspace/manual-carriage/v1","status":stage,"packet_revision":digest(packet)?,"returned":invocation["arguments"]["returned"],"provenance":invocation["arguments"]["provenance"],"admission":invocation["arguments"]["admission"],"reentry":reentry,"delivery_observed":false,"execution_observed":false,"claim_boundary":{"proof":false,"independent_review":false,"completion":false}}});
        let prepared = crate::attempt_store::prepare_commit(
            &target.to_string_lossy(),
            admission["custody"].clone(),
            outcome.clone(),
        )?;
        create_carrier(
            &root,
            &terminal,
            &json!({"custody":prepared["custody"],"outcome":outcome}),
        )?;
        let link = json!({"kind":"agentic-workspace/manual-continuation/v1","packet_revision":digest(packet)?,"custody":prepared["custody"],"terminal":terminal});
        write_continuation(&root, &path, &invocation["idempotency_key"], &link)?;
        crate::attempt_store::commit(
            json!({"target":target,"custody":admission["custody"],"outcome":outcome}),
        )?
    };
    // Preserve a later continuation when replaying an earlier exported report.
    let rank = |s: &Value| {
        if s == "exported" {
            0
        } else if s == "reported" {
            1
        } else {
            2
        }
    };
    if !previous.as_ref().is_some_and(|h| {
        (admission["disposition"] == "replay"
            && h["record"]["invocation"]["arguments"]["packet"] != *packet)
            || h["record"]["invocation"]["arguments"]["packet"] == *packet
                && rank(&h["record"]["outcome"]["value"]["status"])
                    > rank(&committed["record"]["outcome"]["value"]["status"])
    }) {
        let link = json!({"kind":"agentic-workspace/manual-continuation/v1","packet_revision":digest(packet)?,"custody":committed["custody"]});
        write_continuation(&root, &path, &invocation["idempotency_key"], &link)?;
    }
    Ok(
        json!({"outcome":committed["record"]["outcome"],"custody":committed["custody"],"post_effect_changed_paths":[]}),
    )
}
