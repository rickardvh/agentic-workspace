# One richer-host comparison (#3267)

Disposition: **NO_ADAPTER** for the evaluated selected-proof journey. No host
adapter, implementation child, vendor skill copy or additional runtime is added.
This does not reject richer interaction for a future independently measured need.

## Portable baseline and remaining burden

The comparison ran on Windows on 2026-09-16 after the portable frontier/proof
integration at `85b4c8dea`. It includes standard skill exposure from #3325,
executable proof composition from #3315, and the #3334 construction boundary.
The [frontier evidence](decision-frontier.md) separates mandatory owner work from
optional construction and transport. Avoided full-state work is credited to
that portable change, not to the host.

Two disposable repositories contained the same subject, one declared command
(`Get-Content a.txt`), canonical skill sources and task intent: read that subject
and admit the exact command receipt. Native Configuration exposed the canonical
skill directories through owned `.agents/skills` junctions. Actual Codex 0.154.0
app-server `skills/list` discovered all six product skills in each repository.
The selected standard `workspace-proof-selection/SKILL.md` was byte-identical to
the canonical source and contributed 5,184 bytes in each arm. The six serialized
discovery rows measured 3,151/3,175 bytes; the difference is target path length.
An unrelated global skill had a frontmatter error in both catalogues; it did not
prevent product discovery. No nested model execution or inherited-tool parity
was assumed.

After portable composition, the remaining mechanical burden was carrying the
prepared exact request across the genuine command-selection boundary, then
parsing the shell result. The portable arm already performs this with a
disposable JSON response file and ordinary PowerShell. It does not require the
model to reconstruct owner revisions or request fields. The command choice is
agent judgment and must not be silently automated by a host wrapper.

## One tested host mechanism

The richer arm used this active host's `functions.exec` programmatic orchestration:
call `tools.exec_command`, parse its native JSON result, retain the exact prepared
value with `store`, and submit its selected request in a later call. The actual
shell tool and native `proof-procedure` were invoked successfully. That verifies
only this shell/native transport class. Generic labels such as programmatic tool
calling do not establish access to arbitrary MCP tools, provider callbacks,
interactive shells, or a child model's tools.

Both arms used the same core binary, canonical standard skill, source grammar,
current policy and check-to-receipt procedure. Neither used a full operating
diagnostic as its normal comparison answer. Both summarized the same native
decision/effect fields for inspection; the portable shell can make that same
projection without host machinery. Raw native results were still counted.
Both stopped with command evidence admitted and claim review not requested;
neither claimed task completion or independent review.

| Measurement | Portable PowerShell | Programmatic host |
| --- | ---: | ---: |
| Caller interactions: prepare, select/execute | 2 | 2 |
| Shell/native command invocations | 2 | 2 |
| Explicit owner calls reported by the method | 4 | 4 |
| Native prepare result bytes | 7,832 | 7,836 |
| Native execute result bytes | 15,483 | 15,503 |
| Same normalized visible summary bytes, both steps | 1,196 | 1,196 |
| Selected canonical skill bytes | 5,184 | 5,184 |
| Prepare elapsed ms | 115 | 326 |
| Execute elapsed ms | 2,636 | 2,897 |

Byte figures are UTF-8 JSON/ASCII in these fixtures; differing target paths and
bound identities explain small result differences. Native invoke's internal
pre-effect validation and current continuation remain additional work in both
arms. There were no effect retries in the matched journey. Staging, discovery,
measurement extraction and recovery probes are outside the two journey calls.

Elapsed observations are single trials. The portable timer surrounded the child
process; the host timer included orchestration/tool dispatch. They are not a
matched latency benchmark and establish no causal speed ranking. Host tool
schemas, orchestration code and existing session context are additional nonzero
costs; provider-effective tokens and cache billing were not observable here.
The table does not treat unmeasured metadata/context as free.

The host avoids one portable prepared-response file by retaining the same bytes
in its ephemeral store. Both still create the native proof receipt/custody and
standard-exposure records. The portable result file was measurement evidence,
not a second semantic owner. Temporary fixtures and measurement copies belong
to the task scratch lifecycle; no host truth is added to repository state.

## Currentness, interruption and fallback

