//! Repository-owned standing assessments. Freshness is mechanical; satisfaction
//! remains an explicitly authorised semantic judgement, never command proof.
use crate::{CoreError, dependency_binding, digest};
use cap_std::{ambient_authority, fs::Dir};
use serde::Deserialize;
use serde_json::{Value, json};
use std::{
    collections::BTreeMap,
    path::Path,
    time::{SystemTime, UNIX_EPOCH},
};

pub(crate) const MANIFEST: &str = ".agentic-workspace/verification/manifest.toml";
pub(crate) const STATE: &str = ".agentic-workspace/proof/current/current-evidence.json";
pub(crate) const REQUEST: &str = "verification/assess-current-evidence/v1";
pub(crate) const RETIRE: &str = "verification/retire-current-evidence/v1";
pub(crate) const OP: &str = "verification.record-current-evidence";
pub(crate) const RECOVER: &str = "verification/recover-current-evidence/v1";
pub(crate) const RECOVERY: &str = "verification.recover-current-evidence";
const LOCK: &str = ".agentic-workspace/local/effects/current-evidence.lock";
const EFFECT: &str = "proof-execution";

fn err(value: impl ToString) -> CoreError {
    CoreError::new(value.to_string())
}
fn now() -> Result<u64, CoreError> {
    Ok(SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .map_err(err)?
        .as_secs())
}

// Freshness adds a repository procedure reference without narrowing the existing
// assurance detail route, which may name an owner route or command.
#[derive(Clone, Deserialize)]
#[serde(deny_unknown_fields)]
struct Freshness {
    procedure: String,
    max_age_seconds: u64,
    dependencies: Vec<String>,
    disposition: String,
}

fn bounded_text(value: &str) -> bool {
    !value.trim().is_empty() && value.len() <= 4096
}

fn declarations(root: &Dir) -> Result<BTreeMap<String, Value>, CoreError> {
    let Some(bytes) = crate::native_planning::read(root, MANIFEST)? else {
        return Ok(BTreeMap::new());
    };
    let manifest: toml::Value = toml::from_str(
        std::str::from_utf8(&bytes)
            .map_err(err)?
            .trim_start_matches('\u{feff}'),
    )
    .map_err(err)?;
    let manifest = serde_json::to_value(manifest).map_err(err)?;
    if manifest["schema_version"] != "agentic-workspace/verification-manifest/v1" {
        return Err(err("unsupported Verification manifest schema"));
    }
    let Some(assurance) = manifest.get("assurance") else {
        return Ok(BTreeMap::new());
    };
    let schema: Value =
        serde_json::from_str(include_str!("contracts/assurance.schema.json")).map_err(err)?;
    crate::schema_validator(&schema, "Verification assurance")?
        .validate(assurance)
        .map_err(err)?;
    let rows: BTreeMap<String, Value> = assurance["requirements"]
        .as_object()
        .into_iter()
        .flatten()
        .filter(|(_, row)| row.get("freshness").is_some())
        .map(|(id, row)| (id.clone(), row.clone()))
        .collect();
    if rows.len() > 32 {
        return Err(err("current evidence exceeds the 32-entry bound"));
    }
    for (id, row) in &rows {
        if id.is_empty()
            || id.len() > 64
            || !id
                .bytes()
                .all(|b| b.is_ascii_lowercase() || b.is_ascii_digit() || matches!(b, b'-' | b'_'))
        {
            return Err(err(
                "current evidence identity must be a short lowercase identifier",
            ));
        }
        let freshness: Freshness = serde_json::from_value(row["freshness"].clone()).map_err(err)?;
        if freshness.max_age_seconds == 0
            || freshness.max_age_seconds > 315_576_000
            || !matches!(freshness.disposition.as_str(), "report" | "route" | "work")
        {
            return Err(err("invalid current evidence freshness"));
        }
        let mut paths = freshness.dependencies;
        paths.push(freshness.procedure);
        for path in paths {
            crate::decision_source::relative(&path)?;
            if !bounded_text(&path)
                || path == STATE
                || path.starts_with(".agentic-workspace/local/")
            {
                return Err(err(
                    "current evidence dependencies and procedure must be repository-owned",
                ));
            }
        }
    }
    Ok(rows)
}

fn observe(root: &Dir, paths: impl IntoIterator<Item = String>) -> Result<Value, CoreError> {
    let mut values = serde_json::Map::new();
    for path in paths {
        crate::decision_source::relative(&path)?;
        let observed =
            dependency_binding::observe(root, &path, dependency_binding::Scheme::RawBytes);
        values.insert(path, serde_json::to_value(observed).map_err(err)?);
    }
    Ok(Value::Object(values))
}

fn present(values: &Value) -> bool {
    values
        .as_object()
        .is_some_and(|v| v.values().all(|o| o["status"] == "current"))
}

fn source_basis(root: &Dir, row: &Value) -> Result<Value, CoreError> {
    let declaration: Freshness = serde_json::from_value(row["freshness"].clone()).map_err(err)?;
    let mut dependencies = declaration.dependencies;
    dependencies.push(declaration.procedure);
    let source = row["source_intent_ref"].as_str().unwrap();
    if !source.contains("://") {
        dependencies.push(source.to_owned());
    }
    Ok(
        json!({"requirement":row,"dependencies":observe(root, dependencies)?,
        "producer":digest(&json!(["current-evidence/v1",include_str!("current_evidence.rs")]))?}),
    )
}

