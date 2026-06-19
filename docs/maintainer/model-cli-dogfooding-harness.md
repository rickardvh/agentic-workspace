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
  --model gemini-3-flash-preview `
  --scenario startup-orientation
```

The Codex adapter defaults to GPT-5.3 Codex Spark:

```powershell
uv run python scripts/model_cli_harness/run_model_cli_harness.py `
  --adapter codex `
  --model gpt-5.3-codex-spark `
  --scenario startup-orientation
```

The Docker Sandbox-backed Codex adapter runs the copied fixture through Docker Sandboxes instead of the host shell:

```powershell
uv run python scripts/model_cli_harness/build_sbx_codex_template.py

uv run python scripts/model_cli_harness/run_model_cli_harness.py `
  --adapter codex-sbx `
  --model gpt-5.3-codex-spark `
  --scenario startup-orientation
```

Install the Docker Sandboxes CLI as `sbx` first. On Windows without `winget`, install the official `DockerSandboxes.msi` release asset and make sure `%LOCALAPPDATA%\DockerSandboxes\bin` is on `PATH`; the harness also checks that user-local path during preflight. Authenticate with `sbx login`, `sbx secret set -g openai --oauth`, or an `OPENAI_API_KEY` before an executed run.

The `build_sbx_codex_template.py` helper builds the repo-owned template image `agentic-workspace/codex-sbx:local`, saves it from Docker, and loads it into Docker Sandboxes with `sbx template load`. The image is based on Docker's Codex sandbox template and sets Linux-safe uv defaults for mounted fixtures. It does not copy the source checkout into the runtime image; the copied fixture installs AW from the public root GitHub release wheel as a normal package dependency through `uv sync`. Authentication and credentials stay host-side; the sandboxed Codex run preserves Docker Sandboxes' generated Codex config so OAuth subscription auth can route through the sandbox proxy provider.

Release-mode dependencies are the default for long-horizon evaluations and cross-agent comparisons. Use source-candidate dogfooding only when evaluating unreleased AW changes:

```powershell
uv run python scripts/model_cli_harness/run_model_cli_harness.py `
  --adapter codex-sbx `
  --scenario startup-orientation `
  --aw-dependency-mode local-wheelhouse
```

`--aw-dependency-mode local-wheelhouse` builds wheels from the current checkout, copies them into the disposable fixture, patches the copied root wheel to point at sibling fixture-local wheels, and makes the fixture depend on that single root wheel. It still exercises packaged artifacts through `uv sync`; it does not use editable installs or copy raw source into the sandbox image.

The runner defaults to dry-run. It copies the scenario fixture into the configured local scratch root under `.agentic-workspace/local/scratch/model-cli-harness`, renders the prompt, writes `run.json`, and prints the exact CLI command it would execute. Add `--execute` only when you intentionally want to spend model calls and allow the configured CLI to operate in the copied fixture.

Scenarios may define `prompt_variants` for non-deterministic probing. By default the runner uses the first/default prompt. Use `--prompt-variant all` to run every variant, or `--prompt-variant <id>` for a single one:

```powershell
uv run python scripts/model_cli_harness/run_model_cli_harness.py `
  --adapter codex `
  --scenario broad-work-decomposition `
  --prompt-variant all
```

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
- `sandbox`: optional sandbox adapter metadata. The result record includes `sandbox.kind`, `backend`, `agent`, `identity`, `repo_path`, `setup_status`, `setup_failures`, and `evidence: sandbox-backed`.
- `artifact_capture`: optional host artifact capture from adapter-visible paths. The `codex-sbx` adapter writes the final message inside the mounted fixture and the harness copies it back to the standard run-local `share_path`.
- `scenarios`: disposable fixture name, human prompt or `prompt_variants`, expected signals, scoring notes, and optional metadata scoring.
- `fixtures`: copied repos under `tools/model-cli-harness/fixtures/`.

Scenario metadata can express common scoring without adding Python branches:

- `allowed_write_patterns`: changed paths must match one of these glob patterns.
- `ignored_write_patterns`: changed paths matching these glob patterns are omitted from allowed/forbidden write scoring; use this only for known runtime byproducts that are not part of the task outcome.
- `forbidden_write_patterns`: changed paths must not match these glob patterns.
- `required_command_mentions`: final/transcript text must mention these commands or routed files.
- `required_executed_commands`: structured command transcripts must show that these commands actually ran; use this when a quoted command in docs or config is not enough.
- `forbidden_executed_commands`: structured command transcripts must not include these commands; use this for avoidable raw reads when a compact CLI surface should answer the question.
- `forbidden_response_phrases`: final/transcript text must not contain these phrases.
- `required_artifact_patterns`: paths that must exist in the copied fixture after an executed run.

