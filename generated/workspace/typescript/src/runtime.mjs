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
  if (keys.length === 1 && keys[0] === '$select_by_value') {
    const spec = template.$select_by_value;
    if (!isObject(spec) || !isObject(spec.choices)) throw new RuntimeError('template $select_by_value choices must be an object');
    let selectedKey = String(values[String(spec.value ?? '')] ?? spec.default ?? '');
    if (!Object.prototype.hasOwnProperty.call(spec.choices, selectedKey)) selectedKey = String(spec.default ?? '');
    if (!Object.prototype.hasOwnProperty.call(spec.choices, selectedKey)) throw new RuntimeError(`template $select_by_value cannot resolve choice for ${String(spec.value ?? '')}`);
    return resolveTemplate(spec.choices[selectedKey], values);
  }
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

function fieldByPath(root, dottedPath) {
  if (!dottedPath) return [false, null];
  let current = root;
  for (const part of String(dottedPath).split('.')) {
    if (isObject(current) && Object.prototype.hasOwnProperty.call(current, part)) {
      current = current[part];
      continue;
    }
    if (Array.isArray(current)) {
      const index = Number(part);
      if (Number.isInteger(index) && index >= 0 && index < current.length) {
        current = current[index];
        continue;
      }
    }
    return [false, null];
  }
  return [true, current];
}

function selectorTokens(value) {
  if (Array.isArray(value)) return value.map(String).map((item) => item.trim()).filter(Boolean);
  return String(value ?? '').split(',').map((item) => item.trim()).filter(Boolean);
}

function availableSelectorsForPayload(payload, prefix = '') {
  const selectors = [];
  if (isObject(payload)) {
    for (const key of Object.keys(payload).map(String).sort()) {
      const path = prefix ? `${prefix}.${key}` : key;
      selectors.push(path);
      selectors.push(...availableSelectorsForPayload(payload[key], path));
    }
  } else if (Array.isArray(payload)) {
    for (const [index, item] of payload.slice(0, 10).entries()) {
      const path = prefix ? `${prefix}.${index}` : String(index);
      selectors.push(path);
      selectors.push(...availableSelectorsForPayload(item, path));
    }
  }
  return selectors;
}

