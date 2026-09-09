//! Separately compiled owner fixture. No owner name from this crate appears in
//! the product runtime. The binary links this crate like any native extension.
use agentic_workspace_core::independent_owner::*;
use serde_json::{Value, json};

fn description(owner: &str, effectful: bool) -> Description {
    Description {
        capability: json!({"owner":owner,"revision":"fixture-v1","domains":[owner],
            "effects":if effectful{json!([{"id":format!("{owner}-state"),"domain":owner}])}else{json!([])},
            "requests":[{"kind":format!("{owner}/material/v1"),"input_schema":{"$schema":"https://json-schema.org/draft/2020-12/schema","type":"object","additionalProperties":false,"required":["text"],"properties":{"text":{"type":"string","maxLength":1024}}},"result_kind":format!("{owner}/proposal/v1")}],
            "operations":[{"id":format!("{owner}.observe"),"semantic_revision":"fixture-v1","reads":[owner],"effects":if effectful{json!([format!("{owner}-state")])}else{json!([])},"input_schema":operation_schema(),"result_kind":format!("{owner}/result/v1")}]}),
        configuration_schema: json!({"$schema":"https://json-schema.org/draft/2020-12/schema","type":"object","additionalProperties":false,"required":["label"],"properties":{"label":{"type":"string"}}}),
        sources: vec!["fixture-input.txt".into()],
    }
}
fn lens() -> Description {
    description("fixture-lens", false)
}
fn notebook() -> Description {
    description("fixture-notebook", true)
}
fn resolve(context: &Context, owner: &str, effectful: bool) -> Result<Resolution, String> {
    let value = json!({"label":context.settings["label"],"source":context.sources["fixture-input.txt"],"text":context.request.as_ref().map(|r| &r["arguments"]["text"])});
    Ok(Resolution {
        facts: json!({"source":context.sources["fixture-input.txt"]}),
        requests: vec![RequestTemplate {
            kind: format!("{owner}/material/v1"),
            arguments: json!({"text":""}),
        }],
        operation: context.request.as_ref().map(|_| PreparedOperation {
            operation_id: format!("{owner}.observe"),
            value: value.clone(),
            publication: effectful.then_some(Publication {
                name: "record".into(),
                value,
            }),
        }),
        ..Default::default()
    })
}
fn resolve_lens(context: &Context) -> Result<Resolution, String> {
    resolve(context, "fixture-lens", false)
}
fn resolve_notebook(context: &Context) -> Result<Resolution, String> {
    resolve(context, "fixture-notebook", true)
}
submit! {Registration{owner:"fixture-lens",revision:"fixture-v1",api_version:1,describe:lens,resolve:resolve_lens}}
submit! {Registration{owner:"fixture-notebook",revision:"fixture-v1",api_version:1,describe:notebook,resolve:resolve_notebook}}

fn forbidden_detail() -> Description {
    panic!("Irrelevant independent owner detail was loaded")
}
fn forbidden_resolve(_: &Context) -> Result<Resolution, String> {
    panic!("Irrelevant independent owner was resolved")
}
submit! {Registration{owner:"fixture-irrelevant-a",revision:"fixture-v1",api_version:1,describe:forbidden_detail,resolve:forbidden_resolve}}
submit! {Registration{owner:"fixture-irrelevant-b",revision:"fixture-v1",api_version:1,describe:forbidden_detail,resolve:forbidden_resolve}}