To add another model CLI, add an adapter entry with a command list. Do not hard-code CLI behavior in the runner unless it is common to all adapters.

## Scenario Coverage

The current suite evaluates these semi-realistic workflow pressure points. The prompts are deliberately less package-specific than the expected signals:

- `startup-orientation`: whether a fresh agent follows `AGENTS.md` into the workspace front door before doing work.
- `direct-task-minimal-overhead`: whether a tiny edit stays direct and avoids creating planning residue.
- `broad-work-decomposition`: whether broad product work is classified and decomposed before implementation.
- `cli-discovery-before-planning`: whether an agent verifies actual Agentic Workspace commands instead of hallucinating lifecycle commands or mixing in runtime-native plan commands.
- `planning-artifact-integrity`: whether a created planning artifact lands on canonical schema-backed surfaces and is checked with `summary`.
- `native-plan-bridge`: whether an agent can use native/private planning while bridging durable decisions into repo-visible Agentic Workspace state.
- `memory-consult-before-edit`: whether an agent consults the Memory index and a narrow durable note before a context-sensitive edit.
- `memory-learning-capture`: whether repeated friction becomes compact durable Memory instead of staying in chat.
- `invalid-planning-recovery`: whether an agent diagnoses unsafe planning state and chooses non-destructive recovery.
- `capability-fit-routing`: whether agents route work according to capability fit, proof risk, and cost only when quality is not compromised.
- `config-closeout-obligation`: whether a direct edit still honours repo-configured workflow obligations, improvement latitude, and output posture at closeout.
- `local-delegation-posture`: whether agents distinguish checked-in repo policy from local-only delegation controls and avoid auto-delegation when local safety disables it.
- `config-output-posture`: whether agents use config to shape reporting style without turning output posture into execution-method authority.

`direct-task-minimal-overhead`, `next-decision-output-profile`, and `config-closeout-obligation` are proportionality guardrails for small bounded work. Their `run.json` entries include `proportionality_metrics` for command count, package output size, changed-file count, Planning/Memory residue, raw workspace reads, verbose/full diagnostics, requests to completion, and final-answer length. The harness emits proportionality warning classes for over-planning, over-reading, over-proofing, Memory ceremony, and closeout ceremony. Treat those warnings as review signals: compact AW routing is allowed when it prevents wrong action, but tiny work should not become a broad diagnostic or Planning exercise.

Use these as optimisation probes rather than regular regression tests. A good run matrix samples a few scenarios across weaker, cheaper, and stronger agents, then turns repeated weak points into package changes, clearer CLI output, docs, fixtures, or new scorer warnings. Do not expect a single deterministic pass/fail result to settle a workflow question.

## Adaptive Optimisation Loop

1. Pick a capability to stress, such as startup routing, proportional overhead, decomposition, native-plan bridging, recovery, proof selection, or closeout.
2. Run two or more adapters against related scenarios, keeping prompts realistic and slightly varied between rounds.
3. Inspect `run.json`, transcripts, final messages, copied fixture diffs, and `warnings`.
4. Classify findings as product ambiguity, model-specific weakness, harness blind spot, fixture weakness, or acceptable variance.
5. Fix product ambiguity immediately when the package can reduce confusion; otherwise add or refine scorer warnings and scenarios.
6. Rerun the smallest scenario set that should expose the improvement.

This loop is intentionally exploratory. The harness provides isolation, comparable transcripts, and first-pass semantic warnings; the maintainer still acts dynamically as the human evaluator.

Use comparison mode after product or harness changes to check whether a targeted weakness improved:

```powershell
uv run python scripts/model_cli_harness/run_model_cli_harness.py `
  --compare-baseline .agentic-workspace/local/scratch/model-cli-harness/baseline/run.json `
  --compare-current .agentic-workspace/local/scratch/model-cli-harness/current/run.json `
  --format json
```

The comparison report lists resolved, retained, and new warnings, mutation deltas, proportionality metric deltas, a compact product interpretation, and the recommended next action. Treat it as a review aid, not a benchmark verdict.

## Long-Horizon Episodes

Long-horizon episodes extend the harness for multi-phase continuity evaluation. They are not replacements for the Tier 1 smoke suite. Use them when the question is whether repo state, AW state, proof evidence, and handoff boundaries survive restart or agent switch.

Episode metadata lives under `tools/model-cli-harness/episodes/` and validates against the hand-authorable `agentic-workspace/long-horizon-episode/v1` shape. Evaluator outputs validate against `agentic-workspace/long-horizon-evaluation/v1`. The runner is separate from the smoke runner:

```powershell
uv run python scripts/model_cli_harness/long_horizon_episode.py `
  --episode tools/model-cli-harness/episodes/intent-proof-packaging-specifier.json `
  --suite tools/model-cli-harness/suites/copilot-workflow-smoke.json `
  --format json
```

