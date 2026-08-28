# Self-configuration integration review — 2026-08-28

## Conclusion

The #2767 product claim is supported by the stacked implementation and the maintained `self_configuration_lifecycle_v1` scenario: a user performs the intentional install/lifecycle choices, while an ordinary contract-following agent receives setup from `start`, infers strong facts, applies typed owner decisions, defers and resumes from compact state, and returns the repository to quiet operation. Later capability changes surface only their current semantic/source delta.

Parent closure is honest when the #2768–#2772, #2774, and this integration-review stack merges. The remaining limitations below are evidence-environment limits, not missing lifecycle behavior.

## Maintained evidence

- Scenario definition: `tests/fixtures/self_configuration_lifecycle_v1.json` (`agentic-workspace/self-configuration-lifecycle-scenario/v1`).
- Executable lifecycle: `tests/test_self_configuration_lifecycle.py`.
- Runtime and child-stack regression evidence: 439 root Workspace CLI tests, 96 external/module tests, and 302 external-operation conformance passes.
- Public source-obligation inventory: `docs/repo-source-obligation-contract.md`.

The scenario starts with an ordinary repository containing a README, one explicit Python test route, and a deliberately weak scratch policy note. It performs the documented minimal install with an explicitly selected independent capability, then uses a non-setup task for the first `start`.

## Trace and attention cost

| Stage | Routed evidence | User/manual administration |
| --- | --- | --- |
| Minimal bootstrap | `init` creates thin routing/readiness surfaces | one intentional install command |
| First ordinary task | `start` returns `reconcile-repository-configuration`, the setup skill, and the exact setup command | no setup/doctor discovery |
| Strong inference | README/system-intent and explicit pytest metadata create zero-question owner actions; scratch policy is excluded | zero questions |
| Semantic choice | human opts into orchestration through `config.policy-apply`; AW returns plain-language automatic-vs-explicit delegation consequences | genuine behavior choices only |
| Defer/resume | local deferral leaves readiness non-current; README work proceeds; delegation work re-elevates; a fresh call resumes the one unresolved id | no transcript or repeated settled question |
| Completion/quiet | the generated TypeScript `config.policy-apply` operation removes the complete deferred `[setup]` table; Python startup then observes exact current basis/concern receipts and three representative direct tasks omit `configuration_readiness` | no ceremony |
| Capability lifecycle | cosmetic contract refresh is quiet; v3 source need surfaces only the independent module concern; v7 is consumed directly; explicit uninstall retires it | intentional lifecycle actions and one domain policy answer |

The versioned fixture records five install/lifecycle actions, three genuine semantic answers, zero user-invoked setup/doctor rituals, and zero raw AW-state edits. Agent-invoked setup/config/system-intent operations are routed work, not user administration.

Durable residue is limited to canonical config/owner sources, temporary local `[setup]` disposition while deferred, and the adoption receipt’s current concern set. There is no transcript, questionnaire history, chronological setup generation, or parallel source registry.

## Acceptance review

- **Bootstrap and front door:** satisfied by the minimal `init` followed by a normal formatter task whose first `start` returns the exact setup continuation without setup wording.
- **Agent independence:** satisfied by a harness that consumes public decision/question/operation fields only. It never reads raw AW config or internal setup docs to choose a route.
- **Inference and weak-signal refusal:** satisfied by zero-question system-intent/proof actions and the excluded `scratch/policy.md` counterexample.
- **Human semantics and typed mutation:** satisfied by outcome/consequence wording and exact `config.policy-apply` decisions; system-intent sync remains with its owner.
- **Partial apply, defer, compact repeat, cross-session resume:** satisfied by the local disposition trace and exact unresolved concern identity.
- **Selective hard prerequisite:** satisfied by unrelated README work remaining available while delegation-dependent work returns `action-required`; #2789 additionally proves required source completion rejection.
- **Local deferral versus durable decline/disable:** local `[setup]` changes prompting only; explicit module uninstall changes durable capability selection and retires the concern.
- **Quiet configured operation:** satisfied structurally across three representative tasks and after source resolution/disable; no readiness payload or setup action is present.
- **Explicit lifecycle and no implicit enable/upgrade:** the capability is selected by install and removed by uninstall. Setup never mutates `modules.enabled` or package state.
- **No-semantic, inferable/current, human, and multi-release deltas:** cosmetic metadata is quiet; satisfied concerns require no question; v3 produces one module/source question; the next observed v7 is reconciled directly without v4–v6 replay.
- **Independent module composition:** the `signals` entry-point contract contributes through `module-setup-concerns-v1` and `source_obligation`; Workspace contains no module-name branch.
- **Generic/weak-agent evidence:** the deterministic consumer follows structured output and safely pauses on deferral. Maintainer path knowledge is not an input.
- **Host-repository evolution overlap:** deleting a satisfied source returns through the existing compact source/currentness comparison, explicitly handing ongoing repository evolution to #2661 rather than a second maintenance loop.

## Subtraction review

- `start` is the only ordinary first question. `docs/package/lifecycle.md` now describes `setup` as agent-routed reconciliation detail, not a user-discovered optional ritual.
- `workspace-setup-jumpstart` remains because it is the bounded procedure selected by `start`; it is background routing, not a second front door or wizard.
- Direct shared config edits are not part of ordinary setup. Bounded scalar/local choices use `config.policy-apply`; nested domain policy remains an ordinary repo-owned source under its existing owner.
- `doctor` remains recovery/diagnostic detail and is absent from the maintained ordinary path.
- Setup findings remain optional improvement evidence; they are not readiness authority, a questionnaire, or continuation state.
- The adoption receipt stores only current identity/basis/concern receipts. Historical setup generations and transcript residue were not introduced.

## Evidence limitations

- The generic-agent proof is a deterministic contract consumer, not paid external-model telemetry. Its value is that the harness has no maintainer route hints and fails if public fields are absent.
- Independent module releases are represented by a live entry-point contract changing revisions in-process; package-manager transport itself is outside the setup contract. Install/uninstall ownership is exercised through public lifecycle commands.
- The complete lifecycle uses Python’s root CLI for routing and the generated TypeScript `config.policy-apply` operation for the deferred-to-current cleanup transition. Broader native/generated parity remains covered by the external operation and generated-package conformance suites.

These limits do not require user-side setup administration and do not weaken the claimed route semantics.