fn state(root: &Dir) -> Result<Value, CoreError> {
    let Some(value) = crate::current_projection::read(root, STATE)? else {
        return Ok(json!({"kind":"agentic-workspace/requirement-assessments/v1","assessments":{}}));
    };
    if value["kind"] != "agentic-workspace/requirement-assessments/v1"
        || value["assessments"]
            .as_object()
            .is_none_or(|rows| rows.len() > 32)
    {
        return Err(err(
            "standing assessment source is invalid; preserve it for owner repair",
        ));
    }
    Ok(value)
}

// Bind only authority applicable to this requirement and its exact evidence.
// Invocation admission still checks the complete live Configuration revision.
fn authority(configuration: &Value, basis: &Value, evidence: &Value) -> Value {
    let mut scope = vec![MANIFEST.to_owned()];
    scope.extend(
        basis["dependencies"]
            .as_object()
            .into_iter()
            .flatten()
            .map(|(p, _)| p.clone()),
    );
    scope.extend(
        evidence
            .as_object()
            .into_iter()
            .flatten()
            .map(|(p, _)| p.clone()),
    );
    scope.sort();
    scope.dedup();
    let mut value =
        crate::native_decision_authority::delegated(configuration, "verification", &scope)
            .unwrap_or_else(|| json!({"kind":"bounded-human-decision-required"}));
    value.as_object_mut().unwrap().remove("policy_revision");
    value
}

fn assessment_status(
    root: &Dir,
    row: &Value,
    record: &Value,
    policy: &Value,
    at: u64,
) -> Result<(&'static str, &'static str), CoreError> {
    if record.is_null() {
        return Ok(("due", "no-current-assessment"));
    }
    if record["revision"] != digest(&record["assessment"])? {
        return Ok(("unknown", "assessment-content-identity-mismatch"));
    }
    let value = &record["assessment"];
    if value["authority_basis"] != authority(policy, &value["basis"], &value["evidence"]) {
        return Ok(("due", "assessment-policy-changed"));
    }
    if value["basis"] != source_basis(root, row)? {
        return Ok(("due", "declaration-procedure-or-dependency-changed"));
    }
    if !present(&value["basis"]["dependencies"]) {
        return Ok(("unknown", "dependency-unavailable"));
    }
    let Some(recorded) = value["observed_at"].as_u64().filter(|time| *time <= at) else {
        return Ok(("unknown", "assessment-time-unavailable-or-future"));
    };
    if at - recorded >= row["freshness"]["max_age_seconds"].as_u64().unwrap() {
        return Ok(("due", "freshness-expired"));
    }
    match value["outcome"].as_str() {
        Some("failed") => return Ok(("due", "assessment-failed")),
        Some("unknown") => return Ok(("unknown", "assessment-unresolved")),
        Some("satisfied") => (),
        _ => return Ok(("unknown", "assessment-outcome-invalid")),
    }
    let Some(evidence) = value["evidence"].as_object() else {
        return Ok(("unknown", "evidence-unavailable"));
    };
    if evidence.is_empty() || evidence.len() > 6 {
        return Ok(("unknown", "evidence-unavailable"));
    }
    let current = observe(root, evidence.keys().cloned())?;
    if !present(&current) {
        return Ok(("unknown", "evidence-unavailable"));
    }
    if current != value["evidence"] {
        return Ok(("due", "evidence-changed"));
    }
    match value["outcome"].as_str() {
        Some("satisfied")
            if matches!(
                value["authorization"]["kind"].as_str(),
                Some("exact-bounded-human-answer" | "exact-policy-delegated-decision")
            ) =>
        {
            Ok(("satisfied", "current-authorised-assessment"))
        }
        Some("failed") => Ok(("due", "assessment-failed")),
        _ => Ok(("unknown", "assessment-unresolved")),
    }
}

// This is a source-owned semantic assessment, not an authenticated producer
// receipt. Consumers must not promote it into command proof or review approval.
fn inspect_at(target: &Path, policy: &Value, at: u64) -> Result<Value, CoreError> {
    let root = Dir::open_ambient_dir(target, ambient_authority()).map_err(err)?;
    let declarations = declarations(&root)?;
    let current = state(&root)?;
    let mut entries = Vec::new();
    for (id, row) in &declarations {
        let (status, reason) =
            assessment_status(&root, row, &current["assessments"][id], policy, at)?;
        entries.push(json!({"id":id,"status":status,"reason":reason,"declaration":row,
            "claim_boundary":"Recorded semantic assessment only; no command proof, independent review or execution authority."}));
    }
    let retired: Vec<_> = current["assessments"]
        .as_object()
        .unwrap()
        .keys()
        .filter(|id| !declarations.contains_key(*id))
        .cloned()
        .collect();
    Ok(
        json!({"entries":entries,"retired":retired,"state_revision":digest(&current)?,"authority_effect":"none"}),
    )
}

