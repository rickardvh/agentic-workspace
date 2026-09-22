//! Passive, selected procedure resources. No semantic evaluation or effects.
use crate::{
    CoreError,
    decision_source::{hash, relative},
};
use cap_std::fs::Dir;
use serde::Deserialize;
use serde_json::{Value, json};
use std::collections::BTreeSet;

const FENCE: &str = "```agentic-procedure";

#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct Question {
    kind: String,
    id: String,
    question: String,
    branches: Vec<Branch>,
    #[serde(default)]
    context: Vec<String>,
}

#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct Branch {
    id: String,
    description: String,
    next: String,
}

fn error(message: impl ToString) -> CoreError {
    CoreError::new(message.to_string())
}

fn reference(base: &str, path: &str) -> Result<String, CoreError> {
    relative(path)?;
    let parent = base.rsplit_once('/').map(|v| v.0).unwrap_or("");
    Ok(if parent.is_empty() {
        path.to_owned()
    } else {
        format!("{parent}/{path}")
    })
}

fn read(root: &Dir, path: &str) -> Result<(String, String), CoreError> {
    let bytes = crate::native_planning::read(root, path)?
        .ok_or_else(|| error(format!("procedure resource missing: {path}")))?;
    if bytes.len() > 65536 {
        return Err(error("procedure resource exceeds 64 KiB"));
    }
    let text = String::from_utf8(bytes.clone()).map_err(error)?;
    Ok((text, hash(&bytes)))
}

/// The registry nominates a resource relative to its SKILL.md. Exact selections
/// can only read that resource or one of its explicitly declared next/context
/// references. All paths use the existing confined, bounded native reader.
pub(crate) fn detail(
    root: &Dir,
    source: &Value,
    declaration: &Value,
    selected: Option<&str>,
) -> Value {
    let resolve = || -> Result<Value, CoreError> {
        let skill = source["procedure"]["reference"]
            .as_str()
            .ok_or_else(|| error("skill path missing"))?;
        if source["procedure"]["status"] != "available" {
            return Err(error("skill source unavailable"));
        }
        let declared = declaration
            .as_str()
            .ok_or_else(|| error("procedure_resource must be a relative path"))?;
        let path = reference(skill, declared)?;
        let (text, revision) = read(root, &path)?;
        let normalized = text.replace("\r\n", "\n");
        let lines: Vec<_> = normalized.lines().collect();
        let starts: Vec<_> = lines
            .iter()
            .enumerate()
            .filter(|(_, line)| **line == FENCE)
            .map(|(i, _)| i)
            .collect();
        if starts.len() != 1 {
            return Err(error(
                "procedure resource requires one agentic-procedure fence",
            ));
        }
        let start = starts[0] + 1;
        let end = lines[start..]
            .iter()
            .position(|line| *line == "```")
            .map(|i| start + i)
            .ok_or_else(|| error("procedure fence is not closed"))?;
        let question: Question =
            serde_json::from_str(&lines[start..end].join("\n")).map_err(error)?;
        if question.kind != "agentic-workspace/procedure/v1" {
            return Err(error("incompatible procedure resource"));
        }
        fn identity(value: &str) -> bool {
            !value.is_empty()
                && value.len() <= 128
                && value
                    .bytes()
                    .all(|b| b.is_ascii_alphanumeric() || b == b'-' || b == b'_')
        }
        if !identity(&question.id)
            || question.question.trim().is_empty()
            || question.question.len() > 8192
            || question.branches.is_empty()
            || question.branches.len() > 32
            || question.context.len() > 32
        {
            return Err(error("invalid or over-limit procedure question"));
        }
        let mut ids = BTreeSet::new();
        let mut references = BTreeSet::new();
        let mut dependencies = BTreeSet::new();
        let mut branches = Vec::new();
        for branch in question.branches {
            if !identity(&branch.id)
                || !ids.insert(branch.id.clone())
                || branch.description.trim().is_empty()
                || branch.description.len() > 8192
            {
                return Err(error("invalid or duplicate procedure branch"));
            }
            let next = reference(&path, &branch.next)?;
            references.insert(next.clone());
            branches.push(json!({"id":branch.id,"description":branch.description,"next":next}));
        }
        let mut context = Vec::new();
        for item in question.context {
            let next = reference(&path, &item)?;
            references.insert(next.clone());
            dependencies.insert(next.clone());
            context.push(next);
        }
        let mut material = Vec::new();
        for dependency in &dependencies {
            let (_, revision) = read(root, dependency)?;
            material.push(json!({"reference":dependency,"revision":revision}));
        }
        let identity = json!({"source_ref":source["source_ref"],"skill":skill,"resource":path,"id":question.id});
        let mut result = json!({"status":"current","identity":identity,"reference":path,
            "source_revision":revision,"question":question.question,"branches":branches,"context":context,
            "dependencies":material,"authority_effect":"none"});
        if let Some(selected) = selected {
            if selected != path && !references.contains(selected) {
                return Err(error("resource is not declared by this procedure"));
            }
            let (body, revision) = read(root, selected)?;
            if selected != path && !dependencies.contains(selected) {
                result["dependencies"]
                    .as_array_mut()
                    .unwrap()
                    .push(json!({"reference":selected,"revision":revision}));
            }
            result["selected"] = json!({"reference":selected,"revision":revision,"text":body});
        }
        result["revision"] = json!(crate::digest(
            &json!({"detail":result,"skill_revision":source["procedure"]["revision"]})
        )?);
        Ok(result)
    };
    resolve().unwrap_or_else(|problem| json!({"status":"unavailable","reason":problem.to_string(),"authority_effect":"none",
        "recovery":"Repair or reselect the exact procedure resource; ordinary skill use and owner restrictions remain unchanged."}))
}
