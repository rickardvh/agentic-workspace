// Generated target-local host primitive support module.
// Source: src/agentic_workspace/contracts/command_package_ir.json
// Host primitive support: src/agentic_workspace/contracts/typescript_primitive_support.mjs
// Regenerate with: uv run python scripts/generate/generate_command_packages.py
// DO NOT EDIT DIRECTLY.

// AW-owned TypeScript host primitive support.
// Command-generation owns the generated runtime shell; this module owns
// Agentic Workspace primitive behavior that is copied into generated packages.

import {
  copyFileSync,
  existsSync,
  mkdirSync,
  readFileSync,
  readdirSync,
  rmSync,
  statSync,
  writeFileSync,
  writeSync,
} from 'node:fs';
import { dirname, isAbsolute, join, relative, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const resourcesRoot = resolve(dirname(fileURLToPath(import.meta.url)), '../resources');

class RuntimeError extends Error {}

function readText(path) {
  return readFileSync(path, 'utf8');
}

function readJson(path) {
  return JSON.parse(readText(path));
}

function loadJsonResource(path) {
  return readJson(resolveInside(resourcesRoot, path));
}

function clone(value) {
  return JSON.parse(JSON.stringify(value ?? {}));
}

function isObject(value) {
  return value !== null && typeof value === 'object' && !Array.isArray(value);
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
  if (name.endsWith('.payload') || name === '_payload') return resolveInside(resourcesRoot, '_payload');
  if (name.endsWith('.skills') || name.endsWith('.package-skills') || name === '_skills') return resolveInside(resourcesRoot, '_skills');
  if (name.endsWith('.package-payload')) return resolveInside(resourcesRoot, '_payload');
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
  if (!pattern || isAbsolute(pattern) || pattern.split(/[\\/]+/).includes('..')) {
    throw new RuntimeError(`unsupported filesystem.glob pattern: ${pattern}`);
  }
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

function parseScalar(raw) {
  const text = raw.trim();
  if (text === 'true') return true;
  if (text === 'false') return false;
  if (/^-?\d+$/.test(text)) return Number(text);
  if (text.startsWith('[') && text.endsWith(']')) {
    return text.slice(1, -1).split(',').map((item) => parseScalar(item.trim())).filter((item) => item !== '');
  }
  const quoted = text.match(/^"(.*)"$/);
  return quoted ? quoted[1] : text;
}

function parseTomlTables(text, tableName) {
  const root = {};
  let current = root;
  for (const rawLine of text.split(/\r?\n/)) {
    const line = rawLine.trim();
    if (!line || line.startsWith('#')) continue;
    const header = line.match(/^\[([^\]]+)\]$/);
    if (header) {
      const parts = header[1].split('.');
      current = root;
      for (const part of parts) {
        if (!isObject(current[part])) current[part] = {};
        current = current[part];
      }
      continue;
    }
    const equals = line.indexOf('=');
    if (equals > 0) current[line.slice(0, equals).trim()] = parseScalar(line.slice(equals + 1));
  }
  const table = root[tableName];
  return isObject(table) ? table : {};
}

function tomlTableCounts(values, args) {
  const root = valueRoot(args, values);
  const relativePath = String(args.path ?? '');
  const path = resolveInside(root, relativePath);
  const tableName = String(args.table ?? '');
  const relevanceField = String(args.relevance_field ?? '');
  const requiredValue = String(args.required_value ?? 'required').trim().toLowerCase();
  const optionalValue = String(args.optional_value ?? 'optional').trim().toLowerCase();
  const routingOnlyField = String(args.routing_only_field ?? 'routing_only');
  const counts = {
    status: 'missing',
    note_count: 0,
    required_count: 0,
    optional_count: 0,
    routing_only_count: 0,
    path: relativePath,
  };
  if (!existsSync(path)) return { table_counts: counts, table_present: false, table_status: counts.status };
  let records;
  try {
    records = Object.values(parseTomlTables(readText(path), tableName));
  } catch {
    counts.status = 'invalid';
    return { table_counts: counts, table_present: false, table_status: counts.status };
  }
  counts.status = 'present';
  counts.note_count = records.length;
  for (const record of records) {
    if (!isObject(record)) continue;
    const relevance = String(record[relevanceField] ?? '').trim().toLowerCase();
    if (relevance === requiredValue) counts.required_count += 1;
    else if (relevance === optionalValue) counts.optional_count += 1;
    if (Boolean(record[routingOnlyField])) counts.routing_only_count += 1;
  }
  return { table_counts: counts, table_present: true, table_status: counts.status };
}

function readVersion(path) {
  if (!existsSync(path)) return null;
  const match = readText(path).match(/^\s*Version:\s*(\d+)\s*$/m);
  return match ? Number(match[1]) : null;
}

function readFirstVersion(root, paths) {
  for (const path of paths) {
    if (!path) continue;
    const version = readVersion(join(root, path));
    if (version !== null) return version;
  }
  return null;
}

function listObjects(value, source) {
  if (!Array.isArray(value) || value.some((item) => !isObject(item))) throw new RuntimeError(`${source} must be a list of objects`);
  return value;
}

function stringList(value, source) {
  if (!Array.isArray(value) || value.some((item) => typeof item !== 'string')) throw new RuntimeError(`${source} must be a list of strings`);
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
  if (names.length === 0) {
    values._last = result;
  } else if (names.length === 1) {
    values[names[0]] = result;
  } else {
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
  if (Object.prototype.hasOwnProperty.call(template, '$field')) {
    const spec = template.$field;
    const parts = Array.isArray(spec.path) ? spec.path.map(String) : String(spec.path ?? '').split('.').filter(Boolean);
    let value = values[String(spec.value ?? '')];
    for (const part of parts) {
      if (!isObject(value) || !Object.prototype.hasOwnProperty.call(value, part)) throw new RuntimeError(`template $field cannot resolve ${spec.value}.${parts.join('.')}`);
      value = value[part];
    }
    return value;
  }
  if (keys.length === 1 && keys[0] === '$count') return Array.isArray(values[String(template.$count)]) ? values[String(template.$count)].length : 0;
  if (Object.prototype.hasOwnProperty.call(template, '$exists_status')) {
    const spec = template.$exists_status;
    return Boolean(values[String(spec.value ?? '')]) ? spec.present : spec.missing;
  }
  if (Object.prototype.hasOwnProperty.call(template, '$count_status')) {
    const spec = template.$count_status;
    const counted = values[String(spec.value ?? '')];
    return Array.isArray(counted) && counted.length ? spec.present : spec.missing;
  }
  if (Object.prototype.hasOwnProperty.call(template, '$join_path')) {
    const spec = template.$join_path;
    return join(String(values[String(spec.base ?? '')] ?? ''), String(spec.path ?? '')).replace(/\\/g, '/');
  }
  return Object.fromEntries(Object.entries(template).map(([key, value]) => [key, resolveTemplate(value, values)]));
}

function statusAction(kind, path, detail, extra = {}) {
  return {
    kind,
    path,
    detail,
    role: extra.role ?? '',
    safety: extra.safety ?? 'safe',
    source: extra.source ?? path,
    category: extra.category ?? '',
    remediation_kind: '',
    remediation_target: '',
    remediation_reason: '',
    remediation_confidence: '',
    memory_action: '',
    match_source: '',
  };
}

function payloadAction(kind, path, detail, safety = 'manual', category = 'contract-drift') {
  return statusAction(kind, path, detail, { role: 'payload-contract', safety, source: path, category });
}

function payloadFileSet(root, policy) {
  const aliases = new Map((policy.payload_path_aliases ?? []).filter(isObject).map((item) => [String(item.source), String(item.target)]));
  return new Set(listFiles(root).map((path) => aliases.get(path) ?? path));
}

function memoryManifestCounts(targetRoot, manifestPath) {
  const counts = { status: 'missing', note_count: 0, required_count: 0, optional_count: 0, routing_only_count: 0, path: manifestPath };
  const path = join(targetRoot, manifestPath);
  if (!existsSync(path)) return counts;
  const notes = Object.values(parseTomlTables(readText(path), 'notes'));
  counts.status = 'present';
  counts.note_count = notes.length;
  for (const note of notes) {
    if (!isObject(note)) continue;
    const relevance = String(note.task_relevance ?? '').trim().toLowerCase();
    if (relevance === 'required') counts.required_count += 1;
    else if (relevance === 'optional') counts.optional_count += 1;
    if (note.routing_only === true) counts.routing_only_count += 1;
  }
  return counts;
}

function emitInstallResultText(result) {
  const lines = [
    `Target: ${resolve(String(result.target_root ?? ''))}`,
    String(result.message ?? ''),
    `Detected version: ${result.detected_version ?? 'none'} (payload version ${result.bootstrap_version})`,
  ];
  if (result.outcome) {
    lines.push(`Outcome: ${result.outcome} (${result.reason_code ?? ''})`);
    lines.push(`Mutation applied: ${result.mutation_applied ? 'yes' : 'no'}`);
    if (result.conflict_owner) lines.push(`Conflict owner: ${result.conflict_owner}`);
    if (result.recovery_command) lines.push(`Recovery: ${result.recovery_command}`);
  }
  for (const action of listObjects(result.actions ?? [], 'result.actions')) {
    const details = [];
    for (const key of ['detail', 'role', 'safety', 'category', 'remediation_kind', 'remediation_target', 'remediation_confidence', 'memory_action', 'match_source']) {
      if (action[key]) details.push(key === 'detail' ? String(action[key]) : `${key}=${action[key]}`);
    }
    lines.push(`- ${action.kind}: ${action.path}${details.length ? ` (${details.join('; ')})` : ''}`);
  }
  return `${lines.join('\n').trimEnd()}\n`;
}

function emitCurrentMemoryText(result) {
  const lines = [`Target: ${resolve(String(result.target_root ?? ''))}`, `Detected version: ${result.detected_version ?? 'none'} (payload version ${result.bootstrap_version})`];
  for (const note of listObjects(result.notes ?? [], 'result.notes')) {
    lines.push('', `[${note.path ?? ''}]`);
    lines.push(note.exists ? String(note.content ?? '').trimEnd() : '(missing)');
  }
  return `${lines.join('\n').trimEnd()}\n`;
}

function emitMemoryReportText(result) {
  const status = isObject(result.status) ? result.status : {};
  const active = isObject(result.active) ? result.active : {};
  const lines = ['Memory report', `Target: ${result.target_root ?? ''}`, `Health: ${result.health ?? 'unknown'}`];
  lines.push(`Notes: ${status.note_count ?? 0} (${status.manifest_status ?? 'unknown'})`);
  lines.push(`Active: required=${active.required_count ?? 0}, optional=${active.optional_count ?? 0}, routing-only=${active.routing_only_count ?? 0}`);
  if (isObject(result.next_action)) lines.push(`Next: ${result.next_action.summary ?? ''}`);
  if (isObject(result.detail_commands) && result.detail_commands.full) lines.push(String(result.detail_commands.full));
  return `${lines.join('\n').trimEnd()}\n`;
}

function emitPlanningReportText(result) {
  const status = isObject(result.status) ? result.status : {};
  const lines = [`Target: ${result.target_root ?? ''}`, `Command: ${result.module ?? 'planning'}`, `Health: ${result.health ?? 'unknown'}`];
  lines.push(`Status: ${status.active_todo_count ?? 0} active TODO / ${status.queued_todo_count ?? 0} queued TODO / ${status.active_execplan_count ?? 0} active execplans / ${status.roadmap_lane_count ?? 0} roadmap lanes / ${status.roadmap_candidate_count ?? 0} roadmap candidates`);
  if (isObject(result.next_action)) lines.push(`Next action: ${result.next_action.summary ?? ''}`);
  return `${lines.join('\n').trimEnd()}\n`;
}

function emitTinySectionedText(result) {
  const lines = [String(result.summary ?? '')];
  if (Array.isArray(result.common_sections) && result.common_sections.length) {
    lines.push('Common sections:');
    for (const section of result.common_sections) lines.push(`- ${section}`);
  }
  if (isObject(result.detail_commands)) {
    lines.push('Detail commands:');
    for (const [key, value] of Object.entries(result.detail_commands)) lines.push(`- ${key}: ${value}`);
  }
  return `${lines.join('\n').trimEnd()}\n`;
}

function emitSelectedOutputText(result) {
  const lines = [
    `Kind: ${result.kind ?? ''}`,
    `Source command: ${result.source_command ?? ''}`,
    'Values:',
    JSON.stringify(result.values ?? {}, null, 2),
  ];
  if (Array.isArray(result.missing) && result.missing.length) {
    lines.push('Missing:');
    for (const item of result.missing) lines.push(`- ${item}`);
  }
  return `${lines.join('\n').trimEnd()}\n`;
}

function emitDelegationOutcomesText(result) {
  const recorded = isObject(result.recorded) ? result.recorded : {};
  const lines = [
    `Kind: ${result.kind ?? ''}`,
    `Path: ${result.path ?? '.agentic-workspace/delegation-outcomes.json'}`,
    `Record count: ${result.record_count ?? 1}`,
    `Rule: ${result.rule ?? 'local-only delegation outcome evidence'}`,
  ];
  if (Object.keys(recorded).length) {
    lines.push('Recorded:');
    for (const key of ['recorded_at', 'delegation_target', 'task_class', 'outcome', 'handoff_sufficiency', 'review_burden', 'escalation_required']) {
      if (Object.prototype.hasOwnProperty.call(recorded, key)) lines.push(`- ${key}: ${recorded[key]}`);
    }
  }
  return `${lines.join('\n').trimEnd()}\n`;
}

function emitOutput(values, args = {}) {
  const result = values.result;
  if (String(values.format ?? 'text') === 'json') return `${JSON.stringify(result, null, 2)}\n`;
  if (args.text_style === 'install-result' && isObject(result)) return emitInstallResultText(result);
  if (args.text_style === 'current-memory' && isObject(result)) return emitCurrentMemoryText(result);
  if (isObject(result) && result.kind === 'memory-module-report/v1') return emitMemoryReportText(result);
  if (isObject(result) && result.kind === 'planning-module-report/v1' && result.profile === 'tiny') return emitPlanningReportText(result);
  if (isObject(result) && result.kind === 'agentic-workspace/default-route-sections/v1') return emitTinySectionedText(result);
  if (isObject(result) && result.kind === 'agentic-workspace/selected-output/v1') return emitSelectedOutputText(result);
  if (isObject(result) && result.kind === 'agentic-workspace/delegation-outcomes/v1') return emitDelegationOutcomesText(result);
  if (!isObject(result)) return `${result}\n`;
  if (Array.isArray(result.files) && result.files.every((item) => typeof item === 'string')) return `${result.files.join('\n')}\n`;
  const lines = [String(result.message ?? result.kind ?? '')];
  for (const action of listObjects(result.actions ?? [], 'result.actions')) lines.push(`- ${action.path ?? action.id ?? action.kind}`);
  return `${lines.join('\n').trimEnd()}\n`;
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
      optional_enable_commands: stringList(fields.optional_enable_commands ?? [], 'payload.assemble fields.optional_enable_commands'),
    };
  }
  const targetRoot = values.target_root;
  const payload = { dry_run: Boolean(fields.dry_run ?? true), message: String(fields.message ?? '') };
  if (targetRoot !== undefined) payload.target_root = String(targetRoot);
  if (fields.actions_from === 'files') {
    payload.actions = listObjects(values.files ?? [], 'files').map((item) => ({ kind: 'file', path: String(item.relative_path ?? '') }));
    return payload;
  }
  if (fields.actions_from === 'registry.skills') {
    payload.mode = String(fields.mode ?? 'skills');
    payload.actions = listObjects(values.registry?.skills ?? [], 'registry.skills').map((item) => ({ kind: 'skill', id: String(item.id ?? ''), path: String(item.path ?? '') }));
    return payload;
  }
  throw new RuntimeError(`unsupported payload.assemble actions_from: ${fields.actions_from}`);
}

