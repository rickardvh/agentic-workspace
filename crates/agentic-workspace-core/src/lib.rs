use serde::{Deserialize, Serialize};
use serde_json::{Map, Value, json};
use sha2::{Digest, Sha256};
use std::collections::{BTreeSet, HashSet};
use std::fmt::{Display, Formatter};

const CONTRIBUTION_KIND: &str = "agentic-workspace/source-contribution/v1";
const DECISION_KIND: &str = "agentic-workspace/operating-decision/v1";
const INVOCATION_KIND: &str = "agentic-workspace/operation-invocation/v1";
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
struct DecisionInput {
    contributions: Vec<ContributionInput>,
    #[serde(default = "empty_object")]
    intent: Value,
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
    #[serde(flatten)]
    extra: Map<String, Value>,
}

#[derive(Debug, Deserialize)]
struct ActionInput {
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
    #[serde(default)]
    response_operation_id: String,
    #[serde(default)]
    choices: Vec<Choice>,
    #[serde(default)]
    affects: Vec<String>,
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

#[derive(Debug, Deserialize, Serialize)]
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
}

#[derive(Debug, Clone, Serialize)]
struct NormalizedAction {
    consequence_id: String,
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
    response_operation_id: String,
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
                .any(|prefix| value.starts_with(prefix))
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

fn normalize_contribution(input: ContributionInput) -> Result<NormalizedContribution, CoreError> {
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

    let mut actions = input
        .actions
        .into_iter()
        .enumerate()
        .map(|(index, action)| normalize_action(action, &owner, &revision, index))
        .collect::<Result<Vec<_>, _>>()?;
    actions.sort_by(|left, right| left.consequence_id.cmp(&right.consequence_id));

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
        .map(|(index, decision)| normalize_decision(decision, &owner, &revision, index))
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
    )?
    .into_iter()
    .filter(|claim| !blocked_set.contains(claim))
    .collect();
    let outcome = input
        .outcome
        .map(|value| normalize_outcome(value, &owner))
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
    })
}

