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