pub(crate) fn needs(
    view: &Value,
    work: &Value,
    configuration: &Value,
) -> Result<Vec<Value>, CoreError> {
    let latitude = configuration["improvement_latitude"]
        .as_str()
        .unwrap_or("conservative");
    view["entries"].as_array().into_iter().flatten()
        .filter(|entry| entry["status"] != "satisfied")
        .map(|entry| {
            let declared = entry["declaration"]["freshness"]["disposition"].as_str().unwrap();
            let disposition = match (latitude, declared) {
                ("none" | "reporting", _) | (_, "report") => "report",
                ("proactive", "work") => "work",
                _ => "route",
            };
            let id = entry["id"].as_str().unwrap();
            let material = json!({"id":format!("current-evidence:{id}"),"kind":"need",
                "summary":entry["declaration"]["notes"],"work":work,
                "source":{"producer":"verification","reference":format!("{MANIFEST}#assurance.requirements.{id}"),
                    "revision":view["revision"],"coverage":"bounded"}});
            Ok(json!({"material":material,"revision":digest(&json!([material,entry,disposition]))?,
                "trust":"repository-declaration-and-currentness-observation","currentness":entry["status"],
                "gap":entry["reason"],"disposition":disposition,"declared_disposition":declared,
                "procedure":{"resource":entry["declaration"]["freshness"]["procedure"],
                    "owner_reference":{"kind":"request","owner":"verification","id":if view["status"] == "publication-result-unresolved" { RECOVER.to_owned() } else { format!("current-evidence:{id}") }}},
                "evidence_requirement":entry["declaration"]["required_evidence"],
                "authority":"Current need only. Follow existing repository, issue or Planning ownership; no new issue, mutation, proof execution or completion is authorised by this observation."}))
        }).collect()
}

pub(crate) fn extend_contract(owner: &mut Value) -> Result<(), CoreError> {
    let text = json!({"type":"string","minLength":1,"maxLength":4096});
    owner["requests"].as_array_mut().unwrap().extend([
        json!({"kind":REQUEST,"result_kind":"agentic-workspace/current-evidence/v1","input_schema":{
            "type":"object","additionalProperties":false,"required":["id","source_revision"],"properties":{
            "id":{"type":"string","minLength":1,"maxLength":64},"source_revision":text,
            "observed_at":{"type":"integer","minimum":0},"outcome":{"enum":["satisfied","failed","unknown"]},
            "reason":text,"evidence_refs":{"type":"array","maxItems":6,"uniqueItems":true,"items":text},
            "proposal_revision":text,"answer":{"enum":["confirm","defer"]}}}}),
        json!({"kind":RETIRE,"result_kind":"agentic-workspace/current-evidence/v1","input_schema":{
            "type":"object","additionalProperties":false,"required":["source_revision"],"properties":{"source_revision":text}}}),
        json!({"kind":RECOVER,"result_kind":"agentic-workspace/current-evidence/v1","input_schema":{
            "type":"object","additionalProperties":false,"required":["source_revision"],"properties":{"source_revision":text}}}),
    ]);
    for op in [OP, RECOVERY] {
        owner["operations"].as_array_mut().unwrap().push(json!({"id":op,"semantic_revision":"current-evidence/v1",
            "input_schema":{"type":"object","additionalProperties":false,"required":["target","before","after","request","policy"],
                "properties":{"target":text,"before":text,"after":{"type":"object"},"request":{"type":"object"},"policy":text}},
            "result_kind":"agentic-workspace/current-evidence/v1","effects":[EFFECT],"reads":["verification"]}));
    }
    for field in ["requests", "operations"] {
        for declaration in owner[field].as_array_mut().unwrap().iter_mut().filter(|d| {
            matches!(d["kind"].as_str(), Some(REQUEST | RETIRE | RECOVER))
                || matches!(d["id"].as_str(), Some(OP | RECOVERY))
        }) {
            declaration["input_schema"]["$schema"] =
                json!("https://json-schema.org/draft/2020-12/schema");
        }
    }
    Ok(())
}

/// Attach the current result to the existing requirement and its evidence gap.
/// A standing assessment does not replace measurement or independent review.
pub(crate) fn compose(verification: &mut Value, current: &Value) {
    for entry in current["entries"].as_array().into_iter().flatten() {
        let id = entry["id"].as_str().unwrap();
        for row in verification["assurance_applicability"]["requirements"]
            .as_array_mut()
            .into_iter()
            .flatten()
        {
            if row["id"] == id {
                row["current_evidence"] = entry.clone();
            }
        }
        if entry["status"] != "satisfied" {
            continue;
        }
        let source = &entry["declaration"];
        let mut remaining = vec![];
        if source.get("measurement").is_some() {
            remaining.push("measurement-owner-result-unavailable");
        }
        if source.get("review_owner").is_some() {
            remaining.push("required-reviewer-result-not-admitted");
        }
        for gap in verification["assurance_owner_gaps"]
            .as_array_mut()
            .into_iter()
            .flatten()
        {
            if gap["requirement_id"] == id {
                gap["current_evidence"] = entry.clone();
                gap["missing_admissions"] = json!(remaining);
                gap["status"] = json!(if remaining.is_empty() {
                    "current-requirement-satisfied"
                } else {
                    "owner-evidence-not-admitted"
                });
            }
        }
        if remaining.is_empty()
            && let Some(blockers) = verification["contribution"]["blockers"].as_array_mut()
        {
            let prefix = format!("assurance:{id}:");
            blockers.retain(|b| !b["code"].as_str().is_some_and(|c| c.starts_with(&prefix)));
        }
    }
}

