# Agent-facing source audit (#3665)

The accepted style guide is in #3666/#3667. The implementation is divided into
three complete source families:

| Child | Audit | PR |
| --- | --- | --- |
| #3668 core | [Core dispositions and reader evidence](agent-facing-core-audit.md) | #3671 |
| #3669 modules | [Planning and Memory dispositions](agent-facing-module-audit.md) | #3672 |
| #3670 maintainers | [Maintainer dispositions and reader evidence](agent-facing-maintainer-audit.md) | #3674 |
| #3687 runtime decisions | [Human decision producers and reader evidence](human-decision-audit.md) | #3690 |

These audits disposition every tracked file in the canonical core, instruction,
Planning, Memory, repository Memory-skill, maintainer and fallback directories,
including registry selection prose and host prompts. New detail references are
listed with their owning family. The root pointer, compatibility pointer, embedded
bootstrap authoring text, skill schema and generator are in the core audit.

## Additional pointer

| Source | Disposition | Reason |
| --- | --- | --- |
| `.agentic-workspace/AGENTS.md` | keep | Managed adapter explicitly names the canonical startup source and current owner operations; no extra runtime command is required. |

No current `prompts/` tree or Verification skill tree exists. The six Memory host
launcher prompts are in the module audit. Test fixtures and archived Planning
records are evidence/history, not current entry procedures. Retired Memory notes
remain historical according to their manifest dispositions. Human architecture
and generated API documentation are linked reference material, not new copies of
the canonical writing guide. Future installed authoring work #3548 must reuse the
guide linked from `docs/package/skill-authoring.md`; this change does not claim that
future skill exists.

## Generated copies

Every following file is **generated-from-source**. Its authoritative source is the
same path after removing `src/core/payload/`. The existing interface generator
checks this declared set; edits were made only at the sources. Registry activation
entries are generated from the procedure fences in their own source families.

