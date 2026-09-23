# Current decision frontier (#3334)

Compact/carried entry and post-effect continuation select private native
resolution before optional owner detail is built. Full remains the exhaustive
diagnostic surface. There is no new public projection, query language, owner
callback protocol, cache or durable reference registry.

Ordinary `start` also accepts optional `material`: at most 16 observations or
unmet needs, totalling 64 KiB. Each item has `id`, `kind` (`observation` or
`need`), `summary`, and `source` with `producer`, `reference`, optional `revision`,
and `coverage` (`bounded`, `partial`, or `unknown`). An optional `dependencies`
list contains exact repository `reference`/`revision` pairs, reobserved with the
normal universal-newline SHA-256 source reader. External revisions remain
caller assertions. Neither a `user` producer label nor matching bytes confer
truth, human authority, permission, or proof.

An `observation` also carries findings produced by current repository work:
source/test inspection, repeated friction, unnecessary cost or a positive
simplification opportunity. Use truthful acting-agent/source-inspection
provenance and exact source dependencies when known. No failure or human
message is required. Materiality and the receiving owner's act/report/no-action
disposition remain semantic judgments; a weak code smell can stay disposable.

For CLI ingress, pass the context object (including `target`, `task` and
`material`) through `start --input`; explicit flags must match the envelope.
Python, TypeScript and JSON use the same context shape. Returned material binds
`work` to current work; carrying that item into different work is rejected.
Material does not change task identity or create retained state. A fresh start
without it is quiet; retain useful consequences only through an existing owner.

An existing `agentic-procedure` resource may declare optional `activation` with
`occasions` (`observation`, `need`, `binding`), natural-language `applicability`
and `outcome`. The resource itself is the entry; its existing qualified skill
and route identify it. `binding_owners` nominates current native blocker owners,
so their consequence can make the method visible without another semantic
question. Optional `settled_by` pairs (`selector`, scalar `value`) observe exact
native owner outcomes. They suppress only the optional method; source-authored
activation cannot modify native requirements or establish proof.

The existing registry carries a generated `activation_index`, derived from those
procedure declarations through the shipped native command:

```sh
agentic-workspace activation-index --target . --input index-request.json
```

The input is `{"registry":"tools/skills/REGISTRY.json","mode":"write"}`.
Use `"mode":"check"` in authoring validation; drift exits nonzero without writing.
Run this after adding/removing a declaration or changing its occasions, before
using or publishing the registry. The explicit authoring pass reads all declared
procedure resources, so it detects newly relevant membership that lazy operating
lookup cannot discover. Ordinary `start` does not perform this scan. This works
with installed native/npm/Python distributions and needs no source checkout,
Python maintainer module or copied declaration. First-party interface generation
includes equivalent derivation, checked for parity. Do not hand-maintain the
projection. Plain
skills need no index entry. Discovery admits registry membership and reads this
bounded projection (at most 128 entries), without constructing the route catalogue
or opening unindexed procedure resources. Only entries matching a current material
kind or binding owner open their skill/procedure sources for currentness validation;
changed declarations require regeneration. Registry parsing still scales with source
bytes, but unrelated skills add no procedure reads or activation construction.

On material or binding signals, the current activation frontier exposes these
occasions without loading branch bodies. The acting agent supplies only unresolved
applicability through the returned request. Each answer binds its own material,
procedure and declared context; unrelated material does not invalidate peers.
`unknown` and `defer` remain visible. `no-match` and justified `no-retention`
suppress their optional occasion while binding restrictions remain. Selecting or
reading a procedure leaves its outcome unsettled. There is no durable cursor.

## Construction and authority

All resolutions retain configuration/source grammar and compatibility admission,
current capability discovery, source-set membership, startup/instruction delivery
and restrictions, Memory applicability/capture custody, Planning selection and
pending changes, Assignment/requirements, Verification obligations/evidence and
source reconciliation. Independently registered owners still run their admitted
resolver: its opaque contribution can block, so it cannot safely be skipped.
These are current authority inputs, not optional diagnostics.

