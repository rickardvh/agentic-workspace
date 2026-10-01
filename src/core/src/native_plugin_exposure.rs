//! Optional Configuration-owned project plugin references. The canonical passive
//! bundle is payload-owned; no host manager runs here or during ordinary entry.
use crate::{CoreError, digest};
use cap_std::{
    ambient_authority,
    fs::{Dir, OpenOptions},
};
use serde_json::{Value, json};
use std::{io::Write, path::Path};

pub(crate) const READ: &str = "configuration/read-plugin-exposure/v1";
pub(crate) const EDIT: &str = "configuration/plugin-exposure/v1";
pub(crate) const OP: &str = "configuration.plugin-exposure";
const NAME: &str = "agentic-workspace-entry";
const BUNDLE: &str = ".agentic-workspace/plugins/agentic-workspace-entry";
const CATALOGUE: &str = ".agentic-workspace/plugins/.claude-plugin/marketplace.json";
const LOCK: &str = ".agentic-workspace/local/effects/configuration.lock";
const HOSTS: [&str; 3] = ["codex", "claude-project", "claude-local"];
fn err(e: impl ToString) -> CoreError {
    CoreError::new(e.to_string())
}
fn marker(host: &str) -> String {
    format!(".agentic-workspace/local/effects/plugin-exposure-{host}.json")
}
fn text(root: &Dir, path: &str) -> Result<Option<String>, CoreError> {
    crate::native_planning::read(root, path)?
        .map(|b| String::from_utf8(b).map_err(err))
        .transpose()
}
fn revision(value: &Option<String>) -> Value {
    value
        .as_ref()
        .map(|s| json!(crate::native_intent::hash(s.as_bytes())))
        .unwrap_or(Value::Null)
}
fn encode(value: &Value) -> Result<String, CoreError> {
    Ok(format!(
        "{}\n",
        serde_json::to_string_pretty(value).map_err(err)?
    ))
}
fn object(value: Option<&str>) -> Result<Value, CoreError> {
    let v = value
        .map(serde_json::from_str)
        .transpose()
        .map_err(err)?
        .unwrap_or(json!({}));
    if !v.is_object() {
        return Err(err("host configuration must be an object; preserve it"));
    }
    Ok(v)
}
pub(crate) fn declarations(owner: &mut Value) {
    owner["requests"].as_array_mut().unwrap().extend([
        json!({"kind":READ,"result_kind":"agentic-workspace/plugin-exposure/v1","input_schema":{"$schema":"https://json-schema.org/draft/2020-12/schema","type":"object","additionalProperties":false,"properties":{}}}),
        json!({"kind":EDIT,"result_kind":"agentic-workspace/plugin-exposure/v1","input_schema":{"$schema":"https://json-schema.org/draft/2020-12/schema","type":"object","additionalProperties":false,"required":["host","mode","expected_revision"],"properties":{"host":{"enum":HOSTS},"mode":{"enum":["expose","remove","recover"]},"expected_revision":{"type":"string"},"answer":{"enum":["authorize-write"]}}}}),
    ]);
    owner["operations"].as_array_mut().unwrap().push(json!({"id":OP,"semantic_revision":"project-entry-plugin-v1","input_schema":{"$schema":"https://json-schema.org/draft/2020-12/schema","type":"object","additionalProperties":false,"required":["target","request","binding","post_revision"],"properties":{"target":{"type":"string"},"request":{"type":"object"},"binding":{"type":"object"},"post_revision":{"type":"string"}}},"result_kind":"agentic-workspace/plugin-exposure-result/v1","effects":["configuration-source"],"reads":["configuration"]}));
}
fn retained(target: &Path, root: &Dir, host: &str) -> Result<Option<Value>, CoreError> {
    let Some(raw) = text(root, &marker(host))? else {
        return Ok(None);
    };
    let r: Value = serde_json::from_str(&raw).map_err(err)?;
    let attempt = crate::attempt_store::read_source(
        target.to_str().unwrap(),
        &serde_json::from_value(r["custody"]["attempt"].clone()).map_err(err)?,
    )?;
    let i = &r["invocation"];
    if attempt["invocation"] != *i
        || i["operation_id"] != OP
        || i["source_owner"] != "configuration"
        || i["arguments"]["target"] != json!(target)
        || i["arguments"]["request"]["arguments"]["host"] != host
    {
        return Err(err(
            "plugin exposure custody invalid; preserve all surfaces",
        ));
    }
    Ok(Some(r))
}
fn outcome(i: &Value) -> Value {
    let s = &i["arguments"]["binding"]["state"];
    json!({"status":"applied","effects":["configuration-source"],"value":{"kind":"agentic-workspace/plugin-exposure-result/v1","host":s["host"],"mode":s["mode"],"selector":s["selector"],"host_actions":s["host_actions"],"authority_effect":"discovery-only","completion_authority":false}})
}
fn committed(target: &Path, root: &Dir, record: &Value) -> Result<bool, CoreError> {
    let prepared = crate::attempt_store::prepare_commit(
        target.to_str().unwrap(),
        record["custody"].clone(),
        outcome(&record["invocation"]),
    )?;
    if text(
        root,
        prepared["custody"]["committed"]["path"].as_str().unwrap(),
    )?
    .is_none()
    {
        return Ok(false);
    }
    crate::attempt_store::inspect_committed(target.to_str().unwrap(), prepared["custody"].clone())?;
    Ok(true)
}
// Exact fragment custody allows unrelated host edits without adopting a matching
// unowned fragment. Missing/changed owned fields are collisions, including false.
fn field(
    map: &mut Value,
    key: &str,
    prior: &Value,
    desired: Option<Value>,
) -> Result<(), CoreError> {
    let old = map.get(key).cloned().unwrap_or(Value::Null);
    if old != *prior {
        return Err(err(format!(
            "unowned or modified plugin field {key}; preserve it"
        )));
    }
    if let Some(v) = desired {
        map[key] = v;
    } else {
        map.as_object_mut()
            .ok_or_else(|| err("host settings malformed"))?
            .remove(key);
    }
    Ok(())
}
fn observe(target: &Path, host: &str, mode: &str) -> Result<Value, CoreError> {
    let root = Dir::open_ambient_dir(target, ambient_authority()).map_err(err)?;
    let record = retained(target, &root, host)?;
    if let Some(r) = &record
        && !committed(target, &root, r)?
    {
        let previous = &r["invocation"]["arguments"]["binding"]["state"];
        for (path, update) in previous["updates"]
            .as_object()
            .ok_or_else(|| err("plugin recovery updates missing"))?
        {
            let current = text(&root, path)?;
            if revision(&current) != update["before"]
                && current != update["after"].as_str().map(str::to_owned)
            {
                return Err(err(format!(
                    "{path}: interrupted plugin source changed; preserve"
                )));
            }
        }
        return Ok(
            json!({"host":host,"mode":mode,"status":"recovery-required","pending":r,"observations":previous["updates"].as_object().unwrap().keys().map(|p| Ok((p.clone(),revision(&text(&root,p)?)))).collect::<Result<serde_json::Map<String,Value>,CoreError>>()?}),
        );
    }
    if mode == "recover" {
        return Err(err("no interrupted plugin exposure"));
    }
    let prior = record
        .as_ref()
        .map(|r| &r["invocation"]["arguments"]["binding"]["state"]);
    let active = prior.is_some_and(|s| s["mode"] == "expose");
    let namespace = prior
        .and_then(|s| s["marketplace"].as_str())
        .map(str::to_owned)
        .unwrap_or(format!("aw-entry-{}", &digest(&json!(target))?[7..23]));
    let removing = mode == "remove";
    let local_ignored = if host == "claude-local" {
        Some(
            std::process::Command::new("git")
                .args([
                    "-C",
                    target.to_str().unwrap(),
                    "check-ignore",
                    "--quiet",
                    "--",
                    ".claude/settings.local.json",
                ])
                .status()
                .map_err(err)?
                .success(),
        )
    } else {
        None
    };
    let mut observations = json!({});
    let mut updates = json!({});
    let mut fragments = json!({});
    let mut add = |path: &str, after: Option<String>| -> Result<(), CoreError> {
        crate::native_skill_exposure::no_link_directory(
            &root,
            Path::new(path).parent().unwrap().to_str().unwrap(),
        )?;
        let before = text(&root, path)?;
        observations[path] = revision(&before);
        if before != after {
            updates[path] = json!({"before":revision(&before),"after":after});
        }
        Ok(())
    };
    let old = if active {
        prior.unwrap()["fragments"].clone()
    } else {
        json!({})
    };
    let mut marketplace = namespace.clone();
    if host == "codex" {
        let path = ".agents/plugins/marketplace.json";
        let before = text(&root, path)?;
        let mut catalog = object(before.as_deref())?;
        if let Some(name) = catalog["name"].as_str() {
            marketplace = name.to_owned();
        }
        if marketplace.is_empty()
            || !marketplace
                .bytes()
                .all(|c| c.is_ascii_lowercase() || c.is_ascii_digit() || c == b'-')
        {
            return Err(err(
                "marketplace name must be a lowercase host identifier; preserve",
            ));
        }
        if active && prior.unwrap()["marketplace"] != marketplace {
            return Err(err("owned marketplace name changed; preserve"));
        }
        if catalog.get("plugins").is_none() {
            catalog["plugins"] = json!([]);
        }
        let plugins = catalog["plugins"]
            .as_array_mut()
            .ok_or_else(|| err("marketplace plugins must be an array"))?;
        let positions: Vec<_> = plugins
            .iter()
            .enumerate()
            .filter(|(_, v)| v["name"] == NAME)
            .map(|(n, _)| n)
            .collect();
        if positions.len() > 1
            || positions
                .first()
                .map(|n| plugins[*n].clone())
                .unwrap_or(Value::Null)
                != old["entry"]
        {
            return Err(err("unowned or modified marketplace entry; preserve"));
        }
        if let Some(n) = positions.first() {
            plugins.remove(*n);
        }
        if !removing {
            let entry = json!({"name":NAME,"source":{"source":"local","path":format!("./{BUNDLE}")},"policy":{"installation":"AVAILABLE","authentication":"ON_INSTALL"},"category":"Productivity"});
            plugins.push(entry.clone());
            fragments["entry"] = entry;
            catalog["name"] = json!(marketplace);
        }
        // Remove only the catalogue created by us when it has no other content.
        let empty = removing
            && catalog["plugins"] == json!([])
            && catalog
                .as_object()
                .unwrap()
                .keys()
                .all(|k| k == "name" || k == "plugins")
            && prior.is_some_and(|s| s["catalogue_created"] == true);
        add(
            path,
            if empty {
                None
            } else if removing && !active {
                before.clone()
            } else {
                Some(encode(&catalog)?)
            },
        )?;
        fragments["catalogue_created"] = json!(if active {
            prior.unwrap()["catalogue_created"] == true
        } else {
            before.is_none()
        });
        let selector = format!("{NAME}@{marketplace}");
        let path = ".codex/config.toml";
        let before = text(&root, path)?;
        let mut doc: toml_edit::DocumentMut =
            before.as_deref().unwrap_or("").parse().map_err(err)?;
        let observed = doc
            .get("plugins")
            .and_then(|v| v.get(&selector))
            .map(|v| v.to_string().trim().to_owned());
        if observed.as_ref().map(|s| json!(s)).unwrap_or(Value::Null) != old["config_entry"] {
            return Err(err("unowned or modified Codex plugin config; preserve"));
        }
        if removing {
            if let Some(t) = doc
                .get_mut("plugins")
                .and_then(toml_edit::Item::as_table_like_mut)
            {
                t.remove(&selector);
                if t.is_empty() {
                    doc.remove("plugins");
                }
            }
        } else {
            doc["plugins"][&selector]["enabled"] = toml_edit::value(true);
            fragments["config_entry"] = json!(doc["plugins"][&selector].to_string().trim());
        }
        add(
            path,
            if removing
                && doc.to_string().trim().is_empty()
                && prior.is_some_and(|s| s["config_created"] == true)
            {
                None
            } else if removing && !active {
                before.clone()
            } else {
                Some(doc.to_string())
            },
        )?;
        fragments["config_created"] = json!(if active {
            prior.unwrap()["config_created"] == true
        } else {
            before.is_none()
        });
    } else {
        let other = if host == "claude-project" {
            "claude-local"
        } else {
            "claude-project"
        };
        if let Some(r) = retained(target, &root, other)?
            && r["invocation"]["arguments"]["binding"]["state"]["mode"] == "expose"
        {
            return Err(err(
                "remove the other Claude scope before changing scope; never promote local state",
            ));
        }
        let selector = format!("{NAME}@{marketplace}");
        let before = text(&root, CATALOGUE)?;
        let expected = if active {
            old["catalogue"].as_str().map(str::to_owned)
        } else {
            None
        };
        if before != expected {
            return Err(err(
                "unowned or modified repository Claude catalogue; preserve",
            ));
        }
        let catalogue = encode(
            &json!({"name":marketplace,"owner":{"name":"Agentic Workspace"},"plugins":[{"name":NAME,"source":format!("./{NAME}")}]}),
        )?;
        add(
            CATALOGUE,
            if removing {
                None
            } else {
                Some(catalogue.clone())
            },
        )?;
        if !removing {
            fragments["catalogue"] = json!(catalogue);
        }
        let path = if host == "claude-project" {
            ".claude/settings.json"
        } else {
            ".claude/settings.local.json"
        };
        let before = text(&root, path)?;
        let mut settings = object(before.as_deref())?;
        {
            for (group, key, value) in [
                ("enabledPlugins", selector.as_str(), json!(true)),
                (
                    "extraKnownMarketplaces",
                    marketplace.as_str(),
                    json!({"source":{"source":"directory","path":"./.agentic-workspace/plugins"}}),
                ),
            ] {
                if settings.get(group).is_none() {
                    settings[group] = json!({});
                }
                if !settings[group].is_object() {
                    return Err(err("Claude settings group must be an object"));
                }
                field(
                    &mut settings[group],
                    key,
                    &old[group],
                    if removing { None } else { Some(value.clone()) },
                )?;
                if !removing {
                    fragments[group] = value;
                }
                if removing && settings[group] == json!({}) {
                    settings.as_object_mut().unwrap().remove(group);
                }
            }
        }
        add(
            path,
            if removing
                && settings == json!({})
                && prior.is_some_and(|s| s["config_created"] == true)
            {
                None
            } else if removing && !active {
                before.clone()
            } else {
                Some(encode(&settings)?)
            },
        )?;
        fragments["config_created"] = json!(if active {
            prior.unwrap()["config_created"] == true
        } else {
            before.is_none()
        });
    }
    let mut bundle = json!({});
    if !removing {
        for suffix in [
            "plugin.json",
            ".claude-plugin/plugin.json",
            "skills/agentic-workspace-entry/SKILL.md",
        ] {
            let path = format!("{BUNDLE}/{suffix}");
            let body = text(&root, &path)?.ok_or_else(|| {
                err("canonical entry bundle missing; use repository adoption/refresh")
            })?;
            observations[&path] = revision(&Some(body.clone()));
            bundle[&path] = json!(body);
        }
    }
    let selector = format!("{NAME}@{marketplace}");
    let bundle_revision = digest(&bundle)?;
    let refresh_needed =
        !removing && active && prior.unwrap()["bundle_revision"] != bundle_revision;
    let host_actions = if removing || (active && !refresh_needed) {
        json!([])
    } else {
        host_actions(host, &marketplace, refresh_needed)
    };
    Ok(
        json!({"host":host,"mode":mode,"status":if active {"owned"} else {"absent"},"marketplace":marketplace,"selector":selector,"local_settings_ignored":local_ignored,"observations":observations,"updates":updates,"fragments":fragments,"catalogue_created":fragments["catalogue_created"],"config_created":fragments["config_created"],"bundle_revision":bundle_revision,"refresh_needed":refresh_needed,"host_actions":host_actions,"prior_custody":record.as_ref().map(digest).transpose()?}),
    )
}
fn host_actions(host: &str, marketplace: &str, refresh_needed: bool) -> Value {
    let selector = format!("{NAME}@{marketplace}");
    let scope = if host == "claude-local" {
        "local"
    } else {
        "project"
    };
    if host == "codex" {
        json!([
            "Refresh the repository plugin view in Codex, then restart the session in this trusted repository. Project config enables the plugin; the host may cache its bytes."
        ])
    } else if refresh_needed {
        json!([
            format!("claude plugin marketplace update {marketplace}"),
            format!("claude plugin update {selector} --scope {scope}"),
            "Start a new Claude session or run /reload-plugins."
        ])
    } else {
        json!([
            "Start Claude Code in this repository and trust its settings to register the declared repository marketplace. Plugin bytes remain per-machine.",
            format!("claude plugin install {selector} --scope {scope}"),
            "Start a new Claude session or run /reload-plugins. Each collaborator installs plugin bytes on their own machine."
        ])
    }
}
/// Bind host cache consequences to an adoption proposal's exact bundle
/// postimages. Ordinary entry delivers no plugin-manager action.
pub(crate) fn refresh_actions(target: &Path, updates: &Value) -> Result<Value, CoreError> {
    let root = Dir::open_ambient_dir(target, ambient_authority()).map_err(err)?;
    let mut bundle = json!({});
    for suffix in [
        "plugin.json",
        ".claude-plugin/plugin.json",
        "skills/agentic-workspace-entry/SKILL.md",
    ] {
        let path = format!("{BUNDLE}/{suffix}");
        let body = if let Some(update) = updates.get(&path) {
            update["after"].as_str().map(str::to_owned)
        } else {
            text(&root, &path)?
        };
        let Some(body) = body else {
            return Ok(json!([]));
        };
        bundle[&path] = json!(body);
    }
    let revision = digest(&bundle)?;
    let mut actions = Vec::new();
    for host in HOSTS {
        if let Some(r) = retained(target, &root, host)?
            && committed(target, &root, &r)?
        {
            let s = &r["invocation"]["arguments"]["binding"]["state"];
            if s["mode"] == "expose" && s["bundle_revision"] != revision {
                actions.push(json!({"host":host,"selector":s["selector"],"bundle_revision":revision,"host_actions":host_actions(host,s["marketplace"].as_str().unwrap(),true)}));
            }
        }
    }
    Ok(json!(actions))
}

