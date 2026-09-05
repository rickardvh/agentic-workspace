import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import { readFileSync } from "node:fs";
import { join } from "node:path";
import { fileURLToPath } from "node:url";
import test from "node:test";
import { compileSourceDecision, admitInvocation, prepareRequest, answerDecision, operationResult, admitAttempt, commitAttempt } from "../semantic-decision.mjs";

const vectors = JSON.parse(readFileSync(new URL("../../../tests/vectors/source_decision.json", import.meta.url), "utf8"));
const capabilityContract = JSON.parse(readFileSync(new URL("../../../tests/vectors/capability_contract.json", import.meta.url), "utf8"));

const authorityBearing = (input) => Boolean(
  input.intent?.outcome || input.intent?.public_request || input.contributions.some((contribution) =>
    ["actions", "blockers", "decisions"].some((field) => contribution[field]?.length)
      || contribution.outcome || contribution.request_response
      || contribution.claims?.allowed?.length || contribution.claims?.blocked?.length),
);
process.env.AGENTIC_WORKSPACE_CORE_BINARY ||= join(
  fileURLToPath(new URL("../../../target/debug", import.meta.url)),
  process.platform === "win32" ? "agentic-workspace-core.exe" : "agentic-workspace-core",
);
const direct = (input) => {
  const result = spawnSync(process.env.AGENTIC_WORKSPACE_CORE_BINARY, [], { input: JSON.stringify(input), encoding: "utf8", windowsHide: true });
  return result.status === 0 ? JSON.parse(result.stdout) : JSON.parse(result.stderr);
};

test("Node binding executes the exact shared core", () => {
  for (const vector of vectors.cases) {
    const contract = vector.input.capability_contract ?? (authorityBearing(vector.input) ? capabilityContract : null);
    assert.deepEqual(compileSourceDecision(vector.input.contributions, vector.input.intent, contract), direct({...vector.input, ...(contract && {capability_contract: contract})}), vector.id);
  }
});

test("Node binding preserves shared fail-closed errors", () => {
  for (const vector of vectors.error_cases) {
    assert.throws(
      () => compileSourceDecision(vector.input.contributions, vector.input.intent, vector.input.capability_contract ?? (authorityBearing(vector.input) ? capabilityContract : null)),
      (error) => error.message.includes(vector.error_contains),
      vector.id,
    );
  }
});


test("action dependencies and logical effects have separate lifetimes", () => {
  const payload = structuredClone(vectors.cases.find(v => v.id === "action-material-dependencies").input);
  const compile = () => compileSourceDecision(payload.contributions, payload.intent, capabilityContract);
  const first = compile();
  payload.contributions[0].revision = "unrelated-advice";
  const unrelated = compile();
  assert.notEqual(first.input_revision, unrelated.input_revision);
  assert.deepEqual(first.primary_action, unrelated.primary_action);
  assert.equal(admitInvocation(unrelated, first.primary_action).disposition, "execute");
  payload.contributions[0].actions[0].dependency_revision = "proof-2";
  const changed = compile();
  assert.equal(first.primary_action.idempotency_key, changed.primary_action.idempotency_key);
  assert.throws(() => admitInvocation(changed, first.primary_action), /stale or differs/);
  payload.contributions[0].actions[0].effect_generation = "authorized-repeat-2";
  assert.notEqual(first.primary_action.idempotency_key, compile().primary_action.idempotency_key);
});


test("a client can choose either exact ready action", () => {
  const p = vectors.cases.find(v => v.id === "two-independent-ready-actions").input;
  const decision = compileSourceDecision(p.contributions, p.intent, p.capability_contract);
  assert.equal(decision.primary_action, null);
  assert.equal(decision.ready_actions.length, 2);
  for (const action of decision.ready_actions) assert.equal(admitInvocation(decision, action).disposition, "execute");
});


test("request preparation is shared and same-ID argument changes reject old responses", () => {
  const p = structuredClone(vectors.cases.find(v => v.id === "typed-public-request-returns-an-exact-owner-action").input);
  const prepared = prepareRequest(p.intent.public_request, p.intent.current_work, capabilityContract);
  assert.deepEqual(prepared.request, p.intent.public_request);
  assert.equal(prepared.identity, p.contributions[0].request_response.request_identity);
  p.intent.public_request.arguments.subject.name = "different";
  assert.throws(() => compileSourceDecision(p.contributions, p.intent, capabilityContract), /references a different request/);
});


