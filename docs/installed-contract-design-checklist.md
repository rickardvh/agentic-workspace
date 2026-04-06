# Installed-Contract Design Checklist

Use this checklist when adding or materially changing a shipped installed surface in a package payload.

Use `docs/compatibility-policy.md` for stable-versus-mutable surface guidance, `docs/maintainer-commands.md` for commands, and `docs/contributor-playbook.md` for routing; this page is only the review bar for collaboration-sensitive installed surfaces.

## Ownership

- Does the surface have one clear primary owner: planning, memory, workspace orchestration, or generated support?
- If the surface is product-managed, is it clearly under `.agentic-workspace/` or another explicit managed boundary instead of blending into repo-owned prose?
- If the surface is repo-owned, can normal contributors edit it directly without guessing whether an upgrade will overwrite it?

## Canonical Source

- Is the editable source obvious?
- If the surface is generated, is the canonical manifest, template, or renderer named explicitly in the docs and workflow?
- Would a maintainer know what to edit first instead of patching a mirror?

## File Shape

- Is the file compact enough to merge safely under concurrent edits?
- Does it avoid broad hand-maintained tables, journal-like history, or status residue that should archive or rerender instead?
- If it is a current-state surface, is it weak-authority and easy to compress, replace, or delete?

## Lifecycle Markers

- Does the surface make active versus archived or current versus durable state explicit?
- Does it tell maintainers when the file should shrink, archive, rerender, or disappear?
- If the surface is temporary bootstrap or calibration state, is that temporary role explicit?

## Partial Adoption

- Does the package still make sense when installed alone?
- If another module is absent, does the surface degrade cleanly instead of assuming the full stack?
- If both modules are installed, is ownership still separate rather than merged into one ambiguous layer?

## Validation

- Is there a narrow check, doctor rule, or payload verification step that will catch obvious drift?
- If the surface is collaboration-sensitive, does at least one validation path check the collaboration-safe contract directly?
- Are generated outputs and their source validated against each other when drift matters?

## Upgrade And Removal

- Can upgrades replace or reconcile the surface deterministically?
- Is uninstall behavior obvious, especially for product-managed versus repo-owned surfaces?
- Would a maintainer know whether local customisation is expected, preserved, or overwritten?

## Review Bar

- If two contributors edited this surface on different branches, would the merge path be obvious?
- Does the surface stay quiet by default instead of adding ongoing workflow ceremony for simple work?
- Does it reduce reading and reasoning cost, or does it mostly create new startup burden?
- Does it preserve one clear owner per concern and avoid pushing package-local logic into the workspace layer by convenience?
- If the answer depends on chat context or maintainer folklore, tighten the contract before shipping the change.
