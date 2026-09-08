import { readFile } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import { start, invoke } from '@agentic-workspace/workspace-cli/native';

const request = JSON.parse(await readFile(process.argv[2], 'utf8'));
let payload;
try {
  const result = request.action === 'provenance'
    ? { module: fileURLToPath(import.meta.resolve('@agentic-workspace/workspace-cli/native')) }
    : { start, invoke }[request.action](request.context);
  payload = { status: 'ok', result };
} catch (error) {
  payload = { status: 'error', message: error.message };
}
process.stdout.write(`${JSON.stringify(payload)}\n`);
