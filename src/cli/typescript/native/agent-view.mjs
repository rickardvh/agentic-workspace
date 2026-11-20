import { randomBytes } from 'node:crypto'
import { anchored, jsonText, parseJSON } from './_agent-yaml.mjs'

const digest = /sha256:[0-9a-f]{64}(?![0-9a-f])/g
const idString = /^[A-Za-z0-9_:./#-]+$/
const isRecord = value => value !== null && typeof value === 'object' && !Array.isArray(value)
const rows = value => Array.isArray(value) ? value : []

// The native response supplies the authoritative selectors. Owner material,
// source text, answer values and operation arguments remain literal YAML.
function project(view, shorten, knownSelection) {
  const packet = view?.decision_packet
  if (packet?.kind !== 'agentic-workspace/operating-decision/v1') return
  function field(record, key, role) {
    if (isRecord(record) && typeof record[key] === 'string') record[key] = shorten(record[key], role)
  }
  function action(record) {
    if (record?.kind === 'agentic-workspace/operation-invocation/v1') {
      field(record, 'idempotency_key', 'action')
    } else if (record?.kind === 'agentic-workspace/carried-action-view/v1') {
      field(record, 'reference', 'action')
    }
  }
  for (const record of [packet.decision_request, ...rows(packet.pending_consequences?.decisions)]) {
    field(record, 'reference', 'answer')
  }
  for (const record of [packet.primary_action, ...rows(packet.ready_actions), ...rows(packet.pending_consequences?.actions)]) action(record)
  if (isRecord(view.detail_refs)) {
    for (const [key, value] of Object.entries(view.detail_refs)) {
      if (typeof value !== 'string') continue
      if (value.startsWith('detail:')) field(view.detail_refs, key, 'detail')
      else view.detail_refs[key] = knownSelection(value) ?? value
    }
  }
  for (const group of rows(view.consequence_recovery)) {
    for (const route of rows(group.routes)) {
      if (typeof route?.reference === 'string' && route.reference.startsWith('detail:')) field(route, 'reference', 'detail')
    }
  }
  for (const name of ['assignment_context', 'setup_context', 'planning_context', 'verification_context']) {
    const step = view[name]?.next_step
    if (typeof step?.reference === 'string' && step.reference.startsWith('request:')) field(step, 'reference', 'answer')
  }
}

function unwrap(native) {
  // Native carried output is a host transport. Its view is the entire model input.
  const carriageKind = 'agentic-workspace/operating-carriage/v1'
  if (native?.kind === carriageKind) throw new TypeError('Supply the response containing its model-facing view.')
  if (isRecord(native) && Object.hasOwn(native, 'carriage')) {
    if (!isRecord(native.view) || native.carriage?.kind !== carriageKind) {
      throw new TypeError('Unrecognized carriage. Resolve the current AW response again.')
    }
    return native.view
  }
  return native
}

function modelView(raw) {
  const view = unwrap(parseJSON(raw))
  if (isRecord(view?.effect_outcome) && view.continuation?.status === 'current' && isRecord(view.continuation.result)) {
    try {
      view.continuation.result = unwrap(view.continuation.result)
    } catch (error) {
      // Keep the observed effect and native retry decision when a newer host
      // bundle cannot be rendered. Only the follow-up view is unavailable.
      view.continuation.result = { presentation_error: error.message }
    }
  }
  return view
}

export function renderAgentYaml(raw, yamlLibrary) {
  return anchored(modelView(raw), yamlLibrary)
}

export function createAgentSession(yamlLibrary) {
  let active
  return {
    clear() { active = undefined },
    present(raw) {
      // Invalidate even if the successor is malformed or rendering fails.
      active = undefined
      const view = modelView(raw)
      const literal = jsonText(view)
      let prefix
      do { prefix = 'h_' + randomBytes(9).toString('base64url') + '.' } while (literal.includes(prefix))
      const symbols = new Map()
      const byDisplay = new Map()
      const byValue = new Map()
      function shorten(value, role) {
        if (!idString.test(value)) return value
        const display = value.replace(digest, hash => {
          if (!symbols.has(hash)) symbols.set(hash, prefix + (symbols.size + 1).toString(36))
          return symbols.get(hash)
        })
        if (value !== display) {
          if (!byDisplay.has(display)) byDisplay.set(display, { value, roles: new Set() })
          byDisplay.get(display).roles.add(role)
          byValue.set(value, display)
        }
        return display
      }
      project(view, shorten, value => byValue.get(value))
      if (isRecord(view?.effect_outcome) && view.continuation?.status === 'current') {
        project(view.continuation.result, shorten, value => byValue.get(value))
      }
      const yaml = anchored(view, yamlLibrary)
      active = byDisplay
      function lookup(handle, role) {
        const entry = byDisplay.get(handle)
        if (active !== byDisplay || !entry || (role !== 'inspect' && !entry.roles.has(role))) {
          throw new RangeError('Unknown, expired or wrong-purpose selection. Re-read the current AW response.')
        }
        return entry.value
      }
      return Object.freeze({
        yaml,
        inspect: handle => lookup(handle, 'inspect'),
        resolve(handle, role) {
          if (!['detail', 'answer', 'action'].includes(role)) throw new TypeError('Expected detail, answer or action')
          return lookup(handle, role)
        }
      })
    }
  }
}
