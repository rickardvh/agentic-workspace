// Exercise the real package adapter against the prepared source-checkout core.
import { fileURLToPath } from 'node:url'

process.env.AGENTIC_WORKSPACE_CORE_BINARY ??= fileURLToPath(new URL(
  '../../../../target/debug/agentic-workspace-core' + (process.platform === 'win32' ? '.exe' : ''), import.meta.url))
export { createAgentSession, renderAgentYaml } from '../../../cli/typescript/native/agent-view.mjs'
