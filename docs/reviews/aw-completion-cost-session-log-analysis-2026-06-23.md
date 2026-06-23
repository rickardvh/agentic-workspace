# AW Completion-Cost Session Log Analysis

Date: 2026-06-23

Scope: pre-work analysis for #1680 from the long dogfooding chat, PR #1689, and recent local command logs.

## Evidence Sources

- Long running Codex chat ending in PR #1689.
- PR #1689: `codex/dogfooding-completion-cost-fixes`.
- Recent command logs under `scratch/command-logs/`, especially repeated `20260622-23*.log` workspace-test failures.
- #1680 grounding comment: https://github.com/rickardvh/agentic-workspace/issues/1680#issuecomment-4777077961

## Observed Cost Sinks

| Sink | Cost type | Evidence | Likely owner |
| --- | --- | --- | --- |
| Long chat continuity | reread/re-grounding | Context compression still carried dense lane history, corrections, PR state, and old decisions. | operator pattern plus AW handoff/digest surfaces |
| Large ordinary AW payloads | output noise | Small tasks still surfaced nested startup/implement context: memory packets, installed-state compatibility, skill catalogs, planning candidates, delegation, acceptance, and proof. | workspace ordinary outputs |
| Repeated broad proof runs | proof/test cost | `make test-workspace` failed repeatedly before focused fixes isolated proof command liveness behavior. | proof selection and repair-loop guidance |
| Duplicate failure logs | review/repair churn | Workspace-test logs reached roughly 40-50 KB with many downstream failures from one root cause. | command-log/proof failure summarization |
| Giant runtime files | reread/re-grounding | Targeted edits in `workspace_runtime_primitives.py` and Planning `installer.py` still required file-level reasoning. | runtime symbol routing and proof inventory |
| PR comment handling overhead | review/repair churn | A PR-body/doc closure-boundary comment required broad PR/comment/CI inspection and local proof routing. | GitHub review delta surface |
| Pasted shaping material | operator/tool friction | Long ChatGPT shaping text was useful once but expensive to carry across future turns. | operator guidance plus lane/session digest |
| Source-checkout uv rebuilds | provider/tool friction | A read-only `start` rebuilt/reinstalled local packages during this capture turn. | local dev invocation/cache/runtime packaging |

## Follow-Up Issues

- #1692 - Add compact lane/session digest for fresh-session continuation.
- #1693 - Cluster command-log failures before rerunning broad proof.
- #1694 - Add broad-proof retry ladder to reduce premature full-suite reruns.
- #1695 - Tighten ordinary output budgets and selector-first defaults.
- #1696 - Add PR comment delta packet for review-response turns.
- #1697 - Route giant runtime edits by symbol-level working set.
- #1698 - Record operator guidance for external shaping and fresh-session lanes.

## Suggested First Tranche

Start #1680 with a small tranche that makes the new-session operating model cheaper immediately:

1. #1692 lane/session digest.
2. #1693 command-log failure clustering.
3. #1694 broad-proof retry ladder.

This tranche targets the largest observed avoidable costs without weakening proof or closure. #1695 is likely the next high-leverage tranche, but should be shaped carefully because ordinary outputs also carry hard blockers and safety-critical proof/residue signals.

## Operating Guidance For Next Session

- Start a fresh session for #1680.
- Use #1680 and this artifact as durable context instead of replaying the old chat.
- Keep long external shaping in issue comments or review artifacts; paste only short pointers and decision boundaries.
- Treat the first #1680 slice as optimization work, not as a reason to hide proof, intent, or residue signals.
