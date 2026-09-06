pub mod attempt;
pub mod attempt_store;
pub mod continuity;
pub mod decision_source;
pub mod planning;
use serde::{Deserialize, Serialize};
use serde_json::{Map, Value, json};
use sha2::{Digest, Sha256};
use std::collections::{BTreeMap, BTreeSet, HashSet};
use std::fmt::{Display, Formatter};

const CONTRIBUTION_KIND: &str = "agentic-workspace/source-contribution/v1";
const DECISION_KIND: &str = "agentic-workspace/operating-decision/v1";
const INVOCATION_KIND: &str = "agentic-workspace/operation-invocation/v1";
const CAPABILITY_CONTRACT_KIND: &str = "agentic-workspace/capability-contract/v1";
const PUBLIC_REQUEST_KIND: &str = "agentic-workspace/public-request/v1";
const TASK: &str = "task";
const CONSEQUENCE_PREFIXES: [&str; 5] = ["action:", "decision:", "effect:", "claim:", "outcome:"];

#[derive(Debug, Clone)]
pub struct CoreError(String);

impl CoreError {
    fn new(message: impl Into<String>) -> Self {
        Self(message.into())
    }
}

impl Display for CoreError {
    fn fmt(&self, formatter: &mut Formatter<'_>) -> std::fmt::Result {
        formatter.write_str(&self.0)
    }
}

impl std::error::Error for CoreError {}

#[derive(Debug, Deserialize)]
#[serde(deny_unknown_fields)]
struct DecisionInput {
    contributions: Vec<ContributionInput>,
    decision_context: Option<continuity::Context>,
    #[serde(default = "empty_object")]
    intent: Value,
    capability_contract: Option<CapabilityContractInput>,
}

#[derive(Debug, Deserialize)]
struct ContributionInput {
    #[serde(default)]
    owner: String,
    #[serde(default)]
    revision: String,
    #[serde(default = "default_true")]
    relevant: bool,
    #[serde(default)]
    settled: bool,
    #[serde(default = "empty_object")]
    facts: Value,
    #[serde(default)]
    blockers: Vec<BlockerInput>,
    #[serde(default)]
    decisions: Vec<BoundedDecisionInput>,
    #[serde(default)]
    actions: Vec<ActionInput>,
    #[serde(default)]
    claims: ClaimsInput,
    outcome: Option<OutcomeInput>,
    request_response: Option<RequestResponseInput>,
    #[serde(flatten)]
    extra: Map<String, Value>,
}

#[derive(Debug, Deserialize)]
#[serde(deny_unknown_fields)]
struct CapabilityContractInput {
    kind: String,
    revision: String,
    owners: Vec<CapabilityOwnerInput>,
    #[serde(default)]
    claim_authorities: Vec<ClaimAuthorityInput>,
    #[serde(default)]
    restriction_authorities: Vec<RestrictionAuthorityInput>,
}

#[derive(Debug, Deserialize)]
#[serde(deny_unknown_fields)]
struct RestrictionAuthorityInput {
    owner: String,
    affects: Vec<String>,
}

#[derive(Debug, Deserialize)]
#[serde(deny_unknown_fields)]
struct CapabilityOwnerInput {
    owner: String,
    revision: String,
    #[serde(default)]
    domains: Vec<String>,
    #[serde(default)]
    effects: Vec<EffectAuthorityInput>,
    #[serde(default)]
    operations: Vec<OperationCapabilityInput>,
    #[serde(default)]
    requests: Vec<RequestShapeInput>,
}

#[derive(Debug, Deserialize)]
#[serde(deny_unknown_fields)]
struct EffectAuthorityInput {
    id: String,
    domain: String,
}

#[derive(Debug, Deserialize)]
#[serde(deny_unknown_fields)]
struct ClaimAuthorityInput {
    claim: String,
    owner: String,
}

#[derive(Debug, Deserialize)]
#[serde(deny_unknown_fields)]
struct OperationCapabilityInput {
    id: String,
    semantic_revision: String,
    reads: Option<Vec<String>>,
    input_schema: Value,
    result_kind: String,
    #[serde(default)]
    effects: Vec<String>,
    #[serde(default)]
    claims: Vec<String>,
}

#[derive(Debug, Deserialize)]
#[serde(deny_unknown_fields)]
struct RequestShapeInput {
    kind: String,
    input_schema: Value,
    result_kind: String,
}

#[derive(Debug, Deserialize)]
#[serde(deny_unknown_fields)]
struct PublicRequestInput {
    kind: String,
    id: String,
    owner: String,
    owner_revision: String,
    source_revision: String,
    request_kind: String,
    capability_revision: String,
    task_identity: CurrentWorkIdentity,
    arguments: Value,
}

#[derive(Debug, Deserialize)]
#[serde(deny_unknown_fields)]
struct RequestResponseInput {
    request_identity: String,
    consequence_ids: Vec<String>,
    status: String,
}

#[derive(Debug, Deserialize)]
struct ActionInput {
    dependency_revision: String,
    #[serde(default)]
    effect_generation: String,
    #[serde(default)]
    operation_id: String,
    #[serde(default = "empty_object")]
    arguments: Value,
    #[serde(default)]
    effects: Vec<String>,
    authority: Option<String>,
    #[serde(flatten)]
    extra: Map<String, Value>,
}

#[derive(Debug, Deserialize)]
struct BlockerInput {
    #[serde(default)]
    code: String,
    #[serde(default)]
    message: String,
    owner: Option<String>,
    recovery: Option<String>,
    #[serde(default)]
    affects: Vec<String>,
}

#[derive(Debug, Deserialize)]
struct BoundedDecisionInput {
    #[serde(default)]
    id: String,
    #[serde(default)]
    question: String,
    response_request: AnswerRequestInput,
    #[serde(default)]
    choices: Vec<Choice>,
    #[serde(default)]
    affects: Vec<String>,
}

#[derive(Debug, Clone, Deserialize, Serialize)]
#[serde(deny_unknown_fields)]
struct AnswerRequestInput {
    request_kind: String,
    arguments: Value,
}

#[derive(Debug, Clone, Deserialize, Serialize)]
struct Choice {
    #[serde(default)]
    id: String,
    #[serde(default)]
    label: String,
}

#[derive(Debug, Default, Deserialize)]
struct ClaimsInput {
    #[serde(default)]
    allowed: Vec<String>,
    #[serde(default)]
    blocked: Vec<String>,
}

#[derive(Debug, Deserialize)]
struct OutcomeInput {
    #[serde(default)]
    required_claims: Vec<String>,
    #[serde(default)]
    id: String,
    #[serde(default)]
    status: String,
    #[serde(default)]
    claim: String,
    #[serde(default)]
    evidence_revision: String,
    #[serde(default)]
    residual_work: Vec<String>,
}

#[derive(Debug, Deserialize)]
struct IntendedOutcome {
    id: String,
    owner: String,
    claim: String,
}

#[derive(Debug, Clone, Deserialize, Serialize)]
#[serde(deny_unknown_fields)]
struct CurrentWorkIdentity {
    kind: String,
    id: String,
}

#[derive(Debug, Deserialize)]
#[serde(deny_unknown_fields)]
struct SemanticRouteSource {
    revision: String,
    routes: Vec<String>,
}

#[derive(Debug, Deserialize)]
#[serde(deny_unknown_fields)]
struct SemanticRouteSelection {
    posture: String,
    routes: Vec<String>,
    task_identity: CurrentWorkIdentity,
    source_revision: String,
    provenance: String,
    authority_effect: String,
}

#[derive(Debug, Clone, Serialize)]
struct NormalizedContribution {
    kind: &'static str,
    owner: String,
    revision: String,
    relevant: bool,
    settled: bool,
    facts: Value,
    blockers: Vec<NormalizedBlocker>,
    decisions: Vec<NormalizedDecision>,
    actions: Vec<NormalizedAction>,
    claims: NormalizedClaims,
    outcome: Option<NormalizedOutcome>,
    #[serde(skip_serializing_if = "Option::is_none")]
    request_response: Option<NormalizedRequestResponse>,
}

#[derive(Debug, Clone, Serialize)]
struct NormalizedCapabilityContract {
    kind: &'static str,
    revision: String,
    owners: BTreeMap<String, NormalizedCapabilityOwner>,
    claim_authorities: BTreeMap<String, String>,
    restriction_authorities: BTreeMap<String, BTreeSet<String>>,
}

