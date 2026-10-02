//! Optional local observations. One state and two fixed recovery/postimage files;
//! neither this working set nor its recovery grants knowledge or task custody.
use crate::{CoreError, digest};
use cap_std::{
    ambient_authority,
    fs::{Dir, OpenOptions},
};
use serde_json::{Value, json};
use std::{
    io::Write,
    path::Path,
    time::{SystemTime, UNIX_EPOCH},
};

pub(crate) const REQUEST: &str = "memory/consider-observation/v1";
pub(crate) const OP: &str = "memory.update-candidates";
const HOME: &str = ".agentic-workspace/local/memory-candidates";
const STATE: &str = ".agentic-workspace/local/memory-candidates/state.json";
const PREPARED: &str = ".agentic-workspace/local/memory-candidates/prepared.json";
const LOCK: &str = ".agentic-workspace/local/memory-candidates/owner.lock";
const BYTES: usize = 65536;
const RESIDUE: usize = BYTES + 4096;
const COUNT: usize = 16;
const AGE: u64 = 14 * 24 * 60 * 60;
fn err(e: impl ToString) -> CoreError {
    CoreError::new(e.to_string())
}
fn now() -> u64 {
    SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap_or_default()
        .as_secs()
}

pub(crate) fn extend_owner(owner: &mut Value) -> Result<(), CoreError> {
    let text = json!({"type":"string","minLength":1,"maxLength":8192});
    let cues = json!({"type":"array","maxItems":16,"uniqueItems":true,"items":{"type":"string","minLength":1,"maxLength":2048}});
    owner["requests"].as_array_mut().unwrap().push(json!({"kind":REQUEST,"result_kind":"agentic-memory/observation-consideration/v1","input_schema":{
        "$schema":"https://json-schema.org/draft/2020-12/schema","type":"object","additionalProperties":false,
        "properties":{"operation":{"enum":["consider","capture","read","consolidate","complete","defer","discard","maintain","recover"]},
            "material_revision":text,"candidate_ids":cues,"consequence":text,"uncertainty":text,
            "paths":cues,"semantic_routes":cues,"captured_at":{"type":"integer","minimum":0},
            "optional":{"const":true},"reason":text,"advisory_material":{"type":"object"},
            "revise_source":text,"source_revision":text,"validity_review":text,
            "publication":{"type":"object","additionalProperties":false,"properties":{"source":text,"revision":text},"required":["source","revision"]},
            "receiving_source":{"type":"object","additionalProperties":false,"properties":{"reference":text,"revision":text},"required":["reference","revision"]},
            "receiving_consequence":{"type":"object","additionalProperties":false,"properties":{"claim":text,"evidence_reference":text,"proof_subject":text},"required":["claim","evidence_reference","proof_subject"]},
            "candidate_evidence_requests":{"type":"array","maxItems":8,"items":{"type":"object"}}},"required":["operation"]}}));
    owner["operations"].as_array_mut().unwrap().push(json!({"id":OP,"semantic_revision":"memory-bounded-local-candidates-v1",
        "input_schema":{"$schema":"https://json-schema.org/draft/2020-12/schema","type":"object","additionalProperties":false,
            "properties":{"target":{"type":"string"},"request":{"type":"object"},"binding":{"type":"object"}},"required":["target","request","binding"]},
        "result_kind":"agentic-memory/candidate-effect/v1","effects":["memory-state"],"reads":["memory"]}));
    owner["revision"] = json!(digest(&json!([owner["requests"], owner["operations"]]))?);
    Ok(())
}

fn read(root: &Dir, path: &str, limit: usize) -> Result<Option<Vec<u8>>, CoreError> {
    // Reuse the confined reader before opening; it rejects every linked ancestor.
    let Some(bytes) = crate::native_planning::read(root, path)? else {
        return Ok(None);
    };
    if bytes.len() > limit {
        return Err(err(
            "Candidate source exceeds its fixed byte bound; preserve unknown source",
        ));
    }
    Ok(Some(bytes))
}
fn empty() -> Value {
    json!({"kind":"agentic-memory/local-candidates/v1","candidates":[]})
}
fn validate(state: &Value) -> Result<(), CoreError> {
    let rows = state["candidates"]
        .as_array()
        .filter(|r| r.len() <= COUNT)
        .ok_or_else(|| err("Invalid bounded candidate state"))?;
    if state["kind"] != "agentic-memory/local-candidates/v1"
        || state.as_object().is_none_or(|o| o.len() != 2)
        || serde_json::to_vec(state).map_err(err)?.len() > BYTES
    {
        return Err(err("Unknown candidate state preserved"));
    }
    let mut ids = std::collections::BTreeSet::new();
    for row in rows {
        if row["id"].as_str().is_none_or(|id| !ids.insert(id))
            || row["captured_at"].as_u64().is_none()
            || row["material"]["kind"] != "observation"
            || row["material"].get("work").is_some()
            || row["uncertainty"].as_str().is_none_or(|s| s.is_empty())
            || row["paths"].as_array().is_none()
            || row["semantic_routes"].as_array().is_none()
            || row["event"] != event(&row["material"])?
        {
            return Err(err("Unknown candidate row preserved"));
        }
    }
    Ok(())
}
fn event(material: &Value) -> Result<String, CoreError> {
    digest(&json!([material["id"], material["source"]]))
}
fn current(row: &Value, clock: u64) -> bool {
    row["captured_at"]
        .as_u64()
        .is_some_and(|t| t <= clock && clock.saturating_sub(t) < AGE)
}
fn snapshot(root: &Dir) -> Result<(Value, Value), CoreError> {
    let bytes = read(root, STATE, BYTES)?;
    let state = bytes
        .as_ref()
        .map(|b| serde_json::from_slice(b).map_err(err))
        .transpose()?
        .unwrap_or_else(empty);
    validate(&state)?;
    Ok((
        state,
        bytes
            .as_ref()
            .map(|b| json!(crate::native_intent::hash(b)))
            .unwrap_or(Value::Null),
    ))
}
fn pending(root: &Dir) -> Result<Option<Value>, CoreError> {
    let Some(bytes) = read(root, PREPARED, RESIDUE)? else {
        return Ok(None);
    };
    let value: Value = serde_json::from_slice(&bytes).map_err(|_| {
        err("Incomplete candidate temporary preserved; inspect exact residue before repair")
    })?;
    validate(&value["postimage"])?;
    if value["kind"] != "agentic-memory/candidate-prepared/v1"
        || value.as_object().is_none_or(|o| o.len() != 4)
        || digest(&value["postimage"])? != value["post_revision"]
    {
        return Err(err("Unknown candidate recovery preserved"));
    }
    Ok(Some(value))
}
fn selectors(row: &Value, changed: &[String], routes: &Value) -> bool {
    row["paths"]
        .as_array()
        .into_iter()
        .flatten()
        .filter_map(Value::as_str)
        .any(|p| {
            changed
                .iter()
                .any(|c| crate::instruction_applicability::patterns_overlap(p, c))
        })
        || routes["status"] == "current"
            && row["semantic_routes"]
                .as_array()
                .into_iter()
                .flatten()
                .any(|r| routes["routes"].as_array().is_some_and(|rs| rs.contains(r)))
}
fn evidence(root: &Dir, row: &Value) -> Value {
    let drift: Vec<_> = row["material"]["dependencies"]
        .as_array()
        .into_iter()
        .flatten()
        .filter(|d| {
            d["reference"].as_str().is_none_or(|p| {
                crate::decision_source::read(root, p)
                    .map(|b| crate::decision_source::hash(&b) != d["revision"])
                    .unwrap_or(true)
            })
        })
        .cloned()
        .collect();
    json!({"observation":row,"trust":"unconfirmed caller-asserted historical observation; no inherited work authority",
        "currentness":if drift.is_empty(){"historical-observation"}else{"dependency-review-required"},"changed_dependencies":drift,
        "live_state":"unknown; check current environment before depending on earlier availability"})
}