function projectPayload(values, args) {
  const sourceName = String(args.source ?? 'result');
  if (!Object.prototype.hasOwnProperty.call(values, sourceName)) throw new RuntimeError(`payload.project source value is missing: ${sourceName}`);
  const payload = values[sourceName];
  const selectValueName = String(args.select_value ?? 'select');
  const selectors = selectorTokens(args.selectors ?? values[selectValueName]);
  if (selectors.length === 0) return payload;
  const selected = {
    kind: String(args.selected_output_kind ?? 'command-generation/selected-output/v1'),
    source_command: String(args.source_command ?? values.operation_id ?? ''),
    values: {}
  };
  const missing = [];
  for (const selector of selectors) {
    const [found, value] = fieldByPath(payload, selector);
    if (found) selected.values[selector] = value;
    else missing.push(selector);
  }
  if (missing.length) {
    selected.missing = missing;
    selected.selector_rule = 'Comma-separated dot paths select exact JSON fields; unknown fields are reported in missing.';
    selected.available_selectors = availableSelectorsForPayload(payload);
  }
  return selected;
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
  if (fields.payload_kind === 'package-resource-manifest') {
    const manifestFrom = String(fields.manifest_from ?? 'manifest');
    const manifest = values[manifestFrom] ?? {};
    if (!isObject(manifest)) throw new RuntimeError(`${manifestFrom} must be an object`);
    const filesPath = String(fields.files_path ?? 'files');
    const bundledSkillsPath = String(fields.bundled_skill_files_path ?? 'bundled_skill_files');
    return {
      files: manifestPathList(dottedValue(manifest, filesPath) ?? [], `${manifestFrom}.${filesPath}`),
      default_files: stringList(fields.default_files ?? [], 'payload.assemble fields.default_files'),
      optional_files: stringList(fields.optional_files ?? [], 'payload.assemble fields.optional_files'),
      bundled_skill_files: manifestPathList(dottedValue(manifest, bundledSkillsPath) ?? [], `${manifestFrom}.${bundledSkillsPath}`),
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

function manifestPathList(value, source) {
  if (!Array.isArray(value)) throw new RuntimeError(`${source} must be a list`);
  return value.map((item) => {
    if (typeof item === 'string') return item;
    if (isObject(item) && typeof item.relative_path === 'string') return item.relative_path;
    if (isObject(item) && typeof item.path === 'string') return item.path;
    throw new RuntimeError(`${source} entries must be strings or objects with path`);
  });
}

function emitOutput(values, args = {}) {
  const result = values.result;
  if (String(values.format ?? 'text') === 'json') return `${JSON.stringify(result, null, 2)}
`;
  if (isObject(result)) {
    const declaredView = emitDeclaredTextView(result, args.text_views ?? []);
    if (declaredView !== null) return declaredView;
  }
  if (!isObject(result)) return `${result}
`;
  if (Array.isArray(result.files) && result.files.every((item) => typeof item === 'string')) return `${result.files.join('\n')}
`;
  const lines = [String(result.message ?? result.kind ?? '')];
  for (const action of (Array.isArray(result.actions) ? result.actions : [])) lines.push(`- ${action.path ?? action.id ?? action.kind}`);
  return `${lines.join('\n').trimEnd()}
`;
}

function emitDeclaredTextView(result, views) {
  if (views === null || views === undefined) return null;
  if (!Array.isArray(views)) throw new RuntimeError('output.emit text_views must be a list');
  for (const view of views) {
    if (!isObject(view)) throw new RuntimeError('output.emit text_views entries must be objects');
    validateDeclaredTextView(view);
  }
  let defaultView = null;
  for (const view of views) {
    if (view.default) defaultView = view;
    if (declaredTextViewMatches(result, view)) return renderDeclaredTextView(result, view);
  }
  return defaultView ? renderDeclaredTextView(result, defaultView) : null;
}

function declaredTextViewMatches(result, view) {
  const match = view.match ?? {};
  if (!isObject(match) || Object.keys(match).length === 0) return false;
  for (const [path, expected] of Object.entries(match)) {
    if (!declaredTextIsScalar(expected)) throw new RuntimeError('output.emit text view match values must be JSON scalars');
    const [found, actual] = fieldByPath(result, path);
    if (!found || !declaredTextScalarEqual(actual, expected)) return false;
  }
  return true;
}

function validateDeclaredTextView(view) {
  const match = view.match ?? {};
  if (Object.prototype.hasOwnProperty.call(view, 'match') && !isObject(match)) throw new RuntimeError('output.emit text view match must be an object');
  for (const expected of Object.values(match)) {
    if (!declaredTextIsScalar(expected)) throw new RuntimeError('output.emit text view match values must be JSON scalars');
  }
  if (Object.prototype.hasOwnProperty.call(view, 'lines')) validateDeclaredTextLines(view.lines);
}

function validateDeclaredTextLines(lines) {
  if (!Array.isArray(lines)) throw new RuntimeError('output.emit text view lines must be a list');
  for (const line of lines) validateDeclaredTextLine(line);
}

function validateDeclaredTextLine(line) {
  if (typeof line === 'string') return;
  if (!isObject(line)) throw new RuntimeError('output.emit text view lines must be strings or objects');
  const discriminators = ['when', 'for_each', 'json', 'template', 'literal'];
  const present = discriminators.filter((key) => Object.prototype.hasOwnProperty.call(line, key));
  if (present.length !== 1) throw new RuntimeError('output.emit text view line object must declare exactly one of when, for_each, json, template, or literal');
  const key = present[0];
  const keys = Object.keys(line).sort();
  if (key === 'literal') {
    if (keys.length !== 1 || keys[0] !== 'literal') throw new RuntimeError('output.emit literal line must only declare literal');
    return;
  }
  if (key === 'template') {
    if (keys.length !== 1 || keys[0] !== 'template') throw new RuntimeError('output.emit template line must only declare template');
    return;
  }
  if (key === 'json') {
    if (keys.length !== 1 || keys[0] !== 'json') throw new RuntimeError('output.emit json line must only declare json');
    return;
  }
  if (key === 'when') {
    if (keys.length !== 2 || keys[0] !== 'lines' || keys[1] !== 'when') throw new RuntimeError('output.emit when line must declare when and lines');
    validateDeclaredTextLines(line.lines);
    return;
  }
  const spec = line.for_each;
  if (!isObject(spec)) throw new RuntimeError('output.emit for_each line must be an object');
  if (!Object.prototype.hasOwnProperty.call(spec, 'path')) throw new RuntimeError('output.emit for_each line must declare path');
  const nestedForms = ['lines', 'template'].filter((name) => Object.prototype.hasOwnProperty.call(spec, name));
  if (nestedForms.length !== 1) throw new RuntimeError('output.emit for_each line must declare exactly one of lines or template');
  const specKeys = Object.keys(spec).sort();
  const expectedKeys = ['path', nestedForms[0]].sort();
  if (specKeys.length !== 2 || specKeys[0] !== expectedKeys[0] || specKeys[1] !== expectedKeys[1]) throw new RuntimeError('output.emit for_each line has unsupported fields');
  if (Object.prototype.hasOwnProperty.call(spec, 'lines')) validateDeclaredTextLines(spec.lines);
}

function renderDeclaredTextView(result, view) {
  return `${renderDeclaredTextLines(view.lines ?? [], result, result).join('\n').trimEnd()}
`;
}

function renderDeclaredTextLines(lines, current, root) {
  if (!Array.isArray(lines)) throw new RuntimeError('output.emit text view lines must be a list');
  return lines.flatMap((line) => renderDeclaredTextLine(line, current, root));
}

function renderDeclaredTextLine(line, current, root) {
  if (typeof line === 'string') return [renderDeclaredTextTemplate(line, current, root)];
  if (!isObject(line)) throw new RuntimeError('output.emit text view lines must be strings or objects');
  if (Object.prototype.hasOwnProperty.call(line, 'when')) {
    const [found, value] = declaredTextValue(line.when, current, root);
    return found && declaredTextTruthy(value) ? renderDeclaredTextLines(line.lines ?? [], current, root) : [];
  }
  if (Object.prototype.hasOwnProperty.call(line, 'for_each')) {
    const spec = line.for_each;
    if (!isObject(spec)) throw new RuntimeError('output.emit for_each line must be an object');
    const [found, value] = declaredTextValue(spec.path ?? '', current, root);
    if (!found || value === null || value === undefined || value === '') return [];
    if (!Array.isArray(value)) throw new RuntimeError('output.emit for_each path must resolve to a list');
    const nestedLines = spec.lines ?? [String(spec.template ?? '{}')];
    return value.flatMap((item) => renderDeclaredTextLines(nestedLines, item, root));
  }
  if (Object.prototype.hasOwnProperty.call(line, 'json')) {
    const [found, value] = declaredTextValue(line.json, current, root);
    return JSON.stringify(declaredTextCanonicalJsonValue(found ? value : null), null, 2).split('\n');
  }
  if (Object.prototype.hasOwnProperty.call(line, 'template')) return [renderDeclaredTextTemplate(String(line.template), current, root)];
  if (Object.prototype.hasOwnProperty.call(line, 'literal')) return [String(line.literal)];
  throw new RuntimeError('output.emit text view line object must declare when, for_each, json, template, or literal');
}

function renderDeclaredTextTemplate(template, current, root) {
  return String(template).replace(/\{([^}]*)\}/g, (_match, token) => {
    const [found, value] = declaredTextPlaceholderValue(String(token), current, root);
    return declaredTextFormat(found ? value : '');
  });
}

function declaredTextPlaceholderValue(token, current, root) {
  const parts = String(token).split('|');
  let [found, value] = declaredTextValue(parts[0], current, root);
  for (const rawFilter of parts.slice(1)) {
    const separatorIndex = rawFilter.indexOf(':');
    const name = separatorIndex === -1 ? rawFilter : rawFilter.slice(0, separatorIndex);
    const argument = separatorIndex === -1 ? '' : rawFilter.slice(separatorIndex + 1);
    if (name === 'len') {
      value = Array.isArray(value) ? value.length : 0;
      found = true;
    } else if (name === 'join') {
      if (!found || value === null || value === undefined) {
        value = '';
      } else if (Array.isArray(value)) {
        if (!value.every(declaredTextIsScalar)) throw new RuntimeError('output.emit join filter requires a list of JSON scalars');
        value = value.map(declaredTextFormatScalar).join(argument);
      } else {
        throw new RuntimeError('output.emit join filter requires a list');
      }
      found = true;
    } else if (name === 'empty') {
      if (!declaredTextTruthy(value)) value = argument;
      found = true;
    } else {
      throw new RuntimeError(`unsupported output.emit text view filter: ${name}`);
    }
  }
  return [found, value];
}

function declaredTextValue(path, current, root) {
  const pathText = String(path ?? '');
  if (pathText === '' || pathText === '.') return [true, current];
  if (pathText.startsWith('root.')) return fieldByPath(root, pathText.slice('root.'.length));
  if (isObject(current)) {
    const [found, value] = fieldByPath(current, pathText);
    if (found) return [true, value];
  }
  return fieldByPath(root, pathText);
}

function declaredTextTruthy(value) {
  if (value === null || value === undefined) return false;
  if (Array.isArray(value)) return value.length > 0;
  if (isObject(value)) return Object.keys(value).length > 0;
  if (typeof value === 'string') return value.length > 0;
  return Boolean(value);
}

function declaredTextFormat(value) {
  if (!declaredTextIsScalar(value)) throw new RuntimeError('output.emit text view placeholders require JSON scalars; use json lines for arrays or objects');
  return declaredTextFormatScalar(value);
}

function declaredTextIsScalar(value) {
  return value === null || value === undefined || ['string', 'boolean'].includes(typeof value) || declaredTextIsSafeInteger(value);
}

function declaredTextIsSafeInteger(value) {
  return typeof value === 'number' && Number.isSafeInteger(value);
}

function declaredTextScalarEqual(actual, expected) {
  if (expected === null || expected === undefined) return actual === null || actual === undefined;
  if (typeof expected === 'boolean') return typeof actual === 'boolean' && actual === expected;
  if (typeof expected === 'string') return typeof actual === 'string' && actual === expected;
  if (declaredTextIsSafeInteger(expected)) return declaredTextIsSafeInteger(actual) && actual === expected;
  return false;
}

function declaredTextFormatScalar(value) {
  if (typeof value === 'boolean') return value ? 'true' : 'false';
  if (value === null || value === undefined) return '';
  if (declaredTextIsSafeInteger(value)) return String(value);
  return String(value);
}

function declaredTextCanonicalJsonValue(value) {
  if (Array.isArray(value)) return value.map(declaredTextCanonicalJsonValue);
  if (isObject(value)) {
    const out = {};
    for (const key of Object.keys(value).sort()) out[key] = declaredTextCanonicalJsonValue(value[key]);
    return out;
  }
  if (value === null || value === undefined || ['string', 'boolean'].includes(typeof value)) return value;
  if (declaredTextIsSafeInteger(value)) return value;
  if (typeof value === 'number') throw new RuntimeError('output.emit text view JSON numbers must be finite safe integers');
  return value;
}

function limitedViewValue(value, limit) {
  if (!Number.isInteger(limit) || typeof value === 'string') return value;
  if (Array.isArray(value)) return value.slice(0, Math.max(limit, 0));
  return value;
}

function viewPayload(values, args) {
  const sourceName = String(args.source ?? 'result');
  if (!Object.prototype.hasOwnProperty.call(values, sourceName)) throw new RuntimeError(`payload.view source value is missing: ${sourceName}`);
  const fields = stringList(args.fields ?? [], 'payload.view fields');
  if (args.limits !== undefined && !isObject(args.limits)) throw new RuntimeError('payload.view limits must be an object');
  const limits = args.limits ?? {};
  const payload = values[sourceName];
  const viewed = {
    kind: String(args.view_kind ?? 'command-generation/payload-view/v1'),
    source_command: String(args.source_command ?? values.operation_id ?? ''),
    values: {}
  };
  const missing = [];
  for (const field of fields) {
    const [found, value] = fieldByPath(payload, field);
    if (found) viewed.values[field] = limitedViewValue(value, limits[field]);
    else missing.push(field);
  }
  if (missing.length) viewed.missing = missing;
  return viewed;
}

function transactionPlan(values, args) {
  const resourcesFrom = String(args.resources_from ?? 'resources');
  const rawResources = values[resourcesFrom] ?? args.resources ?? [];
  if (!Array.isArray(rawResources)) throw new RuntimeError('transaction.plan resources must be a list');
  const defaultAction = String(args.default_action ?? 'write');
  const defaultKind = String(args.default_kind ?? 'file');
  const actions = rawResources.map((item) => {
    if (typeof item === 'string') return { action: defaultAction, kind: defaultKind, path: validateResourcePath(item) };
    if (!isObject(item)) throw new RuntimeError('transaction.plan resources must be strings or objects');
    const rawPath = item.path ?? item.relative_path;
    if (typeof rawPath !== 'string' || !rawPath) throw new RuntimeError('transaction.plan resource path is required');
    return {
      action: String(item.action ?? defaultAction),
      kind: String(item.kind ?? defaultKind),
      path: validateResourcePath(rawPath)
    };
  });
  const targetRootValue = String(args.target_root_value ?? 'target_root');
  return {
    kind: String(args.plan_kind ?? 'command-generation/transaction-plan/v1'),
    dry_run: true,
    target_root: String(values[targetRootValue] ?? ''),
    schema_ref: String(args.schema_ref ?? ''),
    actions,
    mutation_safety: {
      apply_status: 'package-owned',
      apply_primitive: String(args.apply_primitive ?? ''),
      conflict_hooks: stringList(args.conflict_hooks ?? [], 'transaction.plan conflict_hooks'),
      provenance_hooks: stringList(args.provenance_hooks ?? [], 'transaction.plan provenance_hooks'),
      rule: 'Generic transaction planning is dry-run only; mutating apply remains an explicit package-domain primitive.'
    }
  };
}

function validateResourcePath(path) {
  const resourcePath = String(path).replace(/\\/g, '/');
  const parts = resourcePath.split('/');
  if (
    !resourcePath ||
    resourcePath.startsWith('/') ||
    /^[A-Za-z]:/.test(parts[0] ?? '') ||
    parts.some((part) => part === '' || part === '.' || part === '..')
  ) {
    throw new RuntimeError(`transaction.plan resource path must be relative and stay inside resources: ${path}`);
  }
  return resourcePath;
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
  if (primitive === 'path.target_root.resolve') {
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
  if (primitive === 'payload.view') return viewPayload(values, args);
  if (primitive === 'payload.project') return projectPayload(values, args);
  if (primitive === 'output.emit') return emitOutput(values, args);
  if (primitive === 'transaction.plan') return transactionPlan(values, args);
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
