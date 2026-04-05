# Decision: Repository Foundation Stability

## Status

Decided

## Date

2026-04-05

## Load when

- Planning the next iteration after the orchestration foundation stabilised.
- Deciding whether to promote the next ROADMAP candidate into active execution.

## Review when

- Next quarterly or major release planning occurs.
- Organizational priorities shift regarding developer tooling or agent infrastructure.

## Failure signals

- Root planning or memory systems stop acting as the single operational authority for the monorepo.
- A new active tranche is started without a bounded TODO or execplan surface.
- Package-local runtime copies or fixtures start acting as operational state again.

## Decision

Treat the repository foundation as stable.

- Root-owned planning and memory systems are the single operational authority.
- Both bootstraps use the unified `.agentic-workspace/` namespace with end-to-end validation.
- Package boundaries remain preserved with independent release cadence.
- Planning surfaces pass drift validation without warnings.

Next work is optional and should be driven by product priorities rather than repository cleanup debt.

## Why

- The root orchestration contract, ownership ledger, and validation targets are in place.
- Remaining work is additive product improvement, not structural cleanup.
- Dogfooding the planning and memory systems in this repo has validated that the operating model is usable in day-to-day development.

## Consequences

- The monorepo host is now the normal source of truth for ongoing work.
- Package maintainers can release independently with confidence in root orchestration.
- Future work should start from ROADMAP promotion rather than historical cleanup plans.

## Follow-through

- Keep archived execplans only as lightweight historical context.
- Promote new TODO entries only from bounded roadmap candidates.
- Monitor whether shared-tooling, integration-lane, or onboarding candidates become urgent enough to activate.

## Verify

- `TODO.md` has no active cleanup residue.
- `ROADMAP.md` carries only inactive candidate work.
- `make check` passes from the repository root.
- Package READMEs point at current `.agentic-workspace/` paths.

## Last confirmed

2026-04-05 after repository cleanup guidance was simplified
