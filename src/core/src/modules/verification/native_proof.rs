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
    process::Command,
    time::Duration,
};

const RUNS: &str = ".agentic-workspace/local/proof-receipts/runs";
const REVISION: &str = "native-selected-proof-v1";
fn err(e: impl std::fmt::Display) -> CoreError {
    CoreError::new(e.to_string())
}
fn sha(bytes: &[u8]) -> String {
    format!("{:x}", Sha256::digest(bytes))
}
fn schema(name: &str) -> Value {
    let schema = crate::source_schema();
    let mut shape = schema["$defs"][name].clone();
    shape["$schema"] = schema["$schema"].clone();
    shape
}
pub(crate) fn declaration() -> Value {
    json!({"kind":"verification/execute-selected/v1","result_kind":"agentic-workspace/proof-execution-result/v1","input_schema":schema("verification_execute_request")})
}
pub(crate) fn record_declaration() -> Value {
    json!({"kind":"verification/record-receipt/v1","result_kind":"agentic-workspace/proof-execution-result/v1","input_schema":schema("verification_record_request")})
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
pub(crate) fn binary(path: &Path) -> Result<Value, CoreError> {
    // Node's Windows launcher uses a namespaced path; native/Python launchers
    // may not. Observe one filesystem identity for the same actual executable.
    let path = std::fs::canonicalize(path).map_err(err)?;
    let mut file = std::fs::File::open(&path).map_err(err)?;
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
fn runtime(target: &Path, strategy: &Value) -> Result<Value, CoreError> {
    let execution = crate::proof_executor::configuration(target)?;
    if !execution.is_null() {
        let mut requirements = Vec::new();
        for declaration in std::iter::once(&strategy["route"]).chain(
            strategy["protocols"]
                .as_object()
                .into_iter()
                .flat_map(|p| p.values()),
        ) {
            if let Some(value) = declaration.get("execution_prerequisites") {
                requirements.push(value.clone());
            }
        }
        let subject = json!({"route_id":strategy["route_id"],"command":strategy["command"],
            "route_revision":digest(&strategy["route"])?,"protocol_revision":digest(&strategy["protocols"])?,"requirements":requirements});
        return Ok(
            json!({"implementation":"native-aw-proof","producer_contract":REVISION,
            "producer":binary(&std::env::current_exe().map_err(err)?)?,
            "executor":crate::proof_executor::observe(target, &execution, &subject)?,
            "shell_dialect":"posix-sh", "strategy_revision":digest(strategy)?,
            "environment_scope":"isolated-image-and-readonly-source", "nested_tool_runtime":"image-bound"}),
        );
    }
    Ok(
        json!({"implementation":"native-aw-proof","producer_contract":REVISION,
        "producer":binary(&std::env::current_exe().map_err(err)?)?,"shell":binary(&shell()?)?,
        "shell_dialect":if cfg!(windows) {"powershell"} else {"posix-sh"},
        "strategy_revision":digest(strategy)?,"environment_scope":"producer-and-declared-shell",
        "nested_tool_runtime":"unobserved"}),
    )
}
pub(crate) struct SelectionMode<'a> {
    pub report: Option<&'a Value>,
    pub alternatives: bool,
}
pub(crate) fn select_mode(
    target: &Path,
    task: &str,
    changed: &[String],
    work: &Value,
    strategy: &Value,
    choice: Option<&Value>,
    mode: SelectionMode<'_>,
) -> Result<Value, CoreError> {
    let SelectionMode {
        report,
        alternatives,
    } = mode;
    if report
        .is_some_and(|value| serde_json::to_vec(value).map_or(true, |bytes| bytes.len() > 262144))
    {
        return Ok(
            json!({"status":"blocked","reason":"interoperability-report-exceeds-native-bound","choices":[]}),
        );
    }
    let mut available = Vec::new();
    let mut domain_count = 0usize;
    let mut profile_count = 0usize;
    let mut omitted_profile_commands = 0usize;
    let mut omitted_domain_commands = 0usize;
    if let Some(routes) = strategy["proof_routes"]
        .as_object()
        .filter(|_| alternatives)
    {
        for (id, route) in routes {
            for command in route["commands"]
                .as_array()
                .into_iter()
                .flatten()
                .filter_map(Value::as_str)
            {
                if route["source_kind"] == "config-domain-lane" {
                    if domain_count >= 16
                        || serde_json::to_vec(&json!({"route_id":id,"command":command}))
                            .map_or(true, |bytes| bytes.len() > 4096)
                    {
                        omitted_domain_commands += 1;
                        continue;
                    }
                    domain_count += 1;
                }
                if route["source_kind"] == "config-proof-profile" {
                    if profile_count >= 16 || command.len() > 4096 {
                        omitted_profile_commands += 1;
                        continue;
                    }
                    profile_count += 1;
                }
                #[cfg(test)]
                crate::native_frontier::built("proof-choice");
                available.push(json!({"route_id":id,"command":command}));
            }
        }
    }
    let Some(choice) = choice else {
        return Ok(
            json!({"status":"selection-required","choices":available,"omitted_domain_command_count":omitted_domain_commands,"omitted_profile_command_count":omitted_profile_commands,"candidate_boundary":"Bounded candidates; other commands remain at source. Agent selection grants no proof sufficiency."}),
        );
    };
    let source_selected = strategy["proof_routes"]
        .get(choice["route_id"].as_str().unwrap_or(""))
        .is_some_and(|route| {
            route["commands"]
                .as_array()
                .is_some_and(|commands| commands.contains(&choice["command"]))
        });
    if !source_selected && report.is_none() {
        return Err(err(
            "proof selection is not a current source-declared command",
        ));
    }
    let command = choice["command"].as_str().unwrap();
    if strategy["selection_blocked"] == true {
        return Ok(
            json!({"status":"blocked","reason":"current-strategy-assessment-unresolved","choices":available}),
        );
    }
    if strategy["disallowed_commands"]
        .as_array()
        .is_some_and(|commands| commands.iter().any(|value| value == command))
    {
        return Ok(
            json!({"status":"blocked","reason":"selected-proof-profile-disallows-command","choices":available}),
        );
    }
    let admission = proof_receipt::command(&json!(command));
    if admission["admitted"] != true {
        return Ok(json!({"status":"blocked","reason":admission["reason"],"choices":available}));
    }
    let route = if source_selected {
        &strategy["proof_routes"][choice["route_id"].as_str().unwrap()]
    } else {
        &Value::Null
    };
    if matches!(
        route["source_kind"].as_str(),
        Some("config-domain-lane" | "config-proof-profile" | "instruction-check")
    ) && serde_json::to_vec(route).map_or(true, |bytes| bytes.len() > 32768)
    {
        return Ok(
            json!({"status":"blocked","reason":"domain-lane-selected-detail-exceeds-native-bound","source_ref":route["source_ref"],"source_revision":route["source_revision"],"choices":available}),
        );
    }
    let mut protocols = serde_json::Map::new();
    let mut dependencies = serde_json::Map::new();
    let root = Dir::open_ambient_dir(target, ambient_authority()).map_err(err)?;
    let mut gaps = Vec::new();
    if !source_selected {
        gaps.push("interoperability-strategy-selection-unproven".into());
    }
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
    }
    for authority in protocols.values().chain(
        (matches!(
            route["source_kind"].as_str(),
            Some("config-domain-lane" | "config-proof-profile" | "instruction-check")
        ))
        .then_some(route),
    ) {
        for field in ["authority_refs", "stale_when"] {
            for reference in authority[field]
                .as_array()
                .into_iter()
                .flatten()
                .filter_map(Value::as_str)
            {
                if reference.contains(['*', '?', '[']) {
                    gaps.push(format!("proof-dependency-selector-unresolved:{reference}"));
                    continue;
                }
                let observation = crate::dependency_binding::observe(
                    &root,
                    reference,
                    crate::dependency_binding::Scheme::RawBytes,
                );
                if observation.status == crate::dependency_binding::Currentness::Current {
                    dependencies.insert(reference.into(), json!(observation.revision.unwrap()));
                } else {
                    gaps.push(format!("proof-dependency-unavailable:{reference}"));
                }
            }
        }
    }
    let semantic_strategy = json!({"execution":strategy["execution"],"command":command,"task_identity":crate::direct_task::subject(task,changed)?,"work":{"id":work["id"],"revision":work["revision"]},"route_id":choice["route_id"],"route":route,"protocols":protocols,"dependencies":dependencies,"source_strategy_revision":digest(strategy)?,"assessment":strategy["assessment"],"assurance_request":strategy["assurance_request"],"strategy_coverage":if source_selected{"selected-command-covered"}else{"unproven"}});
    let observed = if report.is_some() {
        json!({"implementation":"interoperability-report","strategy_revision":digest(&semantic_strategy)?,"producer_admission":"unproven","environment_scope":"unobserved"})
    } else {
        match runtime(target, &semantic_strategy) {
            Ok(value) => value,
            Err(error) if !strategy["execution"].is_null() => {
                return Ok(
                    json!({"status":"blocked","reason":"proof-execution-capability-unavailable","recovery":{"kind":"capability-gap","human_answer_allowed":false,
                        "detail":"The selected proof cannot run with its configured isolation. Supply any named missing declared source inputs in the snapshot and runtime/Git prerequisites in the immutable image, or prepare the Linux Docker daemon, then select the proof again. Human approval cannot supply this capability.",
                        "diagnostic":error.to_string()},"choices":available}),
                );
            }
            Err(error) => return Err(error),
        }
    };
    let mut subject = proof_subject::build(target, changed, command, None, None, &[], &observed)?;
    let mut promotion = Value::Null;
    if let Some(request) = choice.get("promotion") {
        let reference = request["evidence_ref"].as_str().unwrap_or("");
        let receipt = local_receipt(target, reference)?;
        let consumer = request["consumer"].as_str().unwrap_or("");
        if report.is_some()
            || receipt["result"] != "passed"
            || receipt["command"] != command
            || receipt["changed_paths"] != json!(changed)
            || consumer.contains('\\')
            || consumer
                .split('/')
                .any(|part| matches!(part, "" | "." | ".."))
            || !consumer.starts_with(".agentic-workspace/")
            || consumer.starts_with(".agentic-workspace/local/")
            || consumer.starts_with(".agentic-workspace/proof/receipts/")
            || freshness(target, task, changed, work, strategy, &receipt)?["status"] != "reusable"
        {
            return Err(err(
                "repository proof promotion requires current exact local proof and a durable consumer",
            ));
        }
        let durable = format!(
            "proof://receipts/{}",
            receipt["receipt_id"].as_str().unwrap()
        );
        let admitted_consumer = crate::repository_proof::consumer(target, consumer, &durable)?;
        subject = receipt["proof_subject"].clone();
        promotion =
            json!({"receipt":receipt,"consumer":admitted_consumer,"reason":request["reason"]});
    }
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
        "work":{"id":work["id"],"revision":work["revision"]},"strategy":semantic_strategy,"proof_subject":subject,"timeout_seconds":timeout,"reported_observation":report,"promotion":promotion},"choices":available,
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
    // The publication's authenticated native custody already identifies the
    // selected route and command. Revalidate that exact selection, never a
    // catalogue of hypothetical alternatives (including same-command aliases).
    let repository = crate::repository_proof::is_repository(receipt);
    let committed = if repository {
        Some(
            json!({"invocation":{"arguments":{"selection":crate::repository_proof::selection(target, receipt)?}}}),
        )
    } else {
        committed_publication(target, receipt)?
    };
    let Some(committed) = committed else {
        return Ok(
            json!({"status":"unproven","strategy_coverage":"unproven","reason":"native-selected-receipt-custody-unavailable"}),
        );
    };
    let choice = &committed["invocation"]["arguments"]["selection"]["choice"];
    // Observe execution inputs independently of current strategy. Historical
    // runtime strategy_revision participates in the old fingerprint, so retain
    // that field only while rebuilding the observation, never as current policy.
    let previous = &committed["invocation"]["arguments"]["selection"];
    if previous["work"]["id"]
        .as_str()
        .is_some_and(|id| !id.starts_with("direct-task:") && !id.is_empty())
        && if repository {
            previous["work"]["revision"] != work["revision"]
        } else {
            previous["work"] != *work
        }
    {
        return Ok(
            json!({"status":"stale","strategy_coverage":"unproven","reason":"planning-proof-subject-changed"}),
        );
    }
    let mut observed = match runtime(target, &previous["strategy"]) {
        Ok(value) => value,
        Err(_) => {
            return Ok(
                json!({"status":"unproven","strategy_coverage":"unproven","reason":"proof-execution-capability-unavailable"}),
            );
        }
    };
    observed["strategy_revision"] =
        receipt["proof_subject"]["runtime"]["strategy_revision"].clone();
    if repository {
        observed = crate::repository_proof::runtime(&observed);
    }
    let current_subject = proof_subject::build(
        target,
        changed,
        choice["command"].as_str().unwrap(),
        None,
        None,
        &[],
        &observed,
    )?;
    let comparison = proof_subject::compare(
        &receipt["proof_subject"],
        &current_subject,
        receipt["command"].as_str().unwrap_or(""),
    );
    if comparison["status"] != "reusable" {
        return Ok(
            json!({"status":"stale","strategy_coverage":"unproven","reason":if receipt["proof_subject"]["runtime"]["producer"] != observed["producer"] {"native-producer-binary-compatibility-unproven"}else{"current-native-runtime-or-subject-mismatch"},"comparison":comparison}),
        );
    }
    let declared = strategy["proof_routes"]
        .get(choice["route_id"].as_str().unwrap_or(""))
        .is_some_and(|route| {
            route["commands"]
                .as_array()
                .is_some_and(|commands| commands.contains(&choice["command"]))
        });
    if !declared {
        return Ok(
            json!({"status":"reusable","strategy_coverage":"not-required","reason":"observation-current-command-not-required","comparison":comparison}),
        );
    }
    let current = select_mode(
        target,
        task,
        changed,
        work,
        strategy,
        Some(choice),
        SelectionMode {
            report: None,
            alternatives: false,
        },
    )?;
    if current["status"] != "selected" {
        return Ok(
            json!({"status":"reusable","strategy_coverage":"unproven","remaining_gaps":current,"comparison":comparison}),
        );
    }
    use crate::dependency_binding::{Basis, Currentness, Observation, Scheme};
    let adapt = |strategy: &Value| -> Vec<Observation> {
        strategy["dependencies"]
            .as_object()
            .into_iter()
            .flatten()
            .map(|(identity, revision)| Observation {
                identity: identity.clone(),
                scheme: Scheme::RawBytes,
                revision: revision.as_str().map(|s| {
                    if s.starts_with("sha256:") {
                        s.into()
                    } else {
                        format!("sha256:{s}")
                    }
                }),
                status: Currentness::Current,
            })
            .collect()
    };
    let old_dependencies = adapt(&previous["strategy"]);
    let dependencies = adapt(&current["selection"]["strategy"]);
    let identity = json!({"conclusion":"selected-command-sufficiency","choice":choice});
    let compared = crate::dependency_binding::compare(
        Basis {
            conclusion: &identity,
            dependencies: &dependencies,
        },
        Some(Basis {
            conclusion: &identity,
            dependencies: &old_dependencies,
        }),
    );
    let coverage = compared.status == Currentness::Current
        && current["gaps"].as_array().is_some_and(Vec::is_empty);
    let identity = |strategy: &Value| {
        let mut route = strategy["route"].clone();
        if let Some(route) = route.as_object_mut() {
            route.remove("source_revision");
        }
        json!({"conclusion":"proof-sufficiency","choice":choice,"protocols":strategy["protocols"],"route":route})
    };
    let current_identity = identity(&current["selection"]["strategy"]);
    let old_identity = identity(&previous["strategy"]);
    let sufficiency = crate::dependency_binding::compare(
        Basis {
            conclusion: &current_identity,
            dependencies: &dependencies,
        },
        Some(Basis {
            conclusion: &old_identity,
            dependencies: &old_dependencies,
        }),
    );
    Ok(
        json!({"status":"reusable","strategy_coverage":if coverage{"selected-command-covered"}else{"unproven"},"command_coverage":if coverage{choice.clone()}else{Value::Null},"comparison":comparison,
        "sufficiency_currentness":sufficiency.status,"changed_dependencies":compared.changed,"remaining_gaps":current["gaps"],
        "environment_scope":observed["environment_scope"],"nested_tool_runtime":observed["nested_tool_runtime"]}),
    )
}

