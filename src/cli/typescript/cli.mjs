#!/usr/bin/env node
import { runNativeCli } from "./native/_transport.mjs";

async function run(args) {
  if (args.length === 0 || args.includes("--help")) {
    const status = runNativeCli(args);
    if (status === 0) {
      console.log("  npm adapter supports --format yaml with Node 22.12+ and yaml@2.9.1.");
    }
    return status;
  }
  const formatIndex = args.findIndex((arg, index) => index > 0 && (arg === "--format" || arg.startsWith("--format=")));
  const explicit = formatIndex >= 0;
  const split = explicit && args[formatIndex] === "--format";
  const format = explicit
    ? (split ? args[formatIndex + 1] : args[formatIndex].slice("--format=".length))
    : process.env.AGENTIC_WORKSPACE_OUTPUT_FORMAT;
  const interactive = !explicit && !format && args[0] !== "setup" && process.stdout.isTTY && process.stderr.isTTY;

  if (format === "json" && !explicit) return runNativeCli([...args, "--format", "json"]);
  if (format !== "yaml" && !interactive) {
    if (format && !explicit) throw new TypeError("AGENTIC_WORKSPACE_OUTPUT_FORMAT must be json or yaml");
    return runNativeCli(args);
  }

  // Load the renderer before running a command that may have effects.
  const { anchored, loadYaml, parseJSON } = await import("./native/_agent-yaml.mjs");
  let yaml;
  try {
    yaml = await loadYaml();
  } catch (error) {
    if (interactive) return runNativeCli(args);
    throw error;
  }
  const nativeArgs = [...args];
  if (!explicit) nativeArgs.push("--format", "json");
  else if (split) nativeArgs[formatIndex + 1] = "json";
  else nativeArgs[formatIndex] = "--format=json";

  const { status, stdout, stderr } = runNativeCli(nativeArgs, { capture: true });
  function write(stream, raw) {
    if (!raw) return;
    let output;
    try {
      output = anchored(parseJSON(raw), yaml);
    } catch {
      // Preserve native diagnostics and any effect receipt if rendering fails.
      output = raw;
    }
    stream.write(output);
  }
  write(process.stdout, stdout);
  write(process.stderr, stderr);
  return status;
}

try {
  process.exitCode = await run(process.argv.slice(2));
} catch (error) {
  console.error(error.message);
  process.exitCode = 2;
}
