# Merge-order-independent package state

Issue #2532 removes two false shared-write boundaries while preserving semantic drift detection.

## Before and after evidence

PRs #2522 and #2525 were independent implementation lanes, yet both changed
`.agentic-workspace/verification/test-strategy-dispositions.json` and
`generated/.agentic-workspace-cli-fingerprint.json`. PRs #2523 and #2524 show the same pair of
branch-global writes. #2522, #2523, and #2524 each needed a merge-from-master commit after those
otherwise disjoint lanes overlapped. The overlap forced conflict-only head changes, another CI
round, and formerly another approval round even when the already-approved commit remained in the
branch history and the underlying owners did not compete. The review gate now carries a
`merge-ready` decision forward only across trusted-base merge commits whose stable PR patch remains
identical. Ordinary follow-up commits, unrelated merges, patch-changing conflict resolutions, and
newer blockers still fail closed.

The new storage shape removes both common paths:

- dispositions are written at
  `.agentic-workspace/verification/test-strategy-dispositions/<disposition-id>.json`;
- generated freshness receipts are written at
  `generated/<generated-package-owner>/.agentic-workspace-cli-fingerprint.json`.

The integration fixture creates two branches from one base. Each changes a different real
operation contract, corresponding generated output, owner freshness receipt, and disposition.
Both A→B and B→A merge without repair and produce the same sorted disposition set with all owner
receipts current. Separate fixtures prove that edits to the same disposition record and the same
generated owner still conflict explicitly.

## Fingerprint dependency classifications

Each retained input is read by command-package generation:

| Category | Scope | Why retained |
| --- | --- | --- |
| `pyproject.toml`, `uv.lock` | shared | Select the command-generation implementation and locked toolchain. |
| `LICENSE`, `.github/release-ownership.json` | shared | Supply generated package license and release metadata. |
| `scripts/generate/generate_command_packages.py`, `workspace_command_generation.py` | shared | Define generation and Agentic Workspace rendering behavior. |
| `command_package_ir.json` | shared | Defines package owners, targets, commands, and referenced contracts. |
| primitive manifest and Python/TypeScript support sources | shared | Define generated primitive support and copied runtime support. |
| referenced operation contracts | owner-scoped | Only contracts referenced by one package contribute to that owner's receipt. |
| `generated/<owner>/typescript/package.json` | owner-scoped | Its coordinated-release version is an intentional generator input. |

Ordinary runtime, Planning, tests, docs, unrelated contracts, and generated outputs are not
fingerprint inputs. Shared inputs intentionally update every owner receipt because they change the
generator or package model for every owner; owner operation changes update only their receipt.

## Consumer and migration parity

The runtime loader rejects the former shared disposition aggregate, validates filename/id and kind
for each owner record, and derives the same sorted logical `items` collection consumed by test
strategy checks. Existing records were migrated without changing their semantic fields. Launcher
status validates every checked-in owner receipt semantically. After that admission it stores the
aggregate Git-index identity only in `.agentic-workspace/local/cache`; subsequent clean checks use
Git metadata without hashing file contents. Dirty, missing-cache, no-Git, and semantic-drift paths
fall back to content validation and remain fail closed.
