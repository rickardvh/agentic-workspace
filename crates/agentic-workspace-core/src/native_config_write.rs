//! Exact edits to externally owned configuration. Attempts attest one write;
//! neither source shape nor a previous write grants continuing custody.
use crate::{CoreError, digest};
use cap_std::{
    ambient_authority,
    fs::{Dir, OpenOptions},
};
use serde_json::{Value, json};
use std::{io::Write, path::Path};
const SHARED: &str = ".agentic-workspace/config.toml";
const LOCAL: &str = ".agentic-workspace/config.local.toml";
const EDIT: &str = "configuration/edit-source/v1";
const RECOVER: &str = "configuration/recover-write/v1";
const DEFER: &str = "configuration.defer-choice";
const READ: &str = "configuration/read-choice/v1";
const READ_CREATION: &str = "configuration/read-creation-choices/v1";
const READ_PAYLOAD: &str = "configuration/read-payload-choices/v1";
const PAYLOAD_KEY: &str = "package.payload";
const EFFECT: &str = "configuration-source";
// Durable choices consumed by current owners, including explicit native module
// admission. Task answers, learned evidence and operational registries stay out.
const CHOICES: &[(&str, &str)] = &[
    (SHARED, "workspace.enabled"),
    (LOCAL, "workspace.enabled"),
    (LOCAL, "session_logging.enabled"),
    (LOCAL, "session_logging.path_mode"),
    (LOCAL, "clarification.mode"),
    (SHARED, "workspace.cli_invoke"),
    (SHARED, "workspace.improvement_latitude"),
    (LOCAL, "workspace.cli_invoke"),
    (SHARED, "modules.enabled"),
    (SHARED, "modules.independent"),
    (SHARED, "assurance.decision_delegations"),
    (SHARED, "workspace.agent_instructions_file"),
    (SHARED, "system_intent.sources"),
    (SHARED, "system_intent.preferred_source"),
    (LOCAL, "safety.safe_to_auto_run_commands"),
    (LOCAL, "safety.requires_human_verification_on_pr"),
];
const PROGRESSIVE_CHOICES: &[&str] = &["modules.independent", "assurance.decision_delegations"];
fn choice_schema(source: &str, key: &str) -> Result<Value, CoreError> {
    if !CHOICES.contains(&(source, key)) {
        return Err(err(
            "This field is outside the durable configuration writer boundary",
        ));
    }
    let (section, field) = key.split_once('.').unwrap();
    let schema: Value = serde_json::from_str(source_schema(source)?).map_err(err)?;
    let mut value = schema["properties"][section]["properties"][field].clone();
    if value.is_null() {
        return Err(err("Current configuration choice schema is unavailable"));
    }
    value["$schema"] = json!("https://json-schema.org/draft/2020-12/schema");
    if value["type"] == "string" {
        value["maxLength"] = json!(4096);
    }
    if value["type"] == "array" {
        value["maxItems"] = json!(32);
        if value["items"]["type"] == "string" {
            value["items"]["maxLength"] = json!(4096);
        }
    }
    Ok(value)
}
fn err(e: impl ToString) -> CoreError {
    CoreError::new(e.to_string())
}
fn read(root: &Dir, path: &str) -> Result<Vec<u8>, CoreError> {
    crate::native_planning::read(root, path)?.ok_or_else(|| err("configuration source missing"))
}
fn source_schema(source: &str) -> Result<&'static str, CoreError> {
    match source {
        SHARED => Ok(include_str!(
            "../../../src/agentic_workspace/contracts/schemas/workspace_config.schema.json"
        )),
        LOCAL => Ok(include_str!(
            "../../../src/agentic_workspace/contracts/schemas/workspace_local_override.schema.json"
        )),
        _ => Err(err("configuration source is not canonical")),
    }
}
fn sources(target: &Path) -> Result<Value, CoreError> {
    let root = Dir::open_ambient_dir(target, ambient_authority()).map_err(err)?;
    let mut values = json!({});
    for source in [SHARED, LOCAL] {
        values[source] =
            match crate::native_config::load(&root, source, source_schema(source)?).map_err(err)? {
                Some((_, revision)) => {
                    json!(revision)
                }
                None => Value::Null,
            };
    }
    // Shared-local files are read dependencies, never write targets.
    for source in crate::native_assignment_policy::load(target)?.sources {
        values[source["reference"].as_str().unwrap()] = source["revision"].clone();
    }
    Ok(values)
}
fn bound_sources(target: &Path, source: Option<&str>) -> Result<Value, CoreError> {
    let mut values = sources(target)?;
    if let Some(source) = source.filter(|source| crate::native_payload::paths().contains(source)) {
        let root = Dir::open_ambient_dir(target, ambient_authority()).map_err(err)?;
        values[source] = crate::native_planning::read(&root, source)?
            .map(|bytes| json!(crate::native_intent::hash(&bytes)))
            .unwrap_or(Value::Null);
    }
    Ok(values)
}
fn proposed(target: &Path, source: &str, key: &str, value: &Value) -> Result<Vec<u8>, CoreError> {
    if key == PAYLOAD_KEY {
        let bytes = crate::native_payload::shipped(source)?;
        if *value != crate::native_intent::hash(&bytes) {
            return Err(err("payload choice differs from the current artifact"));
        }
        bound_sources(target, Some(source))?;
        return Ok(bytes);
    }
    if key == "modules.independent" {
        let root = Dir::open_ambient_dir(target, ambient_authority()).map_err(err)?;
        let before = crate::native_config::load(&root, source, source_schema(source)?)
            .map_err(err)?
            .map(|v| v.0)
            .unwrap_or(json!({}));
        let entries = value
            .as_object()
            .ok_or_else(|| err("Independent admissions must be an object"))?;
        let schema = choice_schema(source, key)?;
        for (owner, admission) in entries {
            if before["modules"]["independent"][owner] == *admission {
                continue;
            }
            crate::schema_validator(&schema, "selected independent admission")?
                .validate(&json!({owner:admission}))
                .map_err(err)?;
            crate::native_independent::validate_choice(owner, admission)?;
        }
    } else {
        crate::schema_validator(&choice_schema(source, key)?, "configuration choice")?
            .validate(value)
            .map_err(err)?;
    }
    let (section, field) = key.split_once('.').unwrap();
    let replacement = toml_edit::ser::to_document(&json!({"value":value})).map_err(err)?["value"]
        .as_value()
        .unwrap()
        .clone();
    let root = Dir::open_ambient_dir(target, ambient_authority()).map_err(err)?;
    sources(target)?;
    let raw = crate::native_planning::read(&root, source)?.unwrap_or_default();
    let text = std::str::from_utf8(&raw).map_err(err)?;
    if text.starts_with('\u{feff}') {
        return Err(err(
            "BOM configuration editing is not supported; source preserved",
        ));
    }
    let document = toml_edit::ImDocument::parse(text).map_err(err)?;
    let current = document
        .get(section)
        .and_then(|v| v.get(field))
        .and_then(toml_edit::Item::as_value);
    let rendered = if let Some(current) = current {
        let span = current
            .span()
            .ok_or_else(|| err("configuration literal span unavailable"))?;
        let mut rendered = text.to_owned();
        rendered.replace_range(span, &replacement.to_string());
        rendered
    } else {
        let crlf = text.contains("\r\n");
        if crlf && text.replace("\r\n", "").contains('\n') {
            return Err(err(
                "Mixed configuration line endings require source-owner repair",
            ));
        }
        let normalized = text.replace("\r\n", "\n");
        let mut edited = normalized.parse::<toml_edit::DocumentMut>().map_err(err)?;
        let had_section = edited.contains_key(section);
        if !had_section {
            edited[section] = toml_edit::Item::Table(toml_edit::Table::new());
        }
        let table = edited
            .get_mut(section)
            .and_then(toml_edit::Item::as_table_mut)
            .ok_or_else(|| {
                err(format!(
                    "configuration insertion requires an ordinary {section} table"
                ))
            })?;
        let prior = table.insert(field, toml_edit::Item::Value(replacement));
        let rendered = edited.to_string();
        // Admission is narrower than TOML equivalence: removing only the exact
        // insertion must recover all prior bytes, including comments and policy.
        if had_section {
            if let Some(prior) = prior {
                edited[section].as_table_mut().unwrap().insert(field, prior);
            } else {
                edited[section].as_table_mut().unwrap().remove(field);
            }
        } else {
            edited.remove(section);
        }
        if edited.to_string() != normalized {
            return Err(err(
                "configuration insertion cannot preserve unrelated source bytes",
            ));
        }
        if crlf {
            rendered.replace('\n', "\r\n")
        } else {
            rendered
        }
    };
    if rendered.len()
        > crate::native_config::MAX_SOURCE_BYTES.min(crate::decision_source::MAX_SOURCE_BYTES)
    {
        return Err(err(
            "Configuration postimage exceeds the bounded source reader; source preserved",
        ));
    }
    let parsed: toml::Value = toml::from_str(&rendered).map_err(err)?;
    let parsed = serde_json::to_value(parsed).map_err(err)?;
    crate::native_config::validate_source(&parsed, source_schema(source)?).map_err(err)?;
    // Local enablement/invocation are preference overrides. Independent module,
    // source-admission, proof and safety requirements remain with their owners.
    Ok(rendered.into_bytes())
}
pub(crate) fn contract() -> Result<Value, CoreError> {
    // Choice schemas are delivered by READ, not copied into every ordinary
    // capability projection. proposed() still validates the exact value against
    // the source-owned schema before any disposition or publication.
    let mut alternatives: Vec<Value> = [SHARED, LOCAL].map(|source| json!({"properties":{
        "source":{"const":source},"key":{"enum":CHOICES.iter().filter(|(s,_)| *s == source).map(|(_,key)| *key).collect::<Vec<_>>()}}})).to_vec();
    // Artifact paths are lazy discovery data. proposed()/bound_sources() enforce
    // their exact ownership before publication; do not repeat the roster in
    // every ordinary capability schema.
    alternatives.push(json!({"properties":{"source":{"type":"string"},"key":{"const":PAYLOAD_KEY},"value":{"type":"string"}}}));
    let mut args = json!({"$schema":"https://json-schema.org/draft/2020-12/schema","type":"object","properties":{"source":{"enum":[SHARED,LOCAL]},"key":{"type":"string"},"value":{},"answer":{"enum":["authorize-write","defer"]},"proposal_revision":{"type":"string"}},"required":["source","key","value"],"additionalProperties":false,"oneOf":alternatives});
    args["properties"]["nomination"] = crate::native_owner_change::schema();
    args["properties"]["source"] = json!({"type":"string"});
    let recovery = json!({"$schema":"https://json-schema.org/draft/2020-12/schema","type":"object","properties":{"source":{"type":"string"},"record_revision":{"type":"string"}},"required":["source","record_revision"],"additionalProperties":false});
    let operation = |id: &str| json!({"id":id,"semantic_revision":"configuration-external-source-write-v4","input_schema":{"$schema":"https://json-schema.org/draft/2020-12/schema","type":"object","properties":{"target":{"type":"string"},"request":{"type":"object"},"binding":{"type":"object"},"post_revision":{"type":"string"}},"required":["target","request","binding","post_revision"],"additionalProperties":false},"result_kind":"agentic-workspace/configuration-write-result/v1","effects":[EFFECT],"reads":["configuration"]});
    let mut owner = json!({"owner":"configuration","revision":"pending","domains":["configuration"],"effects":[{"id":EFFECT,"domain":"configuration"}],"requests":[{"kind":EDIT,"result_kind":"agentic-workspace/configuration-write-proposal/v1","input_schema":args},{"kind":RECOVER,"result_kind":"agentic-workspace/configuration-write-result/v1","input_schema":recovery}],"operations":[operation("configuration.write"),operation("configuration.recover-write"), operation(DEFER)]});
    owner["requests"].as_array_mut().unwrap().push(json!({"kind":READ_CREATION,"result_kind":"agentic-workspace/configuration-creation-choices/v1","input_schema":{"$schema":"https://json-schema.org/draft/2020-12/schema","type":"object","additionalProperties":false,"properties":{}}}));
    owner["requests"].as_array_mut().unwrap().push(json!({"kind":READ_PAYLOAD,"result_kind":"agentic-workspace/configuration-payload-choices/v1","input_schema":{"$schema":"https://json-schema.org/draft/2020-12/schema","type":"object","additionalProperties":false,"properties":{}}}));
    owner["requests"].as_array_mut().unwrap().push(json!({"kind":READ,"result_kind":"agentic-workspace/configuration-choice/v1","input_schema":{"$schema":"https://json-schema.org/draft/2020-12/schema","type":"object","additionalProperties":false,"required":["source","key"],"properties":{"source":{"enum":[SHARED,LOCAL]},"key":{"type":"string"},"selected_owner":{"type":"string","pattern":"^[a-z][a-z0-9-]{0,63}$"}}}}));
    owner["requests"]
        .as_array_mut()
        .unwrap()
        .push(crate::native_configuration_procedure::declaration());
    crate::native_skill_exposure::declarations(&mut owner);
    crate::native_adoption::declarations(&mut owner);
    owner["revision"] = json!(digest(&owner)?);
    let mut result = json!({"kind":"agentic-workspace/capability-contract/v1","revision":"pending","owners":[owner],"restriction_authorities":[{"owner":"configuration","affects":["task","effect:configuration-source"]}]});
    result["revision"] = json!(digest(&result)?);
    Ok(result)
}
fn marker(source: &str, post: &str) -> Result<String, CoreError> {
    Ok(format!(
        ".agentic-workspace/local/effects/configuration-{}.prepared.json",
        &digest(&json!([source, post]))?[7..]
    ))
}
fn outcome(invocation: &Value) -> Value {
    json!({"status":"applied","effects":[EFFECT],"value":{"kind":"agentic-workspace/configuration-write-result/v1","source":invocation["arguments"]["request"]["arguments"]["source"],"post_revision":invocation["arguments"]["post_revision"],"source_ownership":if invocation["arguments"]["request"]["arguments"]["key"] == PAYLOAD_KEY {"package-managed"} else {"repo-human"},"continuing_custody":false,"completion_authority":false}})
}
fn retained(target: &Path, source: &str, post: &str) -> Result<Option<Value>, CoreError> {
    let root = Dir::open_ambient_dir(target, ambient_authority()).map_err(err)?;
    let Some(raw) = crate::native_planning::read(&root, &marker(source, post)?)? else {
        return Ok(None);
    };
    let record: Value = serde_json::from_slice(&raw).map_err(err)?;
    let evidence = serde_json::from_value(record["custody"]["attempt"].clone()).map_err(err)?;
    let attempt = crate::attempt_store::read_source(target.to_str().unwrap(), &evidence)?;
    let i = &record["invocation"];
    if attempt["invocation"] != *i
        || i["operation_id"] != "configuration.write"
        || i["arguments"]["target"] != target.to_str().unwrap()
        || i["arguments"]["request"]["arguments"]["source"] != source
        || i["arguments"]["post_revision"] != post
        || record["outcome"] != outcome(i)
    {
        return Err(err(
            "configuration write evidence does not match its exact attempt",
        ));
    }
    Ok(Some(record))
}
fn deferred_path(source: &str, key: &str) -> Result<String, CoreError> {
    Ok(format!(
        ".agentic-workspace/local/configuration/{}.json",
        &digest(&json!([source, key]))?[7..]
    ))
}
fn deferred(target: &Path, source: &str, key: &str) -> Result<Option<Value>, CoreError> {
    let root = Dir::open_ambient_dir(target, ambient_authority()).map_err(err)?;
    let Some(bytes) = crate::native_planning::read(&root, &deferred_path(source, key)?)? else {
        return Ok(None);
    };
    let record: Value = serde_json::from_slice(&bytes).map_err(err)?;
    let prepared = crate::attempt_store::prepare_commit(
        target.to_str().unwrap(),
        record["custody"].clone(),
        record["outcome"].clone(),
    )?;
    let i = &record["invocation"];
    if prepared["record"]["invocation"] != *i
        || i["operation_id"] != DEFER
        || i["source_owner"] != "configuration"
        || i["arguments"]["request"]["arguments"]["source"] != source
        || i["arguments"]["request"]["arguments"]["key"] != key
        || record["outcome"] != deferred_outcome(i)
    {
        return Err(err(
            "configuration continuation lacks exact owner custody; preserve it",
        ));
    }
    Ok(Some(record))
}
fn deferred_outcome(i: &Value) -> Value {
    json!({"status":"applied","effects":[EFFECT],"value":{"kind":"agentic-workspace/configuration-write-result/v1","source":i["arguments"]["request"]["arguments"]["source"],"key":i["arguments"]["request"]["arguments"]["key"],"disposition":"deferred","material_written":false,"continuing_custody":false,"completion_authority":false}})
}
pub(crate) fn view(
    target: &Path,
    work: &Value,
    config: &Value,
    contract: &Value,
    request: Option<&Value>,
) -> Result<Value, CoreError> {
    view_selected(target, work, config, contract, request, true)
}

