# Compatibility Policy And Stable Surfaces

This page names which repository surfaces are stable today, which remain mutable while active work is in progress, and which are generated mirrors that must stay in sync with their canonical sources.

Use it when you need to decide whether a change is a normal refresh, an intentional contract update, or a breaking surface change that needs broader review.

## Stable Today

- Repo-owned guidance and planning surfaces: `AGENTS.md`, `TODO.md`, `ROADMAP.md`, `docs/execplans/`, `docs/design-principles.md`, `docs/boundary-and-extraction.md`, `docs/maturity-model.md`, `docs/which-package.md`, and this policy.
- Maintainer-facing root docs that describe commands, routing, review bars, or package selection.
- Public CLI entrypoints and module names that are already part of the checked-in contract.
- Package READMEs and packaging metadata that define the current installable entrypoints.

## Mutable Today

- Active milestone fields inside execplans.
- The `TODO.md` now-row and the roadmap candidate queue.
- Current-state notes such as `memory/current/` and other weak-authority reorientation surfaces.
- Implementation details inside package source trees while the surrounding contract is still settling.

## Generated Surfaces

- Root generated docs and manifests such as `tools/agent-manifest.json`, `tools/AGENT_QUICKSTART.md`, and `tools/AGENT_ROUTING.md`.
- Product-managed mirrors under `.agentic-workspace/` that are rendered from canonical manifests or package payloads.
- Any installed surface that is explicitly described as a generated output rather than a hand-edited source.

## What Counts As Breaking

- Renaming or removing a stable CLI entrypoint or installed surface without a compatible replacement.
- Moving ownership of a stable surface between repo-owned and product-managed layers without updating the canonical docs.
- Changing the meaning of a stable surface so existing adopters would need to change how they use it.
- Letting a generated surface drift away from its canonical source.

## What Does Not Count As Breaking

- Pruning completed work from `TODO.md` or `ROADMAP.md`.
- Rewording an active execplan while the milestone is still in progress.
- Refreshing generated docs after the source manifest or renderer changes.
- Tightening maintainer guidance without changing the owned surface contract.

## Review Rule

If a change touches a stable surface, check the adopter-facing docs, maintainer docs, and generated outputs together before treating the change as done.

If the answer depends on chat context or local folklore, the policy is not explicit enough yet.