# Maintainer Documentation

This section is for source-checkout maintenance of this repository. It is not the first-contact documentation for users installing `agentic-workspace` into another repository.

## Core Maintainer Routes

- [Contributor playbook](contributor-playbook.md): routing, ownership, validation lanes, and maintainer workflow.
- [Maintainer commands](maintainer-commands.md): literal command index.
- [Dogfooding feedback](dogfooding-feedback.md): friction classification and admission policy.
- [Testing strategy](testing-strategy.md): inventory, consolidation, pruning, and contract-owned conformance guidance.
- [Contract-owned test replacement plan](contract-test-replacement-plan.md): sequencing and inventory for replacing regression tests with contract-owned conformance cases.
- [AW contract test replacement inventory](aw-contract-test-replacement-inventory.md): retained keep/convert/merge/delete record for AW-side generated-command behavior tests.
- [Generated command check inventory](generated-command-check-inventory.md): checked split between AW-owned generated-command proof and command-generation-owned generic target baselines.
- [Installed-contract design checklist](installed-contract-design-checklist.md): review bar for collaboration-sensitive installed surfaces.
- [Operational affordance design](operational-affordance-design.md): design review rubric for operational surfaces.
- [Ordinary caution action-shape audit](ordinary-caution-action-shape-audit.md): disposition table for ordinary warning and gate classes.
- [Planning continuation action-shape audit](planning-continuation-action-shape-audit.md): disposition table for active-owner and Planning continuation cautions.
- [Summary/status/preflight action-shape audit](summary-status-preflight-action-shape-audit.md): disposition table for recovery and status-adjacent caution outputs.

## Boundary And Measurement

- [Source, payload, and root install boundary](source-payload-operational-install.md): maintainer boundary between package source, shipped payload, and root install.
- [Lazy discovery measurements](lazy-discovery-measurements.md): framework for checking whether compact selectors beat broad reads.
- [Benchmarking contract](benchmarking-contract.md): benchmark shape and evaluation policy.

## Related Supporting Docs

- [Design principles](../design-principles.md)
- [Architecture](../architecture.md)
- [Integration contract](../integration-contract.md)
- [Module capability contract](../module-capability-contract.md)
- [Historical reviews](../reviews/)
