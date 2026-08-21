import { readFile } from 'node:fs/promises';
import { dirname } from 'node:path';
import { fileURLToPath } from 'node:url';
import {
  AWClientError,
  detectWorkspace,
  externalOperationConformanceReceipts,
  externalReadinessReport,
  invokeOperation,
  negotiateRequirements,
} from '@agentic-workspace/workspace-cli';

async function execute(request) {
  const action = String(request.action);
  const target = String(request.target ?? '.');
  if (action === 'provenance') {
    const moduleUrl = import.meta.resolve('@agentic-workspace/workspace-cli');
    return { module: fileURLToPath(moduleUrl), resources: dirname(fileURLToPath(moduleUrl)) };
  }
  if (action === 'detect') return detectWorkspace(target);
  if (action === 'readiness') {
    return externalReadinessReport((request.operations ?? []).map(String), {
      allowRuntimeBacked: Boolean(request.allow_runtime_backed),
    });
  }
  if (action === 'receipts') return externalOperationConformanceReceipts();
  if (action === 'negotiate') {
    return negotiateRequirements(request.requirements ?? {}, {
      allowRuntimeBacked: Boolean(request.allow_runtime_backed),
    });
  }
  if (action === 'invoke') {
    return invokeOperation(String(request.operation_id), request.values ?? {}, {
      target,
      invocation: request.invocation ?? undefined,
      allowRuntimeBacked: Boolean(request.allow_runtime_backed),
    });
  }
  throw new Error(`unknown consumer action: ${action}`);
}

const request = JSON.parse(await readFile(process.argv[2], 'utf8'));
let payload;
try {
  payload = { status: 'ok', result: await execute(request) };
} catch (error) {
  if (error instanceof AWClientError || error?.kind) {
    payload = {
      status: 'error',
      kind: error.kind,
      message: error.message,
      details: error.details ?? {},
    };
  } else {
    throw error;
  }
}
await new Promise((resolve, reject) => {
  process.stdout.write(`${JSON.stringify(payload)}\n`, (error) => {
    if (error) reject(error);
    else resolve();
  });
});
