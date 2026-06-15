# Verification Module

Agentic Workspace Verification is the repo-native home for reusable soft
verification protocols and bounded evidence records.

Boundary:

```text
Planning says what work is active.
Assurance says what evidence is required.
Verification says how evidence is produced, repeated, recorded, bounded, and reviewed.
Proof routes verification work into validation choices.
Closeout says what may honestly be claimed.
Memory keeps durable anti-rediscovery lessons after verification, not raw evidence.
```

The first implementation uses `.agentic-workspace/verification/manifest.toml`.
It supports protocol, scenario, proof-route, evidence-bundle, and known-gap
records and exposes them through:

```text
agentic-verification report --target . --format json
agentic-workspace report --section verification --format json
agentic-workspace proof --changed <paths> --verbose --format json
agentic-workspace implement --select verification --changed <paths> --format json
```

The module implementation lives in `packages/verification/`. Its
`agentic-verification` CLI is generated from the Verification operation contract
under `packages/verification/src/repo_verification_bootstrap/contracts/operations/`;
module-owned runtime primitives own manifest semantics, while root workspace
surfaces adapt the resulting projection.

## Evidence Strategy Report

The Verification report also includes a diagnostic `evidence_strategy` section:

```json
{
  "kind": "agentic-workspace/verification-evidence-strategy/v1",
  "status": "ready"
}
```

This section helps an agent inspect proposed or existing proof evidence next to
candidate host-owned strategy sources. It is intentionally host-neutral:
Verification does not prescribe a testing pyramid, AW-specific coverage style,
or conformance-first policy. It surfaces facts and decision questions; the agent
does the reasoning.

The first diagnostic slice uses cheap local inputs only:

- changed paths and task text passed to `agentic-verification report`
- `.agentic-workspace/verification/manifest.toml`, when present
- candidate repo-owned strategy, proof, and test-knowledge inventory docs, when present
- simple AST facts from changed Python test files

The first slice does not interpret prose in those docs and does not infer a
host strategy from phrase matching. It can report that candidate source files
exist, list changed test functions, identify simple same-file/name-prefix
groups, and ask what the agent should decide. Group questions ask whether the
members are one behavior class or separate regression records, which labels must
remain visible, what replacement evidence would be required, and which
host-owned source the agent should read. Item questions ask what behavior claim
is preserved, whether the item is executable proof or historical knowledge, who
should own the evidence after migration, and what replacement evidence must
exist before changing it.

The report also includes an `inventory_review` diagnostic for migration work.
It lists candidate test-knowledge inventory sources and per-file AST counts so
an agent can choose where to inspect first. These counts are routing facts only:
they do not prove coverage and do not authorize deletion, merging, or conversion.

Without host-owned structured strategy enums or configuration, dispositions remain
`needs-human-strategy-choice`, owners remain `unknown`, and confidence stays low.
The report does not delete tests, prove semantic equivalence, require a manifest
extension, or create a universal testing strategy for the host repository.

## Manifest Shape

```toml
schema_version = "agentic-workspace/verification-manifest/v1"

[scenarios.manual_walkthrough]
protocol_id = "manual_review"
title = "Manual walkthrough"
steps = ["Exercise the user-visible flow"]
expected_observations = ["The expected behavior is visible"]
pass_evidence_labels = ["manual_walkthrough_passed"]
fail_evidence_labels = ["manual_walkthrough_failed"]

[protocols.manual_review]
title = "Manual review"
purpose = "Repeatable verification when automated tests are not enough."
applies_to_paths = ["src/ui/**"]
scenario_refs = ["manual_walkthrough"]
expected_evidence = ["manual_walkthrough_passed"]
review_owner = "ui-review"

[proof_routes.manual_review_route]
protocol_refs = ["manual_review"]
scenario_refs = ["manual_walkthrough"]
commands = ["uv run pytest tests/test_ui_flow.py"]
review_aids = ["Capture a short observation summary."]

[evidence_bundles.manual_review_2026_05]
protocol_id = "manual_review"
scenario_id = "manual_walkthrough"
outcome = "passed"
evidence_items = ["manual_walkthrough_passed"]
transcript_summaries = ["Manual walkthrough passed; raw transcript not retained."]
claim_boundaries = ["slice"]
retention_until = "2099-01-01"

[known_gaps.manual_review_mobile_gap]
protocol_id = "manual_review"
scenario_id = "manual_walkthrough"
reason = "Desktop walkthrough does not prove mobile layout."
owner = "ui-review"
evidence_labels = ["mobile_walkthrough_passed"]
blocked_claims = ["close-parent-lane"]
residual_risk = "Mobile behavior remains unverified."
```

## Retention

Protocols and scenarios are durable repo artifacts. Evidence bundles are compact
claim evidence and should carry retention or staleness metadata when they can
expire.

Transcript evidence is summary-first. Raw transcript refs are optional and
bounded. Hidden/reference oracle material from evaluator workflows must stay out
of primary evaluator prompts and appear only as post-score review metadata.

Memory receives durable lessons or repeated gaps after verification. It should
not store raw transcript content or active evidence.

## Behavior-Preserving Refactors

For refactors and modernization work, use Verification to record current
behavior evidence before making or closing preservation claims. Keep the record
compact and claim-boundary focused:

```toml
[scenarios.parser_characterization]
protocol_id = "parser_refactor_characterization"
title = "Parser characterization"
steps = ["Run representative parser fixtures before and after the refactor"]
expected_observations = ["Existing valid-input outputs remain byte-for-byte stable"]
pass_evidence_labels = ["parser_characterization_passed"]
fail_evidence_labels = ["parser_characterization_changed"]

[protocols.parser_refactor_characterization]
title = "Parser refactor characterization"
purpose = "Current-behavior proof for a behavior-preserving parser refactor."
applies_to_paths = ["src/parser/**", "tests/fixtures/parser/**"]
scenario_refs = ["parser_characterization"]
expected_evidence = ["parser_characterization_passed"]
review_owner = "parser-review"

[evidence_bundles.parser_refactor_2026_06]
protocol_id = "parser_refactor_characterization"
scenario_id = "parser_characterization"
outcome = "passed"
evidence_items = ["parser_characterization_passed"]
transcript_summaries = ["Representative parser fixtures matched before and after; raw outputs not retained."]
claim_boundaries = ["work"]
residual_risk = "Malformed legacy inputs are not characterized."
retention_until = "2026-12-31"

[known_gaps.parser_malformed_legacy_gap]
protocol_id = "parser_refactor_characterization"
scenario_id = "parser_characterization"
reason = "Malformed legacy-input behavior lacks fixtures and domain acceptance."
owner = "parser-review"
evidence_labels = ["malformed_legacy_characterization"]
blocked_claims = ["close-parent-lane"]
residual_risk = "Do not claim full parser behavior preservation until this gap is closed or accepted."
```

Closeout may cite this evidence as characterization/current-behavior proof. If
only ordinary tests ran, closeout should say that explicitly and caveat any
`no behavior changed`, `business logic preserved`, compatibility, migration, or
dependency-upgrade claim unless domain acceptance or a stronger evidence class is
recorded. The same pattern can represent golden-master comparisons,
compatibility checks, migration dry-runs, or manual-scenario evidence by naming
the protocol, scenario, evidence bundle, claim boundary, and known gap. Keep raw
outputs out of Verification unless they are intentionally retained artifacts;
prefer compact summaries and stable evidence labels.

## Non-Goals

- No generic QA management system.
- No CI replacement.
- No raw transcript database.
- No Assurance ownership transfer.
- No Closeout ownership transfer.
