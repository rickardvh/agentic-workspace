//! Disposable semantic answers. These never contribute policy, proof or effects.
use crate::{CoreError, digest};
use cap_std::{ambient_authority, fs::Dir};
use serde_json::{Value, json};
use std::path::Path;

pub(crate) fn contract() -> Result<Value, CoreError> {
    let schema = crate::source_schema();
    let mut shape = schema["$defs"]["procedure_answer_input"].clone();
    shape["$schema"] = schema["$schema"].clone();
    let requests = json!([{"kind":"procedure/select/v1","input_schema":shape,"result_kind":"agentic-workspace/procedure-answer/v1"},
        {"kind":"procedure/answer/v1","input_schema":shape,"result_kind":"agentic-workspace/procedure-answer/v1"}]);
    let mut value = json!({"kind":"agentic-workspace/capability-contract/v1","revision":"pending",
        "owners":[{"owner":"procedure","revision":digest(&requests)?,"requests":requests}]});
    value["revision"] = json!(digest(&value)?);
    Ok(value)
}

fn template(work: &Value, contract: &Value, kind: &str, basis: &str, selection: &Value) -> Value {
    let owner = contract["owners"]
        .as_array()
        .unwrap()
        .iter()
        .find(|o| o["owner"] == "procedure")
        .unwrap();
    json!({"kind":"agentic-workspace/public-request/v1","id":kind,"owner":"procedure",
        "owner_revision":owner["revision"],"capability_revision":contract["revision"],"task_identity":work,
        "request_kind":kind,"source_revision":basis,"arguments":{"selection":selection}})
}

fn forbidden(value: &Value) -> bool {
    if matches!(
        value["kind"].as_str(),
        Some(
            "agentic-workspace/public-request/v1"
                | "agentic-workspace/operation-invocation/v1"
                | "agentic-workspace/operating-carriage/v1"
        )
    ) {
        return true;
    }
    match value {
        Value::Object(values) => values.values().any(forbidden),
        Value::Array(values) => values.iter().any(forbidden),
        _ => false,
    }
}