#[allow(clippy::too_many_arguments)]
pub(crate) fn view(
    target: &Path,
    work: &Value,
    material: &Value,
    changed: &[String],
    routes: &Value,
    config: &Value,
    contract: &Value,
    verification: &Value,
    request: Option<&Value>,
) -> Result<Value, CoreError> {
    match view_at(
        target,
        work,
        material,
        changed,
        routes,
        config,
        contract,
        verification,
        request,
        now(),
    ) {
        Err(problem) if request.is_none() => Ok(
            json!({"status":"source-review-required","diagnostic":problem.to_string(),"requests":[],"selected":[]}),
        ),
        result => result,
    }
}
#[allow(clippy::too_many_arguments)]
fn view_at(
    target: &Path,
    work: &Value,
    material: &Value,
    changed: &[String],
    routes: &Value,
    config: &Value,
    contract: &Value,
    verification: &Value,
    request: Option<&Value>,
    clock: u64,
) -> Result<Value, CoreError> {
    let owner = contract["owners"]
        .as_array()
        .unwrap()
        .iter()
        .find(|o| o["owner"] == "memory")
        .unwrap();
    let findings: Vec<_> = material["items"]
        .as_array()
        .into_iter()
        .flatten()
        .filter(|r| r["material"]["kind"] == "observation")
        .collect();
    // Ordinary unrelated entry doesn't open the working set. Explicit selection
    // or existing activity/path cues can ask for its bounded historical evidence.
    if request.is_none()
        && findings.is_empty()
        && changed.is_empty()
        && routes["status"] != "current"
    {
        return Ok(Value::Null);
    }
    let root = Dir::open_ambient_dir(target, ambient_authority()).map_err(err)?;
    let (state, before) = snapshot(&root)?;
    let prepared = pending(&root)?;
    let revision = digest(&json!([
        before,
        prepared,
        config["revision"],
        work,
        material
    ]))?;
    let template = |args: Value| {
        json!({"kind":"agentic-workspace/public-request/v1","id":if args["operation"]=="read" {REQUEST.to_owned()} else {format!("{REQUEST}:{}",digest(&args).unwrap())},"owner":"memory",
        "owner_revision":owner["revision"],"source_revision":revision,"capability_revision":contract["revision"],
        "task_identity":work,"request_kind":REQUEST,"arguments":args})
    };
    let mut result = json!({"status":"available","requests":[],"selected":[],"bounds":{"count":COUNT,"state_bytes":BYTES,"age_seconds":AGE,"total_attributable_bytes":2*BYTES+RESIDUE},
        "contribution":{"owner":"memory","revision":revision,"actions":[]}});
    for finding in &findings {
        result["requests"].as_array_mut().unwrap().push(template(json!({"operation":"consider","material_revision":finding["revision"],"captured_at":clock})));
    }
    result["requests"]
        .as_array_mut()
        .unwrap()
        .push(template(json!({"operation":"read"})));
    if prepared.is_some() {
        result["requests"]
            .as_array_mut()
            .unwrap()
            .push(template(json!({"operation":"recover"})));
    }
    if let Some(r) = request {
        crate::prepare_request_value(
            json!({"request":r,"current_work":work,"capability_contract":contract}),
        )?;
        if r["source_revision"] != revision {
            return Err(err(
                "Candidate proposal changed; resolve current observation request",
            ));
        }
    }
    let args = request
        .map(|r| r["arguments"].clone())
        .unwrap_or(Value::Null);
    let ids = args["candidate_ids"].as_array();
    for row in state["candidates"]
        .as_array()
        .unwrap()
        .iter()
        .filter(|r| current(r, clock))
    {
        if ids.map_or_else(
            || selectors(row, changed, routes),
            |ids| ids.contains(&row["id"]),
        ) || args["operation"] == "read" && ids.is_none()
        {
            result["selected"]
                .as_array_mut()
                .unwrap()
                .push(evidence(&root, row));
        }
    }
    if !result["selected"].as_array().unwrap().is_empty() {
        let selected_ids = result["selected"]
            .as_array()
            .unwrap()
            .iter()
            .map(|r| r["observation"]["id"].clone())
            .collect::<Vec<_>>();
        result["requests"].as_array_mut().unwrap().push(template(json!({"operation":"discard","candidate_ids":selected_ids,"reason":"<deliberate disposition>"})));
        result["requests"].as_array_mut().unwrap().push(template(
            json!({"operation":"consolidate","candidate_ids":selected_ids}),
        ));
    }
    let Some(request) = request else {
        return Ok(result);
    };
    if ["consolidate", "complete", "defer"]
        .iter()
        .any(|op| args["operation"] == *op)
    {
        let ids = ids
            .filter(|ids| !ids.is_empty())
            .ok_or_else(|| err("Consolidation requires exact candidate identities"))?;
        if ids.iter().any(|id| {
            !state["candidates"]
                .as_array()
                .unwrap()
                .iter()
                .any(|r| r["id"] == *id && current(r, clock))
        }) {
            result["status"] = json!("optional-evidence-unavailable");
            return Ok(result);
        }
        if args["operation"] == "defer" {
            result["status"] = json!("deferred");
            return Ok(result);
        }
        if args["operation"] == "consolidate" {
            result["status"] = json!("semantic-judgment-required");
            result["next"] = json!({"choices":["new-advice","revise-advice","checked-stronger-owner","defer","discard"],
                "question":"Compare the selected observations and current sources. Preserve differing scopes, origins and uncertainty; recurrence does not prove equivalence. Supply advisory_material only when a concrete future decision justifies publication. Publish first, then complete these exact candidates with the confirmed source/revision. Durable obsolete material uses the existing terminal disposition."});
            if args["advisory_material"].is_object() {
                let scope = changed
                    .iter()
                    .map(|p| format!("path:{p}"))
                    .collect::<Vec<_>>();
                let capture = crate::native_memory_capture::view_for(
                    target,
                    work,
                    &scope,
                    config,
                    contract,
                    (
                        crate::native_memory_capture::Destination::Advisory,
                        &Value::Null,
                    ),
                    None,
                )?;
                let mut publication = capture["requests"][0].clone();
                publication["arguments"]["candidate_ids"] = json!(ids);
                publication["arguments"]["material"] = args["advisory_material"].clone();
                publication["arguments"]["material"]["origins"] = json!(
                    state["candidates"]
                        .as_array()
                        .unwrap()
                        .iter()
                        .filter(|r| ids.contains(&r["id"]))
                        .map(|r| r["material"]["source"].clone())
                        .collect::<Vec<_>>()
                );
                // Keep deliberately supplied earlier provenance alongside this
                // opportunity's origins. Deduplication is identity, not evidence
                // corroboration; bounded publication still needs agent judgment.
                for origin in args["advisory_material"]["origins"]
                    .as_array()
                    .into_iter()
                    .flatten()
                {
                    let origins = publication["arguments"]["material"]["origins"]
                        .as_array_mut()
                        .unwrap();
                    if !origins.contains(origin) {
                        origins.push(origin.clone());
                    }
                }
                if publication["arguments"]["material"]["origins"]
                    .as_array()
                    .unwrap()
                    .len()
                    > 16
                {
                    return Err(err(
                        "Narrow the consolidation provenance to its relevant bounded opportunity",
                    ));
                }
                for key in ["revise_source", "source_revision", "validity_review"] {
                    if let Some(value) = args.get(key) {
                        publication["arguments"][key] = value.clone();
                    }
                }
                result["publication_request"] = publication;
            }
            return Ok(result);
        }
    }
    if ["read", "consider"]
        .iter()
        .any(|op| args["operation"] == *op)
    {
        if args["operation"] == "consider" {
            let finding = findings
                .iter()
                .find(|f| f["revision"] == args["material_revision"])
                .ok_or_else(|| err("Select an exact supplied observation"))?;
            result["finding"] = (*finding).clone();
            result["next"] = json!({"choices":["correct-current-source","retain-advice","no-retention","capture"],
                "question":"Would losing this observation discard a concrete learning opportunity? Save only optional uncertain-value material; commitments and uncertain effects need their existing durable owner."});
        }
        return Ok(result);
    }
    let mut post = state.clone();
    if args["operation"] == "recover" {
        let p = prepared
            .as_ref()
            .ok_or_else(|| err("No candidate effect to recover"))?;
        if before != p["before"] && digest(&state)? != p["post_revision"] {
            return Err(err(
                "Candidate recovery conflicts with current source; preserve both",
            ));
        }
        post = p["postimage"].clone();
    } else {
        if prepared.is_some() {
            result["status"] = json!("pending-local-effect");
            return Ok(result);
        }
        if args["operation"] == "capture" {
            if args["optional"] != true
                || args["uncertainty"]
                    .as_str()
                    .is_none_or(|s| s.trim().is_empty())
            {
                return Err(err(
                    "Provisional capture needs optional material and its uncertainty; explicit commitments/effects belong to their durable owner",
                ));
            }
            let finding = findings
                .iter()
                .find(|f| f["revision"] == args["material_revision"])
                .ok_or_else(|| err("Capture requires the exact ordinary observation"))?;
            let mut observation = finding["material"].clone();
            observation.as_object_mut().unwrap().remove("work");
            let id = event(&observation)?;
            if let Some(old) = state["candidates"]
                .as_array()
                .unwrap()
                .iter()
                .find(|r| r["event"] == id)
            {
                result["status"] = json!("already-considered");
                result["candidate"] = old.clone();
                return Ok(result);
            }
            let captured = args["captured_at"]
                .as_u64()
                .filter(|t| *t <= clock && clock - *t < AGE)
                .ok_or_else(|| {
                    err("Observation age is unknown or expired; nominate a new current observation")
                })?;
            let paths = args["paths"].as_array().cloned().unwrap_or_default();
            let semantic_routes = args["semantic_routes"]
                .as_array()
                .cloned()
                .unwrap_or_default();
            for p in &paths {
                crate::decision_source::relative(p.as_str().unwrap())?;
            }
            if paths.is_empty() && semantic_routes.is_empty() {
                return Err(err(
                    "Provide a deliberately scoped path or existing activity cue for later consideration",
                ));
            }
            post["candidates"]
                .as_array_mut()
                .unwrap()
                .retain(|r| current(r, clock));
            post["candidates"].as_array_mut().unwrap().push(json!({"id":id,"event":id,"material":observation,
                "consequence":args["consequence"].as_str().unwrap_or(finding["material"]["summary"].as_str().unwrap()),
                "uncertainty":args["uncertainty"],"paths":paths,"semantic_routes":semantic_routes,"captured_at":captured}));
            // Optional oldest material is evicted before publication; new input
            // too large for an empty set is explicitly declined.
            while post["candidates"].as_array().unwrap().len() > COUNT
                || serde_json::to_vec(&post).map_err(err)?.len() > BYTES
            {
                if post["candidates"].as_array().unwrap().len() == 1 {
                    result["status"] = json!("declined-capacity");
                    return Ok(result);
                }
                post["candidates"].as_array_mut().unwrap().remove(0);
            }
        } else if args["operation"] == "discard" || args["operation"] == "complete" {
            let selected = ids
                .filter(|ids| !ids.is_empty())
                .ok_or_else(|| err("Discard requires exact candidate identities"))?;
            if args["operation"] == "complete" {
                let confirmation = if args["publication"].is_object() {
                    crate::native_memory_capture::confirmed_publication(
                        target,
                        args["publication"]["source"].as_str().unwrap(),
                        &args["publication"]["revision"],
                    )?
                } else {
                    crate::native_memory_learning::checked_receiving_consequence(
                        target,
                        &args,
                        verification,
                    )?
                };
                result["confirmation"] = confirmation;
            } else if args["reason"].as_str().is_none_or(|s| s.trim().is_empty()) {
                return Err(err("Discard requires a deliberate disposition"));
            }
            post["candidates"]
                .as_array_mut()
                .unwrap()
                .retain(|r| !selected.contains(&r["id"]));
        } else if args["operation"] == "maintain" {
            post["candidates"]
                .as_array_mut()
                .unwrap()
                .retain(|r| current(r, clock));
        }
    }
    validate(&post)?;
    if post == state && args["operation"] != "recover" {
        result["status"] = json!("unchanged");
        return Ok(result);
    }
    let binding = json!({"before":before,"postimage":post,"post_revision":digest(&post)?,"prepared":prepared,"confirmation":result["confirmation"]});
    result["status"] = json!("write-ready");
    result["contribution"]["actions"] = json!([{"operation_id":OP,"dependency_revision":digest(&json!([binding,request]))?,
        "arguments":{"target":target,"request":request,"binding":binding},"effects":["memory-state"],"source_requests":[request]}]);
    Ok(result)
}

