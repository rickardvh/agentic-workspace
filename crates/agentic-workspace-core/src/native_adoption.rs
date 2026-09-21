//! Configuration-owned repository foothold. No lifecycle CLI or domain setup.
use crate::{CoreError, digest};
use cap_std::{
    ambient_authority,
    fs::{Dir, OpenOptions},
};
use serde_json::{Value, json};
use std::{collections::BTreeMap, io::Write, path::Path, process::Command};

pub(crate) const READ: &str = "configuration/read-repository-adoption/v1";
pub(crate) const EDIT: &str = "configuration/repository-adoption/v1";
pub(crate) const OP: &str = "configuration.repository-adoption";
const RECORD: &str = ".agentic-workspace/local/effects/adoption.prepared.json";
const IDENTITY: &str = ".agentic-workspace/adoption.json";
const LOCK: &str = ".agentic-workspace/local/effects/configuration.lock";
fn err(e: impl ToString) -> CoreError {
    CoreError::new(e.to_string())
}
fn contract() -> Value {
    serde_json::from_str(include_str!(
        "../../../src/agentic_workspace/contracts/workspace_surfaces.json"
    ))
    .expect("host surface contract")
}
fn bytes(root: &Dir, path: &str) -> Result<Option<String>, CoreError> {
    crate::native_planning::read(root, path)?
        .map(|b| String::from_utf8(b).map_err(err))
        .transpose()
}
fn revision(text: &Option<String>) -> Value {
    text.as_ref()
        .map(|s| json!(crate::native_intent::hash(s.as_bytes())))
        .unwrap_or(Value::Null)
}
fn preceding_fence() -> String {
    let c = contract();
    format!(
        "{}\nUse `.agentic-workspace/skills/workspace-startup/SKILL.md` for repository procedure; if native skill discovery is unavailable, read it directly.\n{}",
        c["instruction_fence"]["start"].as_str().unwrap(),
        c["instruction_fence"]["end"].as_str().unwrap()
    )
}
fn fence() -> String {
    preceding_fence().replace(
        "Use `.agentic-workspace/skills/workspace-startup/SKILL.md`",
        "At runtime-capable session entry and after a known dependency change, use the configured AW `start` unless a sufficient current observation is held.\nUse `.agentic-workspace/skills/workspace-startup/SKILL.md`",
    )
}
fn instruction(before: &Option<String>, removing: bool) -> Result<Option<String>, CoreError> {
    let text = before.as_deref().unwrap_or("");
    let c = contract();
    let start = c["instruction_fence"]["start"].as_str().unwrap();
    let end = c["instruction_fence"]["end"].as_str().unwrap();
    let normalized = text.replace("\r\n", "\n");
    let expected = fence();
    if normalized.contains(start) || normalized.contains(end) {
        if normalized.matches(start).count() != 1
            || normalized.matches(end).count() != 1
            || (!normalized.contains(&expected) && !normalized.contains(&preceding_fence()))
        {
            return Err(err(
                "AGENTS.md has a conflicting managed fence; preserve and reconcile its source",
            ));
        }
        if removing {
            // Remove only exact managed bytes. Preserve surrounding source verbatim.
            let a = text.find(start).unwrap();
            let b = text.find(end).unwrap() + end.len();
            let result = format!("{}{}", &text[..a], &text[b..]);
            return Ok(Some(result));
        }
        let a = text.find(start).unwrap();
        let b = text.find(end).unwrap() + end.len();
        return Ok(Some(format!("{}{}{}", &text[..a], expected, &text[b..])));
    }
    if removing {
        return Ok(before.clone());
    }
    Ok(Some(format!(
        "{text}{}{expected}\n",
        if text.is_empty() || text.ends_with('\n') {
            ""
        } else {
            "\n"
        }
    )))
}
fn held(target: &Path, root: &Dir) -> Result<Option<Value>, CoreError> {
    let Some(raw) = bytes(root, RECORD)? else {
        return Ok(None);
    };
    let record: Value = serde_json::from_str(&raw).map_err(err)?;
    let evidence = serde_json::from_value(record["custody"]["attempt"].clone()).map_err(err)?;
    let attempt = crate::attempt_store::read_source(target.to_str().unwrap(), &evidence)?;
    if attempt["invocation"] != record["invocation"]
        || record["invocation"]["operation_id"] != OP
        || record["invocation"]["source_owner"] != "configuration"
        || record["invocation"]["arguments"]["target"] != json!(target)
    {
        return Err(err(
            "repository adoption custody is unavailable; preserve all surfaces",
        ));
    }
    Ok(Some(record))
}
fn committed(target: &Path, root: &Dir, record: &Value) -> Result<bool, CoreError> {
    let prepared = crate::attempt_store::prepare_commit(
        target.to_str().unwrap(),
        record["custody"].clone(),
        outcome(&record["invocation"]),
    )?;
    if bytes(
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

pub(crate) fn ownership_baseline(target: &Path) -> Result<Value, CoreError> {
    let root = Dir::open_ambient_dir(target, ambient_authority()).map_err(err)?;
    let Some(record) = held(target, &root)? else {
        return Ok(Value::Null);
    };
    if !committed(target, &root, &record)? {
        return Ok(Value::Null);
    }
    let state = &record["invocation"]["arguments"]["binding"]["state"];
    if !state["ownership_baseline"].is_null() {
        return Ok(state["ownership_baseline"].clone());
    }
    // The committed legacy postimage is an exact historical migration source,
    // not an input to today's portable payload. Authenticate it against the old
    // installed identity before reconciling a subsequently customized host.
    let installed = &state["installed"][crate::native_ownership::LEDGER];
    if let Some(old) = state["updates"][crate::native_ownership::LEDGER]["after"].as_str()
        && *installed == json!(crate::native_intent::hash(old.as_bytes()))
    {
        return crate::native_ownership::parse(old);
    }
    // Older records without a retained postimage can still migrate unchanged
    // bytes. Unknown customized bytes never acquire inferred package custody.
    let ledger = bytes(&root, crate::native_ownership::LEDGER)?;
    if let Some(text) = ledger.as_deref()
        && *installed == revision(&ledger)
    {
        return crate::native_ownership::parse(text);
    }
    Ok(Value::Null)
}
pub(crate) fn declarations(owner: &mut Value) {
    owner["requests"].as_array_mut().unwrap().extend([
        json!({"kind":READ,"result_kind":"agentic-workspace/repository-adoption/v1","input_schema":{"type":"object","additionalProperties":false,"properties":{}}}),
        json!({"kind":EDIT,"result_kind":"agentic-workspace/repository-adoption/v1","input_schema":{"type":"object","additionalProperties":false,"required":["mode","expected_revision"],"properties":{"mode":{"enum":["adopt","remove","recover","reconcile-payload"]},"expected_revision":{"type":"string"},"disposition":{"enum":["preserve"]},"answer":{"enum":["authorize-write"]}}}})
    ]);
    owner["operations"].as_array_mut().unwrap().push(json!({"id":OP,"semantic_revision":"repository-foothold-v1","input_schema":{"type":"object","additionalProperties":false,"required":["target","request","binding","post_revision"],"properties":{"target":{"type":"string"},"request":{"type":"object"},"binding":{"type":"object"},"post_revision":{"type":"string"}}},"result_kind":"agentic-workspace/repository-adoption-result/v1","effects":["configuration-source"],"reads":["configuration"]}));
    for row in owner["requests"].as_array_mut().unwrap().iter_mut() {
        if row["kind"] == READ || row["kind"] == EDIT {
            row["input_schema"]["$schema"] = json!("https://json-schema.org/draft/2020-12/schema");
        }
    }
    owner["operations"]
        .as_array_mut()
        .unwrap()
        .last_mut()
        .unwrap()["input_schema"]["$schema"] =
        json!("https://json-schema.org/draft/2020-12/schema");
}

fn observe(target: &Path, mode: &str) -> Result<Value, CoreError> {
    let root = Dir::open_ambient_dir(target, ambient_authority()).map_err(err)?;
    let c = contract();
    let identity = bytes(&root, IDENTITY)?;
    let held = held(target, &root)?;
    if mode == "reconcile-payload" {
        // Refresh only artifact-owned identity after independently verifying every
        // installed postimage. This is not custody for host edits or adoption.
        let provenance = ".agentic-workspace/payload-provenance.json";
        let before = bytes(&root, provenance)?;
        let current: Value = before
            .as_deref()
            .and_then(|s| serde_json::from_str(s).ok())
            .unwrap_or(Value::Null);
        let mut blockers = Vec::new();
        if current["kind"] != "agentic-workspace/payload-provenance/v1"
            || current["payload_schema"] != "agentic-workspace/payload/v1"
            || current["release_identity"]["package"] != "agentic-workspace"
            || !current.as_object().is_some_and(|o| {
                o.keys().all(|k| {
                    [
                        "kind",
                        "payload_schema",
                        "managed_revision",
                        "payload_capabilities",
                        "payload_files",
                        "release_identity",
                        "rule",
                    ]
                    .contains(&k.as_str())
                })
            })
            || !current["release_identity"].as_object().is_some_and(|o| {
                o.keys()
                    .all(|k| ["package", "version"].contains(&k.as_str()))
            })
            || !current["release_identity"]["version"].is_string()
            || current
                .get("managed_revision")
                .is_some_and(|v| !v.is_string())
            || !["payload_files", "payload_capabilities"].iter().all(|k| {
                current[k]
                    .as_array()
                    .is_some_and(|a| a.iter().all(Value::is_string))
            })
            || current["rule"]
                != serde_json::from_slice::<Value>(&crate::native_payload::shipped(provenance)?)
                    .map_err(err)?["rule"]
        {
            blockers.push("unrecognized payload identity preserved".to_owned());
        }
        let mut observations = BTreeMap::new();
        for path in crate::native_payload::paths()
            .into_iter()
            .filter(|p| *p != provenance)
        {
            let observed = bytes(&root, path)?;
            observations.insert(path.to_owned(), revision(&observed));
            let expected = match crate::native_payload::desired(target, path) {
                Ok(raw) => String::from_utf8(raw).map_err(err)?,
                Err(error) => {
                    blockers.push(format!("{path}: {error}; preserve content"));
                    continue;
                }
            };
            if observed.as_ref().map(|s| s.replace("\r\n", "\n"))
                != Some(expected.replace("\r\n", "\n"))
            {
                blockers.push(format!(
                    "{path}: current artifact bytes not established; preserve content"
                ));
            }
        }
        let after = String::from_utf8(crate::native_payload::shipped(provenance)?).map_err(err)?;
        let pending = match held.as_ref() {
            Some(record) if !committed(target, &root, record)? => Some(record),
            _ => None,
        };
        if pending.is_some() {
            blockers.push("interrupted adoption effect requires exact recovery".to_owned());
        }
        observations.insert(provenance.to_owned(), revision(&before));
        let mut installed = held
            .as_ref()
            .map(|r| r["invocation"]["arguments"]["binding"]["state"]["installed"].clone())
            .unwrap_or(json!({}));
        installed[provenance] = revision(&Some(after.clone()));
        let baseline = ownership_baseline(target)?;
        let updates = if before.as_deref() == Some(after.as_str()) {
            json!({})
        } else {
            json!({provenance:{"before":revision(&before),"after":after}})
        };
        return Ok(
            json!({"contract_revision":digest(&c)?,"mode":mode,"enclave":null,
            "observations":observations,"updates":updates,"installed":installed,
            "ownership_baseline":baseline,"preserved":[],"blockers":blockers,
            "identity":revision(&identity),"prior_custody":held.as_ref().map(digest).transpose()?,"pending":pending}),
        );
    }
    let mut observations = BTreeMap::new();
    let mut updates = BTreeMap::new();
    let mut preserved = Vec::new();
    let mut blockers = Vec::new();
    let removing = mode == "remove";
    let enclave = if removing {
        Value::Null
    } else {
        crate::native_enclave::inventory(&root, &crate::native_enclave::declarations(&root, &c)?)?
    };
    let ledger_before = bytes(&root, crate::native_ownership::LEDGER)?;
    let preserve_ownership = removing
        && ledger_before
            .as_deref()
            .is_some_and(crate::native_ownership::has_host_meaning);
    if preserve_ownership {
        blockers.push("host ownership declarations and their read profile are preserved; removal has no host-policy custody".into());
    }
    let composed = if removing {
        None
    } else {
        match crate::native_ownership::compose(
            ledger_before.as_deref(),
            &ownership_baseline(target)?,
        ) {
            Ok(ledger) => Some(ledger),
            Err(error) => {
                blockers.push(format!("{}: {error}", crate::native_ownership::LEDGER));
                None
            }
        }
    };
    let profile = composed
        .as_deref()
        .map(crate::native_ownership::profile)
        .transpose()?;
    if !removing
        && let Err(error) = crate::native_ownership::admit_profile(
            bytes(&root, crate::native_ownership::PROFILE)?.as_deref(),
        )
    {
        blockers.push(format!("{}: {error}", crate::native_ownership::PROFILE));
    }
    let mut add = |path: &str, after: Option<String>, package: bool| -> Result<(), CoreError> {
        let before = bytes(&root, path)?;
        observations.insert(path.to_owned(), revision(&before));
        if before != after {
            if package
                && before.is_some()
                && mode == "adopt"
                && ![
                    crate::native_ownership::LEDGER,
                    crate::native_ownership::PROFILE,
                ]
                .contains(&path)
            {
                // Existing package content needs exact prior adoption custody.
                let owned = held.as_ref().and_then(|r| {
                    r["invocation"]["arguments"]["binding"]["state"]["installed"].get(path)
                });
                if owned != Some(&revision(&before)) {
                    blockers.push(format!(
                        "{path}: existing content lacks current package custody"
                    ));
                    return Ok(());
                }
            }
            updates.insert(
                path.to_owned(),
                json!({"before":revision(&before),"after":after}),
            );
        }
        Ok(())
    };
    let mut installed = BTreeMap::new();
    for path in crate::native_payload::paths() {
        if preserve_ownership
            && [
                crate::native_ownership::LEDGER,
                crate::native_ownership::PROFILE,
            ]
            .contains(&path)
        {
            add(path, bytes(&root, path)?, true)?;
            continue;
        }
        let mode = crate::native_payload::materialization(path)?;
        let mut shipped = match mode {
            crate::native_payload::Materialization::PackageVerbatim => {
                String::from_utf8(crate::native_payload::shipped(path)?).map_err(err)?
            }
            crate::native_payload::Materialization::HostComposed => composed
                .clone()
                .or_else(|| ledger_before.clone())
                .unwrap_or_default(),
            crate::native_payload::Materialization::TargetDerived => {
                profile.clone().or(bytes(&root, path)?).unwrap_or_default()
            }
        };
        if !removing
            && mode == crate::native_payload::Materialization::TargetDerived
            && let Some(current) = bytes(&root, path)?
            && crate::native_ownership::profile_matches(&current, &shipped)
        {
            shipped = current;
        }
        installed.insert(
            path.to_owned(),
            json!(crate::native_intent::hash(shipped.as_bytes())),
        );
        if removing {
            let current = bytes(&root, path)?;
            if current.is_some()
                && held.as_ref().and_then(|r| {
                    r["invocation"]["arguments"]["binding"]["state"]["installed"].get(path)
                }) != Some(&revision(&current))
            {
                // Keep discovery available so the owner can report preservation.
                add(path, current, true)?;
                continue;
            }
        }
        add(path, if removing { None } else { Some(shipped) }, true)?;
    }
    let instruction_path = c["instruction_fence"]["path"].as_str().unwrap();
    let instructions = bytes(&root, instruction_path)?;
    add(
        instruction_path,
        instruction(&instructions, removing)?,
        false,
    )?;
    let desired_identity = if removing {
        None
    } else {
        Some(format!("{}\n", serde_json::to_string_pretty(&json!({"kind":"agentic-workspace/adopted-repository/v1","contract_revision":digest(&c)?,"package_files":installed,"instruction_fence":fence()})).map_err(err)?))
    };
    add(IDENTITY, desired_identity, false)?;
    // The adoption attempt store is machine-local even in a plain Git host.
    // Establish its ignore rule only when absent; it survives de-adoption with
    // the independent local records and never rewrites repository ignore policy.
    let local_ignore = c["local_ignore"]["path"].as_str().unwrap();
    if mode == "adopt" && bytes(&root, local_ignore)?.is_none() {
        add(local_ignore, Some("*\n".into()), false)?;
    }
    if removing {
        for path in crate::native_payload::paths() {
            let current = bytes(&root, path)?;
            if current.is_some()
                && held.as_ref().and_then(|r| {
                    r["invocation"]["arguments"]["binding"]["state"]["installed"].get(path)
                }) != Some(&revision(&current))
            {
                blockers.push(format!(
                    "{path}: edited or unowned package surface preserved"
                ));
            }
        }
        if held.is_none()
            && instructions
                .as_deref()
                .unwrap_or("")
                .contains(c["instruction_fence"]["start"].as_str().unwrap())
        {
            blockers.push("AGENTS.md fence has no authenticated adoption custody; preserve".into());
        }
    }
    if !removing && identity.is_some() && held.is_none() {
        let parsed: Value =
            serde_json::from_str(identity.as_deref().unwrap()).unwrap_or(Value::Null);
        if parsed["kind"] != "agentic-workspace/adopted-repository/v1" {
            blockers.push("adoption identity is unknown; preserve and reconcile its source".into());
        }
    }
    if removing && identity.is_some() && held.is_none() {
        blockers.push("adoption identity has no authenticated local producer custody; preserve and explicitly adopt current matching surfaces first".into());
    }
    // Retired package files have an exact source-contract digest. Removal is
    // separately visible in the authorized convergence proposal, never recursive.
    for row in c["retired_package_surfaces"]
        .as_array()
        .unwrap()
        .iter()
        .filter(|_| removing)
    {
        let path = row["path"].as_str().unwrap();
        if let Some(current) = bytes(&root, path)? {
            observations.insert(
                path.to_owned(),
                json!(crate::native_intent::hash(current.as_bytes())),
            );
            let normalized = current.replace("\r\n", "\n");
            if crate::native_intent::hash(normalized.as_bytes())
                == format!("sha256:{}", row["sha256"].as_str().unwrap())
            {
                updates.insert(
                    path.to_owned(),
                    json!({"before":crate::native_intent::hash(current.as_bytes()),"after":null}),
                );
            } else {
                preserved.push(json!({"path":path,"reason":"edited or unknown retired surface"}));
            }
        }
    }
    if !removing {
        for (path, observed) in enclave["removals"].as_object().unwrap() {
            updates.insert(
                path.clone(),
                json!({"before":observed,"after":null,"enclave_residue":true}),
            );
        }
    }
    for (class, paths) in c["preserved_classes"].as_object().unwrap() {
        for path in paths.as_array().unwrap() {
            let path = path.as_str().unwrap();
            if removing && (class == "local-only" || target.join(path).exists()) {
                preserved.push(json!({"path":path,"class":class,"disposition":"preserve"}));
            }
        }
    }
    if !removing {
        for (path, declaration) in enclave["entries"].as_object().unwrap() {
            if ["mutable-state", "customization", "local-only"]
                .contains(&declaration["class"].as_str().unwrap_or(""))
            {
                preserved.push(json!({"path":path,"owner":declaration["owner"],"class":declaration["class"],"lifetime":declaration["lifetime"],"disposition":"preserve"}));
            }
        }
    }
    let pending = match held.as_ref() {
        Some(record) if !committed(target, &root, record)? => Some(record),
        _ => None,
    };
    if pending.is_some() && mode != "recover" {
        blockers.push("interrupted adoption effect requires exact recover request".into());
    }
    let state = json!({"contract_revision":digest(&c)?,"mode":mode,"enclave":enclave,"observations":observations,"updates":updates,"installed":installed,"ownership_baseline":crate::native_ownership::baseline(),"preserved":preserved,"blockers":blockers,
        "identity":revision(&identity),"prior_custody":held.as_ref().map(digest).transpose()?,"pending":pending});
    Ok(state)
}

pub(crate) fn view(
    target: &Path,
    request: &Value,
    binding: &Value,
    template: &dyn Fn(&str, Value) -> Value,
    result: &mut Value,
) -> Result<(), CoreError> {
    let args = &request["arguments"];
    let mode = args["mode"].as_str().unwrap_or("adopt");
    if request["request_kind"] == EDIT
        && matches!(mode, "adopt" | "reconcile-payload")
        && let Err(error) = crate::native_configuration_assessment::admit_maintenance(target)
    {
        result["status"] = json!("preserved-blocked");
        result["migration_gap"] = json!(error.to_string());
        return Ok(());
    }
    if request["request_kind"] == EDIT && mode == "remove" {
        let mut exposure = json!({});
        crate::native_skill_exposure::view(
            target,
            &template(crate::native_skill_exposure::READ, json!({})),
            binding,
            template,
            &mut exposure,
        )?;
        let owned: Vec<_> = exposure["skill_exposure"]
            .as_array()
            .into_iter()
            .flatten()
            .filter(|row| row["state"]["observed"]["status"] == "owned")
            .cloned()
            .collect();
        if !owned.is_empty() {
            result["status"] = json!("remove-owned-skill-exposures-first");
            result["skill_exposure"] = json!(owned);
            return Ok(());
        }
    }
    let git = Command::new("git")
        .args([
            "-C",
            target.to_str().unwrap(),
            "rev-parse",
            "--show-toplevel",
        ])
        .output()
        .map_err(err)?;
    if !git.status.success() {
        result["status"] = json!("git-repository-required");
        return Ok(());
    }
    let git_root = String::from_utf8(git.stdout).map_err(err)?;
    if std::fs::canonicalize(git_root.trim()).map_err(err)?
        != std::fs::canonicalize(target).map_err(err)?
    {
        result["status"] = json!("git-working-tree-root-required");
        return Ok(());
    }
    let state = observe(target, mode)?;
    let state_revision = digest(&state)?;
    result["repository_adoption"] = state.clone();
    if request["request_kind"] == READ {
        result["status"] = json!(if state["identity"].is_null() {
            "unadopted"
        } else if state["enclave"]["status"] == "dirty" {
            "adopted-dirty"
        } else {
            "adopted-source-present"
        });
        result["adoption_requests"] = json!([
            template(
                EDIT,
                json!({"mode":"adopt","expected_revision":state_revision})
            ),
            template(
                EDIT,
                json!({"mode":"remove","expected_revision":digest(&observe(target,"remove")?)?})
            )
        ]);
        result["adoption_requests"].as_array_mut().unwrap().push(template(
            EDIT, json!({"mode":"reconcile-payload","expected_revision":digest(&observe(target,"reconcile-payload")?)?})
        ));
        if !state["pending"].is_null() {
            result["recovery_requests"] = json!([template(
                EDIT,
                json!({"mode":"recover","expected_revision":digest(&observe(target,"recover")?)?})
            )]);
        }
        return Ok(());
    }
    if args["expected_revision"] != state_revision {
        return Err(err(
            "adoption source changed; reobserve exact current surfaces",
        ));
    }
    if mode != "recover" && !state["blockers"].as_array().unwrap().is_empty() {
        result["status"] = json!("preserved-blocked");
        return Ok(());
    }
    let root = Dir::open_ambient_dir(target, ambient_authority()).map_err(err)?;
    let mut effective = state.clone();
    if mode == "recover" {
        let record = state["pending"]
            .as_object()
            .ok_or_else(|| err("no interrupted adoption effect"))?;
        let record = Value::Object(record.clone());
        let previous_policy = &record["invocation"]["arguments"]["binding"]["policy"];
        // Payload conformance is the repaired observation, not governing policy.
        // Recovery still binds all configuration sources, artifact and owner code.
        let same_policy = if record["invocation"]["arguments"]["request"]["arguments"]["mode"]
            == "reconcile-payload"
        {
            !previous_policy["payload_recovery_policy"].is_null()
                && previous_policy["payload_recovery_policy"] == binding["payload_recovery_policy"]
        } else {
            *previous_policy == *binding
        };
        if !same_policy {
            return Err(err(
                "adoption recovery governing configuration changed; preserve",
            ));
        }
        effective["updates"] =
            record["invocation"]["arguments"]["binding"]["state"]["updates"].clone();
        for (path, update) in effective["updates"].as_object().unwrap() {
            if update["enclave_residue"] == true {
                let current = crate::native_enclave::identity(&root, path)?;
                if !current.is_null() && current != update["before"] {
                    return Err(err(format!("{path}: recovery residue changed")));
                }
                continue;
            }
            let current = bytes(&root, path)?;
            if revision(&current) != update["before"]
                && current != update["after"].as_str().map(str::to_owned)
            {
                return Err(err(format!(
                    "{path}: recovery source differs from both exact preimage and postimage"
                )));
            }
        }
    } else if state["updates"].as_object().unwrap().is_empty()
        && (!state["prior_custody"].is_null() || mode == "remove")
    {
        result["status"] = json!("already-current");
        return Ok(());
    }
    if args["answer"] != "authorize-write"
        || (mode == "remove" && args["disposition"] != "preserve")
    {
        let mut answer = args.clone();
        if mode == "remove" {
            answer["disposition"] = json!("preserve");
        }
        result["status"] = json!("authorization-required");
        result["contribution"]["decisions"] = json!([{"id":"repository-adoption-authorization","question":"Authorize these exact package integration changes and preserve the listed repository/domain/local state?","material":effective,"response_request":{"request_kind":EDIT,"arguments":answer},"choices":[{"id":"authorize-write","label":"Authorize this bounded repository integration change"}],"affects":["effect:configuration-source"]}]);
        return Ok(());
    }
    let bound = json!({"policy":binding,"state":effective});
    result["status"] = json!("write-ready");
    result["contribution"]["actions"] = json!([{"operation_id":OP,"dependency_revision":digest(&json!([bound,request]))?,"arguments":{"target":target,"request":request,"binding":bound,"post_revision":digest(&state["updates"])?},"effects":["configuration-source"],"source_requests":[request]}]);
    Ok(())
}
fn outcome(i: &Value) -> Value {
    json!({"status":"applied","effects":["configuration-source"],"value":{"kind":"agentic-workspace/repository-adoption-result/v1","mode":i["arguments"]["request"]["arguments"]["mode"],"completion_authority":false}})
}
pub(crate) fn write_scope(i: &Value) -> Result<Vec<String>, CoreError> {
    let mut paths =
        crate::attempt_store::write_paths(&json!({"idempotency_key":i["logical_effect_id"]}))?;
    paths.extend([RECORD.into(), format!("{RECORD}.*.tmp"), LOCK.into()]);
    for path in i["arguments"]["binding"]["state"]["updates"]
        .as_object()
        .ok_or_else(|| err("adoption updates missing"))?
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
    bytes(&root, LOCK)?;
    root.create_dir_all(".agentic-workspace/local/effects")
        .map_err(err)?;
    let lock = root
        .open_with(LOCK, OpenOptions::new().read(true).write(true).create(true))
        .map_err(err)?
        .into_std();
    if lock.metadata().map_err(err)?.len() != 0 {
        return Err(err("unknown configuration lock preserved"));
    }
    lock.try_lock().map_err(err)?;
    revalidate()?;
    let recovery = i["arguments"]["request"]["arguments"]["mode"] == "recover";
    let original = if recovery {
        i["arguments"]["binding"]["state"]["pending"]["invocation"].clone()
    } else {
        i.clone()
    };
    let admission =
        crate::attempt_store::admit(json!({"target":target,"decision":decision,"invocation":i}))?;
    if !recovery {
        let temporary = format!("{RECORD}.{}.tmp", &digest(i)?[7..]);
        let mut file = root
            .open_with(&temporary, OpenOptions::new().write(true).create_new(true))
            .map_err(err)?;
        file.write_all(
            serde_json::to_string(&json!({"invocation":i,"custody":admission["custody"]}))
                .map_err(err)?
                .as_bytes(),
        )
        .map_err(err)?;
        file.sync_all().map_err(err)?;
        drop(file);
        root.rename(&temporary, &root, RECORD).map_err(err)?;
    }
    let updates = i["arguments"]["binding"]["state"]["updates"]
        .as_object()
        .unwrap();
    // Identity is published last and removed first; partial material is never
    // reported adopted merely because an earlier file write succeeded.
    let mut paths: Vec<_> = updates.keys().collect();
    paths.sort_by_key(|path| {
        if path.as_str() == IDENTITY {
            if original["arguments"]["request"]["arguments"]["mode"] == "adopt" {
                (2, 0)
            } else {
                (0, 0)
            }
        } else {
            (1, usize::MAX - path.matches('/').count())
        }
    });
    for path in paths {
        let update = &updates[path];
        if update["enclave_residue"] == true {
            crate::native_enclave::remove(&root, path, &update["before"], recovery)?;
            continue;
        }
        let current = bytes(&root, path)?;
        let after = update["after"].as_str().map(str::to_owned);
        if recovery && current == after {
            continue;
        }
        if revision(&current) != update["before"] {
            return Err(err(format!(
                "{path}: adoption source changed at publication barrier"
            )));
        }
        if let Some(text) = after {
            root.create_dir_all(Path::new(path).parent().unwrap_or(Path::new(".")))
                .map_err(err)?;
            let temporary = format!("{path}.{}.tmp", &digest(&original)?[7..]);
            if let Some(existing) = bytes(&root, &temporary)? {
                if existing != text || !recovery {
                    return Err(err(format!(
                        "{temporary}: unknown or incomplete temporary preserved"
                    )));
                }
            } else {
                let mut file = root
                    .open_with(&temporary, OpenOptions::new().write(true).create_new(true))
                    .map_err(err)?;
                file.write_all(text.as_bytes()).map_err(err)?;
                file.sync_all().map_err(err)?;
            }
            if revision(&bytes(&root, path)?) != update["before"] {
                return Err(err("adoption source changed before replacement"));
            }
            if current.is_none() {
                root.hard_link(&temporary, &root, path).map_err(err)?;
                root.remove_file(&temporary).map_err(err)?;
            } else {
                root.rename(&temporary, &root, path).map_err(err)?;
            }
        } else if current.is_some() {
            root.remove_file(path).map_err(err)?;
        }
    }
    if recovery {
        let record =
            held(target, &root)?.ok_or_else(|| err("adoption recovery custody missing"))?;
        crate::attempt_store::commit(
            json!({"target":target,"custody":record["custody"],"outcome":outcome(&record["invocation"])}),
        )?;
    }
    let out = outcome(i);
    let committed = crate::attempt_store::commit(
        json!({"target":target,"custody":admission["custody"],"outcome":out}),
    )?;
    Ok(
        json!({"outcome":out,"custody":committed["custody"],"post_effect_changed_paths":updates.keys().collect::<Vec<_>>()}),
    )
}
