# Governing-source review preparation: #3776 evidence

The trusted review helper now nominates existing Verification reconciliation
checks from admitted repository instruction metadata. It carries observations for
the exact PR base/head and leaves semantic currentness and readiness judgments
with their existing owners and independent reviewer.

On 2 October 2026, the focused helper suite passed seven cases. One bounded
governing-source fixture covered absent evidence, stale head evidence after a
current base, exact current head evidence, inherited stale base, ordinary consumer
and unrelated changes, and instruction-policy edits. Evidence for a different
stack head remained unknown. Malformed trusted metadata made preparation partial,
rather than silently removing a possible obligation. The existing trusted-loader
case confirmed that an unreviewed worktree replacement never executes.

The fixture's governing relationship matches this repository's documentation
instruction: `docs/documentation-style-guide.md` nominates the existing
Verification source reconciliation for
`.agentic-workspace/instructions/documentation.md`. A bounded repository check
also discovered that relationship directly from trusted baseline
`d1a29ed99f1896197b53c683f9bcd0cf399bc6b6` and its admitted instruction snapshot.
No manual relation nomination, head-authored helper execution or filesystem
corpus scan was used. Git reads were confined to the existing declared metadata.

Raw admitted and baseline instruction bytes differ after the repository's path
migration. The helper records both revisions as provenance; it does not interpret
that difference as semantic staleness. Native Verification remains responsible
for declaring whether migrated instruction bindings and coverage are current.

A fresh instruction consumer read the updated proof reference and six harmless
packets. It correctly distinguished introduced and inherited debt, rejected
unknown head evidence as sufficient, used the existing owner, and added no whole
relation repair for ordinary consumers or unrelated changes. Initially it treated
the helper's raw-byte `current`/`stale` declaration label as a second readiness
gate. That ambiguity was corrected at its source: provenance now says which
snapshot was read and whether its bytes match, and the guidance explicitly leaves
semantic currentness to the existing owner. The consumer's bounded re-entry
understood that exact current owner evidence resolves the particular obligation
while independent readiness remains separate. The original confusion is retained.

The reader additionally followed required repository startup guidance before its
two assigned reads; this scope deviation is recorded. It ran no runtime checks,
reviewed no real PR and supplied no approval. This is author comprehension
validation, not independent review. Its model identity was inherited from the
host and was not independently measured.

Two existing native source-reconciliation cases passed, proving governing-source
reverse scope and overlapping relation isolation at the actual owner. The helper
does not reimplement those semantics. The legacy review-owner fixture was corrected
to expect remembered Planning state to remain inert without current work selection;
no production Planning behavior changed.

The failure risk is omission or misattribution of a declared governing-source
obligation. The focused packet fixture and existing native owner tests cover that
boundary. No 375-document semantic audit, persistent review ledger, provider matrix
or additional review authority was introduced. Broader checks require a named
remaining risk. Raw packet and reader observations remain in task-owned scratch
`5450a90060156dbc06e596469e4954e7f32db2b8e18f0d40fbbcfa2a89d7fe82` for inspection.
