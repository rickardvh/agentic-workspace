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
2. Use this skill to decide what information or procedure is useful. Keep sufficient direct work direct. Acquire evidence when missing, stale, conflicting or repeatedly reconstructed information could materially change the task, a required claim or justified future work; use the [evidence sufficiency boundary](evidence.md), not a mandatory context-gathering phase.
3. When exact current state, admission, action, effect, or recovery matters, use the repository's configured AW invocation. Prefer `.agentic-workspace/config.local.toml` `[workspace].cli_invoke` when present, then `.agentic-workspace/config.toml` `[workspace].cli_invoke`, then the package default `agentic-workspace`. Source checkouts may provide a repo-local invocation through their bootstrap instructions.
4. Ask the Rust-backed surface for the smallest current answer needed. `start` may compose current owners and return exact requests/actions/references; dedicated public operations may be used when the request maps directly to them. Consume returned exact identity/currentness instead of reconstructing hidden packet fields.
5. If reusable specialized procedure would materially help, discover or select the relevant semantic skill route. A knowledgeable agent may select a known current leaf directly; an unfamiliar agent may inspect a bounded route branch. Do not load a fixed skill/module tree.
6. Perform the user's work with ordinary judgment. Use exact owner-returned requests/actions for bounded mutations and effects; do not manufacture effect-bearing actions or edit managed state as a substitute for an owner operation.
7. Reconcile only what this work changed or may now claim. A local action succeeding, an owner becoming quiescent, and the user's intended outcome being complete are different facts.

The compiled operating decision is a deterministic information/action substrate for this procedure and other clients. It is not a universal model-facing workflow that every agent must execute step by step.

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

## Guardrails

- Human/repository intent remains source-owned; this skill is procedure, not policy authority.
- The Rust core remains the sole deterministic ordinary semantic/effect authority; Python, TypeScript, JSON, and native surfaces are projections/bindings over it.
- Natural-language or keyword matching may aid discovery but cannot decide genuine semantic applicability or effects.
- Do not bypass current owner restrictions because another skill or advisory source appears permissive.
- Do not infer whole-task completion from one owner's local result.
- Do not preserve historical protocol or guidance merely because it existed; prefer the current owner and current procedure.
