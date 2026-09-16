//! Configuration-owned, passive discovery links to canonical product bundles.
//! No second catalogue, copied procedure, helper execution or activation grant.
use crate::{CoreError, digest};
use cap_std::{
    ambient_authority,
    fs::{Dir, OpenOptions},
};
use serde_json::{Value, json};
use std::{io::Write, path::Path};

pub(crate) const READ: &str = "configuration/read-skill-exposure/v1";
pub(crate) const EDIT: &str = "configuration/skill-exposure/v1";
pub(crate) const OP: &str = "configuration.skill-exposure";
const REGISTRY: &str = ".agentic-workspace/skills/REGISTRY.json";
fn err(e: impl ToString) -> CoreError {
    CoreError::new(e.to_string())
}

fn path(name: &str) -> String {
    format!(".agents/skills/{name}")
}
fn destination(name: &str) -> String {
    format!("../../.agentic-workspace/skills/{name}")
}
fn marker(name: &str) -> String {
    format!(".agentic-workspace/local/effects/skill-exposure-{name}.json")
}

pub(crate) fn declarations(owner: &mut Value) {
    owner["requests"].as_array_mut().unwrap().extend([
        json!({"kind":READ,"result_kind":"agentic-workspace/skill-exposure/v1","input_schema":{"$schema":"https://json-schema.org/draft/2020-12/schema","type":"object","additionalProperties":false,"properties":{}}}),
        json!({"kind":EDIT,"result_kind":"agentic-workspace/skill-exposure/v1","input_schema":{"$schema":"https://json-schema.org/draft/2020-12/schema","type":"object","additionalProperties":false,"required":["name","mode","expected_revision"],"properties":{"name":{"type":"string","pattern":"^[a-z0-9-]{1,64}$"},"mode":{"enum":["expose","remove","recover"]},"expected_revision":{"type":"string"},"answer":{"enum":["authorize-write"]}}}}),
    ]);
    owner["operations"].as_array_mut().unwrap().push(json!({"id":OP,"semantic_revision":"passive-skill-exposure-v1","input_schema":{"$schema":"https://json-schema.org/draft/2020-12/schema","type":"object","properties":{"target":{"type":"string"},"request":{"type":"object"},"binding":{"type":"object"},"post_revision":{"type":"string"}},"required":["target","request","binding","post_revision"],"additionalProperties":false},"result_kind":"agentic-workspace/skill-exposure-result/v1","effects":["configuration-source"],"reads":["configuration"]}));
}

fn valid_name(name: &str) -> bool {
    !name.is_empty()
        && name.len() <= 64
        && name
            .bytes()
            .all(|b| b.is_ascii_lowercase() || b.is_ascii_digit() || b == b'-')
}
fn names(root: &Dir) -> Result<Vec<String>, CoreError> {
    let Some(raw) = crate::native_planning::read(root, REGISTRY)? else {
        return Ok(Vec::new());
    };
    let registry: Value = serde_json::from_slice(&raw).map_err(err)?;
    let mut names = Vec::new();
    for row in registry["skills"]
        .as_array()
        .ok_or_else(|| err("skill registry malformed"))?
    {
        if !matches!(
            (row["scope"].as_str(), row["visibility"].as_str()),
            (Some("main-operating-skill"), Some("ordinary-default"))
                | (Some("specialized-subskill"), Some("routed-on-demand"))
        ) {
            continue;
        }
        let name = row["id"]
            .as_str()
            .ok_or_else(|| err("skill identity missing"))?;
        if name.is_empty()
            || name.len() > 64
            || !name
                .bytes()
                .all(|b| b.is_ascii_lowercase() || b.is_ascii_digit() || b == b'-')
            || row["path"] != format!("{name}/SKILL.md")
            || names.contains(&name.to_owned())
        {
            return Err(err("noncanonical or duplicate skill identity"));
        }
        names.push(name.to_owned());
    }
    Ok(names)
}