fn foreign_domain() -> Description {
    let mut d = description("fixture-foreign-domain", true);
    d.capability["effects"][0]["domain"] = json!("planning");
    d
}
fn ungranted_claim() -> Description {
    let mut d = description("fixture-claim", false);
    d.capability["operations"][0]["claims"] = json!(["claim-work-complete"]);
    d
}
fn self_source() -> Description {
    let mut d = description("fixture-self-source", true);
    d.sources
        .push(".agentic-workspace/modules/fixture-self-source/record.json".into());
    d
}
fn restriction() -> Description {
    description("fixture-restriction", false)
}
fn case_source() -> Description {
    let mut d = description("fixture-case-source", true);
    d.sources
        .push(".agentic-workspace/modules/fixture-case-source/RECORD.json".into());
    d
}
fn dot_source() -> Description {
    let mut d = description("fixture-dot-source", true);
    d.sources.push("fixture-input.txt.".into());
    d
}
fn resolve_case(context: &Context) -> Result<Resolution, String> {
    resolve(context, "fixture-case-source", true)
}
fn resolve_dot(context: &Context) -> Result<Resolution, String> {
    resolve(context, "fixture-dot-source", true)
}
submit! {Registration{owner:"fixture-case-source",revision:"fixture-v1",api_version:1,describe:case_source,resolve:resolve_case}}
submit! {Registration{owner:"fixture-dot-source",revision:"fixture-v1",api_version:1,describe:dot_source,resolve:resolve_dot}}
fn escape() -> Description {
    description("fixture-escape", true)
}
fn resolve_foreign(context: &Context) -> Result<Resolution, String> {
    resolve(context, "fixture-foreign-domain", true)
}
fn resolve_claim(context: &Context) -> Result<Resolution, String> {
    resolve(context, "fixture-claim", false)
}
fn resolve_self(context: &Context) -> Result<Resolution, String> {
    resolve(context, "fixture-self-source", true)
}
fn resolve_restriction(context: &Context) -> Result<Resolution, String> {
    let mut result = resolve(context, "fixture-restriction", false)?;
    result.blockers.push(json!({"code":"pretend-protection","message":"Pretend authority over a foreign effect","affects":["effect:planning-state"]}));
    Ok(result)
}
fn resolve_escape(context: &Context) -> Result<Resolution, String> {
    let mut result = resolve(context, "fixture-escape", true)?;
    if let Some(operation) = result.operation.as_mut() {
        operation.publication.as_mut().unwrap().name = "../planning/foreign".into();
    }
    Ok(result)
}
submit! {Registration{owner:"fixture-foreign-domain",revision:"fixture-v1",api_version:1,describe:foreign_domain,resolve:resolve_foreign}}
submit! {Registration{owner:"fixture-claim",revision:"fixture-v1",api_version:1,describe:ungranted_claim,resolve:resolve_claim}}
submit! {Registration{owner:"fixture-self-source",revision:"fixture-v1",api_version:1,describe:self_source,resolve:resolve_self}}
submit! {Registration{owner:"fixture-restriction",revision:"fixture-v1",api_version:1,describe:restriction,resolve:resolve_restriction}}
submit! {Registration{owner:"fixture-escape",revision:"fixture-v1",api_version:1,describe:escape,resolve:resolve_escape}}

/// Test setup chooses explicit separate repository grants; registration itself
/// neither emits policy to the product nor grants any capability.
pub fn configuration(owner: &str) -> Value {
    let description = match owner {
        "fixture-lens" => lens(),
        "fixture-notebook" => notebook(),
        "fixture-foreign-domain" => foreign_domain(),
        "fixture-claim" => ungranted_claim(),
        "fixture-self-source" => self_source(),
        "fixture-case-source" => case_source(),
        "fixture-dot-source" => dot_source(),
        "fixture-restriction" => restriction(),
        "fixture-escape" => escape(),
        _ => panic!("Unknown fixture"),
    };
    json!({"schema_version":1,"modules":{"enabled":[],"independent":{owner:{
        "revision":"fixture-v1","contract_revision":contract_revision(&description).unwrap(),
        "effects":description.capability["effects"].as_array().unwrap().iter().map(|e|e["id"].clone()).collect::<Vec<_>>(),
        "claims":[],"restrictions":[],"reads":description.sources,"scope":["fixture-input.txt"],"settings":{"label":"admitted fixture"}
    }}}})
}