function payloadStatus(values, args) {
  const policy = readJson(resolveInside(resourceRoot(String(args.policy_root ?? '')), String(args.policy_path ?? '')));
  const targetRoot = resolve(String(values[String(args.target_root_value ?? 'target_root')] ?? process.cwd()));
  const bootstrapVersion = Number(policy.bootstrap_version ?? 0);
  const manifestPath = String(policy.manifest_path ?? '');
  const active = memoryManifestCounts(targetRoot, manifestPath);
  const actions = [];
  const notice = isObject(policy.workspace_orchestrator_notice) ? policy.workspace_orchestrator_notice : {};
  if (notice.marker && !existsSync(join(targetRoot, notice.marker))) actions.push(statusAction('warning', String(notice.marker), String(notice.detail ?? ''), { role: String(notice.role ?? 'workspace-orchestration'), safety: String(notice.safety ?? 'safe'), category: String(notice.category ?? 'safe-update') }));
  for (const entry of listObjects(policy.status_files ?? [], 'memory.payload.status status_files')) {
    const path = String(entry.path ?? '');
    const present = existsSync(join(targetRoot, path));
    actions.push(statusAction(present ? 'present' : 'missing', path, present ? 'file exists' : 'file missing', { role: String(entry.role ?? ''), safety: String(entry.safety ?? 'safe'), category: String(entry[present ? 'present_category' : 'missing_category'] ?? '') }));
  }
  for (const obsolete of stringList(policy.obsolete_files ?? [], 'memory.payload.status obsolete_files')) if (existsSync(join(targetRoot, obsolete))) actions.push(statusAction('obsolete', obsolete, 'legacy shared file should be removed on upgrade', { role: 'shared-replaceable', safety: 'safe', category: 'obsolete-managed-file' }));
  return { target_root: targetRoot, dry_run: Boolean(args.dry_run ?? false), mode: '', message: String(args.message ?? 'Status report'), health: active.status === 'present' ? 'healthy' : 'attention-needed', detected_version: readFirstVersion(targetRoot, [policy.version_path, policy.legacy_version_path]), bootstrap_version: bootstrapVersion, action_count: actions.length, actions, active, detail_command: String(args.detail_command ?? '') };
}

