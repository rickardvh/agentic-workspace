# Historical TypeScript activation and current native custody

TypeScript new-plan activation preserves an existing local selector or receipt before writing a candidate. With absent carriers, selection goes through the existing owner-select admission boundary and exclusive creation. A failed selection preserves its draft and reports the actual refusal; state registration does not proceed. No byte-check-based rollback deletion is attempted.

The earlier TypeScript scaffold lacked canonical owner fields required by
owner-select. That historical activation reported `owner-not-selectable` and
retained an unselected draft. This was a limitation of that scaffold, not the
current public native creation path.

The shared Rust owner now exposes bounded `planning/create/v1` and
`planning/update/v1` requests through ordinary native, JSON, Python and TypeScript
consumers. Creation validates the canonical material and acquires the exact
absent destination; selection remains a separate operation. Current creation,
update, return adoption and interruption recovery reuse native owner custody.
See [native creation](native-planning-creation.md) and the
[real-source migration evidence](native-planning-migration-dogfood.md).
Adding another TypeScript semantic constructor would recreate the split.

Existing local selections without native reconciliation custody remain readable source authority, but `continue-selected` is only task applicability. #3001 owns exact source-owner release/current producer admission and destination acceptance before first mutation; #2984 owns preserving the former representation until that reconciliation is complete. An old receipt kind, matching digest or owner-name string alone cannot supply transfer authority. No generic ownership database or second Planning representation is required.

The historical `tests/test_planning_selection_custody.py` evidence records the
scaffold correction. Current public creation and real-source continuation are
covered in `tests/test_native_planning_create.py` and
`tests/test_native_public_cli.py`. The retained-adapter negative in the former
also proves that old Python writes, TypeScript overwrite and rollback paths
cannot replace or remove a current native owner. Historical scaffold results
must not be presented as a limitation of current native creation or as acceptance
of the broader release candidate.
