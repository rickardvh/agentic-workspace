# AW clear planning gate compression

Date: 2026-06-23

Related issues: #1680, #1695

## Context

After the initial ordinary-output budget guards, representative `implement` payload contributors showed `context.planning_safety_gate` as the largest docs-only default section. In clear direct-work cases, much of that gate duplicated `context.guidance` or selector-backed detail.

## Change

Tiny/default `implement` output now keeps clear/satisfied planning gates to an action-critical summary:

- status and gate result;
- workflow sufficiency;
- required next action;
- implementation/delegation booleans;
- compact changed-path facts.

Verbose and selector-backed implement output still expose richer planning safety detail. Attention or blocking gates retain richer default evidence so hard blockers, external issue gates, proof boundaries, and closure risks stay visible.

## Dogfood Measurement

Representative payload sizes from the local fixture:

- docs-only `implement README.md`: about 13.7 KB before, 11.9 KB after;
- simple code `implement src/app.py`: about 12.8 KB before, 11.1 KB after.

The budget guards were tightened to:

- docs-only implement: under 13 KB;
- code-task implement: under 12 KB.

## Guardrail

This reduction applies only to clear/satisfied planning gates. Non-clear planning safety gates still need enough default evidence for agents to see blockers without guessing or doing selector drill-down first.