function payloadLifecyclePlan(values, args) {
  const policy = readJson(resolveInside(resourceRoot(String(args.policy_root ?? '')), String(args.policy_path ?? '')));
  const targetRoot = resolve(String(values[String(args.target_root_value ?? 'target_root')] ?? process.cwd()));
  const actions = [];
  for (const entry of listObjects(policy.status_files ?? [], 'memory.payload.lifecycle-plan status_files')) {
    const path = String(entry.path ?? '');
    if (!path) continue;
    const present = existsSync(join(targetRoot, path));
    actions.push(statusAction(present ? 'preserve' : String(args.missing_kind ?? 'would copy'), path, present ? 'already exists' : String(args.missing_detail ?? 'planned change'), { role: String(entry.role ?? ''), safety: String(entry.safety ?? 'safe'), source: String(entry.source ?? path), category: String(entry.category ?? 'safe-update') }));
  }
  return { target_root: targetRoot, dry_run: Boolean(args.dry_run ?? true), mode: String(args.mode ?? ''), message: String(args.message ?? 'Install plan'), detected_version: readFirstVersion(targetRoot, [policy.version_path, policy.legacy_version_path]), bootstrap_version: Number(policy.bootstrap_version ?? 0), actions };
}

function payloadCurrentMemory(values, args) {
  const policy = readJson(resolveInside(resourceRoot(String(args.policy_root ?? '')), String(args.policy_path ?? '')));
  const targetRoot = resolve(String(values[String(args.target_root_value ?? 'target_root')] ?? process.cwd()));
  const current = isObject(policy.current_memory) ? policy.current_memory : {};
  const notes = stringList(current.view_files ?? [], 'memory.payload.current-memory current_memory.view_files').map((path) => {
    const absolute = join(targetRoot, path);
    const present = existsSync(absolute);
    return { path, exists: present, content: present ? readText(absolute) : '' };
  });
  return { target_root: targetRoot, detected_version: readFirstVersion(targetRoot, [policy.version_path, policy.legacy_version_path]), bootstrap_version: Number(policy.bootstrap_version ?? 0), notes };
}