#[derive(Debug, Clone, Serialize)]
struct NormalizedCapabilityOwner {
    revision: String,
    domains: BTreeSet<String>,
    effects: BTreeMap<String, String>,
    operations: BTreeMap<String, NormalizedOperationCapability>,
    requests: BTreeMap<String, NormalizedRequestShape>,
}

#[derive(Debug, Clone, Serialize)]
struct NormalizedOperationCapability {
    semantic_revision: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    reads: Option<BTreeSet<String>>,
    input_schema: Value,
    result_kind: String,
    effects: BTreeSet<String>,
    claims: BTreeSet<String>,
}

#[derive(Debug, Clone, Serialize)]
struct NormalizedRequestShape {
    input_schema: Value,
    result_kind: String,
}

#[derive(Debug, Clone, Serialize)]
struct NormalizedPublicRequest {
    kind: &'static str,
    id: String,
    identity: String,
    owner: String,
    owner_revision: String,
    source_revision: String,
    request_kind: String,
    result_kind: String,
    capability_revision: String,
    task_identity: CurrentWorkIdentity,
    arguments: Value,
}

#[derive(Debug, Clone, Serialize)]
struct NormalizedRequestResponse {
    request_identity: String,
    consequence_ids: Vec<String>,
    status: String,
}

#[derive(Debug, Clone, Serialize)]
struct NormalizedAction {
    consequence_id: String,
    dependency_revision: String,
    logical_effect_id: String,
    operation_revision: String,
    operation_id: String,
    arguments: Value,
    effects: Vec<String>,
    authority: String,
}

#[derive(Debug, Clone, Serialize)]
struct NormalizedBlocker {
    consequence_id: String,
    code: String,
    message: String,
    owner: String,
    revision: String,
    affects: Vec<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    recovery: Option<String>,
}

#[derive(Debug, Clone, Serialize)]
struct NormalizedDecision {
    consequence_id: String,
    id: String,
    owner: String,
    revision: String,
    question: String,
    response_request: Value,
    response_schema: Value,
    choices: Vec<Choice>,
    affects: Vec<String>,
}

#[derive(Debug, Clone, Serialize)]
struct NormalizedClaims {
    allowed: Vec<String>,
    blocked: Vec<String>,
}

#[derive(Debug, Clone, Serialize)]
struct NormalizedOutcome {
    required_claims: Vec<String>,
    id: String,
    status: String,
    claim: String,
    evidence_revision: String,
    residual_work: Vec<String>,
}

#[derive(Debug, Clone)]
struct OwnedAction {
    owner: String,
    action: NormalizedAction,
}

fn default_true() -> bool {
    true
}

fn empty_object() -> Value {
    Value::Object(Map::new())
}

fn require_text(value: &str, field: &str) -> Result<String, CoreError> {
    let normalized = value.trim();
    if normalized.is_empty() {
        Err(CoreError::new(format!("{field} is required")))
    } else {
        Ok(normalized.to_owned())
    }
}

fn strings(
    mut values: Vec<String>,
    field: &str,
    canonical_set: bool,
) -> Result<Vec<String>, CoreError> {
    if values.iter().any(|value| value.is_empty()) {
        return Err(CoreError::new(format!(
            "{field} must contain non-empty strings"
        )));
    }
    if canonical_set {
        values.sort();
        values.dedup();
    }
    Ok(values)
}

fn unique_strings(values: Vec<String>, field: &str) -> Result<Vec<String>, CoreError> {
    let original_len = values.len();
    let values = strings(values, field, true)?;
    if values.len() != original_len {
        return Err(CoreError::new(format!(
            "{field} must not contain duplicate values"
        )));
    }
    Ok(values)
}

fn affects(values: Vec<String>, field: &str) -> Result<Vec<String>, CoreError> {
    let values = strings(values, field, true)?;
    if values.is_empty() {
        return Err(CoreError::new(format!(
            "{field} must name at least one affected consequence"
        )));
    }
    if values.iter().any(|value| {
        value != TASK
            && !CONSEQUENCE_PREFIXES
                .iter()
                .any(|prefix| value.starts_with(prefix) && value.len() > prefix.len())
    }) {
        return Err(CoreError::new(format!(
            "{field} contains an unsupported consequence identity"
        )));
    }
    Ok(values)
}

fn digest(value: &impl Serialize) -> Result<String, CoreError> {
    let encoded = serde_json::to_vec(value).map_err(|error| CoreError::new(error.to_string()))?;
    let bytes = Sha256::digest(encoded);
    Ok(format!("sha256:{bytes:x}"))
}

fn normalize_capability_contract(
    input: CapabilityContractInput,
) -> Result<NormalizedCapabilityContract, CoreError> {
    if input.kind != CAPABILITY_CONTRACT_KIND {
        return Err(CoreError::new(format!(
            "capability_contract.kind must be {CAPABILITY_CONTRACT_KIND}"
        )));
    }
    let revision = require_text(&input.revision, "capability_contract.revision")?;
    if !sha256_revision(&revision) {
        return Err(CoreError::new(
            "capability_contract.revision must be a lowercase sha256 revision",
        ));
    }

    let mut owners = BTreeMap::new();
    let mut owned_domains = BTreeMap::<String, String>::new();
    let mut owned_effects = BTreeMap::<String, String>::new();
    let mut operation_owners = BTreeMap::<String, String>::new();
    let mut request_kinds = BTreeMap::<String, String>::new();
    for (owner_index, input_owner) in input.owners.into_iter().enumerate() {
        let owner = require_text(
            &input_owner.owner,
            &format!("capability_contract.owners[{owner_index}].owner"),
        )?;
        if owners.contains_key(&owner) {
            return Err(CoreError::new(format!(
                "capability owner {owner} is declared more than once"
            )));
        }
        let owner_revision = require_text(
            &input_owner.revision,
            &format!("capability_contract.owners[{owner_index}].revision"),
        )?;
        let domains = unique_strings(
            input_owner.domains,
            &format!("capability_contract owner {owner}.domains"),
        )?
        .into_iter()
        .collect::<BTreeSet<_>>();
        for domain in &domains {
            if let Some(existing) = owned_domains.insert(domain.clone(), owner.clone()) {
                return Err(CoreError::new(format!(
                    "domain {domain} has conflicting owners {existing} and {owner}"
                )));
            }
        }

        let mut effects = BTreeMap::new();
        for (effect_index, effect) in input_owner.effects.into_iter().enumerate() {
            let id = require_text(
                &effect.id,
                &format!("capability_contract owner {owner}.effects[{effect_index}].id"),
            )?;
            let domain = require_text(
                &effect.domain,
                &format!("capability_contract owner {owner}.effects[{effect_index}].domain"),
            )?;
            if !domains.contains(&domain) {
                return Err(CoreError::new(format!(
                    "effect {id} names domain {domain}, which is not owned by {owner}"
                )));
            }
            if effects.insert(id.clone(), domain).is_some() {
                return Err(CoreError::new(format!(
                    "effect {id} is declared more than once by {owner}"
                )));
            }
            if let Some(existing) = owned_effects.insert(id.clone(), owner.clone()) {
                return Err(CoreError::new(format!(
                    "effect {id} has conflicting owners {existing} and {owner}"
                )));
            }
        }

        let mut operations = BTreeMap::new();
        for (operation_index, operation) in input_owner.operations.into_iter().enumerate() {
            let id = require_text(
                &operation.id,
                &format!("capability_contract owner {owner}.operations[{operation_index}].id"),
            )?;
            if let Some(existing) = operation_owners.insert(id.clone(), owner.clone()) {
                return Err(CoreError::new(format!(
                    "operation {id} has conflicting owners {existing} and {owner}"
                )));
            }
            schema_validator(&operation.input_schema, &format!("operation {id}"))?;
            let operation_effects = unique_strings(
                operation.effects,
                &format!("capability_contract operation {id}.effects"),
            )?
            .into_iter()
            .collect::<BTreeSet<_>>();
            if let Some(effect) = operation_effects
                .iter()
                .find(|effect| !effects.contains_key(*effect))
            {
                return Err(CoreError::new(format!(
                    "operation {id} advertises effect {effect} outside owner {owner}"
                )));
            }
            let claims = unique_strings(
                operation.claims,
                &format!("capability_contract operation {id}.claims"),
            )?
            .into_iter()
            .collect::<BTreeSet<_>>();
            operations.insert(
                id,
                NormalizedOperationCapability {
                    semantic_revision: require_text(
                        &operation.semantic_revision,
                        "operation.semantic_revision",
                    )?,
                    reads: operation
                        .reads
                        .map(|reads| {
                            unique_strings(reads, "operation.reads")
                                .map(|reads| reads.into_iter().collect())
                        })
                        .transpose()?,
                    input_schema: operation.input_schema,
                    result_kind: require_text(
                        &operation.result_kind,
                        "capability_contract operation result_kind",
                    )?,
                    effects: operation_effects,
                    claims,
                },
            );
        }
        let mut requests = BTreeMap::new();
        for request in input_owner.requests {
            let kind = require_text(&request.kind, "capability request.kind")?;
            if let Some(existing) = request_kinds.insert(kind.clone(), owner.clone()) {
                return Err(CoreError::new(format!(
                    "public request kind {kind} has conflicting declarations by {existing} and {owner}"
                )));
            }
            schema_validator(&request.input_schema, &format!("request {kind}"))?;
            requests.insert(
                kind,
                NormalizedRequestShape {
                    input_schema: request.input_schema,
                    result_kind: require_text(
                        &request.result_kind,
                        "capability request.result_kind",
                    )?,
                },
            );
        }
        owners.insert(
            owner,
            NormalizedCapabilityOwner {
                revision: owner_revision,
                domains,
                effects,
                operations,
                requests,
            },
        );
    }
    if owners.is_empty() {
        return Err(CoreError::new(
            "capability_contract must declare at least one owner",
        ));
    }

    let mut claim_authorities = BTreeMap::new();
    for (index, authority) in input.claim_authorities.into_iter().enumerate() {
        let claim = require_text(
            &authority.claim,
            &format!("capability_contract.claim_authorities[{index}].claim"),
        )?;
        let owner = require_text(
            &authority.owner,
            &format!("capability_contract.claim_authorities[{index}].owner"),
        )?;
        if !owners.contains_key(&owner) {
            return Err(CoreError::new(format!(
                "claim {claim} names unknown authority owner {owner}"
            )));
        }
        if let Some(existing) = claim_authorities.insert(claim.clone(), owner.clone()) {
            return Err(CoreError::new(format!(
                "claim {claim} has conflicting authorities {existing} and {owner}"
            )));
        }
    }
    for (owner, capability) in &owners {
        for (operation_id, operation) in &capability.operations {
            if let Some(reads) = &operation.reads {
                for domain in reads {
                    if !owned_domains.contains_key(domain) {
                        return Err(CoreError::new(format!(
                            "operation {operation_id} reads unknown domain {domain}"
                        )));
                    }
                }
            }
            if let Some(claim) = operation
                .claims
                .iter()
                .find(|claim| claim_authorities.get(*claim) != Some(owner))
            {
                return Err(CoreError::new(format!(
                    "operation {operation_id} advertises claim {claim} without authority owned by {owner}"
                )));
            }
        }
    }

    let mut restriction_authorities = BTreeMap::new();
    for grant in input.restriction_authorities {
        let owner = require_text(&grant.owner, "restriction authority.owner")?;
        if !owners.contains_key(&owner) {
            return Err(CoreError::new(format!(
                "restriction authority names unknown owner {owner}"
            )));
        }
        let scopes = affects(grant.affects, "restriction authority.affects")?;
        for scope in &scopes {
            if let Some(claim) = scope.strip_prefix("claim:")
                && !claim_authorities.contains_key(claim)
            {
                return Err(CoreError::new(format!(
                    "restriction authority names unknown claim {claim}"
                )));
            }
            if let Some(effect) = scope.strip_prefix("effect:")
                && !owned_effects.contains_key(effect)
            {
                return Err(CoreError::new(format!(
                    "restriction authority names unknown effect {effect}"
                )));
            }
        }
        if restriction_authorities
            .insert(owner.clone(), scopes.into_iter().collect())
            .is_some()
        {
            return Err(CoreError::new(format!(
                "restriction authority for {owner} is declared more than once"
            )));
        }
    }

    Ok(NormalizedCapabilityContract {
        kind: CAPABILITY_CONTRACT_KIND,
        revision,
        owners,
        claim_authorities,
        restriction_authorities,
    })
}