pub(crate) fn action(
    target: &Path,
    task: &str,
    changed: &[String],
    view: &Value,
    capability_revision: &Value,
) -> Result<Value, CoreError> {
    if view["status"] != "selected" {
        return Ok(json!([]));
    }
    let mut arguments =
        json!({"target":target,"task":task,"changed":changed,"selection":view["selection"]});
    arguments[if view["selection"]["reported_observation"].is_null() {
        "execute_selected"
    } else {
        "record_receipt"
    }] = json!(true);
    Ok(
        json!([{"operation_id":"proof.report","dependency_revision":digest(&json!({"selection":view["selection"],"capability_revision":capability_revision}))?,
        "arguments":arguments,
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
pub(crate) fn run_path(invocation: &Value) -> Result<String, CoreError> {
    Ok(format!(
        "{RUNS}/native-{}/run.json",
        digest(&invocation["idempotency_key"])?.replace(':', "-")
    ))
}
/// Publication may replace the receipt index and retire superseded native
/// receipts/runs. These bounded owner directories are checked independently of
/// the child-process filesystem, including locks and attempt custody.
pub(crate) fn write_scope(action: &Value) -> Result<Vec<String>, CoreError> {
    let mut writes =
        crate::attempt_store::write_paths(&json!({"idempotency_key":action["logical_effect_id"]}))?;
    writes.push(format!("{RUNS}/**"));
    if !action["arguments"]["selection"]["promotion"].is_null() {
        writes.extend([
            ".agentic-workspace/proof/receipts/**".into(),
            ".agentic-workspace/local/effects/source-reconciliation.lock".into(),
        ]);
    }
    Ok(writes)
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

pub(crate) fn retained_attempt(target: &Path, invocation: &Value) -> Result<bool, CoreError> {
    let root = Dir::open_ambient_dir(target, ambient_authority()).map_err(err)?;
    Ok(retained(&root, &run_path(invocation)?, invocation)?.is_some())
}
/// Read a prior native producer's exact committed publication relationship.
/// This is historical effect custody, never current proof or continuation.
pub(crate) fn committed_publication(
    target: &Path,
    receipt: &Value,
) -> Result<Option<Value>, CoreError> {
    let Some(reference) = receipt["source_ref"].as_str() else {
        return Ok(None);
    };
    if !reference.starts_with(&format!("{RUNS}/native-sha256-"))
        || !reference.ends_with("/run.json")
    {
        return Ok(None);
    }
    let root = Dir::open_ambient_dir(target, ambient_authority()).map_err(err)?;
    let Some(bytes) = read(&root, reference)? else {
        return Ok(None);
    };
    let initial: Value = serde_json::from_slice(&bytes).map_err(err)?;
    let invocation = &initial["invocation"];
    if invocation["source_owner"] != "verification"
        || invocation["operation_id"] != "proof.report"
        || run_path(invocation)? != reference
        || receipt["proof_subject"] != invocation["arguments"]["selection"]["proof_subject"]
        || receipt["command"] != invocation["arguments"]["selection"]["choice"]["command"]
    {
        return Ok(None);
    }
    let Some(held) = retained(&root, reference, invocation)? else {
        return Ok(None);
    };
    let committed = crate::attempt_store::inspect_committed(
        &target.to_string_lossy(),
        held["custody"].clone(),
    )?;
    if committed["invocation"] != *invocation
        || committed["outcome"]["value"]["proof_subject"] != receipt["proof_subject"]
        || (committed["outcome"]["value"]["publication"]["reference"]
            != format!(
                "proof://receipts/{}",
                receipt["receipt_id"].as_str().unwrap_or("")
            )
            && committed["outcome"]["value"]["publication"]["reference"]
                != local_reference(receipt)?)
    {
        return Ok(None);
    }
    Ok(Some(committed))
}

pub(crate) fn local_reference(receipt: &Value) -> Result<String, CoreError> {
    let path = receipt["source_ref"]
        .as_str()
        .ok_or_else(|| err("missing local proof custody"))?;
    let id = path
        .strip_prefix(&format!("{RUNS}/native-sha256-"))
        .and_then(|s| s.strip_suffix("/run.json"))
        .filter(|s| s.len() == 64 && s.bytes().all(|b| b.is_ascii_hexdigit()))
        .ok_or_else(|| err("invalid local proof custody"))?;
    Ok(format!("proof://local/{id}"))
}

pub(crate) fn local_receipt(target: &Path, reference: &str) -> Result<Value, CoreError> {
    let id = reference
        .strip_prefix("proof://local/")
        .filter(|s| s.len() == 64 && s.bytes().all(|b| b.is_ascii_hexdigit()))
        .ok_or_else(|| err("invalid local proof reference"))?;
    let root = Dir::open_ambient_dir(target, ambient_authority()).map_err(err)?;
    let path = format!("{RUNS}/native-sha256-{id}/run.json");
    let initial: Value =
        serde_json::from_slice(&read(&root, &path)?.ok_or_else(|| err("local proof unavailable"))?)
            .map_err(err)?;
    let held = retained(&root, &path, &initial["invocation"])?
        .ok_or_else(|| err("local proof custody unavailable"))?;
    let committed = crate::attempt_store::inspect_committed(
        &target.to_string_lossy(),
        held["custody"].clone(),
    )?;
    let receipt = if committed["outcome"]["value"]["receipt"].is_object() {
        committed["outcome"]["value"]["receipt"].clone()
    } else {
        serde_json::from_slice(
            &read(&root, &format!("{path}.receipt.json"))?
                .ok_or_else(|| err("local proof receipt unavailable"))?,
        )
        .map_err(err)?
    };
    if local_reference(&receipt)? != reference
        || crate::native_verification::publication_identity(&receipt)? != receipt["receipt_id"]
        || committed_publication(target, &receipt)?.is_none()
        || committed["outcome"]["value"]["source_current"] != true
    {
        return Err(err("local proof custody or content mismatch"));
    }
    Ok(receipt)
}

/// Preserve a legacy execution in its existing run carrier before retiring its
/// repository copy. This never grants new proof authority or rewrites execution.
pub(crate) fn retain_local(target: &Path, receipt: &Value) -> Result<(), CoreError> {
    if committed_publication(target, receipt)?.is_none() {
        return Err(err(
            "local transfer requires exact committed producer custody",
        ));
    }
    let root = Dir::open_ambient_dir(target, ambient_authority()).map_err(err)?;
    let path = format!("{}.receipt.json", receipt["source_ref"].as_str().unwrap());
    if let Some(bytes) = read(&root, &path)? {
        if serde_json::from_slice::<Value>(&bytes).map_err(err)? != *receipt {
            return Err(err("local proof transfer conflicts with retained bytes"));
        }
    } else {
        create(&root, &path, receipt)?;
    }
    Ok(())
}
fn process(
    command: &str,
    target: &Path,
    executable: &Path,
    budget: Duration,
) -> Result<Value, CoreError> {
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
    cmd.current_dir(target);
    let mut result = crate::process_execution::run(cmd, None, budget)?;
    result["execution_kind"] = json!("trusted-shell");
    Ok(result)
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
    if old.is_none() {
        crate::native_proof_retention::preparation_ready(target)?;
    }
    if old.is_none() && read(&root, &format!("{path}.completed.json"))?.is_some() {
        return Err(err(
            "unowned proof completion carrier exists; preserved before launch",
        ));
    }
    if old.is_none() && !invocation["arguments"]["selection"]["promotion"].is_null() {
        crate::proof_publication::check(target)?;
    }
    let admission = crate::attempt_store::admit(
        json!({"target":target,"decision":current["decision_packet"],"invocation":invocation,"custody":old.as_ref().map(|v|&v["custody"])}),
    )?;
    if admission["disposition"] == "replay" {
        return Ok(
            json!({"status":admission["record"]["outcome"]["status"],"effects":admission["record"]["outcome"]["effects"],"value":admission["record"]["outcome"]["value"],"custody":admission["custody"],"post_effect_changed_paths":[]}),
        );
    }
    if admission["disposition"] != "execute" {
        if let Some(committed) =
            crate::proof_publication::recover(target, invocation, &mut revalidate)?
        {
            return Ok(
                json!({"status":committed["record"]["outcome"]["status"],"effects":committed["record"]["outcome"]["effects"],"value":committed["record"]["outcome"]["value"],"custody":committed["custody"],"post_effect_changed_paths":[]}),
            );
        }
        return Err(err(
            "proof-execution-uncertain; do not replay the possibly non-idempotent command",
        ));
    }
    let run = json!({"kind":"agentic-workspace/proof-execution-run/v1","invocation":invocation,"custody":admission["custody"]});
    create(&root, &path, &run)?;
    revalidate()?;
    let selection = &invocation["arguments"]["selection"];
    if let Some(receipt) = selection["promotion"].get("receipt") {
        let outcome = json!({"status":"applied","effects":["proof-execution"],"value":{
            "kind":"agentic-workspace/proof-execution-result/v1","proof_subject":receipt["proof_subject"],
            "source_current":true,"process":receipt["execution"],"promotion":selection["promotion"],
            "claim_boundary":{"completion_claim_allowed":false},"command_reexecuted":false}});
        let committed = crate::proof_publication::publish(
            target,
            receipt,
            invocation,
            &admission["custody"],
            outcome,
            &mut revalidate,
        )?;
        let mut final_run = run;
        final_run["custody"] = committed["custody"].clone();
        create(&root, &format!("{path}.completed.json"), &final_run)?;
        return Ok(
            json!({"status":"applied","effects":["proof-execution"],"value":committed["record"]["outcome"]["value"],"custody":committed["custody"],"post_effect_changed_paths":[]}),
        );
    }
    // Admission created a carrier, but that alone cannot exempt a new command
    // from ownership checks. Genuine replay/recovery returned above; check the
    // live publication state again after revalidation, before any new execution.
    crate::native_proof_retention::preparation_ready(target)?;
    let command = selection["choice"]["command"]
        .as_str()
        .ok_or_else(|| err("missing selected command"))?;
    let manual = invocation["arguments"]["record_receipt"] == true;
    let executable = selection["proof_subject"]["runtime"]["shell"]["path"]
        .as_str()
        .unwrap_or("");
    let mut result = if manual {
        json!({"status":selection["reported_observation"]["result"],"execution_kind":"interoperability-report","producer_admission":"unproven","reported_observation":selection["reported_observation"],"output":{}})
    } else if selection["proof_subject"]["runtime"]["executor"]["kind"]
        == crate::proof_executor::KIND
    {
        crate::proof_executor::execute(
            target,
            invocation,
            command,
            selection["timeout_seconds"].as_u64().unwrap(),
        )?
    } else {
        process(
            command,
            target,
            Path::new(executable),
            Duration::from_secs(selection["timeout_seconds"].as_u64().unwrap()),
        )?
    };
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
    let publication =
        json!({"status":"unpublished","reason":"proof-source-changed-during-execution"});
    let value = json!({"kind":"agentic-workspace/proof-execution-result/v1","process":result,"publication":publication,
        "proof_subject":selection["proof_subject"],"strategy":selection["strategy"],"source_current":still_current,
        "claim_boundary":{"completion_claim_allowed":false,"task_judgment":"not-produced","independent_review":"not-produced"},
        "producer_admission":if manual {"unproven-interoperability-observation"}else{"retained-native-execution"},
        "strategy_coverage":selection["strategy"]["strategy_coverage"],
        "environment_scope":selection["proof_subject"]["runtime"]["environment_scope"],"nested_tool_runtime":selection["proof_subject"]["runtime"]["nested_tool_runtime"]});
    let mut outcome = json!({"status":"applied","effects":["proof-execution"],"value":value});
    outcome["value"]["receipt"] = receipt.clone();
    if still_current {
        outcome["value"]["publication"] = json!({"status":"local","reference":local_reference(&receipt)?,"scope":"current-checkout","repository_reference":format!("proof://receipts/{id}")});
    }
    let committed = crate::attempt_store::commit(
        json!({"target":target,"custody":admission["custody"],"outcome":outcome}),
    )?;
    let value = committed["record"]["outcome"]["value"].clone();
    let mut final_run = run;
    final_run["custody"] = committed["custody"].clone();
    create(&root, &format!("{path}.completed.json"), &final_run)?;
    // Proof publication adds evidence outputs, not semantic source inputs.
    // Command mutation of declared inputs already makes source_current false;
    // arbitrary nested command effects are not authenticated source edits.
    Ok(
        json!({"status":"applied","effects":["proof-execution"],"value":value,"custody":committed["custody"],"post_effect_changed_paths":[]}),
    )
}
