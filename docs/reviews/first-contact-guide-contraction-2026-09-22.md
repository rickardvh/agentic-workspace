# First-contact and current-guide contraction evidence

Implementation audit, 2026-09-22, for #3559 → #3558 → #3562. This is author
evidence, not independent PR review or acceptance. Baseline: `0f9bc5b84`.

## Scope and method

Enumerated README and Markdown under `docs/`, separating generated reference and
dated decision/review/release evidence. Inspected entry text and headings to
select current reader journeys and the largest narrative surfaces. The bounded
semantic audit below covers those selected pages, not a claim that every old
document is factually current. Counts are whitespace-delimited words including
examples/tables; they expose reading cost, not a quota. Before/after roles are
the intended reader job; mixed guides now delegate lookup to existing owners.

Historical evidence is retained in place, outside guide-first navigation. Exact
generated references remain source-owned, including the approximately 6,000-word
workspace/startup/implementer projections. No generated catalogue was shortened
for prose style. No new documentation registry or lint framework was introduced.

## Selected before/after inventory

`compress` includes deleting repeated or obsolete sections and merging their
remaining consequence into the relevant step. `reference` means expose the
existing specialist owner below the guide, not copy its contents into a new page.
`keep` for evidence preserves its historical subject rather than endorsing it as
current instructions. No whole-file deletion or physical move was necessary.