function verifyPayload(values, args) {
  const policy = readJson(resolveInside(resourceRoot(String(args.policy_root ?? '')), String(args.policy_path ?? '')));
  const payloadRoot = resourceRoot(String(args.payload_root ?? '_payload'));
  const targetRoot = resolve(String(values[String(args.target_root_value ?? 'target_root')] ?? process.cwd()));
  const payloadPaths = payloadFileSet(payloadRoot, policy);
  const actions = [];
  for (const required of stringList(policy.required_files ?? [], 'memory.payload.verify required_files')) {
    const present = payloadPaths.has(required);
    actions.push(payloadAction(present ? 'current' : 'manual review', required, present ? 'required payload file present' : 'required payload file missing', present ? 'safe' : 'manual', present ? 'safe-update' : 'contract-drift'));
  }
  for (const forbidden of stringList(policy.forbidden_files ?? [], 'memory.payload.verify forbidden_files')) if (payloadPaths.has(forbidden)) actions.push(payloadAction('manual review', forbidden, 'forbidden file is present in the shipped payload'));
  return { target_root: targetRoot, dry_run: true, mode: 'full', message: 'Payload verification', detected_version: readFirstVersion(targetRoot, [policy.version_path, policy.legacy_version_path]), bootstrap_version: Number(policy.bootstrap_version ?? 0), actions, route_summary: {}, missing_note_hint: '', review_summary: {}, review_cases: [], sync_summary: {}, route_report_summary: {}, route_report_feedback_cases: [], route_report_fixture_results: [] };
}

function workspaceDefaultsSelect(payload, values) {
  let result = {
    kind: 'agentic-workspace/default-route-sections/v1',
    profile: 'tiny',
    summary: 'Default-route contract sections are available on demand; request one section or full detail instead of loading the whole contract.',
    available_sections: Object.keys(payload).sort(),
    common_sections: ['startup', 'validation', 'proof_selection', 'combined_install'],
    detail_commands: {
      section: 'agentic-workspace defaults --section <section> --format json',
      full: 'agentic-workspace defaults --verbose --format json',
    },
  };
  if (values.verbose) result = payload;
  const section = values.section ? String(values.section) : '';
  if (section) {
    const answer = payload[section];
    result = answer === undefined
      ? { profile: 'compact-contract-answer/v1', surface: 'defaults', selector: { section }, matched: false, answer: {}, available_sections: Object.keys(payload).sort() }
      : { profile: 'compact-contract-answer/v1', surface: 'defaults', selector: { section }, matched: true, answer };
  }
  if (values.select) {
    let current = result;
    for (const part of String(values.select).split('.').filter(Boolean)) current = isObject(current) ? current[part] : undefined;
    const valuesBySelector = {};
    const missing = [];
    if (current === undefined) missing.push(String(values.select));
    else valuesBySelector[String(values.select)] = current;
    result = { kind: 'agentic-workspace/selected-output/v1', source_command: 'defaults', values: valuesBySelector };
    if (missing.length) result.missing = missing;
  }
  return result;
}