/// Constructible next input, not a cleanup action. Only a committed native
/// publisher supplies the bound candidate identities; normal completion still
/// reobserves candidates, publication custody and validity before subtraction.
pub(crate) fn publication_completion(
    candidates: &Value,
    invocation: &Value,
    outcome: &Value,
) -> Result<Option<Value>, CoreError> {
    if !matches!(
        invocation["operation_id"].as_str(),
        Some("memory.capture-advisory" | "memory.recover-advisory")
    ) || outcome["status"] != "applied"
        || invocation["arguments"]["binding"]["disposition"] == "no-retention"
    {
        return Ok(None);
    }
    let Some(ids) = invocation["arguments"]["binding"]["candidate_ids"]
        .as_array()
        .filter(|ids| !ids.is_empty() && ids.len() <= COUNT)
    else {
        return Ok(None);
    };
    let Some(mut request) = candidates["requests"]
        .as_array()
        .into_iter()
        .flatten()
        .find(|r| r["arguments"]["operation"] == "read")
        .cloned()
    else {
        return Ok(None);
    };
    request["arguments"] = json!({"operation":"complete","candidate_ids":ids,
        "publication":{"source":outcome["value"]["source"],"revision":outcome["value"]["post_revision"]}});
    request["id"] = json!(format!("{REQUEST}:{}", digest(&request["arguments"])?));
    Ok(Some(request))
}