fn normalize_contribution(
    input: ContributionInput,
    capabilities: Option<&NormalizedCapabilityContract>,
    intent: &Value,
) -> Result<NormalizedContribution, CoreError> {
    let owner = require_text(&input.owner, "contribution.owner")?;
    let revision = require_text(&input.revision, &format!("{owner}.revision"))?;
    if input.extra.contains_key("terminal") {
        return Err(CoreError::new(format!(
            "{owner}.terminal is obsolete; use settled plus explicit outcome authority"
        )));
    }
    if !input.facts.is_object() {
        return Err(CoreError::new(format!("{owner}.facts must be an object")));
    }

    let authority_bearing = !input.blockers.is_empty()
        || !input.decisions.is_empty()
        || !input.actions.is_empty()
        || !input.claims.allowed.is_empty()
        || !input.claims.blocked.is_empty()
        || input.outcome.is_some()
        || input.request_response.is_some();
    let capability = capabilities.and_then(|contract| contract.owners.get(&owner));
    if authority_bearing && capability.is_none() {
        return Err(CoreError::new(format!(
            "authority-bearing contribution {owner} requires a current capability owner declaration"
        )));
    }

    let mut actions = input
        .actions
        .into_iter()
        .enumerate()
        .map(|(index, action)| normalize_action(action, &owner, capability, index))
        .collect::<Result<Vec<_>, _>>()?;
    actions.sort_by(|left, right| left.consequence_id.cmp(&right.consequence_id));
    if let Some(capability) = capability {
        for action in &actions {
            let operation = capability
                .operations
                .get(&action.operation_id)
                .ok_or_else(|| {
                    CoreError::new(format!(
                        "{owner} action {} is not declared by its capability owner",
                        action.operation_id
                    ))
                })?;
            if action.authority != owner {
                return Err(CoreError::new(format!(
                    "{owner} action {} cannot claim authority {}",
                    action.operation_id, action.authority
                )));
            }
            validate_operation_arguments(
                &action.arguments,
                &operation.input_schema,
                &format!("{owner} action {}", action.operation_id),
            )?;
            if let Some(effect) = action
                .effects
                .iter()
                .find(|effect| !operation.effects.contains(*effect))
            {
                return Err(CoreError::new(format!(
                    "{owner} action {} advertises undeclared effect {effect}",
                    action.operation_id
                )));
            }
        }
    }

    let mut blockers = input
        .blockers
        .into_iter()
        .enumerate()
        .map(|(index, blocker)| normalize_blocker(blocker, &owner, &revision, index))
        .collect::<Result<Vec<_>, _>>()?;
    blockers.sort_by(|left, right| left.consequence_id.cmp(&right.consequence_id));

    let mut decisions = input
        .decisions
        .into_iter()
        .enumerate()
        .map(|(index, decision)| {
            normalize_decision(decision, &owner, &revision, index, capabilities, intent)
        })
        .collect::<Result<Vec<_>, _>>()?;
    decisions.sort_by(|left, right| left.consequence_id.cmp(&right.consequence_id));

    let blocked = strings(
        input.claims.blocked,
        &format!("{owner}.claims.blocked"),
        true,
    )?;
    let blocked_set = blocked.iter().cloned().collect::<HashSet<_>>();
    let allowed = strings(
        input.claims.allowed,
        &format!("{owner}.claims.allowed"),
        true,
    )?;
    if let Some(contract) = capabilities {
        for claim in &blocked {
            if !contract.claim_authorities.contains_key(claim) {
                return Err(CoreError::new(format!(
                    "{owner} blocks unknown claim {claim}"
                )));
            }
        }
        for claim in &allowed {
            if contract.claim_authorities.get(claim) != Some(&owner) {
                return Err(CoreError::new(format!(
                    "{owner} allows claim {claim} without exclusive claim authority"
                )));
            }
        }
        // Every restriction is admitted independently of allow/effect authority.
        // `task` is an exact scope, never a wildcard granting other vetoes.
        for scope in blockers
            .iter()
            .flat_map(|item| item.affects.iter().cloned())
            .chain(
                decisions
                    .iter()
                    .flat_map(|item| item.affects.iter().cloned()),
            )
            .chain(blocked.iter().map(|claim| format!("claim:{claim}")))
        {
            if !contract
                .restriction_authorities
                .get(&owner)
                .is_some_and(|scopes| scopes.contains(&scope))
            {
                return Err(CoreError::new(format!(
                    "{owner} restricts {scope} without admitted restriction authority"
                )));
            }
        }
    }
    let allowed = allowed
        .into_iter()
        .filter(|claim| !blocked_set.contains(claim))
        .collect();
    let outcome = input
        .outcome
        .map(|value| normalize_outcome(value, &owner))
        .transpose()?;
    if let (Some(contract), Some(outcome)) = (capabilities, outcome.as_ref())
        && contract.claim_authorities.get(&outcome.claim) != Some(&owner)
    {
        return Err(CoreError::new(format!(
            "{owner} outcome grants claim {} without exclusive claim authority",
            outcome.claim
        )));
    }
    if let (Some(contract), Some(outcome)) = (capabilities, outcome.as_ref()) {
        for claim in &outcome.required_claims {
            if !contract.claim_authorities.contains_key(claim) {
                return Err(CoreError::new(format!(
                    "{owner} outcome requires unknown claim {claim}"
                )));
            }
        }
    }
    let request_response = input
        .request_response
        .map(|response| normalize_request_response(response, &owner))
        .transpose()?;

    Ok(NormalizedContribution {
        kind: CONTRIBUTION_KIND,
        owner,
        revision,
        relevant: input.relevant,
        settled: input.settled,
        facts: input.facts,
        blockers,
        decisions,
        actions,
        claims: NormalizedClaims { allowed, blocked },
        outcome,
        request_response,
    })
}

