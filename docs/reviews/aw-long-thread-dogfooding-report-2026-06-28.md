# AW Long-Thread Dogfooding Report

Date: 2026-06-28

Reporter / runtime: Codex agent using the Agentic Workspace source checkout

Package source: source checkout at `v0.6.3` after release recovery

Run goal: report on AW experience across the long issue-triage, lane implementation, PR review, release recovery, and dogfooding thread.

Slice type: mixed long-running maintenance thread: issue intake, active lane work, stacked PRs, CI repair, release recovery, and closeout reflection.

Assurance level: medium. Evidence comes from the visible chat transcript, local AW command output, merged PRs, GitHub Actions runs, and the final `v0.6.3` release. This report does not claim to reconstruct every intermediate local state before compaction.

## Run Summary

Requested outcome:

- Ingest and prioritize open issues in a new branch from `master`.
- Group issues into lanes, promote lanes into active planning, implement lanes as PRs, address PR comments, fix CI/release failures, clean stale/completed issues, and eventually release.
- Dogfood AW while doing the work and report what the experience shows about current product state.

What landed:

- Issue and lane work progressed through a sequence of merged PRs, including #1805, #1806, #1807, #1808, #1810-#1825.
- Runtime packet/boundary and P2 lane work landed in stacked PRs, including #1816-#1823.
- The command-generation release promotion helper landed in #1824, then its explicit wheel SHA verification review concern was fixed before merge.
- The Linux release-runner local path leak failure was fixed in #1825.
- A manual coordinated bump published `v0.6.3`: <https://github.com/rickardvh/agentic-workspace/releases/tag/v0.6.3>.
- Durable dogfooding follow-up issues were filed from this report: #1826, #1827, #1828, #1829, #1830, #1831, #1832, #1833.

What did not land:

- No further implementation was done for the four new dogfooding follow-ups.
- Local installed payload state still reported `payload-upgrade-required` at the start of this report-writing turn; this report does not claim payload freshness.

Closure decision:

- Thread-level work is usable and released, but the dogfooding findings are routed follow-up, not closed product work.

Residue destination:

- Checked-in review artifact: this file.
- GitHub issues: #1826, #1827, #1828, #1829, #1830, #1831, #1832, #1833.

## Assurance And Proof

Required refs:

- `AGENTS.md` ordinary AW route and dogfooding instruction.
- `docs/maintainer/dogfooding-feedback.md`.
- `docs/host-repo-dogfooding-report-template.md`.

Control gates or blockers observed:

- AW consistently required `start` or `implement --changed` before substantive work.
- Changed-path proof selection blocked completion claims until proof ran.
- Generated-surface trust blocked freshness claims when generated package manifests changed.
- Installed-state compatibility surfaced payload drift and blocked claims of installed-state freshness.

Proof profiles selected during the thread included:

- `make test-workspace`
- `make lint-workspace`
- `make maintainer-surfaces`
- package-specific memory/planning proof
- generated command package freshness and operation conformance checks
- PR checks and release workflow inspection through GitHub Actions

Proof commands executed during the late thread included:

- `make test-workspace`
- `make lint-workspace`
- `make test-memory`
- `make lint-memory`
- `make test-planning`
- `make lint-planning`
- `uv run python scripts/check/check_generated_command_packages.py`
- `uv run python scripts/check/run_operation_conformance_tests.py --target all`
- `uv run python scripts/run_agentic_workspace.py defaults --section root_cli_authority --format json`
- release workflow run <https://github.com/rickardvh/agentic-workspace/actions/runs/28302436191>

Waivers, skips, or unavailable proof:

- During #1825, AW selected `uv run pytest tests/test_model_cli_harness.py -q`, but that file did not exist. The agent substituted the current relevant file, `tests/test_external_agent_evaluation_lane.py`, and filed #1826.

Trust state after proof:

- Release state is usable: `v0.6.3` published successfully.
- Local payload freshness remains partial: startup reported source-checkout payload drift after release.

## What AW Made Better

AW materially helped in four ways.

First, it gave a stable operating loop for a very long thread. The same `start` and `implement --changed` flow kept reestablishing branch state, changed paths, proof obligations, and claim boundaries after interruptions, PR comments, CI failures, release failures, and sleep/resume. Without that, the thread would have depended much more on chat memory.

Second, changed-path proof routing was usually valuable. For narrow helper work, AW selected the relevant workspace, lint, and maintainer surface proof. For release-owned package version edits, it expanded proof to package tests, generated command package checks, conformance, and defaults authority. That breadth was expensive, but appropriate for release identity.

Third, generated-surface and installed-state signals caught real hazards. During the manual release bump, generated TypeScript package manifests were explicitly marked as generated surfaces requiring freshness proof. During this report turn, installed-state compatibility exposed payload drift instead of letting the agent imply source and installed payload were synced.

Fourth, recent work improved visible recovery. The local checkpoint and candidate-route improvements from #1810/#1814 made resume context more explicit. Runtime packet owner/boundary work from #1816-#1823 made the P2 runtime decomposition easier to reason about. The command-generation promotion helper from #1824 removed a manual release-pinning task and was strengthened by the review comment requiring explicit wheel digest verification.

## Where AW Still Cost Work

The largest cost was orientation and obligation discovery. Early in the thread, the agent did not proactively convert dogfooding observations into issues until the user pointed back to `AGENTS.md`. That is an agent failure, but it also shows that the dogfooding obligation is not yet visible enough in the ordinary closeout path. Filed #1829.

The second cost was stale or incorrect proof selection. AW selected a non-existent harness test file during release repair. The agent recovered, but required proof should not contain dead paths when the current repository has an obvious replacement. Filed #1826.

