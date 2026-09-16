---
name: workspace-proof-selection
description: Select and interpret proof for a routed claim level. Use when validation evidence, skips, warnings, retries, crashes, or negative proof need proof-specific interpretation.
---

# Workspace Proof Selection

This package-managed standard Agent Skill supplies a replaceable method over
Verification. Repository instructions/config own policy; current owners supply
scope, strategy, evidence and claims. The agent supplies semantic judgment.

## Callable path

Use the configured native invocation with `proof-procedure --target . --task
"<task>" --changed <path> --input <step.json> --format json`. Repeat `--changed`
for known paths. This command consumes one step, not a workflow program:

- `{"operation":"prepare"}` returns selected proof context, exact owner requests,
  the current operating decision and `procedure_revision`.
- Supply an owner-returned request or request array in `request`, with only its
  requested judgment filled, to another `prepare`. Existing operating `reference`
  and `answer` carriage can answer an exact current question. No effect runs.
- `{"operation":"execute"}` can carry one missing required check when current
  Verification returns `required_execution.status=unique-required-action`. The owner
  checks complete current scope and strategy, including lazy alternatives. One
  candidate alone is not a requirement. Multiple methods or unresolved applicability,
  strategy or authority yield for judgment; do not choose the first or shortest check.
- Otherwise choose a relevant `proof.execution_requests` item. Pass it unchanged in
  `{"operation":"execute","request":<exact item>,"expected_revision":<revision>}`.
  The method resolves that selection, invokes only its exact authorized native
  check, and carries its receipt into current Verification. It returns the
  remaining claim/source/reviewer obligations. No arbitrary next action runs.
- An exact previously returned `proof.report` action may instead be supplied in
  `invocation` for native custody reentry. Keep the full selected request set when
  a strategy assessment is needed; the method will not reconstruct its envelope.
- `{"operation":"direct"}` makes zero owner calls. Ordinary no-proof work need
  not call the method at all.

Retain exact work/request and method identity in disposable caller carriage.
There is no durable skill cursor. Preparation and continuation use the shared
current decision frontier. Receipt admission checks the exact authenticated route
and command without rebuilding untaken alternatives. Optional profile catalogues and full diagnostics remain
behind `operating.detail_refs`; a nonzero `omitted_profile_count` means more profiles
are available through the Verification detail reference. After relevant procedure drift, reread the
current skill; after policy, subject or source-set drift, use the returned owner
recovery. Unrelated files do not invalidate selected method material.

Inspect `effect` independently from preparation. A committed check stays committed
when later resolution fails. `reentry-required` preserves the exact native action
and diagnostic; `retry_effect=false` forbids assuming absence or preparing a new
run. Unknown effects use the existing native custody recovery. Batch execution
and automatic strategy/sufficiency answers are intentionally unsupported.

## Judgment boundary

Select evidence for the actual task, slice, lane or epic claim. Read the selected
protocol purpose, expected observations, escalation and review aids when judging
adequacy. Baseline and escalation/de-escalation permissions come from Verification.
Source commands and numeric ordering do not decide that judgment.

Classify failed, warning, skipped, retried, crashed, unavailable or incomplete
results honestly. A selected check's exit zero is not intent satisfaction.
Measurement admission comes from the native owner and its current private receipt,
not labels or helper arithmetic. Semantic protocol/domain applicability comes
from exact current judgments; never match task words or reinterpret the manifest.

Use current `proof.claim_review.request` to propose a bounded judgment with the
actual evidence refs and reason. Return its authorized answer through `prepare`.
Required source reconciliation and independent reviewer custody stay separate.
`strict_closeout` still requires a task claim judgment with no matching protocol.
A method's availability, skill identity or completion never grants proof or claims.

## Direct and unavailable paths

A knowledgeable agent can use `start` / `invoke` with the same exact owner requests,
policy and claim boundary without selecting this optional method. If the method
or compatible runtime is absent, read this Markdown and applicable repository
sources; current execution, evidence admission and claim authority remain unknown.
Do not emulate owners, fabricate waivers or advance source trust to clear a gap.

## Evidence and retention

Run the lowest sufficient current proof selected for the changed behavior and
requested outcome. Broaden only for a named unresolved risk. Distinguish validation,
issue completion, intent satisfaction and total operating cost. Reconcile actionable
remaining gaps through their existing owner; retain only knowledge that prevents
rediscovery. Do not infer lane completion from a local check or self-review.

The native composition and resource-method tests protect exact effects, currentness,
strict closeout and confirmed-effect recovery. Changes to this procedure must
cite behavior-impact evidence and update its canonical/payload surfaces together.

## Advisory consequences of observed proof

The executable procedure delivers current selected Memory advice with its ordinary
answer, expanding selected large detail for the active judgment. Treat it as
advisory, never as proof or permission. A currently admitted command may explicitly
emit a bounded `future_value_candidate` with `lesson` and `rationale`. The owner
then asks for the remaining materiality/strongest-owner disposition; failures and
retries alone do not nominate learning. Carry that exact pending request through
partial work or handoff, and use the existing capture authorization if advisory
retention is selected. No-retention is a valid disposition.