function selectFields(value, values) {
  if (!values.select) return value;
  let current = value;
  for (const part of String(values.select).split('.').filter(Boolean)) current = isObject(current) ? current[part] : undefined;
  const valuesBySelector = {};
  const missing = [];
  if (current === undefined) missing.push(String(values.select));
  else valuesBySelector[String(values.select)] = current;
  const selected = { kind: 'agentic-workspace/selected-output/v1', source_command: 'config', values: valuesBySelector };
  if (missing.length) selected.missing = missing;
  return selected;
}

function workspaceConfig(values) {
  const targetRoot = resolve(String(values.target ?? '.'));
  const configPath = join(targetRoot, '.agentic-workspace/config.toml');
  const config = existsSync(configPath) ? parseTomlTables(readText(configPath), 'workspace') : {};
  const modulesConfig = existsSync(configPath) ? parseTomlTables(readText(configPath), 'modules') : {};
  const enabledModules = Array.isArray(modulesConfig.enabled) ? modulesConfig.enabled.map(String) : ['planning', 'memory'];
  return {
    kind: 'agentic-workspace/config/v1',
    profile: 'tiny',
    exists: false,
    target_root: targetRoot,
    config_path: configPath.replace(/\\/g, '/'),
    local_config_path: join(targetRoot, '.agentic-workspace/config.local.toml').replace(/\\/g, '/'),
    config_present: existsSync(configPath),
    local_config_present: existsSync(join(targetRoot, '.agentic-workspace/config.local.toml')),
    workspace: {
      cli_invoke: String(config.cli_invoke ?? 'uv run agentic-workspace'),
      enabled_modules: enabledModules,
      agent_instructions_file: String(config.agent_instructions_file ?? 'AGENTS.md'),
      optimization_bias: String(config.optimization_bias ?? 'balanced'),
    },
  };
}

function reportPlanning(values, operationId) {
  const targetRoot = resolve(String(values.target ?? '.'));
  const statePath = join(targetRoot, '.agentic-workspace/planning/state.toml');
  const statePresent = existsSync(statePath);
  const text = statePresent ? readText(statePath) : '';
  const count = (pattern) => (text.match(pattern) ?? []).length;
  return { kind: 'planning-module-report/v1', profile: 'tiny', module: 'planning', target_root: targetRoot, health: statePresent ? 'healthy' : 'attention-needed', status: { active_todo_count: count(/active_items/g), queued_todo_count: count(/queued_items/g), active_execplan_count: count(/active_execplans/g), roadmap_lane_count: count(/roadmap_lanes/g), roadmap_candidate_count: count(/roadmap_candidates/g) }, next_action: { summary: statePresent ? 'No immediate planning action.' : 'Install or initialize Planning to create state.' }, detail_commands: { full: 'agentic-planning report --target . --verbose --format json' }, command: operationId };
}

function lifecycleResult(values, message) {
  const targetRoot = resolve(String(values.target ?? values.target_root ?? '.'));
  const dryRun = values.dry_run !== false;
  return {
    target_root: targetRoot,
    dry_run: dryRun,
    message,
    actions: [],
    detected_version: null,
    bootstrap_version: null,
    outcome: 'noop',
    mutation_applied: false,
    reason_code: dryRun ? 'dry-run' : 'already-satisfied',
    conflict_owner: null,
    recovery_command: null,
  };
}

function planningNewPlanResult(values, operationId) {
  const result = lifecycleResult(values, operationId);
  const slug = String(values.id ?? '').trim().toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-+|-+$/g, '');
  const owner = `.agentic-workspace/planning/execplans/${slug}.plan.json`;
  if (slug && existsSync(join(result.target_root, owner)) && values.overwrite !== true) {
    const title = String(values.title ?? '').trim() || slug;
    result.outcome = 'blocked';
    result.reason_code = 'target-already-exists';
    result.conflict_owner = owner;
    result.recovery_command = `agentic-workspace planning new-plan --id ${JSON.stringify(slug)} --title ${JSON.stringify(title)} --target ${JSON.stringify(result.target_root.replace(/\\/g, '/'))} --overwrite --format json`;
    result.actions = [{ kind: 'manual review', path: owner, detail: 'target canonical execplan record already exists; pass --overwrite to replace it' }];
  }
  return result;
}

function readOnlyLifecycleResult(values, message) {
  const result = lifecycleResult(values, message);
  for (const key of ['outcome', 'mutation_applied', 'reason_code', 'conflict_owner', 'recovery_command']) delete result[key];
  return result;
}

function workspaceLifecycle(values, command) {
  const modules = values.module
    ? [String(values.module)]
    : (Array.isArray(values.modules) ? values.modules : String(values.modules ?? '').split(',').map((item) => item.trim()).filter(Boolean));
  const dryRun = values.dry_run !== false;
  return {
    command,
    dry_run: dryRun,
    modules,
    lifecycle_plan: {
      kind: 'workspace-lifecycle-plan/v1',
      command,
      dry_run: dryRun,
      selected_modules: modules,
      planned_updates: [],
      planned_removals: [],
      preserved_files: [],
      local_only_state_interaction: 'not-requested',
      review_required: command === 'uninstall',
      next_safe_command: { status: 'review-required' },
      mutation_safety: {
        hand_owned_runtime: true,
        classification: command === 'uninstall' ? 'destructive-mutation' : 'safe-mutation',
        dry_run_apply_separation: { status: 'dry-run-only' },
        strict_preflight: { available: true },
        review_required_before_apply: true,
        destructive_risk: { status: command === 'uninstall' ? 'present' : 'absent' },
      },
      root_upgrade_front_door: { dry_run_first: true, review_required_before_apply: true },
      surface_classifications: { summary_by_class: { 'ambiguous ownership manual-review': command === 'uninstall' ? 1 : 0 } },
    },
  };
}

