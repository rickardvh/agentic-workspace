# Shell Adapter Feasibility

Purpose: record the #400 shell-adapter decision for bash and PowerShell as downstream projections of the command-package definition. This is evidence/history, not ordinary startup input.

## Decision

Bash and PowerShell adapters are worth generating only as thin projection surfaces after the shared command-package definition is stable for Python and TypeScript.

Safe generated shell surfaces:

- command and option help derived from the shared definition
- argument validation that does not inspect repository state
- completion metadata where the target shell supports it cleanly
- wrapper invocation that delegates runtime behavior to the owning package
- effect and preflight hints rendered from the same operation metadata

Out of scope for generated shell adapters:

- runtime primitive behavior
- live workspace inspection
- rich JSON/report rendering beyond passing through runtime output
- host-repository, agent, or issue-tracker assumptions
- ordinary development requirements for shell-specific toolchains

## Proof Strategy

Shell adapter tests should follow the TypeScript pattern: generated fixtures plus container-selected proof. Docker is acceptable for generated shell proof, but ordinary Python development must not require bash, PowerShell, Node, or shell-specific package managers.

## Downstream Rule

Future shell work must start from `src/agentic_workspace/contracts/command_package_ir.json`. If a shell target needs data that is not in that IR, add the universal field only when Python and TypeScript can also consume it without learning shell-specific semantics.
