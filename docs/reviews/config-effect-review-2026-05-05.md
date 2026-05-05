# Config Effect Review

Date: 2026-05-05

## Purpose

This review checks whether settings in `.agentic-workspace/config.toml`
and `.agentic-workspace/config.local.toml` concretely affect Agentic
Workspace tool output or behavior, or whether they mainly rely on agents
noticing and following advice.

The review used these surfaces:

- `agentic-workspace start --profile tiny --format json`
- `agentic-workspace config --target . --profile compact --format json`
- `agentic-workspace report --section workflow_obligations --format json`
- `agentic-workspace report --section repo_friction --format json`
- `agentic-workspace report --section output_contract --format json`
- `agentic-workspace implement --profile tiny --changed ... --format json`

## Summary

Most configured settings are consumed by tool surfaces, but many are still
structured advice rather than hard behavior.

The strongest settings change command output, selected modules, startup
adapters, lifecycle metadata, compatibility diagnostics, proof suggestions,
or delegation decisions. The weakest settings are visible and queryable, but
if an agent ignores the relevant command output, the package does not
independently force compliance.

The current `agentic-workspace config` output already exposes a useful
`config_enforcement` table. Its classification is directionally right, but it
can overstate operational force when a setting changes only guidance emitted
to the agent.

## Effect Classes

Hard:

- Invalid or incompatible values stop command execution or validation.
- Examples: `schema_version` and schema-invalid config values.

Operational:

- Values directly change package output, installation behavior, lifecycle
  behavior, selected files, command strings, or diagnostics.
- Examples: `workspace.default_preset`, `workspace.agent_instructions_file`,
  `workspace.workflow_artifact_profile`, `workspace.cli_invoke`,
  `system_intent.*`, and `update.modules.*`.

Advisory-operational:

- Values produce structured decisions or diagnostics, but enforcement still
  depends on the agent or on a later closeout/report command.
- Examples: `cli_compatibility.*`, `assurance.*`, and local delegation or
  runtime posture.

Advisory:

- Values mainly change guidance, policy text, or report framing.
- Examples: `workflow_obligations.*`, `workspace.improvement_latitude`, and
  `workspace.optimization_bias`.

Local advisory:

- Machine-local values shape current-agent routing but cannot become shared
  repo authority.
- Examples: `delegation_targets.*`, `runtime.*`, `handoff.*`, `safety.*`,
  and `local_memory.*`.

## Repo Config Effects

`workspace.default_preset` is operational. It affects setup, install, init,
and module selection defaults.

`workspace.agent_instructions_file` is operational. It affects startup adapter
placement and which agent instruction file is treated as the configured front
door.

`workspace.workflow_artifact_profile` is operational. It changes startup
adapter and handoff guidance. In this repo it resolves to `repo-owned`, making
`.agentic-workspace/planning/state.toml` and
`.agentic-workspace/planning/execplans/` the canonical planning surfaces.

`workspace.advanced_features` is operational in the sense that it controls
advanced report sections, skills routing, and startup guidance. It does not by
itself require agents to use those advanced surfaces.

`system_intent.sources` and `system_intent.preferred_source` are operational.
They drive `system-intent`, config output, and report mirrors.

`update.modules.*` is operational. It drives module update metadata,
status/doctor/upgrade source reporting, and freshness checks.

`cli_compatibility.*` is advisory-operational. It concretely compares the
invoked CLI identity against expected source class and target relation. With
`enforcement = "advisory"`, drift is reported rather than made a hard failure.

`assurance.*` is advisory-operational. It appears in config, proof,
summary/planning records, and closeout guidance. Without active planning or an
explicit closeout/report check, it does not strongly gate execution.

`workflow_obligations.*` is advisory. The tool reports configured obligations,
match evidence, relevant scope tags, commands, and review hints. In the current
no-active-plan state, report output shows no matching current scope tags. The
package does not force agents to run matched obligation commands unless the
agent consults and follows the output.

`workspace.improvement_latitude` is advisory. It changes repo-friction policy
mode and initiative posture. It helps decide whether to adapt inside workspace
surfaces or report/promote improvement work, but the actual action remains
agent-mediated.

`workspace.optimization_bias` is advisory with a narrow concrete rendering
effect. `report --section output_contract` says it may change rendering
density and residue style, but must not change execution method, reasoning
depth, proof requirements, ownership semantics, machine-readable truth, or
canonical state semantics.

