import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import { readFileSync } from "node:fs";
import { join } from "node:path";
import { fileURLToPath } from "node:url";
import test from "node:test";
import { compileSourceDecision, admitInvocation } from "../semantic-decision.mjs";

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
