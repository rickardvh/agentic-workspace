//! Source-owned occasions over current material and native consequences.
//! This is disposable applicability, never policy, evidence or workflow custody.
use crate::{CoreError, decision_source, digest};
use cap_std::{ambient_authority, fs::Dir};
use serde::Deserialize;
use serde_json::{Value, json};
use std::{collections::BTreeSet, path::Path};

const KIND: &str = "procedure/activation-judgment/v1";
#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct Occasion {
    occasions: Vec<String>,
    applicability: String,
    outcome: String,
    #[serde(default)]
    binding_owners: Vec<String>,
    #[serde(default)]
    settled_by: Vec<Fact>,
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn independent_procedure_occasions_compose_and_settle_only_from_current_outcomes() {
        let target = std::env::temp_dir().join(format!("aw-activation-{}", std::process::id()));
        let folder = target.join("tools/skills/lab");
        std::fs::create_dir_all(&folder).unwrap();
        std::fs::write(folder.join("SKILL.md"),"---\nname: lab\ndescription: Establish current laboratory readiness.\n---\nRead procedure.md.").unwrap();
        std::fs::write(target.join("tools/skills/REGISTRY.json"),json!({"skills":[{"id":"lab","path":"lab/SKILL.md","semantic_routes":["lab/readiness"],"procedure_resource":"procedure.md"}]}).to_string()).unwrap();
        let declaration = json!({"kind":"agentic-workspace/procedure/v1","id":"readiness","question":"What readiness is missing?",
            "branches":[{"id":"check","description":"Establish readiness","next":"check.md"}],
            "activation":{"occasions":["observation","need","binding"],"applicability":"A laboratory prerequisite affects current work.","outcome":"The current laboratory owner establishes readiness.","binding_owners":["laboratory"],"settled_by":[{"selector":"/laboratory/status","value":"ready"}]}});
        let body = format!("```agentic-procedure\n{}\n```\n", declaration);
        std::fs::write(folder.join("procedure.md"), &body).unwrap();
        let work = json!({"kind":"current-work","id":"work"});
        let c = contract().unwrap();
        let mut full =
            json!({"current_work":work,"capability_contract":c,"decision_packet":{"blockers":[]}});
        assert!(view(&target, &full, None).unwrap().is_null());
        full["material"] = json!({"items":[
            {"material":{"id":"discovered","kind":"observation","summary":"A new laboratory fact"},"revision":"one"},
            {"material":{"id":"upcoming","kind":"need","summary":"Readiness before proof"},"revision":"two"}]});
        let first = view(&target, &full, None).unwrap();
        assert_eq!(first["candidates"].as_array().unwrap().len(), 2);
        assert_eq!(
            first["candidates"][0]["entry"]["resource"],
            "tools/skills/lab/procedure.md"
        );
        let mut request = first["requests"][0].clone();
        request["arguments"]["judgments"][0]["status"] = json!("no-match");
        request["arguments"]["judgments"][1]["status"] = json!("applicable");
        let next = view(&target, &full, Some(&request)).unwrap();
        assert_eq!(next["candidates"].as_array().unwrap().len(), 1);
        assert_eq!(next["candidates"][0]["outcome_status"], "unsettled");
        std::fs::write(target.join("unrelated.txt"), "unrelated").unwrap();
        assert_eq!(view(&target, &full, Some(&request)).unwrap(), next);
        for status in ["unknown", "defer", "no-retention"] {
            let mut changed = request.clone();
            changed["arguments"]["judgments"][1]["status"] = json!(status);
            assert!(view(&target, &full, Some(&changed)).is_ok());
        }
        let mut changed = full.clone();
        changed["material"]["items"][1]["revision"] = json!("changed");
        assert!(view(&target, &changed, Some(&request)).is_err());
        // An added independent signal does not stale an earlier judgment.
        let mut added = full.clone();
        added["material"]["items"]
            .as_array_mut()
            .unwrap()
            .push(json!({"material":{"id":"third","kind":"need"},"revision":"three"}));
        assert!(view(&target, &added, Some(&request)).is_ok());
        std::fs::write(
            folder.join("procedure.md"),
            format!("{body}\nNew relevant procedure guidance"),
        )
        .unwrap();
        assert!(view(&target, &full, Some(&request)).is_err());
        std::fs::write(folder.join("procedure.md"), body).unwrap();
        full["laboratory"] = json!({"status":"ready"});
        assert!(view(&target, &full, Some(&request)).unwrap().is_null());
        full.as_object_mut().unwrap().remove("laboratory");
        full.as_object_mut().unwrap().remove("material");
        full["decision_packet"]["blockers"] =
            json!([{"owner":"laboratory","code":"current-readiness-required"}]);
        let bound = view(&target, &full, None).unwrap();
        assert_eq!(bound["candidates"][0]["status"], "binding-consequence");
        assert!(
            bound["requests"][0]["arguments"]["judgments"]
                .as_array()
                .unwrap()
                .is_empty()
        );
        // Missing optional skill never alters the native restriction.
        std::fs::remove_file(folder.join("procedure.md")).unwrap();
        assert!(view(&target, &full, None).unwrap().is_null());
        assert_eq!(
            full["decision_packet"]["blockers"][0]["code"],
            "current-readiness-required"
        );
        std::fs::remove_dir_all(target).unwrap();
    }
}
#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct Fact {
    selector: String,
    value: Value,
}
fn err(s: &str) -> CoreError {
    CoreError::new(s)
}
pub(crate) fn validate(value: &Value) -> Result<(), CoreError> {
    let row: Occasion =
        serde_json::from_value(value.clone()).map_err(|_| err("invalid activation declaration"))?;
    if row.occasions.is_empty()
        || row.occasions.len() > 3
        || row
            .occasions
            .iter()
            .any(|s| !["observation", "need", "binding"].contains(&s.as_str()))
        || row.applicability.trim().is_empty()
        || row.applicability.len() > 2048
        || row.outcome.trim().is_empty()
        || row.outcome.len() > 2048
        || row.binding_owners.len() > 16
        || row.settled_by.len() > 8
        || row
            .binding_owners
            .iter()
            .any(|s| s.is_empty() || s.len() > 128)
        || row.settled_by.iter().any(|f| {
            !f.selector.starts_with('/')
                || f.selector.len() > 512
                || f.value.is_null()
                || f.value.is_array()
                || f.value.is_object()
                || ["/material", "/activation", "/semantic_routes", "/procedure"]
                    .iter()
                    .any(|p| f.selector.starts_with(p))
        })
    {
        return Err(err("invalid bounded activation declaration"));
    }
    Ok(())
}
pub(crate) fn contract() -> Result<Value, CoreError> {
    let text = json!({"type":"string","minLength":1,"maxLength":2048});
    let requests = json!([{"kind":KIND,"result_kind":"agentic-workspace/activation/v1","input_schema":{
        "$schema":"https://json-schema.org/draft/2020-12/schema","type":"object","additionalProperties":false,
        "required":["judgments"],"properties":{"judgments":{"type":"array","maxItems":128,"items":{
            "type":"object","additionalProperties":false,"required":["id","revision","status","reason"],
            "properties":{"id":text,"revision":text,"reason":text,"status":{"enum":["applicable","unknown","defer","no-match","no-retention"]}}}}}}}]);
    let mut c = json!({"kind":"agentic-workspace/capability-contract/v1","revision":"pending",
        "owners":[{"owner":"activation","revision":digest(&requests)?,"requests":requests}]});
    c["revision"] = json!(digest(&c)?);
    Ok(c)
}

