# Modules

`agentic-workspace` is the package. It composes first-party modules behind one root lifecycle and context CLI. Modules own domain behavior; the package root owns orchestration, shared config, compact routing, and lifecycle coordination.

## Module Profiles

| Profile | Modules | Checked-in footprint |
| --- | --- | --- |
| routing-only | none | root config, startup, ownership, workspace skills, module map, and report routing surfaces |
| memory | Memory | durable repo knowledge surfaces |
| planning | Planning | active execution state and execplan surfaces |
| verification | Verification | soft verification protocols and bounded evidence projections |
| full | Planning and Memory | both active work state and durable repo knowledge |

The AW package currently bundles first-party modules for simple `uvx` and `pipx` lifecycle use. That may change later, but the installed repository footprint is already selected by profile. The exact profile and component metadata is defined by the generated [Module registry](../reference/module-registry.md) and [Module capability](../reference/module-capability.md) references.

## Planning

Planning owns active execution state. Use it when work needs to stay bounded, resumable, and finishable across sessions.

Planning is good for:

- active queue state;
- bounded execution plans;
- handoff and restart contracts;
- proof expectations for active work;
- honest closeout and required continuation routing.

Planning is not a ticketing system, backlog manager, durable knowledge base, or broad documentation system.

Module implementation: [Planning README](../../packages/planning/README.md).

Command: `agentic-planning`.

## Memory

Memory owns durable repo knowledge that is expensive to rediscover. Use it when agents repeatedly relearn the same boundaries, runbooks, invariants, or subsystem orientation.

Memory is good for:

- durable technical facts;
- subsystem orientation;
- recurring failure lessons;
- authority boundaries;
- operator runbooks;
- routing hints that help agents read less.

Memory is not active task state, execution history, issue triage, or a replacement for canonical docs.

Module implementation: [Memory README](../../packages/memory/README.md).

Command: `agentic-memory`.

## Verification

Verification owns repo-native soft verification protocols, bounded evidence
records, known gaps, and proof route hints. Use it when executable tests are not
enough and the repo needs shared, reviewable verification expectations.

Verification is good for:

- declaring protocol activation by changed path, task marker, assurance
  requirement, proof profile, or planning ref;
- routing proof selection toward manual or semi-automated verification;
- recording bounded evidence summaries, transcript refs, residual risk, and
  stale conditions;
- keeping verification context repo-visible without turning AW into a browser
  automation platform.

Verification is not a generic test runner, compliance engine, UI automation
host, or global evidence store.

Module implementation: [Verification README](../../packages/verification/README.md).

Command: `agentic-verification`.

## Command Generation

`packages/command-generation/` is an internal implementation workspace for generic command package generation. It is not a host-repo module and is not part of the ordinary installed runtime.

Implementation reference: [Command generation README](../../packages/command-generation/README.md).

## Module Contracts

The module registry declares available modules, profiles, component metadata, and repository footprint policy. See [Module registry](../reference/module-registry.md) for the generated field reference. The lower-level command and component generation path is documented by [Command package IR](../reference/command-package-ir.md), [Command adapter generation](../reference/command-adapter-generation.md), and [Lifecycle generation readiness](../reference/lifecycle-generation-readiness.md).

