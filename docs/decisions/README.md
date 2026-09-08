# Repository decisions

This sparse archive preserves current choices whose rationale prevents repeated mistakes or re-litigation. It is ordinary repository-owned content, independent of AW and separate from Memory fallback or Planning state.

- [One semantic authority](shared-semantic-authority.md)
- [Identity lifetimes](identity-lifetimes.md)
- [Selected-outcome terminality](outcome-terminality.md)

Keep prose useful without software: decision, consequence, rationale, meaningful rejected alternatives, actual authors and deciding authority, scope, evidence and supersession. The optional fenced `aw-decision` block is a projection source for AW's existing material-decision contract, not executable permission.

Acceptance of a source record is distinct from configuring automatic consumption. The repository host must explicitly admit an exact Git commit for this archive, including the records' semantic provenance. A filename, tracked status, inline owner, or actor string alone is insufficient. New or changed records require source-owner admission; do not automatically advance that pin from HEAD.

Prefer adding a few decisions with future value over summarizing history. The ambiguous April Memory note remains under its existing owner and is not silently promoted or replaced here.

Ordinary native, Python, TypeScript and JSON `start` responses expose
`decision_sources.requests` for rationale in the current selected decision
closure. Submit one returned `decision-continuity/read-current-source/v1`
request through the ordinary public request interface to retrieve its bounded
body and the existing owner's current decision state. The request is bound to
the exact task, scope, admission, source and capability revision. Reading a
superseded or stale rationale grants no current consequence or authority;
unrelated work receives no rationale request. Changed source bytes require
source-owner reconciliation before another read.

The public regression copies the real shared-semantic-authority decision and
its admitted authority basis into a temporary repository, then independently
consumes this path through all four surfaces. Its fixture admission does not
supply independent acceptance of current repository changes. This read path
also does not supply the still-missing native admission of an independently
owned Memory fallback snapshot, promote the April note, author a decision or
advance the repository's configured admission.
