import { spawnSync } from "node:child_process";
import { existsSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const packagedBinary = () => join(
  dirname(fileURLToPath(import.meta.url)),
  "bin",
  process.platform === "win32" ? "agentic-workspace-core.exe" : "agentic-workspace-core",
);

const coreBinary = () => {
  const candidate = process.env.AGENTIC_WORKSPACE_CORE_BINARY || packagedBinary();
  if (!existsSync(candidate)) {
    throw new Error("shared Agentic Workspace core is unavailable; install a supported native package or set AGENTIC_WORKSPACE_CORE_BINARY");
  }
  return candidate;
};

export function compileSourceDecision(contributions, intent = {}, capabilityContract = null) {
  const payload = { contributions: [...contributions], intent: { ...(intent || {}) } };
  if (capabilityContract !== null) payload.capability_contract = { ...capabilityContract };
  return request(payload);
}

export function admitInvocation(decision, invocation, previousInvocation = null) {
  return request({admission: {decision, invocation, previous_invocation: previousInvocation}});
}

export function prepareRequest(publicRequest, currentWork, capabilityContract) {
  return request({prepare_request: {request: publicRequest, current_work: currentWork, capability_contract: capabilityContract}});
}

export function answerDecision(decision, consequenceId, answer, capabilityContract) {
  return request({answer_decision: {decision, question: consequenceId, answer, capability_contract: capabilityContract}});
}

function request(payload) {
  const result = spawnSync(coreBinary(), [], {
    input: JSON.stringify(payload),
    encoding: "utf8",
    windowsHide: true,
  });
  if (result.status !== 0) {
    let message = result.stderr.trim() || `shared core exited with status ${result.status}`;
    try { message = JSON.parse(result.stderr).error.message; } catch {}
    throw new Error(message);
  }
  return JSON.parse(result.stdout);
}