| Surface | Role after | Before → after words | Disposition | Reader-job judgement |
| --- | --- | ---: | --- | --- |
| [README.md](../../README.md) | guide | 1661 → 1471 | compress | Product introduction; setup is the human entry. |
| [docs/index.md](../../docs/index.md) | guide | 206 → 206 | keep | Reader-job navigation precedes exact lookup. |
| [docs/agentic-workspace-install.md](../../docs/agentic-workspace-install.md) | guide | 926 → 392 | compress | Install, setup, ordinary work; released-version boundary explicit. |
| [docs/everyday-use.md](../../docs/everyday-use.md) | guide | 771 → 730 | compress | Ordinary tasks; delete repeated machine choreography. |
| [docs/customization.md](../../docs/customization.md) | guide | 771 → 771 | keep | Choose shared/local scope and strongest owner. |
| [docs/troubleshooting.md](../../docs/troubleshooting.md) | guide | 724 → 724 | keep | Symptom-first recovery; fix changed installation anchor. |
| [docs/evidence-and-support.md](../../docs/evidence-and-support.md) | guide | 391 → 392 | compress | Release/support choices; exact accepted identity in generated reference. |
| [docs/package/installed-surfaces.md](../../docs/package/installed-surfaces.md) | guide | 855 → 855 | keep | Data, update and removal consequences remain necessary. |
| [docs/package/overview.md](../../docs/package/overview.md) | guide | 303 → 303 | keep | Short conceptual introduction. |
| [docs/package/modules.md](../../docs/package/modules.md) | guide | 350 → 350 | keep | Select modules by need. |
| [docs/package/commands.md](../../docs/package/commands.md) | reference | 479 → 479 | keep | Machine request/action examples for CLI integrators. |
| [docs/package/lifecycle.md](../../docs/package/lifecycle.md) | reference | 691 → 800 | reference | Detailed adoption protocol; human setup routes to installation guide. |
| [docs/package/contracts.md](../../docs/package/contracts.md) | guide | 283 → 287 | keep | Source selection and regeneration; repair retired source path. |
| [docs/package/skill-authoring.md](../../docs/package/skill-authoring.md) | guide | 2032 → 588 | compress | One method example; exact branches/fields link to existing fixture and contract. |
| [docs/package/scoped-instructions.md](../../docs/package/scoped-instructions.md) | reference | 1746 → 1746 | keep | Scope, protection and reconciliation semantics need exact treatment. |
| [docs/package/knowledge-routing.md](../../docs/package/knowledge-routing.md) | reference | 2474 → 2474 | keep | Source-kind, authority, trigger and freshness taxonomy is lookup material. |
| [docs/package/knowledge-gates.md](../../docs/package/knowledge-gates.md) | reference | 1415 → 1415 | keep | Gate fields, force levels and effects are lookup material. |
| [docs/package/output-profiles.md](../../docs/package/output-profiles.md) | reference | 729 → 729 | keep | Output-selection and budget contract, not entry reading. |
| [docs/package/generated-behavior-test-inventory.md](../../docs/package/generated-behavior-test-inventory.md) | evidence | 1416 → 1416 | keep | Retain historical migration/coverage dispositions. |
| [docs/documentation-style-guide.md](../../docs/documentation-style-guide.md) | guide | 722 → 858 | keep | Strengthen shortest-sufficient rule without deleting binding rules. |
| [docs/release-and-versioning.md](../../docs/release-and-versioning.md) | guide | 4412 → 849 | compress | Remove retired publication model and copied catalogues; link source owners. |
| [docs/architecture.md](../../docs/architecture.md) | guide | 780 → 780 | keep | Route contributors to the implementation owner. |
| [docs/extension-boundary.md](../../docs/extension-boundary.md) | guide | 632 → 632 | keep | Integration entry distinct from ordinary installation. |
| [docs/module-capability-contract.md](../../docs/module-capability-contract.md) | guide | 686 → 686 | keep | Capability author entry with exact Rust seam linked. |
| [docs/design-principles.md](../../docs/design-principles.md) | reference | 2210 → 2210 | keep | Source-owned product doctrine, not an installation tutorial. |
| [docs/agent-os-capabilities.md](../../docs/agent-os-capabilities.md) | reference | 2820 → 2820 | keep | Long-horizon taxonomy; April snapshot has factual currency limits noted below. |
| [docs/security/threat-model.md](../../docs/security/threat-model.md) | reference | 1035 → 1035 | keep | Security boundary completeness is valuable, not a length defect. |
| [docs/maintainer/index.md](../../docs/maintainer/index.md) | guide | 192 → 216 | compress | Separate release guide from specialist topology; expose skill/probe jobs. |
| [docs/maintainer/contributor-playbook.md](../../docs/maintainer/contributor-playbook.md) | guide | 825 → 825 | keep | Checkout, change, validate, PR; safety and proof steps remain. |
| [docs/maintainer/maintainer-commands.md](../../docs/maintainer/maintainer-commands.md) | reference | 480 → 480 | keep | Selected executable command lookup. |
| [docs/maintainer/model-cli-dogfooding-harness.md](../../docs/maintainer/model-cli-dogfooding-harness.md) | guide | 3063 → 583 | compress | One dry run; suite/runner own options; preserve execution limits. |
| [docs/maintainer/testing-strategy.md](../../docs/maintainer/testing-strategy.md) | reference | 2959 → 2959 | keep | Binding evidence design, retention and no-prune policy; length protects distinct obligations. |
| [docs/maintainer/repo-evidence-requirements.md](../../docs/maintainer/repo-evidence-requirements.md) | reference | 1800 → 1800 | keep | Source-owned evidence/authority policy and exact authoring semantics. |
| [docs/maintainer/native-release-topology.md](../../docs/maintainer/native-release-topology.md) | reference | 2302 → 2302 | reference | Exact paired/platform topology; candidate publication records remain specialist evidence, off the guide route. |
| [docs/maintainer/operating-carriage.md](../../docs/maintainer/operating-carriage.md) | reference | 2406 → 2406 | keep | Exact thin-host carriage and continuation contracts; example completeness matters. |
| [docs/maintainer/native-planning-creation.md](../../docs/maintainer/native-planning-creation.md) | reference | 2082 → 2082 | keep | Exact creation/currentness/custody and terminal-retention semantics. |
| [docs/maintainer/configuration-contraction.md](../../docs/maintainer/configuration-contraction.md) | evidence | 1908 → 1908 | keep | Named source-disposition and implementation-validation record, not required setup reading. |
| [docs/maintainer/chatgpt-review-continuation.md](../../docs/maintainer/chatgpt-review-continuation.md) | reference | 1857 → 1857 | keep | Specialist operational controls and recovery, separate from contribution guide. |
| [docs/maintainer/scheduled-tasks/README.md](../../docs/maintainer/scheduled-tasks/README.md) | guide | 817 → 817 | keep | Bind an external scheduler to existing task instructions. |
| [docs/maintainer/scheduled-tasks/aw-public-watch.md](../../docs/maintainer/scheduled-tasks/aw-public-watch.md) | reference | 1967 → 1967 | keep | Executable standing task requirements and boundaries; not an introductory guide. |
| [docs/maintainer/test-knowledge-inventory.md](../../docs/maintainer/test-knowledge-inventory.md) | evidence | 2588 → 2588 | keep | Historical coverage/knowledge migration ledger. |
| [docs/maintainer/final-reconstruction-frontier.md](../../docs/maintainer/final-reconstruction-frontier.md) | evidence | 1943 → 1943 | keep | Dated cumulative implementation and acceptance frontier. |
| [docs/maintainer/first-stable-safety-disposition.md](../../docs/maintainer/first-stable-safety-disposition.md) | evidence | 1603 → 1603 | keep | Retained safety and candidate dispositions. |
| [docs/reference/native-delegation-transport.md](../../docs/reference/native-delegation-transport.md) | reference | 2904 → 2904 | keep | Exact transport states and authority boundaries. |
| [.agentic-workspace/skills/workspace-startup/SKILL.md](../../.agentic-workspace/skills/workspace-startup/SKILL.md) | guide | 247 → 132 | compress | Short entry routes to selected procedure. |
| [.agentic-workspace/skills/workspace-startup/references/ordinary.md](../../.agentic-workspace/skills/workspace-startup/references/ordinary.md) | guide | 783 → 314 | compress | Ordinary current entry, then useful work; delete duplicated doctrine. |
| [.agentic-workspace/skills/workspace-setup-jumpstart/SKILL.md](../../.agentic-workspace/skills/workspace-setup-jumpstart/SKILL.md) | guide | 126 → 78 | compress | Short setup choice routes exact mechanics to selected branch. |