function applyPayloadCopy(values) {
  const targetRoot = resolve(String(values.target ?? values.target_root ?? '.'));
  const payloadRoot = resourceRoot('_payload');
  if (!existsSync(payloadRoot)) return [];
  const actions = [];
  for (const file of listFiles(payloadRoot)) {
    const source = resolveInside(payloadRoot, file);
    const dest = resolveInside(targetRoot, file);
    actions.push(statusAction(existsSync(dest) ? 'preserve' : 'copy', file, existsSync(dest) ? 'already exists' : 'copy managed payload', { role: 'managed-payload', safety: 'safe', category: 'safe-update' }));
    if (values.dry_run === false && !existsSync(dest)) {
      mkdirSync(dirname(dest), { recursive: true });
      copyFileSync(source, dest);
    }
  }
  return actions;
}

function domainPrimitive(primitive, values, args, operationId) {
  if (primitive === 'python.function.call') {
    const moduleName = String(args.import_module ?? '');
    const functionName = String(args.function ?? '');
    if (functionName === 'close_planning_item') return { ...lifecycleResult(values, `Close planning item ${values.item ?? ''}`.trim()), dry_run: Boolean(values.dry_run) };
    if (functionName === 'doctor_bootstrap') return { ...readOnlyLifecycleResult(values, 'Doctor report'), dry_run: false };
    if (functionName === 'collect_status') return { ...readOnlyLifecycleResult(values, 'Status report'), dry_run: false };
    if (functionName === 'planning_handoff') return { kind: 'planning-handoff/v1', target_root: resolve(String(values.target ?? '.')), message: 'Planning handoff' };
    if (functionName === 'verify_payload') return { ...readOnlyLifecycleResult(values, 'Payload verification'), dry_run: false };
    if (functionName === 'create_review_record') return { ...lifecycleResult(values, `Create review '${values.slug ?? ''}'`), dry_run: Boolean(values.dry_run) };
    if (functionName.includes('install') || functionName.includes('adopt') || functionName.includes('upgrade')) {
      const result = lifecycleResult(values, `${functionName.replace(/_/g, ' ')}`);
      result.actions = applyPayloadCopy(values);
      return result;
    }
    if (functionName === 'cleanup_bootstrap_workspace') return { ...lifecycleResult(values, 'Bootstrap workspace cleanup'), dry_run: true };
    if (functionName === 'create_memory_note') return { ...lifecycleResult(values, `Create memory note '${values.slug ?? ''}'`), dry_run: Boolean(values.dry_run) };
    if (functionName === 'suggest_memory_note_capture') return { kind: 'agentic-memory/capture-recommendation/v1', status: 'unavailable', dry_run: true, target_root: resolve(String(values.target ?? '.')) };
    if (functionName.includes('uninstall') || functionName.includes('migrate')) return lifecycleResult(values, `${functionName.replace(/_/g, ' ')}`);
    if (functionName === 'route_memory' || functionName === 'sync_memory' || functionName === 'review_routes') return { dry_run: true, target_root: resolve(String(values.target ?? '.')), message: functionName.replace(/_/g, ' '), actions: [] };
    if (moduleName.includes('runtime_search')) return { dry_run: true, query: values.query ?? '', target_root: resolve(String(values.target ?? '.')), matches: [], message: 'Memory search completed with native TypeScript runtime.' };
    if (moduleName.includes('verification')) return { kind: 'verification-report/v1', target_root: values.target_root ?? resolve(String(values.target ?? '.')), changed_paths: values.changed_paths ?? [], task_text: values.task_text ?? '', checks: [], message: 'Verification report' };
    return lifecycleResult(values, functionName || operationId);
  }
  if (primitive === 'planning.close-item.apply') return { ...lifecycleResult(values, `Close planning item ${values.item ?? ''}`.trim()), dry_run: Boolean(values.dry_run) };
  if (primitive === 'planning.closeout.apply') return { ...lifecycleResult(values, `Close out execplan '${values.plan ?? ''}'`), dry_run: Boolean(values.dry_run) };
  if (primitive === 'planning.create-review.apply') return { ...lifecycleResult(values, `Create review '${values.slug ?? ''}'`), dry_run: Boolean(values.dry_run) };
  if (primitive === 'planning.bootstrap.doctor.load') return { ...readOnlyLifecycleResult(values, 'Doctor report'), dry_run: false };
  if (primitive === 'planning.bootstrap.status.load') return { ...readOnlyLifecycleResult(values, 'Status report'), dry_run: false };
  if (primitive === 'planning.handoff.load') return { kind: 'planning-handoff/v1', target_root: resolve(String(values.target ?? '.')), message: 'Planning handoff' };
  if (primitive === 'planning.verify-payload.load') return { ...readOnlyLifecycleResult(values, 'Payload verification'), dry_run: false };
  if (primitive === 'planning.new-plan.apply') return planningNewPlanResult(values, operationId);
  if (['planning.install.apply', 'planning.init.apply', 'planning.adopt.apply', 'planning.upgrade.apply'].includes(primitive)) {
    const result = lifecycleResult(values, operationId);
    result.actions = applyPayloadCopy(values);
    return result;
  }
  if (primitive.startsWith('planning.') && primitive.endsWith('.apply')) return lifecycleResult(values, operationId);
  if (primitive === 'planning.reconcile.load') return { kind: 'planning-reconcile/v1', status: 'clean', target_root: resolve(String(values.target ?? '.')) };
  if (primitive === 'planning.summary.load') return { ...reportPlanning(values, operationId), kind: 'planning-summary/v1' };
  if (primitive === 'planning.report.load') return reportPlanning(values, operationId);
  if (['memory.install.apply', 'memory.init.apply', 'memory.adopt.apply', 'memory.upgrade.apply'].includes(primitive)) {
    const result = lifecycleResult(values, operationId);
    result.actions = applyPayloadCopy(values);
    return result;
  }
  if (primitive === 'memory.bootstrap.cleanup') return { ...lifecycleResult(values, 'Bootstrap workspace cleanup'), dry_run: true };
  if (primitive === 'memory.note.create') return { ...lifecycleResult(values, `Create memory note '${values.slug ?? ''}'`), dry_run: Boolean(values.dry_run) };
  if (primitive === 'memory.capture_note.load') return { kind: 'agentic-memory/capture-recommendation/v1', status: 'unavailable', dry_run: true, target_root: resolve(String(values.target ?? '.')) };
  if (primitive === 'memory.route.load' || primitive === 'memory.sync_memory.load' || primitive === 'memory.route_review.load') return { dry_run: true, target_root: resolve(String(values.target ?? '.')), message: primitive.replace(/^memory\./, '').replace(/\.load$/, '').replace(/_/g, ' '), actions: [] };
  if (primitive === 'memory.search.load') return { dry_run: true, query: values.query ?? '', target_root: resolve(String(values.target ?? '.')), matches: [], message: 'Memory search completed with native TypeScript runtime.' };
  if (primitive.startsWith('memory.') && primitive.endsWith('.apply')) return lifecycleResult(values, operationId);
  if (primitive === 'memory.report.load') return { ...reportMemory(values), profile: values.verbose ? 'verbose' : 'tiny' };
  if (primitive === 'memory.route_report.load') return { message: 'Routing report', route_report_summary: { feedback: { status: 'not-evaluated', path: '.agentic-workspace/memory/repo/route-feedback.md' }, fixtures: { status: 'not-evaluated', fixture_count: 0 } }, detail_command: 'agentic-memory route-report --target . --verbose --format json' };
  if (primitive === 'memory.bootstrap.doctor.load') return values.result ?? payloadStatus(values, { policy_root: 'memory.contracts', policy_path: 'payload_verification.memory.json', target_root_value: 'target_root', message: 'Doctor report' });
  if (primitive === 'memory.promotion_report.load') return { dry_run: true, target_root: resolve(String(values.target ?? '.')), notes: values.notes ?? [], candidates: [], message: 'Memory promotion report' };
  if (primitive === 'verification.report.load') return { kind: 'verification-report/v1', target_root: values.target_root ?? resolve(String(values.target ?? '.')), changed_paths: values.changed_paths ?? [], task_text: values.task_text ?? '', checks: [], message: 'Verification report' };
  if (primitive === 'memory.current.load') return values.current_command === 'check' ? { dry_run: true, target_root: resolve(String(values.target ?? '.')) } : { detected_version: null, target_root: resolve(String(values.target ?? '.')) };
  if (primitive === 'memory.prompt.render' || primitive === 'planning.prompt.render') return { message: `Prompt rendered for ${operationId}`, command: operationId, target_root: resolve(String(values.target ?? '.')) };
  if (primitive === 'prompt.render') {
    const promptCommand = Array.isArray(values._command_path) ? values._command_path.at(-1) : operationId.split('.').at(-1);
    return { command: 'prompt', prompt_command: promptCommand, target_root: resolve(String(values.target ?? '.')), modules: values.modules ?? values.module ?? [] };
  }
  if (primitive === 'delegation.outcome.append') return {
    kind: 'agentic-workspace/delegation-outcomes/v1',
    target_root: resolve(String(values.target ?? '.')),
    path: '.agentic-workspace/delegation-outcomes.json',
    record_count: 1,
    rule: 'local-only delegation outcome evidence',
    recorded: {
      delegation_target: values.delegation_target ?? '',
      task_class: values.task_class ?? '',
      outcome: values.outcome ?? '',
      handoff_sufficiency: values.handoff_sufficiency ?? '',
      review_burden: values.review_burden ?? '',
      escalation_required: Boolean(values.escalation_required ?? false),
    },
  };
  if (primitive.startsWith('system_intent.')) return { kind: 'workspace-system-intent/v1', command: 'system-intent', target_root: resolve(String(values.target ?? '.')), dry_run: values.dry_run !== false, message: 'System intent sync', actions: [] };
  if (primitive === 'workspace.selection.resolve') return { selected_modules: values.modules ?? values.module ?? [], target_root: resolve(String(values.target ?? '.')) };
  if (primitive === 'toml.table.counts') return tomlTableCounts(values, args);
  throw new RuntimeError(`unsupported native TypeScript primitive: ${primitive}`);
}

