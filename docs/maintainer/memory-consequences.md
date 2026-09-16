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

A source-declared native Verification command may emit complete JSON stdout with
`future_value_candidate: {"lesson": "...", "rationale": "..."}`. Both nonempty
strings are bounded to 2048 bytes; total stdout is bounded to 8192 bytes and must
be untruncated. Only a currently admitted receipt nominates the observation. A
failure, retry, ordinary prose, transcript or private reasoning does not nominate
anything. The producer suggestion is untrusted and cannot authorize retention.

The ordinary executable proof procedure carries this candidate to a Memory
question. The agent judges future value and chooses unresolved, no retention,
stronger owner/already absorbed, or advisory Memory. Stronger-owner disposition
requires a current non-Memory source containing the complete bounded lesson; it
records an agent judgment, not owner admission. Advisory publication uses the
existing exact human/delegated capture authorization. Multiple candidates remain
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

Existing Memory owner tests cover interruption stages, policy drift and current
selection, including actual historical underuse material. Two public journeys
cover bounded advice delivery/large-detail activation and a non-Memory-worded
proof task through nomination, disposition, authorized publication and fresh
relevant delivery. Existing adapter conformance owns transport parity; these
journeys use one public transport. There is no new ordinary CI command or polling
loop. The additional work is bounded selected-source delivery and parsing one
already-read admitted command artifact. This evidence supports these owner
consequences, not whole-release acceptance or empirical agent learning quality.

The native frontier construction observer checks zero large-body materializations
for compact entry and exactly one on selected Memory/proof expansion, including
UTF-8 and CRLF chunk boundaries. Public stale/missing/dependency checks remain
unchanged. Streaming hashing preserves the existing normalized source identity.
