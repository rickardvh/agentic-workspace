# Native domain proof candidates

The existing Verification owner now admits exact path-matched commands from `.agentic-workspace/config.toml` `assurance.domain_proof_lanes` through its existing typed `verification/execute-selected/v1` request and `proof.report` operation. `domain:<id>` is the existing lane identity convention. No new protocol, policy format, store, or orchestration engine is introduced.

Selection is explicit and bound to current task, source and capability identity. Full selected lane metadata remains part of the strategy: manual evidence, authority refs, proof profiles, escalation, composition and claim boundaries do not disappear. Candidate constructibility proves only that the source declares the command. It does not decide whole-lane applicability, required composition, proof sufficiency, review identity or completion. Current config residual claim restrictions remain until their owners establish those meanings. Local command safety still restricts the admitted action.

Task-marker-only lanes remain current unresolved semantic scope; native code does not infer task intent from words. Unmatched path-only lanes contribute no candidates. Real source drift and a different task stale the prior request. The process producer, replay custody and evidence boundary remain shared across native CLI, JSON, Python and Node.

## Bounded public output

Discovery shows at most 32 source-bound descriptors and 16 domain command candidates, with explicit omitted counts and the exact source field reference. Descriptors are bounded to 2 KiB and command candidates to 4 KiB. The full forest is not copied into ordinary strategy or judgment packets. An explicitly selected lane exposes its current metadata up to 32 KiB; a larger lane gets an exact detail-bound blocker before any execution action. Remaining discovery/detail work is an explicit partial-coverage boundary, not silent retirement of source intent. Existing manifest behavior is unchanged.

The owner recomputes current source projection from confined, bounded configuration reads. This slice adds no cache or claim of cheaper durable reuse. Whole-strategy dependent currentness and repeated source parsing remain possible follow-up work under #2981, requiring measured benefit before retention machinery.

## Current assurance disposition

| Control | Actual current meaning | Native state after this layer |
| --- | --- | --- |
| `default_level` | Baseline proof/trust guidance | Still requires current level/strategy judgment; no invented level inference. |
| `agent_may_escalate` | Permission to raise the chosen assurance level | Still requires level owner consumption; command availability does not consume it. |
| `agent_may_deescalate` | Permission to lower below the configured baseline | Still requires level owner consumption; a command choice cannot weaken it. |
| `proof_profiles` | Required/optional command bundles selected by current requirements or Planning | Still unresolved selected-profile ingress; no global default activation. |
| `domain_proof_lanes` | Source command routes with scope, evidence, composition and escalation metadata | Exact path-scoped candidates now executable; semantic applicability, composition and sufficiency remain unresolved. |
| `subsystem_profiles` | Obligations scoped by actual OWNERSHIP subsystems and Planning scope | Still needs those typed current owner facts; filenames or prose cannot substitute. |
| `strict_closeout` | Required proof/gate trust before affected closeout | Still explicit claim restriction; unrelated direct execution is not generally prohibited. |

Manifest path/protocol selection and assurance requirement applicability already existed and are preserved. This advances #2334/#2613 source reachability; none of #2334, #2613 or #2981 is closed by command discovery or process success.

## Implementation evidence and friction

Public regressions use the exact real `proof_subject_owner` lane declaration, bounded source-command fixtures, same invocation replay, task/source drift, safety refusal, no-keyword semantic-scope uncertainty, and a 41-lane packet below 100 KiB. A selected oversized-detail negative preserves source bytes without producing an action.

No provider work or monetary estimates were used. Initial fixture failures exposed two implementation-agent mistakes: expecting an exception instead of the established stale-request diagnostic, and copying unrelated repository ADR pins into a source-lane fixture without their admitted archive. The fixture now preserves the exact real lane declaration and independently asserts its public effect; no product authority rule was weakened. These checks are implementation evidence, not independent acceptance.

The composed public response exposes its capability contract once. Owner-local fragments remain internal composition inputs; each returned request still binds the full public contract. Integration with canonical Planning creation exposed duplicated fragments pushing the 41-lane fixture to 103136 bytes; removing that duplication preserves the existing 100 KiB bound and public constructibility. This is a bounded projection correction under #2986/#2987/#3059, not deferred-schema loading or completion of host-efficiency acceptance.
