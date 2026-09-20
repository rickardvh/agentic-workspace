# Maintain the documentation

Use this page when writing or reorganizing AW documentation. For product help,
start with the [documentation home](index.md).

## Give each page one reader and one job

The user guide answers how to install, use, configure, troubleshoot and remove AW.
Reference pages answer exact lookup questions. Integration guides help developers
build on public interfaces. Contributor pages explain changes to AW itself.

Keep those routes separate. The documentation home should help readers choose,
not list every document in the source tree. Reuse an existing page before adding a
new one; merge duplicate explanations and remove obsolete prose instead of
creating another layer of navigation.

## Introduce context before details

Open with the reader's task and the result the page helps them obtain. Define the
subject before using its specialized vocabulary. Each paragraph should build on
information already established, not require a later paragraph to explain why it
was relevant.

Explain general behavior before an example, and label the example's assumptions.
Show the action, expected result and meaningful failure case together. Put safety
warnings before the affected operation. Keep unrelated internals and historical
justification out of the sequence.

Avoid making readers translate implementation terms into practical consequences.
“Your saved instruction applies only to this checkout” is useful to a user;
its underlying admission mechanics belong in an integration reference.

## Keep examples usable and claims accurate

Use executable commands and supported imports. State prerequisites and placeholders.
Verify examples against the installed/public boundary, not merely a similarly
named source-maintenance function. Distinguish source-checked examples from ones
actually executed against a named artifact.

Generated references should come from their named contracts. Keep changing release
identities with the release guidance, but do not make a user reconstruct the basic
installation path from machine receipts. A concrete version-bound example is
better than either an invented command or a page of caveats without a next action.

Check links and fragments when replacing headings. Keep public paths when useful;
use a small compatibility anchor only for a real incoming reference, not to retain
an entire obsolete explanation. Check that each stacked PR works without a later
layer repairing its links or source claims.

## Retain the right detail

Do not delete required safety, compatibility or contribution rules while shortening
prose. Link to the specialist owner for detail and retain the practical consequence
at the point where a reader needs it.

Schemas, release evidence and historical reviews may remain exhaustive for their
specific consumers. They are not the ordinary user guide. Git and dated evidence
can preserve reconstruction history; current API introductions should not replay it.

A changed declaration of system intent still requires its existing source
reconciliation. A documentation rewrite does not itself establish new runtime
capability, supported platforms, independent review or release publication.
