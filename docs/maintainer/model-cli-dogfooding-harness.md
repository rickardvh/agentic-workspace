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

Before execution, the runner evaluates adapter prerequisites such as the CLI executable and declared shell/tool dependencies. If a blocking prerequisite is missing, the scenario result is `environment-blocked` and the model is not called. Use `--allow-environment-blocked` only when deliberately collecting partial evidence from a degraded runtime.

```powershell
uv run python scripts/model_cli_harness/run_model_cli_harness.py `
  --adapter copilot `
  --model claude-haiku-4.5 `
  --scenario broad-work-decomposition `
  --execute
```

Copilot stores authenticated state under `COPILOT_HOME`. The harness does not isolate this by default because an empty home may not be authenticated. To run with run-local provider state after arranging authentication for that home, pass:

```powershell
uv run python scripts/model_cli_harness/run_model_cli_harness.py `
  --adapter copilot `
  --model claude-haiku-4.5 `
  --scenario startup-orientation `
  --execute `
  --isolate-provider-home
```

## Reuse Contract

Suites live under `tools/model-cli-harness/suites/`. Each suite defines:

- `adapters`: command templates with placeholders such as `{prompt}`, `{repo}`, `{model}`, `{share_path}`, and `{source_root}`.
- `required_executables` and `required_shells`: optional preflight requirements.
- `block_on_preflight_failure`: whether missing requirements should prevent model execution.
- `provider_home_env` and `provider_home_path`: optional state-isolation hook used by `--isolate-provider-home`.
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
- Scenario repository mutations should happen only in copied fixtures under `scratch/`.
- Provider CLIs may still maintain their own local state outside the fixture. For Copilot, the harness routes logs to the run directory, but authenticated session/config state may still use `COPILOT_HOME` unless the operator provides an isolated authenticated home.
- The Copilot adapter denies `git push`.
- The Copilot adapter requires `pwsh` before execution because its shell tool uses PowerShell 7 on Windows.
- The runner emits warnings when transcripts report shell-runtime failures or modified files outside the copied fixture.
- Normal tests should validate command rendering and fixture isolation, not run external models.
