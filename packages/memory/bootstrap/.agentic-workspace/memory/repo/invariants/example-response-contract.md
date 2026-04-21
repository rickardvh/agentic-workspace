# Starter Example: Response Contract

This is a starter example for an invariant note.
Replace or delete it once the repository has a real contract or safety boundary to record.

## Invariant

- Machine-readable command output should keep a stable top-level `kind` and `schema` so weaker agents can stop guessing about shape.

## Why it matters

- Restart and handoff get more expensive when consumers have to infer output structure from prose or examples.

## Load when

- A task consumes or changes machine-readable command output.

## Review when

- A CLI report, summary, or handoff JSON shape changes.

## Failure signals

- Agents start inferring output shape from prose because the top-level schema is missing or unstable.

## Verify

- Run the narrowest command test or payload check that proves the contract still matches the shipped schema.

## Last confirmed

2026-04-15
