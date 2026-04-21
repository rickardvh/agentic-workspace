# Lazy Discovery Workflow Measurements

## Scope

- Run the expanded lazy-discovery measurement framework against a bounded set of current workflow classes instead of only the original three selector questions.

## Method

- Command: `uv run python scripts/check/measure_lazy_discovery.py --target .`
- Proxy metrics:
  - artifacts loaded before the first safe action
  - file reads avoided when a compact route replaces prose-first rereading
  - UTF-8 bytes returned
  - approximate tokens via `ceil(character_count / 4)`
- Comparison rule:
  - preferred compact/query-first route for one workflow question
  - broader plausible fallback route for the same question

## Results

| Workflow class | Preferred route | Fallback route | Preferred artifacts | Fallback artifacts | Artifacts saved | Bytes saved | Reduction |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: |
| Startup and routing | `agentic-workspace defaults --section startup --format json` | `AGENTS.md`, `TODO.md`, `tools/AGENT_QUICKSTART.md`, `tools/AGENT_ROUTING.md` | 1 | 4 | 3 | 17811 | 94.6% |
| Active planning inspection and restart handoff | `agentic-planning-bootstrap summary --target ./repo --format json` | `TODO.md`, `ROADMAP.md`, `.agentic-workspace/planning/execplans/README.md`, `docs/environment-recovery-contract.md` | 1 | 4 | 3 | 18858 | 86.0% |
| Proof-lane selection | `agentic-workspace defaults --section proof_selection --format json` | `docs/default-path-contract.md`, `.agentic-workspace/docs/proof-surfaces-contract.md` | 1 | 2 | 1 | 10090 | 81.9% |
| Ownership lookup | `agentic-workspace ownership --target ./repo --concern active-execution-state --format json` | `AGENTS.md`, `.agentic-workspace/docs/ownership-authority-contract.md`, `.agentic-workspace/OWNERSHIP.toml` | 1 | 3 | 2 | 16311 | 96.2% |
| Setup and jumpstart inspection | `agentic-workspace setup --target ./repo --format json` | `llms.txt`, `docs/init-lifecycle.md`, `docs/jumpstart-contract.md` | 1 | 3 | 2 | 5401 | 56.2% |
| **Total** |  |  | **5** | **16** | **11** | **68471** | **86.0%** |

Approximate token proxy:

| Workflow class | Preferred approx tokens | Fallback approx tokens | Tokens saved | Reduction |
| --- | ---: | ---: | ---: | ---: |
| Startup and routing | 257 | 4710 | 4453 | 94.5% |
| Active planning inspection and restart handoff | 770 | 5484 | 4714 | 86.0% |
| Proof-lane selection | 557 | 3080 | 2523 | 81.9% |
| Ownership lookup | 162 | 4239 | 4077 | 96.2% |
| Setup and jumpstart inspection | 1054 | 2404 | 1350 | 56.2% |
| **Total** | **2800** | **19917** | **17117** | **85.9%** |

## Takeaways

- The broader workflow tranche still supports the compact/query-first contract: five compact routes replace sixteen fallback file reads and cut the retrieval payload by about 86% overall in this repo.
- The strongest measured wins are startup/routing and ownership lookup, where one narrow answer replaces multiple broad startup or authority surfaces.
- Active planning inspection and setup/jumpstart still show meaningful wins, but setup remains smaller than startup or ownership because it legitimately carries more contract detail than a single selector answer.
- The restart/handoff case is now measured through `agentic-planning-bootstrap summary --format json`, which gives a current-state answer without reopening TODO, roadmap, execplan guidance, and recovery prose together.

## Qualitative Notes

- This tranche still does not directly score planning curation mistakes or repeated proof correction. Those remain review-shaped questions, not cheap script metrics.
- The audit does now cover the practical “first safe action” pressure from file-first fallback paths, which was the main missing evidence in the earlier selector-only pass.
- The current numbers support the repo’s recent report-first, summary-first, selector-first, and setup-first guidance instead of leaving those claims at the level of contract neatness.

## Decision

- GitHub issue `#87` can close on this expanded evidence pass.
- Future compactness work should keep using this workflow-class audit pattern before claiming that a new surface reduces reading or restart cost.