Dry-run remains the default. Add `--execute` only when you intentionally want the runner to clone or copy the episode repo, run phase prompts, and optionally invoke an evaluator adapter.

To collect sandbox-backed Codex evidence for a pinned episode, override the phase and evaluator adapters:

```powershell
uv run python scripts/model_cli_harness/long_horizon_episode.py `
  --episode tools/model-cli-harness/episodes/intent-proof-packaging-specifier.json `
  --suite tools/model-cli-harness/suites/copilot-workflow-smoke.json `
  --adapter codex-sbx `
  --evaluator-adapter codex-sbx `
  --format json
```

The episode runner supports:

- multiple modes, such as baseline and AW-assisted;
- AW-assisted mode bootstrapping from the existing minimal AW fixture for pinned external repos;
- multiple phases against the same copied or cloned repo;
- hidden-transcript resume phases via `hide_transcript_for_resume`;
- per-phase adapter/model selection for agent switching;
- CLI adapter/model overrides for sandbox-backed or comparison runs without changing episode metadata;
- mode-level phase overrides for same-agent continuation versus switched-agent comparison;
- checkpoint capture for diffs, transcripts, final answers, and validation output;
- a separate evaluator adapter with a controlled evidence bundle;
- post-score hidden/reference oracle metadata, kept out of the primary evaluator prompt;
- comparison summaries for mistake classes, same-agent versus agent-switch continuation, post-score reference status, AW effect, human-review-needed status, and follow-up routing.

The first episode pack is intentionally small:

- `intent-proof-packaging-specifier.json`: Packaging `===` original-string behavior, aimed at intent-proof and residual-risk scoring.
- `reuse-abstraction-pluggy.json`: Pluggy multi-implementation unregister behavior, aimed at abstraction/reuse, agent-switch continuation, and same-agent continuation comparison.
- `intent-proof-click-pager.json`: Click `CliRunner` / pager closed-file behavior, aimed at proof confidence for user-visible CLI behavior.
- `managed-planning-state-agentic-workspace.json`: AW invalid Planning fixture, aimed at managed-state and wrong-owner edit traps.

Most records pin real upstream repos and reference fixes; the managed-state episode uses a repo-local fixture so it can exercise AW-owned surfaces without mutating this checkout. Ordinary CI should use fake-adapter tests for deterministic coverage. Real model executions are maintainer evidence and should be reviewed with the evaluator output and transcripts, not treated as a leaderboard.

Executed run results include two different cost signals:

- `usage_summary`: provider/runtime token counters when the adapter exposes them.
- `package_read_surface_summary`: bytes and lines emitted by Agentic Workspace command executions found in structured transcripts.

Use `package_read_surface_summary` when optimising package output size. Use `usage_summary` as a broader provider/runtime context signal; it may include adapter scaffolding, cached context, prompt injection, and model-runtime overhead that the package cannot directly control.

Use pushed-to-completion follow-ups when a realistic human would keep steering the same agent until the intended outcome is actually complete. Each `--follow-up-prompt` is recorded as another request, with its own prompt, command, transcript, share file, result, and usage summary under `followups/`. Add `--completion-validation-command` to record final validation separately from first-pass success:

```powershell
uv run python scripts/model_cli_harness/run_model_cli_harness.py `
  --adapter gemini `
  --model gemini-3-flash-preview `
  --scenario csv-import-hard `
  --execute `
  --completion-followthrough pushed-to-completion `
  --follow-up-prompt "Run the test suite and fix any failing objective you missed." `
  --completion-validation-command "uv run pytest -q"
```

The per-run `completion_loop` distinguishes `first_pass_success`, `eventual_success`, `requests_to_completion`, `final_validation_status`, and cumulative usage. Use it for adaptive optimisation loops; it is not a deterministic benchmark score.

Use postmortem feedback during real optimisation loops when a run exposes ambiguous routing, excess file reads, surprising confidence, or high token use. The follow-up prompt asks the same agent why it chose its workflow and commands, what was ambiguous or too verbose, what package surface would have made the next step obvious, and what would reduce token usage without reducing safety or proof quality:

```powershell
uv run python scripts/model_cli_harness/run_model_cli_harness.py `
  --adapter copilot `
  --model claude-haiku-4.5 `
  --scenario startup-orientation `
  --execute `
  --postmortem-feedback