- Editing the selected method after the richer arm completed made its retained
  `expected_revision` stale. A second submission returned
  `unavailable-or-stale-method`, `not-invoked`, and zero owner calls. The count of
  retained local files stayed at 24; no new check was run. The canonical fixture
  method was restored afterward.
- Pre-dispatch suppression was exercised without calling a native tool. This is
  a wrapper branch, not a claim that the host can atomically cancel a dispatched
  command. Host/process cancellation after dispatch can lose an already committed
  result. No automatic retry is implemented or allowed by this experiment;
  exact native custody/current reentry owns that disposition.
- The native composition tests separately exercise confirmed effects with failed
  mandatory continuation and with stale optional method material while the
  frontier remains current. They preserve effect truth and `retry_effect=false`.
  No host cancellation capability or process-kill recovery was invented.
- A fresh portable CLI preparation on the richer arm's repository yielded current
  context in one owner call without reading the host store. The experiment's
  host store was then discarded. Existing receipts remain repository-owned;
  preparation alone does not re-admit an unspecified historical receipt.
- Disabling this optional orchestration requires no repository migration or
  adapter removal. Generic agents keep the same standard skill and native
  contracts. No-runtime agents retain the skill's explicit unknown-effect/proof
  boundary and must not emulate owners.

## Corrected portable baseline recheck

The stack now includes the receipt-currentness and unique-required-action fix at
`9cc50112d`. The original trial above remains historical evidence at its named
base; its numbers are not presented as measurements of the corrected code.

A bounded rerun used the corrected code, the same one-candidate source grammar,
subject and intent, and the current canonical proof skill (5,632 bytes per arm).
Two disposable source fixtures exercised ordinary PowerShell response-file
carriage and this host's actual programmatic shell transport with the prepared
result retained in its ephemeral store. No new discovery or vendor trial was
needed; the earlier discovery observation remains bound to the original version.

| Corrected-code measurement | Portable PowerShell | Programmatic host |
| --- | ---: | ---: |
| Caller interactions | 2 | 2 |
| Shell/native invocations | 2 | 2 |
| Explicit public owner calls | 4 | 4 |
| Native prepare result bytes | 7,873 | 7,869 |
| Native execute result bytes | 14,829 | 14,809 |
| Child process prepare elapsed ms | 607 | 112 |
| Child process execute elapsed ms | 2,693 | 2,678 |

The final pass followed restacking and rebuilding both native binaries; earlier
probe receipts in these fixtures were unreferenced. These raw UTF-8 results exclude the common trailing output newline. Path lengths
and bound identities differ. Both elapsed measurements here surround only the
child process, unlike the original host timer; they remain single observations,
not a causal latency claim. Host orchestration, tool schemas, context, setup and
measurement extraction remain additional nonzero costs. No new token or normalized
summary measurement is claimed.

Both preparations returned `required_execution.status=not-settled`: the fixture
contains a candidate command, not a missing required check. Both executions
committed, admitted `selected-command-passed`, and left claim review `not-requested`.
Thus this residual choice still has two caller interactions. Separately, the
portable regression now establishes that a genuinely unique required check uses
one caller interaction and four owner calls with no selection echo; that saving
belongs to portable Verification/procedure composition, not a richer host.

The corrected Rust regression executes one of 128 alternatives and admits its
receipt through compact and composed paths with zero untaken choice/report
builders. Full/compact claim restrictions remain equal. The Rust suite passed
128 tests (3 existing ignored), and the targeted frontier/proof/strategy/scope/
measurement/carriage/continuation/skill lane passed 116 tests. These establish
implementation behavior; acceptance of #3335 remains an independent review duty.

The refreshed selected journey still removes only the disposable response file
in the richer arm. `NO_ADAPTER` is unchanged. The prior uncertainty, recovery and
portable fallback boundaries remain; no additional host cancellation capability
is claimed.

## Decision and stop rule

For this remaining burden the host changes where an exact JSON value is held,
but removes no caller judgment boundary, native call, effect admission or claim
obligation. The portable path already avoids protocol reconstruction and eager
optional owner detail. Saving one disposable response file does not justify
maintaining a host-specific adapter and its availability/recovery contract.

Stop with this one access-audited comparison and **NO_ADAPTER**. Do not build a
vendor matrix, generalized CLI mirroring layer, or speculative integration child.
The broader candidate/parent lane and independent acceptance of the portable
stack remain separate from this evaluation's disposition.
