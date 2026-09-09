---
name: foundation-stability-check
description: Recheck current Planning and Memory authority after a change to their install, state, or ownership boundaries. Use to detect competing operational sources; do not use as a general reconstruction checklist.
---

# Foundation Stability Check

Use this skill only when a change may alter which source owns Planning continuity,
Memory knowledge, or their installed repository state. Ordinary implementation does
not need this check merely because it touches Planning or Memory code.

## Check

1. Read the current `.agentic-workspace/OWNERSHIP.toml` and relevant system intent
   before asserting an authority boundary. Do not preserve an older topology merely
   because this skill once described it.
2. Confirm Planning semantic continuity remains with the current Planning owner and
   its declared execution-plan authority. Selector state, indexes, receipts, caches,
   generated payloads, and package fixtures may project or transport that authority;
   they must not become a competing semantic owner.
3. Confirm Memory remains durable advisory knowledge under its current owner. It
   must not become active Planning state, backlog authority, proof, or completion
   authority merely because a note is selected or persisted.
4. Confirm package bootstrap/generated copies are distribution artifacts rather
   than live repository operational state, and repo-owned sources remain repo-owned
   where the ownership ledger says so.
5. Run only the focused validation needed for the boundary actually changed. A
   broad root validation loop is not part of this skill by default.

## Typical surfaces

- `.agentic-workspace/OWNERSHIP.toml`
- `.agentic-workspace/planning/execplans/`
- `.agentic-workspace/planning/state.toml`
- `.agentic-workspace/memory/`
- package bootstrap/generated payload copies
