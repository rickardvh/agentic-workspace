// Installed npm lifecycle entry. Configuration owns the only permitted effect.
import { existsSync, readFileSync } from 'node:fs';
import { basename, dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { request } from './_transport.mjs';

let directory = dirname(fileURLToPath(import.meta.url));
while (dirname(directory) !== directory && basename(directory) !== 'node_modules') directory = dirname(directory);
const target = dirname(directory);
function observe() {
  if (basename(directory) !== 'node_modules' || !existsSync(join(target, '.agentic-workspace/adoption.json'))) return;
  try {
    // A retained bridge makes repeat interpreter/install entries no-write.
    // It is never evidence that Configuration assessment is complete.
    if (readFileSync(join(target, 'AGENTS.md'), 'utf8').includes('<!-- agentic-workspace:update-observation:start -->')) return;
    const context = {target, task: 'Observe installed AW dependency', projection: 'full'};
    const configuration = request({start: context}).configuration_write;
    if (configuration?.update_notice_status === 'unavailable') throw new Error('Configuration update notice requires recovery');
    const notice = configuration?.update_notice_request;
    if (notice) {
      const action = request({start: {...context, request: notice}}).decision_packet?.primary_action;
      if (action?.operation_id !== 'configuration.write' || action.arguments?.request?.arguments?.key !== 'package.update-notice') throw new Error('Configuration notice is not executable');
      const result = request({invoke: {...context, invocation: action}});
      if (result.effect_outcome?.status !== 'committed') throw new Error('Configuration notice publication needs recovery');
    }
  } catch {
    console.error('AW update notice unavailable; use the configured AW start entry for recovery.');
  }
}
observe();
