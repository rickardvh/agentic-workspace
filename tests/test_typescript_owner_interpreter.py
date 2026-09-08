"""Public owner bridge discovers python3 without replaying an executed owner."""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize("scenario", ["python3-only", "absent", "rejected", "non-json", "denied"])
def test_public_owner_interpreter_discovery(tmp_path: Path, scenario: str) -> None:
    node = shutil.which("node")
    if node is None:
        pytest.skip("Node is required for the public TypeScript owner adapter")
    script = """
import childProcess from 'node:child_process';
import fs from 'node:fs';
import { syncBuiltinESMExports } from 'node:module';
const [cli, target, scenario] = process.argv.slice(1);
const calls = [];
const originalSpawn = childProcess.spawnSync;
const originalExists = fs.existsSync;
fs.existsSync = (path) => /[\\\\/]python(?:\\.exe)?$/.test(String(path)) ? false : originalExists(path);
childProcess.spawnSync = (command, args, options) => {
  if (!['python', 'python3'].includes(command)) return originalSpawn(command, args, options);
  calls.push({ command, args });
  if (scenario === 'denied') return { error: Object.assign(new Error('interpreter denied'), { code: 'EACCES' }), status: null };
  if (scenario === 'absent' || (scenario === 'python3-only' && command === 'python')) {
    return { error: Object.assign(new Error(`${command} missing`), { code: 'ENOENT' }), status: null };
  }
  if (scenario === 'non-json') return { status: 1, stdout: 'owner failed', stderr: 'owner diagnostic' };
  return { status: scenario === 'rejected' ? 7 : 0, stdout: JSON.stringify({ kind: 'owner-answer', status: scenario === 'rejected' ? 'blocked' : 'accepted' }) };
};
syncBuiltinESMExports();
process.on('exit', () => process.stderr.write(JSON.stringify(calls)));
process.argv = [process.execPath, cli, 'proof', '--target', target, '--format', 'json'];
await import(new URL(`file:///${cli.replaceAll('\\\\', '/')}`));
"""
    result = subprocess.run(
        [node, "--input-type=module", "-e", script, str(ROOT / "generated/workspace/typescript/src/cli.mjs"), str(tmp_path), scenario],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    payload = json.loads(result.stdout)
    calls = json.loads(result.stderr)
    assert [call["command"] for call in calls] == (["python", "python3"] if scenario in {"python3-only", "absent"} else ["python"])
    if len(calls) == 2:
        assert calls[0]["args"] == calls[1]["args"]
    if scenario == "python3-only":
        assert result.returncode == 0
        assert payload["status"] == "accepted"
    elif scenario == "rejected":
        assert result.returncode == 7
        assert payload["status"] == "blocked"
    else:
        assert result.returncode == 2
        assert payload["completion_claim_allowed"] is False
        assert (
            payload["diagnostic"] == {"absent": "python3 missing", "non-json": "owner diagnostic", "denied": "interpreter denied"}[scenario]
        )
        assert payload["mutation_applied"] is (False if scenario == "absent" else None)