fn normalize_action(
    input: ActionInput,
    owner: &str,
    revision: &str,
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
    let identity = json!({
        "owner": owner,
        "revision": revision,
        "operation_id": operation_id,
        "arguments": input.arguments,
        "effects": effects,
        "authority": authority,
    });
    let consequence_id = format!("action:{owner}:{revision}:{}", digest(&identity)?);
    Ok(NormalizedAction {
        consequence_id,
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
) -> Result<NormalizedDecision, CoreError> {
    let id = require_text(&input.id, &format!("{owner}.decisions[{index}].id"))?;
    let question = require_text(
        &input.question,
        &format!("{owner}.decisions[{index}].question"),
    )?;
    let response_operation_id = require_text(
        &input.response_operation_id,
        &format!("{owner}.decisions[{index}].response_operation_id"),
    )?;
    if input.choices.is_empty() {
        return Err(CoreError::new(format!(
            "{owner}.decisions[{index}] requires bounded choices"
        )));
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
        "response_operation_id": response_operation_id, "choices": choices, "affects": affected,
    });
    Ok(NormalizedDecision {
        consequence_id: format!("decision:{owner}:{revision}:{}", digest(&identity)?),
        id: identity["id"].as_str().expect("id is text").to_owned(),
        owner: owner.to_owned(),
        revision: revision.to_owned(),
        question: identity["question"]
            .as_str()
            .expect("question is text")
            .to_owned(),
        response_operation_id: identity["response_operation_id"]
            .as_str()
            .expect("response operation is text")
            .to_owned(),
        choices: serde_json::from_value(identity["choices"].clone()).expect("choices are valid"),
        affects: serde_json::from_value(identity["affects"].clone()).expect("affects are strings"),
    })
}

fn normalize_outcome(input: OutcomeInput, owner: &str) -> Result<NormalizedOutcome, CoreError> {
    Ok(NormalizedOutcome {
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
    if current.is_none() && source.is_none() && selection.is_none() {
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

pub fn compile_value(value: Value) -> Result<Value, CoreError> {
    let input: DecisionInput =
        serde_json::from_value(value).map_err(|error| CoreError::new(error.to_string()))?;
    compile(input)
}

fn compile(input: DecisionInput) -> Result<Value, CoreError> {
    if !input.intent.is_object() {
        return Err(CoreError::new("intent must be an object"));
    }
    let mut intent = input.intent;
    let semantic_task_routes = normalize_semantic_routes(&mut intent)?;
    let intended = intended_outcome(&intent)?;
    let mut relevant = input
        .contributions
        .into_iter()
        .map(normalize_contribution)
        .collect::<Result<Vec<_>, _>>()?
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

    let input_revision = digest(&json!({"intent": intent, "sources": relevant}))?;
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

    let primary_action = if available_actions.len() == 1 {
        let selected = &available_actions[0];
        let idempotency_key = digest(&json!({
            "action_consequence_id": selected.action.consequence_id,
            "input_revision": input_revision,
        }))?;
        Some(json!({
            "kind": INVOCATION_KIND,
            "consequence_id": selected.action.consequence_id,
            "operation_id": selected.action.operation_id,
            "arguments": selected.action.arguments,
            "effects": selected.action.effects,
            "authority": selected.action.authority,
            "source_owner": selected.owner,
            "expected_input_revision": input_revision,
            "idempotency_key": idempotency_key,
        }))
    } else {
        None
    };

    let task_decisions = decisions
        .iter()
        .filter(|item| item.affects.iter().any(|affected| affected == TASK))
        .cloned()
        .collect::<Vec<_>>();
    let action_composition = (available_actions.len() > 1).then(|| {
        json!({
            "code": "multiple-actions",
            "message": "multiple current actions require an explicit dependency or authority relation",
            "owner": "operating-decision",
            "revision": input_revision,
            "affects": [TASK],
            "alternatives": available_actions.iter().map(pending_action).collect::<Vec<_>>(),
        })
    });
    let decision_request =
        if primary_action.is_none() && action_composition.is_none() && task_decisions.len() == 1 {
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
        &actions,
        &task_decisions,
        composition_blocker.as_ref(),
        &constrained,
        &allowed_claims,
        &blocked_claims,
    );
    let globally_blocked = composition_blocker.is_some()
        || blockers
            .iter()
            .any(|item| item.affects.iter().any(|affected| affected == TASK));
    let status = if primary_action.is_some() {
        "actionable"
    } else if globally_blocked {
        "blocked"
    } else if decision_request.is_some() {
        "decision"
    } else if terminal_authority.is_some() {
        "terminal"
    } else {
        "direct"
    };

    let pending_actions = actions.iter().map(pending_action).collect::<Vec<_>>();
    let mut answer = json!({
        "input_revision": input_revision,
        "status": status,
        "primary_action": primary_action,
        "decision_request": decision_request,
        "blockers": blocker_values,
        "pending_consequences": {"blockers": blocker_values, "decisions": decisions, "actions": pending_actions},
        "claim_boundary": {"allowed": allowed_claims, "blocked": blocked_claims},
        "relevant_owners": relevant.iter().map(|item| &item.owner).collect::<Vec<_>>(),
        "owner_states": relevant.iter().map(|item| json!({"owner": item.owner, "revision": item.revision, "settled": item.settled})).collect::<Vec<_>>(),
        "terminal_authority": terminal_authority,
    });
    if let Some(routes) = semantic_task_routes {
        answer
            .as_object_mut()
            .expect("answer is an object")
            .insert("semantic_task_routes".to_owned(), routes);
    }
    let decision_id = format!("operating-decision:{}", &digest(&answer)?[7..23]);
    let mut output = answer.as_object().expect("answer is an object").clone();
    output.insert("kind".to_owned(), Value::String(DECISION_KIND.to_owned()));
    output.insert("decision_id".to_owned(), Value::String(decision_id));
    Ok(Value::Object(output))
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

#[allow(clippy::too_many_arguments)]
fn terminal_authority(
    intended: Option<&IntendedOutcome>,
    relevant: &[NormalizedContribution],
    actions: &[OwnedAction],
    task_decisions: &[NormalizedDecision],
    composition_blocker: Option<&Value>,
    constrained: &BTreeSet<String>,
    allowed_claims: &BTreeSet<String>,
    blocked_claims: &BTreeSet<String>,
) -> Option<Value> {
    let intended = intended?;
    if !actions.is_empty() || !task_decisions.is_empty() || composition_blocker.is_some() {
        return None;
    }
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
    }))
}
