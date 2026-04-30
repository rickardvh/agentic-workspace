# Documentation Status

This page is a compact role and freshness index for the public documentation set. It helps readers distinguish current product capability from long-horizon doctrine, maintainer references, and historical evidence.

Last reviewed: 2026-04-30.
Refresh route: update this index when a public doc changes role, starts owning current capability claims, or is reviewed for freshness.

| Doc | Audience | Authority class | Currentness status | Owns current capability or vision | Refresh route |
| --- | --- | --- | --- | --- | --- |
| [`README.md`](../README.md) | external adopters and evaluators | public entrypoint | current | current capability summary and install starting point | Review on public positioning, preset policy, or capability-status changes. |
| [`docs/which-package.md`](which-package.md) | adopters choosing install shape | public selector explanation | current | current package and preset positioning | Keep aligned with `agentic-workspace defaults --section install_profiles --format json`. |
| [`docs/architecture.md`](architecture.md) | technical reviewers | architecture explanation | current | current architecture summary | Review when module boundaries, lifecycle routing, or registry behavior changes. |
| [`docs/design-principles.md`](design-principles.md) | maintainers and reviewers | doctrine | current | design rationale and product constraints | Review when doctrine changes; do not use as the first current-capability matrix. |
| [`docs/maturity-model.md`](maturity-model.md) | maintainers and evaluators | maturity signal | current | package maturity and adoption expectations | Review when package maturity or public support promises change. |
| [`docs/module-capability-contract.md`](module-capability-contract.md) | maintainers and integration reviewers | internal contract | current | first-party module capability contract | Review when descriptor fields or module registry guarantees change. |
| [`docs/extension-boundary.md`](extension-boundary.md) | integration reviewers | boundary doctrine | current | plugin/extension non-support boundary and gates | Review when external module or plugin support moves closer to public API. |
| [`docs/ecosystem-roadmap.md`](ecosystem-roadmap.md) | maintainers and roadmap readers | roadmap doctrine | current | long-horizon ecosystem stance | Review when extraction stance or external package sequencing changes. |
| [`docs/agent-os-capabilities.md`](agent-os-capabilities.md) | architecture reviewers | long-horizon capability map | current but vision-oriented | vision and capability taxonomy, not first-contact shipped status | Review when a capability category, home, or extraction stance changes. |
| [`docs/contributor-playbook.md`](contributor-playbook.md) | maintainers | maintainer workflow reference | current | source-checkout contribution workflow | Review when maintainer commands, closeout expectations, or package-boundary workflow changes. |
| [`docs/maintainer-commands.md`](maintainer-commands.md) | maintainers | source-checkout operational reference | current | maintainer command map | Review when proof, generation, or maintenance commands change. |
| [`docs/reviews/`](reviews/) | maintainers and auditors | historical evidence | historical/current as dated | evidence, not first-line product promise | Add new reviews instead of rewriting old evidence except for clear hygiene fixes. |

Status buckets used in this repo:

- `current`: reviewed against the current public package shape.
- `current but vision-oriented`: still relevant, but not a shipped-capability selector.
- `historical/current as dated`: useful evidence whose date and purpose limit its authority.

