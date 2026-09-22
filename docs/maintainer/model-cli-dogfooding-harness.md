# Probe an agent workflow

Use the model CLI harness to observe how an external coding agent handles a
realistic task in a copied AW repository. It exposes discovery, continuity and
proof-selection problems; it is not a model leaderboard. Keep prompts like normal
human requests. Put expected AW signals in scenario metadata, not in the prompt.

## Prepare one bounded probe

Choose a scenario and an available adapter from the
[suite declaration](../../src/tooling/model-cli-harness/suites/copilot-workflow-smoke.json).
Use the runner's `--help` for current flags and the suite for model, prerequisite
and adapter settings. Start with a dry run:

```sh
uv run python src/tooling/model-cli-harness/run_model_cli_harness.py --adapter codex --scenario startup-orientation
```

Inspect the rendered command, prompt and run directory before adding `--execute`.
Execution spends model calls and grants the adapter access described below.
Missing prerequisites should leave the run `environment-blocked`; use
`--allow-environment-blocked` only to collect deliberately partial evidence.
Ordinary tests use fake adapters, not external models.

For released-product claims, use release dependencies. For an unreleased change,
select `--aw-dependency-mode local-wheelhouse` and report it as source-candidate
packaged evidence. It does not prove the public release. Use prompt variants or a
second adapter only when they test a named ambiguity, rather than multiplying
every run automatically.

## Know the execution boundary

The runner copies fixtures under `.agentic-workspace/local/scratch/`. This protects
the source checkout from intended scenario edits; it is not a general sandbox.
Provider CLIs can retain authenticated state outside the fixture. Inspect adapter
commands and credentials before execution. Copilot may use its existing
`COPILOT_HOME`; `--isolate-provider-home` requires authentication in the isolated
home. The Copilot adapter denies Git push, but that is not general network or
credential confinement.

Gemini's executed adapter uses its permissive approval mode. Plain Codex bypasses
its approval/sandbox controls inside the copied fixture. The `codex-sbx` adapter
instead requires Docker Sandboxes, its authenticated provider and the repo-owned
template. Follow the [bridge](../../src/tooling/model-cli-harness/run_sbx_codex_adapter.py)
and [template builder](../../src/tooling/model-cli-harness/build_sbx_codex_template.py)
for that setup. Preserve the sandbox-generated provider configuration; failures
must not fall back silently to host Codex. Keep a sandbox only for deliberate
debugging. Warnings about writes outside the fixture require investigation.

## Interpret and improve

Inspect `run.json`, the transcript, final message, copied diff and validation
output together. Separate product ambiguity, fixture defects, adapter/tool limits,
provider availability and model mistakes. A one-off capacity failure is not proof
that the product workflow is wrong or that a model is a poor fit.

Compare total work to the result: requests to completion, retries, repair,
validation, retained state and emitted context. Provider token usage and AW output
size measure different things. First-pass success, eventual success and final
validation also remain distinct. The comparison mode reports changed warnings
and costs; it cannot supply semantic acceptance.

Repair the strongest source responsible for a material finding, then rerun the
smallest scenario that can expose the improvement. Retain only useful recurring
or high-consequence findings in the existing
[weakness ledger](../../src/tooling/model-cli-harness/model-task-weakness-ledger.json).
Do not promote a favourable summary into independent review or proof.

## Select deeper evaluation only when needed

Use [long-horizon episodes](../../src/tooling/model-cli-harness/episodes/) for
restart, agent-switch or handoff questions. The
[episode runner](../../src/tooling/model-cli-harness/long_horizon_episode.py)
owns phase, evaluator, checkpoint and comparison options. Keep hidden reference
answers out of the primary evaluator prompt. Large prompts need file-backed
transport; unsupported adapter limits stay explicit.

Completion follow-ups can measure eventual success when continued steering is the
realistic user behaviour. Keep final validation separate from the first answer.
Postmortem feedback is optional advice: use a no-tool/no-repository reflection
mode, or mark it unsupported rather than launching another unrestricted coding
session. Exact evaluator contracts and retained evidence belong to the
[external evaluation pack](../../src/tooling/model-cli-harness/external-agent-evaluation/README.md),
not a duplicate field catalogue here.