pub(crate) fn view(
    target: &Path,
    work: &Value,
    configuration: &Value,
    contract: &Value,
    request: Option<&Value>,
) -> Result<Value, CoreError> {
    let root = Dir::open_ambient_dir(target, ambient_authority()).map_err(err)?;
    let rows = declarations(&root)?;
    let current = state(&root)?;
    let mut bases = serde_json::Map::new();
    for (id, row) in &rows {
        bases.insert(id.clone(), source_basis(&root, row)?);
    }
    let revision = digest(
        &json!({"declarations":rows,"bases":bases,"state":current,"policy":configuration["revision"]}),
    )?;
    let owner = contract["owners"]
        .as_array()
        .unwrap()
        .iter()
        .find(|o| o["owner"] == "verification")
        .unwrap();
    let template = |id: &str, kind: &str, args: Value| {
        json!({"kind":"agentic-workspace/public-request/v1",
        "id":id,"owner":"verification","owner_revision":owner["revision"],"source_revision":revision,
        "capability_revision":contract["revision"],"task_identity":work,"request_kind":kind,"arguments":args})
    };
    let mut output = inspect_at(target, configuration, now()?)?;
    output["revision"] = json!(revision);
    output["requests"] = json!(
        rows.keys()
            .map(|id| template(
                &format!("current-evidence:{id}"),
                REQUEST,
                json!({"id":id,"source_revision":revision})
            ))
            .collect::<Vec<_>>()
    );
    output["decisions"] = json!([]);
    output["action"] = Value::Null;
    let retained = held(target, &digest(&current)?)?;
    let pending = retained.as_ref().is_some_and(|r| r["committed"] != true);
    if pending {
        output["requests"] = json!([template(
            RECOVER,
            RECOVER,
            json!({"source_revision":revision})
        )]);
        output["status"] = json!("publication-result-unresolved");
        for entry in output["entries"].as_array_mut().unwrap() {
            if entry["status"] == "satisfied" {
                entry["status"] = json!("unknown");
                entry["reason"] = json!("publication-result-unresolved");
            }
        }
    }
    if output["retired"].as_array().is_some_and(|v| !v.is_empty()) {
        output["requests"].as_array_mut().unwrap().push(template(
            RETIRE,
            RETIRE,
            json!({"source_revision":revision}),
        ));
    }
    let Some(request) = request else {
        return Ok(output);
    };
    crate::prepare_request_value(
        json!({"request":request,"current_work":work,"capability_contract":contract}),
    )?;
    if request["source_revision"] != revision || request["arguments"]["source_revision"] != revision
    {
        return Err(err(
            "standing obligation sources or current assessment changed; resolve a fresh request",
        ));
    }
    if pending {
        if request != &template(RECOVER, RECOVER, json!({"source_revision":revision})) {
            return Err(err(
                "recover the existing standing publication before another assessment",
            ));
        }
        let record = retained.as_ref().unwrap();
        let original = &record["invocation"]["arguments"];
        if original["policy"] != configuration["revision"] || original["after"] != current {
            return Err(err(
                "standing recovery policy or publication changed; preserve it",
            ));
        }
        if let Some(id) = original["request"]["arguments"]["id"].as_str() {
            let value = &current["assessments"][id]["assessment"];
            if !rows.contains_key(id) || value["basis"] != bases[id] {
                return Err(err("standing recovery dependency changed; preserve it"));
            }
            let evidence = value["evidence"]
                .as_object()
                .ok_or_else(|| err("standing recovery evidence invalid"))?;
            if observe(&root, evidence.keys().cloned())? != value["evidence"] {
                return Err(err("standing recovery evidence changed; preserve it"));
            }
        }
        output["action"] = json!({"operation_id":RECOVERY,"dependency_revision":digest(&json!([revision,request,record]))?,
            "arguments":{"target":target,"before":digest(&current)?,"after":current,"request":request,"policy":configuration["revision"]},
            "effects":[EFFECT],"source_requests":[request]});
        return Ok(output);
    }
    let mut after = current.clone();
    // This map belongs solely to Verification. Never remove referenced evidence.
    after["assessments"]
        .as_object_mut()
        .unwrap()
        .retain(|id, _| rows.contains_key(id));
    if request["request_kind"] == REQUEST {
        let id = request["arguments"]["id"].as_str().unwrap();
        let row = rows
            .get(id)
            .ok_or_else(|| err("standing obligation no longer declared"))?;
        let args = &request["arguments"];
        if args["outcome"].is_null() {
            output["status"] = json!("assessment-material-required");
            return Ok(output);
        }
        let at = now()?;
        let observed = args["observed_at"]
            .as_u64()
            .ok_or_else(|| err("assessment requires its observation time"))?;
        if observed > at || at - observed >= row["freshness"]["max_age_seconds"].as_u64().unwrap() {
            return Err(err("standing assessment observation is future or expired"));
        }
        let reason = args["reason"]
            .as_str()
            .filter(|s| bounded_text(s))
            .ok_or_else(|| err("assessment requires a bounded reason"))?;
        let refs: Vec<String> =
            serde_json::from_value(args["evidence_refs"].clone()).map_err(err)?;
        if refs
            .iter()
            .any(|p| p == STATE || p.starts_with(".agentic-workspace/local/"))
        {
            return Err(err(
                "standing evidence must be repository-owned and outside its own assessment source",
            ));
        }
        let evidence = observe(&root, refs.clone())?;
        if args["outcome"] == "satisfied"
            && (refs.is_empty() || !present(&evidence) || !present(&bases[id]["dependencies"]))
        {
            return Err(err(
                "satisfied assessment requires present current evidence, procedure and dependencies",
            ));
        }
        let assessment = json!({"basis":bases[id],"authority_basis":authority(configuration,&bases[id],&evidence),"observed_at":observed,"outcome":args["outcome"],"reason":reason,"evidence":evidence});
        let mut scope = vec![MANIFEST.to_owned()];
        scope.extend(
            bases[id]["dependencies"]
                .as_object()
                .unwrap()
                .keys()
                .cloned(),
        );
        scope.extend(refs);
        scope.sort();
        scope.dedup();
        let delegated =
            crate::native_decision_authority::delegated(configuration, "verification", &scope);
        let proposal = json!({"id":id,"assessment":assessment,"retired":output["retired"],"destination":STATE,
            "assessment_role":"untrusted-caller-proposal","identity_authentication":"not-claimed",
            "claim_boundary":"Authorise this bounded semantic assessment; no command proof, independent review or task completion."});
        let proposal_revision = digest(&proposal)?;
        let mut arguments = args.clone();
        arguments.as_object_mut().unwrap().remove("answer");
        arguments["proposal_revision"] = json!(proposal_revision);
        let decisions = json!([{"id":"current-evidence-assessment","question":"Publish this exact current-evidence assessment?",
            "material":proposal,"response_request":{"request_kind":REQUEST,"arguments":arguments},
            "choices":[{"id":"confirm","label":"Publish this assessment"},{"id":"defer","label":"Leave it unresolved"}],"affects":["effect:proof-execution"]}]);
        let mut authorised = request.clone();
        if args["answer"].is_null() {
            if delegated.is_none() {
                output["status"] = json!("bounded-answer-required");
                output["decisions"] = decisions;
                return Ok(output);
            }
            let compiled = crate::compile_value(
                json!({"intent":{"current_work":work},"capability_contract":contract,
                "contributions":[{"owner":"verification","revision":revision,"decisions":decisions}]}),
            )?;
            authorised =
                compiled["pending_consequences"]["decisions"][0]["response_request"].clone();
            authorised["arguments"]["answer"] = json!("confirm");
        } else {
            let compiled = crate::compile_value(
                json!({"intent":{"current_work":work},"capability_contract":contract,
                "contributions":[{"owner":"verification","revision":revision,"decisions":decisions}]}),
            )?;
            let mut exact =
                compiled["pending_consequences"]["decisions"][0]["response_request"].clone();
            exact["arguments"]["answer"] = args["answer"].clone();
            if exact != *request {
                return Err(err(
                    "standing assessment answer differs from the exact proposal",
                ));
            }
        }
        if authorised["arguments"]["answer"] == "defer" {
            output["status"] = json!("deferred");
            return Ok(output);
        }
        let mut assessment = assessment;
        assessment["authorization"] = delegated.unwrap_or_else(|| {
            json!({"kind":"exact-bounded-human-answer",
            "proposal_revision":proposal_revision,"identity_authentication":"not-claimed"})
        });
        after["assessments"][id] = json!({"revision":digest(&assessment)?,"assessment":assessment});
        if after == current {
            output["status"] = json!("current");
            return Ok(output);
        }
        output["authorised_request"] = authorised.clone();
        output["action"] = json!({"operation_id":OP,"dependency_revision":digest(&json!([revision,authorised,after]))?,
            "arguments":{"target":target,"before":digest(&current)?,"after":after,"request":authorised,"policy":configuration["revision"]},
            "effects":[EFFECT],"source_requests":[authorised]});
    } else if request["request_kind"] == RETIRE {
        if request != &template(RETIRE, RETIRE, json!({"source_revision":revision})) {
            return Err(err(
                "standing retirement request differs from the current owner request",
            ));
        }
        if after != current {
            output["action"] = json!({"operation_id":OP,"dependency_revision":digest(&json!([revision,request,after]))?,
                "arguments":{"target":target,"before":digest(&current)?,"after":after,"request":request,"policy":configuration["revision"]},
                "effects":[EFFECT],"source_requests":[request]});
        }
    } else {
        return Err(err("unsupported standing obligation request"));
    }
    output["status"] = json!(if output["action"].is_object() {
        "publication-required"
    } else {
        "current"
    });
    Ok(output)
}