fn normalize_request_response(
    input: RequestResponseInput,
    owner: &str,
) -> Result<NormalizedRequestResponse, CoreError> {
    let request_identity = require_text(
        &input.request_identity,
        &format!("{owner}.request_response.request_identity"),
    )?;
    let consequence_ids =
        unique_strings(input.consequence_ids, "request_response.consequence_ids")?;
    if !matches!(
        input.status.as_str(),
        "action" | "decision" | "blocked" | "settled"
    ) {
        return Err(CoreError::new(format!(
            "{owner}.request_response.status must be action, decision, blocked, or settled"
        )));
    }
    Ok(NormalizedRequestResponse {
        request_identity,
        consequence_ids,
        status: input.status,
    })
}

fn operation_revision(
    owner: &str,
    id: &str,
    capability: &NormalizedCapabilityOwner,
) -> Result<String, CoreError> {
    let operation = capability
        .operations
        .get(id)
        .ok_or_else(|| CoreError::new("operation is not declared by its capability owner"))?;
    digest(&json!({"owner": owner, "id": id, "operation": operation,
        "custody": operation.effects.iter().map(|effect| (effect, capability.effects.get(effect))).collect::<BTreeMap<_, _>>()}))
}

fn normalize_action(
    input: ActionInput,
    owner: &str,
    capability: Option<&NormalizedCapabilityOwner>,
    index: usize,
) -> Result<NormalizedAction, CoreError> {
    if input.extra.contains_key("priority") {
        return Err(CoreError::new(format!(
            "{owner}.actions[{index}].priority is obsolete; authority cannot be self-ranked"
        )));
    }
    let operation_id = require_text(
        &input.operation_id,
        &format!("{owner}.actions[{index}].operation_id"),
    )?;
    if !input.arguments.is_object() {
        return Err(CoreError::new(format!(
            "{owner}.actions[{index}].arguments must be an object"
        )));
    }
    let effects = strings(
        input.effects,
        &format!("{owner}.actions[{index}].effects"),
        false,
    )?;
    let authority = input
        .authority
        .filter(|value| !value.is_empty())
        .unwrap_or_else(|| owner.to_owned());
    let dependency_revision =
        require_text(&input.dependency_revision, "action.dependency_revision")?;
    let identity = json!({
        "owner": owner,
        "effect_generation": input.effect_generation,
        "operation_id": operation_id,
        "arguments": input.arguments,
        "effects": effects,
        "authority": authority,
    });
    let logical_effect_id = digest(&identity)?;
    // The operation contract and its effect custody are material; unrelated
    // owner descriptors and aggregate contract revisions are not dependencies.
    let dependency_revision = digest(&json!({
        "source_dependencies": dependency_revision,
        "operation": capability.and_then(|item| item.operations.get(&operation_id)),
        "effect_custody": effects.iter().map(|effect| (effect, capability.and_then(|item| item.effects.get(effect)))).collect::<BTreeMap<_, _>>(),
    }))?;
    let consequence_id = format!(
        "action:{owner}:{}",
        digest(
            &json!({"logical_effect_id": logical_effect_id, "dependency_revision": dependency_revision})
        )?
    );
    Ok(NormalizedAction {
        consequence_id,
        dependency_revision,
        logical_effect_id,
        operation_revision: operation_revision(
            owner,
            &operation_id,
            capability.ok_or_else(|| CoreError::new("operation requires admitted owner"))?,
        )?,
        operation_id: identity["operation_id"]
            .as_str()
            .expect("identity operation is text")
            .to_owned(),
        arguments: identity["arguments"].clone(),
        effects: serde_json::from_value(identity["effects"].clone())
            .expect("identity effects are strings"),
        authority: identity["authority"]
            .as_str()
            .expect("identity authority is text")
            .to_owned(),
    })
}

fn normalize_blocker(
    input: BlockerInput,
    owner: &str,
    revision: &str,
    index: usize,
) -> Result<NormalizedBlocker, CoreError> {
    let code = require_text(&input.code, &format!("{owner}.blockers[{index}].code"))?;
    let message = require_text(
        &input.message,
        &format!("{owner}.blockers[{index}].message"),
    )?;
    let blocker_owner = input
        .owner
        .filter(|value| !value.is_empty())
        .unwrap_or_else(|| owner.to_owned());
    if blocker_owner != owner {
        return Err(CoreError::new(format!(
            "{owner} blocker cannot claim owner {blocker_owner}"
        )));
    }
    let affected = affects(input.affects, &format!("{owner}.blockers[{index}].affects"))?;
    let identity = json!({"code": code, "message": message, "owner": blocker_owner, "revision": revision, "affects": affected, "recovery": input.recovery});
    Ok(NormalizedBlocker {
        consequence_id: format!("blocker:{owner}:{revision}:{}", digest(&identity)?),
        code: identity["code"].as_str().expect("code is text").to_owned(),
        message: identity["message"]
            .as_str()
            .expect("message is text")
            .to_owned(),
        owner: identity["owner"]
            .as_str()
            .expect("owner is text")
            .to_owned(),
        revision: revision.to_owned(),
        affects: serde_json::from_value(identity["affects"].clone()).expect("affects are strings"),
        recovery: input.recovery.filter(|value| !value.is_empty()),
    })
}

fn normalize_decision(
    input: BoundedDecisionInput,
    owner: &str,
    revision: &str,
    index: usize,
    capabilities: Option<&NormalizedCapabilityContract>,
    intent: &Value,
) -> Result<NormalizedDecision, CoreError> {
    let id = require_text(&input.id, &format!("{owner}.decisions[{index}].id"))?;
    let question = require_text(
        &input.question,
        &format!("{owner}.decisions[{index}].question"),
    )?;
    let contract = capabilities
        .ok_or_else(|| CoreError::new("bounded answer requires admitted capabilities"))?;
    let capability = contract
        .owners
        .get(owner)
        .ok_or_else(|| CoreError::new("bounded answer owner is not admitted"))?;
    let shape = capability
        .requests
        .get(&input.response_request.request_kind)
        .ok_or_else(|| CoreError::new("bounded answer names undeclared response request"))?;
    let current = current_work(intent)?
        .ok_or_else(|| CoreError::new("bounded answer requires current_work"))?;
    let fixed = input
        .response_request
        .arguments
        .as_object()
        .ok_or_else(|| CoreError::new("response request arguments must be an object"))?;
    if fixed.contains_key("answer") {
        return Err(CoreError::new(
            "response request cannot prefill the human answer",
        ));
    }
    for choice in &input.choices {
        let mut arguments = fixed.clone();
        arguments.insert("answer".to_owned(), Value::String(choice.id.clone()));
        validate_operation_arguments(
            &Value::Object(arguments),
            &shape.input_schema,
            "bounded answer choice",
        )?;
    }
    let choices = input
        .choices
        .into_iter()
        .enumerate()
        .map(|(choice_index, choice)| {
            Ok(Choice {
                id: require_text(
                    &choice.id,
                    &format!("{owner}.decisions[{index}].choices[{choice_index}].id"),
                )?,
                label: require_text(
                    &choice.label,
                    &format!("{owner}.decisions[{index}].choices[{choice_index}].label"),
                )?,
            })
        })
        .collect::<Result<Vec<_>, CoreError>>()?;
    let affected = affects(
        input.affects,
        &format!("{owner}.decisions[{index}].affects"),
    )?;
    let identity = json!({
        "id": id, "owner": owner, "revision": revision, "question": question,
        "response_request": input.response_request, "response_schema": shape.input_schema, "current_work": current, "capability_revision": contract.revision, "choices": choices, "affects": affected,
    });
    let consequence_id = format!("decision:{owner}:{revision}:{}", digest(&identity)?);
    let response_request = json!({"kind": PUBLIC_REQUEST_KIND, "id": format!("answer:{consequence_id}"),
        "owner": owner, "owner_revision": capability.revision, "source_revision": revision,
        "request_kind": input.response_request.request_kind, "capability_revision": contract.revision,
        "task_identity": current, "arguments": input.response_request.arguments});
    Ok(NormalizedDecision {
        consequence_id,
        response_request,
        response_schema: shape.input_schema.clone(),
        id: identity["id"].as_str().expect("id is text").to_owned(),
        owner: owner.to_owned(),
        revision: revision.to_owned(),
        question: identity["question"]
            .as_str()
            .expect("question is text")
            .to_owned(),
        choices: serde_json::from_value(identity["choices"].clone()).expect("choices are valid"),
        affects: serde_json::from_value(identity["affects"].clone()).expect("affects are strings"),
    })
}

