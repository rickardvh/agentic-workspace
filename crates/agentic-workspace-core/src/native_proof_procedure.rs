//! One selected proof operation plus current receipt admission. No action loop,
//! source interpreter, semantic answers, independent review or retained cursor.
use crate::{CoreError, native_methods, operating};
use serde::Deserialize;
use serde_json::{Value, json};
use std::path::Path;

#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct Input {
    target: String,
    #[serde(default)]
    task: String,
    #[serde(default)]
    changed: Vec<String>,
    #[serde(default)]
    projection: Option<String>,
    request: Step,
}
#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct Step {
    operation: String,
    #[serde(default)]
    request: Option<Value>,
    #[serde(default)]
    invocation: Option<Value>,
    #[serde(default)]
    reference: Option<Value>,
    #[serde(default)]
    answer: Option<Value>,
    #[serde(default)]
    expected_revision: Option<String>,
    #[serde(default)]
    evidence_refs: Vec<String>,
}
const SKILL: &str = "workspace-proof-selection";
const COMMAND: &str = "proof-procedure";
fn err(message: impl ToString) -> CoreError {
    CoreError::new(message.to_string())
}
fn requests(value: Option<&Value>) -> Vec<Value> {
    value
        .map(|v| v.as_array().cloned().unwrap_or_else(|| vec![v.clone()]))
        .unwrap_or_default()
}
fn present(full: Value, context: Value, method: &Value, calls: usize) -> Result<Value, CoreError> {
    let verification = &full["verification"];
    let mut proof = serde_json::Map::new();
    for key in [
        "status",
        "strategy",
        "strategy_control",
        "strategy_request",
        "assurance_request",
        "execution_requests",
        "evidence",
        "assurance_owner_gaps",
        "evidence_gaps",
        "claim_review",
        "source_reconciliation",
    ] {
        if let Some(value) = verification.get(key) {
            proof.insert(key.to_owned(), value.clone());
        }
    }
    // Shared operating projection preserves all owner restrictions and exact
    // question/action envelopes without duplicating capability schemas.
    let view = operating::project_start(full, context, &json!("compact"))?;
    Ok(
        json!({"kind":"agentic-workspace/proof-procedure-result/v1","status":"yielded","procedure_revision":method["revision"],"public_owner_calls":calls,"proof":proof,"operating":view,"completion_authority":false}),
    )
}

