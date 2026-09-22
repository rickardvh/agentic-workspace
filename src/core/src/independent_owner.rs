//! Native owner extension boundary. Linked code supplies deterministic semantics;
//! repository admission supplies authority. Neither substitutes for the other.
//!
//! An owner receives bounded current values, not a target directory capability.
//! Core validates its contribution and publishes its prepared owned result.
//! This is an API boundary between admitted Rust implementations, not an OS
//! sandbox for malicious native code.
use serde_json::Value;

/// Shared prepared-operation carrier, not an executable schema or an ingress
/// escape hatch. Only the current responsible owner constructs these values.
pub fn operation_schema() -> Value {
    serde_json::json!({"$schema":"https://json-schema.org/draft/2020-12/schema","type":"object","additionalProperties":false,
        "required":["target","request","source_revision","value","publication"],
        "properties":{"target":{"type":"string"},"request":{"type":"object"},
            "source_revision":{"type":"string"},"value":{},"publication":{}}})
}

pub fn contract_revision(description: &Description) -> Result<String, crate::CoreError> {
    crate::digest(&serde_json::json!({"capability":description.capability,
        "configuration_schema":description.configuration_schema,"sources":description.sources}))
}

pub use inventory::submit;

/// Cheap linked identity. Detailed contracts are loaded only after selection.
pub struct Registration {
    pub owner: &'static str,
    pub revision: &'static str,
    pub api_version: u32,
    pub describe: fn() -> Description,
    pub resolve: fn(&Context) -> Result<Resolution, String>,
}

inventory::collect!(Registration);

/// Declarative contracts, interpreted by the existing capability compiler.
pub struct Description {
    /// One capability owner (domains, effects, operations and request schemas).
    pub capability: Value,
    /// Durable owner settings. No task answers, custody or continuation state.
    pub configuration_schema: Value,
    /// Exact relative source references needed by this owner, bounded by its
    /// separately admitted read grants. Absence is observed on every entry.
    pub sources: Vec<String>,
}

pub struct Context {
    pub current_work: Value,
    pub settings: Value,
    /// Current observed source values and revisions; no admitted foreign claims.
    pub sources: Value,
    pub request: Option<Value>,
}

/// An owner exposes argument templates against its declared request schemas.
pub struct RequestTemplate {
    pub kind: String,
    pub arguments: Value,
}

/// One deterministic operation prepared by the responsible Rust owner.
/// The exact current proposal is rederived before execution; public clients
/// cannot supply an operation or publication in place of an owner request.
pub struct PreparedOperation {
    pub operation_id: String,
    pub value: Value,
    /// Immutable, owner-namespaced material. Existing unowned destinations are
    /// preserved. Cross-owner material is returned as evidence instead.
    pub publication: Option<Publication>,
}

pub struct Publication {
    pub name: String,
    pub value: Value,
}

#[derive(Default)]
pub struct Resolution {
    pub facts: Value,
    pub blockers: Vec<Value>,
    pub requests: Vec<RequestTemplate>,
    pub operation: Option<PreparedOperation>,
}
