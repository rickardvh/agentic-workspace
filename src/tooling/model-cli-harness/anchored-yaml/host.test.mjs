import assert from 'node:assert/strict'
import test from 'node:test'
import * as yamlLibrary from 'yaml'
import { createAgentSession as newSession, renderAgentYaml } from '../../../cli/typescript/native/agent-view.mjs'

const { parse } = yamlLibrary
const createAgentSession = () => newSession(yamlLibrary)

const hash = char => 'sha256:' + char.repeat(64)
const choices = [{ id: 'authorize-write', label: 'Authorize this write' }]
function native() {
  return {
    decision_packet: {
      kind: 'agentic-workspace/operating-decision/v1',
      decision_request: { reference: hash('a'), choices, material: { reference: hash('a') } },
      primary_action: { kind: 'agentic-workspace/operation-invocation/v1', idempotency_key: hash('b'),
        arguments: { reference: hash('c'), value: hash('a') } },
      blockers: [{ code: 'protected', affects: ['effect:write'], revision: hash('d') }]
    },
    detail_refs: { '/configuration': 'detail:configuration:' + hash('c') }
  }
}

test('exact selections are role-bound and literal owner content stays intact', () => {
  const raw = native()
  const view = createAgentSession().present(JSON.stringify(raw))
  const result = parse(view.yaml)
  const packet = result.decision_packet
  const detail = result.detail_refs['/configuration']
  assert.notEqual(detail, raw.detail_refs['/configuration'])
  assert.equal(view.resolve(detail, 'detail'), raw.detail_refs['/configuration'])
  assert.equal(view.resolve(packet.decision_request.reference, 'answer'), hash('a'))
  assert.equal(view.resolve(packet.primary_action.idempotency_key, 'action'), hash('b'))
  assert.equal(packet.blockers[0].revision, hash('d'))
  assert.equal(view.inspect(detail), raw.detail_refs['/configuration'])
  assert.deepEqual(packet.primary_action.arguments, raw.decision_packet.primary_action.arguments)
  assert.deepEqual(packet.decision_request.material, raw.decision_packet.decision_request.material)
  assert.deepEqual(packet.decision_request.choices, choices)
  assert.deepEqual(packet.blockers[0].affects, ['effect:write'])
  for (const handle of [detail, packet.blockers[0].revision, hash('b'), 'unknown']) {
    assert.throws(() => view.resolve(handle, 'action'), RangeError)
  }
})

test('each presentation, lost host or malformed successor invalidates old selections', () => {
  const raw = JSON.stringify(native())
  const session = createAgentSession()
  const original = session.present(raw)
  const old = parse(original.yaml).decision_packet.primary_action.idempotency_key
  const next = session.present(raw)
  const current = parse(next.yaml).decision_packet.primary_action.idempotency_key
  assert.notEqual(old, current)
  assert.throws(() => original.resolve(old, 'action'), RangeError)
  assert.throws(() => next.resolve(old, 'action'), RangeError)
  assert.throws(() => createAgentSession().present(raw).resolve(current, 'action'), RangeError)
  assert.throws(() => session.present('invalid'))
  assert.throws(() => next.resolve(current, 'action'), RangeError)
  const again = session.present(raw)
  session.clear()
  assert.throws(() => again.inspect(parse(again.yaml).decision_packet.primary_action.idempotency_key), RangeError)
})

test('carriage is private, native errors survive and foreign carriage fails closed', () => {
  const session = createAgentSession()
  const kind = 'agentic-workspace/operating-carriage/v1'
  const view = native()
  view.decision_packet.primary_action = { kind: 'agentic-workspace/carried-action-view/v1', reference: hash('e') }
  const wrapped = session.present(JSON.stringify({ view, carriage: { kind, secret: 'host only' } }))
  const data = parse(wrapped.yaml)
  assert.equal(wrapped.resolve(data.decision_packet.primary_action.reference, 'action'), hash('e'))
  assert.ok(!wrapped.yaml.includes('host only'))
  for (const invalid of [{kind}, {carriage:{kind:'future'},view}, {carriage:{kind}}]) {
    assert.throws(() => session.present(JSON.stringify(invalid)), TypeError)
  }
  const error = { effect_outcome: { status: 'uncertain' }, continuation: { retry_effect: false } }
  assert.deepEqual(parse(session.present(JSON.stringify(error)).yaml), error)
})

test('post-effect continuation preserves the receipt and keeps nested carriage host-side', () => {
  const receipt = {
    effect_outcome: { status: 'committed' },
    continuation: { status: 'current', retry_effect: false, result: {
      view: native(), carriage: { kind: 'agentic-workspace/operating-carriage/v1', secret: 'opaque-envelope' }
    } }
  }
  const raw = JSON.stringify(receipt)
  const literal = parse(renderAgentYaml(raw, yamlLibrary))
  assert.equal(literal.effect_outcome.status, 'committed')
  assert.deepEqual(literal.continuation.result, native())
  const selected = createAgentSession().present(raw)
  const current = parse(selected.yaml).continuation.result
  assert.equal(selected.resolve(current.decision_packet.decision_request.reference, 'answer'), hash('a'))
  assert.ok(!selected.yaml.includes('opaque-envelope'))
  receipt.continuation.result.carriage.kind = 'new-version'
  const unsupported = parse(renderAgentYaml(JSON.stringify(receipt), yamlLibrary))
  assert.equal(unsupported.effect_outcome.status, 'committed')
  assert.equal(unsupported.continuation.retry_effect, false)
  assert.ok(unsupported.continuation.result.presentation_error)
})