fn normalize_outcome(input: OutcomeInput, owner: &str) -> Result<NormalizedOutcome, CoreError> {
    Ok(NormalizedOutcome {
        required_claims: unique_strings(input.required_claims, "outcome.required_claims")?,
        id: require_text(&input.id, &format!("{owner}.outcome.id"))?,
        status: require_text(&input.status, &format!("{owner}.outcome.status"))?,
        claim: require_text(&input.claim, &format!("{owner}.outcome.claim"))?,
        evidence_revision: require_text(
            &input.evidence_revision,
            &format!("{owner}.outcome.evidence_revision"),
        )?,
        residual_work: strings(
            input.residual_work,
            &format!("{owner}.outcome.residual_work"),
            false,
        )?,
    })
}

fn intended_outcome(intent: &Value) -> Result<Option<IntendedOutcome>, CoreError> {
    let Some(value) = intent.get("outcome") else {
        return Ok(None);
    };
    if !value.is_object() {
        return Err(CoreError::new("intent.outcome must be an object"));
    }
    let parsed: IntendedOutcome = serde_json::from_value(value.clone())
        .map_err(|_| CoreError::new("intent.outcome requires id, owner, and claim"))?;
    Ok(Some(IntendedOutcome {
        id: require_text(&parsed.id, "intent.outcome.id")?,
        owner: require_text(&parsed.owner, "intent.outcome.owner")?,
        claim: require_text(&parsed.claim, "intent.outcome.claim")?,
    }))
}

fn semantic_route_id(value: &str) -> bool {
    let segments = value.split('/').collect::<Vec<_>>();
    segments.len() >= 2
        && segments.iter().all(|segment| {
            !segment.is_empty()
                && segment.chars().next().is_some_and(|character| {
                    character.is_ascii_lowercase() || character.is_ascii_digit()
                })
                && segment.chars().all(|character| {
                    character.is_ascii_lowercase() || character.is_ascii_digit() || character == '-'
                })
        })
}

fn sha256_revision(value: &str) -> bool {
    value.len() == 71
        && value.starts_with("sha256:")
        && value[7..]
            .chars()
            .all(|character| character.is_ascii_hexdigit() && !character.is_ascii_uppercase())
}

fn route_ids(mut values: Vec<String>, field: &str) -> Result<Vec<String>, CoreError> {
    if values.iter().any(|value| !semantic_route_id(value)) {
        return Err(CoreError::new(format!(
            "{field} contains an invalid semantic route identity"
        )));
    }
    let original_len = values.len();
    values.sort();
    values.dedup();
    if values.len() != original_len {
        return Err(CoreError::new(format!(
            "{field} must not contain duplicate routes"
        )));
    }
    Ok(values)
}

fn normalize_semantic_routes(intent: &mut Value) -> Result<Option<Value>, CoreError> {
    let object = intent
        .as_object_mut()
        .expect("intent was checked as an object");
    let current = object.get("current_work");
    let source = object.get("semantic_route_source");
    let selection = object.get("semantic_task_routes");
    if source.is_none() && selection.is_none() {
        return Ok(None);
    }
    if current.is_none() || source.is_none() || selection.is_none() {
        return Err(CoreError::new(
            "current_work, semantic_route_source, and semantic_task_routes must be supplied together",
        ));
    }
    let mut current: CurrentWorkIdentity =
        serde_json::from_value(current.expect("present").clone())
            .map_err(|error| CoreError::new(format!("intent.current_work is invalid: {error}")))?;
    current.kind = require_text(&current.kind, "intent.current_work.kind")?;
    current.id = require_text(&current.id, "intent.current_work.id")?;
    if current.kind != "current-work" {
        return Err(CoreError::new(
            "intent.current_work.kind must be current-work",
        ));
    }

    let mut source: SemanticRouteSource = serde_json::from_value(source.expect("present").clone())
        .map_err(|error| {
            CoreError::new(format!("intent.semantic_route_source is invalid: {error}"))
        })?;
    source.revision = require_text(&source.revision, "intent.semantic_route_source.revision")?;
    if !sha256_revision(&source.revision) {
        return Err(CoreError::new(
            "intent.semantic_route_source.revision must be a lowercase sha256 revision",
        ));
    }
    source.routes = route_ids(source.routes, "intent.semantic_route_source.routes")?;

    let mut selection: SemanticRouteSelection =
        serde_json::from_value(selection.expect("present").clone()).map_err(|error| {
            CoreError::new(format!("intent.semantic_task_routes is invalid: {error}"))
        })?;
    selection.routes = route_ids(selection.routes, "intent.semantic_task_routes.routes")?;
    if !matches!(
        selection.posture.as_str(),
        "selected" | "none" | "unresolved"
    ) {
        return Err(CoreError::new(
            "intent.semantic_task_routes.posture must be selected, none, or unresolved",
        ));
    }
    if (selection.posture == "selected") != !selection.routes.is_empty() {
        return Err(CoreError::new(
            "selected semantic-route posture requires routes; none and unresolved require no routes",
        ));
    }
    if selection.task_identity.kind != current.kind || selection.task_identity.id != current.id {
        return Err(CoreError::new(
            "semantic route selection is stale for the current task identity",
        ));
    }
    if selection.source_revision != source.revision {
        return Err(CoreError::new(
            "semantic route selection is stale for the current route-source revision",
        ));
    }
    let known = source.routes.iter().collect::<HashSet<_>>();
    if selection.routes.iter().any(|route| !known.contains(route)) {
        return Err(CoreError::new(
            "semantic route selection contains a route absent from the current source",
        ));
    }
    if selection.provenance != "agent-selected"
        || selection.authority_effect != "applicability-only"
    {
        return Err(CoreError::new(
            "semantic routes must be agent-selected and applicability-only",
        ));
    }

    let normalized = json!({
        "posture": selection.posture,
        "routes": selection.routes,
        "task_identity": current,
        "source_revision": source.revision,
        "provenance": "agent-selected",
        "authority_effect": "applicability-only",
    });
    object.insert(
        "current_work".to_owned(),
        normalized["task_identity"].clone(),
    );
    object.insert(
        "semantic_route_source".to_owned(),
        json!({"revision": normalized["source_revision"], "routes": source.routes}),
    );
    object.insert("semantic_task_routes".to_owned(), normalized.clone());
    Ok(Some(normalized))
}

fn current_work(intent: &Value) -> Result<Option<CurrentWorkIdentity>, CoreError> {
    let Some(value) = intent.get("current_work") else {
        return Ok(None);
    };
    let mut current: CurrentWorkIdentity = serde_json::from_value(value.clone())
        .map_err(|error| CoreError::new(format!("intent.current_work is invalid: {error}")))?;
    current.kind = require_text(&current.kind, "intent.current_work.kind")?;
    current.id = require_text(&current.id, "intent.current_work.id")?;
    if current.kind != "current-work" {
        return Err(CoreError::new(
            "intent.current_work.kind must be current-work",
        ));
    }
    Ok(Some(current))
}

fn schema_validator(schema: &Value, field: &str) -> Result<jsonschema::Validator, CoreError> {
    if schema.get("$schema").and_then(Value::as_str)
        != Some("https://json-schema.org/draft/2020-12/schema")
    {
        return Err(CoreError::new(format!(
            "{field}.input_schema must declare JSON Schema Draft 2020-12"
        )));
    }
    // Schemas are carried in the current capability contract. External HTTP/file
    // retrieval is disabled; local $defs/$ref remain ordinary JSON Schema.
    jsonschema::draft202012::options()
        .build(schema)
        .map_err(|error| CoreError::new(format!("{field}.input_schema is invalid: {error}")))
}

