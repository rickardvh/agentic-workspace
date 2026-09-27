# Maintainer agent-facing audit (#3670)

This child covers the repository maintainer skills and their registry, plus the
repo-specific Memory skills discovered during the aggregate inventory. That scope
was added to the issue before their edits. All use the canonical
[writing guide](../../.agentic-workspace/instructions/agent-facing-style.md).

| Source | Disposition | Reason |
| --- | --- | --- |
| `tools/skills/foundation-stability-check/SKILL.md` | keep | Scoped source checks and stopping conditions identify current ownership evidence without ambient validation. |
| `tools/skills/github-issue-creation/references/prepare-and-publish.md` | merge | Moves exact issue request and recovery protocol behind the entry; adds bounded unknown-identity recovery. |
| `tools/skills/github-issue-creation/SKILL.md` | rewrite | Names the concrete task, current source or missing evidence; preserves authority and exact request identifiers. |
| `tools/skills/github-issue-shaping/references/evidence-and-output.md` | merge | Moves the existing shaping checklist, examples and output schema behind the entry; corrects optional continuation wording. |
| `tools/skills/github-issue-shaping/SKILL.md` | rewrite | Names the concrete task, current source or missing evidence; preserves authority and exact request identifiers. |
| `tools/skills/ownership-ledger-check/SKILL.md` | keep | Scoped source checks and stopping conditions identify current ownership evidence without ambient validation. |
| `tools/skills/path-consolidation-check/SKILL.md` | rewrite | Names the concrete task, current source or missing evidence; preserves authority and exact request identifiers. |
| `tools/skills/pr-review-recheck/prepare.py` | keep | Read-only executable protocol and CLI descriptions name exact inputs; no prose tutorial or API behavior change. |
| `tools/skills/pr-review-recheck/procedure.md` | rewrite | Names the concrete task, current source or missing evidence; preserves authority and exact request identifiers. |
| `tools/skills/pr-review-recheck/references/closure.md` | keep | Focused deeper protocol supplies exact evidence, decision limits and recovery after the entry has established the task. |
| `tools/skills/pr-review-recheck/references/compatibility.md` | keep | Focused deeper protocol supplies exact evidence, decision limits and recovery after the entry has established the task. |
| `tools/skills/pr-review-recheck/references/decision.md` | keep | Focused deeper protocol supplies exact evidence, decision limits and recovery after the entry has established the task. |
| `tools/skills/pr-review-recheck/references/eligibility.md` | keep | Explicit independent reviewer prerequisites, trusted source and implementer/spawned-agent disqualification remain intact. |
| `tools/skills/pr-review-recheck/references/proof.md` | keep | Focused deeper protocol supplies exact evidence, decision limits and recovery after the entry has established the task. |
| `tools/skills/pr-review-recheck/references/recheck.md` | rewrite | Names the concrete task, current source or missing evidence; preserves authority and exact request identifiers. |
| `tools/skills/pr-review-recheck/references/scope.md` | keep | Focused deeper protocol supplies exact evidence, decision limits and recovery after the entry has established the task. |
| `tools/skills/pr-review-recheck/SKILL.md` | rewrite | Names the concrete task, current source or missing evidence; preserves authority and exact request identifiers. |
| `tools/skills/README.md` | rewrite | Names the concrete task, current source or missing evidence; preserves authority and exact request identifiers. |
| `tools/skills/REGISTRY.json` | rewrite | Names the concrete task, current source or missing evidence; preserves authority and exact request identifiers. |
| `tools/skills/self-improvement-dogfooding/SKILL.md` | keep | Concrete activation conditions, repair classes, human direction boundary and no-finding stop already guide the next action. |
| `.agentic-workspace/memory/repo/skills/memory-reporting/SKILL.md` | rewrite | Names the concrete task, current source or missing evidence; preserves authority and exact request identifiers. |
| `.agentic-workspace/memory/repo/skills/package-context-inspection/SKILL.md` | rewrite | Names the concrete task, current source or missing evidence; preserves authority and exact request identifiers. |
| `.agentic-workspace/memory/repo/skills/README.md` | keep | Registry/README names concrete source families and selection scope; no additional operation is promised. |
| `.agentic-workspace/memory/repo/skills/REGISTRY.json` | keep | Registry/README names concrete source families and selection scope; no additional operation is promised. |
| `.agentic-workspace/memory/repo/skills/vague-prompt-domain-understanding/SKILL.md` | rewrite | Names the concrete task, current source or missing evidence; preserves authority and exact request identifiers. |

## Repairs and evidence

Issue shaping now starts with the action and closure rule; its detailed assumption
checklist and output fields are a linked reference. Creation starts with prepared
fields, authorized publication and verification; exact helper schemas and recovery
remain in a reference. Review choices name missing evidence. The existing reviewer
eligibility gate and trusted-baseline requirement are unchanged.

The fresh maintainer reader correctly separated implementation from later evidence,
refused self/spawned approval, selected a bounded recheck and left ordinary work
free of dogfooding triage. It identified unclear parent timing, unknown issue-number
recovery, obsolete refresh wording and unspecified prior-obligation entries. These
were repaired at their sources. Its extra reads followed the linked evidence,
publication, eligibility and recheck references. No wrong action or user intervention
was observed. This exercise is author validation, not independent review.

The aggregate pass found current repo-specific skills still pointing at retired
package directories and `agentic-memory` diagnostics. They now point to native
module sources, current Make targets and the authorized correction procedure.
Historical package-context notes are already marked retired in the Memory manifest;
their historical bytes and disposition are preserved.

## Test disposition

At the user's explicit direction, issue #3673 owns removal of all prose-wording
assertion tests and the testing-strategy update. This patch removes the five
prose-only cases encountered in the edited families: four in
`tests/test_github_workflow_skills.py` and the correction-retention wording test in
`tests/test_skills_first_interface.py`. They assert wording, not executable behavior.
No synonym assertions or snapshots replace them. Existing native consumer,
preparation, payload parity and structural checks remain. #3673 stays open for its
repository-wide audit and strategy update.

The surviving interface, selected-procedure, trusted review preparation and issue
body helper suites passed: **42 tests**. This validates unchanged executable
mechanisms, not comprehension. Reader evidence addresses the latter. Broader
runtime testing is unnecessary unless a source/protocol defect is found.

Markdown, local links, registry/generator parity and whitespace checks passed.
