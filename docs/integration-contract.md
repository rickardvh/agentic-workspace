# Module Interaction Contract

This page records the compact interaction contract for first-party modules under
the root `agentic-workspace` CLI. It is a boundary note, not a second module
manual. For module responsibilities, use [Modules](package/modules.md).

## Core Rule

One concern has one primary owner:

| Concern | Primary owner | May reference | Must not become |
| --- | --- | --- | --- |
| Active execution state | Planning | Memory, Verification, repo docs | durable knowledge base or backlog mirror |
| Durable repo knowledge | Memory | Planning state and repo docs as routing context | active task tracker or execution log |
| Verification protocols and bounded evidence | Verification | Planning refs, Memory lessons, Assurance requirements | CI runner, claim authority, or universal testing policy |
| Shared lifecycle and routing | Workspace root | selected module reports and manifests | hidden module policy owner |
| Generated references and adapters | Source contracts and generated outputs | module manifests and operation contracts | hand-edited source of truth |

## Operating Model

1. Workspace routes the agent to compact context and the selected modules.
2. Planning says what work is active and what continuation or closeout requires.
3. Memory says what durable knowledge is expensive to rediscover.
4. Verification says what evidence protocols, proof routes, bundles, or gaps are
   relevant.
5. The agent owns semantic judgment and completion claims using those facts.

Module interaction should reduce rereads and duplicated authority. If the same
guidance appears in multiple modules, tighten ownership instead of relying on
contributors to guess which copy is current.

## Residue Routing

After work finishes, route leftover detail by owner:

- active continuation or unfinished parent intent: Planning;
- durable anti-rediscovery lesson: Memory;
- reusable evidence protocol, bounded evidence, or known gap: Verification;
- stable human-facing guidance or policy: docs or contracts;
- one-off task narration already recoverable from code, tests, or PR history:
  drop it.

Writing nothing is valid when no durable residue exists. Broadly preserving
chat, plan prose, or raw logs is not proof of diligence.

## Source Precedence

Prefer the narrowest current owner:

1. module-managed active state and manifests for module-specific facts;
2. repo-owned docs or Memory for durable knowledge;
3. Verification records for evidence protocol and gap facts;
4. generated references only as derived contract projections;
5. dated reviews and archives only as historical evidence.

Historical archives are not current policy unless a current owner links to them
for that purpose.
