//! Configuration's current setup judgment, using the existing source writer and
//! dependency comparison. This is neither feature activation nor domain evidence.
use crate::{CoreError, dependency_binding as deps, digest};
use cap_std::{ambient_authority, fs::Dir};
use serde_json::{Value, json};
use std::path::Path;

pub(crate) const READ: &str = "configuration/read-setup-assessment/v1";
pub(crate) const KEY: &str = "package.setup-assessment";
pub(crate) const SHARED: &str = ".agentic-workspace/configuration-assessment.json";
pub(crate) const LOCAL: &str = ".agentic-workspace/local/configuration-assessment.json";
const KIND: &str = "agentic-workspace/configuration-assessment/v1";
fn err(e: impl ToString) -> CoreError {
    CoreError::new(e.to_string())
}
pub(crate) fn is_source(s: &str) -> bool {
    [SHARED, LOCAL].contains(&s)
}
fn version() -> &'static str {
    env!("CARGO_PKG_VERSION")
}
fn version_tuple(s: &str) -> Option<Vec<u64>> {
    let s = s.split('+').next()?;
    let (base, prerelease) = s
        .split_once("-rc.")
        .or_else(|| s.split_once("rc"))
        .map(|(base, rc)| (base, Some(rc)))
        .unwrap_or((s, None));
    let mut value = base
        .split('.')
        .map(str::parse)
        .collect::<Result<Vec<_>, _>>()
        .ok()
        .filter(|v| v.len() == 3)?;
    value.extend(match prerelease {
        Some(rc) => [0, rc.parse().ok()?],
        None => [1, 0],
    });
    Some(value)
}
fn material() -> Result<Value, CoreError> {
    #[cfg(test)]
    crate::native_frontier::built("setup-material");
    let mut files = serde_json::Map::new();
    for path in crate::native_payload::paths()
        .into_iter()
        .filter(|p| p.starts_with(".agentic-workspace/skills/workspace-setup-jumpstart/"))
    {
        files.insert(
            path.into(),
            json!(String::from_utf8(crate::native_payload::shipped(path)?).map_err(err)?),
        );
    }
    // Existing declarations, not another capability roster or release ledger.
    files.insert(
        "workspace_config.schema.json".into(),
        json!(
            include_str!("../contracts/schemas/workspace_config.schema.json").replace("\r\n", "\n")
        ),
    );
    files.insert(
        "workspace_local_override.schema.json".into(),
        json!(
            include_str!("../contracts/schemas/workspace_local_override.schema.json")
                .replace("\r\n", "\n")
        ),
    );
    Ok(Value::Object(files))
}
// Bump only when repository setup needs reconsideration, including same-version
// development changes. Cosmetic/package-only changes use PAYLOAD_REVISION instead.
fn basis() -> &'static str {
    "configuration-setup-v2"
}
// Configuration can settle consideration without acquiring another owner's
// readiness authority. This is a disposition in the existing assessment, not
// another evidence store or a substitute for that owner's admission.
fn owner_managed(concern: &str) -> bool {
    matches!(
        concern,
        "diagnostics" | "assignment" | "modules" | "invocation"
    )
}
fn effective(concern: &str) -> bool {
    matches!(concern, "instructions" | "preferences")
}
pub(crate) fn settlement(concern: &str) -> Value {
    let boundary = match concern {
        "instructions" => {
            "Effectiveness means the selected startup source was delivered by the startup adapter."
        }
        "preferences" => {
            "Repository effectiveness covers the shared improvement preference only. Machine-local effectiveness covers the effective clarification and improvement preferences. Witnesses are scope-bound; neither grants effect authorization."
        }
        "diagnostics" => {
            "Actual capture belongs to the session-logging transport on this machine and target. Configuration assessment certifies neither capture nor diagnostic readiness, in either scope."
        }
        "assignment" => {
            "Task-specific feasibility, selection and result admission belong to current Assignment requirements and admission. Configuration assessment certifies none of those outcomes."
        }
        "modules" => {
            "Readiness belongs to each enabled module's current setup, state and admission. Configuration assessment does not certify modules from enablement or replace their owner evidence."
        }
        "invocation" => {
            "Assess repository invocation configuration against intent. Launch readiness belongs to actual execution on the target machine; saved command text and the running AW process prove no configured launch. Configuration assessment certifies no launch in either scope."
        }
        _ => "Unsupported concern.",
    };
    json!({"effective_supported":effective(concern),"terminal_disposition":if owner_managed(concern){"owner-managed"}else{"effective"},"boundary":boundary})
}
fn valid_settlement(row: &Value) -> bool {
    let concern = row["concern"].as_str().unwrap_or("");
    match row["status"].as_str() {
        Some("effective" | "already-effective") => {
            effective(concern) && row["observation"].is_object()
        }
        Some("owner-managed") => owner_managed(concern) && row.get("observation").is_none(),
        Some("irrelevant" | "excluded" | "pending" | "deferred" | "blocked" | "unavailable") => {
            true
        }
        _ => false,
    }
}
pub(crate) fn declaration() -> Value {
    json!({"kind":READ,"result_kind":KIND,"input_schema":{"$schema":"https://json-schema.org/draft/2020-12/schema","type":"object","additionalProperties":false,"properties":{"scope":{"enum":["repository","machine-local"]},"reconsider":{"type":"boolean"},"dependencies":{"type":"array","maxItems":64,"uniqueItems":true,"items":{"type":"string","maxLength":4096}}}}})
}
fn read(root: &Dir, source: &str) -> Result<Option<Value>, CoreError> {
    Ok(deps::read(root, source)?
        .map(|b| serde_json::from_slice(&b).unwrap_or(json!({"kind":"unrecognized-preserved"}))))
}
fn references(root: &Dir, scope: &str, extra: &[String]) -> Result<Vec<String>, CoreError> {
    // Configuration and explicitly declared governing sources are mechanical
    // dependencies. Other repository sources belong here only when the agent
    // selected them as inputs to its judgment, not merely because they exist.
    let mut paths = vec![".agentic-workspace/config.toml".to_owned()];
    if scope == "machine-local" {
        paths.push(".agentic-workspace/config.local.toml".into());
    }
    for source in [
        ".agentic-workspace/config.toml",
        if scope == "machine-local" {
            ".agentic-workspace/config.local.toml"
        } else {
            ".agentic-workspace/config.toml"
        },
    ] {
        if let Some(bytes) = deps::read(root, source)? {
            let config: toml::Value =
                toml::from_str(std::str::from_utf8(&bytes).map_err(err)?).map_err(err)?;
            if let Some(path) = config
                .get("workspace")
                .and_then(|v| v.get("agent_instructions_file"))
                .and_then(toml::Value::as_str)
            {
                paths.push(path.into());
            }
            if let Some(sources) = config
                .get("system_intent")
                .and_then(|v| v.get("sources"))
                .and_then(toml::Value::as_array)
            {
                paths.extend(
                    sources
                        .iter()
                        .filter_map(toml::Value::as_str)
                        .map(str::to_owned),
                );
            }
        }
    }
    paths.extend(extra.iter().cloned());
    paths.sort();
    paths.dedup();
    if paths.len() > 128 {
        return Err(err("setup dependency selection exceeds bounded review"));
    }
    for p in &paths {
        if p.is_empty()
            || p.contains('\\')
            || Path::new(p).is_absolute()
            || p.split('/').any(|v| v == ".." || v == ".")
            || is_source(p)
            || (scope == "repository"
                && (p.contains("/local/") || p.ends_with("config.local.toml")))
        {
            return Err(err(
                "setup dependency must be a confined source in the assessment scope",
            ));
        }
    }
    Ok(paths)
}
fn observe(root: &Dir, paths: &[String]) -> Result<Vec<deps::Observation>, CoreError> {
    paths
        .iter()
        .map(|p| {
            // An absent optional source is a known source state; unreadability is not.
            let bytes = deps::read(root, p)?;
            Ok(deps::Observation {
                identity: p.clone(),
                scheme: deps::Scheme::UniversalNewlineUtf8,
                revision: Some(digest(
                    &bytes
                        .as_ref()
                        .map(|b| deps::revision(b, deps::Scheme::UniversalNewlineUtf8))
                        .transpose()?,
                )?),
                status: deps::Currentness::Current,
            })
        })
        .collect()
}
fn dependencies(
    root: &Dir,
    scope: &str,
    extra: &Value,
) -> Result<Vec<deps::Observation>, CoreError> {
    let extra: Vec<String> = serde_json::from_value(extra.clone()).map_err(err)?;
    observe(root, &references(root, scope, &extra)?)
}
fn compatibility(record: &Value) -> &'static str {
    if record.is_null() {
        return "compatible";
    }
    if record["kind"] != KIND {
        return "unavailable";
    }
    match (
        record["runtime_version"].as_str().and_then(version_tuple),
        version_tuple(version()),
    ) {
        (Some(old), Some(now)) if old[0] != now[0] => "major-transition",
        (Some(old), Some(now)) if old > now => "newer-integration-preserved",
        (Some(_), Some(_)) => "compatible",
        _ => "unavailable",
    }
}
fn transition(root: &Dir, record: &Value) -> Result<&'static str, CoreError> {
    let accepted = compatibility(record);
    if accepted != "compatible" {
        return Ok(accepted);
    }
    let installed =
        read(root, ".agentic-workspace/payload-provenance.json")?.unwrap_or(Value::Null);
    if installed.is_null() {
        return Ok(accepted);
    }
    Ok(compatibility(
        &json!({"kind":KIND,"runtime_version":installed["release_identity"]["version"]}),
    ))
}
pub(crate) fn admit_maintenance(target: &Path) -> Result<(), CoreError> {
    let root = Dir::open_ambient_dir(target, ambient_authority()).map_err(err)?;
    for source in [SHARED, LOCAL] {
        let status = transition(&root, &read(&root, source)?.unwrap_or(Value::Null))?;
        if status != "compatible" {
            return Err(err(format!(
                "{status}: preserve package integration; current Configuration migration judgment is required"
            )));
        }
    }
    Ok(())
}
pub(crate) fn view(
    target: &Path,
    config: &Value,
    request: Option<&Value>,
    template: &dyn Fn(&str, Value) -> Value,
    result: &mut Value,
) -> Result<(), CoreError> {
    if let Err(error) = view_inner(target, config, request, template, result) {
        if request.is_some_and(|r| r["request_kind"] == READ) {
            return Err(error);
        }
        result["setup_assessment"] = json!({"status":"unavailable","reason":error.to_string(),"integration_complete":false,"request":template(READ,json!({"scope":"repository"}))});
        restrict(result);
    }
    Ok(())
}
pub(crate) fn restrict(result: &mut Value) {
    let mut blockers = result["contribution"]["blockers"]
        .as_array()
        .cloned()
        .unwrap_or_default();
    if !blockers
        .iter()
        .any(|b| b["code"] == "configuration-assessment-required")
    {
        blockers.push(json!({"code":"configuration-assessment-required","message":"Current package setup needs Configuration assessment. Read its exact current material, integrate useful authorized capabilities and verify their consumers; preserve unresolved choices and the original task.","affects":["claim:configuration-integration-complete"]}));
    }
    result["contribution"]["blockers"] = json!(blockers);
}
fn view_inner(
    target: &Path,
    config: &Value,
    request: Option<&Value>,
    template: &dyn Fn(&str, Value) -> Value,
    result: &mut Value,
) -> Result<(), CoreError> {
    let root = Dir::open_ambient_dir(target, ambient_authority()).map_err(err)?;
    if config["enabled"] == false {
        return Ok(());
    }
    if deps::read(&root, ".agentic-workspace/config.toml")?.is_none()
        && deps::read(&root, ".agentic-workspace/payload-provenance.json")?.is_none()
    {
        return Ok(());
    }
    let selected = request.is_some_and(|r| r["request_kind"] == READ);
    let scope = request
        .and_then(|r| r["arguments"]["scope"].as_str())
        .unwrap_or("repository");
    let source = if scope == "machine-local" {
        LOCAL
    } else {
        SHARED
    };
    let record = read(&root, source)?.unwrap_or(Value::Null);
    let compatibility = transition(&root, &record)?;
    let extra = if selected && request.unwrap()["arguments"]["dependencies"].is_array() {
        request.unwrap()["arguments"]["dependencies"].clone()
    } else {
        record
            .get("selected_dependencies")
            .cloned()
            .unwrap_or(json!([]))
    };
    let observed = dependencies(&root, scope, &extra)?;
    let setup = basis();
    let accepted: Option<Vec<deps::Observation>> = record
        .get("dependencies")
        .cloned()
        .map(serde_json::from_value)
        .transpose()
        .map_err(err)?;
    let comparison = deps::compare(
        deps::Basis {
            conclusion: &json!(setup),
            dependencies: &observed,
        },
        accepted.as_ref().map(|d| deps::Basis {
            conclusion: &record["basis"],
            dependencies: d,
        }),
    );
    let reviewed = compatibility == "compatible"
        && !request.is_some_and(|r| selected && r["arguments"]["reconsider"] == true)
        && record["scope"] == scope
        && record["coverage"]
            .as_str()
            .is_some_and(|s| !s.trim().is_empty())
        && comparison.status == deps::Currentness::Current
        && record["dispositions"].as_array().is_some_and(|rows| {
            !rows.is_empty()
                && rows.iter().all(|r| {
                    ["subject", "reason"]
                        .iter()
                        .all(|k| r[k].as_str().is_some_and(|s| !s.trim().is_empty()))
                        && valid_settlement(r)
                })
        });
    let settled = reviewed
        && record["dispositions"].as_array().is_some_and(|rows| {
            rows.iter().all(|r| {
                matches!(
                    r["status"].as_str(),
                    Some(
                        "effective"
                            | "already-effective"
                            | "owner-managed"
                            | "irrelevant"
                            | "excluded"
                    )
                )
            })
        });
    let status = if compatibility != "compatible" {
        compatibility
    } else if settled {
        "settled"
    } else if comparison.status == deps::Currentness::Current {
        "unfinished"
    } else {
        "assessment-required"
    };
    result["setup_assessment"] = json!({"status":status,"scope":scope,"basis":setup,"currentness":comparison.status,"changed_dependencies":comparison.changed,"record":record,"integration_complete":settled,"review_complete":reviewed,"assessment_due":!reviewed,"machine_readiness":"not-certified-by-configuration-assessment","request":template(READ,json!({"scope":scope})),"authority":"Current Configuration judgment only; no policy consent, domain proof or whole-task completion."});
    result["setup_assessment"]["settlement_boundary"] = json!(
        "integration_complete settles Configuration assessment only. Owner-managed concerns certify no readiness: use the responsible current owner when readiness is needed. Pending authorized setup work must retain an unfinished disposition."
    );
    result["setup_assessment"]["owner_managed_concerns"] = json!(
        record["dispositions"]
            .as_array()
            .into_iter()
            .flatten()
            .filter(|r| r["status"] == "owner-managed")
            .map(|r| r["concern"].clone())
            .collect::<Vec<_>>()
    );
    if !reviewed {
        restrict(result);
    }
    // Prepared artifact identity: no payload construction or repository walk.
    let provenance =
        read(&root, ".agentic-workspace/payload-provenance.json")?.unwrap_or(Value::Null);
    let refresh_due = !provenance.is_null()
        && provenance["managed_revision"] != crate::native_payload::identity();
    result["managed_refresh"] = json!({"required":refresh_due,"revision":crate::native_payload::identity(),"request":result["payload_discovery_request"],"adoption_request":result["repository_adoption_request"]});
    if refresh_due && compatibility == "compatible" {
        let blockers = result["contribution"]["blockers"]
            .as_array()
            .cloned()
            .unwrap_or_default();
        let mut blockers = blockers;
        blockers.push(json!({"code":"configuration-managed-refresh-required","message":"Managed package material changed. Use existing adoption/payload refresh; retain current semantic setup choices.","affects":["claim:configuration-integration-complete"]}));
        result["contribution"]["blockers"] = json!(blockers);
    }
    if selected {
        result["setup_assessment"]["material"] = material()?;
        result["setup_assessment"]["concerns"] = json!(
            [
                "instructions",
                "diagnostics",
                "assignment",
                "modules",
                "invocation",
                "preferences"
            ]
            .into_iter()
            .map(|concern| json!({"concern":concern,"settlement":settlement(concern)}))
            .collect::<Vec<_>>()
        );
        result["setup_assessment"]["judgment_schema"] = json!({
            "type":"object","required":["coverage","dispositions"],
            "description":"Fill only semantic judgment in record_request.arguments.value; preserve returned kind, scope, runtime_version, basis and dependency observations. Re-request with extra dependency paths when needed.",
            "properties":{
                "coverage":{"type":"string","minLength":1,"description":"Explain consideration of the current setup material against standing repository intent, including useful optional additions."},
                "dispositions":{"type":"array","minItems":1,"maxItems":64,"items":{"type":"object","required":["subject","status","reason"],"properties":{
                    "subject":{"type":"string","minLength":1},
                    "status":{"enum":["effective","already-effective","owner-managed","irrelevant","excluded","pending","deferred","blocked","unavailable"]},
                    "reason":{"type":"string","minLength":1},
                    "concern":{"enum":["instructions","diagnostics","assignment","modules","invocation","preferences"]},
                    "observation":{"type":"object","description":"Only instructions/preferences support effective/already-effective: request behavior with this assessment's scope and copy the non-null configuration_behavior.setup_witness exactly. It is reobserved in that scope before publication and reuse. Never supply observation for owner-managed."},
                    "resume":{"type":"string","description":"Required for pending/deferred/blocked/unavailable: precise owner and next action."}
                },"allOf":[
                    {"if":{"properties":{"status":{"enum":["effective","already-effective"]}}},"then":{"required":["concern","observation"],"properties":{"concern":{"enum":["instructions","preferences"]}}}},
                    {"if":{"properties":{"status":{"const":"owner-managed"}}},"then":{"required":["concern"],"properties":{"concern":{"enum":["diagnostics","assignment","modules","invocation"]}},"not":{"required":["observation"]}}}
                ],"description":"owner-managed settles consideration of a relevant concern whose effectiveness is outside Configuration assessment in both scopes. Explain the responsible owner and why no setup action remains here; never use it to hide pending authorized setup work or to claim readiness."}},
                "continuation":{"type":["object","null"],"properties":{"task":{"type":"string","minLength":1}},"description":"Required original ordinary task when any disposition remains unfinished."}
            }
        });
        result["setup_assessment"]["remaining_routes"] = json!({"payload":result["payload_discovery_request"],"adoption":result["repository_adoption_request"],"behavior":result["behavior_request"],"exposure":result["skill_exposure_request"]});
        if compatibility == "compatible" {
            let mut value = json!({"kind":KIND,"runtime_version":version(),"scope":scope,"basis":setup,"selected_dependencies":extra,"dependencies":observed,"coverage":"","dispositions":[],"continuation":null});
            if !record.is_null() {
                for field in ["coverage", "dispositions", "continuation"] {
                    value[field] = record[field].clone();
                }
            }
            result["setup_assessment"]["record_request"] = template(
                "configuration/edit-source/v1",
                json!({"source":source,"key":KEY,"value":value}),
            );
        }
    }
    if scope == "repository" && deps::read(&root, LOCAL)?.is_some() {
        let mut local = json!({"contribution":{}});
        view_inner(
            target,
            config,
            Some(&json!({"request_kind":"automatic-local","arguments":{"scope":"machine-local"}})),
            template,
            &mut local,
        )?;
        result["local_setup_assessment"] = local["setup_assessment"].clone();
        if local["setup_assessment"]["assessment_due"] == true {
            restrict(result);
        }
    }
    Ok(())
}
pub(crate) fn proposed(target: &Path, source: &str, value: &Value) -> Result<Vec<u8>, CoreError> {
    if !value.as_object().is_some_and(|o| {
        o.keys().all(|k| {
            [
                "kind",
                "runtime_version",
                "scope",
                "basis",
                "selected_dependencies",
                "dependencies",
                "coverage",
                "dispositions",
                "continuation",
            ]
            .contains(&k.as_str())
        })
    }) {
        return Err(err("unrecognized setup assessment fields preserved"));
    }
    if !is_source(source) {
        return Err(err("setup assessment source is not canonical"));
    }
    let root = Dir::open_ambient_dir(target, ambient_authority()).map_err(err)?;
    if transition(&root, &read(&root, source)?.unwrap_or(Value::Null))? != "compatible" {
        return Err(err("incompatible or newer integration preserved"));
    }
    let scope = if source == LOCAL {
        "machine-local"
    } else {
        "repository"
    };
    if value["kind"] != KIND
        || value["scope"] != scope
        || value["runtime_version"] != version()
        || value["basis"] != basis()
        || value["dependencies"]
            != json!(dependencies(&root, scope, &value["selected_dependencies"])?)
    {
        return Err(err(
            "setup assessment basis changed; reassess current material and sources",
        ));
    }
    if !value["coverage"]
        .as_str()
        .is_some_and(|s| !s.trim().is_empty())
    {
        return Err(err("setup material coverage judgment required"));
    }
    let rows = value["dispositions"]
        .as_array()
        .filter(|a| !a.is_empty() && a.len() <= 64)
        .ok_or_else(|| err("bounded setup dispositions required"))?;
    for row in rows {
        if !valid_settlement(row) {
            return Err(err(
                "unsupported setup settlement: effective requires instructions/preferences consumer evidence; diagnostics/assignment/modules/invocation use owner-managed without a readiness claim, or preserve unfinished work",
            ));
        }
        if !["subject", "reason"]
            .iter()
            .all(|k| row[k].as_str().is_some_and(|s| !s.trim().is_empty()))
        {
            return Err(err("grounded setup disposition required"));
        }
        match row["status"].as_str() {
            Some("effective" | "already-effective")
                if row["concern"].is_string() && row["observation"].is_object() => {}
            Some("irrelevant" | "excluded" | "owner-managed") => (),
            Some("pending" | "deferred" | "blocked" | "unavailable")
                if row["resume"].as_str().is_some_and(|s| !s.trim().is_empty())
                    && value["continuation"]["task"]
                        .as_str()
                        .is_some_and(|s| !s.trim().is_empty()) => {}
            _ => {
                return Err(err(
                    "disposition needs current consumer evidence or a precise unresolved continuation",
                ));
            }
        }
    }
    let mut bytes = serde_json::to_vec_pretty(value).map_err(err)?;
    if bytes.len() > 128 * 1024 {
        return Err(err(
            "setup assessment exceeds bounded current judgment size",
        ));
    }
    bytes.push(b'\n');
    Ok(bytes)
}
/// Reobserve the real consumer, including at invoke's publication revalidation.
/// Stored observations are dependency witnesses, never copies of owner authority.
pub(crate) fn validate_consumers(target: &Path, current: &Value) -> Result<(), CoreError> {
    let proposal = &current["configuration_write"]["assessment_proposal"];
    if proposal.is_null() {
        return Ok(());
    }
    for row in proposal["dispositions"]
        .as_array()
        .into_iter()
        .flatten()
        .filter(|r| {
            matches!(
                r["status"].as_str(),
                Some("effective" | "already-effective")
            )
        })
    {
        let concern = row["concern"].as_str().unwrap_or("");
        let witness = consumer_witness(
            target,
            concern,
            proposal["scope"].as_str().unwrap_or(""),
            current,
        )?;
        if witness.is_null() || witness != row["observation"] {
            return Err(err(
                "setup consumer effectiveness not established; preserve pending owner verification",
            ));
        }
    }
    Ok(())
}
/// Owner observations can change independently of the selected source paths.
/// Reusing a saved effectiveness claim needs the same evidence as publishing it.
pub(crate) fn revalidate_saved(
    target: &Path,
    configuration: &Value,
    startup: &Value,
    config_write: &mut Value,
) -> Result<(), CoreError> {
    let current = json!({"configuration":configuration,"startup_adapter":startup});
    for field in ["setup_assessment", "local_setup_assessment"] {
        let assessment = &config_write[field];
        if assessment["review_complete"] != true
            || assessment["status"] == "publication-recovery-required"
        {
            continue;
        }
        let mut changed = Vec::new();
        for row in assessment["record"]["dispositions"]
            .as_array()
            .into_iter()
            .flatten()
        {
            if matches!(
                row["status"].as_str(),
                Some("effective" | "already-effective")
            ) {
                let concern = row["concern"].as_str().unwrap_or("");
                let observed = consumer_witness(
                    target,
                    concern,
                    assessment["scope"].as_str().unwrap_or(""),
                    &current,
                )?;
                if observed.is_null() || observed != row["observation"] {
                    changed.push(concern.to_owned());
                }
            }
        }
        if !changed.is_empty() {
            let assessment = &mut config_write[field];
            assessment["status"] = json!("assessment-required");
            assessment["review_complete"] = json!(false);
            assessment["integration_complete"] = json!(false);
            assessment["assessment_due"] = json!(true);
            assessment["changed_consumers"] = json!(changed);
            restrict(config_write);
        } else if config_write[field]["status"] == "settled" {
            config_write[field]
                .as_object_mut()
                .unwrap()
                .remove("record_request");
        }
    }
    Ok(())
}
pub(crate) fn consumer_witness(
    target: &Path,
    concern: &str,
    scope: &str,
    current: &Value,
) -> Result<Value, CoreError> {
    if !matches!(scope, "repository" | "machine-local") {
        return Err(err("unsupported setup witness scope"));
    }
    let actual = crate::native_configuration_procedure::observe(target, concern, current)?;
    let o = &actual["observation"];
    let material = match concern {
        "instructions" if o["current"]["status"] == "source-context-delivered" => {
            json!({"owner":"startup-adapter","source":o["current"]["source"]})
        }
        // clarification is owned by local configuration, while improvement
        // latitude is shared. Never hash the merged local view into a shared
        // assessment or add local sources to repository dependencies.
        "preferences" if scope == "repository" => {
            json!({"owner":o["owner"],"improvement_latitude":o["improvement_latitude"]})
        }
        "preferences" => o.clone(),
        _ => return Ok(Value::Null),
    };
    Ok(
        json!({"owner":o["owner"],"scope":scope,"revision":digest(&json!({"scope":scope,"material":material}))?}),
    )
}
