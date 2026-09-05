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

export function compileSourceDecision(contributions, intent = {}) {
  const result = spawnSync(coreBinary(), [], {
    input: JSON.stringify({ contributions: [...contributions], intent: { ...(intent || {}) } }),
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
