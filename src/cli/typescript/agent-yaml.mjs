#!/usr/bin/env node
import { readFileSync } from 'node:fs'
import { renderAgentYaml } from './native/agent-view.mjs'

if (process.argv[2] === '--help') {
  console.log('Read one native AW JSON response on stdin and print anchored YAML. Requires Node 22.12+.')
} else {
  try {
    if (process.argv.length !== 2) throw new TypeError('Supply one JSON response on stdin.')
    process.stdout.write(renderAgentYaml(readFileSync(0, 'utf8')))
  } catch (error) {
    console.error(error.message)
    process.exitCode = 2
  }
}
