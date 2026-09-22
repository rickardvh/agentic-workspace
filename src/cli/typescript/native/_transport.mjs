import { spawnSync } from "node:child_process";
import { existsSync, readFileSync } from "node:fs";
import { createHash } from "node:crypto";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const nativeDirectory = () => {
  const root = join(dirname(fileURLToPath(import.meta.url)), "bin");
  const selected = join(root, `${process.platform}-${process.arch}`);
  return existsSync(selected) ? selected : root;
};

const packagedBinary = () => join(
  nativeDirectory(),
  process.platform === "win32" ? "agentic-workspace-core.exe" : "agentic-workspace-core",
);

const coreBinary = () => {
  let candidate = process.env.AGENTIC_WORKSPACE_CORE_BINARY || packagedBinary();
  const manifestPath = join(nativeDirectory(), "artifact.json");
  const packagePath = join(dirname(fileURLToPath(import.meta.url)), "../..", "package.json");
  const packageMetadata = existsSync(packagePath) ? JSON.parse(readFileSync(packagePath, 'utf8')) : null;
  if (packageMetadata && !existsSync(manifestPath) && (packageMetadata.agenticWorkspace?.nativeRuntime || !process.env.AGENTIC_WORKSPACE_CORE_BINARY)) throw new Error("packaged shared-core manifest missing; stage the native npm artifact (unpackaged development requires explicit AGENTIC_WORKSPACE_CORE_BINARY)");
  if (existsSync(manifestPath)) {
    const manifest = JSON.parse(readFileSync(manifestPath, 'utf8'));
    const packageJson = JSON.parse(readFileSync(join(dirname(fileURLToPath(import.meta.url)), '../..', 'package.json'), 'utf8'));
    // The paired native/Python identity uses PEP 440; this one RC lane has an
    // explicit npm SemVer spelling. Numeric releases retain exact equality.
    const nativeVersion = packageJson.version.replace(/^1\.0\.0-rc\.([1-9][0-9]*)$/, '1.0.0rc$1');
    if (manifest.platform !== process.platform || manifest.arch !== process.arch || manifest.package_version !== nativeVersion) throw new Error('packaged shared-core platform/version mismatch');
    if (!existsSync(candidate) || createHash('sha256').update(readFileSync(candidate)).digest('hex') !== manifest.sha256) throw new Error('packaged shared-core artifact missing or digest mismatch');
  }
  if (!existsSync(candidate)) {
    throw new Error("shared Agentic Workspace core is unavailable; install a supported native package or set AGENTIC_WORKSPACE_CORE_BINARY");
  }
  return candidate;
};

export function runNativeCli(args) {
  const core = coreBinary();
  const binary = join(dirname(core), process.platform === "win32" ? "agentic-workspace.exe" : "agentic-workspace");
  const manifestPath = join(nativeDirectory(), "artifact.json");
  if (!existsSync(binary)) throw new Error("paired native CLI missing");
  if (existsSync(manifestPath)) {
    const manifest = JSON.parse(readFileSync(manifestPath, "utf8"));
    if (createHash("sha256").update(readFileSync(binary)).digest("hex") !== manifest.cli_sha256) throw new Error("paired native CLI digest mismatch");
  }
  const result = spawnSync(binary, args, {stdio: "inherit", windowsHide: true});
  if (result.error) throw result.error;
  return result.status ?? 1;
}

export function request(payload) {
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

