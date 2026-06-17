---
name: memory-consultation-and-residue
description: Decide whether Memory was consulted, whether durable residue exists, and where reusable learning or improvement signals should route. Use during closeout, intake, repeated-correction review, or any workflow that must distinguish no memory write from ignored memory.
---

# Memory Consultation And Residue

This is a bootstrap-managed core skill shipped with the payload under `.agentic-workspace/memory/skills/`. Add repo-specific sibling skills under `.agentic-workspace/memory/repo/skills/` instead of customising this core skill unless the shared reusable procedure itself changed.

Use this skill when a workflow needs an explicit Memory answer without turning Memory into a task tracker.

It makes three decisions visible:

- whether Memory was consulted
- whether durable residue exists
- where reusable learning or improvement pressure should route

## Workflow

1. Start from the structured surfaces before broad reading:
   - `agentic-workspace start --format json` for `memory_consult`
   - `agentic-workspace summary --format json` for active planning pressure
   - `agentic-workspace report --section closeout_trust --format json` when closeout evidence matters
   - `agentic-workspace memory route --files <paths...> --format json` when changed paths are known
   - `agentic-workspace memory promotion-report --mode remediation --format json` when improvement pressure may belong outside Memory
2. Classify `memory_consultation_status`:
   - `not_checked`: no routing or Memory index was inspected
   - `checked_none`: routing was inspected and no relevant note was found
   - `relevant_notes_found`: existing notes informed the work
   - `capture_candidate`: a durable lesson may belong in Memory
   - `routed_elsewhere`: the residue belongs in Planning, docs, tests, contracts, config, review, or an issue
   - `dismissed`: the signal is one-off or too weak to keep
   - `follow_up_required`: the decision needs a later owner or proof
3. Classify `durable_residue_decision`:
   - `repo_memory`
   - `local_memory`
   - `planning`
   - `docs`
   - `tests`
   - `contracts`
   - `config`
   - `review`
   - `issue`
   - `dismissed`
   - `none_found`
   - Treat legacy `memory` as an ambiguous compatibility label; prefer `repo_memory` or `local_memory` when recording a new decision.
4. Classify `improvement_signal_status` when a repeated correction, missing guardrail, or workflow friction appears:
   - `passive`
   - `accumulating`
   - `routed`
   - `promoted`
   - `stale`
   - `resolved`
5. Keep the proof separate from the write decision. Passing tests can prove behavior, but it does not prove Memory residue exists or that a memory write is appropriate.
6. If the answer is `repo_memory` or `local_memory`, use `memory-capture` for the actual write. If the answer is `routed_elsewhere`, name the owning surface and do not create a memory note just to show activity.
7. Use local-only Memory when the lesson is machine-local, user-local, runtime-specific, private, or low-confidence. Use repo-shared Memory only when the lesson should travel with the repository.

## Guardrails

- Red flag: No Memory write means no durable lesson exists.
- Use instead: Inspect Memory routing or promotion-report, then record `memory_consultation_status`, `durable_residue_decision`, and `improvement_signal_status`.
- Do not bulk-read Memory to prove diligence.
- Do not capture every chat correction, task step, validation transcript, backlog item, or plan history.
- Do not call `checked_none` unless the index, manifest route, or structured memory route was actually inspected.
- Do not call `dismissed` when the same issue has repeated or an explicit invariant/runbook/check would prevent rediscovery.
- Do not overwrite Planning closeout. Planning owns active intent, sequencing, issue linkage, and completion claims.
- Do not overwrite canonical docs, tests, contracts, or config when the durable fix belongs there.
- Do not put local execution quirks into checked-in repo Memory just because they are useful to the current agent.
- Do not use prompt keywords, filenames, or phrase markers as authority for a Memory write or storage decision.

## No-CLI fallback

If the CLI is unavailable, read only:

- `AGENTS.md`
- `.agentic-workspace/memory/repo/index.md`
- `.agentic-workspace/memory/repo/manifest.toml` when present
- already-routed notes named by those surfaces

Record the same three fields in the final answer or planning closeout, and avoid mutating managed state by hand.

## Typical outputs

- `memory_consultation_status=<status>`
- `durable_residue_decision=<route>`
- `improvement_signal_status=<status>`
- a short reason naming the inspected surface and the next owner
