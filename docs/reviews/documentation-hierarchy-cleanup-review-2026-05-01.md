# Documentation Hierarchy Cleanup Review - 2026-05-01

## Scope

This review covers the public and maintainer-facing Markdown documentation that explains the shipped `agentic-workspace` package and its first-party parts. It supports #635 and #636.

Reviewed surfaces:

- `README.md`
- `docs/*.md`
- `docs/reference/*.md`
- `docs/reviews/*.md`
- package README files under `packages/*/README.md`
- shipped package contracts in `src/agentic_workspace/contracts/*.json`
- installed contract docs under `.agentic-workspace/docs/*.md`

The review goal is not to make every page shorter. The goal is to make the documentation navigable by abstraction level so a reader can understand what the package ships without code archaeology.

## Findings

### 1. There is no primary package documentation spine

Severity: high.

`README.md` is a reasonable product entrypoint, but the next hop fans out to `which-package`, `architecture`, `documentation-status`, `maturity-model`, package READMEs, and maintainer workflow. None of those pages owns the simple hierarchy:

1. What is the shipped root package?
2. What does it install into a host repository?
3. What are the root lifecycle and context commands?
4. What are the selectable module capabilities?
5. Which contracts and generated references define the precise shapes?

The closest source of truth is split between `src/agentic_workspace/contracts/module_registry.json`, `src/agentic_workspace/contracts/cli_commands.json`, package READMEs, and historical review inventories. That is exactly the code archaeology the documentation should remove.

Recommended action: create `docs/index.md` and `docs/package/` as the current-behavior spine before moving older pages.

### 2. Top-level `docs/` mixes current product explanation, maintainer doctrine, operational policy, and historical evidence

Severity: high.

The current flat namespace makes pages with very different authority look equivalent:

- current shipped behavior: `which-package.md`, `architecture.md`
- maintainer workflow: `contributor-playbook.md`, `maintainer-commands.md`
- doctrine and review criteria: `design-principles.md`, `operational-affordance-design.md`, `collaboration-safety.md`
- internal contract doctrine: `integration-contract.md`, `module-capability-contract.md`, `extension-boundary.md`
- historical evidence: `docs/reviews/*.md`
- generated schema reference: `docs/reference/*.md`

`docs/documentation-status.md` tries to classify this, but it is itself another flat page and does not give readers the conceptual path from shipped package to subparts.

Recommended action: keep `docs/reference/` and `docs/reviews/`, add an explicit user-facing package section, and move or re-index maintainer and doctrine pages behind secondary navigation.

### 3. Generated schema reference is improving, but it is carrying explanatory pressure it should not own

Severity: medium.

`docs/reference/*.md` now has better field descriptions, but the generated pages still answer contract-shape questions, not product-understanding questions. A user should not have to read `workspace-report.md`, `startup-context.md`, or `module-registry.md` to understand how `start`, `summary`, `report`, `proof`, Memory, and Planning fit together.

Recommended action: each conceptual package page should link down to the relevant generated reference pages only after it explains the behavior in prose.

### 4. The package READMEs are useful but too deep to be second-hop docs

Severity: medium.

`packages/memory/README.md` and `packages/planning/README.md` contain strong descriptions of Memory and Planning, but they also include package-local install paths, stability details, skills, command summaries, optional payload behavior, and development commands. They are appropriate package references, not the first explanation of the root package's module model.

Recommended action: add short root-level module overview pages that explain when each module is selected, what it installs, and what it owns. Link to package READMEs for package-local details.

### 5. Several existing review artifacts already contain the inventory needed for cleanup, but they are hidden as history

Severity: medium.

`docs/reviews/visible-product-surface-inventory-2026-04-26.md` and `docs/reviews/shipped-payload-surface-inventory-2026-04-29.md` already classify core entrypoints, secondary surfaces, generated adapters, payload files, and hidden machinery. Those records should inform the new package docs, but readers should not be sent into dated reviews for the current answer.

Recommended action: promote the stable conclusions into current package docs and keep the review files as evidence.

### 6. The maintainer playbook is doing too much

Severity: medium.

`docs/contributor-playbook.md` is valuable, but it has become a dense router for startup, ownership, validation lanes, dogfooding, package boundaries, design guardrails, and review expectations. That is useful for maintainers, but it should not sit beside user-facing package explanation as if it were a normal next read.

