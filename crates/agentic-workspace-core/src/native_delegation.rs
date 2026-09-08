//! Execution of the current sealed handoff. Assignment and admission stay separate.
use crate::{CoreError, digest};
use cap_std::fs::{Dir, OpenOptions};
use serde_json::{Value, json};
use std::{io::Write, path::Path, process::Command, time::Duration};

const KIND: &str = "delegation/dispatch/v1";
const OP: &str = "delegation.dispatch";
fn error(value: impl ToString) -> CoreError {
    CoreError::new(value.to_string())
}
pub(crate) fn contract() -> Result<Value, CoreError> {
    let declaration = json!({"kind":KIND,"result_kind":"agentic-workspace/delegation-execution/v1","input_schema":{"$schema":"https://json-schema.org/draft/2020-12/schema","type":"object","properties":{"handoff_revision":{"type":"string"}},"required":["handoff_revision"],"additionalProperties":false}});
    let operation = json!({"id":OP,"semantic_revision":"native-delegation-v1","input_schema":{"$schema":"https://json-schema.org/draft/2020-12/schema","type":"object","properties":{"target":{"type":"string"},"packet":{"type":"object"},"execution":{"type":"object"}},"required":["target","packet","execution"],"additionalProperties":false},"effects":["delegation-execution"],"reads":["delegation"],"result_kind":"agentic-workspace/delegation-execution/v1"});
    let mut result = json!({"kind":"agentic-workspace/capability-contract/v1","revision":"pending","owners":[{"owner":"delegation","revision":digest(&json!([declaration,operation]))?,"requests":[declaration],"operations":[operation],"domains":["delegation"],"effects":[{"id":"delegation-execution","domain":"delegation"}]}]});
    result["revision"] = json!(digest(&result)?);
    Ok(result)
}

pub(crate) fn view(
    target: &Path,
    work: &Value,
    requirements: &Value,
    handoff: &Value,
    submitted: &[Value],
    contract: &Value,
) -> Result<Value, CoreError> {
    let owner = contract["owners"]
        .as_array()
        .unwrap()
        .iter()
        .find(|o| o["owner"] == "delegation")
        .unwrap();
    let selected = &requirements["assignment"]["result"]["selected"]["configuration"];
    let packet = &handoff["packet"];
    let source = digest(
        &json!({"work":work,"assignment":requirements["assignment"]["result"]["assignment_identity"],"packet":packet,"execution":selected["execution"]}),
    )?;
    let submitted_request = submitted.iter().find(|r| r["request_kind"] == KIND);
    let ready = handoff["status"] == "exported-read-only"
        && selected["transport"] == "cli"
        && selected["execution"]["adapter"]["kind"] == "process"
        && selected["execution"]["adapter"]["output_mode"] == "stdout";
    let mut requests = Vec::new();
    let mut actions = Vec::new();
    if ready {
        let template = json!({"kind":"agentic-workspace/public-request/v1","id":KIND,"owner":"delegation","owner_revision":owner["revision"],"source_revision":source,"capability_revision":contract["revision"],"task_identity":work,"request_kind":KIND,"arguments":{"handoff_revision":digest(packet)?}});
        if let Some(request) = submitted_request {
            crate::prepare_request_value(
                json!({"request":request,"current_work":work,"capability_contract":contract}),
            )?;
            if *request != template {
                return Err(error(
                    "delegation handoff or execution configuration changed",
                ));
            }
            actions.push(json!({"operation_id":OP,"dependency_revision":source,"arguments":{"target":target,"packet":packet,"execution":selected["execution"]},"effects":["delegation-execution"],"source_requests":submitted}));
        } else {
            let mut prerequisites = submitted.to_vec();
            prerequisites.push(template);
            requests.push(json!(prerequisites));
        }
    } else if submitted_request.is_some() {
        return Err(error(
            "current sealed process handoff required before delegation execution",
        ));
    }
    Ok(
        json!({"status":if ready {"dispatch-ready"} else {"not-ready"},"requests":requests,"contribution":{"owner":"delegation","revision":source,"settled":actions.is_empty(),"actions":actions},"claim_boundary":"Execution transports the sealed assignment only; no return admission, Verification proof, Planning progress or completion authority."}),
    )
}

