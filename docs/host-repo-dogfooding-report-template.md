# Host-Repo Dogfooding Report Template

Use this template when a host repository runs Agentic Workspace and needs to report findings back to this package without copying host-private state or turning the report into a new evaluation framework.

The report should be compact enough to file as a Markdown issue, review artifact, or checked-in host note. Fill only the fields that materially affect product follow-up.

## Report Header

- Host repo: `<name, anonymized id, or private>`
- Report date: `YYYY-MM-DD`
- Reporter / agent runtime: `<human, agent, or mixed>`
- Package source: `<version, commit, source checkout, or installed package>`
- Installed preset/modules: `<minimal|planning|memory|full>` plus module list
- Run goal: `<one sentence>`
- Slice type: `<direct task|active execplan|handoff/restart|review|closeout>`
- Assurance level: `<absent|low|medium|high|critical>` plus source

## Run Summary

- Requested outcome:
- What landed:
- What did not land:
- Closure decision: `<closed honestly|left active|routed follow-up|blocked>`
- Residue destination: `<none|planning|memory|docs|config/check|issue|host-local>`

## Assurance And Proof

- Required refs:
- Control gates or blockers:
- Proof profiles selected:
- Proof commands selected:
- Proof commands executed:
- Waivers, skips, or unavailable proof:
- Missing evidence:
- Trust state after proof: `<usable|partial|lower-trust|blocked>`

## Touched Surfaces

List only the surfaces relevant to product learning.

| Surface | Owner | Why it changed | Host-private? |
| --- | --- | --- | --- |
|  |  |  |  |

## Friction Items

Classify every item before routing it. Do not treat every observation as package work.

| Observation | Evidence | Likely owner | Product should absorb? | Recommendation | Follow-up target |
| --- | --- | --- | --- | --- | --- |
|  | `<path, command, issue, or short transcript>` | `<product-general|repo-local adaptation|host docs/config|agent/operator mistake|successful behavior|non-actionable>` | `<yes|maybe|no>` | `<fix now|issue|docs|memory|dismiss|preserve>` |  |

## Operating-Cost Review

Use this section when assurance, planning, or proof machinery changed the cost of ordinary work.

| Work shape | Required fields | Inferred or optional fields | Default output impact | Decision |
| --- | --- | --- | --- | --- |
| Low-risk direct task |  |  |  | `<keep|hide|merge|remove|follow up>` |
| Medium-risk planned task |  |  |  | `<keep|hide|merge|remove|follow up>` |
| High/critical task |  |  |  | `<keep|hide|merge|remove|follow up>` |

## Privacy And Sensitivity

- Omitted host details:
- Redactions or anonymization:
- Evidence that should stay in the host repo:

## Conversion To Focused Issues

Create a package issue only when the row is product-general or likely product-general, has concrete evidence, and the suggested correction is narrower than the report.

Use the review/friction issue template for trust gaps or operating-cost friction. Use the bug template only for actual broken or unintended behavior. Leave repo-local adaptation needs in the host repo.
