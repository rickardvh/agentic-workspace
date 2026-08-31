# Delegation policy ownership and migration

Delegation policy has four independent source-owned inputs:

| Question | Canonical owner | Legal values / source |
| --- | --- | --- |
| Which target should own the task? | `delegation.assignment_policy` | retained local, advisory best fit, or binding best fit |
| May the selected transport execute? | `delegation.transport_authority` | manual or automatic, intersected with the independent safety ceiling |
| Who may replace a binding assignment? | `delegation.human_override_policy` | explicit-only, recorded-reason, or disallowed |
| What targets and transports exist? | `delegation.current_target` plus `delegation_targets.*` facts | identity, capability classes, forbidden classes, cost, and constructible transport data |

Every assignment-policy, transport-authority, and human-override value is a legal combination. Capability evidence may make a selected action unavailable, but does not make the policy combination invalid.

## Field audit

| Previous field | Classification | Disposition |
| --- | --- | --- |
| `delegation.mode` | overlapping transport authority | compatibility alias; derive from `transport_authority` |
| `delegation.execution_role` | derived execution context | compatibility alias; derive orchestrator/local role from assignment policy |
| `delegation.assignment_policy` | assignment authority | retained canonical owner |
| `delegation.selection_objective` | overlapping ranking preference | compatibility alias; best fit always ranks safety/capability/quality/proof before total successful-completion cost |
| `delegation.underfit_behavior` / `down_routing_behavior` | split directions of one selector | compatibility aliases; derive both directions from assignment policy |
| `delegation.manual_transport_policy` | overlapping transport authority | compatibility alias; derive fallback from transport authority |
| `runtime.cheap_bounded_executor_available` | target availability summary | compatibility alias; derive from target capability, cost, and readiness |
| `handoff.prefer_internal_delegation_when_available` | transport ranking preference | compatibility alias; rank only constructible peer transports |
| target `reasoning_profile` | duplicate strength axis | compatibility alias; derive from `strength` |
| target `safe_task_classes` | duplicate eligibility list | compatibility alias; derive from `capability_classes - forbidden_task_classes` |
| target `human_control_modes` | target-local policy authority | compatibility alias; global assignment/transport authority owns control |
| target `execution_methods` plus adapter data | capability and readiness | retained facts; internal is ready only with runtime support, CLI/API only with adapter data |

Compatibility aliases remain readable for a finite migration window and cannot override a present canonical field. New configuration should write only canonical fields. The effective config/start projection reports canonical provenance and derived values, so an agent never needs to solve the legacy knob matrix.
