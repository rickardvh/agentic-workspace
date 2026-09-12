---
name: workspace-startup
description: Use Agentic Workspace as a skills-first repository competence layer. Read current policy from its owners, use precise Rust-backed tools for current facts and bounded effects, load specialized skills only when useful, and degrade honestly when no runtime is available.
---

# Agentic Workspace

This is the canonical ordinary agent procedure for an Agentic Workspace repository.

Agentic Workspace is **skills-first**: this skill teaches how to use the product. It does not own repository policy, current domain state, proof, or effect authority.

## Responsibility split

Keep these owners distinct:

- **skills** provide reusable procedure;
- **repository/local instructions and config** provide human- or repository-owned policy, constraints, preferences, and applicability;
- **domain owners** provide current Planning, Memory, Verification, Assignment, decision, and other state/evidence under their own lifetime;
- **Rust-backed CLI/native/Python/TypeScript/JSON operations** provide exact current information, validation/currentness, bounded mutations/effects, and recovery;
- **the agent or human** supplies semantic judgment and performs the actual work.

Do not copy mutable policy or current owner state into this skill. Do not treat a skill reference, route, or operating decision as mutation, proof, completion, or claim authority.

## Ordinary use

1. Read the repository/local instructions that apply to the work. Treat them as policy and constraints, not as a second procedural manual.
2. Use this skill to decide what information or procedure is useful. Keep direct/no-signal work direct; do not create AW artifacts merely to demonstrate AW use.
3. When exact current state, admission, action, effect, or recovery matters, use the repository's configured AW invocation. Prefer `.agentic-workspace/config.local.toml` `[workspace].cli_invoke` when present, then `.agentic-workspace/config.toml` `[workspace].cli_invoke`, then the package default `agentic-workspace`. Source checkouts may provide a repo-local invocation through their bootstrap instructions.
4. Ask the Rust-backed surface for the smallest current answer needed. `start` may compose current owners and return exact requests/actions/references; dedicated public operations may be used when the request maps directly to them. Consume returned exact identity/currentness instead of reconstructing hidden packet fields.
5. If reusable specialized procedure would materially help, discover or select the relevant semantic skill route. A knowledgeable agent may select a known current leaf directly; an unfamiliar agent may inspect a bounded route branch. Do not load a fixed skill/module tree.
6. Perform the user's work with ordinary judgment. Use exact owner-returned requests/actions for bounded mutations and effects; do not manufacture effect-bearing actions or edit managed state as a substitute for an owner operation.
7. Reconcile only what this work changed or may now claim. A local action succeeding, an owner becoming quiescent, and the user's intended outcome being complete are different facts.

The compiled operating decision is a deterministic information/action substrate for this procedure and other clients. It is not a universal model-facing workflow that every agent must execute step by step.

## Corrections and retention

Treat an explicit user or reviewer correction intended to change future behavior (for example, "work like this from now on") as reconciliation input. Apply it to the current work and route it through the current correction/instruction owner when available, using that owner's current scope and retention semantics. Do not broaden a task-local correction into repository or global policy. Keep one-off requests non-retained; if future intent or scope is unclear, clarify only what is needed before retaining it.

Use the owner's exact returned request/action and verify its outcome before claiming the correction was retained. If the native owner or supported persistence path is unavailable, surface the exact owner/path gap and state that retention is not established. Do not substitute an apology, chat promise, Memory note, invented persistence, or a direct managed-state edit for correction reconciliation. Repository visibility alone does not establish retention, including when executable AW is unavailable.

## Specialized skills and semantic routes

Specialized package or repository skills are progressive-disclosure units for genuinely reusable procedure, not one skill per owner, module, command, or phase.

Use semantic route discovery when task meaning or current facts indicate that another procedure may help. Route selection is agent judgment admitted as current structured context. Lexical hints may help discovery but cannot impose hard semantic applicability.

Rules:

- exact structured path/operation/source/owner facts take precedence when they already determine relevance;
- irrelevant skills stay absent from ordinary context;
- known current leaves should be directly selectable without walking an ancestry tree;
- once a relevant leaf is known, use its returned skill/procedure reference rather than rediscovering module topology;
- changing the task/current-work identity or route source may invalidate a carried route;
- loss of local route carriage falls back to fresh discovery rather than inventing repository authority;
- route/skill identity never widens effect, proof, publication, review, or claim authority.

Repository-owned skills and package-owned specialized skills participate through the same route mechanism. A new capability does not require a new core-owned skill slot.

## Exact tools without protocol copying

Use the public Rust-backed contract as a tool, not as prose to memorize.

For generic current resolution, a configured invocation may use `start --target . --task "<task>" --format json`. Known changed paths can be supplied with repeated `--changed` arguments. Compact output may include exact requests/actions/references and same-work carriage; optional detail remains lazy.

When a bounded owner request is returned, supply only the requested human/agent judgment or material and return the exact request through the supported public input. When an effect-bearing action is returned, execute that exact action through `invoke`; do not reconstruct it from schema-valid parts.

After an invocation, distinguish the effect outcome from continuation. Never retry a possibly committed effect merely because continuation failed. Use a current continuation when available; otherwise use exact re-entry/recovery or freshly resolve current state. Currentness is revalidated by the owner, not guaranteed by remembered model context.

Detailed schemas and packet fields belong to generated contracts/reference surfaces. Load them only when a client or debugging task actually needs them.

## When executable AW is unavailable

Use the **same skills-first model**, but stop at repository-readable facts.

1. Read this skill and the applicable repo instructions; do not switch to a competing no-runtime operating manual.
2. Use `.agentic-workspace/OWNERSHIP.toml` as the compact static orientation map for package-managed and repo-owned authority surfaces. Follow only the owner/source refs relevant to the current planning, shaping, review, or context question.
3. Read canonical repository sources directly where the ledger or relevant skill points: for example `SYSTEM_INTENT.md`, scoped instructions/config, Planning-owned records, relevant Memory material, or Verification/proof declarations. Prefer exact refs over broad `.agentic-workspace/**` scanning.
4. Treat only facts established by the repository bytes you actually read as known. Runtime capability, machine-local state not present in those bytes, live external state, current effect admission, and owner conclusions requiring executable resolution remain **unknown**.
5. Do not mutate managed owner state, claim an AW effect, manufacture proof/completion authority, or emulate `start` from static files. Record the exact source paths/revisions used so later reasoning can be reconsidered if those sources change.
6. If executable AW later becomes available, return to the ordinary path above; no new mental model or migration is required.

A missing, malformed, stale, or insufficient static surface is a reason to narrow the conclusion or request executable/current owner resolution—not to infer an operating decision.

## Directness and residue

- Do not read broad module state just because a capability exists.
- Do not create Planning, Memory, proof, handoff, or local scratch artifacts unless they have a real owner and future decision value.
- Do not turn `.agentic-workspace/local/` or other package-owned roots into general scratch space.
- Prefer the smallest sufficient query, skill, source read, or bounded operation.
- Stronger future agents may use less procedure when they already know what is relevant; durable policy/currentness/authority boundaries still apply.

## Guardrails

- Human/repository intent remains source-owned; this skill is procedure, not policy authority.
- The Rust core remains the sole deterministic ordinary semantic/effect authority; Python, TypeScript, JSON, and native surfaces are projections/bindings over it.
- Natural-language or keyword matching may aid discovery but cannot decide genuine semantic applicability or effects.
- Do not bypass current owner restrictions because another skill or advisory source appears permissive.
- Do not infer whole-task completion from one owner's local result.
- Do not preserve historical protocol or guidance merely because it existed; prefer the current owner and current procedure.
