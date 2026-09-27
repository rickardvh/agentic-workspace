# Core agent-facing audit (#3668)

Baseline: `257340554` (merged #3667). This audit covers authoritative sources;
payload copies are derived and checked separately. Every row was read against
the canonical [writing guide](../../.agentic-workspace/instructions/agent-facing-style.md).

| Source | Disposition | Reason |
| --- | --- | --- |
| `.agentic-workspace/WORKFLOW.md` | rewrite | Names the situation, action and completion boundary with exact deeper links. |
| `.agentic-workspace/fallback/no-cli-policy.json` | keep | Exact pointer with read-only and unknown-state boundaries. |
| `.agentic-workspace/fallback/no_cli_startup.py` | keep | Returns only an exact startup pointer and unknown runtime status. |
| `.agentic-workspace/instructions/agent-facing-style.md` | keep | Canonical contract accepted in #3666/#3667; retained without a parallel guide. |
| `.agentic-workspace/instructions/documentation.md` | keep | Names the governing guide, authoring trigger, source regeneration and reviewer obligation. |
| `.agentic-workspace/instructions/github-issue-creation.md` | keep | Names both required skills and the first external-write boundary. |
| `.agentic-workspace/instructions/github-issue-refinement.md` | keep | Names changed issue fields, supporting reads and unavailable-procedure stop. |
| `.agentic-workspace/instructions/github-pr-completion.md` | keep | Explicit issue-completion trigger, required outcome and partial-work prohibition. |
| `.agentic-workspace/instructions/github-pr-review.md` | keep | Explicit implementer prohibition and independent-review path; permits remaining implementation. |
| `.agentic-workspace/instructions/local-worktree-policy.md` | keep | Exact selection/input details are locally anchored; preserve the supported contract and recovery boundary. |
| `.agentic-workspace/instructions/workspace-dogfooding.md` | keep | States maintainer trigger, concrete findings and report destination; requirements remain scoped. |
| `.agentic-workspace/instructions/workspace-operating.md` | keep | Names protected source, exact owner procedure, validation rule and separate completion claims. |
| `.agentic-workspace/instructions/workspace-ownership-audit.md` | keep | Scoped route resolves its named skill through use metadata; grants no write. |
| `.agentic-workspace/skills/REGISTRY.json` | rewrite | Rewrite selection summaries; derive activation text and revisions from procedure sources. |
| `.agentic-workspace/skills/workspace-instruction-correction/SKILL.md` | rewrite | Names the situation, action and completion boundary with exact deeper links. |
| `.agentic-workspace/skills/workspace-instruction-correction/procedure.md` | rewrite | Names the situation, action and completion boundary with exact deeper links. |
| `.agentic-workspace/skills/workspace-instruction-correction/references/destination.md` | rewrite | Names the situation, action and completion boundary with exact deeper links. |
| `.agentic-workspace/skills/workspace-instruction-correction/references/instructions.md` | rewrite | Names the situation, action and completion boundary with exact deeper links. |
| `.agentic-workspace/skills/workspace-instruction-correction/references/opportunity.md` | keep | Lists effective initiative modes and limits publication to its destination authority. |
| `.agentic-workspace/skills/workspace-instruction-correction/references/other.md` | keep | Names capture/nomination inputs and verifies the receiving source; no universal writer. |
| `.agentic-workspace/skills/workspace-intent-discovery/SKILL.md` | rewrite | Names the situation, action and completion boundary with exact deeper links. |
| `.agentic-workspace/skills/workspace-intent-discovery/procedure.md` | rewrite | Names the situation, action and completion boundary with exact deeper links. |
| `.agentic-workspace/skills/workspace-intent-discovery/references/intent.md` | keep | Provides clarification conditions, supported configuration field and practical examples. |
| `.agentic-workspace/skills/workspace-intent-discovery/references/shape.md` | keep | Defines work sizes and distinguishes implementation issues from reporting destinations. |
| `.agentic-workspace/skills/workspace-proof-selection/SKILL.md` | rewrite | Names the situation, action and completion boundary with exact deeper links. |
| `.agentic-workspace/skills/workspace-proof-selection/procedure.md` | rewrite | Names the situation, action and completion boundary with exact deeper links. |
| `.agentic-workspace/skills/workspace-proof-selection/references/claim.md` | keep | Names claim request, evidence fields, strict closeout and independent-review limits. |
| `.agentic-workspace/skills/workspace-proof-selection/references/execute.md` | keep | Exact proof.report action and separate result/continuation inspection. |
| `.agentic-workspace/skills/workspace-proof-selection/references/learning.md` | rewrite | Names the situation, action and completion boundary with exact deeper links. |
| `.agentic-workspace/skills/workspace-proof-selection/references/receipt.md` | rewrite | Names the situation, action and completion boundary with exact deeper links. |
| `.agentic-workspace/skills/workspace-proof-selection/references/recovery.md` | rewrite | Names the situation, action and completion boundary with exact deeper links. |
| `.agentic-workspace/skills/workspace-proof-selection/references/select.md` | keep | Defines the selection need and exact request; does not infer obligation from candidate count. |
| `.agentic-workspace/skills/workspace-resources/SKILL.md` | rewrite | Names the situation, action and completion boundary with exact deeper links. |
| `.agentic-workspace/skills/workspace-resources/procedure.md` | rewrite | Names the situation, action and completion boundary with exact deeper links. |
| `.agentic-workspace/skills/workspace-resources/references/build.md` | keep | Names disposable roots and creation lease; preserves unknown output. |
| `.agentic-workspace/skills/workspace-resources/references/cleanup.md` | rewrite | Names retain/release/remove operations and exact-path recovery; refuses forced cleanup. |
| `.agentic-workspace/skills/workspace-resources/references/hygiene.md` | rewrite | Names audit operation, shallow scope and preservation of unknown files. |
| `.agentic-workspace/skills/workspace-resources/references/operation.md` | keep | Names resource proposal and invocation with exact path preservation. |
| `.agentic-workspace/skills/workspace-resources/references/recovery.md` | keep | Names missing result and no-replay boundary with current recovery. |
| `.agentic-workspace/skills/workspace-resources/references/select.md` | keep | Defines when scratch or isolation is needed and keeps ordinary work in the existing checkout. |
| `.agentic-workspace/skills/workspace-setup-jumpstart/SKILL.md` | rewrite | Names the situation, action and completion boundary with exact deeper links. |
| `.agentic-workspace/skills/workspace-setup-jumpstart/procedure.md` | rewrite | Names the situation, action and completion boundary with exact deeper links. |
| `.agentic-workspace/skills/workspace-setup-jumpstart/references/boundaries.md` | rewrite | Exact source-build command and rebuild conditions; no alternate runtime authority. |
| `.agentic-workspace/skills/workspace-setup-jumpstart/references/consequences.md` | keep | Names configuration result fields, affected consumer checks and lost-reply recovery. |
| `.agentic-workspace/skills/workspace-setup-jumpstart/references/package.md` | keep | Exact setup requests, witness fields, scope, recovery and terminal conditions belong in this deeper reference. |
| `.agentic-workspace/skills/workspace-setup-jumpstart/references/selection.md` | keep | Names configuration behavior request and concern values; settled choices stop. |
| `.agentic-workspace/skills/workspace-startup/SKILL.md` | rewrite | Names the situation, action and completion boundary with exact deeper links. |
| `.agentic-workspace/skills/workspace-startup/procedure.md` | rewrite | Names the situation, action and completion boundary with exact deeper links. |
| `.agentic-workspace/skills/workspace-startup/references/constraints.md` | rewrite | Names the situation, action and completion boundary with exact deeper links. |
| `.agentic-workspace/skills/workspace-startup/references/evidence.md` | keep | Explains source coverage fields, sufficient evidence, conflicts and when to stop collecting. |
| `.agentic-workspace/skills/workspace-startup/references/ordinary.md` | rewrite | Names the situation, action and completion boundary with exact deeper links. |
| `.agentic-workspace/skills/workspace-startup/references/owners.md` | rewrite | Names the situation, action and completion boundary with exact deeper links. |
| `.agentic-workspace/skills/workspace-startup/references/reconcile.md` | rewrite | Names the situation, action and completion boundary with exact deeper links. |
| `.agentic-workspace/skills/workspace-startup/references/unavailable.md` | keep | Numbered fallback identifies exact read profile and preserves unknown runtime authority. |
| `AGENTS.md` | keep | Exact pointer names the startup source and read fallback; no runtime invocation implied. |
| `docs/package/skill-authoring.md` | rewrite | Names the situation, action and completion boundary with exact deeper links. |
| `src/core/src/native_adoption.rs` | keep | Embedded bootstrap text matches the short, explicit root pointer; implementation and API reference excluded. |
| `src/tooling/contracts/schemas/skill_spec.schema.json` | keep | Generated/API reference is kept exact; field descriptions already identify their objects. |
| `src/tooling/generate/generate_agent_interface.py` | keep | Derives mirrors from declared sources; no independent tutorial prose. |

## Generated surfaces

All declared copies of these sources under `src/core/payload/` are
**generated-from-source** using `src/tooling/generate/generate_agent_interface.py`.
They are not independent authoring surfaces. Activation entries in the registry
are likewise generated from the procedure fences. No merge/remove disposition
was selected: the references serve distinct decisions or exact transport details.

## Representative decisions

- Startup now names `affects` and the request that resolves a restriction, and
  introduces owner against the component responsible for a concrete record.
- Owner interaction defines request, action and carriage before its exact examples.
- Branches now describe missing input or an observed result; for example,
  “Disposition of observed learning” becomes “A returned lesson may prevent future rediscovery.”
- Instruction correction now explicitly reuses the existing filename. A fresh
  reader identified that ambiguity; the correction prevents a duplicate policy file.
- Public skill-authoring guidance links the canonical guide. The future installed
  authoring procedure remains owned by #3548 and must use the same principles.

## Evidence and limits

The baseline fresh reader chose direct work, preserved a blocked edit and avoided
replaying an uncertain write. The revised-source exercise also chose those actions,
and correctly handled instruction publication, receipt versus issue completion,
and implementer independence. No glossary or prior conversation was supplied.
The revised exercise identified the filename ambiguity above; no wrong action
or user intervention occurred. Missing scenario-specific request objects stayed
unknown rather than being invented. These are author-side usability exercises,
not independent PR review or measured reliability/economic improvement.

The startup entry shrank from 500 to 457 whitespace-delimited words. Both readers
chose zero AW calls for the supplied-text control; this establishes the bounded
quiet-entry behaviour, not token or monetary savings.

Validation: native binaries built. The initial 58-case run had one failure from
an obsolete prose-wording test. Updating its expected phrases did not prove the
procedure's meaning. That test is now deleted on the core PR itself, with no
replacement phrase, regex or snapshot assertion. The remaining structural and
native consumer tests establish executable contracts; fresh-reader exercises
supply the interpretation evidence. The surviving 15-case interface suite passed
again after deletion. Markdown lint, changed-source links, generator parity and
whitespace checks passed.
No permanent test or CI job was added. Existing native checks cover unchanged
mechanisms; fresh-reader exercises cover interpretation. Independent review remains
pending and is not supplied by these implementation-lineage exercises.

## Setup and resources reader

A separate fresh reader correctly kept a supplied-text edit direct, distinguished
artifact refresh from configuration effectiveness, selected scratch without a
worktree, and preserved owner-referenced evidence during cleanup. It followed only
the setup/resources links needed for those questions. It found vague fallback
pointers and an ambiguity between worktree preservation and owned disposable
scratch. The pointers now link the exact startup fallback and cleanup names the
resource type. The package link now says refresh and assessment. No wrong action
or user intervention was observed; this is author-side evidence, not independent
review. Generated parity, links, Markdown and commit hooks validate these repairs.

## Blocking-review repair

The core layer owns deletion of its obsolete correction-retention wording test.
Documentation reconciliation is published through Verification for the current
core audit and authoring guide, with unchanged group members retained only on
unchanged source evidence. This is bounded source reconciliation, not independent
approval or a reassessment of the documentation corpus.
