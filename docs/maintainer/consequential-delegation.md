# Consequential delegation

Repository policy, local capabilities and current Assignment compose through the
ordinary Rust-backed `start` requests. The main workspace skill remains the entry
procedure. There is no second selection loop or provider registry.

## Repository posture and local facts

The shared configuration can attach provider-neutral requirements and preferences
to exact, repository-defined semantic routes:

```toml
[execution_posture."design/boundaries"]
required_execution_guarantees = ["reasoning.general"]
preferred_execution_guarantees = ["context.large"]

[execution_posture."maintenance/bounded"]
preferred_execution_guarantees = ["cost.bounded"]
```

These names are examples, not a core taxonomy. Only current semantic-route facts
select posture; matching words in a task do not. The selected posture and current
task requirements bind Assignment currentness. Changing a different route's
posture does not invalidate this Assignment. Raw source revisions remain visible
for configuration editing and evidence.

Local targets advertise `execution_guarantees`, for example:

```toml
[delegation_targets.general]
execution_guarantees = ["reasoning.general", "context.large"]
transports = [{ kind = "manual" }]
```

Required guarantees narrow eligibility before comparative judgement. Matched
preferences inform the agent's comparison among eligible alternatives; they do
not grant execution, safety or proof authority. A manual-only target can win,
and the retained current target can win when it satisfies the requirements.
Availability and economics remain local facts, never shared routing policy.

`independent_context = true` is a separate work-relative requirement. None of the
currently supported native configurations asserts an independent review relation;
such a requirement remains unsatisfied. A capability tag, model name or new
provider thread does not establish independent review.

Canonical guarantee profiles exclude `strength`, `reasoning_profile`,
`capability_classes`, `safe_task_classes`, `forbidden_task_classes`,
`escalation_target` and `human_control_modes`. Mixing them is a configuration
error, not a precedence rule. Existing profiles without `execution_guarantees`
retain their old source interpretation for transition; these legacy labels are
never inferred into guarantees. When repository posture applies, a legacy target
with overlapping fields is unavailable until migrated, so the two eligibility
models cannot run together. Migrate a target by replacing the overlapping
fields with its current capability facts, and put task-class policy in the shared
route owner. Identity, transport, context capacity, cost and latency remain
distinct local descriptive dimensions.

Assignment authority, transport authority and the independent command-safety
ceiling retain their existing contracts. Current configuration-owner override
admission remains revision-bound; comparison and result evaluation confer no
standing override authority.

## Supported transports

| Path | Supported result and boundary |
| --- | --- |
| Retained current host | Current eligible Assignment; execution stays with the acting agent. |
| Manual export | Bounded read-only packet and typed unproven return; no automatic launch. |
| Process CLI/stdout | One sealed invocation, read-only material or an unapplied UTF-8 patch, committed custody and exact re-entry. |
| Codex app-server bridge | The same sealed invocation through `agentic_workspace.sealed_codex_transport`; one fresh read-only provider turn and typed material return. |
| API, JSON-file result, undeclared native command | No native automatic execution claim. |

For the Codex bridge, configure a local native transport with
`adapter = "codex-app-server/v1"`, a `command` invoking the installed Python
module (`python -m agentic_workspace.sealed_codex_transport`), and `parameters`
containing the locally selected `model` and any supported `reasoning_effort`.
Use the actual local interpreter executable and set `timeout_seconds` on the
transport. The bridge requires the existing Codex CLI/app-server and credentials.
For a best-fit comparison, the native owner observes the configured executable
and calls that bridge with `--aw-capability`, sending only its exact parameters on
stdin. The bridge checks the installed protocol and current model availability
without starting a worker turn or retaining a capability file. The bounded result
binds the adapter implementation, provider capability revision and parameters into
the execution configuration. Assignment and dispatch reobserve those facts;
changed capability requires fresh comparison. Immediately before the provider
turn, the bridge checks the same capability again. Runtime quota or provider
failure remains execution failure, not negative target-quality evidence.

A non-current `internal` declaration has no portable launch or typed return
binding. Under `required-best-fit`, an otherwise eligible unbound internal target
remains an explicit unresolved alternative and prevents local admission. Replace
that declaration in the machine-local source with a concrete supported transport;
do not add a static capability flag or infer a binding from a model name. For the
supported Codex host, one target can be configured as follows, using the actual
interpreter and a model validated by current host discovery:

```toml
[delegation_targets.worker]
target_id = "local:worker"
transports = [{ kind = "native", adapter = "codex-app-server/v1", command = ["/actual/python", "-m", "agentic_workspace.sealed_codex_transport"], parameters = { model = "<current-host-model>" }, timeout_seconds = 1800 }]
```

The source declaration selects the binding; the current host observation supplies
feasibility. A confirmed absent executable or unsupported model is unavailable,
so local may win among the remaining feasible alternatives. Interrupted discovery,
malformed responses and unbound internal capability remain unknown; they cannot
be dismissed as unavailable. Source prohibitions and command safety are checked
before probing. A retained-local policy does not probe host workers. Discovery
does not create a worker session, Assignment ledger, queue or provider registry.

The bridge receives the sealed captured inputs, validates entry and constructs
return identity through Rust. It neither inherits parent chat nor uses the former
Python Assignment/dispatch owner. Provider material cannot supply identity or
approve its own result. Process/host completion still requires current result
evaluation, patch integration where applicable, Planning adoption and Verification.

## Serial replacement and evidence

After resolving replacement Assignment B, the returned
`delegation/reconcile-prior-result/v1` request accepts original execution custody A
and a disposition. `replace` preserves the committed original outcome and allows
the current B dispatch. Missing or in-flight custody cannot authorise replacement;
use the original attempt recovery owner. The original record is never rewritten.

`reuse-readonly` admits an original completed read-only return only when current
work, role, requirements, proof obligation, captured inputs and scope still match.
It records both current Assignment and original executing configuration. Repeating
the observation applies no effect. Changed input or work is rejected. Late patches
and uncertain effects remain with their original integration/recovery owners;
this path does not claim general concurrent workers, live session migration or
automatic cancellation of an unresolved attempt.

An acting-orchestrator `repair-required` or `rejected` evaluation can be adopted
into Planning's repair frontier without claiming accepted progress or requiring
integration of a rejected patch. Target evidence is a bounded projection of that
current Planning outcome plus Verification covering its exact source. Positive
patch evidence additionally requires current integrated postimages. Supersession
or changed evidence inputs de-adopts the observation. Original execution receives
attribution even when a return is reused after replacement. No observation claims
human authorship, independent review, universal target quality or task completion.

## Evidence and closure

The policy fixture exercises the same repository policy in two local environments,
manual upward selection, retained-local eligibility, relational independence
failure and relevant/unrelated posture changes. The existing native handoff
journey adds the host bridge, committed serial replacement, non-conflicting late
return, missing custody, stale inputs and repair evaluation through Planning and
Verification. Provider protocol fixtures cover discovery, exact parameters,
read-only execution, cleanup and failures. They are deterministic integration
evidence, not a paid-provider run or economic measurement.

These are the Priority 1 implementation and supported-transport dispositions for
#3208. Independent acceptance owns checklist completion. #2947/#2817 require
aggregate acceptance of their current children and these explicit limits; this
document and a green local test run alone do not close those parents. Real-provider
burden and economics remain #3192; final candidate composition remains #2909.
