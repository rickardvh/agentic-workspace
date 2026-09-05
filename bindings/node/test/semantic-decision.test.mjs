import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import { readFileSync } from "node:fs";
import { join } from "node:path";
import { fileURLToPath } from "node:url";
import test from "node:test";
import { compileSourceDecision } from "../semantic-decision.mjs";

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
    const contract = authorityBearing(vector.input) ? capabilityContract : null;
    assert.deepEqual(compileSourceDecision(vector.input.contributions, vector.input.intent, contract), direct({...vector.input, ...(contract && {capability_contract: contract})}), vector.id);
  }
});

test("Node binding preserves shared fail-closed errors", () => {
  for (const vector of vectors.error_cases) {
    assert.throws(
      () => compileSourceDecision(vector.input.contributions, vector.input.intent, authorityBearing(vector.input) ? capabilityContract : null),
      (error) => error.message.includes(vector.error_contains),
      vector.id,
    );
  }
});
