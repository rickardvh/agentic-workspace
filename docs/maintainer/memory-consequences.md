# Memory consequences at the ordinary frontier

Selected advisory notes now arrive in `advisory_context`. A small note needs no
follow-up read request. The compact budget is 4096 bytes per note and 16384 total;
Source identity and UTF-8 validity are checked in bounded streaming chunks;
compact delivery retains at most its selected small-body budget and does not
construct a large body or decode/copy it into a string. Larger detail stays lazy
until selected Memory detail or the active proof
procedure needs it. Only selected sources are read. The existing bounded manifest
selection still parses metadata; adding unrelated entries does not add delivered
bodies. Source identity does not establish factual freshness. Missing, changed,
superseded or explicitly stale material requires reconciliation. Delivery is not
an acknowledgement, disposition, policy, proof or completion grant.

An interrupted disposition or publication formerly required copying a recovery
request back to its owner. A unique exact recoverable transaction now exposes the
same owner action directly. Execution still checks current policy, sources,
receiver, work and custody. Uncertain effects are not an instruction to replay the
original write. Multiple unresolved transactions retain their explicit choices.

## Explicit future-value observations

Advisory authoring also works without edited paths. Optional `origin` records
asserted evidence provenance; `routes_from` and `semantic_routes` declare future
retrieval applicability, while `dependency_paths` binds current source validity.
The exact proposal binds all of these and the note/manifest postimages separately
from publication authority. Without explicit cues, legacy edited-path authoring
is unchanged. No-edit authoring asks for a future cue instead of inventing changed
files or blanket scope. The existing reader delivers accepted advice for an
agent-selected current activity before the dependent action, under its existing
small-body budgets. No new route registry, feedback ledger or retrieval engine is
introduced. Manifest parsing scales with bounded metadata; unrelated bodies are
not delivered. A changed dependency suppresses reliance and exposes review evidence;
historical runtime availability still requires a present-state check.

Ordinary observations supplied through `material` also reach
`memory.candidates.requests`, through the existing correction procedure. Nomination
uses the supplied summary and provenance; it needs no permanent lesson or forecast.
Capture requires deliberate optionality, uncertainty and future applicability.
Accepted commitments and uncertain effects must remain with their durable owner.
There is no automatic tool-output collector or second activation question.

The local working set has 16 rows, 64 KiB of serialized state and a 14-day age
limit. Same-event replay keeps the original row and timestamp. Reads do not write
or refresh age; expired rows are excluded. Authorised capture evicts oldest optional
rows before writing, while `maintain` removes expired rows in the foreground.
Attributable files are fixed: `state.json` (64 KiB), `state.tmp` (64 KiB),
`prepared.json` (68 KiB), and a zero-byte lock, at most 196 KiB in total. A single
pending replacement precedes new mutations. Recovery checks exact preimages and
postimages; unknown files and conflicting source bytes remain preserved.
No-signal entry opens none of these files; path/activity selection reads only the
bounded set, presenting matches as unconfirmed historical evidence. Dependency
drift requires review, and present service availability always needs a live check.
Local files are ignored and do not establish portable handoff continuity.

Selected candidates expose a bounded `consolidate` request. The acting agent
compares the supplied evidence, scopes and current sources; there is no similarity
classifier, recurrence threshold or automatic synthesis. A justified result
returns the existing advisory publisher's request with selected evidence origins.
Deferral is passive and does not renew age. Deliberate discard is a valid outcome.
Confirmed publication precedes `complete` candidate subtraction; the owner checks
current native publication, declaration and validity. Alternatively, actual
stronger-owner absorption requires the existing exact receiving source and current
Verification consequence. Copied text and proposed edits are insufficient.

Advisory publication can revise one ordinary declared Memory note through
`revise_source` and `source_revision`. It binds exact source/manifest preimages,
preserves identity and unrelated declarations, and requires deliberate
`validity_review` when dependency baselines change. Governing material keeps its
deciding owner. An unchanged conclusion is quiet. A revision journal carries its
complete replacement and only the previous owned receipt references; confirmation
precedes their removal. Four interruption stages recover without duplicate
publication. Repeated completed revisions retain one note, one stable journal,
one current attempt/result pair and the shared zero-byte Memory lock. Unknown
temporaries or changed receipts are preserved rather than treated as disposable.
This guarantees process-interruption recovery at the tested publication stages,
not power-loss durability or automatic repair of arbitrary partial bytes.

Useful application, contradiction and inapplicability are ordinary supplied
observations referencing the affected note and scope. They can refine or discard
current meaning through the same path. Passive selection creates no feedback
ledger, hit count, age renewal or usefulness prompt. Durable obsolete material
still uses the existing terminal retirement owner; candidate expiry does not
retire advice, commitments or pending publication effects.

A source-declared native Verification command may emit complete JSON stdout with
`future_value_candidate: {"lesson": "...", "rationale": "..."}`. Both nonempty
strings are bounded to 2048 bytes; total stdout is bounded to 8192 bytes and must
be untruncated. Only a currently admitted receipt nominates the observation. A
failure, retry, ordinary prose, transcript or private reasoning does not nominate
anything. The producer suggestion is untrusted and cannot authorise retention.

The ordinary executable proof procedure carries this candidate to a Memory
question. The agent judges future value and chooses unresolved, no retention,
stronger owner/already absorbed, or advisory Memory. Stronger-owner disposition
requires a current non-Memory source containing the complete bounded lesson; it
records an agent judgement, not owner admission. Advisory publication uses the
existing exact human/delegated capture authorisation. Multiple candidates remain
explicit; publication requires a single selected evidence scope. No new ledger,
session or event store is introduced.

