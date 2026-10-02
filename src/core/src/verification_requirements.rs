//! One source-owned obligation's execution requirements. Evidence and reviewer
//! authentication remain separate Verification contracts, never agent assertions.
use crate::{CoreError, digest, native_verification, prepare_request_value};
use serde_json::{Value, json};
use std::{collections::BTreeSet, path::Path};

pub(crate) fn declaration() -> Value {
    let schema: Value = serde_json::from_str(include_str!(
        "../contracts/schemas/verification_requirements.schema.json"
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
        "../contracts/schemas/verification_requirements.schema.json"
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
    let mut source_work = Value::Null;
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
            if !refs.iter().any(|r| r == reference) {
                return Err(CoreError::new(
                    "Selected obligation is not in the current source scope.",
                ));
            }
            let id = reference
                .split_once("#protocols.")
                .ok_or_else(|| CoreError::new("selected obligation is not a current protocol"))?
                .1;
            selected = json!({"reference":reference,"protocol":protocols.get(id).ok_or_else(||CoreError::new("selected obligation disappeared"))?});
            if let Some(receipt_ref) = args["analysis_receipt_ref"].as_str() {
                if args["role"] != "executor" {
                    return Err(CoreError::new(
                        "Read-only investigation uses executor analysis; it cannot establish evaluator independence.",
                    ));
                }
                source_work = analysis_work(
                    Path::new(input["target"].as_str().unwrap()),
                    &input,
                    &source,
                    &selected,
                    receipt_ref,
                )?;
                if source_work["status"] == "ready" {
                    contribution = json!({"id":source_work["work"]["id"],"revision":source_work["work"]["revision"],"current":true,"role":"executor","independence_mode":"none","required_proof_classes":[]});
                    gaps.clear();
                } else {
                    gaps = vec!["selected-investigation-requires-current-source-and-receipt"];
                }
            }
            if source_work.is_null() && !args["judgment"].is_null() {
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
        json!({"kind":"agentic-workspace/verification-requirements/v1","status":if contribution.is_null(){"unresolved"}else{"resolved"},"source_revision":source_revision,"strategy_revision":source["strategy_revision"],"source":source["source"],"task_identity":task,"current_work":input["current_work"],"role":input["role"],"selected_obligation":selected,"obligations":protocols,"request":template,"capability_contract":contract,"verification":contribution,"source_work":source_work,"gaps":gaps,
        "judgment_question":"Select the exact current protocol assigned to this role. What independence mode and proof capabilities does executing that obligation require, and why? Preserve its actual authority/evidence requirements; leave judgment unresolved if they are unclear.",
        "claim_boundary":"Execution requirements for only the selected obligation. No proof, reviewer authentication, evidence freshness, or satisfaction/waiver of this or any other closeout obligation."}),
    )
}

fn analysis_work(
    target: &Path,
    input: &Value,
    source: &Value,
    selected: &Value,
    reference: &str,
) -> Result<Value, CoreError> {
    use sha2::{Digest, Sha256};
    let analysis = &selected["protocol"]["analysis"];
    let mut gaps = Vec::new();
    if !analysis.is_object() {
        gaps.push("Define the bounded analysis question, input references and stop conditions in this protocol.".to_owned());
    }
    let receipt = crate::native_proof::local_receipt(target, reference);
    let mut inputs = analysis["input_refs"]
        .as_array()
        .cloned()
        .unwrap_or_default();
    let mut observed = Value::Null;
    match receipt {
        Ok(receipt) => {
            let changed = input["changed_paths"].as_array().unwrap().iter().map(|p|p.as_str().unwrap().to_owned()).collect::<Vec<_>>();
            let freshness = crate::native_proof::freshness(target, input["task"].as_str().unwrap(), &changed, &input["current_work"], &source["strategy"], &receipt)?;
            let committed = crate::native_proof::committed_publication(target, &receipt)?;
            let protocol_id = selected["reference"].as_str().unwrap().split_once("#protocols.").unwrap().1;
            let matching = committed.as_ref().is_some_and(|c| c["invocation"]["arguments"]["selection"]["strategy"]["protocols"].get(protocol_id) == Some(&selected["protocol"]));
            if freshness["status"] != "reusable" || !matching {
                gaps.push("The selected receipt does not match this current protocol/subject/environment; use Verification's current selected-proof route.".to_owned());
            }
            let artifact = &receipt["execution_artifact"];
            if let Some(path) = artifact["path"].as_str() {
                let root = cap_std::fs::Dir::open_ambient_dir(target, cap_std::ambient_authority()).map_err(|e|CoreError::new(e.to_string()))?;
                if native_verification::read(&root,path).ok().flatten().is_some_and(|bytes| format!("{:x}",Sha256::digest(&bytes)) == artifact["sha256"]) {
                    inputs.push(json!(path));
                } else {
                    gaps.push("Selected execution log is missing or changed; preserve committed receipt and resolve its owner recovery.".to_owned());
                }
            } else {
                gaps.push("Selected receipt has no bounded execution log.".to_owned());
            }
            observed = json!({"reference":reference,"result":receipt["result"],"command":receipt["command"],"subject":receipt["proof_subject"],"artifact":artifact,"freshness":freshness});
        }
        Err(_) => gaps.push("Selected native receipt is unavailable or lacks committed custody; recover it before investigation.".to_owned()),
    }
    let revision = digest(&json!([selected, observed, input["current_work"]]))?;
    Ok(
        json!({"status":if gaps.is_empty(){"ready"}else{"shaping-required"},"producer":"verification",
        "work":{"id":format!("verification-analysis:{}",selected["reference"].as_str().unwrap()),"revision":revision},
        "definition":{"result_class":"read-only","input_refs":inputs,"mutation_paths":[],"required_proof_classes":[],"accepted_dependencies":[]},
        "outcome":{"question":analysis["question"],"protocol":selected},"scope":{"boundary":"Read supplied code and exact execution artifact; return analysis only."},
        "constraints":{"prohibited_effects":["execute-commands","write-files","grant-proof","independent-approval","claim-completion"],"stop_conditions":analysis["stop_conditions"]},
        "accepted_context":observed,"proof":{"trust_level":"unproven-analysis","satisfies_obligation":false},"next_action":"Investigate the selected receipt and return findings or a specific blocker.",
        "return_destination":"Originating Verification investigation; Assignment admission permits use of analysis only. Further checks use current proof.report; repair requires separate scope.",
        "gaps":gaps,"claim_boundary":"Analysis is not passing proof, evidence sufficiency, reviewer authentication or completion."}),
    )
}
