# Decision: Mature Repo Jumpstart Seed Candidates

## Status

Accepted

## Date

2026-04-14

## Load when

Read this note when deciding what durable memory surfaces a mature-repo jumpstart should seed first after safe install/adopt.

## Review when

Review this note if the jumpstart report starts preferring broad prose import, if the seed surfaces stop being compact, or if mature-repo discovery changes which durable contracts carry the highest anti-rediscovery value.

## Failure signals

Failure looks like jumpstart seeding broad docs, unstable workflow notes, or active backlog residue instead of compact durable operating knowledge.

## Decision

The first Memory seed candidates for mature-repo jumpstart are the compact durable contract surfaces that define repo operating boundaries:

- `docs/delegated-judgment-contract.md`
- `docs/resumable-execution-contract.md`
- `docs/capability-aware-execution.md`
- `docs/execution-summary-contract.md`

These surfaces are high-value because they capture repeatable decision boundaries, restart boundaries, task-shape guidance, and compact follow-through shape without importing broad prose.

## Why

Mature repos already carry useful durable operating knowledge. The first jumpstart Memory slice should extract that knowledge as compact anti-rediscovery facts instead of bulk-importing repository docs.

## Consequences

Memory seeding should prefer compact contract facts, stable boundaries, and execution-shape orientation over narrative doc mirrors. Broad prose remains discoverable through canonical docs, but it is not the first seed target.

## Expected downstream impact

The jumpstart report should remain pre-write and should point toward these candidate surfaces before any seed write happens. Later memory refreshes should keep the note compact instead of expanding it into a second docs index.

## Verify

Confirm that `agentic-workspace report --target ./repo --format json` still classifies the seed candidates in the discovery report, and confirm that the jumpstart contract continues to keep discovery pre-seed only.

## Last confirmed

2026-04-14 during mature-repo jumpstart discovery follow-through
