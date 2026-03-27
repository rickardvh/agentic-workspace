# Agent Workflow Porting Checklist

Use this checklist when adapting the workflow from a proven repo into another one of your own projects.

The goal is not to copy every file mechanically. The goal is to recreate the useful operating properties:

- fast bootstrap
- clear precedence
- minimal rereading
- narrow validation
- durable task state
- durable knowledge only where justified
- low cleanup friction

## 0. Decide Whether The Target Repo Needs The Full Structure

- [ ] Confirm the target repo is complex enough to benefit from explicit agent routing.
- [ ] Confirm active work is getting lost across sessions, handoffs, or long tasks.
- [ ] Confirm the repo would benefit from checked-in task state rather than chat-only state.
- [ ] Confirm the repo would benefit from plan files for multi-step work.
- [ ] Skip the full structure for tiny repos; use only `AGENTS.md` and possibly `TODO.md` if that is enough.

## 1. Establish Precedence First

- [ ] Define a clear precedence order for conflicting guidance.
- [ ] Make explicit user instruction highest priority.
- [ ] Decide where the active execution plan sits in precedence.
- [ ] Decide whether root `AGENTS.md` or local descendant `AGENTS.md` wins for subtree-specific edits.
- [ ] Decide where task-state files such as `TODO.md` sit relative to durable memory.
- [ ] Write the precedence order down in `AGENTS.md`.

Recommended default:

1. explicit user request
2. active execution plan
3. root `AGENTS.md`
4. nearest descendant `AGENTS.md`
5. task-state files such as `TODO.md`
6. durable knowledge or memory
7. supporting docs and runbooks

## 2. Add A Root `AGENTS.md`

- [ ] Create a root `AGENTS.md` if the repo does not already have one.
- [ ] Keep it short enough to reread every session.
- [ ] Separate startup rules from domain detail.
- [ ] Add a small-task path so local changes do not force broad reads.
- [ ] Define what must be updated before a task ends.
- [ ] Add validation policy: prefer the narrowest check that proves the change.
- [ ] Add completion policy: update task state and only update durable knowledge when future decisions would change.

Minimum sections to include:

- [ ] precedence
- [ ] before doing work
- [ ] sources of truth
- [ ] execution policy
- [ ] validation policy
- [ ] completion contract
- [ ] blocker handling

## 3. Add A Lightweight Task Ledger

- [ ] Create `TODO.md` if active task state is currently scattered.
- [ ] Use it only for active and near-term work.
- [ ] Do not use it as a backlog, changelog, or architecture notebook.
- [ ] Choose a required entry shape for each task.
- [ ] Keep completed items pruned aggressively.

Suggested task fields:

- [ ] ID
- [ ] Status
- [ ] Next action
- [ ] Done when

## 4. Add Execution Plans Only When Justified

- [ ] Create `docs/execplans/` if tasks often span milestones or handoffs.
- [ ] Do not require a plan for every small task.
- [ ] Define a threshold for plan creation in `AGENTS.md` or quickstart.
- [ ] Keep one active milestone at a time per plan.
- [ ] Ensure plans are execution-oriented, not essay-like.

Suggested plan sections:

- [ ] goal
- [ ] non-goals
- [ ] active milestone
- [ ] touched paths
- [ ] invariants
- [ ] validation commands
- [ ] completion criteria
- [ ] drift log

## 5. Make Completed Plans Cheap To Ignore

- [ ] Choose an explicit active/archive convention.
- [ ] Either split plans into `active/` and `archive/`, or
- [ ] require a cheap completion marker such as `Status: complete`.
- [ ] Add `docs/execplans/README.md` explaining the convention.
- [ ] Ensure completed plans leave the hot path quickly.
- [ ] Do not leave old finished plans looking active.

## 6. Decide Whether To Add Durable Knowledge

- [ ] Only add a durable memory layer if cross-session technical knowledge is drifting.
- [ ] Keep durable knowledge separate from active task state.
- [ ] Add a routing index before adding a lot of notes.
- [ ] Give each durable fact one primary home.
- [ ] Prune or merge stale notes in the same change that invalidates them.

If using your reusable `memory/` package:

- [ ] Install or scaffold it into the target repo.
- [ ] Add `memory/index.md`.
- [ ] Add `memory/system/WORKFLOW.md`.
- [ ] Route by task class instead of expecting broad reading.
- [ ] Keep large current-state summaries under control so they do not drift.

If not using a memory layer yet:

- [ ] Keep durable knowledge in a small docs lane until the repo genuinely needs more structure.

## 7. Add Machine-Readable Routing Only If It Will Be Maintained

