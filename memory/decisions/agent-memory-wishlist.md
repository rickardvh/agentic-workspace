# Agent Memory Wishlist

## Status

Active

## Scope

- Durable product-feedback wishlist for making the memory system more effective for agents using it in real repository work.

## Applies to

- `AGENTS.md`
- `memory/index.md`
- `memory/manifest.toml`
- `.agentic-memory/WORKFLOW.md`
- `src/repo_memory_bootstrap/`

## Load when

- Turning day-to-day memory-system friction into concrete product improvements.
- Deciding which memory-system weakness should be addressed next.
- Evaluating whether a newly observed problem belongs in the longer-lived product wishlist.

## Review when

- A wishlist item is implemented, split, superseded, or no longer worth keeping.
- Real use in this repo exposes a new recurring weakness in routing, note maintenance, or memory ergonomics.

## Failure signals

- Product feedback stays trapped in chat or scratch notes instead of checked-in memory.
- The same memory-system friction is encountered repeatedly without becoming an explicit improvement target.
- Wishlist items turn into vague aspirations instead of concrete pressure on design or implementation.

## Rule or lesson

- Keep this note focused on recurring product-level improvements, not one-off bugs or task chatter.
- Prefer specific weaknesses and intended outcomes over vague statements that memory should be “better”.
- If an item becomes a current implementation choice, move it into `memory/current/active-decisions.md` or the relevant work item instead of keeping two live homes.
- If an item is resolved, shrink or remove it rather than preserving stale wishlist residue.

## Wishlist

- Improve routing confidence without telemetry: explain not just what was returned, but where the routing decision is weak or relying on fallback behaviour.
- Keep durable truth, calibration artefacts, and temporary review surfaces sharply separated so routing feedback never feels like ordinary durable memory.
- Make note compression easier: shrinking, stubbing, merging, or deleting a note should feel like a supported workflow, not manual bookkeeping.
- Push stable human-facing guidance into canonical docs earlier and more explicitly so memory does not accumulate documentation residue.
- Handle “weakly useful” notes better, especially where a note may help but should not be part of the default routed set.
- Keep aggregate routing views compact and trustworthy: enough to show drift, noise, and improvement, without turning into dashboards or telemetry systems.
- Make the path from repeated prose to repo-owned skill cheaper and more obvious when a memory-adjacent workflow is clearly reusable.
- Add earlier pressure when a note is becoming multi-home across domain, invariant, runbook, or current-context roles.
- Make it easier to tell when a note should stop existing; this is the highest-value long-term memory hygiene improvement.

## Implications

- Prefer improvements that reduce ambiguity and maintenance cost over features that merely increase memory volume.
- Treat this repo as a standing product-feedback environment: friction encountered here should normally become either a concrete improvement, a durable note, or a conscious rejection.
- When in doubt, prioritise changes that help agents read less, compress notes faster, and trust routing decisions more.

## Verify

- Check whether the wishlist still matches current product pain points exposed by real repo use.
- Confirm that active wishlist items are not already duplicated in current decisions or implemented behaviour.

## Verified against

- `AGENTS.md`
- `memory/current/active-decisions.md`
- `memory/index.md`
- `memory/manifest.toml`
- `.agentic-memory/WORKFLOW.md`

## Last confirmed

2026-04-05 during agent-memory wishlist capture
