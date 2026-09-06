import { spawnSync } from "node:child_process";
import { existsSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const packagedBinary = () => join(
  dirname(fileURLToPath(import.meta.url)),
  "bin",
  process.platform === "win32" ? "agentic-workspace-core.exe" : "agentic-workspace-core",
);

const coreBinary = () => {
  let candidate = process.env.AGENTIC_WORKSPACE_CORE_BINARY || packagedBinary();
  const sourceRoot = resolve(dirname(fileURLToPath(import.meta.url)), "../..");
  if (!process.env.AGENTIC_WORKSPACE_CORE_BINARY && !existsSync(candidate) && existsSync(join(sourceRoot, "crates/agentic-workspace-core/Cargo.toml"))) {
    const built = spawnSync("cargo", ["build", "--quiet", "--locked", "--manifest-path", join(sourceRoot, "Cargo.toml"), "--message-format=json", "-p", "agentic-workspace-core"], { cwd: sourceRoot, encoding: "utf8", windowsHide: true });
    if (built.status !== 0) throw new Error(`source checkout core build failed: ${built.error?.message || built.stderr.trim()}`);
    const artifact = built.stdout.split(/\r?\n/).filter(Boolean).map(line => JSON.parse(line)).find(row => row.reason === "compiler-artifact" && row.target?.name === "agentic-workspace-core" && row.executable);
    if (!artifact) throw new Error("Cargo did not return a current shared-core executable");
    candidate = artifact.executable;
  }
  if (!existsSync(candidate)) {
    throw new Error("shared Agentic Workspace core is unavailable; install a supported native package or set AGENTIC_WORKSPACE_CORE_BINARY");
  }
  return candidate;
};

export function compileSourceDecision(contributions, intent = {}, capabilityContract = null, decisionContext = null) {
  const payload = { contributions: [...contributions], intent: { ...(intent || {}) } };
  if (capabilityContract !== null) payload.capability_contract = { ...capabilityContract };
  if (decisionContext !== null) payload.decision_context = { ...decisionContext };
  return request(payload);
}

export function admitInvocation(decision, invocation, previousInvocation = null) {
  return request({admission: {decision, invocation, previous_invocation: previousInvocation}});
}

export function prepareRequest(publicRequest, currentWork, capabilityContract) {
  return request({prepare_request: {request: publicRequest, current_work: currentWork, capability_contract: capabilityContract}});
}

export function semanticRouteView(context) {
  return request({semantic_route_view: context});
}

export function instructionSourceAdmission(context) {
  return request({instruction_source_admission: context});
}

export function replaceAssignment(context) {
  return request({replace_assignment: context});
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

export function operationResult(invocation, outcome, decision) {
  return request({ operation_result: { invocation, outcome, decision } });
}

export function admitAttempt(decision, invocation, record = null) {
  return request({admit_attempt: {decision, invocation, record}});
}

export function commitAttempt(record, outcome) {
  return request({commit_attempt: {record, outcome}});
}

export function admitStoredAttempt(target, decision, invocation, custody = null) {
  return request({admit_stored_attempt: {target, decision, invocation, custody}});
}

export function commitStoredAttempt(target, custody, outcome) {
  return request({commit_stored_attempt: {target, custody, outcome}});
}

export function planningView(context) {
  return request({planning_view: context});
}

export function reconcilePlanning(context) {
  return request({reconcile_planning: context});
}

export function normalizeDecisionRecord(record) {
  return request({normalize_decision_record: record});
}

// Trusted host/source-owner context, never caller-authored public request fields.
export function repositoryDecisionView(context) {
  return request({repository_decision_view: context});
}

export function admitAssignmentPacket(context) {
  return request({admit_assignment_packet: context});
}

export function executionConfigurations(context) {
  return request({execution_configurations: context});
}