Recommended action: move or re-index maintainer-only material under a maintainer section and leave `README.md` pointing to it only for contributor workflows.

### 7. Current docs overuse status and doctrine as navigation

Severity: medium.

The reader often gets sent to status or doctrine pages before seeing the object model. `documentation-status.md`, `design-principles.md`, `maturity-model.md`, and `agent-os-capabilities.md` are useful once the product shape is known. They are poor substitutes for a package map.

Recommended action: make shipped behavior the first hierarchy, then status, doctrine, maturity, and roadmap as supporting material.

## Proposed Target Shape

Keep this lightweight at first:

```text
README.md
docs/
  index.md
  package/
    overview.md
    lifecycle.md
    installed-surfaces.md
    commands.md
    modules.md
    contracts.md
  reference/
    *.md
  maintainer/
    contributor-playbook.md
    maintainer-commands.md
    design-principles.md
    operational-affordance-design.md
    dogfooding-feedback.md
  reviews/
    *.md
```

The exact paths can change, but the separation should hold:

- `docs/package/`: current shipped behavior and conceptual hierarchy.
- `docs/reference/`: generated contract/schema details.
- `docs/maintainer/`: source-checkout maintenance and internal operating rules.
- `docs/reviews/`: dated evidence, audits, and cleanup justification.
- doctrine/roadmap pages: linked as supporting material, not first-contact package docs.

## First Cleanup Slice

Implement #635 with new docs before moving files:

1. Add `docs/index.md` as the navigation root.
2. Add `docs/package/overview.md` explaining the root package, first-party modules, presets, and ordinary host-repo workflow.
3. Add `docs/package/lifecycle.md` explaining `init`, `start`, `summary`, `report`, `proof`, `doctor`, `upgrade`, and `uninstall` by abstraction level.
4. Add `docs/package/installed-surfaces.md` explaining what gets written into a host repo and who owns each surface.
5. Add `docs/package/modules.md` summarizing Memory and Planning without duplicating their full READMEs.
6. Add `docs/package/contracts.md` explaining how contract JSON, JSON schemata, generated reference docs, and runtime outputs relate.

Then implement #636 by re-indexing or moving old pages after the new spine exists.

## Cleanup Candidates

Promote stable content into current docs:

- `docs/reviews/visible-product-surface-inventory-2026-04-26.md`
- `docs/reviews/shipped-payload-surface-inventory-2026-04-29.md`
- `src/agentic_workspace/contracts/module_registry.json`
- `src/agentic_workspace/contracts/cli_commands.json`
- module README summaries from `packages/memory/README.md` and `packages/planning/README.md`

Move or re-index as maintainer-only:

- `docs/contributor-playbook.md`
- `docs/maintainer-commands.md`
- `docs/dogfooding-feedback.md`
- `docs/installed-contract-design-checklist.md`
- `docs/operational-affordance-design.md`
- `docs/source-payload-operational-install.md`
- `docs/lazy-discovery-measurements.md`
- `docs/benchmarking-contract.md`

Keep as supporting doctrine or status:

- `docs/design-principles.md`
- `docs/maturity-model.md`
- `docs/ecosystem-roadmap.md`
- `docs/agent-os-capabilities.md`
- `docs/extension-boundary.md`
- `docs/module-capability-contract.md`
- `docs/integration-contract.md`
- `docs/collaboration-safety.md`

Keep as generated or historical:

- `docs/reference/*.md`
- `docs/reviews/*.md`

## Non-Goals

- Do not delete historical reviews in the first pass.
- Do not rewrite all generated reference pages by hand.
- Do not move package README files into root docs.
- Do not make `.agentic-workspace/docs/` the public documentation spine; those are installed/product-managed contract surfaces and should remain behind package docs or compact CLI routes.

## Dogfooding Notes

No new product bug was found that needs an immediate issue beyond #635 and #636. The review confirms those two issues are the right current owners:

- #635 owns the missing navigable package spine.
- #636 owns reclassification and cleanup of existing docs after that spine lands.

The main dogfooding lesson is that generated reference quality matters, but it cannot substitute for a layered explanation of the shipped package.