pub(crate) fn view(
    target: &Path,
    full: &Value,
    request: Option<&Value>,
) -> Result<Value, CoreError> {
    let materials = full["material"]["items"]
        .as_array()
        .cloned()
        .unwrap_or_default();
    let blockers = full["decision_packet"]["blockers"]
        .as_array()
        .cloned()
        .unwrap_or_default();
    if materials.is_empty() && blockers.is_empty() && request.is_none() {
        return Ok(Value::Null);
    }
    let work = &full["current_work"];
    let contract = &full["capability_contract"];
    let owner = contract["owners"]
        .as_array()
        .unwrap()
        .iter()
        .find(|o| o["owner"] == "activation")
        .unwrap();
    let basis = digest(&json!({"work":work,"contract":owner["revision"]}))?;
    if let Some(r) = request {
        crate::prepare_request_value(
            json!({"request":r,"current_work":work,"capability_contract":contract}),
        )?;
        if r["source_revision"] != basis {
            return Err(err("activation work changed"));
        }
    }
    let root = Dir::open_ambient_dir(target, ambient_authority())
        .map_err(|_| err("activation root unavailable"))?;
    let sources = crate::native_routes::registry_sources(target)?;
    let mut candidates = Vec::new();
    let mut seen = BTreeSet::new();
    for source in sources {
        let registry: Value = serde_json::from_slice(&decision_source::read(&root, &source)?)
            .map_err(|_| err("activation registry invalid"))?;
        for skill in registry["skills"].as_array().into_iter().flatten() {
            let (Some(path), Some(resource)) =
                (skill["path"].as_str(), skill["procedure_resource"].as_str())
            else {
                continue;
            };
            decision_source::relative(path)?;
            decision_source::relative(resource)?;
            let base = source.rsplit_once('/').map(|v| v.0).unwrap_or("");
            let skill_path = format!("{base}/{path}");
            let parent = skill_path.rsplit_once('/').unwrap().0;
            let reference = format!("{parent}/{resource}");
            if !seen.insert(reference.clone()) {
                continue;
            }
            let Some(bytes) = crate::native_planning::read(&root, &reference)? else {
                continue;
            };
            if bytes.len() > 65536 {
                return Err(err("activation procedure exceeds bound"));
            }
            let text = std::str::from_utf8(&bytes)
                .map_err(|_| err("activation procedure is not UTF-8"))?;
            let lines: Vec<_> = text.lines().collect();
            let starts: Vec<_> = lines
                .iter()
                .enumerate()
                .filter(|(_, s)| **s == "```agentic-procedure")
                .map(|(i, _)| i + 1)
                .collect();
            if starts.len() != 1 {
                continue;
            }
            let start = starts[0];
            let Some(end) = lines[start..].iter().position(|s| *s == "```") else {
                continue;
            };
            let Ok(question) = serde_json::from_str::<Value>(&lines[start..start + end].join("\n"))
            else {
                continue;
            };
            let Some(value) = question.get("activation") else {
                continue;
            };
            validate(value)?;
            let Some(skill_bytes) = crate::native_planning::read(&root, &skill_path)? else {
                continue;
            };
            let detail = crate::native_procedure::detail(
                &root,
                &json!({"source_ref":source,"procedure":{"reference":skill_path,"revision":decision_source::hash(&skill_bytes),"status":"available"}}),
                &json!(resource),
                None,
            );
            if detail["status"] != "current" {
                return Err(err(
                    "activation entry procedure unavailable; repair its current source",
                ));
            }
            let occasion: Occasion = serde_json::from_value(value.clone()).unwrap();
            let facts: Vec<_> = occasion
                .settled_by
                .iter()
                .map(|f| json!({"selector":f.selector,"observed":full.pointer(&f.selector)}))
                .collect();
            let settled = !occasion.settled_by.is_empty()
                && occasion
                    .settled_by
                    .iter()
                    .all(|f| full.pointer(&f.selector) == Some(&f.value));
            let binding: Vec<_> = blockers
                .iter()
                .filter(|b| occasion.binding_owners.iter().any(|o| b["owner"] == *o))
                .cloned()
                .collect();
            let mut signals: Vec<Value> = materials
                .iter()
                .filter(|m| {
                    occasion
                        .occasions
                        .iter()
                        .any(|k| m["material"]["kind"] == *k)
                })
                .cloned()
                .collect();
            if occasion.occasions.iter().any(|k| k == "binding") && !binding.is_empty() {
                signals.push(json!({"binding":binding}));
            }
            for signal in signals {
                let id = digest(&json!([
                    reference,
                    signal["material"]["id"],
                    signal.get("binding").map(|_| "binding")
                ]))?;
                let revision =
                    digest(&json!([work, reference, detail["revision"], signal, facts]))?;
                let mut status = if settled {
                    "outcome-satisfied"
                } else if signal.get("binding").is_some() {
                    "binding-consequence"
                } else {
                    "applicability-required"
                };
                let judgment = request
                    .and_then(|r| r["arguments"]["judgments"].as_array())
                    .into_iter()
                    .flatten()
                    .find(|j| j["id"] == id);
                if let Some(j) = judgment {
                    if !settled && j["revision"] != revision {
                        return Err(err(
                            "activation basis changed; reconsider dependent judgment",
                        ));
                    }
                    if !settled && signal.get("binding").is_none() {
                        status = j["status"].as_str().unwrap();
                    }
                }
                candidates.push(json!({"id":id,"revision":revision,"status":status,"source":reference,
                    "occasion":signal,"applicability":occasion.applicability,"outcome":occasion.outcome,
                    "entry":{"source_ref":source,"skill_id":skill["id"],"resource":reference,"route":skill["semantic_routes"][0]},
                    "outcome_status":"unsettled","judgment":judgment,
                    "authority":"procedure discovery only; selection or reading does not discharge owner consequences"}));
                if candidates.len() > 128 {
                    return Err(err(
                        "activation frontier exceeds bound; narrow current material",
                    ));
                }
            }
        }
    }
    let mut answered = BTreeSet::new();
    for j in request
        .and_then(|r| r["arguments"]["judgments"].as_array())
        .into_iter()
        .flatten()
    {
        if !answered.insert(j["id"].to_string()) || !candidates.iter().any(|c| c["id"] == j["id"]) {
            return Err(err(
                "activation judgment unavailable or duplicate; reobserve current outcomes",
            ));
        }
    }
    if candidates.is_empty() {
        return Ok(Value::Null);
    }
    let judgments: Vec<_> = candidates.iter().filter(|c|c["status"]!="binding-consequence").map(|c|{
        if c["judgment"].is_object(){c["judgment"].clone()}else{json!({"id":c["id"],"revision":c["revision"],"status":"unknown","reason":"Semantic applicability remains unresolved."})}
    }).collect();
    candidates.retain(|c| {
        !matches!(
            c["status"].as_str(),
            Some("outcome-satisfied" | "no-match" | "no-retention")
        )
    });
    if candidates.is_empty() {
        return Ok(Value::Null);
    }
    let request = json!({"kind":"agentic-workspace/public-request/v1","id":KIND,"owner":"activation","owner_revision":owner["revision"],
        "capability_revision":contract["revision"],"task_identity":work,"source_revision":basis,"request_kind":KIND,"arguments":{"judgments":judgments}});
    Ok(
        json!({"kind":"agentic-workspace/activation/v1","candidates":candidates,"requests":[request],
        "retention":"none","claim_boundary":"Only actual current owner outcomes suppress procedure. Semantic no-match/no-retention is scoped advisory judgment, never an owner waiver."}),
    )
}