fn read(root: &Dir, path: &str) -> Result<Option<Vec<u8>>, CoreError> {
    crate::native_verification::read(root, path).map_err(error)
}
fn create(root: &Dir, path: &str, value: &Value) -> Result<(), CoreError> {
    read(root, path)?;
    root.create_dir_all(Path::new(path).parent().unwrap())
        .map_err(error)?;
    read(root, path)?;
    let mut file = root
        .open_with(path, OpenOptions::new().write(true).create_new(true))
        .map_err(error)?;
    file.write_all(&serde_json::to_vec(value).map_err(error)?)
        .map_err(error)?;
    file.sync_all().map_err(error)
}
pub(crate) fn execute(
    target: &Path,
    decision: &Value,
    invocation: &Value,
    mut revalidate: impl FnMut() -> Result<(), CoreError>,
) -> Result<Value, CoreError> {
    let root = Dir::open_ambient_dir(target, cap_std::ambient_authority()).map_err(error)?;
    let path = format!(
        ".agentic-workspace/local/delegation-runs/{}.json",
        digest(&invocation["idempotency_key"])?.replace(':', "-")
    );
    let completion = format!("{path}.completed.json");
    let terminal = format!("{path}.terminal.json");
    let mut retained = read(&root, &path)?
        .map(|b| serde_json::from_slice::<Value>(&b).map_err(error))
        .transpose()?;
    if let Some(record) = retained.as_ref() {
        if record["kind"] != "agentic-workspace/delegation-run/v1"
            || record["invocation"] != *invocation
            || !record["custody"].is_object()
        {
            return Err(error(
                "existing delegation run lacks exact producer custody; preserved",
            ));
        }
        if let Some(bytes) = read(&root, &completion)? {
            let completed: Value = serde_json::from_slice(&bytes).map_err(error)?;
            if completed["invocation"] != *invocation
                || completed["custody"]["attempt"] != record["custody"]["attempt"]
            {
                return Err(error("delegation completion custody mismatch; preserved"));
            }
            retained = Some(completed);
        }
    } else if read(&root, &completion)?.is_some() || read(&root, &terminal)?.is_some() {
        return Err(error("unowned delegation completion exists; preserved"));
    }
    // A finished worker may be recovered across publication interruption. The
    // terminal carrier binds the exact future commit before it is written;
    // recognizable result files alone never establish that relationship.
    if let Some(record) = retained.as_ref()
        && record["custody"]["committed"].is_null()
        && let Some(bytes) = read(&root, &terminal)?
    {
        let held: Value = serde_json::from_slice(&bytes).map_err(error)?;
        let prepared = crate::attempt_store::prepare_commit(
            &target.to_string_lossy(),
            held["custody"].clone(),
            held["outcome"].clone(),
        )?;
        if held["kind"] != "agentic-workspace/delegation-terminal/v1"
            || prepared["record"]["invocation"] != *invocation
            || prepared["custody"] != held["custody"]
            || held["custody"]["attempt"] != record["custody"]["attempt"]
        {
            return Err(error("delegation terminal custody mismatch; preserved"));
        }
        revalidate()?;
        let committed_path = held["custody"]["committed"]["path"]
            .as_str()
            .ok_or_else(|| error("terminal commit identity missing"))?;
        if read(&root, committed_path)?.is_none() {
            crate::attempt_store::commit(
                json!({"target":target,"custody":record["custody"],"outcome":held["outcome"]}),
            )?;
        }
        crate::attempt_store::inspect_committed(
            &target.to_string_lossy(),
            held["custody"].clone(),
        )?;
        let recovered = json!({"kind":"agentic-workspace/delegation-run/v1","invocation":invocation,"custody":held["custody"]});
        create(&root, &completion, &recovered)?;
        retained = Some(recovered);
    }
    let admission = crate::attempt_store::admit(
        json!({"target":target,"decision":decision,"invocation":invocation,"custody":retained.as_ref().map(|r|&r["custody"])}),
    )?;
    if admission["disposition"] == "replay" {
        return Ok(
            json!({"outcome":admission["record"]["outcome"],"custody":admission["custody"]}),
        );
    }
    if admission["disposition"] != "execute" {
        return Err(error(
            "delegation execution uncertain; do not repeat the worker",
        ));
    }
    let mut carrier = json!({"kind":"agentic-workspace/delegation-run/v1","invocation":invocation,"custody":admission["custody"]});
    create(&root, &path, &carrier)?;
    revalidate()?;
    let execution = &invocation["arguments"]["execution"];
    let adapter = &execution["adapter"];
    let executable = execution["observed_executable"]["path"]
        .as_str()
        .ok_or_else(|| error("current process executable missing"))?;
    let mut command = Command::new(executable);
    for argument in adapter["command"]
        .as_array()
        .ok_or_else(|| error("current process argv missing"))?
        .iter()
        .skip(1)
    {
        command.arg(
            argument
                .as_str()
                .ok_or_else(|| error("process argument must be text"))?,
        );
    }
    command.current_dir(target);
    let process = crate::process_execution::run(
        command,
        Some(serde_json::to_vec(&invocation["arguments"]["packet"]).map_err(error)?),
        Duration::from_secs(
            adapter["timeout_seconds"]
                .as_u64()
                .ok_or_else(|| error("current process deadline missing"))?,
        ),
    )?;
    let current = revalidate().is_ok();
    let complete =
        process["status"] == "passed" && process["output"]["stdout"]["truncated"] == false;
    let returned = if complete {
        serde_json::from_str::<Value>(process["output"]["stdout"]["tail"].as_str().unwrap_or(""))
            .ok()
    } else {
        None
    };
    let packet = &invocation["arguments"]["packet"];
    let identity_matches = returned.as_ref().is_some_and(|r| {
        packet["return_contract"]["required_identity"]
            .as_object()
            .is_some_and(|identity| identity.iter().all(|(k, v)| r.get(k) == Some(v)))
            && r["changed_paths"] == json!([])
            && r["patch"] == ""
    });
    let schema: Value = serde_json::from_str(include_str!(
        "../../../src/agentic_workspace/contracts/schemas/source_decision_input.schema.json"
    ))
    .expect("checked return schema");
    let mut return_shape = schema["$defs"]["readonly_handoff_return"].clone();
    return_shape["$schema"] = schema["$schema"].clone();
    let valid_return = crate::schema_validator(&return_shape, "delegation return")?
        .is_valid(&json!({"returned":returned}));
    let accepted = current
        && complete
        && identity_matches
        && valid_return
        && returned
            .as_ref()
            .is_some_and(|r| r["stop_conditions_hit"] == json!([]));
    let mut reentry = Value::Null;
    if accepted {
        reentry = packet["return_contract"]["reentry"].clone();
        let request = reentry["request"]
            .as_array_mut()
            .and_then(|r| r.last_mut())
            .ok_or_else(|| error("sealed handoff lacks return re-entry"))?;
        request["arguments"]["returned"] = returned.clone().unwrap();
    }
    let outcome = json!({"status":"applied","effects":["delegation-execution"],"value":{"kind":"agentic-workspace/delegation-execution/v1","status":if accepted {"returned-unproven"} else {"censored-or-invalid-return"},"source_current":current,"returned":if accepted{returned.unwrap()}else{Value::Null},"reentry":reentry,"process":{"status":process["status"],"exit_code":process["exit_code"],"duration_ms":process["duration_ms"],"stdout_bytes":process["output"]["stdout"]["bytes"],"stderr_bytes":process["output"]["stderr"]["bytes"],"truncated":process["output"]["stdout"]["truncated"]},"claim_boundary":{"proof":false,"planning_progress":false,"completion":false},"raw_transcript_stored":false}});
    let prepared = crate::attempt_store::prepare_commit(
        &target.to_string_lossy(),
        admission["custody"].clone(),
        outcome.clone(),
    )?;
    create(
        &root,
        &terminal,
        &json!({"kind":"agentic-workspace/delegation-terminal/v1","custody":prepared["custody"],"outcome":outcome}),
    )?;
    let committed = crate::attempt_store::commit(
        json!({"target":target,"custody":admission["custody"],"outcome":outcome}),
    )?;
    carrier["custody"] = committed["custody"].clone();
    create(&root, &completion, &carrier)?;
    Ok(json!({"outcome":committed["record"]["outcome"],"custody":committed["custody"]}))
}
