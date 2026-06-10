# Documentation Status

This page is a compact role and freshness index for the documentation set. It is not the package overview. For current shipped behavior, start with [docs/index.md](index.md) and the `docs/package/` hierarchy; use this page only to understand each document's role and freshness.

Last reviewed: 2026-05-01.
Refresh route: update this index when a public doc changes role, starts owning current capability claims, or is reviewed for freshness.

| Doc | Audience | Authority class | Currentness status | Owns current capability or vision | Refresh route |
| --- | --- | --- | --- | --- | --- |
| [`README.md`](../README.md) | external adopters and evaluators | public entrypoint | current | stable product positioning and install starting point | Review on public positioning or preset policy changes; keep detailed status in secondary docs. |
| [`docs/index.md`](index.md) | external adopters, evaluators, and agents | documentation and owner map | current | primary navigation hierarchy and canonical owner map for repeated shipped-package concepts | Review when the documentation hierarchy changes or a repeated concept changes owner. |
| [`docs/package/overview.md`](package/overview.md) | adopters and evaluators | shipped package explanation | current | root package, presets, runtime model, and first-party parts | Review when package footprint, presets, or first-contact behavior changes. |
| [`docs/package/lifecycle.md`](package/lifecycle.md) | adopters and agent operators | shipped package explanation | current | lifecycle and context command model | Review when root CLI command roles or audiences change. |
| [`docs/package/commands.md`](package/commands.md) | adopters and agent operators | shipped package explanation | current | human map of the shipped root CLI surface | Review when root CLI command roles or audiences change. |
| [`docs/package/installed-surfaces.md`](package/installed-surfaces.md) | adopters and repository owners | shipped package explanation | current | installed host-repo file surfaces and ownership model | Review when installed payload or ownership boundaries change. |
| [`docs/package/modules.md`](package/modules.md) | adopters and technical reviewers | shipped package explanation | current | first-party module profiles and responsibilities | Review when module registry profiles or module roles change. |
| [`docs/package/knowledge-routing.md`](package/knowledge-routing.md) | adopters, agents, and planning reviewers | shipped package explanation | current | knowledge routing and source authority model for startup, task posture, closeout, Memory, Planning, issues, docs, and external sources | Review when route triggers, source authority classes, posture fields, freshness policy, or capture obligations change. |
| [`docs/package/contracts.md`](package/contracts.md) | technical reviewers | shipped package explanation | current | relationship between contract data, schemata, generated docs, and runtime outputs | Review when contract tooling or reference generation changes. |
| [`docs/which-package.md`](which-package.md) | adopters choosing install shape | public selector explanation | current | current package and preset positioning | Keep aligned with `agentic-workspace defaults --section install_profiles --format json`. |
| [`docs/architecture.md`](architecture.md) | technical reviewers | architecture explanation | current | current architecture summary | Review when module boundaries, lifecycle routing, or registry behavior changes. |
| [`docs/design-principles.md`](design-principles.md) | maintainers and reviewers | doctrine | current | design rationale and product constraints | Review when doctrine changes; do not use as the first current-capability matrix. |
| [`docs/maturity-model.md`](maturity-model.md) | maintainers and evaluators | maturity signal | current | package maturity and adoption expectations | Review when package maturity or public support promises change. |
| [`docs/module-capability-contract.md`](module-capability-contract.md) | maintainers and integration reviewers | internal contract | current | first-party module capability contract | Review when descriptor fields or module registry guarantees change. |
| [`docs/extension-boundary.md`](extension-boundary.md) | integration reviewers | boundary doctrine | current | plugin/extension non-support boundary and gates | Review when external module or plugin support moves closer to public API. |
| [`docs/ecosystem-roadmap.md`](ecosystem-roadmap.md) | maintainers and roadmap readers | roadmap doctrine | current | long-horizon ecosystem stance | Review when extraction stance or external package sequencing changes. |
| [`docs/agent-os-capabilities.md`](agent-os-capabilities.md) | architecture reviewers | long-horizon capability map | current but vision-oriented | vision and capability taxonomy, not first-contact shipped status | Review when a capability category, home, or extraction stance changes. |
| [`docs/maintainer/`](maintainer/) | maintainers | source-checkout maintenance section | current | maintainer-only workflow, validation, dogfooding, and review bars | Review when maintainer docs move or new maintainer-only docs are added. |
| [`docs/maintainer/contributor-playbook.md`](maintainer/contributor-playbook.md) | maintainers | maintainer workflow reference | current | source-checkout contribution workflow | Review when maintainer commands, closeout expectations, or package-boundary workflow changes. |
| [`docs/maintainer/maintainer-commands.md`](maintainer/maintainer-commands.md) | maintainers | source-checkout operational reference | current | maintainer command map | Review when proof, generation, or maintenance commands change. |
| [`docs/reference/`](reference/) | technical reviewers and implementers | generated contract reference | current | field-level schema documentation generated from source schemata | Regenerate from schemata; do not hand-edit generated pages. |
| [`docs/reviews/`](reviews/) | maintainers and auditors | historical evidence | historical/current as dated | evidence, not first-line product promise | Add new reviews instead of rewriting old evidence except for clear hygiene fixes. |

Status buckets used in this repo:

- `current`: reviewed against the current public package shape.
- `current but vision-oriented`: still relevant, but not a shipped-capability selector.
- `historical/current as dated`: useful evidence whose date and purpose limit its authority.
