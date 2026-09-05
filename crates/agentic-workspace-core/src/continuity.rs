//! Bounded material decision context, not executable permission or storage.
use crate::{CoreError, digest, require_text};
use serde::{Deserialize, Serialize};
use serde_json::{Value, json};
use std::collections::{BTreeMap, BTreeSet};

#[derive(Debug, Clone, Deserialize, Serialize, PartialEq, Eq, PartialOrd, Ord)]
#[serde(deny_unknown_fields)]
struct Reference {
    owner: String,
    reference: String,
    revision: String,
}
#[derive(Debug, Clone, Deserialize, Serialize, PartialEq, Eq, PartialOrd, Ord)]
#[serde(deny_unknown_fields)]
struct Actor {
    kind: ActorKind,
    id: String,
}
#[derive(Debug, Clone, Deserialize, Serialize, PartialEq, Eq, PartialOrd, Ord)]
#[serde(rename_all = "kebab-case")]
enum ActorKind {
    Agent,
    Human,
}
#[derive(Debug, Clone, Deserialize, Serialize)]
#[serde(deny_unknown_fields)]
struct Authority {
    actor: Actor,
    basis: Vec<Reference>,
}
#[derive(Debug, Clone, Deserialize, Serialize)]
#[serde(deny_unknown_fields)]
struct Supersedes {
    id: String,
    material_revision: String,
    scope: Vec<String>,
}
#[derive(Debug, Clone, Deserialize, Serialize)]
#[serde(deny_unknown_fields)]
struct Record {
    id: String,
    source: Reference,
    decision: String,
    consequence: String,
    rationale_reference: String,
    authors: Vec<Actor>,
    #[serde(default)]
    contributors: Vec<Actor>,
    authority: Authority,
    scope: Vec<String>,
    #[serde(default)]
    dependencies: Vec<Reference>,
    #[serde(default)]
    context: Vec<Reference>,
    #[serde(default)]
    supersedes: Vec<Supersedes>,
    material_revision: Option<String>,
}
#[derive(Debug, Deserialize)]
#[serde(deny_unknown_fields)]
struct Admission {
    rationale_reference: String,
    id: String,
    material_revision: String,
    source: Reference,
}
/// Host supplies only a bounded relevant selection and its supersession closure.
/// Admissions come independently from the source/deciding-authority boundary;
/// serialized assertions supplied by ordinary clients cannot create them.
#[derive(Debug, Deserialize)]
#[serde(deny_unknown_fields)]
pub(crate) struct Context {
    records: Vec<Record>,
    admissions: Vec<Admission>,
    current_dependencies: Vec<Reference>,
    applicable_scope: Vec<String>,
}
fn error(message: impl Into<String>) -> CoreError {
    CoreError::new(message)
}
fn reference(r: &Reference) -> Result<(), CoreError> {
    require_text(&r.owner, "decision reference owner")?;
    require_text(&r.reference, "decision reference")?;
    require_text(&r.revision, "decision reference revision")?;
    Ok(())
}
fn scopes(values: &mut Vec<String>) -> Result<(), CoreError> {
    for value in values.iter() {
        let Some((kind, id)) = value.split_once(':') else {
            return Err(error("decision scope requires an exact typed identity"));
        };
        if !["path", "owner", "contract", "source", "operation"].contains(&kind)
            || id.trim().is_empty()
        {
            return Err(error("unsupported decision scope identity"));
        }
    }
    values.sort();
    values.dedup();
    Ok(())
}
fn normalized(mut record: Record) -> Result<Record, CoreError> {
    for (name, text) in [
        ("identity", &record.id),
        ("decision", &record.decision),
        ("consequence", &record.consequence),
        ("rationale reference", &record.rationale_reference),
    ] {
        require_text(text, name)?;
    }
    reference(&record.source)?;
    if record.authors.is_empty() || record.authority.basis.is_empty() || record.scope.is_empty() {
        return Err(error(
            "decision requires authors, deciding authority basis and scope",
        ));
    }
    for actor in record
        .authors
        .iter()
        .chain(&record.contributors)
        .chain(std::iter::once(&record.authority.actor))
    {
        require_text(&actor.id, "decision actor identity")?;
    }
    record.authors.sort();
    record.authors.dedup();
    record.contributors.sort();
    record.contributors.dedup();
    scopes(&mut record.scope)?;
    for refs in [
        &mut record.authority.basis,
        &mut record.dependencies,
        &mut record.context,
    ] {
        for item in refs.iter() {
            reference(item)?;
        }
        refs.sort();
        refs.dedup();
        if refs
            .windows(2)
            .any(|pair| pair[0].owner == pair[1].owner && pair[0].reference == pair[1].reference)
        {
            return Err(error("conflicting decision dependency revisions"));
        }
    }
    for relation in &mut record.supersedes {
        require_text(&relation.id, "superseded decision identity")?;
        require_text(&relation.material_revision, "superseded material revision")?;
        scopes(&mut relation.scope)?;
        if relation.id == record.id
            || relation.scope.is_empty()
            || relation.scope.iter().any(|s| !record.scope.contains(s))
        {
            return Err(error(
                "supersession must name a different decision within the new decision scope",
            ));
        }
    }
    record.supersedes.sort_by(|a, b| a.id.cmp(&b.id));
    if record
        .supersedes
        .windows(2)
        .any(|pair| pair[0].id == pair[1].id)
    {
        return Err(error("duplicate supersession target"));
    }
    let mut material = serde_json::to_value(&record).map_err(|e| error(e.to_string()))?;
    material.as_object_mut().unwrap().remove("source");
    material
        .as_object_mut()
        .unwrap()
        .remove("rationale_reference");
    material
        .as_object_mut()
        .unwrap()
        .remove("material_revision");
    let revision = digest(&material)?;
    if record
        .material_revision
        .as_ref()
        .is_some_and(|expected| expected != &revision)
    {
        return Err(error(
            "decision material revision differs from its contents",
        ));
    }
    record.material_revision = Some(revision);
    Ok(record)
}
/// Deterministic normalization is not admission of authority or provenance.
pub fn normalize(value: Value) -> Result<Value, CoreError> {
    let record = serde_json::from_value(value).map_err(|e| error(e.to_string()))?;
    serde_json::to_value(normalized(record)?).map_err(|e| error(e.to_string()))
}