## Local Config Effects

`workspace.cli_invoke` is operational. It concretely rewrites copyable commands
in startup, report, proof, and lifecycle guidance.

`runtime.supports_internal_delegation`, `runtime.strong_planner_available`,
and `runtime.cheap_bounded_executor_available` are advisory-operational. They
shape `local_runtime`, `mixed_agent.runtime_resolution`, and delegation
decisions.

`handoff.prefer_internal_delegation_when_available` is advisory-operational.
It changes handoff guidance and derived runtime posture, but does not execute
delegation by itself.

`safety.safe_to_auto_run_commands` and `safety.requires_human_verification_on_pr`
are advisory-operational. They affect guardrail posture and closeout trust
guidance. Automatic action still depends on delegation mode and runtime
integration.

`delegation.mode` is operational when configured and otherwise defaults to
`suggest`. The default `suggest` mode changes output by surfacing
recommendations without execution. `manual` prepares handoff. `auto` is the
only mode intended to allow execution without first stopping at a
human/orchestrator boundary.

`clarification.mode` is operational for ambiguous or underspecified tasks.
`ask-first` can change the next action to `stop-and-ask-human`; `suggest`
surfaces the option; `auto-continue` permits bounded interpretation unless a
hard blocker remains.

`delegation_targets.*` is advisory-operational. Target strength, confidence,
task fit, capability classes, and execution methods now shape selected target,
escalation/downrouting recommendations, handoff packet guidance, and weak
target guardrails. They remain advisory estimates rather than proof that a
target can safely close the work.

`local_memory.enabled/path` is local advisory. When enabled, it changes local
memory/scratch reporting and discovery, but the surface is non-authoritative,
ignored, and must not override checked-in Memory, Planning, config, or docs.

## Gaps

1. `workflow_obligations` are structured but weakly enforced. They become
   visible through report, preflight, and start surfaces, but an agent that
   skips those surfaces can miss them. Even when visible, they are not
   represented as a blocking gate.

2. `assurance.strict_closeout` sounds stronger than the observed behavior in
   no-active-plan workflows. It shapes closeout/proof guidance, but the force
   depends on using Planning or closeout reports.

3. The current enforcement taxonomy is not yet a first-class audit. `config`
   reports classes, but there is no dedicated command that says which field is
   hard, which field only changes advice, which field appears unused, and
   which field claims stronger behavior than observed.

4. Advisory fields can look like policy to humans while acting as suggestions
   to agents. This is especially relevant for `workflow_obligations`,
   `improvement_latitude`, `optimization_bias`, and local runtime/delegation
   posture.

5. Local delegation settings are now visible in `start` and `implement`, but
   the default `suggest` mode means behavior depends on the agent choosing to
   act on the suggestion. That is correct for human control, but the output
   should continue to be explicit that `suggest` is not execution.

## Recommendations

1. Add a config-effect audit surface.

   A command or report section should classify every repo/local config field
   as `hard`, `operational`, `advisory-operational`, `advisory`,
   `local-advisory`, or `unused`. It should include the concrete commands and
   payload fields affected by each setting.

2. Detect mismatches between claimed and actual effect.

   The audit should warn when a setting name or schema description implies
   enforcement, but the implementation only surfaces advice.
   `strict_closeout` and `workflow_obligations` are the first candidates to
   review.

3. Make obligation force explicit in outputs.

   `workflow_obligations` should say whether a matched obligation is
   informational only, recommended before continuing, required before
   closeout, or blocking under the current config.

4. Keep local delegation human-controlled, but make the mode consequence
   unavoidable.

   For `delegation.mode = "suggest"`, outputs should continue to say that no
   delegation will execute automatically. For `manual`, the next action should
   be to prepare a packet and stop. For `auto`, outputs should identify which
   local safety conditions made execution permissible.

5. Treat optimization and improvement settings as output posture, not
   execution control.

   `optimization_bias` should remain explicitly limited to density and residue
   style. `improvement_latitude` should keep reporting what action is allowed
   versus what must only be reported.

## Product Implication

The package is moving in the right direction: settings are increasingly
inspectable and reflected in compact command output. The remaining weakness is
not missing configuration, but unclear force.

Users will expect settings to have a noticeable and well-defined effect. The
tool should therefore make each setting's effect type inspectable, and should
avoid letting structured advice masquerade as enforcement.