- `src/core/payload/.agentic-workspace/WORKFLOW.md`
- `src/core/payload/.agentic-workspace/fallback/no-cli-policy.json`
- `src/core/payload/.agentic-workspace/fallback/no_cli_startup.py`
- `src/core/payload/.agentic-workspace/planning/skills/README.md`
- `src/core/payload/.agentic-workspace/planning/skills/REGISTRY.json`
- `src/core/payload/.agentic-workspace/planning/skills/bootstrap-upgrade/SKILL.md`
- `src/core/payload/.agentic-workspace/planning/skills/planning-assignment/SKILL.md`
- `src/core/payload/.agentic-workspace/planning/skills/planning-assignment/procedure.md`
- `src/core/payload/.agentic-workspace/planning/skills/planning-assignment/references/assessment.md`
- `src/core/payload/.agentic-workspace/planning/skills/planning-assignment/references/binding.md`
- `src/core/payload/.agentic-workspace/planning/skills/planning-assignment/references/local.md`
- `src/core/payload/.agentic-workspace/planning/skills/planning-assignment/references/manual.md`
- `src/core/payload/.agentic-workspace/planning/skills/planning-assignment/references/recovery.md`
- `src/core/payload/.agentic-workspace/planning/skills/planning-assignment/references/return.md`
- `src/core/payload/.agentic-workspace/planning/skills/planning-closeout-trust/SKILL.md`
- `src/core/payload/.agentic-workspace/planning/skills/planning-closeout-trust/procedure.md`
- `src/core/payload/.agentic-workspace/planning/skills/planning-closeout-trust/references/finish.md`
- `src/core/payload/.agentic-workspace/planning/skills/planning-closeout-trust/references/intent.md`
- `src/core/payload/.agentic-workspace/planning/skills/planning-reporting/SKILL.md`
- `src/core/payload/.agentic-workspace/planning/skills/planning-review-continuation/SKILL.md`
- `src/core/payload/.agentic-workspace/planning/skills/planning-review-continuation/procedure.md`
- `src/core/payload/.agentic-workspace/planning/skills/planning-review-continuation/references/continuation.md`
- `src/core/payload/.agentic-workspace/planning/skills/planning-review-continuation/references/triage.md`
- `src/core/payload/.agentic-workspace/planning/skills/planning-work/SKILL.md`
- `src/core/payload/.agentic-workspace/planning/skills/planning-work/procedure.md`
- `src/core/payload/.agentic-workspace/planning/skills/planning-work/references/continuity.md`
- `src/core/payload/.agentic-workspace/planning/skills/planning-work/references/intake.md`
- `src/core/payload/.agentic-workspace/planning/skills/planning-work/references/structure.md`
- `src/core/payload/.agentic-workspace/skills/REGISTRY.json`
- `src/core/payload/.agentic-workspace/skills/workspace-instruction-correction/SKILL.md`
- `src/core/payload/.agentic-workspace/skills/workspace-instruction-correction/procedure.md`
- `src/core/payload/.agentic-workspace/skills/workspace-instruction-correction/references/destination.md`
- `src/core/payload/.agentic-workspace/skills/workspace-instruction-correction/references/instructions.md`
- `src/core/payload/.agentic-workspace/skills/workspace-instruction-correction/references/opportunity.md`
- `src/core/payload/.agentic-workspace/skills/workspace-instruction-correction/references/other.md`
- `src/core/payload/.agentic-workspace/skills/workspace-intent-discovery/SKILL.md`
- `src/core/payload/.agentic-workspace/skills/workspace-intent-discovery/procedure.md`
- `src/core/payload/.agentic-workspace/skills/workspace-intent-discovery/references/intent.md`
- `src/core/payload/.agentic-workspace/skills/workspace-intent-discovery/references/shape.md`
- `src/core/payload/.agentic-workspace/skills/workspace-proof-selection/SKILL.md`
- `src/core/payload/.agentic-workspace/skills/workspace-proof-selection/procedure.md`
- `src/core/payload/.agentic-workspace/skills/workspace-proof-selection/references/claim.md`
- `src/core/payload/.agentic-workspace/skills/workspace-proof-selection/references/execute.md`
- `src/core/payload/.agentic-workspace/skills/workspace-proof-selection/references/learning.md`
- `src/core/payload/.agentic-workspace/skills/workspace-proof-selection/references/receipt.md`
- `src/core/payload/.agentic-workspace/skills/workspace-proof-selection/references/recovery.md`
- `src/core/payload/.agentic-workspace/skills/workspace-proof-selection/references/select.md`
- `src/core/payload/.agentic-workspace/skills/workspace-resources/SKILL.md`
- `src/core/payload/.agentic-workspace/skills/workspace-resources/procedure.md`
- `src/core/payload/.agentic-workspace/skills/workspace-resources/references/build.md`
- `src/core/payload/.agentic-workspace/skills/workspace-resources/references/cleanup.md`
- `src/core/payload/.agentic-workspace/skills/workspace-resources/references/hygiene.md`
- `src/core/payload/.agentic-workspace/skills/workspace-resources/references/operation.md`
- `src/core/payload/.agentic-workspace/skills/workspace-resources/references/recovery.md`
- `src/core/payload/.agentic-workspace/skills/workspace-resources/references/select.md`
- `src/core/payload/.agentic-workspace/skills/workspace-setup-jumpstart/SKILL.md`
- `src/core/payload/.agentic-workspace/skills/workspace-setup-jumpstart/procedure.md`
- `src/core/payload/.agentic-workspace/skills/workspace-setup-jumpstart/references/boundaries.md`
- `src/core/payload/.agentic-workspace/skills/workspace-setup-jumpstart/references/consequences.md`
- `src/core/payload/.agentic-workspace/skills/workspace-setup-jumpstart/references/package.md`
- `src/core/payload/.agentic-workspace/skills/workspace-setup-jumpstart/references/selection.md`
- `src/core/payload/.agentic-workspace/skills/workspace-startup/SKILL.md`
- `src/core/payload/.agentic-workspace/skills/workspace-startup/procedure.md`
- `src/core/payload/.agentic-workspace/skills/workspace-startup/references/constraints.md`
- `src/core/payload/.agentic-workspace/skills/workspace-startup/references/evidence.md`
- `src/core/payload/.agentic-workspace/skills/workspace-startup/references/ordinary.md`
- `src/core/payload/.agentic-workspace/skills/workspace-startup/references/owners.md`
- `src/core/payload/.agentic-workspace/skills/workspace-startup/references/reconcile.md`
- `src/core/payload/.agentic-workspace/skills/workspace-startup/references/unavailable.md`

## Evidence and acceptance

The baseline and revised startup readers both handled direct work, a scoped edit
restriction and an uncertain write without wrong actions. The quiet control used
no AW command; the entry became shorter (500 to 457 words). Revised readers also
exercised correction, proof, setup, resource, module and maintainer decisions; family audits record
confusion and repairs. These are bounded author-side usability observations, not
independent acceptance or evidence of lower provider cost. No token/cost savings
claim is made. Structural and executable checks are recorded with each child.

All three children still require external independent review. Tests and these
reader exercises cannot close the parent or supply self-approval. The parent may
close administratively only when accepted children plus aggregate evidence satisfy
its full intended outcome. The separately requested prose-test cleanup is #3673;
removing five directly encountered cases here does not complete that issue.