fn validate_operation_arguments(
    value: &Value,
    schema: &Value,
    field: &str,
) -> Result<(), CoreError> {
    if !value.is_object() {
        return Err(CoreError::new(format!(
            "{field}.arguments must be an object"
        )));
    }
    schema_validator(schema, field)?
        .validate(value)
        .map_err(|error| CoreError::new(format!("{field}.arguments violate input_schema: {error}")))
}

fn normalize_public_request(
    intent: &mut Value,
    capabilities: Option<&NormalizedCapabilityContract>,
) -> Result<Option<NormalizedPublicRequest>, CoreError> {
    let Some(value) = intent.get("public_request") else {
        return Ok(None);
    };
    let capabilities = capabilities.ok_or_else(|| {
        CoreError::new("intent.public_request requires a current capability_contract")
    })?;
    let parsed: PublicRequestInput = serde_json::from_value(value.clone())
        .map_err(|error| CoreError::new(format!("intent.public_request is invalid: {error}")))?;
    if parsed.kind != PUBLIC_REQUEST_KIND {
        return Err(CoreError::new(format!(
            "intent.public_request.kind must be {PUBLIC_REQUEST_KIND}"
        )));
    }
    let id = require_text(&parsed.id, "intent.public_request.id")?;
    let owner = require_text(&parsed.owner, "intent.public_request.owner")?;
    let owner_revision = require_text(
        &parsed.owner_revision,
        "intent.public_request.owner_revision",
    )?;
    let source_revision = require_text(
        &parsed.source_revision,
        "intent.public_request.source_revision",
    )?;
    let request_kind = require_text(&parsed.request_kind, "intent.public_request.request_kind")?;
    if parsed.capability_revision != capabilities.revision {
        return Err(CoreError::new(
            "public request is stale for the current capability contract revision",
        ));
    }
    let current = current_work(intent)?
        .ok_or_else(|| CoreError::new("intent.public_request requires intent.current_work"))?;
    if parsed.task_identity.kind != current.kind || parsed.task_identity.id != current.id {
        return Err(CoreError::new(
            "public request is stale for the current task identity",
        ));
    }
    let owner_capability = capabilities.owners.get(&owner).ok_or_else(|| {
        CoreError::new(format!(
            "public request names unknown capability owner {owner}"
        ))
    })?;
    if owner_revision != owner_capability.revision {
        return Err(CoreError::new(format!(
            "public request is stale for capability owner {owner}"
        )));
    }
    let request_shape = owner_capability
        .requests
        .get(&request_kind)
        .ok_or_else(|| {
            CoreError::new(format!(
                "public request names undeclared request kind {request_kind} for {owner}"
            ))
        })?;
    validate_operation_arguments(
        &parsed.arguments,
        &request_shape.input_schema,
        &format!("public request {request_kind}"),
    )?;
    let identity = digest(&json!({
        "id": id,
        "owner": owner,
        "owner_revision": owner_revision,
        "source_revision": source_revision,
        "request_kind": request_kind,
        "request_contract": request_shape,
        "capability_revision": capabilities.revision,
        "task_identity": current,
        "arguments": parsed.arguments,
    }))?;
    let normalized = NormalizedPublicRequest {
        kind: PUBLIC_REQUEST_KIND,
        id,
        identity: format!("request:{identity}"),
        owner,
        owner_revision,
        source_revision,
        request_kind,
        result_kind: request_shape.result_kind.clone(),
        capability_revision: capabilities.revision.clone(),
        task_identity: current,
        arguments: parsed.arguments,
    };
    intent.as_object_mut().expect("intent is an object").insert(
        "public_request".to_owned(),
        serde_json::to_value(&normalized).expect("normalized public request serializes"),
    );
    Ok(Some(normalized))
}

/// Prepare public identity once in Rust before the responsible owner resolves it.
pub fn prepare_request_value(value: Value) -> Result<Value, CoreError> {
    #[derive(Deserialize)]
    #[serde(deny_unknown_fields)]
    struct Prepare {
        request: Value,
        current_work: Value,
        capability_contract: CapabilityContractInput,
    }
    let input: Prepare =
        serde_json::from_value(value).map_err(|error| CoreError::new(error.to_string()))?;
    let contract = normalize_capability_contract(input.capability_contract)?;
    let mut intent = json!({"public_request": input.request, "current_work": input.current_work});
    let normalized =
        normalize_public_request(&mut intent, Some(&contract))?.expect("request is present");
    let mut request = serde_json::to_value(&normalized).expect("request serializes");
    request.as_object_mut().unwrap().remove("identity");
    request.as_object_mut().unwrap().remove("result_kind");
    Ok(
        json!({"request": request, "identity": normalized.identity, "result_kind": normalized.result_kind}),
    )
}

/// Bind only the human/domain-owned answer into the current owner's request.
pub fn answer_decision_value(value: Value) -> Result<Value, CoreError> {
    #[derive(Deserialize)]
    #[serde(deny_unknown_fields)]
    struct Answer {
        decision: Value,
        question: String,
        answer: Value,
        capability_contract: Value,
    }
    let input: Answer =
        serde_json::from_value(value).map_err(|error| CoreError::new(error.to_string()))?;
    let question = input.decision["pending_consequences"]["decisions"]
        .as_array()
        .and_then(|items| {
            items
                .iter()
                .find(|item| item["consequence_id"] == input.question)
        })
        .ok_or_else(|| CoreError::new("answer references a stale or absent decision"))?;
    if question["choices"].as_array().is_some_and(|items| {
        !items.is_empty() && !items.iter().any(|item| item["id"] == input.answer)
    }) {
        return Err(CoreError::new("answer is not a returned bounded choice"));
    }
    let mut request = question["response_request"].clone();
    request["arguments"]
        .as_object_mut()
        .ok_or_else(|| CoreError::new("current decision has no response request"))?
        .insert("answer".to_owned(), input.answer);
    prepare_request_value(
        json!({"current_work": request["task_identity"], "request": request, "capability_contract": input.capability_contract}),
    )
}

pub fn compile_value(value: Value) -> Result<Value, CoreError> {
    let input: DecisionInput =
        serde_json::from_value(value).map_err(|error| CoreError::new(error.to_string()))?;
    compile(input)
}

/// Compose a validated owner result with a fresh host-resolved continuation.
/// The outcome and invocation are committed evidence; the view is never stored
/// as part of that evidence. Null means current resolution is unavailable.
pub fn operation_result_value(value: Value) -> Result<Value, CoreError> {
    #[derive(Deserialize)]
    #[serde(deny_unknown_fields)]
    struct ResultInput {
        invocation: Value,
        outcome: Outcome,
        decision: Value,
    }
    #[derive(Deserialize)]
    #[serde(deny_unknown_fields)]
    struct Outcome {
        status: String,
        #[serde(default)]
        effects: Vec<String>,
        #[serde(default)]
        value: Value,
    }
    let input: ResultInput =
        serde_json::from_value(value).map_err(|error| CoreError::new(error.to_string()))?;
    if !matches!(
        input.outcome.status.as_str(),
        "applied" | "unchanged" | "rejected"
    ) {
        return Err(CoreError::new(
            "operation result status must be applied, unchanged, or rejected",
        ));
    }
    let effects = input.invocation["effects"]
        .as_array()
        .ok_or_else(|| CoreError::new("invocation effects must be an array"))?;
    if input
        .outcome
        .effects
        .iter()
        .any(|effect| !effects.contains(&json!(effect)))
    {
        return Err(CoreError::new(
            "operation result widened its declared effects",
        ));
    }
    Ok(json!({
        "kind": "agentic-workspace/operation-result/v1",
        "operation_id": input.invocation["operation_id"],
        "status": input.outcome.status, "effects": input.outcome.effects,
        "value": input.outcome.value,
        "dependency_revision": input.invocation["expected_dependency_revision"],
        "continuation_status": if input.decision.is_null() { "unavailable" } else { "current" },
        "next_decision": input.decision,
    }))
}