pub(crate) fn write_scope() -> Vec<String> {
    [STATE, PREPARED, LOCK]
        .into_iter()
        .map(str::to_owned)
        .chain([format!("{HOME}/state.tmp")])
        .collect()
}
pub(crate) fn execute(
    target: &Path,
    invocation: &Value,
    mut revalidate: impl FnMut() -> Result<(), CoreError>,
) -> Result<Value, CoreError> {
    execute_checked(target, invocation, &mut revalidate, &mut |_| Ok(()))
}
fn execute_checked(
    target: &Path,
    invocation: &Value,
    revalidate: &mut dyn FnMut() -> Result<(), CoreError>,
    observe: &mut dyn FnMut(&str) -> Result<(), CoreError>,
) -> Result<Value, CoreError> {
    let root = Dir::open_ambient_dir(target, ambient_authority()).map_err(err)?;
    read(&root, LOCK, 0)?;
    root.create_dir_all(HOME).map_err(err)?;
    read(&root, LOCK, 0)?;
    let lock = root
        .open_with(LOCK, OpenOptions::new().read(true).write(true).create(true))
        .map_err(err)?
        .into_std();
    lock.try_lock().map_err(err)?;
    revalidate()?;
    let binding = &invocation["arguments"]["binding"];
    let (state, before) = snapshot(&root)?;
    let prepared = pending(&root)?;
    if before != binding["before"] || json!(prepared) != binding["prepared"] {
        return Err(err("Candidate preimage drift; preserve concurrent work"));
    }
    validate(&binding["postimage"])?;
    if digest(&binding["postimage"])? != binding["post_revision"] {
        return Err(err("Candidate postimage changed"));
    }
    if prepared.is_none() {
        let record = json!({"kind":"agentic-memory/candidate-prepared/v1","before":before,"postimage":binding["postimage"],"post_revision":binding["post_revision"]});
        let bytes = serde_json::to_vec(&record).map_err(err)?;
        if bytes.len() > RESIDUE {
            return Err(err("Candidate recovery exceeds fixed bound"));
        }
        let mut f = root
            .open_with(PREPARED, OpenOptions::new().write(true).create_new(true))
            .map_err(err)?;
        f.write_all(&bytes).map_err(err)?;
        f.sync_all().map_err(err)?;
        observe("prepared")?;
    }
    // The recovery file is the complete postimage envelope. A separate fixed
    // state temporary is unnecessary: replace atomically using its payload in
    // the prepared file, keeping recovery until the replacement is confirmed.
    let temp = format!("{HOME}/state.tmp");
    read(&root, &temp, BYTES)?;
    if let Some(old) = read(&root, &temp, BYTES)? {
        if serde_json::from_slice::<Value>(&old).ok().as_ref() != Some(&binding["postimage"]) {
            return Err(err("Unknown candidate state temporary preserved"));
        }
    } else {
        let mut f = root
            .open_with(&temp, OpenOptions::new().write(true).create_new(true))
            .map_err(err)?;
        f.write_all(&serde_json::to_vec(&binding["postimage"]).map_err(err)?)
            .map_err(err)?;
        f.sync_all().map_err(err)?;
    }
    if state != binding["postimage"] {
        root.rename(&temp, &root, STATE).map_err(err)?;
    } else {
        root.remove_file(&temp).map_err(err)?;
    }
    observe("published")?;
    root.remove_file(PREPARED).map_err(err)?;
    Ok(
        json!({"post_effect_changed_paths":[STATE,PREPARED,LOCK,temp],"outcome":{"status":"applied","effects":["memory-state"],"value":{"kind":"agentic-memory/candidate-effect/v1",
        "post_revision":binding["post_revision"],"remaining":binding["postimage"]["candidates"].as_array().unwrap().len(),"authority":"none"}}}),
    )
}

