// Generated native TypeScript operation runtime.
// Source: src/agentic_workspace/contracts/command_package_ir.json
// Host primitive support: src/agentic_workspace/contracts/typescript_primitive_support.mjs
// Regenerate with: uv run python scripts/generate/generate_command_packages.py
// DO NOT EDIT DIRECTLY.

import { existsSync, readFileSync, readdirSync, statSync, writeSync } from 'node:fs';
import { dirname, isAbsolute, join, relative, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { executeHostPrimitive as configuredHostPrimitive } from './hostPrimitiveSupport.mjs';


const resourcesRoot = resolve(dirname(fileURLToPath(import.meta.url)), '../resources');

class RuntimeError extends Error {}

function isObject(value) {
  return value !== null && typeof value === 'object' && !Array.isArray(value);
}

function readText(path) {
  return readFileSync(path, 'utf8');
}

function readJson(path) {
  return JSON.parse(readText(path));
}

function resolveInside(root, subpath) {
  const rootPath = resolve(root);
  const candidate = resolve(rootPath, String(subpath ?? ''));
  const rel = relative(rootPath, candidate);
  if (rel === '' || (!rel.startsWith('..') && !isAbsolute(rel))) return candidate;
  throw new RuntimeError(`path escapes primitive root: ${candidate}`);
}

function resourceRoot(name) {
  if (!name) return resourcesRoot;
  if (name.endsWith('.contracts') || name === '_contracts') return resolveInside(resourcesRoot, '_contracts');
  if (name.endsWith('.payload') || name.endsWith('.package-payload') || name === '_payload') return resolveInside(resourcesRoot, '_payload');
  if (name.endsWith('.skills') || name.endsWith('.package-skills') || name === '_skills') return resolveInside(resourcesRoot, '_skills');
  return resolveInside(resourcesRoot, name);
}

function valueRoot(args, values) {
  if (Object.prototype.hasOwnProperty.call(args, 'base_value')) {
    const key = String(args.base_value);
    if (!Object.prototype.hasOwnProperty.call(values, key)) throw new RuntimeError(`unknown primitive base value: ${key}`);
    return resolve(String(values[key]));
  }
  return resourceRoot(String(args.root ?? ''));
}

function listFiles(root, prefix = '') {
  const dir = resolveInside(root, prefix);
  if (!existsSync(dir)) return [];
  const out = [];
  for (const entry of readdirSync(dir, { withFileTypes: true })) {
    const child = join(prefix, entry.name);
    if (entry.isDirectory()) out.push(...listFiles(root, child));
    else if (entry.isFile()) out.push(child.replace(/\\/g, '/'));
  }
  return out.sort();
}

function globFiles(root, pattern) {
  if (!pattern || isAbsolute(pattern) || pattern.split(/[\/]+/).includes('..')) throw new RuntimeError(`unsupported filesystem.glob pattern: ${pattern}`);
  const normalized = String(pattern).replace(/\\/g, '/');
  const files = listFiles(root);
  if (normalized === '**/*') return files;
  if (normalized.endsWith('/**/*')) {
    const prefix = normalized.slice(0, -4);
    return files.filter((file) => file.startsWith(prefix));
  }
  if (normalized.startsWith('**/*.')) {
    const suffix = normalized.slice(4);
    return files.filter((file) => file.endsWith(suffix));
  }
  if (!normalized.includes('*')) return files.filter((file) => file === normalized);
  const escaped = normalized.replace(/[.+^${}()|[\]\\]/g, '\\$&').replace(/\*\*/g, '.*').replace(/\*/g, '[^/]*');
  const regex = new RegExp(`^${escaped}$`);
  return files.filter((file) => regex.test(file));
}

function conditionMatches(condition, values) {
  if (condition === undefined || condition === null || (isObject(condition) && Object.keys(condition).length === 0)) return true;
  if (!isObject(condition)) throw new RuntimeError('step when condition must be an object');
  const keys = Object.keys(condition);
  if (keys.length === 1 && keys[0] === 'all') return condition.all.every((item) => conditionMatches(item, values));
  if (keys.length === 1 && keys[0] === 'any') return condition.any.some((item) => conditionMatches(item, values));
  if (keys.length === 1 && keys[0] === 'not') return !conditionMatches(condition.not, values);
  const actual = values[String(condition.value ?? '')];
  if (Object.prototype.hasOwnProperty.call(condition, 'equals')) return actual === condition.equals;
  if (Object.prototype.hasOwnProperty.call(condition, 'present')) return (actual !== undefined && actual !== null) === Boolean(condition.present);
  throw new RuntimeError('step when condition must use all, any, not, equals, or present');
}

function storeStepResult(values, outputs, result) {
  if (result === undefined || result === null) return;
  const names = Array.isArray(outputs) ? outputs.map(String).filter(Boolean) : [];
  if (names.length === 0) values._last = result;
  else if (names.length === 1) values[names[0]] = result;
  else {
    if (!isObject(result)) throw new RuntimeError('multi-output primitive results must be objects');
    for (const name of names) {
      if (!Object.prototype.hasOwnProperty.call(result, name)) throw new RuntimeError(`primitive result missing declared output: ${name}`);
      values[name] = result[name];
    }
  }
}

function resolveTemplate(template, values) {
  if (Array.isArray(template)) return template.map((item) => resolveTemplate(item, values));
  if (!isObject(template)) return template;
  const keys = Object.keys(template);
  if (keys.length === 1 && keys[0] === '$value') return values[String(template.$value)];
  if (keys.length === 1 && keys[0] === '$count') return Array.isArray(values[String(template.$count)]) ? values[String(template.$count)].length : 0;
  return Object.fromEntries(Object.entries(template).map(([key, value]) => [key, resolveTemplate(value, values)]));
}

function dottedValue(root, dottedPath) {
  if (!dottedPath) return null;
  let current = root;
  for (const part of String(dottedPath).split('.')) {
    if (!isObject(current) || !Object.prototype.hasOwnProperty.call(current, part)) return null;
    current = current[part];
  }
  return current;
}

function assemblePayload(values, args) {
  const fields = args.fields ?? {};
  if (fields.template !== undefined) return resolveTemplate(fields.template, values);
  if (fields.payload_kind === 'package-file-list') {
    const filesFrom = String(fields.files_from ?? 'files');
    const bundledSkillsFrom = String(fields.bundled_skill_files_from ?? 'bundled_skill_files');
    return {
      files: relativePathList(values[filesFrom] ?? [], filesFrom),
      default_files: stringList(fields.default_files ?? [], 'payload.assemble fields.default_files'),
      optional_files: stringList(fields.optional_files ?? [], 'payload.assemble fields.optional_files'),
      bundled_skill_files: relativePathList(values[bundledSkillsFrom] ?? [], bundledSkillsFrom),
      optional_enable_commands: stringList(fields.optional_enable_commands ?? [], 'payload.assemble fields.optional_enable_commands')
    };
  }
  const payload = { dry_run: Boolean(fields.dry_run ?? true), message: String(fields.message ?? '') };
  if (values.target_root !== undefined) payload.target_root = String(values.target_root);
  if (fields.actions_from === 'files') {
    payload.actions = (values.files ?? []).map((item) => ({ kind: 'file', path: String(item.relative_path ?? '') }));
    return payload;
  }
  if (fields.actions_from === 'registry.skills') {
    payload.mode = String(fields.mode ?? 'skills');
    payload.bootstrap_version = dottedValue(values.registry ?? {}, String(fields.bootstrap_version_from ?? ''));
    payload.actions = (values.registry?.skills ?? []).filter(isObject).map((item) => ({ kind: 'skill', id: String(item.id ?? ''), path: String(item.path ?? '') }));
    return payload;
  }
  throw new RuntimeError(`unsupported payload.assemble actions_from: ${fields.actions_from}`);
}

function stringList(value, source) {
  if (!Array.isArray(value) || !value.every((item) => typeof item === 'string')) throw new RuntimeError(`${source} must be a list of strings`);
  return value;
}

function relativePathList(value, source) {
  if (!Array.isArray(value)) throw new RuntimeError(`${source} must be a list`);
  return value.map((item) => {
    if (typeof item === 'string') return item;
    if (isObject(item) && typeof item.relative_path === 'string') return item.relative_path;
    throw new RuntimeError(`${source} entries must be strings or objects with relative_path`);
  });
}

function emitOutput(values) {
  const result = values.result;
  if (String(values.format ?? 'text') === 'json') return `${JSON.stringify(result, null, 2)}
`;
  if (!isObject(result)) return `${result}
`;
  if (Array.isArray(result.files) && result.files.every((item) => typeof item === 'string')) return `${result.files.join('\n')}
`;
  const lines = [String(result.message ?? result.kind ?? '')];
  for (const action of (Array.isArray(result.actions) ? result.actions : [])) lines.push(`- ${action.path ?? action.id ?? action.kind}`);
  return `${lines.join('\n').trimEnd()}
`;
}

function executeHostPrimitive(primitive, values, args, operationId) {
  if (typeof configuredHostPrimitive === 'function') return configuredHostPrimitive(primitive, values, args, operationId);
  const hostPrimitive = globalThis.hostPrimitive;
  if (typeof hostPrimitive === 'function') return hostPrimitive(primitive, values, args, operationId);
  throw new RuntimeError(`unsupported native TypeScript primitive: ${primitive}`);
}

function executeHostDomainOperation(operationId, values) {
  if (typeof hostDomainOperation === 'function') return hostDomainOperation(operationId, values);
  throw new RuntimeError(`unsupported native TypeScript domain operation: ${operationId}`);
}

function executePrimitive(primitive, values, args, operationId) {
  if (primitive === 'typescript.domain.execute') return executeHostDomainOperation(String(args.operation_id ?? operationId), values);
  const rootResolvePrimitives = new Set(['path.target_root.resolve', ['workspace', 'root', 'resolve'].join('.')]);
  if (rootResolvePrimitives.has(primitive)) {
    const targetRoot = resolve(String(values.target ?? '.'));
    if (args.must_exist && !existsSync(targetRoot)) throw new RuntimeError(`target root does not exist: ${targetRoot}`);
    if (args.must_be_dir && (!existsSync(targetRoot) || !statSync(targetRoot).isDirectory())) throw new RuntimeError(`target root is not a directory: ${targetRoot}`);
    return targetRoot;
  }
  if (primitive === 'filesystem.exists') {
    const path = resolveInside(valueRoot(args, values), String(args.path ?? ''));
    if (args.kind === 'file') return existsSync(path) && statSync(path).isFile();
    if (args.kind === 'directory') return existsSync(path) && statSync(path).isDirectory();
    return existsSync(path);
  }
  if (primitive === 'filesystem.read') return readText(resolveInside(resourceRoot(String(args.root ?? '')), String(args.path ?? '')));
  if (primitive === 'filesystem.glob') return globFiles(valueRoot(args, values), String(args.pattern ?? '')).map((relative_path) => ({ relative_path }));
  if (primitive === 'json.parse') return JSON.parse(String(values[String(args.source ?? 'registry_text')]));
  if (primitive === 'payload.assemble') return assemblePayload(values, args);
  if (primitive === 'output.emit' || primitive === 'output.emit.install-result' || primitive === 'output.emit.current-memory') return emitOutput(values);
  return executeHostPrimitive(primitive, values, args, operationId);
}

function operationFragments(operation) {
  const rawFragments = operation?.ir_plan?.fragments ?? [];
  if (!Array.isArray(rawFragments)) throw new RuntimeError('operation ir_plan.fragments must be a list');
  const fragments = new Map();
  for (const fragment of rawFragments) {
    if (!isObject(fragment)) throw new RuntimeError('operation ir_plan fragment must be an object');
    const fragmentId = String(fragment.id ?? '').trim();
    if (!fragmentId) throw new RuntimeError('operation ir_plan fragment id is required');
    if (fragments.has(fragmentId)) throw new RuntimeError(`duplicate operation ir_plan fragment: ${fragmentId}`);
    if (!Array.isArray(fragment.steps) || fragment.steps.length === 0) {
      throw new RuntimeError(`operation ir_plan fragment ${fragmentId} must declare non-empty steps`);
    }
    fragments.set(fragmentId, fragment.steps);
  }
  return fragments;
}

function expandOperationSteps(steps, fragments, stack = []) {
  const expanded = [];
  for (const step of steps) {
    if (!isObject(step)) throw new RuntimeError('operation ir_plan step must be an object');
    const uses = String(step.uses ?? '').trim();
    const usesFragment = String(step.uses_fragment ?? '').trim();
    if (uses && usesFragment) throw new RuntimeError(`step ${String(step.id ?? uses)} cannot declare both uses and uses_fragment`);
    if (usesFragment) {
      if (step.arguments !== undefined && !(isObject(step.arguments) && Object.keys(step.arguments).length === 0)) {
        throw new RuntimeError(`fragment step ${String(step.id ?? usesFragment)} cannot declare arguments`);
      }
      if (step.outputs !== undefined && !(Array.isArray(step.outputs) && step.outputs.length === 0)) {
        throw new RuntimeError(`fragment step ${String(step.id ?? usesFragment)} cannot declare outputs`);
      }
      if (stack.includes(usesFragment)) throw new RuntimeError(`operation ir_plan fragment cycle: ${[...stack, usesFragment].join(' -> ')}`);
      if (!fragments.has(usesFragment)) throw new RuntimeError(`unknown operation ir_plan fragment: ${usesFragment}`);
      expanded.push(...expandOperationSteps(fragments.get(usesFragment), fragments, [...stack, usesFragment]));
      continue;
    }
    if (!uses) throw new RuntimeError(`step ${String(step.id ?? '<unknown>')} must declare uses or uses_fragment`);
    expanded.push(step);
  }
  return expanded;
}

function runSteps(operation, values) {
  const steps = operation?.ir_plan?.steps;
  if (!Array.isArray(steps) || steps.length === 0) throw new RuntimeError(`operation ${operation?.id ?? '<unknown>'} has no executable ir_plan.steps`);
  const fragments = operationFragments(operation);
  for (const step of expandOperationSteps(steps, fragments)) {
    if (!conditionMatches(step.when, values)) continue;
    const result = executePrimitive(String(step.uses ?? ''), values, isObject(step.arguments) ? step.arguments : {}, String(operation.id ?? ''));
    storeStepResult(values, step.outputs ?? [], result);
  }
  return values;
}

function executeGeneratedOperationValues({ operationId, operationPath, values }) {
  if (!operationId) throw new RuntimeError('generated command has no operation id');
  if (!operationPath) throw new RuntimeError(`operation ${operationId} has no operation resource path`);
  const resourcePath = resolveInside(resourcesRoot, operationPath);
  if (!existsSync(resourcePath)) throw new RuntimeError(`operation resource is missing: ${operationPath}`);
  const operation = readJson(resourcePath);
  return runSteps(operation, { ...values });
}

export function invokeGeneratedOperation({ operationId, operationPath, values }) {
  const finalValues = executeGeneratedOperationValues({ operationId, operationPath, values });
  return finalValues.result ?? finalValues.emitted ?? emitOutput({ ...finalValues, result: finalValues.result });
}

export function runGeneratedOperation({ operationId, operationPath, values }) {
  const finalValues = executeGeneratedOperationValues({ operationId, operationPath, values });
  let output = finalValues.emitted ?? emitOutput({ ...finalValues, result: finalValues.result });
  if (typeof output !== 'string') output = `${JSON.stringify(output, null, 2)}
`;
  writeSync(1, output);
  return 0;
}