fn marker(post: &str) -> Result<String, CoreError> {
    Ok(format!(
        ".agentic-workspace/local/effects/standing-{}.prepared.json",
        &digest(&json!([STATE, post]))?[7..]
    ))
}

fn outcome(invocation: &Value) -> Result<Value, CoreError> {
    Ok(json!({"status":"applied","effects":[EFFECT],"value":{
        "kind":"agentic-workspace/current-evidence/v1","source":STATE,
        "post_revision":digest(&invocation["arguments"]["after"])?,
        "completion_authority":false,"independent_review":false,"command_proof":false}}))
}

fn held(target: &Path, post: &str) -> Result<Option<Value>, CoreError> {
    let root = Dir::open_ambient_dir(target, ambient_authority()).map_err(err)?;
    let Some(mut record) = crate::current_projection::read(&root, &marker(post)?)? else {
        return Ok(None);
    };
    let invocation = &record["invocation"];
    let evidence = serde_json::from_value(record["custody"]["attempt"].clone()).map_err(err)?;
    let attempt = crate::attempt_store::read_source(target.to_str().unwrap(), &evidence)?;
    if attempt["invocation"] != *invocation
        || invocation["source_owner"] != "verification"
        || invocation["operation_id"] != OP
        || invocation["arguments"]["target"] != json!(target)
        || digest(&invocation["arguments"]["after"])? != post
        || record["outcome"] != outcome(invocation)?
    {
        return Err(err(
            "standing publication lacks exact attempt custody; preserve it",
        ));
    }
    let prepared = crate::attempt_store::prepare_commit(
        target.to_str().unwrap(),
        record["custody"].clone(),
        record["outcome"].clone(),
    )?;
    let result = prepared["custody"]["committed"]["path"].as_str().unwrap();
    let committed = if crate::native_planning::read(&root, result)?.is_some() {
        crate::attempt_store::inspect_committed(
            target.to_str().unwrap(),
            prepared["custody"].clone(),
        )?;
        true
    } else {
        false
    };
    record["committed"] = json!(committed);
    Ok(Some(record))
}

