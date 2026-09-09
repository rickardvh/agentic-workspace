//! Admission and composition of independently linked native owner semantics.
use crate::{CoreError, digest, independent_owner as sdk};
use cap_std::{ambient_authority, fs::Dir};
use serde_json::{Value, json};
use std::{collections::BTreeSet, path::Path};

fn err(value: impl ToString) -> CoreError {
    CoreError::new(value.to_string())
}
fn strings(value: &Value) -> BTreeSet<String> {
    value
        .as_array()
        .into_iter()
        .flatten()
        .filter_map(Value::as_str)
        .map(str::to_owned)
        .collect()
}
fn identifier(value: &str) -> bool {
    !value.is_empty()
        && value.len() <= 64
        && value.as_bytes()[0].is_ascii_lowercase()
        && value
            .bytes()
            .all(|b| b.is_ascii_lowercase() || b.is_ascii_digit() || b == b'-')
}
pub(crate) fn linked(owner: &str) -> bool {
    inventory::iter::<sdk::Registration>
        .into_iter()
        .any(|entry| entry.owner == owner)
}

pub(crate) struct Selected {
    registration: &'static sdk::Registration,
    description: sdk::Description,
    admission: Value,
    sources: Value,
    revision: String,
    source_revision: String,
    configuration_gap: Option<String>,
}
pub(crate) struct Runtime {
    selected: Vec<Selected>,
    pub(crate) contract: Value,
}