pub(crate) fn removal_barriers(
    target: &Path,
    template: &dyn Fn(&str, Value) -> Value,
) -> Result<Vec<Value>, CoreError> {
    let root = Dir::open_ambient_dir(target, ambient_authority()).map_err(err)?;
    let mut rows = Vec::new();
    for host in HOSTS {
        if let Some(r) = retained(target, &root, host)?
            && (r["invocation"]["arguments"]["binding"]["state"]["mode"] == "expose"
                || !committed(target, &root, &r)?)
        {
            match observe(target,host,"remove") {
                Ok(s) => rows.push(json!({"state":s,"remove_request":template(EDIT,json!({"host":host,"mode":"remove","expected_revision":digest(&s)?}))})),
                Err(e) => rows.push(json!({"state":{"host":host,"status":"preserved-blocked","gap":e.to_string()}})),
            }
        }
    }
    Ok(rows)
}
pub(crate) fn view(
    target: &Path,
    request: &Value,
    binding: &Value,
    template: &dyn Fn(&str, Value) -> Value,
    result: &mut Value,
) -> Result<(), CoreError> {
    if request["request_kind"] == READ {
        let mut rows = Vec::new();
        for host in HOSTS {
            match observe(target, host, "expose").or_else(|_| observe(target, host, "remove")) {
                Ok(s) => {
                    let remove = observe(target, host, "remove")?;
                    rows.push(json!({"state":s,"expose_request":template(EDIT,json!({"host":host,"mode":"expose","expected_revision":digest(&s)?})),"remove_request":template(EDIT,json!({"host":host,"mode":"remove","expected_revision":digest(&remove)?})),"recovery_request":if s["status"] == "recovery-required" {Some(template(EDIT,json!({"host":host,"mode":"recover","expected_revision":digest(&observe(target,host,"recover")?)?})))} else {None}}));
                }
                Err(e) => rows.push(
                    json!({"state":{"host":host,"status":"preserved-blocked","gap":e.to_string()}}),
                ),
            }
        }
        result["status"] = json!("plugin-exposure-delivered");
        result["plugin_exposure"] = json!(rows);
        return Ok(());
    }
    let a = &request["arguments"];
    let host = a["host"]
        .as_str()
        .ok_or_else(|| err("plugin host missing"))?;
    if !HOSTS.contains(&host) {
        return Err(err("unsupported plugin host"));
    }
    let mode = a["mode"]
        .as_str()
        .ok_or_else(|| err("plugin mode missing"))?;
    let state = observe(target, host, mode)?;
    if a["expected_revision"] != digest(&state)? {
        return Err(err("plugin exposure changed; reobserve"));
    }
    result["plugin_exposure"] = state.clone();
    if host == "claude-local" && mode == "expose" && state["local_settings_ignored"] != true {
        result["status"] = json!("local-settings-ignore-required");
        result["next_step"] = json!(
            "Exclude .claude/settings.local.json using this checkout's existing local Git ignore policy, then request fresh local exposure. AW never promotes local settings into shared state."
        );
        return Ok(());
    }
    if state["status"] == "recovery-required" && mode != "recover" {
        result["status"] = json!("recovery-required");
        return Ok(());
    }
    if mode == "remove" && state["status"] == "absent" {
        result["status"] = json!("unchanged");
        return Ok(());
    }
    if mode == "expose"
        && state["status"] == "owned"
        && state["updates"] == json!({})
        && state["refresh_needed"] == false
    {
        result["status"] = json!("unchanged");
        return Ok(());
    }
    if a["answer"] != "authorize-write" {
        result["status"] = json!("authorization-required");
        result["authorization_request"] = request.clone();
        result["contribution"]["decisions"] = json!([{"id":"plugin-exposure-authorization","question":"Authorize these exact repository plugin references? Host cache installation remains an explicit host action.","material":state,"response_request":{"request_kind":EDIT,"arguments":a},"choices":[{"id":"authorize-write","label":"Authorize repository plugin exposure"}],"affects":["effect:configuration-source"]}]);
        return Ok(());
    }
    result["status"] = json!("write-ready");
    result["contribution"]["actions"] = json!([{"operation_id":OP,"dependency_revision":digest(&json!([binding,request,state]))?,"arguments":{"target":target,"request":request,"binding":{"policy":binding,"state":state},"post_revision":digest(&state)?},"effects":["configuration-source"],"source_requests":[request]}]);
    Ok(())
}
pub(crate) fn write_scope(i: &Value) -> Result<Vec<String>, CoreError> {
    let host = i["arguments"]["request"]["arguments"]["host"]
        .as_str()
        .ok_or_else(|| err("host missing"))?;
    let state = &i["arguments"]["binding"]["state"];
    let state = if state["mode"] == "recover" {
        &state["pending"]["invocation"]["arguments"]["binding"]["state"]
    } else {
        state
    };
    let mut paths =
        crate::attempt_store::write_paths(&json!({"idempotency_key":i["logical_effect_id"]}))?;
    paths.extend([LOCK.into(), marker(host), format!("{}.*.tmp", marker(host))]);
    for path in state["updates"]
        .as_object()
        .ok_or_else(|| err("updates missing"))?
        .keys()
    {
        paths.extend([path.clone(), format!("{path}.*.tmp")]);
    }
    Ok(paths)
}
pub(crate) fn execute(
    target: &Path,
    decision: &Value,
    i: &Value,
    mut revalidate: impl FnMut() -> Result<(), CoreError>,
) -> Result<Value, CoreError> {
    let root = Dir::open_ambient_dir(target, ambient_authority()).map_err(err)?;
    text(&root, LOCK)?;
    root.create_dir_all(".agentic-workspace/local/effects")
        .map_err(err)?;
    let lock = root
        .open_with(LOCK, OpenOptions::new().read(true).write(true).create(true))
        .map_err(err)?
        .into_std();
    if lock.metadata().map_err(err)?.len() != 0 {
        return Err(err("unknown Configuration lock preserved"));
    }
    lock.try_lock().map_err(err)?;
    revalidate()?;
    let state = &i["arguments"]["binding"]["state"];
    let recovery = state["mode"] == "recover";
    let original = if recovery {
        &state["pending"]["invocation"]
    } else {
        i
    };
    let host = i["arguments"]["request"]["arguments"]["host"]
        .as_str()
        .unwrap();
    let admission =
        crate::attempt_store::admit(json!({"target":target,"decision":decision,"invocation":i}))?;
    if !recovery {
        let temporary = format!("{}.{}.tmp", marker(host), &digest(i)?[7..]);
        let mut file = root
            .open_with(&temporary, OpenOptions::new().write(true).create_new(true))
            .map_err(err)?;
        file.write_all(encode(&json!({"invocation":i,"custody":admission["custody"]}))?.as_bytes())
            .map_err(err)?;
        file.sync_all().map_err(err)?;
        drop(file);
        root.rename(&temporary, &root, marker(host)).map_err(err)?;
    }
    crate::native_adoption::publish(
        &root,
        &original["arguments"]["binding"]["state"]["updates"],
        original,
        recovery,
    )?;
    if recovery {
        crate::attempt_store::commit(
            json!({"target":target,"custody":state["pending"]["custody"],"outcome":outcome(original)}),
        )?;
    }
    let out = if recovery {
        json!({"status":"applied","effects":["configuration-source"],"value":{"kind":"agentic-workspace/plugin-exposure-result/v1","host":host,"mode":"recover","completion_authority":false}})
    } else {
        outcome(i)
    };
    let committed = crate::attempt_store::commit(
        json!({"target":target,"custody":admission["custody"],"outcome":out}),
    )?;
    Ok(
        json!({"outcome":out,"custody":committed["custody"],"post_effect_changed_paths":original["arguments"]["binding"]["state"]["updates"].as_object().unwrap().keys().collect::<Vec<_>>()}),
    )
}
