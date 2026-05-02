# Model CLI Dogfooding Harness

The model CLI harness runs external coding agents as black-box users of host repos that have Agentic Workspace installed. It is meant to expose workflow ambiguity in smaller or differently trained agents, not to benchmark generic coding ability.

Keep scenario prompts close to ordinary human requests. The prompt should not usually tell the agent to use Agentic Workspace, name package commands, or explain the package workflow. The useful question is whether repo instructions, generated surfaces, and CLI affordances pull the agent into the right workflow with little human steering. Package-specific expected signals and scorer warnings belong in the suite metadata and maintainer review, not in the user-facing prompt.

The smoke suite includes adapters for GitHub Copilot CLI, Gemini CLI, and Codex CLI. The Copilot adapter supports runs such as Claude Haiku through Copilot:

```powershell
uv run python scripts/model_cli_harness/run_model_cli_harness.py `
  --adapter copilot `
  --model claude-haiku-4.5 `
  --scenario startup-orientation
```

The Gemini adapter defaults to Gemini 3 Flash:

```powershell
uv run python scripts/model_cli_harness/run_model_cli_harness.py `
  --adapter gemini `
  --model gemini-3-flash `
  --scenario startup-orientation
```

The Codex adapter defaults to GPT-5.3 Codex Spark:

```powershell
uv run python scripts/model_cli_harness/run_model_cli_harness.py `
  --adapter codex `
  --model gpt-5.3-codex-spark `
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
- `required_executables` and `required_shells`: optional preflight requirements. Entries may be strings or objects with `name`, `candidate_paths`, and `add_parent_to_path`.
- `block_on_preflight_failure`: whether missing requirements should prevent model execution.
- `provider_home_env` and `provider_home_path`: optional state-isolation hook used by `--isolate-provider-home`.
- `scenarios`: disposable fixture name, human prompt, expected signals, and scoring notes.
- `fixtures`: copied repos under `tools/model-cli-harness/fixtures/`.

To add another model CLI, add an adapter entry with a command list. Do not hard-code CLI behavior in the runner unless it is common to all adapters.

## Scenario Coverage

The current suite evaluates these semi-realistic workflow pressure points. The prompts are deliberately less package-specific than the expected signals:

- `startup-orientation`: whether a fresh agent follows `AGENTS.md` into the workspace front door before doing work.
- `direct-task-minimal-overhead`: whether a tiny edit stays direct and avoids creating planning residue.
- `broad-work-decomposition`: whether broad product work is classified and decomposed before implementation.
- `cli-discovery-before-planning`: whether an agent verifies actual Agentic Workspace commands instead of hallucinating lifecycle commands or mixing in runtime-native plan commands.
- `planning-artifact-integrity`: whether a created planning artifact lands on canonical schema-backed surfaces and is checked with `summary`.
- `native-plan-bridge`: whether an agent can use native/private planning while bridging durable decisions into repo-visible Agentic Workspace state.
- `invalid-planning-recovery`: whether an agent diagnoses unsafe planning state and chooses non-destructive recovery.

Use these as optimisation probes rather than regular regression tests. A good run matrix samples a few scenarios across weaker, cheaper, and stronger agents, then turns repeated weak points into package changes, clearer CLI output, docs, fixtures, or new scorer warnings. Do not expect a single deterministic pass/fail result to settle a workflow question.

## Adaptive Optimisation Loop

1. Pick a capability to stress, such as startup routing, proportional overhead, decomposition, native-plan bridging, recovery, proof selection, or closeout.
2. Run two or more adapters against related scenarios, keeping prompts realistic and slightly varied between rounds.
3. Inspect `run.json`, transcripts, final messages, copied fixture diffs, and `warnings`.
4. Classify findings as product ambiguity, model-specific weakness, harness blind spot, fixture weakness, or acceptable variance.
5. Fix product ambiguity immediately when the package can reduce confusion; otherwise add or refine scorer warnings and scenarios.
6. Rerun the smallest scenario set that should expose the improvement.

This loop is intentionally exploratory. The harness provides isolation, comparable transcripts, and first-pass semantic warnings; the maintainer still acts dynamically as the human evaluator.

## What To Score

Inspect `run.json`, the CLI transcript, the copied repo diff, and package diagnostics. Useful signals:

- startup: did the agent read `AGENTS.md` and route to `.agentic-workspace/WORKFLOW.md` or CLI help?
- CLI-first use: did it run `agentic-workspace summary`, `preflight`, `planning`, `start`, or equivalent before broad work?
- planning shape: did it use schema-backed records or invent PM-shaped artifacts?
- state safety: did it notice unsupported `state.toml` activation shapes?
- proof: did it select a narrow proof command instead of guessing?
- closeout: did it route residue and report uncertainty honestly?
- proportionality: did direct work stay direct while lane/epic-shaped work got durable planning?
- native-plan bridge: did private runtime planning remain private while durable decisions reached checked-in workspace state?

Treat one-off capability failures cautiously. Give more weight to repeated ambiguity, discovery-cost, proof-selection, and handoff failures across weaker or cheaper models.

## Safety Defaults

- Dry-run is the default.
- Scenario repository mutations should happen only in copied fixtures under `scratch/`.
- Provider CLIs may still maintain their own local state outside the fixture. For Copilot, the harness routes logs to the run directory, but authenticated session/config state may still use `COPILOT_HOME` unless the operator provides an isolated authenticated home.
- The Copilot adapter denies `git push`.
- The Copilot adapter requires `pwsh` before execution because its shell tool uses PowerShell 7 on Windows. The suite includes standard PowerShell install paths and prepends the discovered parent directory to the model CLI `PATH`.
- The Gemini adapter runs `gemini --prompt` in headless mode and records JSON output. It uses `--approval-mode yolo` only when the operator explicitly passes `--execute`; dry-run remains the default.
- The Codex adapter runs `codex exec --dangerously-bypass-approvals-and-sandbox` with a copied fixture as its working directory, writes the final message to the run-local share file, and captures JSONL events when available. The harness relies on copied disposable fixtures for isolation because the Codex sandbox can otherwise block the installed package CLI from running.
- The runner emits warnings when transcripts report shell-runtime failures or modified files outside the copied fixture.
- Normal tests should validate command rendering and fixture isolation, not run external models.
