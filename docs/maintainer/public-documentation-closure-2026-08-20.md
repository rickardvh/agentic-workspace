# Public Documentation Closure

This report closes the operating-context documentation lane. It records subtraction and current owners; it is evidence, not a competing product-definition page.

## Owner map

| Reader question | Before | Final owner |
| --- | --- | --- |
| Product thesis and ordinary loop | README, overview, continuity loop, substep inventory, architecture, design principles | `docs/package/overview.md`, with README as entrypoint |
| Operating-context boundary | distributed across knowledge, Memory, architecture, and design pages | overview + `docs/architecture.md`; glossary supplies the compact definition |
| Modules/extensibility | root/package/module READMEs plus fixed first-party examples | `docs/package/modules.md` + `docs/extension-boundary.md`; module READMEs own domain detail only |
| Exact commands/options/effects | schema-shape pages plus hand-written command tables | generated `docs/reference/cli-catalogue.md` |
| Exact installed footprint/availability | hand-written installed-surface inventory plus raw contract | generated `docs/reference/installed-surface-catalogue.md` |
| Installation/support/security | distributed install, release, maturity, threat, and package pages | `docs/agentic-workspace-install.md` + threat model; generated support-install projection owns exact command |
| Maturity/evidence | package prose, dates, reviews, metadata, harness artifacts | `docs/maturity-model.md` + `docs/evidence-and-support.md`; package metadata and release receipts remain machine owners |
| Exact schema shapes | generated schema pages | unchanged generated schema pages, explicitly labeled as shapes rather than value catalogues |
| Maintainer/history | several pages under the public package path | maintainer docs/reviews; two contract-referenced compatibility pages remain visibly maintainer-only |

## Dispositions and subtraction

- Removed `docs/package/ordinary-continuity-loop.md`; stable loop meaning now lives in the overview and reconciliation contract.
- Removed `docs/package/operating-loop-substeps.md`; it no longer competes with the generic three-step loop.
- Removed `docs/package/generated-behavior-closure-inventory.md`; current exact facts come from generated contract catalogues and maintainer checks.
- Compressed the hand-written command map from 714 to 271 words and the installed-surface page from 1,649 to 363 words.
- Compressed the Planning README from 4,338 to 517 words and Memory README from 4,092 to 429 words. Both now explain only domain purpose, ownership, generic-loop participation, support route, and deeper owner paths. The Planning payload list remains because a checker mechanically binds it to installer authority.
- Retained `cli-boundary-tests.md` and `generated-behavior-test-inventory.md` at compatibility paths because checked-in generated-behavior contracts name them. Both now identify themselves as maintainer-only and are absent from first-contact navigation.
- Removed active issue-number framing from current package documentation and removed manual-date freshness claims from maturity/documentation status.
- Added the requested small glossary and evidence/support summary. These replace distributed definitions and marketing-style maturity inference rather than add another product abstraction.

The measured conceptual/entrypoint sample (README, owner docs, adoption/status docs, and three module READMEs) fell from 20,159 to 11,420 words, a 43.4% reduction. `docs/package/` fell from 14 to 11 pages. Generated current-value catalogues are intentionally larger reference material behind routing and are excluded from first-contact reading cost.

## Ambiguity removed

Before, Memory described itself as a broad checked-in repo-memory layer and package docs repeated durable knowledge/participation inventories, which could make “operating context” sound like a repository knowledge platform. The final public boundary says:

- ordinary source, docs, tests, and history remain canonical;
- core AW does not ingest, index, embed, or semantically model the repository;
- Memory owns bounded anti-rediscovery notes, not general persistence;
- richer retrieval, RAG, semantic indexes, or knowledge graphs are optional module territory.

Planning, Memory, and Verification remain named as shipped examples but not fixed architectural slots. Config, obligations, skills, guidance, and owner operations are host control inputs; closeout is terminal reconciliation.

## Exact-reference and freshness proof

- `generate_contract_catalogues.py` renders all command/subcommand/option values from `cli_commands.json` plus option groups, and all profile/module footprint cells from `workspace_surfaces.json` plus the module registry.
- Catalogue headers carry deterministic source-contract digests. Drift tests compare complete checked-in content to fresh rendering.
- Shared-state mutability is distinct from optional ignored local session/cache/log effects in command authority data and the generated view.
- Verification selected-but-unconfigured behavior is rendered from optional/degraded reference declarations.
- The support-bearing install page is generated from a checked-in projection of the immutable v0.41.1 release receipt, including receipt digest, dereferenced source commit, wheel URL/hash, and exact command. The release receipt remains authority.
- Schema pages remain generated shape references and are no longer advertised as current-value catalogues.

## Evidence and claim boundary

Deterministic tests and release receipts support contracts, installation, generated parity, and exact subjects. The public evidence summary separately retains one clean startup pass, one safe partial-intent pass, one weak/noncompliant Memory run, an active weakness-ledger item, and unavailable distinct-provider/strong-tier routes. The coordinated distributions remain alpha; documentation does not promote maturity beyond metadata or source-bound evidence.

This lane simplifies the public model but does not certify every environment, provider, agent, repository command, or future module.