fn no_link_directory(root: &Dir, path: &str) -> Result<(), CoreError> {
    let mut prefix = std::path::PathBuf::new();
    for part in path.split('/') {
        prefix.push(part);
        match root.symlink_metadata(&prefix) {
            Ok(meta) => {
                #[cfg(windows)]
                let linked = {
                    use cap_std::fs::MetadataExt;
                    meta.file_attributes() & 0x400 != 0
                };
                #[cfg(not(windows))]
                let linked = meta.is_symlink();
                if linked || !meta.is_dir() {
                    return Err(err(
                        "skill exposure parent is not an ordinary directory; preserve it",
                    ));
                }
            }
            Err(e) if e.kind() == std::io::ErrorKind::NotFound => break,
            Err(e) => return Err(err(e)),
        }
    }
    Ok(())
}
fn retained(target: &Path, root: &Dir, name: &str) -> Result<Option<Value>, CoreError> {
    let Some(raw) = crate::native_planning::read(root, &marker(name))? else {
        return Ok(None);
    };
    let record: Value = serde_json::from_slice(&raw).map_err(err)?;
    let evidence = serde_json::from_value(record["custody"]["attempt"].clone()).map_err(err)?;
    let attempt = crate::attempt_store::read_source(target.to_str().unwrap(), &evidence)?;
    let i = &record["invocation"];
    if attempt["invocation"] != *i
        || i["operation_id"] != OP
        || i["arguments"]["target"] != target.to_str().unwrap()
        || i["arguments"]["request"]["arguments"]["name"] != name
        || !matches!(
            i["arguments"]["request"]["arguments"]["mode"].as_str(),
            Some("expose" | "remove")
        )
    {
        return Err(err(
            "skill exposure ownership evidence invalid; preserve it",
        ));
    }
    Ok(Some(record))
}
fn observed_link(target: &Path, root: &Dir, name: &str) -> Result<bool, CoreError> {
    #[cfg(unix)]
    {
        let _ = target;
        Ok(root.read_link_contents(path(name)).map_err(err)? == Path::new(&destination(name)))
    }
    #[cfg(windows)]
    {
        let _ = root;
        let observed = junction::get_target(target.join(path(name))).map_err(err)?;
        let expected = target.join(format!(".agentic-workspace/skills/{name}"));
        let normalize = |p: &Path| p.to_string_lossy().trim_start_matches(r"\\?\").to_owned();
        Ok(normalize(&observed) == normalize(&expected))
    }
}
fn state(target: &Path, root: &Dir, name: &str) -> Result<Value, CoreError> {
    no_link_directory(root, ".agents/skills")?;
    let canonical = format!(".agentic-workspace/skills/{name}");
    no_link_directory(root, &canonical)?;
    let raw = crate::native_planning::read(root, &format!("{canonical}/SKILL.md"))?;
    let record = retained(target, root, name)?;
    let owned = record.is_some();
    let observed = match root.symlink_metadata(path(name)) {
        Err(e) if e.kind() == std::io::ErrorKind::NotFound => json!({"status":"absent"}),
        Err(e) => return Err(err(e)),
        Ok(_) => match observed_link(target, root, name) {
            Ok(true) if owned => {
                json!({"status":"owned","destination":destination(name)})
            }
            _ => {
                json!({"status":"collision","recovery":"Preserve this path. Move or reconcile the conflicting host skill explicitly, then request fresh exposure. Never overwrite or adopt an unowned link."})
            }
        },
    };
    Ok(
        json!({"name":name,"canonical":canonical,"body_revision":raw.as_ref().map(|bytes|crate::native_intent::hash(bytes)),"ownership_revision":record.as_ref().map(|r|digest(&r["invocation"])).transpose()?,"observed":observed}),
    )
}

fn outcome(invocation: &Value) -> Value {
    let args = &invocation["arguments"]["request"]["arguments"];
    let name = args["name"].as_str().unwrap();
    json!({"status":"applied","effects":["configuration-source"],"value":{"kind":"agentic-workspace/skill-exposure-result/v1","name":name,"mode":args["mode"],"source":path(name),"canonical":format!(".agentic-workspace/skills/{name}"),"authority_effect":"discovery-only","completion_authority":false}})
}
fn recoverable(
    target: &Path,
    root: &Dir,
    name: &str,
    state: &Value,
) -> Result<Option<Value>, CoreError> {
    let Some(record) = retained(target, root, name)? else {
        return Ok(None);
    };
    let exposed = state["observed"]["status"] == "owned";
    let mode = &record["invocation"]["arguments"]["request"]["arguments"]["mode"];
    if state["observed"]["status"] == "collision" || exposed != (*mode == "expose") {
        return Ok(None);
    }
    let prepared = crate::attempt_store::prepare_commit(
        target.to_str().unwrap(),
        record["custody"].clone(),
        outcome(&record["invocation"]),
    )?;
    if let Some(raw) = crate::native_planning::read(
        root,
        prepared["custody"]["committed"]["path"].as_str().unwrap(),
    )? {
        let actual: Value = serde_json::from_slice(&raw).map_err(err)?;
        if actual != prepared["record"] {
            return Err(err("exposure result evidence differs; preserve it"));
        }
        return Ok(None);
    }
    Ok(Some(record))
}

pub(crate) fn view(
    target: &Path,
    request: &Value,
    binding: &Value,
    template: &dyn Fn(&str, Value) -> Value,
    result: &mut Value,
) -> Result<(), CoreError> {
    let root = Dir::open_ambient_dir(target, ambient_authority()).map_err(err)?;
    let selected = names(&root)?;
    if request["request_kind"] == READ {
        let mut rows = Vec::new();
        let mut visible = selected.clone();
        no_link_directory(&root, ".agents/skills")?;
        if let Ok(entries) = root.read_dir(".agents/skills") {
            for (index, entry) in entries.enumerate() {
                if index >= 1024 {
                    return Err(err("host skill directory exceeds bounded discovery"));
                }
                let entry = entry.map_err(err)?;
                let name = entry.file_name().to_string_lossy().into_owned();
                if !valid_name(&name) || visible.contains(&name) {
                    continue;
                }
                if retained(target, &root, &name)?.is_some() {
                    visible.push(name);
                }
            }
        }
        for name in visible {
            let state = state(target, &root, &name)?;
            let revision = digest(&state)?;
            rows.push(json!({"state":state,"expose_request":if selected.contains(&name){template(EDIT,json!({"name":name,"mode":"expose","expected_revision":revision}))}else{Value::Null},"remove_request":template(EDIT,json!({"name":name,"mode":"remove","expected_revision":revision})),"recovery_request":if recoverable(target,&root,&name,&state)?.is_some(){template(EDIT,json!({"name":name,"mode":"recover","expected_revision":revision}))}else{Value::Null}}));
        }
        result["status"] = json!("skill-exposure-delivered");
        result["skill_exposure"] = json!(rows);
        return Ok(());
    }
    let args = &request["arguments"];
    let name = args["name"]
        .as_str()
        .ok_or_else(|| err("skill identity missing"))?;
    if !valid_name(name) {
        return Err(err("invalid skill identity"));
    }
    if !selected.iter().any(|n| n == name)
        && (args["mode"] == "expose" || retained(target, &root, name)?.is_none())
    {
        return Err(err(
            "skill is not a discoverable product procedure or owned exposure",
        ));
    }
    if name.is_empty()
        || name.len() > 64
        || !name
            .bytes()
            .all(|b| b.is_ascii_lowercase() || b.is_ascii_digit() || b == b'-')
    {
        return Err(err("invalid skill identity"));
    }
    let state = state(target, &root, name)?;
    if args["expected_revision"] != digest(&state)? {
        return Err(err("skill exposure changed; request fresh material"));
    }
    if state["observed"]["status"] == "collision" {
        result["status"] = json!("collision-preserved");
        result["skill_exposure"] = state;
        return Ok(());
    }
    if args["mode"] == "expose" && state["body_revision"].is_null() {
        return Err(err(
            "canonical skill body missing; restore it through the payload owner",
        ));
    }
    let exposed = state["observed"]["status"] == "owned";
    if args["mode"] == "recover" {
        if recoverable(target, &root, name, &state)?.is_none() {
            return Err(err("no exact published exposure effect to recover"));
        }
    } else if exposed == (args["mode"] == "expose") {
        result["status"] = json!("unchanged");
        return Ok(());
    }
    if args["mode"] != "recover" && args["answer"] != "authorize-write" {
        let mut answer = request.clone();
        answer["arguments"]
            .as_object_mut()
            .unwrap()
            .remove("answer");
        result["status"] = json!("authorization-required");
        result["authorization_request"] = answer.clone();
        result["contribution"]["decisions"] = json!([{"id":"skill-exposure-authorization","question":"Authorize this exact passive discovery link change? Canonical skill material and unrelated host skills are preserved.","response_request":{"request_kind":EDIT,"arguments":answer["arguments"]},"choices":[{"id":"authorize-write","label":"Authorize this link change"}],"affects":["task","effect:configuration-source"]}]);
        return Ok(());
    }
    result["status"] = json!("write-ready");
    result["contribution"]["actions"] = json!([{"operation_id":OP,"dependency_revision":digest(&json!([binding,request,state]))?,"arguments":{"target":target,"request":request,"binding":binding,"post_revision":digest(&json!([name,args["mode"],destination(name)]))?},"effects":["configuration-source"],"source_requests":[request]}]);
    Ok(())
}

pub(crate) fn write_scope(action: &Value) -> Result<Vec<String>, CoreError> {
    let name = action["arguments"]["request"]["arguments"]["name"]
        .as_str()
        .ok_or_else(|| err("skill identity missing"))?;
    let mut paths =
        crate::attempt_store::write_paths(&json!({"idempotency_key":action["logical_effect_id"]}))?;
    paths.extend([
        path(name),
        marker(name),
        format!("{}.*.tmp", marker(name)),
        ".agentic-workspace/local/effects/configuration.lock".into(),
    ]);
    Ok(paths)
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
    no_link_directory(&root, ".agentic-workspace/local/effects")?;
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
    let args = &invocation["arguments"]["request"]["arguments"];
    let name = args["name"]
        .as_str()
        .ok_or_else(|| err("skill identity missing"))?;
    let before = state(target, &root, name)?;
    if args["expected_revision"] != digest(&before)? {
        return Err(err("skill exposure changed before publication"));
    }
    let previous = retained(target, &root, name)?;
    let admission = crate::attempt_store::admit(
        json!({"target":target,"decision":decision,"invocation":invocation,"custody":previous.as_ref().filter(|r|r["invocation"]==*invocation).map(|r|&r["custody"])}),
    )?;
    if args["mode"] == "recover" {
        let prior = recoverable(target, &root, name, &before)?
            .ok_or_else(|| err("published exposure changed before recovery"))?;
        let out = outcome(&prior["invocation"]);
        crate::attempt_store::commit(
            json!({"target":target,"custody":prior["custody"],"outcome":out}),
        )?;
        let recovery = json!({"status":"applied","effects":["configuration-source"],"value":{"kind":"agentic-workspace/skill-exposure-result/v1","name":name,"mode":"recover","source":path(name),"material_written":false,"recovered_effect":out,"completion_authority":false}});
        let committed = crate::attempt_store::commit(
            json!({"target":target,"custody":admission["custody"],"outcome":recovery}),
        )?;
        return Ok(json!({"outcome":recovery,"custody":committed["custody"]}));
    }
    let record = json!({"invocation":invocation,"custody":admission["custody"]});
    let temporary = format!("{}.{}.tmp", marker(name), &digest(invocation)?[7..]);
    let bytes = serde_json::to_vec(&record).map_err(err)?;
    if let Some(existing) = crate::native_planning::read(&root, &temporary)? {
        if existing != bytes {
            return Err(err("unowned exposure temporary preserved"));
        }
    } else {
        let mut file = root
            .open_with(&temporary, OpenOptions::new().write(true).create_new(true))
            .map_err(err)?;
        file.write_all(&bytes).map_err(err)?;
        file.sync_all().map_err(err)?;
    }
    revalidate()?;
    if state(target, &root, name)? != before {
        return Err(err("skill exposure changed before ownership publication"));
    }
    if previous.is_some() {
        root.rename(&temporary, &root, marker(name)).map_err(err)?;
    } else {
        root.hard_link(&temporary, &root, marker(name))
            .map_err(err)?;
        root.remove_file(&temporary).map_err(err)?;
    }
    observe("prepared")?;
    if args["mode"] == "expose" {
        no_link_directory(&root, ".agents/skills")?;
        root.create_dir_all(".agents/skills").map_err(err)?;
        // Keep the Windows ambient junction operation's parents open through
        // publication, preventing their deletion/replacement while it runs.
        // Recheck after opening so a substituted reparse point is refused.
        let _host_parent = root.open_dir(".agents").map_err(err)?;
        let _host_skills = root.open_dir(".agents/skills").map_err(err)?;
        no_link_directory(&root, ".agents/skills")?;
        #[cfg(unix)]
        root.symlink(destination(name), path(name)).map_err(err)?;
        #[cfg(windows)]
        junction::create(target.join(format!(".agentic-workspace/skills/{name}")), target.join(path(name))).map_err(|e|err(format!("junction unavailable; preserve canonical material and use the mixed-reader pointer: {e}")))?;
    } else {
        if before["observed"]["status"] != "owned" {
            return Err(err("unowned exposure preserved"));
        }
        #[cfg(unix)]
        root.remove_file(path(name)).map_err(err)?;
        #[cfg(windows)]
        root.remove_dir(path(name)).map_err(err)?;
    }
    observe("published")?;
    let out = outcome(invocation);
    let committed = crate::attempt_store::commit(
        json!({"target":target,"custody":admission["custody"],"outcome":out}),
    )?;
    Ok(
        json!({"outcome":out,"custody":committed["custody"],"post_effect_changed_paths":[path(name)]}),
    )
}

#[cfg(test)]
mod tests {
    use super::*;
    fn resolve(target: &Path, request: Option<Value>) -> Value {
        crate::native_public::start(
            json!({"target":target,"task":"Adopt standard product skills","request":request}),
        )
        .unwrap()
    }
    fn choice(target: &Path, name: &str, mode: &str) -> Value {
        let read = resolve(target, None)["configuration_write"]["skill_exposure_request"].clone();
        let result = resolve(target, Some(read));
        result["configuration_write"]["skill_exposure"]
            .as_array()
            .unwrap()
            .iter()
            .find(|row| row["state"]["name"] == name)
            .unwrap()[format!("{mode}_request")]
        .clone()
    }
    fn apply(target: &Path, name: &str, mode: &str) -> Value {
        let request = choice(target, name, mode);
        let proposed = resolve(target, Some(request));
        let mut answer = proposed["configuration_write"]["authorization_request"].clone();
        answer["arguments"]["answer"] = json!("authorize-write");
        let ready = resolve(target, Some(answer));
        let action = ready["decision_packet"]["primary_action"].clone();
        assert_eq!(action["operation_id"], OP, "{ready}");
        crate::native_public::invoke_checked(
            json!({"target":target,"task":"Adopt standard product skills","invocation":action}),
        )
        .unwrap()
    }
    #[test]
    fn canonical_bundle_lifecycle_preserves_collisions_resources_and_modifications() {
        let target = std::env::temp_dir().join(format!(
            "aw-skill-exposure-{}-{}",
            std::process::id(),
            std::time::SystemTime::now()
                .duration_since(std::time::UNIX_EPOCH)
                .unwrap()
                .as_nanos()
        ));
        std::fs::create_dir_all(&target).unwrap();
        for source in crate::native_payload::paths()
            .into_iter()
            .filter(|p| p.starts_with(".agentic-workspace/skills/"))
        {
            let path = target.join(source);
            std::fs::create_dir_all(path.parent().unwrap()).unwrap();
            std::fs::write(path, crate::native_payload::shipped(source).unwrap()).unwrap();
        }
        let root = Dir::open_ambient_dir(&target, ambient_authority()).unwrap();
        let names = names(&root).unwrap();
        assert!(names.contains(&"workspace-startup".into()));
        assert!(!names.contains(&"workspace-work-shape".into()));
        std::fs::create_dir_all(target.join(".agents/skills/unrelated")).unwrap();
        std::fs::write(
            target.join(".agents/skills/unrelated/SKILL.md"),
            "user skill",
        )
        .unwrap();
        let result = apply(&target, "workspace-intent-discovery", "expose");
        assert_eq!(
            result["value"]["authority_effect"], "discovery-only",
            "{result}"
        );
        let canonical = target.join(".agentic-workspace/skills/workspace-intent-discovery");
        let exposed = target.join(path("workspace-intent-discovery"));
        assert_eq!(
            std::fs::canonicalize(&exposed).unwrap(),
            std::fs::canonicalize(&canonical).unwrap()
        );
        assert_eq!(
            std::fs::read(exposed.join("prepare.py")).unwrap(),
            std::fs::read(canonical.join("prepare.py")).unwrap()
        );
        apply(&target, "workspace-intent-discovery", "remove");
        apply(&target, "workspace-intent-discovery", "expose");
        let stale = choice(&target, "workspace-intent-discovery", "remove");
        std::fs::write(
            canonical.join("SKILL.md"),
            "user modified canonical material",
        )
        .unwrap();
        assert!(
            crate::native_public::start(
                json!({"target":target,"task":"Adopt standard product skills","request":stale})
            )
            .is_err()
        );
        assert_eq!(
            std::fs::read_to_string(exposed.join("SKILL.md")).unwrap(),
            "user modified canonical material"
        );
        apply(&target, "workspace-intent-discovery", "remove");
        assert!(!exposed.exists());
        assert!(canonical.join("prepare.py").exists());
        assert_eq!(
            std::fs::read_to_string(canonical.join("SKILL.md")).unwrap(),
            "user modified canonical material"
        );
        apply(&target, "workspace-intent-discovery", "expose");
        let mut registry: Value =
            serde_json::from_slice(&std::fs::read(target.join(REGISTRY)).unwrap()).unwrap();
        registry["skills"]
            .as_array_mut()
            .unwrap()
            .retain(|row| row["id"] != "workspace-intent-discovery");
        std::fs::write(
            target.join(REGISTRY),
            serde_json::to_vec(&registry).unwrap(),
        )
        .unwrap();
        std::fs::remove_file(canonical.join("SKILL.md")).unwrap();
        apply(&target, "workspace-intent-discovery", "remove");
        // Restore the catalogue only to exercise an unowned collision next.
        std::fs::write(
            target.join(REGISTRY),
            crate::native_payload::shipped(REGISTRY).unwrap(),
        )
        .unwrap();
        std::fs::write(canonical.join("SKILL.md"), "preserved current source").unwrap();
        std::fs::create_dir(&exposed).unwrap();
        std::fs::write(exposed.join("SKILL.md"), "unowned replacement").unwrap();
        let collision = resolve(
            &target,
            Some(choice(&target, "workspace-intent-discovery", "expose")),
        );
        assert_eq!(
            collision["configuration_write"]["status"],
            "collision-preserved"
        );
        assert_eq!(
            std::fs::read_to_string(exposed.join("SKILL.md")).unwrap(),
            "unowned replacement"
        );
        assert_eq!(
            std::fs::read_to_string(target.join(".agents/skills/unrelated/SKILL.md")).unwrap(),
            "user skill"
        );
        drop(root);
        std::fs::remove_dir_all(target).unwrap();
    }

    #[test]
    fn interrupted_effects_reenter_or_recover_without_replaying_publication() {
        for stage in ["prepared", "published"] {
            let target = std::env::temp_dir().join(format!(
                "aw-skill-recovery-{}-{stage}-{}",
                std::process::id(),
                std::time::SystemTime::now()
                    .duration_since(std::time::UNIX_EPOCH)
                    .unwrap()
                    .as_nanos()
            ));
            for source in crate::native_payload::paths()
                .into_iter()
                .filter(|p| p.starts_with(".agentic-workspace/skills/"))
            {
                let path = target.join(source);
                std::fs::create_dir_all(path.parent().unwrap()).unwrap();
                std::fs::write(path, crate::native_payload::shipped(source).unwrap()).unwrap();
            }
            let name = "workspace-startup";
            let mut request = choice(&target, name, "expose");
            request["arguments"]["answer"] = json!("authorize-write");
            let ready = resolve(&target, Some(request));
            let action = ready["decision_packet"]["primary_action"].clone();
            let failed = execute_checked(
                &target,
                &ready["decision_packet"],
                &action,
                &mut || Ok(()),
                &mut |at| {
                    if at == stage {
                        Err(err("interrupted fixture"))
                    } else {
                        Ok(())
                    }
                },
            );
            assert!(
                failed
                    .unwrap_err()
                    .to_string()
                    .contains("interrupted fixture")
            );
            assert!(crate::native_public::invoke_checked(json!({"target":target,"task":"Adopt standard product skills","invocation":action})).is_err());
            if stage == "prepared" {
                assert!(!target.join(path(name)).exists());
                apply(&target, name, "expose");
            } else {
                let discovery =
                    resolve(&target, None)["configuration_write"]["skill_exposure_request"].clone();
                let rows = resolve(&target, Some(discovery));
                let recovery = rows["configuration_write"]["skill_exposure"]
                    .as_array()
                    .unwrap()
                    .iter()
                    .find(|r| r["state"]["name"] == name)
                    .unwrap()["recovery_request"]
                    .clone();
                let ready = resolve(&target, Some(recovery));
                let recovered=crate::native_public::invoke_checked(json!({"target":target,"task":"Adopt standard product skills","invocation":ready["decision_packet"]["primary_action"]})).unwrap();
                assert_eq!(recovered["value"]["material_written"], false);
            }
            apply(&target, name, "remove");
            std::fs::remove_dir_all(target).unwrap();
        }
    }
}
