## Retire an observed historical publication index

Use this path when Verification reports a nonempty legacy repository index without
authenticated custody. Before its dependent new proof, use the exact
`verification/retire-receipts/v1` request. Judge continuing value and unresolved
intent, then set `retire_legacy_index` and the three disposition judgments when
obsolete locators can be retired. Empty `sources` preserves receipt files; only
owner-offered sources can be separately removed. Preserve unfamiliar files and
unsupported index fields.

The guarded operation replaces obsolete locators with a current empty index and
commits custody. It grants old receipts no current proof authority. Interrupted
disposition returns `verification/recover-retirement/v1`; use that exact recovery
instead of replaying uncertain proof or editing index/custody files. Current proof
uses its normal local lifetime unless an explicit durable consumer needs promotion.