pub(crate) fn write_scope(action: &Value) -> Result<Vec<String>, CoreError> {
    let mut paths =
        crate::attempt_store::write_paths(&json!({"idempotency_key":action["logical_effect_id"]}))?;
    let path = marker(&digest(&action["arguments"]["after"])?)?;
    paths.extend([
        STATE.into(),
        format!("{STATE}.tmp"),
        path.clone(),
        format!("{path}.tmp"),
        LOCK.into(),
    ]);
    if action["operation_id"] == RECOVERY {
        let target = Path::new(action["arguments"]["target"].as_str().unwrap());
        let record = held(target, &digest(&action["arguments"]["after"])?)?
            .ok_or_else(|| err("standing recovery custody missing"))?;
        paths.extend(crate::attempt_store::write_paths(&record["invocation"])?);
    }
    Ok(paths)
}

pub(crate) fn execute(
    target: &Path,
    decision: &Value,
    invocation: &Value,
    mut revalidate: impl FnMut() -> Result<(), CoreError>,
) -> Result<Value, CoreError> {
    use cap_std::fs::OpenOptions;
    let root = Dir::open_ambient_dir(target, ambient_authority()).map_err(err)?;
    if serde_json::to_vec(invocation).map_err(err)?.len() > 100_000 {
        return Err(err("standing publication exceeds bounded recovery size"));
    }
    crate::native_planning::read(&root, LOCK)?;
    root.create_dir_all(".agentic-workspace/local/effects")
        .map_err(err)?;
    let lock = root
        .open_with(LOCK, OpenOptions::new().read(true).write(true).create(true))
        .map_err(err)?
        .into_std();
    if lock.metadata().map_err(err)?.len() != 0 {
        return Err(err("unowned standing lock preserved"));
    }
    lock.try_lock().map_err(err)?;
    revalidate()?;
    let args = &invocation["arguments"];
    let post = digest(&args["after"])?;
    let prior = held(target, &post)?;
    if invocation["operation_id"] == RECOVERY {
        let record = prior.ok_or_else(|| err("standing recovery custody missing"))?;
        if record["committed"] == true || state(&root)? != args["after"] {
            return Err(err(
                "standing recovery is no longer pending at this postimage",
            ));
        }
        let admission = crate::attempt_store::admit(
            json!({"target":target,"decision":decision,"invocation":invocation}),
        )?;
        revalidate()?;
        crate::attempt_store::commit(
            json!({"target":target,"custody":record["custody"],"outcome":record["outcome"]}),
        )?;
        let out = outcome(invocation)?;
        let committed = crate::attempt_store::commit(
            json!({"target":target,"custody":admission["custody"],"outcome":out}),
        )?;
        return Ok(json!({"outcome":out,"custody":committed["custody"]}));
    }
    if prior
        .as_ref()
        .is_some_and(|r| r["invocation"] != *invocation)
    {
        return Err(err("standing publication custody collision preserved"));
    }
    if digest(&state(&root)?)? != args["before"] {
        return Err(err("standing assessment changed before publication"));
    }
    let admission = crate::attempt_store::admit(
        json!({"target":target,"decision":decision,"invocation":invocation,
        "custody":prior.as_ref().map(|r| &r["custody"])}),
    )?;
    let out = outcome(invocation)?;
    if prior.is_none() {
        crate::current_projection::write(
            &root,
            &marker(&post)?,
            &json!({"invocation":invocation,"custody":admission["custody"],"outcome":out}),
        )?;
    }
    revalidate()?;
    if digest(&state(&root)?)? != args["before"] {
        return Err(err("standing assessment changed at publication barrier"));
    }
    crate::current_projection::write(&root, STATE, &args["after"])?;
    let committed = crate::attempt_store::commit(
        json!({"target":target,"custody":admission["custody"],"outcome":out}),
    )?;
    Ok(json!({"outcome":out,"custody":committed["custody"],"post_effect_changed_paths":[STATE]}))
}

#[cfg(test)]
mod tests {
    use super::*;

    struct Fixture(std::path::PathBuf);
    impl Fixture {
        fn new() -> Self {
            let path = std::env::temp_dir().join(format!(
                "aw-standing-{}-{}",
                std::process::id(),
                SystemTime::now()
                    .duration_since(UNIX_EPOCH)
                    .unwrap()
                    .as_nanos()
            ));
            std::fs::create_dir_all(path.join(".agentic-workspace/verification")).unwrap();
            let fixture = Self(path);
            fixture.write(MANIFEST, "schema_version = 'agentic-workspace/verification-manifest/v1'\n[assurance.requirements.docs]\nlevel = 'medium'\nforce = 'required-before-closeout'\nrequirement_class = 'current-evidence'\nsource_intent_ref = 'interface.json'\nsource_intent_revision = 'v1'\nevidence_owner = 'verification:docs'\nrequired_evidence = ['A recorded comparison of the example and interface']\nblocking_claims = ['claim-work-complete']\nnotes = 'The usage example follows the supported interface'\ndetail_route = 'measurement:latency'\n[assurance.requirements.docs.freshness]\nprocedure = 'procedure.md'\nmax_age_seconds = 3600\ndependencies = ['interface.json']\ndisposition = 'route'\n");
            fixture.write(
                "procedure.md",
                "Compare the usage example against the interface.",
            );
            fixture.write("interface.json", "{}");
            fixture.write(
                "evidence.md",
                "Compared the current example and interface; no mismatch.",
            );
            fixture
        }
        fn write(&self, path: &str, text: &str) {
            std::fs::write(self.0.join(path), text).unwrap();
        }
        fn root(&self) -> Dir {
            Dir::open_ambient_dir(&self.0, ambient_authority()).unwrap()
        }
    }
    impl Drop for Fixture {
        fn drop(&mut self) {
            std::fs::remove_dir_all(&self.0).unwrap();
        }
    }

