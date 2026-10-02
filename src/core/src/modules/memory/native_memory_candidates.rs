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
        "properties":{"operation":{"enum":["consider","capture","read","discard","maintain","recover"]},
            "material_revision":text,"candidate_ids":cues,"consequence":text,"uncertainty":text,
            "paths":cues,"semantic_routes":cues,"captured_at":{"type":"integer","minimum":0},
            "optional":{"const":true},"reason":text},"required":["operation"]}}));
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
        if ids.is_some_and(|ids| ids.contains(&row["id"]))
            || selectors(row, changed, routes)
            || args["operation"] == "read" && ids.is_none()
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
    }
    let Some(request) = request else {
        return Ok(result);
    };
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
        } else if args["operation"] == "discard" {
            let selected = ids
                .filter(|ids| !ids.is_empty())
                .ok_or_else(|| err("Discard requires exact candidate identities"))?;
            if args["reason"].as_str().is_none_or(|s| s.trim().is_empty()) {
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
    let binding = json!({"before":before,"postimage":post,"post_revision":digest(&post)?,"prepared":prepared});
    result["status"] = json!("write-ready");
    result["contribution"]["actions"] = json!([{"operation_id":OP,"dependency_revision":digest(&json!([binding,request]))?,
        "arguments":{"target":target,"request":request,"binding":binding},"effects":["memory-state"],"source_requests":[request]}]);
    Ok(result)
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
        json!({"outcome":{"status":"applied","effects":["memory-state"],"value":{"kind":"agentic-memory/candidate-effect/v1",
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
        crate::native_public::invoke_checked(json!({"target":f.0,"task":"Change the fixture test", "changed":["tests/fixture.rs"],"invocation":ready["decision_packet"]["primary_action"]})).unwrap();
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
        std::fs::write(f.0.join(STATE), serde_json::to_vec(&state).unwrap()).unwrap();
        assert!(execute(&f.0, &action(&v), || Ok(())).is_err());
    }
}