/// Admission consumes a freshly resolved trusted decision and, when present,
/// a trusted receipt's original invocation. It does not execute or store effects.
pub fn admit_invocation_value(value: Value) -> Result<Value, CoreError> {
    #[derive(Deserialize)]
    #[serde(deny_unknown_fields)]
    struct Admission {
        decision: Value,
        invocation: Value,
        previous_invocation: Option<Value>,
    }
    let input: Admission =
        serde_json::from_value(value).map_err(|error| CoreError::new(error.to_string()))?;
    if input.invocation.get("kind").and_then(Value::as_str) != Some(INVOCATION_KIND) {
        return Err(CoreError::new("unsupported invocation kind"));
    }
    if let Some(previous) = &input.previous_invocation {
        let id = previous["operation_id"].as_str().unwrap_or("");
        let revision = previous["operation_revision"]
            .as_str()
            .filter(|v| !v.is_empty());
        if revision.is_none()
            || input.decision["operation_revisions"][id].as_str() != revision
            || input.invocation["operation_revision"].as_str() != revision
        {
            return Err(CoreError::new(
                "retained result is incompatible with current operation semantics",
            ));
        }
    }
    let exact_receipt = input.previous_invocation.as_ref() == Some(&input.invocation);
    let exact_current = input
        .decision
        .get("ready_actions")
        .and_then(Value::as_array)
        .is_some_and(|actions| actions.contains(&input.invocation));
    if !exact_receipt && !exact_current {
        return Err(CoreError::new(
            "invocation is stale or differs from the exact returned action",
        ));
    }
    if let Some(previous) = &input.previous_invocation
        && previous.get("idempotency_key") != input.invocation.get("idempotency_key")
    {
        return Err(CoreError::new(
            "receipt belongs to a different logical effect",
        ));
    }
    Ok(
        json!({"kind": "agentic-workspace/invocation-admission/v1", "disposition": if input.previous_invocation.is_some() {"replay"} else {"execute"}}),
    )
}

fn compile(input: DecisionInput) -> Result<Value, CoreError> {
    if !input.intent.is_object() {
        return Err(CoreError::new("intent must be an object"));
    }
    let decision_context = input
        .decision_context
        .map(continuity::project)
        .transpose()?
        .flatten();
    let capabilities = input
        .capability_contract
        .map(normalize_capability_contract)
        .transpose()?;
    let mut intent = input.intent;
    let supported_intent_fields = [
        "current_work",
        "semantic_route_source",
        "semantic_task_routes",
        "outcome",
        "public_request",
    ];
    if let Some(field) = intent
        .as_object()
        .expect("intent is an object")
        .keys()
        .find(|field| !supported_intent_fields.contains(&field.as_str()))
    {
        return Err(CoreError::new(format!(
            "intent contains unsupported public request field {field}"
        )));
    }
    let semantic_task_routes = normalize_semantic_routes(&mut intent)?;
    let public_request = normalize_public_request(&mut intent, capabilities.as_ref())?;
    let intended = intended_outcome(&intent)?;
    if let (Some(intended), Some(capabilities)) = (intended.as_ref(), capabilities.as_ref())
        && capabilities.claim_authorities.get(&intended.claim) != Some(&intended.owner)
    {
        return Err(CoreError::new(format!(
            "intended outcome owner {} lacks exclusive authority for claim {}",
            intended.owner, intended.claim
        )));
    } else if intended.is_some() && capabilities.is_none() {
        return Err(CoreError::new(
            "intent.outcome requires a current capability_contract",
        ));
    }
    let normalized = input
        .contributions
        .into_iter()
        .map(|contribution| normalize_contribution(contribution, capabilities.as_ref(), &intent))
        .collect::<Result<Vec<_>, _>>()?;
    let request_resolution = resolve_public_request(public_request.as_ref(), &normalized)?;
    let mut relevant = normalized
        .into_iter()
        .filter(|item| item.relevant)
        .collect::<Vec<_>>();
    relevant.sort_by(|left, right| left.owner.cmp(&right.owner));
    if relevant
        .windows(2)
        .any(|pair| pair[0].owner == pair[1].owner)
    {
        return Err(CoreError::new(
            "each source owner may contribute at most once",
        ));
    }

    let mut revision_input =
        json!({"intent": intent, "capability_contract": capabilities, "sources": relevant});
    if let Some(context) = &decision_context {
        revision_input["decision_context"] = context.clone();
    }
    let input_revision = digest(&revision_input)?;
    let blockers = relevant
        .iter()
        .flat_map(|item| item.blockers.iter().cloned())
        .collect::<Vec<_>>();
    let mut decisions = relevant
        .iter()
        .flat_map(|item| item.decisions.iter().cloned())
        .collect::<Vec<_>>();
    decisions.sort_by(|left, right| {
        (&left.owner, &left.id, &left.consequence_id).cmp(&(
            &right.owner,
            &right.id,
            &right.consequence_id,
        ))
    });
    let mut actions = relevant
        .iter()
        .flat_map(|item| {
            item.actions.iter().cloned().map(|action| OwnedAction {
                owner: item.owner.clone(),
                action,
            })
        })
        .collect::<Vec<_>>();
    actions.sort_by(|left, right| {
        (
            &left.owner,
            &left.action.operation_id,
            &left.action.consequence_id,
        )
            .cmp(&(
                &right.owner,
                &right.action.operation_id,
                &right.action.consequence_id,
            ))
    });

    let constrained = blockers
        .iter()
        .flat_map(|item| item.affects.iter().cloned())
        .chain(
            decisions
                .iter()
                .flat_map(|item| item.affects.iter().cloned()),
        )
        .collect::<BTreeSet<_>>();
    let available_actions = actions
        .iter()
        .filter(|owned| {
            !constrained.contains(TASK)
                && !constrained.contains(&owned.action.consequence_id)
                && !owned
                    .action
                    .effects
                    .iter()
                    .any(|effect| constrained.contains(&format!("effect:{effect}")))
        })
        .cloned()
        .collect::<Vec<_>>();

    let independent = available_actions.iter().enumerate().all(|(index, left)| {
        available_actions[index + 1..]
            .iter()
            .all(|right| independent_actions(left, right, capabilities.as_ref()))
    });
    let ready_actions = if independent {
        available_actions
            .iter()
            .map(|selected| {
                json!({
                    "kind": INVOCATION_KIND,
                    "consequence_id": selected.action.consequence_id,
                    "operation_id": selected.action.operation_id,
                    "arguments": selected.action.arguments,
                    "effects": selected.action.effects,
                    "authority": selected.action.authority,
                    "source_owner": selected.owner,
                    "expected_dependency_revision": selected.action.dependency_revision,
                    "operation_revision": selected.action.operation_revision,
                    "idempotency_key": selected.action.logical_effect_id,
                })
            })
            .collect::<Vec<_>>()
    } else {
        Vec::new()
    };
    let primary_action = (ready_actions.len() == 1).then(|| ready_actions[0].clone());

    let task_decisions = decisions
        .iter()
        .filter(|item| item.affects.iter().any(|affected| affected == TASK))
        .cloned()
        .collect::<Vec<_>>();
    let action_composition = (!independent).then(|| {
        json!({
            "code": "multiple-actions",
            "message": "current actions have conflicting or unknown read/effect relationships",
            "owner": "operating-decision",
            "revision": input_revision,
            "affects": available_actions.iter().map(|action| &action.action.consequence_id).collect::<Vec<_>>(),
            "alternatives": available_actions.iter().map(pending_action).collect::<Vec<_>>(),
        })
    });
    let decision_request =
        if ready_actions.is_empty() && action_composition.is_none() && task_decisions.len() == 1 {
            Some(serde_json::to_value(&task_decisions[0]).expect("normalized decision serializes"))
        } else {
            None
        };
    let decision_composition = (primary_action.is_none() && action_composition.is_none() && task_decisions.len() > 1).then(|| {
        json!({
            "code": "multiple-decisions",
            "message": "multiple task-wide decisions require an explicit dependency or authority relation",
            "owner": "operating-decision",
            "revision": input_revision,
            "affects": [TASK],
            "alternatives": task_decisions,
        })
    });
    let composition_blocker = action_composition.or(decision_composition);
    let mut blocker_values = blockers
        .iter()
        .map(|blocker| serde_json::to_value(blocker).expect("normalized blocker serializes"))
        .collect::<Vec<_>>();
    if let Some(blocker) = &composition_blocker {
        let mut blocker = blocker.clone();
        let consequence_id = format!(
            "blocker:operating-decision:{input_revision}:{}",
            digest(&blocker)?
        );
        blocker
            .as_object_mut()
            .expect("composition blocker is an object")
            .insert("consequence_id".to_owned(), Value::String(consequence_id));
        blocker_values.push(blocker);
    }

    let blocked_claims = relevant
        .iter()
        .flat_map(|item| item.claims.blocked.iter().cloned())
        .collect::<BTreeSet<_>>();
    let allowed_claims = relevant
        .iter()
        .flat_map(|item| item.claims.allowed.iter().cloned())
        .filter(|claim| !blocked_claims.contains(claim))
        .collect::<BTreeSet<_>>();

    let terminal_authority = terminal_authority(
        intended.as_ref(),
        &relevant,
        &constrained,
        &allowed_claims,
        &blocked_claims,
    );
    let globally_blocked = composition_blocker.is_some()
        || blockers
            .iter()
            .any(|item| item.affects.iter().any(|affected| affected == TASK));
    let status = if terminal_authority.is_some() {
        "terminal"
    } else if !ready_actions.is_empty() {
        "actionable"
    } else if globally_blocked {
        "blocked"
    } else if decision_request.is_some() {
        "decision"
    } else {
        "direct"
    };

    let pending_actions = actions.iter().map(pending_action).collect::<Vec<_>>();
    let mut answer = json!({
        "input_revision": input_revision,
        "status": status,
        "primary_action": if terminal_authority.is_some() { None } else { primary_action },
        "ready_actions": ready_actions,
        "decision_request": decision_request,
        "blockers": blocker_values,
        "pending_consequences": {"blockers": blocker_values, "decisions": decisions, "actions": pending_actions},
        "claim_boundary": {"allowed": allowed_claims, "blocked": blocked_claims},
        "relevant_owners": relevant.iter().map(|item| &item.owner).collect::<Vec<_>>(),
        "owner_states": relevant.iter().map(|item| json!({"owner": item.owner, "revision": item.revision, "settled": item.settled})).collect::<Vec<_>>(),
        "terminal_authority": terminal_authority,
    });
    if let Some(context) = decision_context {
        answer["decision_context"] = context;
    }
    if let Some(routes) = semantic_task_routes {
        answer
            .as_object_mut()
            .expect("answer is an object")
            .insert("semantic_task_routes".to_owned(), routes);
    }
    if let Some(resolution) = request_resolution {
        answer
            .as_object_mut()
            .expect("answer is an object")
            .insert("request_resolution".to_owned(), resolution);
    }
    if let Some(capabilities) = capabilities {
        let revisions = capabilities
            .owners
            .iter()
            .flat_map(|(owner, capability)| {
                capability
                    .operations
                    .keys()
                    .map(move |id| (owner, capability, id))
            })
            .map(|(owner, capability, id)| {
                Ok((id.clone(), operation_revision(owner, id, capability)?))
            })
            .collect::<Result<BTreeMap<_, _>, CoreError>>()?;
        answer
            .as_object_mut()
            .unwrap()
            .insert("operation_revisions".to_owned(), json!(revisions));
        answer.as_object_mut().expect("answer is an object").insert(
            "capability_revision".to_owned(),
            Value::String(capabilities.revision),
        );
    }
    let decision_id = format!("operating-decision:{}", &digest(&answer)?[7..23]);
    let mut output = answer.as_object().expect("answer is an object").clone();
    output.insert("kind".to_owned(), Value::String(DECISION_KIND.to_owned()));
    output.insert("decision_id".to_owned(), Value::String(decision_id));
    Ok(Value::Object(output))
}

