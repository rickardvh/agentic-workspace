import { readFileSync } from 'node:fs'
import * as yamlLibrary from 'yaml'
import { anchored, parseJSON, jsonText } from '../../../cli/typescript/native/_agent-yaml.mjs'
import { renderAgentYaml } from '../../../cli/typescript/native/agent-view.mjs'

const raw = readFileSync(0, 'utf8')
const mode = process.argv[2] ?? 'yaml'
if (mode === 'yaml') {
  process.stdout.write(renderAgentYaml(raw, yamlLibrary))
} else if (mode === 'pair') {
  const { getEncoding } = await import('js-tiktoken')
  const enc = getEncoding('o200k_base')
  const value = parseJSON(raw)
  const json = jsonText(value)
  const yaml = anchored(value, yamlLibrary, {
    minLength: 48, name: n => 'r' + n, inlineLists: false, style: { lineWidth: 0 }
  })
  const tokens = text => enc.encode(text, [], []).length
  process.stdout.write(JSON.stringify({ json, yaml, tokens: { json: tokens(json), yaml: tokens(yaml) } }))
} else {
  throw new Error('Expected yaml or pair')
}