test("finite and open answers need only returned question and human answer", () => {
  const payload = structuredClone(vectors.cases.find(v => v.id === "task-decision-is-current-and-bounded").input);
  const current = compileSourceDecision(payload.contributions, payload.intent, capabilityContract);
  const key = current.pending_consequences.decisions[0].consequence_id;
  const result = answerDecision(current, key, "mit", capabilityContract);
  assert.deepEqual(result.request.arguments, {answer: "mit"});
  assert.deepEqual(result, direct({answer_decision: {decision: current, question: key, answer: "mit", capability_contract: capabilityContract}}));
  assert.throws(() => answerDecision(current, key, "other", capabilityContract), /not a returned bounded choice/);
  payload.contributions[0].revision = "new";
  const changed = compileSourceDecision(payload.contributions, payload.intent, capabilityContract);
  assert.throws(() => answerDecision(changed, key, "mit", capabilityContract), /stale or absent/);
  delete payload.contributions[0].decisions[0].choices;
  const open = compileSourceDecision(payload.contributions, payload.intent, capabilityContract);
  const openKey = open.pending_consequences.decisions[0].consequence_id;
  assert.deepEqual(answerDecision(open, openKey, "human judgment", capabilityContract).request.arguments, {answer: "human judgment"});
  assert.throws(() => answerDecision(open, openKey, 17, capabilityContract), /violate input_schema/);
});


test("committed outcome is composed only with current continuation", () => {
  const payload = vectors.cases.find(v => v.id === "action-material-dependencies").input;
  const first = compileSourceDecision(payload.contributions, payload.intent, capabilityContract);
  const invocation = first.primary_action;
  const outcome = {status: "applied", effects: invocation.effects, value: {exact: "committed"}};
  for (const decision of [first, compileSourceDecision([]), null]) {
    const result = operationResult(invocation, outcome, decision);
    assert.deepEqual(result, direct({operation_result: {invocation, outcome, decision}}));
    assert.deepEqual(result.value, outcome.value);
    assert.deepEqual(result.next_decision, decision);
    assert.equal(result.continuation_status, decision === null ? "unavailable" : "current");
  }
  assert.throws(() => operationResult(invocation, {...outcome, effects: ["unowned"]}, first), /widened/);
  assert.throws(() => operationResult(invocation, {...outcome, next_decision: first}, first), /unknown field/);
});


test("replay rejects incompatible operation semantics without minting an effect", () => {
  const payload = structuredClone(vectors.cases.find(v => v.id === "action-material-dependencies").input);
  const contract = structuredClone(capabilityContract);
  const first = compileSourceDecision(payload.contributions, payload.intent, contract);
  const original = first.primary_action;
  const operation = contract.owners.flatMap(owner => owner.operations).find(op => op.id === original.operation_id);
  operation.semantic_revision = "v2";
  const current = compileSourceDecision(payload.contributions, payload.intent, contract);
  assert.equal(current.primary_action.idempotency_key, original.idempotency_key);
  assert.notEqual(current.primary_action.operation_revision, original.operation_revision);
  assert.throws(() => admitInvocation(current, original, original), /current operation semantics/);
  assert.throws(() => admitInvocation(current, current.primary_action, original), /current operation semantics/);
});


test("retained attempt cannot become a retry and committed evidence replays", () => {
  const payload = vectors.cases.find(v => v.id === "action-material-dependencies").input;
  const decision = compileSourceDecision(payload.contributions, payload.intent, capabilityContract);
  const action = decision.primary_action;
  const admitted = admitAttempt(decision, action);
  assert.equal(admitted.disposition, "execute");
  assert.equal(admitAttempt(decision, action, admitted.record).disposition, "uncertain");
  const committed = commitAttempt(admitted.record, {status: "applied", effects: action.effects, value: 1});
  const replay = admitAttempt(decision, action, committed);
  assert.equal(replay.disposition, "replay");
  assert.equal(replay.attempt_id, admitted.attempt_id);
  assert.deepEqual(replay, direct({admit_attempt: {decision, invocation: action, record: committed}}));
  assert.throws(() => admitAttempt(decision, action, {...committed, attempt_id: "retry-random"}), /invalid/);
  assert.throws(() => commitAttempt(committed, {status: "applied", effects: action.effects, value: 2}), /cannot change/);
});