pub(crate) fn project(mut context: Context) -> Result<Option<Value>, CoreError> {
    if context.records.len() > 64 {
        return Err(error(
            "decision context must be a bounded selection (at most 64 records)",
        ));
    }
    scopes(&mut context.applicable_scope)?;
    let mut records = BTreeMap::new();
    for record in context.records {
        let record = normalized(record)?;
        if records.insert(record.id.clone(), record).is_some() {
            return Err(error("duplicate material decision identity"));
        }
    }
    let mut admissions = BTreeMap::new();
    for admission in context.admissions {
        if admissions.insert(admission.id.clone(), admission).is_some() {
            return Err(error("duplicate decision admission"));
        }
    }
    let mut current = BTreeMap::new();
    for item in context.current_dependencies {
        reference(&item)?;
        if current
            .insert((item.owner, item.reference), item.revision)
            .is_some()
        {
            return Err(error("duplicate current decision dependency"));
        }
    }
    let mut replaced: BTreeMap<String, BTreeSet<String>> = BTreeMap::new();
    for record in records.values() {
        let admission = admissions
            .get(&record.id)
            .ok_or_else(|| error("decision lacks independent host provenance admission"))?;
        if Some(&admission.material_revision) != record.material_revision.as_ref()
            || admission.source != record.source
            || admission.rationale_reference != record.rationale_reference
        {
            return Err(error(
                "decision admission does not bind exact source and semantic provenance",
            ));
        }
        for relation in &record.supersedes {
            let prior = records
                .get(&relation.id)
                .ok_or_else(|| error("supersession closure is incomplete"))?;
            if Some(&relation.material_revision) != prior.material_revision.as_ref()
                || relation.scope.iter().any(|s| !prior.scope.contains(s))
            {
                return Err(error("supersession target revision or scope differs"));
            }
            replaced
                .entry(prior.id.clone())
                .or_default()
                .extend(relation.scope.iter().cloned());
        }
    }
    // A DAG, not an execution schedule. Missing/cyclic relations fail closed.
    fn visit(
        id: &str,
        records: &BTreeMap<String, Record>,
        active: &mut BTreeSet<String>,
        done: &mut BTreeSet<String>,
    ) -> Result<(), CoreError> {
        if done.contains(id) {
            return Ok(());
        }
        if !active.insert(id.to_owned()) {
            return Err(error("cyclic decision supersession"));
        }
        for prior in &records[id].supersedes {
            visit(&prior.id, records, active, done)?;
        }
        active.remove(id);
        done.insert(id.to_owned());
        Ok(())
    }
    let mut done = BTreeSet::new();
    for id in records.keys() {
        visit(id, &records, &mut BTreeSet::new(), &mut done)?;
    }
    // Each scope-specific ancestry may have only one remaining head. Checking
    // immediate edges alone loses a competing branch when its peer advances.
    let mut lineage_heads = BTreeMap::new();
    for record in records.values() {
        for scope in &record.scope {
            if replaced
                .get(&record.id)
                .is_some_and(|scopes| scopes.contains(scope))
            {
                continue;
            }
            let mut pending = vec![record.id.as_str()];
            let mut visited = BTreeSet::new();
            while let Some(ancestor) = pending.pop() {
                // A resolved diamond can reach the same ancestor more than once.
                if !visited.insert(ancestor) {
                    continue;
                }
                if lineage_heads
                    .insert((ancestor, scope), &record.id)
                    .is_some_and(|head| head != &record.id)
                {
                    return Err(error(
                        "competing decision supersession requires owner resolution",
                    ));
                }
                pending.extend(
                    records[ancestor]
                        .supersedes
                        .iter()
                        .filter(|relation| relation.scope.contains(scope))
                        .map(|relation| relation.id.as_str()),
                );
            }
        }
    }
    let mut consequences = Vec::new();
    let mut states = Vec::new();
    for record in records.values() {
        let selected: Vec<_> = record
            .scope
            .iter()
            .filter(|s| context.applicable_scope.contains(s))
            .cloned()
            .collect();
        if selected.is_empty() {
            continue;
        }
        let superseded = replaced.get(&record.id).cloned().unwrap_or_default();
        let remaining: Vec<_> = selected
            .iter()
            .filter(|s| !superseded.contains(*s))
            .cloned()
            .collect();
        let mut stale = Vec::new();
        for dependency in record
            .authority
            .basis
            .iter()
            .chain(&record.dependencies)
            .chain(&record.context)
        {
            if current.get(&(dependency.owner.clone(), dependency.reference.clone()))
                != Some(&dependency.revision)
            {
                stale.push(dependency.clone());
            }
        }
        stale.sort();
        stale.dedup();
        let status = if remaining.is_empty() {
            "superseded"
        } else if !stale.is_empty() {
            "stale"
        } else {
            "current"
        };
        states.push(json!({"id": record.id, "material_revision": record.material_revision, "source": record.source, "status": status, "current_scope": if status == "current" { remaining.clone() } else { vec![] }, "superseded_scope": selected.iter().filter(|s| superseded.contains(*s)).collect::<Vec<_>>(), "stale_dependencies": stale, "rationale_reference": record.rationale_reference}));
        if status == "current" {
            consequences.push(json!({"id": record.id, "material_revision": record.material_revision, "scope": remaining, "summary": record.consequence, "source": record.source, "authors": record.authors, "authority": record.authority}));
        }
    }
    Ok((!states.is_empty()).then(|| json!({"consequences": consequences, "states": states})))
}
