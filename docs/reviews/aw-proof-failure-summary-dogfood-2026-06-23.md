# AW proof failure summary dogfood

Date: 2026-06-23

Related issues: #1680, #1693

## Context

The #1689 dogfooding slice produced broad `make test-workspace` failures with repeated failure lines. The expensive part was not only rerunning the suite; it was reading large repeated logs before identifying that the active faults were localized proof-selection regressions.

## Change

Failed proof receipts can now accept `--receipt-log` as either a repo-local log path or a short caller-supplied excerpt. When present, the receipt stores a compact `failure_summary` instead of embedding the full log.

The summary records:

- failed command and result;
- full-log reference or excerpt provenance;
- failure-line count;
- top root-cause clusters;
- representative first failure per cluster;
- focused pytest rerun commands when pytest node ids are available;
- whether full-suite rerun is premature.

## Guardrail

The summary is repair guidance only. It does not infer semantic correctness from log text, does not hide the full log reference, and does not replace the full selected proof required before completion.

## Dogfood expectation

After a failed broad proof, future #1680 turns should record a failed receipt with `--receipt-log` before rereading or rerunning the full suite. If the summary is unclustered or misleading, that is dogfooding friction and should become a follow-up issue with the source log shape.