    fn record(root: &Dir, row: &Value) -> Value {
        let assessment = json!({"basis":source_basis(root,row).unwrap(),"authority_basis":authority(&json!({}),&source_basis(root,row).unwrap(),&observe(root,["evidence.md".into()]).unwrap()),"observed_at":100,
            "outcome":"satisfied","reason":"Compared the declared sources.","evidence":observe(root,["evidence.md".into()]).unwrap(),
            "authorization":{"kind":"exact-bounded-human-answer","proposal_revision":"accepted"}});
        json!({"revision":digest(&assessment).unwrap(),"assessment":assessment})
    }

    #[test]
    fn ordinary_needs_respect_latitude_and_quiet_controls() {
        let f = Fixture::new();
        let work = json!({"kind":"current-work","id":"entry-test"});
        let config = json!({"revision":"policy-v1"});
        let contract = crate::native_verification::contract().unwrap();
        let initial = view(&f.0, &work, &config, &contract, None).unwrap();
        for (latitude, wanted, expected) in [
            ("none", "work", "report"),
            ("reporting", "work", "report"),
            ("conservative", "work", "route"),
            ("proactive", "work", "work"),
            ("proactive", "report", "report"),
            ("proactive", "route", "route"),
        ] {
            let mut observed = initial.clone();
            observed["entries"][0]["declaration"]["freshness"]["disposition"] = json!(wanted);
            let current =
                needs(&observed, &work, &json!({"improvement_latitude":latitude})).unwrap();
            assert_eq!(current[0]["disposition"], expected);
            assert_eq!(current[0]["procedure"]["resource"], "procedure.md");
            observed["entries"][0]["status"] = json!("satisfied");
            assert!(needs(&observed, &work, &config).unwrap().is_empty());
        }
        f.write(
            MANIFEST,
            "schema_version = 'agentic-workspace/verification-manifest/v1'\n",
        );
        crate::native_planning::TEST_READS.with(|reads| reads.borrow_mut().clear());
        let empty = view(&f.0, &work, &config, &contract, None).unwrap();
        assert!(needs(&empty, &work, &config).unwrap().is_empty());
        let before = crate::native_planning::TEST_READS.with(|reads| reads.borrow().clone());
        for n in 0..200 {
            f.write(&format!("unrelated-{n}.md"), "An unrelated source.");
        }
        crate::native_planning::TEST_READS.with(|reads| reads.borrow_mut().clear());
        view(&f.0, &work, &config, &contract, None).unwrap();
        assert_eq!(
            crate::native_planning::TEST_READS.with(|reads| reads.borrow().clone()),
            before
        );
        assert!(
            !before
                .iter()
                .any(|path| path.contains("procedure.md") || path.contains("interface.json"))
        );
    }

    #[test]
    fn currentness_distinguishes_age_change_failure_and_missing_evidence() {
        let f = Fixture::new();
        let root = f.root();
        let row = declarations(&root).unwrap()["docs"].clone();
        let accepted = record(&root, &row);
        let policy = json!({"revision":"policy-v1"});
        let status =
            |record: &Value, at| assessment_status(&root, &row, record, &policy, at).unwrap();
        assert_eq!(status(&Value::Null, 100), ("due", "no-current-assessment"));
        assert_eq!(
            status(&accepted, 100),
            ("satisfied", "current-authorised-assessment")
        );
        f.write("unrelated.md", "An unrelated task changed this source.");
        assert_eq!(status(&accepted, 101).0, "satisfied");
        assert_eq!(status(&accepted, 99).0, "unknown");
        assert_eq!(status(&accepted, 3700), ("due", "freshness-expired"));
        assert_eq!(
            assessment_status(
                &root,
                &row,
                &accepted,
                &json!({"revision":"policy-v2"}),
                101
            )
            .unwrap()
            .1,
            "current-authorised-assessment"
        );
        let delegated = json!({"revision":"policy-v2","admissions":{"decision_delegations":[{
            "owner":"verification","scope":[format!("path:{MANIFEST}"),"path:procedure.md","path:interface.json","path:evidence.md"]}]}});
        assert_eq!(
            assessment_status(&root, &row, &accepted, &delegated, 101)
                .unwrap()
                .1,
            "assessment-policy-changed"
        );
        let unrelated = json!({"revision":"policy-v2","admissions":{"decision_delegations":[{
            "owner":"verification","scope":["path:unrelated.md"]}]}});
        assert_eq!(
            assessment_status(&root, &row, &accepted, &unrelated, 101)
                .unwrap()
                .0,
            "satisfied"
        );
        let mut changed_requirement = row.clone();
        changed_requirement["source_intent_revision"] = json!("v2");
        assert_eq!(
            assessment_status(&root, &changed_requirement, &accepted, &policy, 101)
                .unwrap()
                .0,
            "due"
        );
        let mut obsolete = accepted["assessment"].clone();
        obsolete["basis"]["producer"] = json!("old-producer");
        assert_eq!(
            status(
                &json!({"revision":digest(&obsolete).unwrap(),"assessment":obsolete}),
                101
            )
            .0,
            "due"
        );
        let mut unadmitted = accepted["assessment"].clone();
        unadmitted["authorization"] = json!({"kind":"caller-label","exit_code":0});
        assert_eq!(
            status(
                &json!({"revision":digest(&unadmitted).unwrap(),"assessment":unadmitted}),
                101
            )
            .0,
            "unknown"
        );
        f.write("evidence.md", "New comparison requires a new assessment.");
        assert_eq!(status(&accepted, 101), ("due", "evidence-changed"));
        std::fs::remove_file(f.0.join("evidence.md")).unwrap();
        assert_eq!(status(&accepted, 101), ("unknown", "evidence-unavailable"));
        for (outcome, expected) in [("failed", "due"), ("unknown", "unknown")] {
            let mut value = accepted["assessment"].clone();
            value["outcome"] = json!(outcome);
            value["evidence"] = json!({});
            assert_eq!(
                status(
                    &json!({"revision":digest(&value).unwrap(),"assessment":value}),
                    101
                )
                .0,
                expected
            );
        }
        f.write("interface.json", "{\"new\":true}");
        assert_eq!(
            status(&accepted, 101).1,
            "declaration-procedure-or-dependency-changed"
        );
    }

