# Package Overview

`agentic-workspace` turns static repository agent guidance into a programmable, repo-native operating context and control system.

The repository preserves a bounded set of context because it materially affects agent behavior. AW selects the relevant part for the current task, environment, and decision, then compiles one compact operating contract: what matters now, what action is supported, what constraints apply, what deeper procedure is relevant, and what may be claimed afterward.

AW is an amortized coordination layer. It should add structure only when that structure costs less than future rediscovery, repair, proof ambiguity, wrong-owner work, or handoff loss.

## Core model

The product has two core concerns:

1. **Operating context** — source-owned context whose current or durable availability can change how an agent should operate.
2. **Dynamic control** — task-shaped selection and composition of that context and applicable repo policy into one current operating decision and action envelope.

Operating context is deliberately narrower than general repository knowledge. AW does not mirror or semantically model the whole repository. Ordinary source, docs, tests, history, and other canonical content remain in their existing owners. Rich semantic retrieval, indexing, RAG, or knowledge graphs are possible future module capabilities rather than core requirements.

## Programmable instruction model

Repo customization should be more than a set of switches choosing prewritten behavior. A repository should be able to state bounded conditional control such as:

> when these authoritative task/path/owner/capability/evidence facts apply, surface this context or procedure, require or nominate this typed action/evidence/human decision, or restrict this effect/claim.

The intended internal normal form is:

```text
source-owned facts
+ bounded instruction clauses
+ available skills and typed operations
+ module capabilities/results
                    ↓
        existing operating-decision compiler
                    ↓
          current operating contract
```

This is not a second compiler. The existing operating decision remains authoritative; specialized config and domain declarations should converge on or compile into the smallest shared control semantics they actually have in common.

The roles are deliberately separate:

- **facts** belong to their existing owners and remain independently fresh/revisioned;
- **instruction clauses** add bounded applicability plus a control effect, not domain state;
- **skills** contain lazily loaded procedure;
- **typed operations** own effectful action and mutation authority;
- **modules** add new facts, capabilities, procedures, operations, and result semantics without adding new global instruction operators.

A useful effect vocabulary should remain closed and small: surface relevant context/procedure, route or require a typed operation, require evidence or a human decision, restrict an effect, or limit a claim. The clause itself should not mutate state.

Composition should be deterministic and authority-preserving. Lower-authority input cannot widen higher-authority permission; restrictions and requirements compose conservatively; incompatible control effects surface a conflict instead of relying on hidden order; provenance and input revisions remain inspectable.

The current product already contains specialized precursors—workflow obligations, assurance/proof declarations, scoped instructions, skill routing, target/correction guidance, configuration projections, and module contributions. They are not yet one public general-purpose instruction API, and they should not be mechanically replaced by a larger rule language. First normalize overlap internally, then expose only authoring semantics that repeatedly prove useful.

## Ordinary loop

The conceptual loop is:

### Resolve

Use the current task, authoritative repo context, environment/runtime facts, applicable instruction policy, and admitted capability contributions to derive the smallest trustworthy operating contract.

Only decision-relevant information should be first-line. Deeper context and procedures remain behind selectors, skills, operations, or owners.

### Act

Follow the current typed/routed action. The action may be a Workspace operation, repo-owned operation, routed skill, module operation, bounded recovery, or explicit human decision.

AW should constrain the operating envelope without scripting ordinary implementation judgment.

### Reconcile

Admit the result to the correct owner, determine what changed, update claim/continuation state, route any future-relevant residue, and resolve again when work remains.

Closeout is simply reconciliation that reaches a justified terminal outcome.

The existing compiled operating-decision and typed-action architecture is the implementation center of this loop. `resolve -> act -> reconcile` is a conceptual simplification, not a second runtime model.

## What ships

The coordinated distribution currently includes:

- the `agentic-workspace` root CLI and compiled operating-decision/routing behavior;
- package-managed skills and thin startup adapters;
- contracts for operations, authority, ownership, proof, reports, selectors, modules, lifecycle, and installed surfaces;
- JSON schemata and generated reference projections;
- first-party Planning, Memory, and Verification module packages;
- installable payload used to create the `.agentic-workspace/` host-repo enclave.

