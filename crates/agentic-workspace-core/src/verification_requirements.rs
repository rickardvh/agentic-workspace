//! One source-owned obligation's execution requirements. Evidence and reviewer
//! authentication remain separate Verification contracts, never agent assertions.
use crate::{CoreError, digest, native_verification, prepare_request_value};
use serde_json::{Value, json};
use std::{collections::BTreeSet, path::Path};

pub(crate) fn declaration() -> Value {
    let schema: Value = serde_json::from_str(include_str!(
        "../../../src/agentic_workspace/contracts/schemas/verification_requirements.schema.json"
    ))
    .expect("checked schema");
    let mut arguments = schema["$defs"]["arguments"].clone();
    arguments["$schema"] = schema["$schema"].clone();
    json!({"kind":"verification/requirements/v1","result_kind":"agentic-workspace/verification-requirements/v1","input_schema":arguments})
}

pub fn view(input: Value) -> Result<Value, CoreError> {
    resolve(input, None, None)
}

pub(crate) fn resolve(
    input: Value,
    transport_work: Option<&Value>,
    full_contract: Option<&Value>,
) -> Result<Value, CoreError> {
    let schema: Value = serde_json::from_str(include_str!(
        "../../../src/agentic_workspace/contracts/schemas/verification_requirements.schema.json"
    ))
    .expect("checked schema");
    crate::schema_validator(&schema, "verification requirements")?
        .validate(&input)
        .map_err(|e| CoreError::new(format!("invalid verification requirements input: {e}")))?;
    let paths: Vec<_> = input["changed_paths"]
        .as_array()
        .unwrap()
        .iter()
        .map(|p| p.as_str().unwrap().to_owned())
        .collect();
    let task = crate::direct_task::subject(input["task"].as_str().unwrap(), &paths)?;
    let binding = json!({"kind":"current-work","id":digest(&json!({"task_identity":task,"current_work":input["current_work"],"role":input["role"]}))?});
    let work = transport_work.unwrap_or(&binding);
    let source = native_verification::view(
        Path::new(input["target"].as_str().unwrap()),
        input["task"].as_str().unwrap(),
        &paths,
        work,
        None,
        None,
    )?;
    let protocols = source["strategy"]["protocols"]
        .as_object()
        .ok_or_else(|| CoreError::new("current Verification protocol owner unavailable"))?;
    let refs: Vec<_> = protocols
        .keys()
        .map(|id| {
            format!(
                "{}#protocols.{id}",
                source["strategy"]["source"].as_str().unwrap()
            )
        })
        .collect();
    if refs.len() > 32 {
        return Err(CoreError::new(
            "more than 32 current Verification obligations; narrow the current work",
        ));
    }
    let source_revision = digest(
        &json!({"source":source["source"],"strategy_revision":source["strategy_revision"],"task":task,"current_work":input["current_work"],"role":input["role"]}),
    )?;
    let contract = full_contract.unwrap_or(&source["capability_contract"]);
    let owner_revision = &source["capability_contract"]["owners"][0]["revision"];
    let template = json!({"kind":"agentic-workspace/public-request/v1","id":format!("verification-requirements:{source_revision}"),"owner":"verification","owner_revision":owner_revision,"source_revision":source_revision,"capability_revision":contract["revision"],"task_identity":work,"request_kind":"verification/requirements/v1","arguments":{"obligation_ref":null,"role":input["role"],"judgment":null}});
    let mut contribution = Value::Null;
    let mut selected = Value::Null;
    let mut gaps = vec![if refs.is_empty() {
        "no-current-path-selected-verification-obligation"
    } else {
        "selected-obligation-requirement-judgment-required"
    }];
    if !input["request"].is_null() {
        let request = &input["request"];
        prepare_request_value(
            json!({"request":request,"current_work":work,"capability_contract":contract}),
        )?;
        if request["source_revision"] != source_revision || request["owner"] != "verification" {
            return Err(CoreError::new(
                "Verification requirements source/task/work/role changed; resolve current judgment again",
            ));
        }
        let args = &request["arguments"];
        if args["role"] != input["role"]
            || request["request_kind"] != "verification/requirements/v1"
        {
            return Err(CoreError::new(
                "Verification requirement judgment role or request kind changed",
            ));
        }
        if let Some(reference) = args["obligation_ref"].as_str() {
            let id = reference
                .split_once("#protocols.")
                .ok_or_else(|| CoreError::new("selected obligation is not a current protocol"))?
                .1;
            selected = json!({"reference":reference,"protocol":protocols.get(id).ok_or_else(||CoreError::new("selected obligation disappeared"))?});
            if !args["judgment"].is_null() {
                let proof: BTreeSet<_> = args["judgment"]["required_proof_classes"]
                    .as_array()
                    .unwrap()
                    .iter()
                    .map(|p| p.as_str().unwrap())
                    .collect();
                let revision = digest(
                    &json!({"source_revision":source_revision,"selected":selected,"role":input["role"],"judgment":args["judgment"]}),
                )?;
                contribution = json!({"id":format!("verification-obligation:{reference}"),"revision":revision,"current":true,"role":input["role"],"independence_mode":args["judgment"]["independence_mode"],"required_proof_classes":proof});
                gaps.clear();
            }
        }
    }
    Ok(
        json!({"kind":"agentic-workspace/verification-requirements/v1","status":if contribution.is_null(){"unresolved"}else{"resolved"},"source_revision":source_revision,"strategy_revision":source["strategy_revision"],"source":source["source"],"task_identity":task,"current_work":input["current_work"],"role":input["role"],"selected_obligation":selected,"obligations":protocols,"request":template,"capability_contract":contract,"verification":contribution,"gaps":gaps,
        "judgment_question":"Select the exact current protocol assigned to this role. What independence mode and proof capabilities does executing that obligation require, and why? Preserve its actual authority/evidence requirements; leave judgment unresolved if they are unclear.",
        "claim_boundary":"Execution requirements for only the selected obligation. No proof, reviewer authentication, evidence freshness, or satisfaction/waiver of this or any other closeout obligation."}),
    )
}