impl Runtime {
    pub(crate) fn discover(
        target: &Path,
        work: &Value,
        changed: &[String],
        requests: &[Value],
        configuration: &Value,
    ) -> Result<Self, CoreError> {
        let admissions = &configuration["independent_admissions"];
        let requested: BTreeSet<_> = requests
            .iter()
            .filter_map(|request| request["owner"].as_str())
            .collect();
        let mut names = BTreeSet::new();
        for (owner, admission) in admissions.as_object().into_iter().flatten() {
            if requested.contains(owner.as_str())
                || strings(&admission["scope"]).iter().any(|scope| {
                    changed
                        .iter()
                        .any(|path| path == scope || path.starts_with(&format!("{scope}/")))
                })
            {
                names.insert(owner.clone());
            }
        }
        // Explicit requests cannot silently disappear with their installation or admission.
        for owner in &requested {
            if linked(owner) && admissions.get(*owner).is_none() {
                return Err(err(format!(
                    "Independent owner {owner} is linked but not admitted by modules.independent; no authority acquired"
                )));
            }
        }
        let root = Dir::open_ambient_dir(target, ambient_authority()).map_err(err)?;
        let mut selected = Vec::new();
        let mut owners = Vec::new();
        let mut claims = Vec::new();
        let mut restrictions = Vec::new();
        for name in names {
            if !identifier(&name) {
                return Err(err("Invalid independent owner identity"));
            }
            let matches: Vec<_> = inventory::iter::<sdk::Registration>
                .into_iter()
                .filter(|entry| entry.owner == name)
                .collect();
            let [registration] = matches.as_slice() else {
                return Err(err(format!(
                    "Relevant independent owner {name} is unavailable or has conflicting installations; preserve its state and restore the exact admitted implementation"
                )));
            };
            let admission = admissions[&name].clone();
            if registration.api_version != 1 || admission["revision"] != registration.revision {
                return Err(err(format!(
                    "Independent owner {name} is incompatible with its current admission; restore the admitted revision or reconcile admission through Configuration"
                )));
            }
            let description = (registration.describe)();
            if sdk::contract_revision(&description)? != admission["contract_revision"] {
                return Err(err(format!(
                    "Independent owner {name} contract differs from its exact admission"
                )));
            }
            let configuration_gap = crate::schema_validator(
                &description.configuration_schema,
                "independent owner configuration",
            )?
            .validate(&admission["settings"])
            .err()
            .map(|e| {
                format!(
                    "Independent owner {name} requires current Configuration material at {}",
                    e.instance_path()
                )
            });
            let mut capability = description.capability.clone();
            if capability["owner"] != name
                || strings(&capability["domains"]) != BTreeSet::from([name.clone()])
            {
                return Err(err("Independent owner cannot acquire a foreign domain"));
            }
            let granted = strings(&admission["effects"]);
            for effect in capability["effects"].as_array().into_iter().flatten() {
                if effect["domain"] != name
                    || !effect["id"].as_str().is_some_and(|id| granted.contains(id))
                {
                    return Err(err(
                        "Independent owner effect is not separately admitted in its owned domain",
                    ));
                }
            }
            for operation in capability["operations"].as_array().into_iter().flatten() {
                if operation["input_schema"] != sdk::operation_schema() {
                    return Err(err(
                        "Independent operation must use the exact prepared-operation carrier",
                    ));
                }
            }
            let allowed_reads = strings(&admission["reads"]);
            if description.sources.len() > 32 {
                return Err(err(
                    "Independent source declaration exceeds bounded discovery",
                ));
            }
            let mut sources = json!({});
            let mut total = 0;
            for reference in &description.sources {
                if !allowed_reads.contains(reference) {
                    return Err(err("Independent owner read is not separately admitted"));
                }
                crate::decision_source::relative(reference)?;
                if reference.split('/').any(|part| part.ends_with(['.', ' '])) {
                    return Err(err("Independent source must not use platform path aliases"));
                }
                let bytes = crate::native_planning::read(&root, reference)?;
                total += bytes.as_ref().map_or(0, Vec::len);
                if total > 1_048_576 {
                    return Err(err("Independent source set exceeds bounded read"));
                }
                sources[reference] = match bytes {
                    Some(bytes) => {
                        json!({"status":"present","revision":digest(&json!(bytes))?,"text":std::str::from_utf8(&bytes).map_err(err)?})
                    }
                    None => json!({"status":"absent"}),
                };
            }
            let revision = digest(
                &json!({"registration":registration.revision,"contract":admission["contract_revision"],"effects":admission["effects"],"claims":admission["claims"],"restrictions":admission["restrictions"]}),
            )?;
            capability["revision"] = json!(revision);
            let source_revision =
                digest(&json!({"work":work,"admission":admission,"sources":sources}))?;
            for claim in strings(&admission["claims"]) {
                claims.push(json!({"owner":name,"claim":claim}));
            }
            if !strings(&admission["restrictions"]).is_empty() {
                restrictions.push(json!({"owner":name,"affects":admission["restrictions"]}));
            }
            owners.push(capability);
            selected.push(Selected {
                registration,
                description,
                admission,
                sources,
                revision,
                source_revision,
                configuration_gap,
            });
        }
        let mut contract = json!({"kind":"agentic-workspace/capability-contract/v1","revision":"pending","owners":owners,"claim_authorities":claims,"restriction_authorities":restrictions});
        contract["revision"] = json!(digest(&contract)?);
        // Existing compiler owns effect/domain/claim/restriction validation.
        if !selected.is_empty() {
            crate::compile_value(json!({"contributions":[],"capability_contract":contract}))?;
        }
        Ok(Self { selected, contract })
    }