The third cost was release recovery. After #1824 merged, the release workflow failed in proof. #1825 fixed the Linux-specific failure, but because #1825 did not touch package-affecting paths, its semver label did not publish a new release. The user had to request a manual coordinated bump to `0.6.3`. Filed #1828.

The fourth cost was source-checkout installed payload drift. AW reported the drift, but the thread showed the sync could still be missed during active work, and the user had already called out that this should be more automatic. Filed #1827.

## Friction Items

| Observation | Evidence | Likely owner | Product should absorb? | Recommendation | Follow-up target |
| --- | --- | --- | --- | --- | --- |
| Required proof can name a deleted/non-existent test file. | `uv run pytest tests/test_model_cli_harness.py -q` selected for #1825 repair, but no such file existed. | product-general, proof selection | yes | fix proof selection or stale-path downgrading | #1826 |
| Source-checkout payload drift is visible but easy to leave unrepaired. | `installed_state_compatibility.status = payload-upgrade-required`; payload provenance still `v0.6.2` after `v0.6.3` release. | product-general, install/upgrade flow | yes | make drift self-healing or harder to miss | #1827 |
| Failed release recovery needed human knowledge of manual coordinated bump. | #1824 release failed; #1825 fix merged but skipped release; manual `Release v0.6.3` push was needed. | product-general, release workflow | yes | expose release recovery command or warning | #1828 |
| Dogfooding issue creation obligation was missed until human reminder. | User asked whether `AGENTS.md` already required proactive dogfooding analysis and issue creation. | product-general, closeout/reporting | yes | surface dogfooding signal routing as closeout obligation | #1829 |
| AW proof breadth was high for release identity changes. | Manual `0.6.3` bump required workspace, memory, planning, generated package, conformance, and defaults proof. | product-general, proof explanation | yes | preserve breadth but explain it as a release-proof profile | #1830 |
| PR comment handling worked once comments were surfaced. | #1824 comment led to default SHA verification and focused mismatch test, but the human had to prompt that a comment existed. | product-general, review continuation | yes | surface actionable PR comments during continuation | #1831 |
| Release CI diagnosis required GitHub log work outside AW. | `gh run view` found failing `test_model_cli_harness_repairs_exported_final_message_without_suppressing_warning`. | product-general, release recovery | yes | expose compact release CI failure summaries | #1832 |
| Low-risk direct-task output can still be costly to scan. | Startup for a docs/report task surfaced bulky checkpoint, installed-state, routine context, and selector detail. | product-general, workflow output | yes | keep low-risk direct-work output selector-first | #1833 |

## Operating-Cost Review

| Work shape | Required fields | Inferred or optional fields | Default output impact | Decision |
| --- | --- | --- | --- | --- |
| Low-risk direct task | changed paths, next safe action, narrow proof | detailed planning candidate pressure, broad routine context | sometimes too large | keep selector-first output; continue hiding detail behind selectors (#1833) |
| Medium-risk planned task | active lane, issue refs, intent satisfaction, proof obligations, PR/comment state | historical roadmap candidate counts | useful but still easy to miss dogfooding closeout | add explicit dogfooding signal status (#1829) |
| High/release task | release ownership, version set, generated-surface trust, lockfile state, full proof, CI/release run links | broad local checkpoint history | high but justified | preserve proof breadth; improve release recovery affordance (#1828) |

## Recent Work Impact

The recent work materially improved AW's ability to run itself:

- #1810/#1814 reduced fresh-session and checkpoint resume ambiguity by surfacing matched candidate routes.
- #1816-#1823 made runtime packet ownership and boundary evidence more explicit, which helped when review comments asked for mirror/parity confirmation.
- #1824 added a release promotion helper for `command-generation`, reducing a recurring maintainer task.
- The #1824 review fix changed explicit wheel URL mode from trusting supplied hashes to verifying wheel bytes by default, which improves release provenance.
- #1825 fixed a Linux-only proof failure that had escaped local Windows proof and blocked the release workflow.
- `v0.6.3` proves the release pipeline can now complete after those fixes.

The impact is not only code. The thread also exposed a pattern: AW is now strong enough to identify most gates, but agents still need some human steering to convert friction into durable issues, recover release state, and reconcile stale local payload state. The next improvements should focus less on adding new concepts and more on making those existing obligations impossible to miss.

## Privacy And Sensitivity

Omitted host details:

- No private host repository content is included. This report concerns the public AW source checkout and public GitHub refs.

Redactions or anonymization:

- None needed beyond not copying long command logs into this document.

Evidence that should stay local:

- Full chat transcript and local command scrollback.

## Conversion To Focused Issues

Created package issues:

- #1826: Required proof can name non-existent test files.
- #1827: Make source-checkout payload drift harder to miss.
- #1828: Make release recovery explicit after failed semver release.
- #1829: Surface dogfooding signal routing as a closeout obligation.
- #1830: Make release-proof breadth explain itself.
- #1831: Surface actionable PR comments during continuation.
- #1832: Expose release CI failure summaries for recovery.
- #1833: Keep low-risk direct-work output selector-first.

Dismissed as no new issue:

- No remaining review rows were intentionally left unissued after #1830-#1833. Positive observations are preserved in this report as impact evidence rather than separate work.

## Bottom Line

AW was effective enough to carry a long, high-change thread through issue triage, stacked PRs, review comments, CI repair, and a successful coordinated release. The main current gap is not lack of state; it is making the right state unavoidable at the right moment. The best next work is to reduce missed obligations and scan cost: stale proof paths, payload drift, release recovery commands, dogfooding signal routing, PR comment attention, release-failure summaries, and low-risk output compression.