The exact request carries its Verification prerequisites across partial work and
handoff. An unresolved candidate affects `claim:complete`, not ordinary work or
unrelated effects. Losing all explicit context cannot reconstruct a candidate;
a fresh consumer must retain the owner request or admit the original receipt.
A changed subject or receipt invalidates the carried candidate. No-retention is a
successful disposition with no durable note. Without executable AW, read sources
under the startup skill and leave runtime nomination/publication unestablished.

## Evidence and operating cost

The #3758 lane uses one finite shared-fixture scenario. Permanent public journeys
cover an ordinary finding, optional candidate capture, new advice, confirmed
subtraction, contradictory runtime feedback and revision of that same note.
A differently scoped migration observation survives separately. Companion owner
checks cover same-event replay, capacity/expiry, dependency and source drift,
stronger receiving evidence, publication/cleanup interruptions and bounded current
receipt state. Activity recall and unrelated-work controls use the existing reader.

One fresh reader started with the ordinary job of preparing fixture checks, using
the shipped guidance and a configured native command. It chose reuse while the
configured shared service was running, restart after its observed status changed
to stopped, and no new retention for a one-off dedicated migration stub. No author
reminder preceded those semantic decisions. The advice remained byte-identical;
only the fixture status changed. The reader's first setup decision came from
current policy/status before advice arrived; advice was available before the
changed-status decision. This establishes scoped semantic behaviour, not saved
search, successful first-action recall or natural long-term payoff. #3191 retains
that separate question.

The exercise made 24 native AW invocations: 23 resolution/answer attempts and one
help call, including seven failures. It read source text 15 times across 11 files,
with 12 follow-up reads after three entry reads, plus one hash verification.
Errors included dropped prior answers, discovery/selection requests competing
within one owner, malformed projection/recovery input and two stale Memory detail
references despite carried context. A separate reproduction isolated a changing
nomination timestamp in lazy detail identity; the #3759 foundation now excludes
request templates from that identity and verifies delayed carried expansion while
changed evidence still rejects the old reference. This does not establish the
cause of every failed exercise call. The fixture's deliberately minimal checks
registry also exposed `procedure-path-undeclared` while advice was delivered.
These costs and limitations remain evidence, rather than being erased by a retry.
The exercise is author validation; independent acceptance remains separate.

Existing Memory owner tests cover interruption stages, policy drift and current
selection, including actual historical underuse material. Two public journeys
cover bounded advice delivery/large-detail activation and a non-Memory-worded
proof task through nomination, disposition, authorised publication and fresh
relevant delivery. Existing adapter conformance owns transport parity; these
journeys use one public transport. There is no new ordinary CI command or polling
loop. The additional work is bounded selected-source delivery and parsing one
already-read admitted command artefact. This evidence supports these owner
consequences, not whole-release acceptance or empirical agent learning quality.

The native frontier construction observer checks zero large-body materialisations
for compact entry and exactly one on selected Memory/proof expansion, including
UTF-8 and CRLF chunk boundaries. Public stale/missing/dependency checks remain
unchanged. Streaming hashing preserves the existing normalised source identity.

### Disposition of the earlier seven failed calls

The original exercise remains 24 native calls with seven failures. Its first
reuse decision preceded advice; it is not evidence of early recall or agent-led
consolidation. No successful rerun changes those observations.

| Failure | Classification and existing owner | Disposition |
| --- | --- | --- |
| Semantic detail after discovery, with prior carriage omitted | Caller misuse; workspace operating carriage | `owners.md` already requires keeping the updated carriage after each answer. The reference depends on that context. No Memory repair is justified. |
| Discover and select requests carried simultaneously | Generic AW interaction defect; `semantic-routes` selection and workspace operating carriage (`operating.rs`, `native_public.rs::owner_requests`) | Repaired in the second layer: automatic replacement and native ingress now share the same owner request key. Selection replaces completed read-only discovery; owners that accept multiple request kinds keep their prerequisites. The public carried discovery-to-selection regression and all 11 operating tests pass. This is a bounded existing-owner repair, not a new Memory subsystem. |
| Memory detail after ordinary material | Memory interaction friction; Memory lazy detail identity in `native_public.rs` | A separate controlled reproduction found wall-clock nomination timestamps changing lazy detail identity. Foundation commit `b34c14d44` excludes request templates from that identity, with delayed expansion and changed-material rejection tested. The historical call's precise cause remains unproven. Current reader evidence below decides whether the promised path still encounters this friction. |
| Memory detail after keep judgment | Memory interaction friction; same lazy detail owner | Same bounded repair and evidential limit as the preceding row. The two historical failures are counted separately. |
| Projection flag conflicting with complete input context | Caller misuse; CLI exact-envelope ingress | `owners.md` already says to put projection in a complete context object and avoid conflicting flags. No state effect occurred. |
| Carriage supplied without a recovery reference | Expected bounded rejection of malformed input; workspace operating reference selection | Recovery requires either an actual returned reference with its context or a fresh explicit task/target resolution. No effect was retried. Existing guidance suffices. |
| Empty recovery reference | Expected bounded rejection of malformed input; same owner | An empty string is not a returned reference. The same existing recovery instruction applies. |

The earlier `procedure-path-undeclared` observation is a fixture authoring defect,
owned by the repository-local tool-skill registry: the minimal checks entry omitted
its procedure path. The replacement fixture declares the path and supplies that
procedure. It does not change route validity rules or load all notes.

The per-layer replacement exercises, exact subjects and call costs are recorded in [Memory lane fresh-reader evidence](memory-lane-reader-evidence.md). The foundation now reports its fixed candidate effect paths so committed local replacements have a current continuation. The public finding/capture/discard journey checks this in addition to its bounded-storage assertions.