    pub(crate) fn resolve(
        &self,
        target: &Path,
        work: &Value,
        contract: &Value,
        requests: &[Value],
    ) -> Result<(Vec<Value>, Value), CoreError> {
        let mut contributions = Vec::new();
        let mut views = json!({});
        for selected in &self.selected {
            let owner = selected.registration.owner;
            if let Some(gap) = &selected.configuration_gap {
                if requests.iter().any(|request| request["owner"] == owner) {
                    return Err(err(gap));
                }
                views[owner] = json!({"status":"configuration-required","reason":gap,"configuration_schema":selected.description.configuration_schema,"requests":[]});
                continue;
            }
            let matching: Vec<_> = requests.iter().filter(|r| r["owner"] == owner).collect();
            if matching.len() > 1 {
                return Err(err(
                    "Supply one current independent owner intention at a time",
                ));
            }
            let request = matching.first().copied();
            if let Some(request) = request {
                crate::prepare_request_value(
                    json!({"request":request,"current_work":work,"capability_contract":contract}),
                )?;
                if request["source_revision"] != selected.source_revision
                    || request["id"]
                        != format!("{owner}:{}", request["request_kind"].as_str().unwrap_or(""))
                {
                    return Err(err(
                        "Independent request is not the exact current owner-issued request",
                    ));
                }
            }
            let resolution = (selected.registration.resolve)(&sdk::Context {
                current_work: work.clone(),
                settings: selected.admission["settings"].clone(),
                sources: selected.sources.clone(),
                request: request.cloned(),
            })
            .map_err(err)?;
            let mut returned_requests = Vec::new();
            for template in resolution.requests {
                if !selected.description.capability["requests"]
                    .as_array()
                    .into_iter()
                    .flatten()
                    .any(|r| r["kind"] == template.kind)
                {
                    return Err(err("Independent owner returned an undeclared request"));
                }
                returned_requests.push(json!({"kind":"agentic-workspace/public-request/v1","id":format!("{owner}:{}",template.kind),"owner":owner,"owner_revision":selected.revision,"source_revision":selected.source_revision,"request_kind":template.kind,"capability_revision":contract["revision"],"task_identity":work,"arguments":template.arguments}));
            }
            let mut actions = Vec::new();
            if let Some(operation) = resolution.operation {
                let request = request.ok_or_else(|| {
                    err("Independent operation requires an explicit current typed intention")
                })?;
                let declaration = selected.description.capability["operations"]
                    .as_array()
                    .into_iter()
                    .flatten()
                    .find(|o| o["id"] == operation.operation_id)
                    .ok_or_else(|| err("Independent operation is undeclared"))?;
                let effects = strings(&declaration["effects"]);
                if operation.publication.is_some() != !effects.is_empty() {
                    return Err(err(
                        "Independent publication must exactly correspond to its admitted owned effects",
                    ));
                }
                let publication = match operation.publication {
                    Some(publication) => {
                        if !identifier(&publication.name) {
                            return Err(err(
                                "Independent publication name must be a confined identifier",
                            ));
                        }
                        json!({"path":format!(".agentic-workspace/modules/{owner}/{}.json",publication.name),"value":publication.value})
                    }
                    None => Value::Null,
                };
                let arguments = json!({"target":target,"request":request,"source_revision":selected.source_revision,"value":operation.value,"publication":publication});
                if publication["path"].as_str().is_some_and(|path| {
                    selected.description.sources.iter().any(|source| {
                        source == path || (cfg!(windows) && source.eq_ignore_ascii_case(path))
                    })
                }) {
                    return Err(err(
                        "Immutable independent publication cannot replace a declared input source; an owner-specific update contract is required",
                    ));
                }
                if serde_json::to_vec(&arguments).map_err(err)?.len() > 131_072 {
                    return Err(err(
                        "Independent prepared result exceeds bounded publication",
                    ));
                }
                actions.push(json!({"operation_id":operation.operation_id,"dependency_revision":digest(&arguments)?,"arguments":arguments,"effects":effects,"source_requests":requests}));
            }
            contributions.push(json!({"owner":owner,"revision":selected.source_revision,"facts":resolution.facts,"blockers":resolution.blockers,"actions":actions}));
            views[owner] = json!({"status":"current","revision":selected.revision,"source_revision":selected.source_revision,"requests":returned_requests,"sources":selected.sources,"authority_boundary":"Exact admitted native owner contribution; returned foreign material is evidence requiring responsible-owner admission"});
        }
        Ok((contributions, views))
    }
}