fn resolve_public_request(
    request: Option<&NormalizedPublicRequest>,
    contributions: &[NormalizedContribution],
) -> Result<Option<Value>, CoreError> {
    let responses = contributions
        .iter()
        .filter(|contribution| contribution.request_response.is_some())
        .collect::<Vec<_>>();
    let Some(request) = request else {
        if !responses.is_empty() {
            return Err(CoreError::new(
                "request_response cannot exist without intent.public_request",
            ));
        }
        return Ok(None);
    };
    if responses.len() != 1 {
        return Err(CoreError::new(
            "public request requires exactly one owner response",
        ));
    }
    let contribution = responses[0];
    let response = contribution
        .request_response
        .as_ref()
        .expect("response was selected");
    if contribution.owner != request.owner {
        return Err(CoreError::new(format!(
            "public request owner {} cannot be answered by {}",
            request.owner, contribution.owner
        )));
    }
    if !contribution.relevant {
        return Err(CoreError::new(format!(
            "public request owner {} returned a non-current response",
            request.owner
        )));
    }
    if contribution.revision != request.source_revision {
        return Err(CoreError::new(format!(
            "public request response from {} is stale for its source revision",
            request.owner
        )));
    }
    if response.request_identity != request.identity {
        return Err(CoreError::new(format!(
            "public request response from {} references a different request",
            request.owner
        )));
    }

    let candidates = match response.status.as_str() {
        "action" => contribution
            .actions
            .iter()
            .map(|item| &item.consequence_id)
            .collect::<BTreeSet<_>>(),
        "decision" => contribution
            .decisions
            .iter()
            .map(|item| &item.consequence_id)
            .collect(),
        "blocked" => contribution
            .blockers
            .iter()
            .map(|item| &item.consequence_id)
            .collect(),
        "settled" => BTreeSet::new(),
        _ => unreachable!("response status was normalized"),
    };
    if (response.status == "settled") != response.consequence_ids.is_empty()
        || response
            .consequence_ids
            .iter()
            .any(|id| !candidates.contains(id))
    {
        return Err(CoreError::new(
            "request response must name its exact current owner consequences of the declared response kind",
        ));
    }
    Ok(Some(json!({
        "request_id": request.id,
        "request_identity": request.identity,
        "owner": request.owner,
        "owner_revision": request.owner_revision,
        "source_revision": request.source_revision,
        "request_kind": request.request_kind,
        "result_kind": request.result_kind,
        "status": response.status,
        "consequence_ids": response.consequence_ids,
    })))
}

fn pending_action(owned: &OwnedAction) -> Value {
    let mut value = serde_json::to_value(&owned.action)
        .expect("normalized action serializes")
        .as_object()
        .expect("normalized action is an object")
        .clone();
    value.insert(
        "source_owner".to_owned(),
        Value::String(owned.owner.clone()),
    );
    Value::Object(value)
}

fn independent_actions(
    left: &OwnedAction,
    right: &OwnedAction,
    capabilities: Option<&NormalizedCapabilityContract>,
) -> bool {
    let Some(contract) = capabilities else {
        return false;
    };
    let footprint = |action: &OwnedAction| -> Option<(BTreeSet<String>, BTreeSet<String>)> {
        let owner = contract.owners.get(&action.owner)?;
        let operation = owner.operations.get(&action.action.operation_id)?;
        // Missing reads means unknown, not an empty read set. Use the full
        // admitted effect ceiling, never a contribution's narrowed effects.
        let reads = operation.reads.clone()?;
        let writes = operation
            .effects
            .iter()
            .map(|effect| owner.effects[effect].clone())
            .collect();
        Some((reads, writes))
    };
    let (Some((left_reads, left_writes)), Some((right_reads, right_writes))) =
        (footprint(left), footprint(right))
    else {
        return false;
    };
    left_writes.is_disjoint(&right_writes)
        && left_writes.is_disjoint(&right_reads)
        && right_writes.is_disjoint(&left_reads)
}

fn terminal_authority(
    intended: Option<&IntendedOutcome>,
    relevant: &[NormalizedContribution],
    constrained: &BTreeSet<String>,
    allowed_claims: &BTreeSet<String>,
    blocked_claims: &BTreeSet<String>,
) -> Option<Value> {
    let intended = intended?;
    let owner = relevant.iter().find(|item| item.owner == intended.owner)?;
    let outcome = owner.outcome.as_ref()?;
    let terminal_consequences = [
        TASK.to_owned(),
        format!("claim:{}", intended.claim),
        format!("outcome:{}", intended.id),
    ];
    if outcome.id != intended.id
        || outcome.claim != intended.claim
        || outcome.status != "complete"
        || outcome.evidence_revision != owner.revision
        || !outcome.residual_work.is_empty()
        || outcome.required_claims.iter().any(|claim| {
            !allowed_claims.contains(claim)
                || blocked_claims.contains(claim)
                || constrained.contains(&format!("claim:{claim}"))
        })
        || !allowed_claims.contains(&outcome.claim)
        || blocked_claims.contains(&outcome.claim)
        || terminal_consequences
            .iter()
            .any(|identity| constrained.contains(identity))
    {
        return None;
    }
    Some(json!({
        "owner": owner.owner,
        "revision": owner.revision,
        "id": outcome.id,
        "status": outcome.status,
        "claim": outcome.claim,
        "evidence_revision": outcome.evidence_revision,
        "residual_work": outcome.residual_work,
        "required_claims": outcome.required_claims,
    }))
}