pub(crate) fn view(value: Value) -> Result<Value, CoreError> {
    let input: Input = serde_json::from_value(value).map_err(err)?;
    if input.projection.as_deref().is_some_and(|p| p != "compact") {
        return Err(err(
            "proof procedure returns selected context; use the ordinary owner for full/carried projections",
        ));
    }
    let step = &input.request;
    if !["direct", "prepare", "execute"].contains(&step.operation.as_str()) {
        return Err(err("unknown proof procedure operation"));
    }
    if step.request.is_some() && step.invocation.is_some() {
        return Err(err("supply an exact request or invocation, not both"));
    }
    if step.evidence_refs.len() > 64 {
        return Err(err("proof evidence references exceed bounded selection"));
    }
    if step.operation == "direct" {
        if step.request.is_some()
            || step.invocation.is_some()
            || step.reference.is_some()
            || step.answer.is_some()
            || !step.evidence_refs.is_empty()
        {
            return Err(err("direct proof procedure accepts no owner material"));
        }
        return Ok(
            json!({"kind":"agentic-workspace/proof-procedure-result/v1","status":"direct","public_owner_calls":0,"effect_outcome":"not-required","authority_effect":"none"}),
        );
    }
    let target = Path::new(&input.target);
    let method = native_methods::selected(target, SKILL, COMMAND)?;
    if method["status"] != "current"
        || step
            .expected_revision
            .as_ref()
            .is_some_and(|r| method["revision"] != *r)
    {
        return Ok(
            json!({"kind":"agentic-workspace/proof-procedure-result/v1","status":"unavailable-or-stale-method","method":method,"public_owner_calls":0,"effect_outcome":"not-invoked","recovery":"Restore or reread the current standard skill and compatible native runtime; Markdown alone does not establish proof."}),
        );
    }
    let mut context = json!({"target":input.target,"task":input.task,"changed":input.changed});
    if let Some(request) = &step.request {
        context["request"] = request.clone();
    }
    if let Some(reference) = &step.reference {
        context["reference"] = reference.clone();
    }
    if let Some(answer) = &step.answer {
        context["answer"] = answer.clone();
    }
    if step.operation == "prepare" {
        if step.invocation.is_some() {
            return Err(err("prepare never invokes an effect"));
        }
        let mut full_input = context.clone();
        full_input["projection"] = json!("full");
        let full = operating::start_owner(full_input, "proof")?;
        return present(full, context, &method, 1);
    }
    if step.reference.is_some() || step.answer.is_some() {
        return Err(err(
            "answer the current question with prepare before selecting execution",
        ));
    }
    let mut calls = 0;
    let action = if let Some(invocation) = &step.invocation {
        invocation.clone()
    } else {
        let supplied = requests(step.request.as_ref());
        if supplied
            .iter()
            .filter(|r| r["request_kind"] == "verification/execute-selected/v1")
            .count()
            != 1
        {
            return Err(err(
                "execute requires exactly one owner-returned selected-check request or exact invocation",
            ));
        }
        let mut full_input = context.clone();
        full_input["projection"] = json!("full");
        let full = operating::start_owner(full_input, "proof")?;
        calls += 1;
        let candidates: Vec<Value> = full["decision_packet"]["ready_actions"]
            .as_array()
            .into_iter()
            .flatten()
            .filter(|a| a["source_owner"] == "verification" && a["operation_id"] == "proof.report")
            .cloned()
            .collect();
        if candidates.len() != 1 {
            return present(full, context, &method, calls);
        }
        candidates[0].clone()
    };
    if action["source_owner"] != "verification"
        || action["operation_id"] != "proof.report"
        || action["arguments"]["execute_selected"] != true
    {
        return Err(err(
            "proof composition only invokes an exact selected native check",
        ));
    }
    if native_methods::selected(target, SKILL, COMMAND)? != method {
        return Ok(
            json!({"status":"stale-method","effect_outcome":"not-invoked","public_owner_calls":calls}),
        );
    }
    let mut execution = json!({"target":input.target,"task":input.task,"changed":input.changed,"invocation":action,"projection":"full"});
    let result = operating::invoke_owner(execution.clone(), "proof")?;
    calls += 1;
    // Retain the exact effect even if later current resolution or evidence
    // admission fails. Reentry uses owner custody; no automatic retry.
    let continuation = (|| -> Result<Value, CoreError> {
        if result["continuation_status"] != "current" {
            return Err(err("owner continuation unavailable"));
        }
        let mut next = result["continuation"]["context"].clone();
        let mut prerequisites = requests(step.request.as_ref());
        prerequisites.retain(|r| {
            !matches!(
                r["request_kind"].as_str(),
                Some("verification/execute-selected/v1" | "verification/claim/v1")
            )
        });
        if step.invocation.is_some() {
            if let Some(scope) = action["arguments"]["selection"]["strategy"]
                .get("assurance_request")
                .filter(|s| !s.is_null())
            {
                prerequisites.push(scope.clone());
            }
            // Strategy assessments need current owner envelopes. Yield when an
            // exact invocation lacks that carriage instead of rebuilding one.
            if !action["arguments"]["selection"]["strategy"]["assessment"].is_null() {
                return Err(err(
                    "retain the selected execution request set to reobserve its strategy assessment",
                ));
            }
        }
        let current = if prerequisites.is_empty() {
            result["continuation"]["result"].clone()
        } else {
            next["request"] = json!(prerequisites);
            let mut query = next.clone();
            query["projection"] = json!("full");
            calls += 1;
            operating::start_owner(query, "proof")?
        };
        let mut claim = current["verification"]["requests"][0].clone();
        if claim.is_null() {
            return Err(err("current claim evidence request unavailable"));
        }
        let mut refs = step.evidence_refs.clone();
        if let Some(reference) = result["value"]["publication"]["reference"].as_str() {
            refs.push(reference.to_owned());
        }
        refs.sort();
        refs.dedup();
        claim["arguments"]["evidence_refs"] = json!(refs);
        prerequisites.push(claim);
        next["request"] = json!(prerequisites);
        if native_methods::selected(target, SKILL, COMMAND)? != method {
            return Err(err("procedure changed after the confirmed effect"));
        }
        let mut query = next.clone();
        query["projection"] = json!("full");
        calls += 1;
        present(
            operating::start_owner(query, "proof")?,
            next,
            &method,
            calls,
        )
    })();
    // Return compact owner effect data, leaving bulky current context in the
    // selected preparation instead of copying it a second time.
    let mut effect = result;
    effect.as_object_mut().unwrap().remove("next_decision");
    if let Some(c) = effect
        .get_mut("continuation")
        .and_then(Value::as_object_mut)
    {
        c.remove("result");
    }
    execution.as_object_mut().unwrap().remove("projection");
    match continuation {
        Ok(mut prepared) => {
            prepared["effect"] = effect;
            Ok(prepared)
        }
        Err(error) => Ok(
            json!({"kind":"agentic-workspace/proof-procedure-result/v1","status":"reentry-required","effect":effect,"exact_reentry":execution,"public_owner_calls":calls,"retry_effect":false,"diagnostic":error.to_string(),"completion_authority":false}),
        ),
    }
}