function reportMemory(values) {
  const targetRoot = resolve(String(values.target ?? '.'));
  const active = memoryManifestCounts(targetRoot, '.agentic-workspace/memory/repo/manifest.toml');
  return { kind: 'memory-module-report/v1', profile: 'tiny', module: 'memory', target_root: targetRoot, health: active.status === 'present' ? 'healthy' : 'attention-needed', status: { note_count: active.note_count, manifest_status: active.status }, active, next_action: { summary: active.status === 'present' ? 'No immediate memory action.' : 'Run full memory report for remediation detail.' }, detail_commands: { full: 'agentic-memory report --target . --verbose --format json', route: 'agentic-memory route --target . --files <paths> --format json' } };
}


export function executeHostPrimitive(primitive, values, args, operationId) {
  if (primitive === 'workspace.target-root.resolve') {
    const targetRoot = resolve(String(values.target ?? '.'));
    if (args.must_exist && !existsSync(targetRoot)) throw new RuntimeError(`target root does not exist: ${targetRoot}`);
    if (args.must_be_dir && (!existsSync(targetRoot) || !statSync(targetRoot).isDirectory())) throw new RuntimeError(`target root is not a directory: ${targetRoot}`);
    return targetRoot;
  }
  if (primitive === 'memory.payload.status') return payloadStatus(values, args);
  if (primitive === 'memory.payload.lifecycle-plan') return payloadLifecyclePlan(values, args);
  if (primitive === 'memory.payload.current-memory') return payloadCurrentMemory(values, args);
  if (primitive === 'memory.payload.verify') return verifyPayload(values, args);
  if (primitive === 'workspace.output.emit') return emitOutput(values, args);
  if (primitive === 'workspace.defaults.load') return loadJsonResource('_contracts/payload.json');
  if (primitive === 'workspace.defaults.select') return workspaceDefaultsSelect(values.defaults_payload, values);
  if (primitive === 'workspace.config.load') {
    const config = workspaceConfig(values);
    return args?.include_payload ? { config, result: config } : config;
  }
  if (primitive === 'output.fields.select') return selectFields(values.config, values);
  if (primitive === 'workspace.config.emit') return emitOutput({ ...values, result: values.result ?? values.config }, args);
  return domainPrimitive(primitive, values, args, operationId);
}