    #[test]
    fn declaration_rejects_ambiguous_or_unbounded_sources() {
        let f = Fixture::new();
        let original = std::fs::read_to_string(f.0.join(MANIFEST)).unwrap();
        for invalid in [
            original.replace("3600", "0"),
            original.replace("3600", "315576001"),
            original.replace("procedure.md", "../escape.md"),
            original.replace("procedure.md", ".agentic-workspace/local/private.md"),
            original.replace("procedure.md", STATE),
            original.replace("procedure.md", "measurement:latency"),
            original.replace("procedure = 'procedure.md'\n", ""),
            original.replace("['interface.json']", "['interface.json', 'interface.json']"),
            original.replace("assurance.requirements.docs", "assurance.requirements.Docs"),
            format!("{original}unexpected = true\n"),
        ] {
            f.write(MANIFEST, &invalid);
            assert!(declarations(&f.root()).is_err(), "{invalid}");
        }
    }

    #[test]
    fn assessment_requires_exact_authority_and_rejects_stale_sources() {
        let f = Fixture::new();
        let work = json!({"kind":"current-work","id":"standing-test"});
        let config = json!({"revision":"policy-v1"});
        let contract = crate::native_verification::contract().unwrap();
        let initial = view(&f.0, &work, &config, &contract, None).unwrap();
        let mut request = initial["requests"][0].clone();
        request["arguments"]["observed_at"] = json!(now().unwrap());
        request["arguments"]["outcome"] = json!("satisfied");
        request["arguments"]["reason"] = json!("Compared the declared sources.");
        request["arguments"]["evidence_refs"] = json!(["evidence.md"]);
        let proposed = view(&f.0, &work, &config, &contract, Some(&request)).unwrap();
        assert!(proposed["action"].is_null());
        assert_eq!(proposed["decisions"].as_array().unwrap().len(), 1);
        let mut forged = request.clone();
        forged["arguments"]["answer"] = json!("confirm");
        assert!(view(&f.0, &work, &config, &contract, Some(&forged)).is_err());
        let compiled=crate::compile_value(json!({"intent":{"current_work":work},"capability_contract":contract,
            "contributions":[{"owner":"verification","revision":proposed["revision"],"decisions":proposed["decisions"]}]})).unwrap();
        let mut answer =
            compiled["pending_consequences"]["decisions"][0]["response_request"].clone();
        answer["arguments"]["answer"] = json!("confirm");
        let ready = view(&f.0, &work, &config, &contract, Some(&answer)).unwrap();
        assert_eq!(ready["action"]["operation_id"], OP);
        let mut delegated_config = config.clone();
        delegated_config["admissions"] = json!({"decision_delegations":[{"owner":"verification","scope":[
            format!("path:{MANIFEST}"),"path:procedure.md","path:interface.json","path:evidence.md"]}]});
        let delegated = view(&f.0, &work, &delegated_config, &contract, Some(&request)).unwrap();
        assert_eq!(
            delegated["action"]["arguments"]["after"]["assessments"]["docs"]["assessment"]["authorization"]
                ["kind"],
            "exact-policy-delegated-decision"
        );
        let carried = &delegated["action"]["source_requests"][0];
        assert_eq!(
            view(&f.0, &work, &delegated_config, &contract, Some(carried)).unwrap()["action"],
            delegated["action"]
        );
        delegated_config["admissions"]["decision_delegations"][0]["scope"] = json!(["path:*"]);
        assert!(
            view(&f.0, &work, &delegated_config, &contract, Some(&request)).unwrap()["action"]
                .is_null()
        );
        let next = ready["action"]["arguments"]["after"].clone();
        assert_eq!(next["assessments"].as_object().unwrap().len(), 1);
        f.write("procedure.md", "Changed procedure.");
        assert!(view(&f.0, &work, &config, &contract, Some(&answer)).is_err());
    }
}