## Subtraction and retained detail

The three selected maintainer guides fall from 9,507 to 2,020 words
(79% less). Deleted material was not relocated into another
required guide:

- Release: the existing topology, ownership JSON, promotion checker and registry
  publishers retain exact contracts. The guide retains immutable subjects,
  authorization, failed-proof handling and same-tag recovery. Retired separate
  Python-package and `scripts/` claims were removed.
- Skill authoring: the existing change-note fixture and source decision contract
  retain the complete branch exchange. The guide retains confinement, currentness,
  authority and independent-review boundaries.
- Agent probes: the existing suite and runner own options and adapter settings.
  The guide retains model cost, credentials, sandbox limits and the distinction
  between local candidate evidence and public release proof.

The largest retained narratives have explicit roles in the table. Testing and
evidence policy retain distinct binding floors; schema/transport/carriage pages
retain exact lookup; migration and candidate records retain their dated subject.
They are not additional required pages in the ordinary user or contributor path.

This role audit does not settle the factual currency of old architectural
snapshots. In particular, `agent-os-capabilities.md` still carries April package
homes and the former `defaults` invocation. Its doctrine owner must reconcile
those facts before using them as present-product evidence. The present guide
routes use current installation, architecture and module owners instead. No trust
revision or unresolved source admission was advanced to hide that distinction.

## Walkthrough and acceptance boundary

The author checked these paths: user installation → setup → ordinary task;
contributor entry → release guide → exact promotion/topology owner; reusable
method → one SKILL example → optional branch fixture; probe guide → dry-run help
→ selected suite. Navigation presents guides before reference/evidence.

Installed candidate wheel and isolated npm-local/npm-global journeys establish
setup, startup-pointer/currentness and fresh-process routing. They do not establish
fresh-agent semantic obedience. The configured Assignment attempt for a bounded
read-only inventory rejected before effect; no worker result or proxy review is
claimed. Its failure and continuation remain with Planning and the existing
delegation evidence owner.

Public 1.2.0 installed successfully but rejected `setup` as an unknown command.
#3558 therefore still needs publication of #3559 and the current public journey;
#3562 still needs that child and externally initiated aggregate acceptance. These
three implementation PRs are ready for independent review, not self-approved.