- [ ] Add `tools/agent-manifest.json` only if structured routing will actually be kept current.
- [ ] Encode task classes and their relevant docs/tests/commands.
- [ ] Encode source-of-truth locations.
- [ ] Encode key invariants and validation bundles.
- [ ] Treat the manifest as authoritative only if it has a maintenance path.

## 8. Add A Human-Readable Quickstart

- [ ] Add `tools/AGENT_QUICKSTART.md` if a quick prose entrypoint would help.
- [ ] Mirror the manifest, do not duplicate a second full source of truth.
- [ ] Include startup reads.
- [ ] Include common task classes.
- [ ] Include default validations.
- [ ] Include the threshold for when to create a plan.
- [ ] Include a small-task path.
- [ ] Remind agents not to update durable knowledge for ordinary implementation progress.

## 9. Add Local Guidance Sparingly

- [ ] Add descendant `AGENTS.md` files only where subtree-specific rules genuinely differ.
- [ ] Require agents to read the nearest relevant descendant file before editing that subtree.
- [ ] Avoid creating lots of weak, overlapping local instruction files.
- [ ] Treat too many local guidance files as a smell.

## 10. Make Validation Routed, Not Guessed

- [ ] Define the narrowest validation for each task class.
- [ ] Distinguish local iteration checks from broader release checks.
- [ ] Make validation escalation rules explicit.
- [ ] Put validation bundles in `AGENTS.md`, the manifest, or both.
- [ ] Make sure the narrow route is actually enough to prove common local changes.

## 11. Add A Routing-Liveness Check

- [ ] Add a cheap check that structured routing still matches reality.
- [ ] Verify that `agent-manifest.json` and `AGENT_QUICKSTART.md` agree.
- [ ] Verify that any generated codebase map or hotspot map is current.
- [ ] Fail fast on routing drift.
- [ ] Remove stale structured surfaces from the contract if they are not maintained.

## 12. Decide Whether To Keep A Codebase Map

- [ ] Keep `tools/codebase-map.json` or similar only if it can be maintained cheaply.
- [ ] If it exists, define who updates it and when.
- [ ] If it drifts too easily, remove it from the workflow contract.
- [ ] Do not keep authoritative-looking generated maps that are no longer trusted.

## 13. Define Completion Hygiene

- [ ] Require task-state updates before ending work.
- [ ] Require active-plan updates when a plan exists.
- [ ] Update durable memory only when durable guidance changed.
- [ ] Prefer pruning stale notes over accumulating status prose.
- [ ] Do not encourage broad cleanup unrelated to the task.

## 14. Add Blocker Handling

- [ ] Define what the agent should do when blocked.
- [ ] Require recording the blocker, failed validation, and cause.
- [ ] Prefer stopping with a clear blocker over speculative broad changes.
- [ ] Define when to escalate to stronger reasoning or broader review.

## 15. Add Subagent Policy Only If You Intend To Use Subagents

- [ ] Decide whether the parent agent may use subagents without prompt-by-prompt permission.
- [ ] Default to direct execution in the parent run.
- [ ] Limit subagents to bounded work where specialization or parallelism is worth the overhead.
- [ ] Prefer read-only subagents for mapping, docs verification, review, and bookkeeping.
- [ ] Use writable subagents only for narrow implementation slices.
- [ ] Keep delegation depth shallow.

## 16. Keep The Whole System Minimal

- [ ] Start with the smallest useful version.
- [ ] Add only the surfaces the repo complexity justifies.
- [ ] Prefer fewer authoritative files with clear ownership.
- [ ] Remove workflow surfaces that are not being maintained.
- [ ] Re-check after adoption whether every added surface is still paying for itself.

## 17. Minimal Useful Layout

Use this if you want the smallest good starting point:

```text
repo/
  AGENTS.md
  TODO.md
  docs/
    execplans/
      README.md
```

## 18. Fuller Layout When Justified

Use this only when the repo really needs stronger routing and durable knowledge:

```text
repo/
  AGENTS.md
  TODO.md
  docs/
    execplans/
      README.md
  memory/
    index.md
    system/
      WORKFLOW.md
  tools/
    agent-manifest.json
    AGENT_QUICKSTART.md
```

## 19. Final Porting Review

Before declaring the port complete:

- [ ] A new agent can tell what to read first without scanning the repo.
- [ ] Active task state is separate from durable knowledge.
- [ ] Multi-step work can be resumed without chat history.
- [ ] Completed plans are cheap to skip.
- [ ] Validation routes are explicit.
- [ ] Structured routing surfaces have a liveness check or maintenance rule.
- [ ] Small tasks do not trigger unnecessary reading or plan creation.
- [ ] The repo has no authoritative-looking workflow files that are stale.
- [ ] The added structure is still smaller than the ambiguity it replaces.