pub(crate) fn view_selected(
    target: &Path,
    work: &Value,
    config: &Value,
    contract: &Value,
    request: Option<&Value>,
    detail: bool,
) -> Result<Value, CoreError> {
    let owner = contract["owners"]
        .as_array()
        .unwrap()
        .iter()
        .find(|v| v["owner"] == "configuration")
        .unwrap();
    let mut result = json!({"requests":[],"creation_requests":[],"recovery_requests":[],"status":"not-applicable","contribution":{"owner":"configuration","revision":owner["revision"],"actions":[]}});
    let current = match bound_sources(
        target,
        request.and_then(|r| r["arguments"]["source"].as_str()),
    ) {
        Ok(v) => v,
        Err(e) => {
            if request.is_some() {
                return Err(e);
            }
            return Ok(result);
        }
    };
    let binding = json!({"sources":current,"effective_policy_revision":config["revision"],"capability_revision":contract["revision"]});
    result["contribution"]["revision"] = json!(digest(&binding)?);
    let template = |kind: &str, args: Value| json!({"kind":"agentic-workspace/public-request/v1","id":kind,"owner":"configuration","owner_revision":owner["revision"],"source_revision":digest(&binding).unwrap(),"capability_revision":contract["revision"],"task_identity":work,"request_kind":kind,"arguments":args});
    result["behavior_request"] = template(
        crate::native_configuration_procedure::READ,
        json!({"concern":"instructions"}),
    );
    result["payload_discovery_request"] = template(READ_PAYLOAD, json!({}));
    result["skill_exposure_request"] = template(crate::native_skill_exposure::READ, json!({}));
    result["repository_adoption_request"] = template(crate::native_adoption::READ, json!({}));
    result["choice_requests"] = json!(
        PROGRESSIVE_CHOICES
            .iter()
            .map(|key| template(READ, json!({"source":SHARED,"key":key})))
            .collect::<Vec<_>>()
    );
    if [SHARED, LOCAL]
        .iter()
        .any(|source| current[source].is_null())
    {
        result["creation_discovery_request"] = template(READ_CREATION, json!({}));
    }
    let root = Dir::open_ambient_dir(target, ambient_authority()).map_err(err)?;
    for source in [SHARED, LOCAL] {
        if current[source].is_null() && request.is_some_and(|r| r["request_kind"] == READ_CREATION)
        {
            for (_, key) in CHOICES.iter().filter(|(s, _)| *s == source) {
                if PROGRESSIVE_CHOICES.contains(key) {
                    continue;
                }
                let schema = choice_schema(source, key)?;
                let value = if !schema["default"].is_null() {
                    schema["default"].clone()
                } else if schema["type"] == "boolean" {
                    json!(false)
                } else if schema["type"] == "array" {
                    json!([])
                } else if *key == "workspace.cli_invoke" {
                    json!("agentic-workspace")
                } else {
                    json!("<explicit-source-choice>")
                };
                result["creation_requests"]
                    .as_array_mut()
                    .unwrap()
                    .push(template(
                        EDIT,
                        json!({"source":source,"key":key,"value":value}),
                    ));
            }
        }
        if let Some((v, revision)) =
            crate::native_config::load(&root, source, source_schema(source)?).map_err(err)?
        {
            if detail {
                #[cfg(test)]
                crate::native_frontier::built("configuration-fields");
                let value = v["workspace"]["cli_invoke"]
                    .as_str()
                    .or(config["cli_invoke"].as_str())
                    .unwrap_or("agentic-workspace");
                result["requests"].as_array_mut().unwrap().push(template(
                    EDIT,
                    json!({"source":source,"key":"workspace.cli_invoke","value":value}),
                ));
                for (choice_source, key) in CHOICES.iter().filter(|(s, k)| {
                    *s == source && *k != "workspace.cli_invoke" && !PROGRESSIVE_CHOICES.contains(k)
                }) {
                    let (section, field) = key.split_once('.').unwrap();
                    let schema = choice_schema(choice_source, key)?;
                    let value = if !v[section][field].is_null() {
                        v[section][field].clone()
                    } else if !schema["default"].is_null() {
                        schema["default"].clone()
                    } else if schema["type"] == "boolean" {
                        json!(false)
                    } else if schema["type"] == "array" {
                        json!([])
                    } else {
                        json!("<explicit-source-choice>")
                    };
                    // Discovery is not a recommendation or standing permission.
                    result["requests"].as_array_mut().unwrap().push(template(
                        EDIT,
                        json!({"source":source,"key":key,"value":value}),
                    ));
                }
            }
            if let Some(record) = retained(target, source, &revision)? {
                let prepared = crate::attempt_store::prepare_commit(
                    target.to_str().unwrap(),
                    record["custody"].clone(),
                    record["outcome"].clone(),
                )?;
                if crate::native_planning::read(
                    &root,
                    prepared["custody"]["committed"]["path"].as_str().unwrap(),
                )?
                .is_none()
                {
                    result["recovery_requests"]
                        .as_array_mut()
                        .unwrap()
                        .push(template(
                            RECOVER,
                            json!({"source":source,"record_revision":digest(&record)?}),
                        ));
                }
            }
        }
    }
    result["requests"]
        .as_array_mut()
        .unwrap()
        .sort_by_key(|r| r["arguments"]["key"] != "workspace.cli_invoke");
    result["deferred_choices"] = json!([]);
    for (source, key) in CHOICES {
        if let Some(record) = deferred(target, source, key)? {
            let args = &record["invocation"]["arguments"]["request"]["arguments"];
            let state = if record["invocation"]["arguments"]["binding"] == binding {
                "current"
            } else {
                "changed-context"
            };
            result["deferred_choices"].as_array_mut().unwrap().push(json!({"source":source,"key":key,"proposed_value":args["value"],"status":state,"authority":"unresolved-choice-only","resume_request":template(EDIT,json!({"source":source,"key":key,"value":args["value"]}))}));
        }
    }
    let Some(request) = request else {
        return Ok(result);
    };
    crate::prepare_request_value(
        json!({"request":request,"current_work":work,"capability_contract":contract}),
    )?;
    if request["source_revision"] != digest(&binding)? {
        return Err(err(
            "configuration source, policy or capability changed; resolve a fresh request",
        ));
    }
    if matches!(
        request["request_kind"].as_str(),
        Some(crate::native_adoption::READ | crate::native_adoption::EDIT)
    ) {
        crate::native_adoption::view(target, request, &binding, &template, &mut result)?;
        return Ok(result);
    }
    if matches!(
        request["request_kind"].as_str(),
        Some(crate::native_skill_exposure::READ | crate::native_skill_exposure::EDIT)
    ) {
        crate::native_skill_exposure::view(target, request, &binding, &template, &mut result)?;
        return Ok(result);
    }
    if request["request_kind"] == crate::native_configuration_procedure::READ {
        result["status"] = json!("behavior-requested");
        result["requested_behavior"] = request["arguments"]["concern"].clone();
        return Ok(result);
    }
    if request["request_kind"] == READ_PAYLOAD {
        let mut choices = Vec::new();
        for source in crate::native_payload::paths() {
            let bytes = crate::native_payload::shipped(source)?;
            let post = crate::native_intent::hash(&bytes);
            let mut exact_binding = binding.clone();
            exact_binding["sources"] = bound_sources(target, Some(source))?;
            let mut choice = template(
                EDIT,
                json!({"source":source,"key":PAYLOAD_KEY,"value":post}),
            );
            choice["source_revision"] = json!(digest(&exact_binding)?);
            let mut row = json!({"source":source,"status":if exact_binding["sources"][source] == post {"current"} else {"refresh-available"},"request":choice});
            if let Some(record) = retained(target, source, &post)? {
                let prepared = crate::attempt_store::prepare_commit(
                    target.to_str().unwrap(),
                    record["custody"].clone(),
                    record["outcome"].clone(),
                )?;
                if exact_binding["sources"][source] == post
                    && crate::native_planning::read(
                        &root,
                        prepared["custody"]["committed"]["path"].as_str().unwrap(),
                    )?
                    .is_none()
                {
                    let mut recovery = template(
                        RECOVER,
                        json!({"source":source,"record_revision":digest(&record)?}),
                    );
                    recovery["source_revision"] = json!(digest(&exact_binding)?);
                    row["recovery_request"] = recovery;
                }
            }
            choices.push(row);
        }
        result["status"] = json!("payload-choices-delivered");
        result["payload_choices"] = json!(choices);
        return Ok(result);
    }
    if request["request_kind"] == READ_CREATION {
        result["status"] = json!("creation-choices-delivered");
        return Ok(result);
    }
    let args = &request["arguments"];
    if request["request_kind"] == READ {
        let key = args["key"].as_str().unwrap();
        let (section, field) = key
            .split_once('.')
            .ok_or_else(|| err("configuration key malformed"))?;
        let source = args["source"].as_str().unwrap();
        if !CHOICES.contains(&(source, key)) {
            let schema: Value = serde_json::from_str(source_schema(source)?).map_err(err)?;
            let shape = &schema["properties"][section]["properties"][field];
            result["status"] = json!("source-owner-route");
            result["selected_choice"] = json!({"source":source,"key":key,
                "authorable":!shape.is_null(),"schema":shape,"edit_request":null,
                "route":if shape.is_null(){"unknown configuration key; use the current source grammar"}else{"repository/local source authoring; preserve independently admitted trust and authority"},
                "authority":"Read-only route; no write, migration or trust admission."});
            return Ok(result);
        }
        let schema = choice_schema(source, key)?;
        let current =
            crate::native_config::load(&root, source, source_schema(source)?).map_err(err)?;
        let mut value = current
            .map(|(source, _)| source[section][field].clone())
            .filter(|value| !value.is_null())
            .unwrap_or_else(|| {
                if !schema["default"].is_null() {
                    schema["default"].clone()
                } else if schema["type"] == "boolean" {
                    json!(false)
                } else if schema["type"] == "array" {
                    json!([])
                } else if key == "workspace.cli_invoke" {
                    json!("agentic-workspace")
                } else {
                    json!("<explicit-source-choice>")
                }
            });
        if key == "modules.independent" {
            let selected = args["selected_owner"]
                .as_str()
                .map(str::to_owned)
                .or_else(|| {
                    let values = value.as_object()?;
                    if values.len() == 1 {
                        values.keys().next().cloned()
                    } else {
                        None
                    }
                });
            if let Some(owner) = selected {
                let detail = crate::native_independent::prepare(&owner, &value[&owner])?;
                if !value.is_object() {
                    value = json!({});
                }
                value[&owner] = detail["value"].clone();
                result["independent_preparation"] = detail;
            } else {
                result["selected_owner_request"] = template(
                    READ,
                    json!({"source":source,"key":key,"selected_owner":"selected-linked-owner"}),
                );
            }
        }
        result["status"] = json!("choice-delivered");
        result["selected_choice"] = json!({"source":source,"key":key,"value":value,"schema":schema,"edit_request":template(EDIT,json!({"source":source,"key":key,"value":value}))});
        return Ok(result);
    }
    let source = args["source"]
        .as_str()
        .ok_or_else(|| err("configuration source missing"))?;
    let post;
    let operation = if request["request_kind"] == RECOVER {
        post = current[source]
            .as_str()
            .ok_or_else(|| err("recovery source missing"))?
            .to_owned();
        let record =
            retained(target, source, &post)?.ok_or_else(|| err("retained write missing"))?;
        if args["record_revision"] != digest(&record)? {
            return Err(err("retained write changed"));
        }
        let mut prior_sources = record["invocation"]["arguments"]["binding"]["sources"].clone();
        prior_sources[source] = current[source].clone();
        if prior_sources != current {
            return Err(err("other configuration changed; recovery is stale"));
        }
        "configuration.recover-write"
    } else if request["request_kind"] == EDIT {
        let value = &args["value"];
        let key = args["key"]
            .as_str()
            .ok_or_else(|| err("configuration key missing"))?;
        let (section, field) = key
            .split_once('.')
            .ok_or_else(|| err("configuration key malformed"))?;
        if args["nomination"].is_object()
            && args["nomination"]["origin"] != "trusted-correction"
            && key != "workspace.cli_invoke"
            && args["nomination"]["disposition"] == "change"
        {
            return Err(err(
                "nominated configuration method change cannot rewrite policy or safety; use explicit owner correction",
            ));
        }
        let bytes = proposed(target, source, key, value)?;
        post = crate::native_intent::hash(&bytes);
        let before = crate::native_planning::read(&root, source)?.unwrap_or_default();
        let before_value = if key == PAYLOAD_KEY {
            if args["nomination"].is_object() {
                return Err(err(
                    "payload refresh requires its exact package-source proposal",
                ));
            }
            json!(crate::native_intent::hash(&before))
        } else {
            let parsed: toml::Value =
                toml::from_str(std::str::from_utf8(&before).map_err(err)?).map_err(err)?;
            parsed
                .get(section)
                .and_then(|v| v.get(field))
                .map(serde_json::to_value)
                .transpose()
                .map_err(err)?
                .unwrap_or(Value::Null)
        };
        if let Some(disposition) =
            crate::native_owner_change::disposition(target, config, args, before_value == *value)?
        {
            result["status"] = disposition["status"].clone();
            result["nomination"] = disposition;
            return Ok(result);
        }
        if before_value == *value {
            result["status"] = json!("unchanged");
            return Ok(result);
        }
        let proposal = digest(
            &json!({"binding":binding,"source":source,"key":args["key"],"value":value,"post_revision":post,"nomination":args["nomination"]}),
        )?;
        if args["answer"].is_null() {
            if !matches!(
                key,
                "assurance.decision_delegations"
                    | "modules.independent"
                    | "modules.enabled"
                    | PAYLOAD_KEY
            ) && let Some(authority) = crate::native_decision_authority::delegated(
                config,
                "configuration",
                &[source.to_owned()],
            ) {
                let mut authorized = request.clone();
                authorized["arguments"]["answer"] = json!("authorize-write");
                authorized["arguments"]["proposal_revision"] = json!(proposal);
                let mut delegated = self::view(target, work, config, contract, Some(&authorized))?;
                delegated["authority_basis"] = authority;
                return Ok(delegated);
            }
            let mut answer = request.clone();
            answer["arguments"]["proposal_revision"] = json!(proposal);
            result["status"] = json!("human-decision-required");
            result["proposal"] = json!({"before":before_value,"after":value,"source":source,"key":key,"binding":binding,"postimage":std::str::from_utf8(&bytes).map_err(err)?,"post_revision":post,"authority":"bounded-human-answer","source_ownership":if key == PAYLOAD_KEY {"package-managed; unrelated source and local state preserved"} else {"repo-human"}});
            result["contribution"]["decisions"] = json!([{"id":"configuration-write-authorization","question":if key == PAYLOAD_KEY {"Authorize this exact artifact-derived package file refresh? Preserve unrelated repository and local state."} else {"Authorize this exact configuration-source edit? The source remains repo/human-owned."},"response_request":{"request_kind":EDIT,"arguments":answer["arguments"]},"choices":[{"id":"authorize-write","label":"Authorize this exact write"},{"id":"defer","label":"Defer without mutation"}],"affects":["task","effect:configuration-source"]}]);
            result["contribution"]["decisions"][0]["material"] = result["proposal"].clone();
            return Ok(result);
        }
        if args["proposal_revision"] != proposal {
            return Err(err(
                "configuration answer is not bound to this exact proposal",
            ));
        }
        if args["answer"] == "defer" {
            result["status"] = json!("deferred");
            result["contribution"]["actions"] = json!([{"operation_id":DEFER,"dependency_revision":digest(&json!([binding,request,post]))?,"arguments":{"target":target,"request":request,"binding":binding,"post_revision":post},"effects":[EFFECT],"source_requests":[request]}]);
            return Ok(result);
        }
        "configuration.write"
    } else {
        return Err(err("unsupported configuration request"));
    };
    result["status"] = json!("write-ready");
    result["contribution"]["actions"] = json!([{"operation_id":operation,"dependency_revision":digest(&json!([binding,request,post]))?,"arguments":{"target":target,"request":request,"binding":binding,"post_revision":post},"effects":[EFFECT],"source_requests":[request]}]);
    Ok(result)
}
pub(crate) fn write_scope(action: &Value) -> Result<Vec<String>, CoreError> {
    if action["operation_id"] == crate::native_adoption::OP {
        return crate::native_adoption::write_scope(action);
    }
    if action["operation_id"] == crate::native_skill_exposure::OP {
        return crate::native_skill_exposure::write_scope(action);
    }
    let args = &action["arguments"]["request"]["arguments"];
    let source = args["source"]
        .as_str()
        .ok_or_else(|| err("configuration source missing"))?;
    let mut paths =
        crate::attempt_store::write_paths(&json!({"idempotency_key":action["logical_effect_id"]}))?;
    paths.push(".agentic-workspace/local/effects/configuration.lock".into());
    if let Some(key) = args["key"].as_str() {
        let path = deferred_path(source, key)?;
        paths.extend([path.clone(), format!("{path}.*.tmp")]);
    }
    if action["operation_id"] != DEFER {
        paths.extend([
            source.to_owned(),
            format!("{source}.*.tmp"),
            marker(
                source,
                action["arguments"]["post_revision"].as_str().unwrap(),
            )?,
        ]);
    }
    Ok(paths)
}
pub(crate) fn execute(
    target: &Path,
    decision: &Value,
    invocation: &Value,
    mut revalidate: impl FnMut() -> Result<(), CoreError>,
) -> Result<Value, CoreError> {
    if invocation["operation_id"] == crate::native_skill_exposure::OP {
        return crate::native_skill_exposure::execute(target, decision, invocation, revalidate);
    }
    if invocation["operation_id"] == crate::native_adoption::OP {
        return crate::native_adoption::execute(target, decision, invocation, revalidate);
    }
    let mut result = execute_checked(target, decision, invocation, &mut revalidate, &mut |_| {
        Ok(())
    })?;
    if invocation["operation_id"] != DEFER {
        result["post_effect_changed_paths"] = json!([result["outcome"]["value"]["source"]]);
    }
    Ok(result)
}
fn execute_checked(
    target: &Path,
    decision: &Value,
    invocation: &Value,
    revalidate: &mut dyn FnMut() -> Result<(), CoreError>,
    observe: &mut dyn FnMut(&str) -> Result<(), CoreError>,
) -> Result<Value, CoreError> {
    if serde_json::to_vec(invocation).map_err(err)?.len() > 100_000 {
        return Err(err(
            "configuration publication exceeds bounded recovery size; preserve source",
        ));
    }
    let root = Dir::open_ambient_dir(target, ambient_authority()).map_err(err)?;
    sources(target)?;
    root.create_dir_all(".agentic-workspace/local/effects")
        .map_err(err)?;
    let lock_path = ".agentic-workspace/local/effects/configuration.lock";
    crate::native_planning::read(&root, lock_path)?;
    let lock = root
        .open_with(
            lock_path,
            OpenOptions::new().read(true).write(true).create(true),
        )
        .map_err(err)?
        .into_std();
    if lock.metadata().map_err(err)?.len() != 0 {
        return Err(err("unrecognized configuration lock preserved"));
    }
    lock.try_lock().map_err(err)?;
    revalidate()?;
    let args = &invocation["arguments"];
    let source = args["request"]["arguments"]["source"].as_str().unwrap();
    let post = args["post_revision"].as_str().unwrap();
    if invocation["operation_id"] == DEFER {
        let key = args["request"]["arguments"]["key"].as_str().unwrap();
        let previous = deferred(target, source, key)?;
        let path = deferred_path(source, key)?;
        let admission = crate::attempt_store::admit(
            json!({"target":target,"decision":decision,"invocation":invocation,"custody":previous.as_ref().filter(|r|r["invocation"]==*invocation).map(|r|&r["custody"])}),
        )?;
        let out = deferred_outcome(invocation);
        root.create_dir_all(".agentic-workspace/local/configuration")
            .map_err(err)?;
        let record = json!({"invocation":invocation,"custody":admission["custody"],"outcome":out});
        let temporary = format!("{path}.{}.tmp", &digest(invocation)?[7..]);
        if previous.as_ref() != Some(&record) {
            let bytes = serde_json::to_vec(&record).map_err(err)?;
            if let Some(existing) = crate::native_planning::read(&root, &temporary)? {
                if existing != bytes {
                    return Err(err(
                        "unknown configuration continuation temporary preserved",
                    ));
                }
            } else {
                let mut f = root
                    .open_with(&temporary, OpenOptions::new().write(true).create_new(true))
                    .map_err(err)?;
                f.write_all(&bytes).map_err(err)?;
                f.sync_all().map_err(err)?;
            }
            revalidate()?;
            if deferred(target, source, key)? != previous {
                return Err(err("configuration continuation changed"));
            }
            if previous.is_none() {
                root.hard_link(&temporary, &root, &path).map_err(err)?;
                root.remove_file(&temporary).map_err(err)?;
            } else {
                root.rename(&temporary, &root, &path).map_err(err)?;
            }
        }
        let committed = crate::attempt_store::commit(
            json!({"target":target,"custody":admission["custody"],"outcome":out}),
        )?;
        return Ok(json!({"outcome":out,"custody":committed["custody"]}));
    }
    if invocation["operation_id"] == "configuration.recover-write" {
        let record =
            retained(target, source, post)?.ok_or_else(|| err("recovery evidence missing"))?;
        let admission = crate::attempt_store::admit(
            json!({"target":target,"decision":decision,"invocation":invocation}),
        )?;
        revalidate()?;
        if crate::native_intent::hash(&read(&root, source)?) != post {
            return Err(err("recovery source changed"));
        }
        crate::attempt_store::commit(
            json!({"target":target,"custody":record["custody"],"outcome":record["outcome"]}),
        )?;
        let out = json!({"status":"applied","effects":[EFFECT],"value":{"kind":"agentic-workspace/configuration-write-result/v1","source":source,"post_revision":post,"material_written":false,"continuing_custody":false,"completion_authority":false}});
        let committed = crate::attempt_store::commit(
            json!({"target":target,"custody":admission["custody"],"outcome":out}),
        )?;
        return Ok(json!({"outcome":out,"custody":committed["custody"]}));
    }
    let bytes = proposed(
        target,
        source,
        args["request"]["arguments"]["key"].as_str().unwrap(),
        &args["request"]["arguments"]["value"],
    )?;
    if crate::native_intent::hash(&bytes) != post {
        return Err(err("configuration postimage changed"));
    }
    let previous = retained(target, source, post)?;
    if let Some(record) = &previous {
        let committed = crate::attempt_store::prepare_commit(
            target.to_str().unwrap(),
            record["custody"].clone(),
            record["outcome"].clone(),
        )?;
        if crate::native_planning::read(
            &root,
            committed["custody"]["committed"]["path"].as_str().unwrap(),
        )?
        .is_some()
        {
            return Err(err(
                "this exact configuration write was already consumed; source preserved",
            ));
        }
    }
    let temporary = format!("{source}.{}.tmp", &digest(invocation)?[7..]);
    if previous.is_none() && crate::native_planning::read(&root, &temporary)?.is_some() {
        return Err(err("unowned configuration temporary preserved"));
    }
    if previous
        .as_ref()
        .is_some_and(|r| r["invocation"] != *invocation)
    {
        return Err(err("configuration evidence collision preserved"));
    }
    let admission = crate::attempt_store::admit(
        json!({"target":target,"decision":decision,"invocation":invocation,"custody":previous.as_ref().map(|r|&r["custody"])}),
    )?;
    let out = outcome(invocation);
    let record = json!({"invocation":invocation,"custody":admission["custody"],"outcome":out});
    let path = marker(source, post)?;
    if previous.is_none() {
        let mut f = root
            .open_with(&path, OpenOptions::new().write(true).create_new(true))
            .map_err(err)?;
        f.write_all(&serde_json::to_vec(&record).map_err(err)?)
            .map_err(err)?;
        f.sync_all().map_err(err)?;
    }
    observe("prepared")?;
    if args["request"]["arguments"]["key"] == PAYLOAD_KEY {
        let parent = Path::new(source)
            .parent()
            .ok_or_else(|| err("payload parent missing"))?;
        // proposed() admitted the exact shipped path and read every existing
        // prefix with the same no-link confinement rule before creation.
        root.create_dir_all(parent).map_err(err)?;
    }
    // Exclusive temporary creation preserves unknown prior work after a crash.
    if let Some(existing) = crate::native_planning::read(&root, &temporary)? {
        if existing != bytes {
            return Err(err("unknown configuration temporary preserved"));
        }
    } else {
        let mut f = root
            .open_with(&temporary, OpenOptions::new().write(true).create_new(true))
            .map_err(err)?;
        if let Ok(metadata) = root.metadata(source) {
            f.set_permissions(metadata.permissions()).map_err(err)?;
        }
        f.write_all(&bytes).map_err(err)?;
        f.sync_all().map_err(err)?;
    }
    revalidate()?;
    if bound_sources(target, Some(source))? != args["binding"]["sources"]
        || crate::native_config::view(target)?["revision"]
            != args["binding"]["effective_policy_revision"]
    {
        return Err(err("configuration sources changed before publication"));
    }
    if args["binding"]["sources"][source].is_null() {
        root.hard_link(&temporary, &root, source).map_err(err)?;
        root.remove_file(&temporary).map_err(err)?;
    } else {
        root.rename(&temporary, &root, source).map_err(err)?;
    }
    let key = args["request"]["arguments"]["key"].as_str().unwrap();
    if deferred(target, source, key)?.is_some() {
        root.remove_file(deferred_path(source, key)?).map_err(err)?;
    }
    observe("published")?;
    let committed = crate::attempt_store::commit(
        json!({"target":target,"custody":admission["custody"],"outcome":out}),
    )?;
    Ok(json!({"outcome":out,"custody":committed["custody"]}))
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn interrupted_payload_publication_recovers_without_rewriting() {
        let target = std::env::temp_dir().join(format!(
            "aw-payload-recovery-{}-{}",
            std::process::id(),
            std::time::SystemTime::now()
                .duration_since(std::time::UNIX_EPOCH)
                .unwrap()
                .as_nanos()
        ));
        std::fs::create_dir(&target).unwrap();
        let discovery =
            resolve(&target, None)["configuration_write"]["payload_discovery_request"].clone();
        let request = resolve(&target, Some(discovery))["configuration_write"]["payload_choices"]
            [0]["request"]
            .clone();
        let source = request["arguments"]["source"].as_str().unwrap().to_owned();
        let mut answer = resolve(&target, Some(request))["decision_packet"]["decision_request"]["response_request"].clone();
        answer["arguments"]["answer"] = json!("authorize-write");
        let ready = resolve(&target, Some(answer));
        let action = ready["decision_packet"]["primary_action"].clone();
        let failed = execute_checked(
            &target,
            &ready["decision_packet"],
            &action,
            &mut || Ok(()),
            &mut |stage| {
                if stage == "published" {
                    Err(err("payload interruption"))
                } else {
                    Ok(())
                }
            },
        );
        assert!(
            failed
                .unwrap_err()
                .to_string()
                .contains("payload interruption")
        );
        let post = std::fs::read(target.join(&source)).unwrap();
        let discovery =
            resolve(&target, None)["configuration_write"]["payload_discovery_request"].clone();
        let rows = resolve(&target, Some(discovery));
        let recovery = rows["configuration_write"]["payload_choices"]
            .as_array()
            .unwrap()
            .iter()
            .find(|row| row["source"] == source)
            .unwrap()["recovery_request"]
            .clone();
        let recovery_action =
            resolve(&target, Some(recovery))["decision_packet"]["primary_action"].clone();
        assert_eq!(
            recovery_action["operation_id"],
            "configuration.recover-write"
        );
        let result = invoke(&target, recovery_action).unwrap();
        assert_eq!(result["value"]["material_written"], false);
        assert_eq!(std::fs::read(target.join(source)).unwrap(), post);
        assert!(invoke(&target, action).is_err());
        std::fs::remove_dir_all(target).unwrap();
    }
    #[test]
    fn interrupted_source_creation_recovers_publication_without_rewriting() {
        let target = std::env::temp_dir().join(format!(
            "aw-config-create-{}-{}",
            std::process::id(),
            std::time::SystemTime::now()
                .duration_since(std::time::UNIX_EPOCH)
                .unwrap()
                .as_nanos()
        ));
        std::fs::create_dir(&target).unwrap();
        let target = target.canonicalize().unwrap();
        let discovery =
            resolve(&target, None)["configuration_write"]["creation_discovery_request"].clone();
        let mut request =
            resolve(&target, Some(discovery))["configuration_write"]["creation_requests"]
                .as_array()
                .unwrap()
                .iter()
                .find(|r| {
                    r["arguments"]["source"] == SHARED
                        && r["arguments"]["key"] == "workspace.cli_invoke"
                })
                .unwrap()
                .clone();
        request["arguments"]["value"] = json!("fixture-native");
        let mut answer = resolve(&target,Some(request))["decision_packet"]["decision_request"]["response_request"].clone();
        answer["arguments"]["answer"] = json!("authorize-write");
        let ready = resolve(&target, Some(answer.clone()));
        let action = &ready["decision_packet"]["primary_action"];
        let failed = execute_checked(
            &target,
            &ready["decision_packet"],
            action,
            &mut || {
                crate::admit_invocation_value(
                    json!({"decision":resolve(&target,Some(answer.clone()))["decision_packet"],"invocation":action}),
                )?;
                Ok(())
            },
            &mut |stage| {
                if stage == "published" {
                    Err(err("fixture interruption"))
                } else {
                    Ok(())
                }
            },
        );
        assert!(
            failed
                .unwrap_err()
                .to_string()
                .contains("fixture interruption")
        );
        let bytes = std::fs::read(target.join(SHARED)).unwrap();
        let recovery =
            resolve(&target, None)["configuration_write"]["recovery_requests"][0].clone();
        let next = resolve(&target, Some(recovery))["decision_packet"]["primary_action"].clone();
        invoke(&target, next).unwrap();
        assert_eq!(std::fs::read(target.join(SHARED)).unwrap(), bytes);
        assert!(
            resolve(&target, None)["configuration_write"]["recovery_requests"]
                .as_array()
                .unwrap()
                .is_empty()
        );
        std::fs::remove_dir_all(target).unwrap();
    }
    fn context(target: &Path) -> Value {
        json!({"target":target,"task":"Authorize exact existing configuration correction"})
    }
    fn resolve(target: &Path, request: Option<Value>) -> Value {
        let mut c = context(target);
        if let Some(r) = request {
            c["request"] = r;
        }
        crate::native_public::start(c).unwrap()
    }
    fn invoke(target: &Path, invocation: Value) -> Result<Value, CoreError> {
        let mut c = context(target);
        c["invocation"] = invocation;
        crate::native_public::invoke_checked(c)
    }
    #[test]
    fn interrupted_configuration_write_recovers_without_rewriting_source() {
        for stage in ["prepared", "published", "drift"] {
            let target = std::env::temp_dir().join(format!(
                "aw-config-write-{}-{}",
                std::process::id(),
                std::time::SystemTime::now()
                    .duration_since(std::time::UNIX_EPOCH)
                    .unwrap()
                    .as_nanos()
            ));
            std::fs::create_dir_all(target.join(".agentic-workspace")).unwrap();
            std::fs::write(
                target.join(SHARED),
                "[workspace]\ncli_invoke='before' # human comment\n",
            )
            .unwrap();
            let mut request = resolve(&target, None)["configuration_write"]["requests"][0].clone();
            request["arguments"]["value"] = json!("after");
            let mut answer = resolve(&target, Some(request))["decision_packet"]["decision_request"]
                ["response_request"]
                .clone();
            answer["arguments"]["answer"] = json!("authorize-write");
            let ready = resolve(&target, Some(answer));
            let action = &ready["decision_packet"]["primary_action"];
            assert_eq!(action["operation_id"], "configuration.write");
            let error = execute_checked(
                &target,
                &ready["decision_packet"],
                action,
                &mut || Ok(()),
                &mut |s| {
                    if stage == "drift" && s == "prepared" {
                        std::fs::write(target.join(LOCAL), "# new policy source\n").unwrap();
                        Ok(())
                    } else if s == stage {
                        Err(err("simulated interruption"))
                    } else {
                        Ok(())
                    }
                },
            )
            .unwrap_err();
            if stage == "drift" {
                assert!(error.to_string().contains("sources changed"));
                assert!(
                    std::fs::read_to_string(target.join(SHARED))
                        .unwrap()
                        .contains("'before'")
                );
                std::fs::remove_dir_all(&target).unwrap();
                continue;
            }
            assert!(error.to_string().contains("simulated"));
            if stage == "prepared" {
                assert!(
                    std::fs::read_to_string(target.join(SHARED))
                        .unwrap()
                        .contains("'before'")
                );
                invoke(&target, action.clone()).unwrap();
            } else {
                let post = std::fs::read(target.join(SHARED)).unwrap();
                let current = resolve(&target, None);
                let recovery = current["configuration_write"]["recovery_requests"][0].clone();
                let recovery_action =
                    resolve(&target, Some(recovery))["decision_packet"]["primary_action"].clone();
                assert_eq!(
                    recovery_action["operation_id"],
                    "configuration.recover-write"
                );
                let result = invoke(&target, recovery_action).unwrap();
                assert_eq!(result["value"]["material_written"], false);
                assert_eq!(std::fs::read(target.join(SHARED)).unwrap(), post);
            }
            assert!(
                resolve(&target, None)["configuration_write"]["recovery_requests"]
                    .as_array()
                    .unwrap()
                    .is_empty()
            );
            assert!(invoke(&target, action.clone()).is_err());
            std::fs::remove_dir_all(&target).unwrap();
        }
    }
}
