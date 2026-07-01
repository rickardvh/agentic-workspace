---
name: workspace-transition-gates
description: Reference SkillSpec-backed transition gates only when the main AW operating skill or compact router names allowed actions, forbidden actions, preferred invocation, interpreted fields, or fallback behavior that need interpretation.
---

# Workspace Transition Gates Reference

This is a package-managed workspace skill installed under `.agentic-workspace/skills/`.

Do not use it as an ordinary startup, implementation, proof, or closeout entrypoint. Start with `workspace-startup`; use this reference only when a routed transition packet needs explicit gate interpretation.
When AW is enabled, these gates are mandatory workflow boundaries. Advisory routing explains agent-owned choices inside the workflow; it is not permission to skip `start`, `implement`, Planning gates, proof, or closeout.

Each gate is a compact SkillSpec-shaped record:

- trigger
- preferred CLI or report
- interpreted fields
- allowed actions
- forbidden actions
- proof required
- no-CLI fallback

## Gates

### Startup To Work

- Trigger: first contact, takeover, or uncertain task shape.
- Preferred route: configured AW invocation with `start --task "<task>" --format json`.
- Interpreted fields: `workflow_participation`, `immediate_next_allowed_action`, `workflow_sufficiency`, `next_safe_action`, `skill_routing`.
- Allowed: follow `next_safe_action.preferred_cli`, request a selector, or continue direct work when the packet says enough.
- Forbidden: open broad raw planning files before the compact summary when the packet forbids it; treat advisory routing or `implementation_allowed` as a bypass around enabled-AW workflow participation.
- Fallback: read `.agentic-workspace/WORKFLOW.md` and preserve forbidden actions.

### Work To Planning

- Trigger: lane/epic shape, active planning pressure, durable sequencing, or issue-linked execution.
- Preferred route: configured AW invocation with `summary --format json`, then Planning commands named by the packet.
- Interpreted fields: active item, active execplan, continuation owner, stop conditions.
- Allowed: create or continue the active planning artifact through package commands.
- Forbidden: hand-edit planning state or claim completion from a local slice.
- Fallback: read the active execplan only after the compact summary points there.

### Work To Proof

- Trigger: changed paths are known or a completion claim is near.
- Preferred route: configured AW invocation with `implement --changed <paths> --format json` or `proof --changed <paths> --format json`.
- Interpreted fields: required commands, proof burden, acceptance guidance, completion-claim boundary.
- Allowed: run the selected narrow proof and classify gaps.
- Forbidden: substitute passing commands for intent satisfaction.
- Fallback: choose the narrowest existing test, lint, contract, or inspection route for the changed surface.

### Work To Memory Residue

- Trigger: repeated correction, durable lesson, closeout residue, or improvement signal.
- Preferred route: configured AW invocation with `memory route --files <paths...> --format json` or `memory promotion-report --mode remediation --format json`.
- Interpreted fields: `memory_consultation_status`, `durable_residue_decision`, `improvement_signal_status`.
- Allowed: capture only durable anti-rediscovery knowledge or route to the owning surface.
- Forbidden: write task logs, plan history, or one-off chat residue to Memory.
- Fallback: inspect the Memory index and only already-routed notes.

### Proof To Closeout

- Trigger: validation has run and the agent is about to say work is complete.
- Preferred CLI: Planning closeout/archive command when planned; otherwise final acceptance reconciliation.
- Interpreted fields: proof result, intent satisfaction, issue linkage, residue decision, completion allowed.
- Allowed: close only the claim level actually proven.
- Forbidden: close parent/lane/epic issues from slice-only proof.
- Fallback: state proof, intent, gaps, and next owner without mutating managed state by hand.

## Guardrails

- Treat `forbidden_actions` as binding until a newer compact packet supersedes them.
- Preserve `module_slot` when falling back without CLI.
- Prefer selector output before opening broad raw files.
- Keep SkillSpec gate records compact enough to reduce context, not create a new manual.
