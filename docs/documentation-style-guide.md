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

## Keep guides short and references exact

A guide gives the shortest sufficient path to its reader's result and stops when
that job is done. Use one representative example; link to the existing exact
reference for options, fields and exceptional cases. Prefer deleting, merging or
linking over adding another explanation. Splitting one long guide into several
equally verbose pages does not reduce the reading burden.

References may be detailed and exhaustive. Keep generated contracts complete and
change them through their source. Put dated evidence and reconstruction history
in their existing evidence homes; retain history in a current guide only when it
changes the reader's present action. Navigation should lead to guides first, then
specialist reference and evidence. Judge sufficiency by the reader's job, not a
word quota. Preserve safety and compatibility details at the affected step.

## Use ordinary language before implementation vocabulary

Open with the reader's task and the result the page helps them obtain. Explain the
concrete file, command, setting, action or consequence before introducing a
specialised term. Each paragraph should make the subject clearer using information
the reader already has; do not make readers hold an unexplained internal term until
later prose reveals what it means.

Do not require readers to learn repository-internal vocabulary merely to follow a
guide. Words such as “owner”, “admission”, “projection”, “custody”, “currentness”,
“surface”, “claim boundary” or “support-bearing” are not documentation shortcuts.
Replace them with the actual meaning when ordinary language is sufficient. When an
exact public identifier or genuinely necessary technical term must remain, keep it
exact and explain it locally at first use.

Explain general behaviour before an example, and label the example's assumptions
so readers can distinguish examples from general claims. Show the action, expected
result and meaningful failure case together. Put safety warnings before the
affected operation. Keep unrelated internals and historical justification out of
the sequence.

Prefer “Your saved instruction applies only to this checkout” over an explanation
of the internal checks that make that true. Put those implementation details in a
specialist reference only when that reader actually needs them.

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

A changed declaration of system intent still requires the existing checks that
keep its generated and copied sources in sync. A documentation rewrite does not itself establish new runtime
capability, supported platforms, independent review or release publication.

## Apply the guide and judge the result

The repository's [documentation instruction](../.agentic-workspace/instructions/documentation.md)
uses `governed_by` to supply this guide for its declared documentation scope.
Changes to the guide require a focused Verification review of the documentation
scope. Review the affected groups until every current document is covered;
unchanged documents that already follow the guide need no artificial edits.

Loading the guide supplies context; it does not prove understanding or compliance.
Writers and independent reviewers judge prose quality against the reader's task.
An accepted group records its exact sources, consumers and rationale. A fresh
agent can continue pending groups without the original conversation.

Use existing deterministic checks for the properties they actually establish,
such as Markdown structure, links or generated-reference freshness. Passing them
does not establish clarity, useful sequencing or suitability for the reader.
