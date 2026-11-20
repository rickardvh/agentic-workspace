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

test('preserves integral floats and escapes nonprinting YAML characters in keys and values', () => {
  const controls = '\u007f\u0084\u0085\u0086\u009f\u2028\u2029\ufeff\ufffe\uffff'
  const wideKey = controls.repeat(18)
  const raw = '{"float":1.0000000000000001e18,"integer":1000000000000000100,' +
    '"tiny":1e-23,"integral":5.0,' + JSON.stringify(wideKey) + ':' + JSON.stringify('line\n' + controls) + '}'
  const output = render(raw)
  for (const char of controls) assert.ok(!output.includes(char))
  const decoded = parse(output, { intAsBigInt: true })
  assert.equal(decoded[wideKey], 'line\n' + controls)
  assert.equal(decoded.integer, 1000000000000000100n)
  assert.equal(BigInt(decoded.float), 1000000000000000128n)
  assert.equal(decoded.integral, 5)
  assert.equal(decoded.tiny, 1e-23)
})

test('nested repeats stay readable with the standard YAML alias limit', () => {
  const row = Array(15).fill('a long repeated value '.repeat(4))
  const value = Array(15).fill(row)
  assert.deepEqual(parse(render(JSON.stringify(value))), value)
})

test('aliases shared evidence inside repeated records', () => {
  const evidence = 'shared-evidence:' + 'ab'.repeat(32)
  const first = { evidence, owner: 'configuration' }
  const second = { evidence, owner: 'verification' }
  const value = [first, second, first, second]
  const yaml = render(JSON.stringify(value))
  assert.equal(yaml.split(evidence).length - 1, 1)
  assert.deepEqual(parse(yaml), value)
})

test('preserves prose, flow punctuation, special scalars and multiline whitespace', () => {
  const values = ['a,b', 'a[b]', 'a # comment', 'a: b', '.NaN', '.INF', 'ON', 'n', '/path',
    'first\nlast', '\nfirst  \n indented\n\n', '  first\nlast', 'first\n   \n', 'first\r\nlast']
  const doc = [Object.fromEntries(values.map(key => [key, [key, key]])), ...values]
  assert.deepEqual(parse(render(JSON.stringify(doc))), doc)
})
