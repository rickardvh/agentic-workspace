import { readFileSync } from 'node:fs'
import { isDeepStrictEqual } from 'node:util'
import * as yamlLibrary from 'yaml'
import { anchored, parseJSON, jsonText } from './node-baseline.mjs'
import { renderAgentYaml } from './checkout-view.mjs'

const raw = readFileSync(0, 'utf8')
const mode = process.argv[2] ?? 'yaml'
if (mode === 'yaml') {
  process.stdout.write(renderAgentYaml(raw))
} else if (mode === 'pair' || mode === 'node-rust') {
  const { getEncoding } = await import('js-tiktoken')
  const enc = getEncoding('o200k_base')
  const value = parseJSON(raw)
  const tokens = text => enc.encode(text, [], []).length
  if (mode === 'node-rust') {
    const rust = renderAgentYaml(raw)
    // This comparison takes full-value model inputs. Reject carried transport
    // before emitting either arm, including a carried effect continuation.
    if (!isDeepStrictEqual(yamlLibrary.parse(rust, { intAsBigInt: true }), value)) {
      throw new Error('The node-rust comparison requires an exact, unwrapped model view.')
    }
    const node = anchored(value, yamlLibrary)
    process.stdout.write(JSON.stringify({ node, rust, tokens: { node: tokens(node), rust: tokens(rust) } }))
  } else {
    const json = jsonText(value)
    const yaml = anchored(value, yamlLibrary, {
      minLength: 48, name: n => 'r' + n, inlineLists: false, style: { lineWidth: 0 }
    })
    process.stdout.write(JSON.stringify({ json, yaml, tokens: { json: tokens(json), yaml: tokens(yaml) } }))
  }
} else {
  throw new Error('Expected yaml, pair or node-rust')
}