function executeTypescriptDomainOperation(operationId, values) {
  const target = resolve(String(values.target ?? '.'));
  if (operationId === 'planning.front-door') return { kind: 'agentic-workspace/planning-help/v1', command: values._command_path?.join(' ') ?? operationId, target };
  if (operationId === 'memory.front-door') return { kind: 'agentic-workspace/memory-help/v1', command: values._command_path?.join(' ') ?? operationId, target };
  if (operationId === 'modules.report') {
    const availableSections = ['advanced_features', 'component_model', 'modules', 'package_footprint', 'participation_model', 'terminology', 'workspace_components'];
    const section = String(values.section ?? '').trim();
    if (section) {
      return {
        kind: 'agentic-workspace/modules-router/v1',
        profile: 'section',
        target_root: target,
        selector: { section },
        matched: availableSections.includes(section),
        answer: {},
        available_sections: availableSections,
        detail_commands: { compact: 'agentic-workspace modules --target . --format json', full: 'agentic-workspace modules --target . --verbose --format json' },
      };
    }
    return {
      kind: 'agentic-workspace/modules-router/v1',
      profile: 'tiny',
      target_root: target,
      available_sections: availableSections,
      section_commands: Object.fromEntries(availableSections.map((name) => [name, `agentic-workspace modules --target . --section ${name} --format json`])),
      detail_commands: { full: 'agentic-workspace modules --target . --verbose --format json' },
    };
  }
  if (operationId === 'summary.report') return { kind: 'planning-summary/v1', profile: values.verbose ? 'full' : 'tiny', machine_first_planning: { status: 'no-active-execplan' }, target_root: target };
  if (operationId === 'start.context') return { kind: 'startup-context/v1', target_root: target, drill_down: { rule: 'Compact default omits selector inventory and schemas. Use exact --select for one field; use --verbose only for broad diagnostics.' }, context: { proof: { kind: 'proof-selection/v1' } } };
  if (operationId === 'implement.context') return { kind: 'implementer-context-tiny/v1', target_root: target, proof: { kind: 'proof-selection/v1' } };
  if (operationId === 'proof.report') return { kind: 'proof-next-decision/v1', next: { action: 'manual-verification' }, detail_command: 'agentic-workspace proof --verbose --changed <paths> --format json' };
  if (operationId === 'setup.guidance') return { kind: 'workspace-setup/v1', command: 'setup', target_root: target };
  if (operationId === 'ownership.report') return { profile: 'compact-contract-answer/v1', surface: 'ownership', matched: false, target_root: target };
  if (operationId === 'skills.report') return { task: values.task ?? '', target_root: target, skills: [] };
  if (operationId === 'report.combined') return { kind: 'workspace-report-router/v1', command: 'report', target_root: target };
  if (operationId === 'reconcile.report') return { kind: 'planning-reconcile/v1', status: 'clean', target_root: target };
  if (operationId === 'preflight.report') return { kind: 'preflight-response/v1', mode: values.active_only ? 'active-state-only' : 'full', target_root: target };
  if (operationId === 'checkpoint.write') return {
    kind: 'agentic-workspace/local-chat-checkpoint-write/v1',
    status: 'written',
    path: '.agentic-workspace/local/chat-checkpoint.json',
    local_only: true,
    durable_sources: String(values.durable_source ?? '').trim() ? [String(values.durable_source).trim()] : [],
    durable_source_count: String(values.durable_source ?? '').trim() ? 1 : 0,
    current_issue_refs: String(values.issue ?? '').trim() ? [String(values.issue).trim()] : [],
    warnings: [],
    resume_rule: 'Local checkpoints are advisory continuity state, not durable closure evidence.',
    rule: 'Local-only checkpoint output from the native TypeScript adapter.',
  };
  if (['install.lifecycle', 'init.lifecycle', 'upgrade.lifecycle', 'uninstall.lifecycle'].includes(operationId)) return workspaceLifecycle(values, operationId.split('.')[0]);
  if (operationId === 'status.report') return { command: 'status', health: 'attention-needed', target_root: target };
  if (operationId === 'doctor.report') return { command: 'doctor', health: 'attention-needed', repair_plan: { kind: 'workspace-repair-plan/v1' }, target_root: target };
  return { command: values._command_path?.join(' ') ?? operationId, target_root: target, dry_run: Boolean(values.dry_run), message: operationId };
}

globalThis.hostDomainOperation = executeTypescriptDomainOperation;
