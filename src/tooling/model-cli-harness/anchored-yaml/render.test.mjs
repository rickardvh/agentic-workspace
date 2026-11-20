import assert from 'node:assert/strict'
import { spawnSync } from 'node:child_process'
import { fileURLToPath } from 'node:url'
import test from 'node:test'
import { parse } from 'yaml'

function render(input) {
  const filename = fileURLToPath(new URL('./render.mjs', import.meta.url))
  const result = spawnSync(process.execPath, [filename], { input, encoding: 'utf8' })
  assert.equal(result.status, 0, result.stderr)
  return result.stdout
}

test('distinct but equal records use an earlier document-local anchor', () => {
  const record = { reference: 'sha256:' + 'ab'.repeat(32), affects: ['effect:implementation'] }
  const input = JSON.stringify({ first: record, next: record })
  const yaml = render(input)
  assert.match(yaml, /first: &a/)
  assert.match(yaml, /next: \*a/)
  assert.deepEqual(parse(yaml), JSON.parse(input))
})

test('ambiguous strings, Unicode, reserved keys and native integer boundaries round-trip', () => {
  const input = '{"max":18446744073709551615,"min":-9223372036854775808,"zero":-0.0,' +
    '"__proto__":"01","text":["true","null","1e3","こんにちは 😀","*r1","line\\r\\nend"]}'
  const document = parse(render(input), { intAsBigInt: true })
  assert.equal(document.max, 18446744073709551615n)
  assert.equal(document.min, -9223372036854775808n)
  assert.ok(Object.is(document.zero, -0))
  assert.equal(document['__proto__'], '01')
  assert.deepEqual(document.text, JSON.parse(input).text)
})

test('nested repeats stay readable with the standard YAML alias limit', () => {
  const row = Array(15).fill('a long repeated value '.repeat(4))
  const value = Array(15).fill(row)
  assert.deepEqual(parse(render(JSON.stringify(value))), value)
})