The current Python distribution bundles the first-party modules for lifecycle convenience. That packaging decision does not make their domains part of the core architecture.

## Modules

Modules are peer extensions of what the operating loop can know and do.

A module author describes the module's domain—identity/compatibility, ownership, relevance, resources/procedures/typed operations, and result/effect semantics. Workspace derives how those declarations participate in its loop; modules do not implement three mandatory resolve/act/reconcile hooks or define new global control operators.

Contribution dimensions are optional. Domain state stays under the module owner. Workspace composes only the bounded current effect needed for the operating decision.

The current first-party modules are examples:

- **Planning** — active execution continuity and bounded intent;
- **Memory** — learned anti-rediscovery repository knowledge;
- **Verification** — reusable soft-verification protocols, evidence, and known gaps.

See [Modules](modules.md) and [Extensibility and public boundary](../extension-boundary.md).

## Repo customization

A host repository can program AW's dynamic control without creating a module. Repo-owned config, obligations, skills, canonical guidance, ownership, proof declarations, and repository operations can all affect the current operating contract.

The long-term goal is a **smaller programming surface**, not a larger policy framework: specialized authoring formats may remain where they carry domain meaning, but overlapping applicability/effect semantics should be normalized instead of spawning more peer knobs, stages, forces, packet types, or runtime branches.

Keep hard repo authority distinct from machine-local capability/preferences and from module-owned policy. A growing `posture` vocabulary is not itself a product goal; the useful output is the resulting current constraint or action.

## External adapters

External adapters project or transport stable AW operations into agents, IDEs, CLIs, MCP-style clients, or vendor workflows.

The dependency remains inverted: the adapter knows about AW. AW does not need a marketplace, adapter registry, credentials, or vendor lifecycle in core.

## Command surface

Commands are affordances for the current question, not the product mental model.

Common routes include:

- `start` to resolve first-contact context and the next action;
- `implement` when changed paths are already known;
- `summary`, proof operations, module operations, or specialized skills when the current contract routes there;
- diagnostics such as `report`, `doctor`, `ownership`, and generated references only when deeper inspection is needed.

The acting agent should not have to infer a command sequence from documentation.

Cross-cutting instruction semantics normalize internally to source-owned facts and bounded clauses. Clauses can only surface or prefer existing capabilities, require a source-owned satisfier, or restrict an action, effect, operation, or claim. They cannot grant authority, execute code, or become a general rule or obligation store. `start` and `implement` expose the explanation on demand through `--select instruction_clause_projection`.

## Ownership model

Keep one primary owner per concern:

- canonical repo content stays repo-owned;
- Workspace owns cross-cutting dynamic-control and instruction-effect composition plus stable action/authority boundaries;
- modules own their domain semantics and state;
- repo customization owns host policy and bounded instruction declarations;
- external adapters own transport/vendor integration;
- local state supports machine-specific operation but is not shared authority by existence alone.

Generated operating contracts and instructions project those owners; they do not replace them.

## Trust model

AW is not a sandbox. Repository-configured shell/proof/executor routes inherit caller filesystem and credential authority. Treat the repository and configured commands as trusted before execution. See [Threat model and supply-chain boundary](../security/threat-model.md).

## Documentation layers

Use the smallest layer that answers the question:

1. **Conceptual docs** explain operating context, programmable dynamic control, modules, trust, and adoption.
2. **Generated/current-value references** answer exact command, schema, module, and footprint questions from machine-readable authority.
3. **Maintainer docs** own source-checkout generation, validation, release, and dogfooding procedure.
4. **Reviews and Planning** retain dated evidence and active implementation shaping rather than current public doctrine.

Read next:

- [Architecture](../architecture.md)
- [Modules](modules.md)
- [Lifecycle and context commands](lifecycle.md)
- [Installed surfaces](installed-surfaces.md)
- [Contracts and references](contracts.md)
- [Documentation index](../index.md)