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
const EFFECT: &str = "configuration-source";
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
    let mut observed = json!({});
    for source in [SHARED, LOCAL] {
        values[source] =
            match crate::native_config::load(&root, source, source_schema(source)?).map_err(err)? {
                Some((value, revision)) => {
                    if value["workspace"]["shared_config_path"]
                        .as_str()
                        .is_some_and(|p| p != SHARED)
                    {
                        return Err(err(
                            "redirected shared configuration is outside this writer boundary",
                        ));
                    }
                    observed[source] = value;
                    json!(revision)
                }
                None => Value::Null,
            };
    }
    if observed[SHARED]["workspace"]["enabled"] == false
        && observed[LOCAL]["workspace"]["enabled"] == true
    {
        return Err(err(
            "local enablement conflicts with stronger shared policy",
        ));
    }
    Ok(values)
}
fn proposed(target: &Path, source: &str, value: &str) -> Result<Vec<u8>, CoreError> {
    let root = Dir::open_ambient_dir(target, ambient_authority()).map_err(err)?;
    sources(target)?;
    let raw = read(&root, source)?;
    let text = std::str::from_utf8(&raw).map_err(err)?;
    if text.starts_with('\u{feff}') {
        return Err(err(
            "BOM configuration editing is not supported; source preserved",
        ));
    }
    let document = toml_edit::ImDocument::parse(text).map_err(err)?;
    let current = document
        .get("workspace")
        .and_then(|v| v.get("cli_invoke"))
        .and_then(toml_edit::Item::as_value);
    let rendered = if let Some(current) = current {
        if !current.is_str() {
            return Err(err("configuration invocation is not a string"));
        }
        let span = current
            .span()
            .ok_or_else(|| err("configuration literal span unavailable"))?;
        let mut rendered = text.to_owned();
        rendered.replace_range(span, &toml_edit::Value::from(value).to_string());
        rendered
    } else {
        let mut edited = text.parse::<toml_edit::DocumentMut>().map_err(err)?;
        let had_workspace = edited.contains_key("workspace");
        if !had_workspace {
            edited["workspace"] = toml_edit::Item::Table(toml_edit::Table::new());
        }
        let table = edited
            .get_mut("workspace")
            .and_then(toml_edit::Item::as_table_mut)
            .ok_or_else(|| err("invocation insertion requires an ordinary workspace table"))?;
        table.insert("cli_invoke", toml_edit::value(value));
        let rendered = edited.to_string();
        // Admission is narrower than TOML equivalence: removing only the exact
        // insertion must recover all prior bytes, including comments and policy.
        if had_workspace {
            edited["workspace"]
                .as_table_mut()
                .unwrap()
                .remove("cli_invoke");
        } else {
            edited.remove("workspace");
        }
        if edited.to_string() != text {
            return Err(err(
                "invocation insertion cannot preserve unrelated source bytes",
            ));
        }
        rendered
    };
    let parsed: toml::Value = toml::from_str(&rendered).map_err(err)?;
    let parsed = serde_json::to_value(parsed).map_err(err)?;
    let schema: Value = serde_json::from_str(source_schema(source)?).map_err(err)?;
    crate::schema_validator(&schema, "configuration write")?
        .validate(&parsed)
        .map_err(err)?;
    // This first slice does not arbitrate override policy. Explicit shared and
    // local values must agree after the edit; ambiguity cannot widen authority.
    let other = if source == SHARED { LOCAL } else { SHARED };
    if let Some((other, _)) =
        crate::native_config::load(&root, other, source_schema(other)?).map_err(err)?
        && other["workspace"]["cli_invoke"]
            .as_str()
            .is_some_and(|v| v != value)
    {
        return Err(err(
            "shared/local invocation conflict; no override authority inferred",
        ));
    }
    Ok(rendered.into_bytes())
}
pub(crate) fn contract() -> Result<Value, CoreError> {
    let args = json!({"$schema":"https://json-schema.org/draft/2020-12/schema","type":"object","properties":{"source":{"enum":[SHARED,LOCAL]},"key":{"const":"workspace.cli_invoke"},"value":{"type":"string","minLength":1,"maxLength":4096},"answer":{"enum":["authorize-write","defer"]},"proposal_revision":{"type":"string"}},"required":["source","key","value"],"additionalProperties":false});
    let recovery = json!({"$schema":"https://json-schema.org/draft/2020-12/schema","type":"object","properties":{"source":{"enum":[SHARED,LOCAL]},"record_revision":{"type":"string"}},"required":["source","record_revision"],"additionalProperties":false});
    let operation = |id: &str| json!({"id":id,"semantic_revision":"configuration-external-source-write-v2","input_schema":{"$schema":"https://json-schema.org/draft/2020-12/schema","type":"object","properties":{"target":{"type":"string"},"request":{"type":"object"},"binding":{"type":"object"},"post_revision":{"type":"string"}},"required":["target","request","binding","post_revision"],"additionalProperties":false},"result_kind":"agentic-workspace/configuration-write-result/v1","effects":[EFFECT],"reads":["configuration"]});
    let owner = json!({"owner":"configuration","revision":digest(&json!([args,recovery,"configuration-external-source-write-v2"]))?,"domains":["configuration"],"effects":[{"id":EFFECT,"domain":"configuration"}],"requests":[{"kind":EDIT,"result_kind":"agentic-workspace/configuration-write-proposal/v1","input_schema":args},{"kind":RECOVER,"result_kind":"agentic-workspace/configuration-write-result/v1","input_schema":recovery}],"operations":[operation("configuration.write"),operation("configuration.recover-write")]});
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
    json!({"status":"applied","effects":[EFFECT],"value":{"kind":"agentic-workspace/configuration-write-result/v1","source":invocation["arguments"]["request"]["arguments"]["source"],"post_revision":invocation["arguments"]["post_revision"],"source_ownership":"repo-human","continuing_custody":false,"completion_authority":false}})
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
pub(crate) fn view(
    target: &Path,
    work: &Value,
    config: &Value,
    contract: &Value,
    request: Option<&Value>,
) -> Result<Value, CoreError> {
    let owner = contract["owners"]
        .as_array()
        .unwrap()
        .iter()
        .find(|v| v["owner"] == "configuration")
        .unwrap();
    let mut result = json!({"requests":[],"recovery_requests":[],"status":"not-applicable","contribution":{"owner":"configuration","revision":owner["revision"],"actions":[]}});
    let current = match sources(target) {
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
    let root = Dir::open_ambient_dir(target, ambient_authority()).map_err(err)?;
    for source in [SHARED, LOCAL] {
        if let Some((v, revision)) =
            crate::native_config::load(&root, source, source_schema(source)?).map_err(err)?
        {
            let value = v["workspace"]["cli_invoke"]
                .as_str()
                .or(config["cli_invoke"].as_str())
                .unwrap_or("agentic-workspace");
            result["requests"].as_array_mut().unwrap().push(template(
                EDIT,
                json!({"source":source,"key":"workspace.cli_invoke","value":value}),
            ));
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
    let args = &request["arguments"];
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
        let other = if source == SHARED { LOCAL } else { SHARED };
        if current[other] != record["invocation"]["arguments"]["binding"]["sources"][other] {
            return Err(err("other configuration changed; recovery is stale"));
        }
        "configuration.recover-write"
    } else if request["request_kind"] == EDIT {
        let value = args["value"].as_str().ok_or_else(|| err("value missing"))?;
        let bytes = proposed(target, source, value)?;
        post = crate::native_intent::hash(&bytes);
        let before = read(&root, source)?;
        let parsed: toml::Value =
            toml::from_str(std::str::from_utf8(&before).map_err(err)?).map_err(err)?;
        let before_value = parsed
            .get("workspace")
            .and_then(|v| v.get("cli_invoke"))
            .and_then(toml::Value::as_str);
        if before_value == Some(value) {
            result["status"] = json!("unchanged");
            return Ok(result);
        }
        let proposal = digest(
            &json!({"binding":binding,"source":source,"key":args["key"],"value":value,"post_revision":post}),
        )?;
        if args["answer"].is_null() {
            let mut answer = request.clone();
            answer["arguments"]["proposal_revision"] = json!(proposal);
            result["status"] = json!("human-decision-required");
            result["proposal"] = json!({"before":before_value,"after":value,"source":source,"authority":"bounded-human-answer"});
            result["contribution"]["decisions"] = json!([{"id":"configuration-write-authorization","question":"Authorize this exact invocation-source edit? The source remains repo/human-owned.","response_request":{"request_kind":EDIT,"arguments":answer["arguments"]},"choices":[{"id":"authorize-write","label":"Authorize this exact write"},{"id":"defer","label":"Defer without mutation"}],"affects":["task","effect:configuration-source"]}]);
            return Ok(result);
        }
        if args["proposal_revision"] != proposal {
            return Err(err(
                "configuration answer is not bound to this exact proposal",
            ));
        }
        if args["answer"] == "defer" {
            result["status"] = json!("deferred");
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
pub(crate) fn execute(
    target: &Path,
    decision: &Value,
    invocation: &Value,
    mut revalidate: impl FnMut() -> Result<(), CoreError>,
) -> Result<Value, CoreError> {
    execute_checked(target, decision, invocation, &mut revalidate, &mut |_| {
        Ok(())
    })
}
fn execute_checked(
    target: &Path,
    decision: &Value,
    invocation: &Value,
    revalidate: &mut dyn FnMut() -> Result<(), CoreError>,
    observe: &mut dyn FnMut(&str) -> Result<(), CoreError>,
) -> Result<Value, CoreError> {
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
        args["request"]["arguments"]["value"].as_str().unwrap(),
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
    // Exclusive temporary creation preserves unknown prior work after a crash.
    if let Some(existing) = crate::native_planning::read(&root, &temporary)? {
        if existing != bytes {
            return Err(err("unknown configuration temporary preserved"));
        }
    } else {
        let mut f = root
            .open_with(&temporary, OpenOptions::new().write(true).create_new(true))
            .map_err(err)?;
        f.set_permissions(root.metadata(source).map_err(err)?.permissions())
            .map_err(err)?;
        f.write_all(&bytes).map_err(err)?;
        f.sync_all().map_err(err)?;
    }
    revalidate()?;
    if sources(target)? != args["binding"]["sources"]
        || crate::native_config::view(target)?["revision"]
            != args["binding"]["effective_policy_revision"]
    {
        return Err(err("configuration sources changed before publication"));
    }
    root.rename(&temporary, &root, source).map_err(err)?;
    observe("published")?;
    let committed = crate::attempt_store::commit(
        json!({"target":target,"custody":admission["custody"],"outcome":out}),
    )?;
    Ok(json!({"outcome":out,"custody":committed["custody"]}))
}

#[cfg(test)]
mod tests {
    use super::*;
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
        crate::native_public::invoke(c)
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
                "schema_version=1\n[workspace]\ncli_invoke='before' # human comment\n",
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
                        std::fs::write(
                            target.join(LOCAL),
                            "schema_version=1\n# new policy source\n",
                        )
                        .unwrap();
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