pub(crate) fn view(
    target: &Path,
    work: &Value,
    routes: &Value,
    request: Option<&Value>,
    contract: &Value,
) -> Result<Value, CoreError> {
    let mut result = json!({"kind":"agentic-workspace/procedure-answer/v1","status":"unselected","requests":[],
        "authority_effect":"none","claim_boundary":"Supplied semantic judgment is advisory procedure input, not semantic truth, evidence, policy, permission or completion.",
        "reentry":"Carry the exact answer request for reuse. Lost or stale carriage requires reconsideration; no answer is reconstructed from branch labels."});
    let mut selections = Vec::new();
    let leaf = &routes["discovery"]["detail"];
    for source in leaf["sources"].as_array().into_iter().flatten() {
        let resource = &source["procedure"]["resource"];
        if resource["status"] == "current" {
            let selection = json!({"route":leaf["id"],"source_ref":source["source_ref"],"skill_id":source["skill_id"],"instance":"default"});
            selections.push(template(
                work,
                contract,
                "procedure/select/v1",
                resource["revision"].as_str().unwrap(),
                &selection,
            ));
        }
    }
    result["requests"] = json!(selections);
    let Some(request) = request else {
        return Ok(result);
    };
    crate::prepare_request_value(
        json!({"request":request,"current_work":request["task_identity"],"capability_contract":contract}),
    )?;
    let selection = &request["arguments"]["selection"];
    let discovered =
        crate::native_routes::discovery(json!({"target":target,"exact":selection["route"]}))?;
    let candidates: Vec<_> = discovered["routes"][0]["sources"]
        .as_array()
        .into_iter()
        .flatten()
        .filter(|source| {
            source["source_ref"] == selection["source_ref"]
                && source["skill_id"] == selection["skill_id"]
        })
        .collect();
    if candidates.len() != 1 || candidates[0]["procedure"]["resource"]["status"] != "current" {
        result["status"] = json!("unavailable");
        return Ok(result);
    }
    let resource = &candidates[0]["procedure"]["resource"];
    let basis = digest(&json!({"selection":selection,"resource":resource["revision"]}))?;
    let select = request["request_kind"] == "procedure/select/v1";
    result["question"] = resource.clone();
    result["selection"] = selection.clone();
    result["basis"] = json!(basis);
    result["requests"] = json!([template(
        work,
        contract,
        "procedure/answer/v1",
        &basis,
        selection
    )]);
    if request["task_identity"] != *work
        || request["source_revision"]
            != if select {
                resource["revision"].clone()
            } else {
                json!(basis)
            }
    {
        result["status"] = json!("stale");
        return Ok(result);
    }
    let answer = &request["arguments"]["answer"];
    if select || answer.is_null() {
        result["status"] = json!("unresolved");
        return Ok(result);
    }
    if serde_json::to_vec(answer)
        .map_err(|e| CoreError::new(e.to_string()))?
        .len()
        > 16384
        || forbidden(answer)
    {
        return Err(CoreError::new(
            "procedure answer exceeds bounds or carries an authority envelope",
        ));
    }
    let root = Dir::open_ambient_dir(target, ambient_authority())
        .map_err(|e| CoreError::new(e.to_string()))?;
    for evidence in answer["evidence"].as_array().into_iter().flatten() {
        let path = evidence["reference"].as_str().unwrap();
        let current = crate::decision_source::relative(path)
            .and_then(|_| crate::native_planning::read(&root, path));
        if !matches!(current, Ok(Some(ref bytes)) if evidence["revision"] == crate::decision_source::hash(bytes))
        {
            result["status"] = json!("stale");
            result["reason"] = json!("relied-upon-evidence-unavailable-or-changed");
            return Ok(result);
        }
    }
    let branches = answer["branches"].as_array().cloned().unwrap_or_default();
    if (answer["disposition"] == "answered") == branches.is_empty() {
        return Err(CoreError::new(
            "answered requires branch identities; unresolved answers cannot select a branch",
        ));
    }
    let mut next = Vec::new();
    for id in branches {
        let branch = resource["branches"]
            .as_array()
            .unwrap()
            .iter()
            .find(|b| b["id"] == id)
            .ok_or_else(|| CoreError::new("answer names an undeclared branch"))?;
        next.push(json!({"source_ref":selection["source_ref"],"skill_id":selection["skill_id"],"resource":branch["next"]}));
    }
    result["status"] = json!("current");
    result["answer"] = answer.clone();
    result["next"] = json!(next);
    result["carriage"] = request.clone();
    Ok(result)
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::{
        fs,
        path::PathBuf,
        time::{SystemTime, UNIX_EPOCH},
    };
    struct Fixture(PathBuf);
    impl Fixture {
        fn new() -> Self {
            let root = std::env::temp_dir().join(format!(
                "aw-procedure-answer-{}-{}",
                std::process::id(),
                SystemTime::now()
                    .duration_since(UNIX_EPOCH)
                    .unwrap()
                    .as_nanos()
            ));
            fs::create_dir_all(root.join("tools/skills/note")).unwrap();
            fs::write(root.join("tools/skills/REGISTRY.json"),json!({"skills":[{"id":"note","path":"note/SKILL.md","semantic_routes":["note/change"],"procedure_resource":"procedure.md"}]}).to_string()).unwrap();
            fs::write(root.join("tools/skills/note/SKILL.md"), "Read procedure.md").unwrap();
            fs::write(root.join("tools/skills/note/procedure.md"),"```agentic-procedure\n{\"kind\":\"agentic-workspace/procedure/v1\",\"id\":\"visible\",\"question\":\"Does this affect users?\",\"branches\":[{\"id\":\"yes\",\"description\":\"Visible change\",\"next\":\"note.md\"}]}\n```\n").unwrap();
            fs::write(root.join("tools/skills/note/note.md"), "Write a user note.").unwrap();
            Self(root)
        }
        fn start(&self, task: &str, request: Value) -> Result<Value, CoreError> {
            crate::operating::start(
                json!({"target":self.0,"task":task,"projection":"full","request":request}),
            )
        }
        fn answer_request(&self) -> Value {
            let initial = self.start("note", Value::Null).unwrap();
            let mut discover = initial["semantic_routes"]["requests"][0].clone();
            discover["arguments"] = json!({"parent":"note/change"});
            let leaf = self.start("note", discover).unwrap();
            let selected = self
                .start("note", leaf["procedure"]["requests"][0].clone())
                .unwrap();
            assert_eq!(selected["procedure"]["status"], "unresolved");
            selected["procedure"]["requests"][0].clone()
        }
    }
    impl Drop for Fixture {
        fn drop(&mut self) {
            fs::remove_dir_all(&self.0).unwrap();
        }
    }

    #[test]
    fn semantic_answer_carriage_is_scoped_current_and_disposable() {
        let f = Fixture::new();
        let mut request = f.answer_request();
        fs::write(f.0.join("evidence.md"), "Observed patch").unwrap();
        request["arguments"]["answer"] = json!({"disposition":"answered","branches":["yes"],"material":{"summary":"Visible change","items":[1,2]},"evidence":[{"reference":"evidence.md","revision":crate::decision_source::hash(b"Observed patch")}]});
        let first = f.start("note", request.clone()).unwrap();
        assert_eq!(first["procedure"]["status"], "current");
        assert_eq!(first["procedure"]["authority_effect"], "none");
        assert_eq!(
            first["procedure"]["next"][0]["resource"],
            "tools/skills/note/note.md"
        );
        assert_eq!(first["procedure"]["carriage"], request);
        fs::write(f.0.join("unrelated.md"), "Unrelated change").unwrap();
        assert_eq!(
            f.start("note", request.clone()).unwrap()["procedure"],
            first["procedure"]
        );
        assert_eq!(
            f.start("another task", request.clone()).unwrap()["procedure"]["status"],
            "stale"
        );
        let mut other = request.clone();
        other["arguments"]["selection"]["instance"] = json!("another");
        assert_eq!(
            f.start("note", other).unwrap()["procedure"]["status"],
            "stale"
        );
        assert_eq!(
            f.start("note", f.answer_request()).unwrap()["procedure"]["status"],
            "unresolved"
        );
        fs::write(f.0.join("evidence.md"), "Changed patch").unwrap();
        assert_eq!(
            f.start("note", request.clone()).unwrap()["procedure"]["status"],
            "stale"
        );
        fs::write(f.0.join("evidence.md"), "Observed patch").unwrap();
        let path = f.0.join("tools/skills/note/procedure.md");
        let text = fs::read_to_string(&path)
            .unwrap()
            .replace("Does this affect users?", "Does this affect maintainers?");
        fs::write(path, text).unwrap();
        assert_eq!(
            f.start("note", request).unwrap()["procedure"]["status"],
            "stale"
        );
        assert!(!f.0.join(".agentic-workspace/local").exists());
    }

    #[test]
    fn unresolved_answers_and_bounds_never_create_false_branches_or_authority() {
        let f = Fixture::new();
        let request = f.answer_request();
        for disposition in ["unknown", "defer", "no-match", "conflict"] {
            let mut carried = request.clone();
            carried["arguments"]["answer"] = json!({"disposition":disposition});
            let result = f.start("note", carried).unwrap();
            assert_eq!(result["procedure"]["answer"]["disposition"], disposition);
            assert_eq!(result["procedure"]["next"], json!([]));
        }
        for answer in [
            json!({"disposition":"answered"}),
            json!({"disposition":"unknown","branches":["yes"]}),
            json!({"disposition":"answered","branches":["missing"]}),
            json!({"disposition":"answered","branches":["yes"],"material":{"kind":"agentic-workspace/operation-invocation/v1"}}),
            json!({"disposition":"unknown","material":"x".repeat(17000)}),
        ] {
            let mut carried = request.clone();
            carried["arguments"]["answer"] = answer;
            assert!(f.start("note", carried).is_err());
        }
    }
}
