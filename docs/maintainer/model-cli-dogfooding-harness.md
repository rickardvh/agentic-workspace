# Model CLI Dogfooding Harness

The model CLI harness runs external coding agents as black-box users of Agentic Workspace. It is meant to expose workflow ambiguity in smaller or differently trained agents, not to benchmark generic coding ability.

The first adapter targets GitHub Copilot CLI, including runs such as Claude Haiku through Copilot:

```powershell
uv run python scripts/model_cli_harness/run_model_cli_harness.py `
  --adapter copilot `
  --model claude-haiku-4.5 `
  --scenario startup-orientation
```

The runner defaults to dry-run. It copies the scenario fixture into `scratch/model-cli-harness`, renders the prompt, writes `run.json`, and prints the exact CLI command it would execute. Add `--execute` only when you intentionally want to spend model calls and allow the configured CLI to operate in the copied fixture.

```powershell
uv run python scripts/model_cli_harness/run_model_cli_harness.py `
  --adapter copilot `
  --model claude-haiku-4.5 `
  --scenario broad-work-decomposition `
  --execute
```

## Reuse Contract

Suites live under `tools/model-cli-harness/suites/`. Each suite defines:

- `adapters`: command templates with placeholders such as `{prompt}`, `{repo}`, `{model}`, `{share_path}`, and `{source_root}`.
- `scenarios`: disposable fixture name, human prompt, expected signals, and scoring notes.
- `fixtures`: copied repos under `tools/model-cli-harness/fixtures/`.

To add another model CLI, add an adapter entry with a command list. Do not hard-code CLI behavior in the runner unless it is common to all adapters.

## What To Score

Inspect `run.json`, the CLI transcript, the copied repo diff, and package diagnostics. Useful signals:

- startup: did the agent read `AGENTS.md` and route to `.agentic-workspace/WORKFLOW.md` or CLI help?
- CLI-first use: did it run `agentic-workspace summary`, `preflight`, `planning`, `start`, or equivalent before broad work?
- planning shape: did it use schema-backed records or invent PM-shaped artifacts?
- state safety: did it notice unsupported `state.toml` activation shapes?
- proof: did it select a narrow proof command instead of guessing?
- closeout: did it route residue and report uncertainty honestly?

Treat one-off capability failures cautiously. Give more weight to repeated ambiguity, discovery-cost, proof-selection, and handoff failures across weaker or cheaper models.

## Safety Defaults

- Dry-run is the default.
- Real execution happens only in copied fixtures under `scratch/`.
- The Copilot adapter denies `git push`.
- Normal tests should validate command rendering and fixture isolation, not run external models.

