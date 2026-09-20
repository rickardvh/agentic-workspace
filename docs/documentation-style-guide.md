# Documentation style guide

This guide is for humans and agents writing or reorganising repository
documentation: user guides, references, integration guides, contributor and
maintainer pages, and generated documentation. It governs documentation throughout
the repository, including package READMEs. For product help, start with the
[documentation home](index.md).

## Use British English

Use British English spelling and usage across all repository documentation, such
as “behaviour”, “specialised” and “organise”. Reconcile documentation you change;
an unrelated change need not copy-edit untouched historical or evidence files.

Preserve canonical spelling in code, API identifiers, commands, filenames and
quoted external text. Change generated prose through its authoritative source or
template, then regenerate it; do not hand-edit generated output to change spelling.

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
subject before using its specialised vocabulary. Apply the sequential-information
(Bayesian) writing rule: each sentence and paragraph should make the subject and
its relevance clearer using information already established. A reader should not
have to retain an unexplained fact while waiting for later prose to reveal why it
matters.

Explain general behaviour before an example, and label the example's assumptions
so readers can distinguish examples from general claims.
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
actually executed against a named artefact.

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
specific consumers. Specialist, generated and reference documentation should use
the structure and precision its actual reader needs, rather than imitate user-guide
prose. Git and dated evidence can preserve reconstruction history; current API introductions should not replay it.

A changed declaration of system intent still requires its existing source
reconciliation. A documentation rewrite does not itself establish new runtime
capability, supported platforms, independent review or release publication.

## Apply the guide and judge the result

The repository's [documentation instruction](../.agentic-workspace/instructions/documentation.md)
uses `governed_by` to supply this guide for its declared documentation scope.
Changes to the guide expose that scope for bounded reassessment through
Verification. Continue the returned groups until every current consumer is
covered; unchanged and still-conforming documents need no artificial edits.

Loading the guide supplies context; it does not prove understanding or compliance.
Writers and independent reviewers judge prose quality against the reader's task.
An accepted group records its exact sources, consumers and rationale. A fresh
agent can continue pending groups without the original conversation.

Use existing deterministic checks for the properties they actually establish,
such as Markdown structure, links or generated-reference freshness. Passing them
does not establish clarity, useful sequencing or suitability for the reader.