```

Treat the answer as evidence, not as ground truth. Separate provider/model limitations from package and harness improvements, and promote only feedback that explains observed behavior or suggests a compact, safer next-step surface.

Postmortem feedback must be isolated from the copied repo and tool access. Adapters can provide a separate `postmortem_command` and `{postmortem_cwd}` for this purpose. If an adapter cannot provide a true no-tool/no-repo reflection mode, mark `postmortem_feedback_supported` as `false`; the harness then records an unsupported postmortem status instead of launching a second tool-using coding session.

`tools/model-cli-harness/model-task-weakness-ledger.json` is the source-checkout-only ledger for repeated weak points. Keep entries compact: area, scenario, models, status, failure classes, evidence references, owner, next probe, and priority. Promote only recurring or high-consequence findings; dismiss one-off provider/runtime failures as acceptable variance or fixture artifacts when the evidence supports that.

The #1600 external-agent evaluation lane is defined in `tools/model-cli-harness/external-agent-evaluation/`. Use that pack when maintainer work needs the scorecard/taxonomy, evaluator invariants, canonical scenario probes, historical failure fixtures, promotion decisions, surface simplification decisions, operational decision trace, or lane-level closure report. Validate it with:

```powershell
uv run python scripts/model_cli_harness/external_agent_evaluation_lane.py validate
```

Generate the closure report with:

```powershell
uv run python scripts/model_cli_harness/external_agent_evaluation_lane.py report --format json
```

## What To Score

Inspect `run.json`, the CLI transcript, the copied repo diff, and package diagnostics. Useful signals:

- startup: did the agent read `AGENTS.md` and route to `.agentic-workspace/WORKFLOW.md` or CLI help?
- CLI-first use: did it run `agentic-workspace implement --changed <paths>` for known-path work, `agentic-workspace start --task "<task>"` for ordinary first contact, or an equivalent compact route before broad work?
- planning shape: did it use schema-backed records or invent PM-shaped artifacts?
- state safety: did it notice unsupported `state.toml` activation shapes?
- proof: did it select a narrow proof command instead of guessing?
- closeout: did it route residue and report uncertainty honestly?
- config: did it inspect the effective config surface when repo/local settings could affect closeout, delegation, proof, or reporting?
- local posture: did it treat `.agentic-workspace/config.local.toml` as local runtime posture, not checked-in repo policy?
- proportionality: did direct work stay direct while lane/epic-shaped work got durable planning?
- native-plan bridge: did private runtime planning remain private while durable decisions reached checked-in workspace state?
- Memory routing: did the agent use the index and the narrow note, and did repeated learning become compact durable context?

Treat one-off capability failures cautiously. Give more weight to repeated ambiguity, discovery-cost, proof-selection, and handoff failures across weaker or cheaper models.

## Safety Defaults

- Dry-run is the default.
- Scenario repository mutations should happen only in copied fixtures under `.agentic-workspace/local/scratch/`.
- Provider CLIs may still maintain their own local state outside the fixture. For Copilot, the harness routes logs to the run directory, but authenticated session/config state may still use `COPILOT_HOME` unless the operator provides an isolated authenticated home.
- The Copilot adapter passes both `-C {repo}` and `--add-dir {repo}` so Copilot roots its session in the copied fixture before invoking edit or PowerShell tools. It also sets `COPILOT_ALLOW_ALL=true` and passes Copilot's explicit `--allow-tool=write` grant because `--allow-all` alone has not reliably unlocked edits in non-interactive harness runs.
- The Copilot adapter denies `git push`.
- The Copilot adapter requires `pwsh` before execution because its shell tool uses PowerShell 7 on Windows. The suite includes standard PowerShell install paths and prepends the discovered parent directory to the model CLI `PATH`.
- The Gemini adapter runs `gemini --prompt` in headless mode and records JSON output. It uses `--approval-mode yolo` only when the operator explicitly passes `--execute`; dry-run remains the default.
- The Codex adapter runs `codex exec --dangerously-bypass-approvals-and-sandbox` with a copied fixture as its working directory, writes the final message to the run-local share file, and captures JSONL events when available. The harness relies on copied disposable fixtures for isolation because the Codex sandbox can otherwise block the installed package CLI from running.
- The `codex-sbx` adapter preflights `sbx`, then runs the host-side bridge `scripts/model_cli_harness/run_sbx_codex_adapter.py`. The bridge creates a named Docker Sandbox from the repo-owned `agentic-workspace/codex-sbx:local` template and executes `codex exec` inside it so Codex operates on the copied fixture from the sandbox. It intentionally preserves the sandbox-provided Codex config because Docker Sandboxes use that config to route OAuth subscription auth through their proxy provider. Authentication, account-scope, network, or sandbox startup failures remain adapter/runtime failures; the harness does not fall back to host `codex`.
- The runner emits warnings when transcripts report shell-runtime failures or modified files outside the copied fixture.
- The runner classifies provider/runtime and adapter/tooling limits separately from product workflow failures. Examples include provider capacity errors, terminal noise, missing shell tools, permission-denied command execution, and adapters that cannot execute `agentic-workspace` commands through their tool layer.
- Normal tests should validate command rendering and fixture isolation, not run external models.
