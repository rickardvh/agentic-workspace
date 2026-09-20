# Configure your project

Configure AW when you have a project rule, local preference or repeatable procedure worth preserving. You do not need to configure every capability before starting work. Repository adoption installs the integration; it does not choose your policy or populate optional task state.

## Choose the scope first

| What you want to preserve | Where it belongs |
| --- | --- |
| A rule for everyone working in the repository | Shared instructions under `.agentic-workspace/instructions/`, or an existing shared setting in `config.toml` |
| A rule specific to this checkout or machine | `.agentic-workspace/local/instructions/`, or `config.local.toml` for a supported setting |
| A reusable method | A repository-owned skill, separate from AW's package-managed skills |
| Progress on an unfinished task | Planning, not configuration |
| A lesson with assumptions that may change | Memory, not permanent policy |

Local preferences cannot relax shared requirements. Keep credentials in your normal credential facilities, not in these files. See [Your repository and data](package/installed-surfaces.md) before committing local settings.

## Save a project rule

Ask the agent for the behaviour you want:

> For this repository, read `docs/api-contract.md` before changing files under `src/api/`. Preserve existing response fields unless the API owner approves a change. Save this as shared guidance and show me where it applies.

A corresponding instruction can be small:

```markdown
---
paths:
  - src/api/**
read:
  - docs/api-contract.md
---
Preserve existing response fields unless the API owner approves a change.
```

The path identifies when the instruction applies; `read` identifies a prerequisite source. The paragraph states the rule. Use paths and a document that actually exist in your project. The agent should publish the instruction through the supported instruction operation and verify the result.

Then inspect both a matching and an unrelated task. The matching task should surface the rule; the unrelated task should not acquire an API requirement.

The [scoped-instruction reference](package/scoped-instructions.md) explains `paths`, `read`, `reconcile`, `use`, `checks` and `protect`, including a worked inspection command. Add those fields only when their behaviour is needed.

## Change an existing setting

Ask for the desired outcome instead of guessing a field name:

> Use this AW executable on this machine, without changing the shared repository invocation.

The agent can inspect the current configuration, propose the supported local setting and report the saved value. For lookup, use the [shared configuration reference](reference/workspace-config.md) or [local override reference](reference/workspace-local-override.md). Do not copy the source repository's full configuration into your project.

A saved setting is only part of the check. For an executable location, also verify that the agent can launch it; for a capability, verify that it becomes available for the intended task.

## Add a reusable procedure

A rule says what must hold. A skill explains how to perform a recurring kind of work.

For example, a change-note skill can tell an agent to compare the patch with accepted behaviour and draft a user-facing note only when behaviour changed. Keep that method in repository-owned files, such as `tools/skills/change-note/SKILL.md`, rather than editing an installed AW skill.

Start with ordinary Markdown the agent can read directly. The [skill-authoring guide](package/skill-authoring.md) shows that complete example, then adds optional questions, selectively loaded branches and a deterministic helper. Those additions are useful only when they reduce repeated work; an ordinary skill does not need them.

## Enable a capability when it becomes useful

Planning helps with interrupted or delegated work. Memory helps retain expensive-to-rediscover lessons. Verification helps reuse checking procedures and evidence.

Ask the agent to enable the relevant capability and identify any configuration it still needs. Selecting Verification, for example, does not invent the project's test commands or prove the code correct. [Modules](package/modules.md) explains these choices.

A new project rule or method usually needs no module. A separately reusable capability with its own facts or operations may justify one; that is the [module-authoring](module-capability-contract.md) path.

## Change or undo a customisation

Ask the agent to locate the existing rule, setting or skill and change that source, rather than adding a competing copy. Inspect the diff and check the affected behaviour again. Remove obsolete advice when its assumptions no longer hold.

If the native operation rejects a change, preserve the source and inspect the reported conflict. Do not bypass the rejection by editing managed state. See [Troubleshooting](troubleshooting.md).