#[cfg(test)]
mod tests {
    use super::*;
    struct Fixture(std::path::PathBuf);
    impl Fixture {
        fn new() -> Self {
            let path = std::env::temp_dir().join(format!(
                "aw-candidates-{}-{}",
                std::process::id(),
                SystemTime::now()
                    .duration_since(UNIX_EPOCH)
                    .unwrap()
                    .as_nanos()
            ));
            std::fs::create_dir_all(&path).unwrap();
            Self(path)
        }
    }
    impl Drop for Fixture {
        fn drop(&mut self) {
            let _ = std::fs::remove_dir_all(&self.0);
        }
    }
    #[test]
    fn carried_observation_detail_survives_clock_tick_with_current_sources() {
        let f = Fixture::new();
        let input = json!({"target":f.0,"task":"Investigate fixture setup","projection":"carried","material":[{"id":"setup-observation","kind":"observation","summary":"A fixture investigation found redundant service provisioning.","source":{"producer":"acting-agent","reference":"fixture:investigation","coverage":"bounded"}}]});
        let first = crate::operating::start(input.clone()).unwrap();
        std::thread::sleep(std::time::Duration::from_millis(1100));
        let expanded=crate::operating::start(json!({"request":first["carriage"],"reference":first["view"]["detail_refs"]["/memory"]})).unwrap();
        assert_eq!(expanded["currentness"], "reobserved");
        assert_eq!(
            expanded["value"]["candidates"]["requests"][0]["arguments"]["operation"],
            "consider"
        );
        assert!(!f.0.join(HOME).exists());
        // Changed ordinary material is a different source, even when its path
        // and task text remain unchanged. The old carriage doesn't grant access.
        let mut changed = input;
        changed["material"][0]["summary"] = json!("Current evidence changed.");
        changed["reference"] = first["view"]["detail_refs"]["/memory"].clone();
        assert!(crate::operating::start(changed).is_err());
    }
    #[test]
    fn ordinary_feedback_consolidates_then_subtracts_only_confirmed_material() {
        let f = Fixture::new();
        std::fs::write(
            f.0.join("service-policy.md"),
            "Use the shared fixture service; check its current status.",
        )
        .unwrap();
        let input = json!({"target":f.0,"task":"Investigate redundant fixture provisioning","material":[{"id":"fixture-discovery","kind":"observation",
            "summary":"Provisioning a second instance wasted work; the configured fixture service was already running.",
            "source":{"producer":"acting-agent","reference":"fixture:investigation","coverage":"bounded"}}]});
        let start = |input: &Value, request: Value| {
            let mut i = input.clone();
            i["request"] = request;
            crate::native_public::start(i).unwrap()
        };
        let invoke = |input: &Value, ready: &Value| {
            let mut i = input.clone();
            i["invocation"] = ready["decision_packet"]["primary_action"].clone();
            crate::native_public::invoke_checked(i).unwrap()
        };
        let initial = start(&input, Value::Null);
        let mut capture = initial["memory"]["candidates"]["requests"][0].clone();
        capture["arguments"]["operation"] = json!("capture");
        capture["arguments"]["optional"] = json!(true);
        capture["arguments"]["uncertainty"] =
            json!("One environment observation; check current runtime and policy before reuse.");
        capture["arguments"]["paths"] = json!(["tests/fixture/**"]);
        invoke(&input, &start(&input, capture));
        let ordinary = json!({"target":f.0,"task":"Prepare fixture checks","changed":["tests/fixture/check.rs"]});
        let selected = start(&ordinary, Value::Null);
        let request = selected["memory"]["candidates"]["requests"]
            .as_array()
            .unwrap()
            .iter()
            .find(|r| r["arguments"]["operation"] == "consolidate")
            .unwrap()
            .clone();
        let ids = request["arguments"]["candidate_ids"].clone();
        let before = std::fs::read(f.0.join(STATE)).unwrap();
        let mut deferred = request.clone();
        deferred["arguments"]["operation"] = json!("defer");
        assert_eq!(
            start(&ordinary, deferred)["memory"]["candidates"]["status"],
            "deferred"
        );
        assert_eq!(std::fs::read(f.0.join(STATE)).unwrap(), before);
        let mut consolidation = request;
        consolidation["arguments"]["advisory_material"] = json!({"id":"shared-fixture","lesson":"Read service-policy.md and inspect current service status before provisioning the shared fixture.","rationale":"Avoid the redundant provisioning found during setup; the earlier running observation is historical.","dependency_paths":["service-policy.md"],"routes_from":["tests/fixture/**"]});
        let considered = start(&ordinary, consolidation);
        let publication = considered["memory"]["candidates"]["publication_request"].clone();
        assert_eq!(publication["arguments"]["candidate_ids"], ids);
        let mut compact_input = ordinary.clone();
        compact_input["projection"] = json!("carried");
        let compact = crate::operating::start(compact_input).unwrap();
        let step = &compact["view"]["candidate_context"]["next_step"];
        assert_eq!(step["operation"], "consolidate");
        let considered = crate::operating::start(json!({"request":compact["carriage"],
            "reference":step["reference"],"answer":{"advisory_material":publication["arguments"]["material"]},"projection":"carried"})).unwrap();
        let step = &considered["view"]["candidate_context"]["next_step"];
        assert_eq!(step["operation"], "publish");
        let proposal = crate::operating::start(json!({"request":considered["carriage"],
            "reference":step["reference"],"answer":{},"projection":"carried"}))
        .unwrap();
        let ready = crate::operating::start(json!({"request":proposal["carriage"],
            "reference":proposal["view"]["decision_packet"]["decision_request"]["reference"],
            "answer":"confirm-retention","projection":"carried"}))
        .unwrap();
        let published = crate::operating::invoke(json!({"invocation":ready["carriage"],
            "reference":ready["view"]["decision_packet"]["primary_action"]["reference"],"projection":"carried"})).unwrap();
        assert_eq!(published["effect_outcome"]["status"], "committed");
        assert_eq!(
            std::fs::read(f.0.join(STATE)).unwrap(),
            before,
            "publication cannot prematurely drop candidates"
        );
        let step = &published["continuation"]["result"]["view"]["candidate_context"]["next_step"];
        assert_eq!(step["operation"], "complete");
        let mut completion_input = step["input"].clone();
        completion_input
            .as_object_mut()
            .unwrap()
            .remove("projection");
        assert_eq!(
            completion_input["request"]["arguments"]["candidate_ids"],
            ids
        );
        assert_eq!(
            completion_input["request"]["arguments"]["publication"]["revision"],
            published["value"]["post_revision"]
        );
        let mut invalid = completion_input.clone();
        invalid["request"]["arguments"]["publication"]["revision"] = json!("sha256:invented");
        assert!(crate::native_public::start(invalid).is_err());
        let mut stale = completion_input.clone();
        stale["task"] = json!("Different task");
        assert!(crate::native_public::start(stale).is_err());
        let ready = crate::native_public::start(completion_input).unwrap();
        let action = &ready["decision_packet"]["primary_action"];
        assert!(
            execute_checked(
                &f.0,
                action,
                &mut || Ok(()),
                &mut |stage| if stage == "prepared" {
                    Err(err("lost cleanup reply"))
                } else {
                    Ok(())
                }
            )
            .is_err()
        );
        let pending = start(&ordinary, Value::Null);
        let recovery = pending["memory"]["candidates"]["requests"]
            .as_array()
            .unwrap()
            .iter()
            .find(|r| r["arguments"]["operation"] == "recover")
            .unwrap()
            .clone();
        invoke(&ordinary, &start(&ordinary, recovery));
        let current = start(&ordinary, Value::Null);
        assert!(
            current["memory"]["candidates"]["selected"]
                .as_array()
                .unwrap()
                .is_empty()
        );
        assert!(
            current["memory"]["advisory_context"][0]["body"]
                .as_str()
                .unwrap()
                .contains("inspect current service status")
        );
        assert!(
            current["memory"]["advisory_context"][0]["body"]
                .as_str()
                .unwrap()
                .contains("fixture:investigation")
        );
        assert_eq!(std::fs::read_dir(f.0.join(HOME)).unwrap().count(), 2);
        // Actual contradiction arrives through the same ordinary material path,
        // with the affected note as its source. Another suite's different scope
        // must not get flattened into the fixture conclusion.
        for (id, summary, path) in [
            (
                "runtime-correction",
                "The shared fixture is stopped now; earlier availability cannot justify reuse without a current check.",
                "tests/fixture/**",
            ),
            (
                "isolated-observation",
                "The isolated migration suite needs a dedicated service.",
                "tests/migration/**",
            ),
        ] {
            let feedback = json!({"target":f.0,"task":"Investigate current fixture setup","material":[{"id":id,"kind":"observation","summary":summary,
                "source":{"producer":"acting-agent","reference":published["value"]["source"],"coverage":"bounded"}}]});
            let mut capture =
                start(&feedback, Value::Null)["memory"]["candidates"]["requests"][0].clone();
            capture["arguments"]["operation"] = json!("capture");
            capture["arguments"]["optional"] = json!(true);
            capture["arguments"]["uncertainty"] =
                json!("A scoped observation; runtime may change.");
            capture["arguments"]["paths"] = json!([path]);
            invoke(&feedback, &start(&feedback, capture));
        }
        let selected = start(&ordinary, Value::Null);
        assert_eq!(
            selected["memory"]["candidates"]["selected"]
                .as_array()
                .unwrap()
                .len(),
            1
        );
        let mut consolidate = selected["memory"]["candidates"]["requests"]
            .as_array()
            .unwrap()
            .iter()
            .find(|r| r["arguments"]["operation"] == "consolidate")
            .unwrap()
            .clone();
        let selected_ids = consolidate["arguments"]["candidate_ids"].clone();
        consolidate["arguments"]["advisory_material"] = json!({"id":"shared-fixture","lesson":"Read service-policy.md and inspect current service status: reuse the shared fixture if running; otherwise restart the configured instance.","rationale":"The current stopped observation corrected a stale runtime interpretation. Isolated migration setup remains separately scoped.","dependency_paths":["service-policy.md"],"routes_from":["tests/fixture/**"],"origins":[{"producer":"acting-agent","reference":"fixture:investigation","coverage":"bounded"}]});
        consolidate["arguments"]["revise_source"] = published["value"]["source"].clone();
        consolidate["arguments"]["source_revision"] = published["value"]["post_revision"].clone();
        let proposal = start(
            &ordinary,
            start(&ordinary, consolidate)["memory"]["candidates"]["publication_request"].clone(),
        );
        let mut answer =
            proposal["decision_packet"]["decision_request"]["response_request"].clone();
        answer["arguments"]["answer"] = json!("confirm-retention");
        let revised = invoke(&ordinary, &start(&ordinary, answer));
        assert_eq!(revised["value"]["source"], published["value"]["source"]);
        let current = start(&ordinary, Value::Null);
        let mut complete = current["memory"]["candidates"]["requests"]
            .as_array()
            .unwrap()
            .iter()
            .find(|r| r["arguments"]["operation"] == "read")
            .unwrap()
            .clone();
        complete["arguments"] = json!({"operation":"complete","candidate_ids":selected_ids,"publication":{"source":revised["value"]["source"],"revision":revised["value"]["post_revision"]}});
        invoke(&ordinary, &start(&ordinary, complete));
        let current = start(&ordinary, Value::Null);
        let body = current["memory"]["advisory_context"][0]["body"]
            .as_str()
            .unwrap();
        assert!(
            body.contains("otherwise restart the configured instance")
                && body.contains("fixture:investigation")
        );
        assert_eq!(
            std::fs::read_dir(f.0.join(".agentic-workspace/memory/repo/domains"))
                .unwrap()
                .count(),
            1
        );
        assert_eq!(
            std::fs::read_dir(f.0.join(".agentic-workspace/local/effects"))
                .unwrap()
                .count(),
            4
        );
        let remaining = snapshot(&Dir::open_ambient_dir(&f.0, ambient_authority()).unwrap())
            .unwrap()
            .0;
        assert_eq!(remaining["candidates"].as_array().unwrap().len(), 1);
        assert_eq!(
            remaining["candidates"][0]["material"]["id"],
            "isolated-observation"
        );
    }
    #[test]
    fn public_no_edit_finding_reaches_capture_and_fresh_scoped_consideration() {
        let f = Fixture::new();
        let task = "Investigate the fixture test setup";
        let input = json!({"target":f.0,"task":task,"material":[{"id":"setup-discovery","kind":"observation",
            "summary":"The fixture service already exists; provisioning another one wastes setup work.",
            "source":{"producer":"acting-agent","reference":"fixture:setup-inspection","coverage":"bounded"}}]});
        let initial = crate::native_public::start(input.clone()).unwrap();
        let mut request = initial["memory"]["candidates"]["requests"][0].clone();
        request["arguments"]["operation"] = json!("capture");
        request["arguments"]["optional"] = json!(true);
        request["arguments"]["uncertainty"] =
            json!("Historical local observation; future usefulness not settled.");
        request["arguments"]["paths"] = json!(["tests/fixture.rs"]);
        let mut proposed = input.clone();
        proposed["request"] = request;
        let ready = crate::native_public::start(proposed).unwrap();
        assert_eq!(
            ready["decision_packet"]["primary_action"]["operation_id"], OP,
            "{}",
            ready["decision_packet"]
        );
        let mut invoke = input;
        invoke["invocation"] = ready["decision_packet"]["primary_action"].clone();
        let applied = crate::native_public::invoke_checked(invoke).unwrap();
        assert_eq!(
            applied["effect_outcome"]["status"], "committed",
            "{applied}"
        );
        assert_eq!(applied["continuation_status"], "current", "{applied}");
        assert!(
            applied["continuation"]["context"]["changed"]
                .as_array()
                .unwrap()
                .contains(&json!(STATE))
        );
        let quiet = crate::native_public::start(
            json!({"target":f.0,"task":"Inspect unrelated documentation"}),
        )
        .unwrap();
        assert!(quiet["memory"].get("candidates").is_none());
        let fresh = crate::native_public::start(
            json!({"target":f.0,"task":"Change the fixture test", "changed":["tests/fixture.rs"]}),
        )
        .unwrap();
        assert_eq!(
            fresh["memory"]["candidates"]["selected"]
                .as_array()
                .unwrap()
                .len(),
            1
        );
        assert!(
            fresh["memory"]["candidates"]["selected"][0]["observation"]["material"]
                .get("work")
                .is_none()
        );
        let mut discard = fresh["memory"]["candidates"]["requests"]
            .as_array()
            .unwrap()
            .iter()
            .find(|r| r["arguments"]["operation"] == "discard")
            .unwrap()
            .clone();
        discard["arguments"]["reason"] =
            json!("One-off fixture observation; no future conclusion needed.");
        let ready = crate::native_public::start(json!({"target":f.0,"task":"Change the fixture test", "changed":["tests/fixture.rs"],"request":discard})).unwrap();
        let discarded = crate::native_public::invoke_checked(json!({"target":f.0,"task":"Change the fixture test", "changed":["tests/fixture.rs"],"invocation":ready["decision_packet"]["primary_action"]})).unwrap();
        assert_eq!(discarded["continuation_status"], "current", "{discarded}");
        assert!(
            snapshot(&Dir::open_ambient_dir(&f.0, ambient_authority()).unwrap())
                .unwrap()
                .0["candidates"]
                .as_array()
                .unwrap()
                .is_empty()
        );
    }
    #[test]
    fn ordinary_observation_lifecycle_is_bounded_passive_and_recoverable() {
        let f = Fixture::new();
        let work = json!({"kind":"current-work","id":"fixture"});
        let routes = json!({"status":"current","routes":["workspace/proof/selection"]});
        let contract =
            crate::native_memory::public_view(&f.0, &[], &Value::Null, &work, None, None, true)
                .unwrap()["capability_contract"]
                .clone();
        let config = json!({"revision":"fixture-policy"});
        let clock = 1_000_000;
        let input = |n| {
            json!({"id":format!("discovery-{n}"),"kind":"observation","summary":"The configured service is shared; provisioning another one failed and wasted setup work.",
            "source":{"producer":"acting-agent","reference":format!("fixture:repair-{n}"),"coverage":"bounded"}})
        };
        let resolve = |material: &Value, request: Option<&Value>, t| {
            view_at(
                &f.0,
                &work,
                material,
                &[],
                &routes,
                &config,
                &contract,
                &Value::Null,
                request,
                t,
            )
            .unwrap()
        };
        let action =
            |view: &Value| json!({"arguments":view["contribution"]["actions"][0]["arguments"]});
        let capture = |n, t| {
            let material = crate::native_material::view(&f.0, &work, &[input(n)]).unwrap();
            let mut request = resolve(&material, None, t)["requests"][0].clone();
            request["arguments"]["operation"] = json!("capture");
            request["arguments"]["optional"] = json!(true);
            request["arguments"]["uncertainty"] =
                json!("One local observation; reusable scope remains uncertain.");
            request["arguments"]["semantic_routes"] = json!(["workspace/proof/selection"]);
            let view = resolve(&material, Some(&request), t);
            (material, request, view)
        };
        let (material, request, ready) = capture(0, clock);
        assert!(!f.0.join(HOME).exists(), "nomination must be passive");
        execute(&f.0, &action(&ready), || Ok(())).unwrap();
        let before = std::fs::read(f.0.join(STATE)).unwrap();
        let root = Dir::open_ambient_dir(&f.0, ambient_authority()).unwrap();
        let state = snapshot(&root).unwrap().0;
        assert!(state["candidates"][0]["material"].get("work").is_none());
        let mut replay = resolve(&material, None, clock + 100)["requests"][0].clone();
        replay["arguments"] = request["arguments"].clone();
        assert_eq!(
            resolve(&material, Some(&replay), clock + 100)["status"],
            "already-considered"
        );
        assert_eq!(
            resolve(&json!({}), None, clock + 100)["selected"]
                .as_array()
                .unwrap()
                .len(),
            1
        );
        assert_eq!(std::fs::read(f.0.join(STATE)).unwrap(), before);
        for n in 1..20 {
            let (_, _, v) = capture(n, clock + n);
            execute(&f.0, &action(&v), || Ok(())).unwrap();
        }
        let state = snapshot(&root).unwrap().0;
        assert_eq!(state["candidates"].as_array().unwrap().len(), COUNT);
        assert!(read(&root, STATE, BYTES).unwrap().unwrap().len() <= BYTES);
        assert!(pending(&root).unwrap().is_none());
        let (_, _, v) = capture(21, clock + 21);
        assert!(
            execute_checked(
                &f.0,
                &action(&v),
                &mut || Ok(()),
                &mut |stage| if stage == "prepared" {
                    Err(err("interrupted"))
                } else {
                    Ok(())
                }
            )
            .is_err()
        );
        let mut recover = resolve(&json!({}), None, clock + 22)["requests"]
            .as_array()
            .unwrap()
            .iter()
            .find(|r| r["arguments"]["operation"] == "recover")
            .unwrap()
            .clone();
        let ready = resolve(&json!({}), Some(&recover), clock + 22);
        assert!(
            execute_checked(&f.0, &action(&ready), &mut || Ok(()), &mut |stage| if stage
                == "published"
            {
                Err(err("lost reply"))
            } else {
                Ok(())
            })
            .is_err()
        );
        recover = resolve(&json!({}), None, clock + 23)["requests"]
            .as_array()
            .unwrap()
            .iter()
            .find(|r| r["arguments"]["operation"] == "recover")
            .unwrap()
            .clone();
        execute(
            &f.0,
            &action(&resolve(&json!({}), Some(&recover), clock + 23)),
            || Ok(()),
        )
        .unwrap();
        assert!(pending(&root).unwrap().is_none());
        assert!(
            resolve(&json!({}), None, clock + AGE + 100)["selected"]
                .as_array()
                .unwrap()
                .is_empty()
        );
        let mut cleanup = resolve(&json!({}), None, clock + AGE + 100)["requests"][0].clone();
        cleanup["arguments"] = json!({"operation":"maintain"});
        execute(
            &f.0,
            &action(&resolve(&json!({}), Some(&cleanup), clock + AGE + 100)),
            || Ok(()),
        )
        .unwrap();
        assert!(
            snapshot(&root).unwrap().0["candidates"]
                .as_array()
                .unwrap()
                .is_empty()
        );
        assert_eq!(
            root.read_dir(HOME).unwrap().count(),
            2,
            "only state and empty lock remain"
        );
        // Exact-preimage checks reject another local writer, including recovery.
        let (_, _, v) = capture(22, clock + AGE + 101);
        let held = root.open(LOCK).unwrap().into_std();
        held.try_lock().unwrap();
        assert!(execute(&f.0, &action(&v), || Ok(())).is_err());
        drop(held);
        execute(&f.0, &action(&v), || Ok(())).unwrap();
        // The receiving owner has already made the actual correction. Its
        // current Verification evidence, not copied text, permits subtraction.
        std::fs::write(
            f.0.join("fixture-policy.md"),
            "Reuse the configured shared service after checking current status.",
        )
        .unwrap();
        let receiver = json!({"reference":"fixture-policy.md","revision":crate::decision_source::hash(&std::fs::read(f.0.join("fixture-policy.md")).unwrap())});
        let selected = resolve(&json!({}), None, clock + AGE + 102);
        let mut completion = selected["requests"][0].clone();
        completion["arguments"] = json!({"operation":"complete","candidate_ids":[selected["selected"][0]["observation"]["id"]],"receiving_source":receiver,
            "receiving_consequence":{"claim":"The current fixture policy avoids redundant provisioning.","evidence_reference":"proof:fixture-policy","proof_subject":"fixture:current"}});
        assert!(
            view_at(
                &f.0,
                &work,
                &json!({}),
                &[],
                &routes,
                &config,
                &contract,
                &Value::Null,
                Some(&completion),
                clock + AGE + 102
            )
            .is_err()
        );
        let proof = json!({"evidence":[{"reference":"proof:fixture-policy","proof_subject":"fixture:current","checked_scope":{"claim":"selected-command-passed","source_inputs":[{"path":"fixture-policy.md"}]}}]});
        let complete = view_at(
            &f.0,
            &work,
            &json!({}),
            &[],
            &routes,
            &config,
            &contract,
            &proof,
            Some(&completion),
            clock + AGE + 102,
        )
        .unwrap();
        std::fs::write(f.0.join("fixture-policy.md"), "Changed receiving source.").unwrap();
        assert!(
            view_at(
                &f.0,
                &work,
                &json!({}),
                &[],
                &routes,
                &config,
                &contract,
                &proof,
                Some(&completion),
                clock + AGE + 102
            )
            .is_err()
        );
        execute(&f.0, &action(&complete), || {
            Err(err("fresh receiving owner rejects drift"))
        })
        .unwrap_err();
        std::fs::write(
            f.0.join("fixture-policy.md"),
            "Reuse the configured shared service after checking current status.",
        )
        .unwrap();
        execute(&f.0, &action(&complete), || Ok(())).unwrap();
        assert!(
            snapshot(&root).unwrap().0["candidates"]
                .as_array()
                .unwrap()
                .is_empty()
        );
        std::fs::write(f.0.join(STATE), serde_json::to_vec(&state).unwrap()).unwrap();
        assert!(execute(&f.0, &action(&v), || Ok(())).is_err());
    }
}
