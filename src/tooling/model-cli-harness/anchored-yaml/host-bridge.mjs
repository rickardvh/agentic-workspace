// Line-delimited host protocol for the Python benchmark. Only the YAML string
// enters model context. Native bindings live in this process for one session.
import { createInterface } from 'node:readline'
import { getEncoding } from 'js-tiktoken'
import * as yamlLibrary from 'yaml'
import { createAgentSession } from '../../../cli/typescript/native/agent-view.mjs'

const session = createAgentSession(yamlLibrary)
const enc = getEncoding('o200k_base')
let view
for await (const line of createInterface({ input: process.stdin, crlfDelay: Infinity })) {
  let reply
  try {
    const request = JSON.parse(line)
    if (request.op === 'present') {
      view = session.present(request.raw)
      reply = { text: view.yaml, tokens: enc.encode(view.yaml, [], []).length }
    } else if (request.op === 'resolve') {
      reply = { value: view.resolve(request.handle, request.role) }
    } else {
      throw new TypeError('Unknown operation')
    }
  } catch (error) {
    reply = { error: error.message }
  }
  process.stdout.write(JSON.stringify(reply) + '\n')
}