The removed duplicate Verification probe is replaced by its static contract;
the real Verification contribution is resolved once with current Planning,
instruction and applicability context. Its authority is unchanged. The private
selection boundary additionally bypasses these optional builders:

- Configuration field-edit catalogues. Recovery/deferred choices, source binding
  and any submitted proposal still resolve.
- Verification command-choice/report alternatives, profile catalogue hashes and
  duplicated judgement packets. Obligations, applicability gaps, source identity,
  evidence admission and exact selected execution remain mandatory.
- Planning portability diagnostics, including metadata probes of referenced
  local artefacts. Current Planning state and reconciliation remain mandatory.

Memory bodies, selected skill resources and claim-review source reads already
had selected-request boundaries; those remain. Parsing/hashing governing source
declarations is still required to notice new members. This is not a claim of
constant total work as source bytes grow, or of avoiding opaque owner callbacks.

Each lazy detail reference addresses a top-level owner and binds that owner's
current identity plus exact work/request context. Selected reentry chooses that
owner's optional builders before resolving; it does not build all diagnostics to
locate a hash. Shared mandatory contributions still run because composed public
request identities depend on their capability/current-work context. It avoids
unrelated optional hydration, not every unrelated owner check. References are
opaque to clients and grant no effect authority. Source additions and relevant
drift are reobserved; lost carriage uses fresh entry.

Carriage contains exact selected action/question envelopes and small lazy owner
descriptors. Full owner objects are never copied into carriage. Exact actions,
questions, competing actions, blockers, claim limits and selected skill refs stay
available without a model detail hop. Full detail remains selectable and must
match the supported exhaustive owner value.

The proof procedure consumes this same boundary. Before command selection it
gets executable choices; after an exact selection it skips untaken choices and
manual report alternatives. Optional profile discovery remains reachable through
its Verification detail reference and reports an omitted count. Native effect
admission still performs its full validation; confirmed effect truth is captured
before resolving the next frontier. Optional method drift can stop composed
preparation without weakening a committed effect or its current continuation.

## Bounded evidence

`native_frontier`'s Rust regression instruments actual builder entry in test
builds only. With one versus 128 declared commands, full resolution builds one
versus 128 command alternatives and the same number of report alternatives;
compact and already-selected proof build zero of either. All three resolve one
Verification contribution. The test compares complete compiled decisions and
owner detail bindings, addresses Configuration without building proof choices,
and verifies that a confirmed check's compact continuation also builds zero
alternatives. It now also readmits the actual committed receipt with 128 alternatives,
compares full/compact claim restrictions, and instruments the composed execution
path after its effect: zero untaken choice/report builders. Freshness retrieves the
exact route and command from authenticated publication custody and validates only
that selection; post-effect composition does not request alternative detail.
There is no production telemetry store.

Before this receipt-reentry correction, the public JSON fixture measured UTF-8 compact serialisation on Windows:

| Declared commands | Full bytes | Compact bytes | Carriage bytes | Full ms | Frontier ms |
| --- | ---: | ---: | ---: | ---: | ---: |
| 1 | 101,456 | 4,229 | 4,841 | 102.3 | 98.5 |
| 128 | 277,230 | 4,229 | 4,841 | 112.0 | 101.9 |

The empty target also carried 4,841 bytes. Times are single process-start-inclusive
observations, not a speedup guarantee. Mandatory source parsing/hashing still
scales; optional construction and transport do not scale with these alternatives.
The old source path resolved Verification twice and carried full owner envelopes;
that baseline diagnosis is a source trace, not a new historical timing trial.

`test_native_frontier.py` checks exact full/detail equivalence, restriction
visibility, unrelated-file reuse, source-set invalidation, carried selection and
fresh-process/no-carriage recovery. Existing operating-carriage and continuation
journeys cover exact action/question use, forged or moved carriage, all three
projections, current source changes and committed-effect recovery. The proof
procedure tests cover receipt admission, scope/measurement integration and both
mandatory-source failure and optional method drift after a committed check.

Stop after these distinct behaviour classes, current native/adapter contract
checks and payload checks pass. Tests establish implementation behaviour; issue
acceptance, source reconciliation and independent review remain separate.
