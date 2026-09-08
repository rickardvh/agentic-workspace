//! Native adapter for the existing selected-proof operation and receipt owner.
//! Execution evidence never supplies task judgment or independent review.
use crate::{CoreError, digest, proof_receipt, proof_subject};
use cap_std::{
    ambient_authority,
    fs::{Dir, OpenOptions},
};
use serde_json::{Value, json};
use sha2::{Digest, Sha256};
use std::{
    io::{Read, Write},
    path::{Path, PathBuf},
    process::{Command, Stdio},
    time::{Duration, Instant},
};

const RUNS: &str = ".agentic-workspace/local/proof-receipts/runs";
const INDEX: &str = ".agentic-workspace/proof/receipts/index.json";
const REVISION: &str = "native-selected-proof-v1";
fn err(e: impl std::fmt::Display) -> CoreError {
    CoreError::new(e.to_string())
}
fn sha(bytes: &[u8]) -> String {
    format!("{:x}", Sha256::digest(bytes))
}
fn schema(name: &str) -> Value {
    let schema: Value = serde_json::from_str(include_str!(
        "../../../src/agentic_workspace/contracts/schemas/source_decision_input.schema.json"
    ))
    .expect("checked schema");
    let mut shape = schema["$defs"][name].clone();
    shape["$schema"] = schema["$schema"].clone();
    shape
}
pub(crate) fn declaration() -> Value {
    json!({"kind":"verification/execute-selected/v1","result_kind":"agentic-workspace/proof-execution-result/v1","input_schema":schema("verification_execute_request")})
}
pub(crate) fn operation() -> Value {
    json!({"id":"proof.report","semantic_revision":REVISION,"input_schema":schema("native_proof_arguments"),"result_kind":"agentic-workspace/proof-execution-result/v1","effects":["proof-execution"],"reads":["verification"]})
}
fn shell() -> Result<PathBuf, CoreError> {
    let names: &[&str] = if cfg!(windows) {
        &["pwsh.exe", "powershell.exe"]
    } else {
        &["sh"]
    };
    for name in names {
        for directory in std::env::split_paths(&std::env::var_os("PATH").unwrap_or_default()) {
            let path = directory.join(name);
            if path.is_file() {
                return std::fs::canonicalize(path).map_err(err);
            }
        }
    }
    Err(err("native-proof-shell-unavailable"))
}
fn binary(path: &Path) -> Result<Value, CoreError> {
    let mut file = std::fs::File::open(path).map_err(err)?;
    let mut hash = Sha256::new();
    let mut chunk = [0; 65536];
    loop {
        let n = file.read(&mut chunk).map_err(err)?;
        if n == 0 {
            break;
        }
        hash.update(&chunk[..n]);
    }
    Ok(json!({"path":path,"sha256":format!("{:x}",hash.finalize())}))
}
fn runtime(strategy: &Value) -> Result<Value, CoreError> {
    Ok(
        json!({"implementation":"native-aw-proof","producer_contract":REVISION,
        "producer":binary(&std::env::current_exe().map_err(err)?)?,"shell":binary(&shell()?)?,
        "shell_dialect":if cfg!(windows) {"powershell"} else {"posix-sh"},
        "strategy_revision":digest(strategy)?,"environment_scope":"producer-and-declared-shell",
        "nested_tool_runtime":"unobserved"}),
    )
}
/// Only exact source commands are constructible. Template resolution belongs to
/// the existing strategy owner and remains an explicit gap here.
pub(crate) fn selected(
    target: &Path,
    task: &str,
    changed: &[String],
    work: &Value,
    strategy: &Value,
    choice: Option<&Value>,
) -> Result<Value, CoreError> {
    let mut available = Vec::new();
    if let Some(routes) = strategy["proof_routes"].as_object() {
        for (id, route) in routes {
            for command in route["commands"]
                .as_array()
                .into_iter()
                .flatten()
                .filter_map(Value::as_str)
            {
                available.push(json!({"route_id":id,"command":command}));
            }
        }
    }
    let Some(choice) = choice else {
        return Ok(json!({"status":"selection-required","choices":available}));
    };
    if !available.iter().any(|item| item == choice) {
        return Err(err(
            "proof selection is not a current source-declared command",
        ));
    }
    let command = choice["command"].as_str().unwrap();
    let admission = proof_receipt::command(&json!(command));
    if admission["admitted"] != true {
        return Ok(json!({"status":"blocked","reason":admission["reason"],"choices":available}));
    }
    let route = &strategy["proof_routes"][choice["route_id"].as_str().unwrap()];
    let mut protocols = serde_json::Map::new();
    let mut dependencies = serde_json::Map::new();
    let root = Dir::open_ambient_dir(target, ambient_authority()).map_err(err)?;
    let mut gaps = Vec::new();
    for id in route["protocol_refs"]
        .as_array()
        .into_iter()
        .flatten()
        .filter_map(Value::as_str)
    {
        let protocol = &strategy["protocols"][id];
        if !protocol.is_object() {
            gaps.push(format!("proof-protocol-unavailable:{id}"));
        }
        protocols.insert(id.into(), protocol.clone());
        for field in ["authority_refs", "stale_when"] {
            for reference in protocol[field]
                .as_array()
                .into_iter()
                .flatten()
                .filter_map(Value::as_str)
            {
                if reference.contains(['*', '?', '[']) {
                    gaps.push(format!("proof-dependency-selector-unresolved:{reference}"));
                    continue;
                }
                match crate::native_verification::read(&root, reference) {
                    Ok(Some(bytes)) => {
                        dependencies.insert(reference.into(), json!(sha(&bytes)));
                    }
                    _ => gaps.push(format!("proof-dependency-unavailable:{reference}")),
                }
            }
        }
    }
    let semantic_strategy = json!({"task_identity":crate::direct_task::subject(task,changed)?,"work":{"id":work["id"],"revision":work["revision"]},"route_id":choice["route_id"],"route":route,"protocols":protocols,"dependencies":dependencies});
    let observed = runtime(&semantic_strategy)?;
    let subject = proof_subject::build(target, changed, command, None, None, &[], &observed)?;
    if subject["identity_complete"] != true {
        gaps.push("proof-subject-incomplete".into());
    }
    let timeout = if route["timeout_seconds"].is_null() {
        1200
    } else {
        match route["timeout_seconds"]
            .as_u64()
            .filter(|value| (1..=1200).contains(value))
        {
            Some(value) => value,
            None => {
                return Ok(
                    json!({"status":"blocked","reason":"proof-timeout-outside-native-bound","choices":available}),
                );
            }
        }
    };
    Ok(
        json!({"status":"selected","selection":{"choice":choice,"task_identity":crate::direct_task::subject(task,changed)?,
        "work":{"id":work["id"],"revision":work["revision"]},"strategy":semantic_strategy,"proof_subject":subject,"timeout_seconds":timeout},"choices":available,
        "gaps":gaps,"environment_boundary":"Native producer and launched shell observed; nested tool environments remain unproven."}),
    )
}
pub(crate) fn freshness(
    target: &Path,
    task: &str,
    changed: &[String],
    work: &Value,
    strategy: &Value,
    receipt: &Value,
) -> Result<Value, CoreError> {
    if receipt["proof_subject"]["runtime"]["implementation"] != "native-aw-proof" {
        return Ok(
            json!({"status":"unproven","strategy_coverage":"unproven","reason":"legacy-proof-recorder-runtime-unobserved"}),
        );
    }
    let choices = selected(target, task, changed, work, strategy, None)?;
    for choice in choices["choices"].as_array().into_iter().flatten() {
        if choice["command"] != receipt["command"] {
            continue;
        }
        let current = selected(target, task, changed, work, strategy, Some(choice))?;
        if current["status"] != "selected" {
            continue;
        }
        let comparison = proof_subject::compare(
            &receipt["proof_subject"],
            &current["selection"]["proof_subject"],
            receipt["command"].as_str().unwrap_or(""),
        );
        if comparison["status"] == "reusable" {
            return Ok(
                json!({"status":if current["gaps"].as_array().is_some_and(Vec::is_empty) {"reusable"} else {"unproven"},"strategy_coverage":"selected-command-covered","comparison":comparison,
                "environment_scope":"producer-and-declared-shell","remaining_gaps":current["gaps"],"nested_tool_runtime":"unobserved"}),
            );
        }
    }
    let reason = if receipt["proof_subject"]["runtime"]["producer"]
        != binary(&std::env::current_exe().map_err(err)?)?
    {
        "native-producer-binary-compatibility-unproven"
    } else {
        "current-native-runtime-subject-or-strategy-mismatch"
    };
    Ok(json!({"status":"stale","strategy_coverage":"unproven","reason":reason}))
}
pub(crate) fn action(
    target: &Path,
    task: &str,
    changed: &[String],
    view: &Value,
) -> Result<Value, CoreError> {
    if view["status"] != "selected" {
        return Ok(json!([]));
    }
    Ok(
        json!([{"operation_id":"proof.report","dependency_revision":digest(&view["selection"])?,
        "arguments":{"target":target,"task":task,"changed":changed,"execute_selected":true,"selection":view["selection"]},
        "effects":["proof-execution"]}]),
    )
}
fn read(root: &Dir, path: &str) -> Result<Option<Vec<u8>>, CoreError> {
    crate::native_verification::read(root, path).map_err(err)
}
fn create(root: &Dir, path: &str, value: &Value) -> Result<Vec<u8>, CoreError> {
    read(root, path)?;
    let parent = Path::new(path).parent().unwrap();
    root.create_dir_all(parent).map_err(err)?;
    // Confinement is checked again after parent creation; links are never custody.
    read(root, path)?;
    let bytes = serde_json::to_vec_pretty(value).map_err(err)?;
    let mut file = root
        .open_with(path, OpenOptions::new().write(true).create_new(true))
        .map_err(err)?;
    file.write_all(&bytes).map_err(err)?;
    file.sync_all().map_err(err)?;
    Ok(bytes)
}
fn run_path(invocation: &Value) -> Result<String, CoreError> {
    Ok(format!(
        "{RUNS}/native-{}/run.json",
        digest(&invocation["idempotency_key"])?.replace(':', "-")
    ))
}
/// A retained carrier only supplies exact attempt references. The common store
/// verifies those bytes and the current invocation before any replay decision.
fn retained(root: &Dir, path: &str, invocation: &Value) -> Result<Option<Value>, CoreError> {
    let Some(bytes) = read(root, path)? else {
        return Ok(None);
    };
    let run: Value = serde_json::from_slice(&bytes).map_err(err)?;
    if run["kind"] != "agentic-workspace/proof-execution-run/v1"
        || run["invocation"] != *invocation
        || !run["custody"].is_object()
    {
        return Err(err(
            "existing proof run has no exact current producer custody; preserved",
        ));
    }
    let completion_path = format!("{path}.completed.json");
    if let Some(bytes) = read(root, &completion_path)? {
        let complete: Value = serde_json::from_slice(&bytes).map_err(err)?;
        if complete["invocation"] != *invocation
            || complete["custody"]["attempt"] != run["custody"]["attempt"]
        {
            return Err(err(
                "proof completion does not belong to retained admission; preserved",
            ));
        }
        return Ok(Some(complete));
    }
    Ok(Some(run))
}
struct ProcessGuard(Box<dyn process_wrap::std::ChildWrapper>);
impl Drop for ProcessGuard {
    fn drop(&mut self) {
        let _ = self.0.kill();
        let until = Instant::now() + Duration::from_millis(250);
        while Instant::now() < until {
            if !matches!(self.0.try_wait(), Ok(None)) {
                break;
            }
            std::thread::sleep(Duration::from_millis(10));
        }
    }
}
fn process(
    command: &str,
    target: &Path,
    executable: &Path,
    budget: Duration,
) -> Result<Value, CoreError> {
    use process_wrap::std::*;
    let mut cmd = Command::new(executable);
    if cfg!(windows) {
        cmd.args([
            "-NoLogo",
            "-NoProfile",
            "-NonInteractive",
            "-Command",
            command,
        ]);
    } else {
        cmd.args(["-c", command]);
    }
    cmd.current_dir(target)
        .stdin(Stdio::null())
        .stdout(Stdio::piped())
        .stderr(Stdio::piped());
    let mut cmd = CommandWrap::from(cmd);
    #[cfg(windows)]
    {
        cmd.wrap(CreationFlags(
            windows::Win32::System::Threading::CREATE_NO_WINDOW,
        ))
        .wrap(JobObject);
    }
    #[cfg(unix)]
    {
        cmd.wrap(ProcessGroup::leader());
    }
    let started = Instant::now();
    let mut guard = ProcessGuard(cmd.spawn().map_err(err)?);
    let child = &mut guard.0;
    let (sender, receiver) = std::sync::mpsc::channel();
    for (name, stream) in [
        (
            "stdout",
            child
                .stdout()
                .take()
                .map(|v| Box::new(v) as Box<dyn Read + Send>),
        ),
        (
            "stderr",
            child
                .stderr()
                .take()
                .map(|v| Box::new(v) as Box<dyn Read + Send>),
        ),
    ] {
        let sender = sender.clone();
        std::thread::spawn(move || {
            let mut tail = Vec::new();
            let mut total = 0usize;
            let mut chunk = [0; 4096];
            if let Some(mut stream) = stream {
                while let Ok(n) = stream.read(&mut chunk) {
                    if n == 0 {
                        break;
                    }
                    total = total.saturating_add(n);
                    tail.extend_from_slice(&chunk[..n]);
                    if tail.len() > 65536 {
                        tail.drain(..tail.len() - 65536);
                    }
                }
            }
            let _ = sender.send((name, total, tail));
        });
    }
    let mut timed_out = false;
    let status = loop {
        if started.elapsed() >= budget {
            timed_out = true;
            child.kill().map_err(err)?;
            break child.wait().map_err(err)?;
        }
        if let Some(status) = child.try_wait().map_err(err)? {
            break status;
        }
        std::thread::sleep(Duration::from_millis(10));
    };
    // A command leaving descendants behind cannot extend the evidence lifetime.
    let _ = child.kill();
    let mut output = serde_json::Map::new();
    for _ in 0..2 {
        match receiver.recv_timeout(Duration::from_secs(2)) {
            Ok((name, count, bytes)) => {
                output.insert(name.into(),json!({"bytes":count,"tail":String::from_utf8_lossy(&bytes),"truncated":count>bytes.len()}));
            }
            Err(_) => {
                return Err(err(
                    "proof output drain incomplete; execution outcome requires owner recovery",
                ));
            }
        }
    }
    Ok(
        json!({"status":if timed_out {"timeout"}else if status.success(){"passed"}else{"failed"},"exit_code":status.code(),
        "duration_ms":started.elapsed().as_millis(),"output":output,"execution_kind":"trusted-shell"}),
    )
}
pub(crate) fn execute(
    target: &Path,
    current: &Value,
    invocation: &Value,
    mut revalidate: impl FnMut() -> Result<(), CoreError>,
) -> Result<Value, CoreError> {
    let root = Dir::open_ambient_dir(target, ambient_authority()).map_err(err)?;
    let path = run_path(invocation)?;
    let old = retained(&root, &path, invocation)?;
    if old.is_none() && read(&root, &format!("{path}.completed.json"))?.is_some() {
        return Err(err(
            "unowned proof completion carrier exists; preserved before launch",
        ));
    }
    if old.is_none() && read(&root, INDEX)?.is_some() {
        return Err(err(
            "proof-publication-index-custody-required; existing index preserved",
        ));
    }
    let admission = crate::attempt_store::admit(
        json!({"target":target,"decision":current["decision_packet"],"invocation":invocation,"custody":old.as_ref().map(|v|&v["custody"])}),
    )?;
    if admission["disposition"] == "replay" {
        return Ok(
            json!({"status":admission["record"]["outcome"]["status"],"effects":admission["record"]["outcome"]["effects"],"value":admission["record"]["outcome"]["value"],"custody":admission["custody"]}),
        );
    }
    if admission["disposition"] != "execute" {
        return Err(err(
            "proof-execution-uncertain; do not replay the possibly non-idempotent command",
        ));
    }
    let run = json!({"kind":"agentic-workspace/proof-execution-run/v1","invocation":invocation,"custody":admission["custody"]});
    create(&root, &path, &run)?;
    revalidate()?;
    let selection = &invocation["arguments"]["selection"];
    let command = selection["choice"]["command"]
        .as_str()
        .ok_or_else(|| err("missing selected command"))?;
    let executable = selection["proof_subject"]["runtime"]["shell"]["path"]
        .as_str()
        .ok_or_else(|| err("missing current shell observation"))?;
    let mut result = process(
        command,
        target,
        Path::new(executable),
        Duration::from_secs(selection["timeout_seconds"].as_u64().unwrap()),
    )?;
    let detail_path = format!("{path}.command.json");
    let detail_bytes = create(&root, &detail_path, &result)?;
    let streams: serde_json::Map<String, Value> = result["output"]
        .as_object()
        .unwrap()
        .iter()
        .map(|(name, stream)| {
            (
                name.clone(),
                json!({"bytes":stream["bytes"],"truncated":stream["truncated"]}),
            )
        })
        .collect();
    result.as_object_mut().unwrap().remove("output");
    result["artifact"] = json!({"path":detail_path,"sha256":sha(&detail_bytes),"streams":streams});
    // Currentness is checked after execution; a process that edits its own
    // subject cannot publish a current proof merely because it exited zero.
    let still_current = revalidate().is_ok();
    let seconds = std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .map_err(err)?
        .as_secs();
    let timestamp = chrono::DateTime::<chrono::Utc>::from_timestamp(seconds as i64, 0)
        .ok_or_else(|| err("clock unavailable"))?
        .to_rfc3339();
    let mut receipt = json!({"kind":"agentic-workspace/proof-receipt/v1","command":command,"changed_paths":invocation["arguments"]["changed"],
        "result":if result["status"]=="passed" {"passed"}else{"failed"},"recorded_at":timestamp,"proof_subject":selection["proof_subject"],
        "producer_class":"aw-proof","authority":"aw-proof","execution":result,"execution_artifact":result["artifact"]});
    let id = crate::native_verification::publication_identity(&receipt)?;
    receipt["receipt_id"] = json!(id);
    receipt["publication_id"] = json!(id);
    receipt["revision"] = json!(timestamp);
    receipt["source_ref"] = json!(path);
    let mut publication =
        json!({"status":"unpublished","reason":"proof-source-changed-during-execution"});
    if still_current {
        let receipt_path = format!(".agentic-workspace/proof/receipts/{id}.json");
        create(&root, &receipt_path, &receipt)?;
        let mut next =
            json!({"kind":"agentic-workspace/trusted-producer-receipt-index/v1","receipts":{}});
        next["receipts"][&id] = json!({"path":format!("{id}.json"),"producer_class":"aw-proof","revision":timestamp,"source_ref":path,"status":"current"});
        if create(&root, INDEX, &next).is_ok() {
            publication = json!({"status":"published","reference":format!("proof://receipts/{id}"),"index_sha256":sha(&serde_json::to_vec_pretty(&next).map_err(err)?)});
        } else {
            publication = json!({"status":"unpublished","reason":"proof-publication-index-collision-preserved","receipt_path":receipt_path});
        }
    }
    let value = json!({"kind":"agentic-workspace/proof-execution-result/v1","process":result,"publication":publication,
        "proof_subject":selection["proof_subject"],"strategy":selection["strategy"],"source_current":still_current,
        "claim_boundary":{"completion_claim_allowed":false,"task_judgment":"not-produced","independent_review":"not-produced"},
        "environment_scope":"producer-and-declared-shell","nested_tool_runtime":"unobserved"});
    let committed = crate::attempt_store::commit(
        json!({"target":target,"custody":admission["custody"],"outcome":{"status":"applied","effects":["proof-execution"],"value":value}}),
    )?;
    let mut final_run = run;
    final_run["custody"] = committed["custody"].clone();
    create(&root, &format!("{path}.completed.json"), &final_run)?;
    Ok(
        json!({"status":"applied","effects":["proof-execution"],"value":value,"custody":committed["custody"]}),
    )
}
