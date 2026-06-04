# Knowledge Promotion Workflow

This document defines the canonical process for promoting durable interpretive understanding from transient contexts (chat, active plans, local notes) into the repository's permanent memory and documentation.

## Promotion Thresholds

Promote knowledge when it satisfies the **Anti-Concealment** and **Repeated-Evidence** rules in [`.agentic-workspace/docs/signal-hygiene-contract.md`](signal-hygiene-contract.md), specifically:

- **Rediscovery Cost**: Future work would pay a significant cost if the knowledge stayed only in chat residue.
- **Repeatability**: The pattern has appeared in at least two independent contexts.
- **Stability**: The understanding is stable enough to explain to a new contributor without immediate correction.

## Surface Selection Rules

Route knowledge to the strongest home based on its class:

| Knowledge Class | Surface | Purpose |
| --- | --- | --- |
| **Interpretive Hints** | Memory | Subsystem-specific context, recurring gotchas, and "why we do it this way" notes. |
| **Stable Doctrine** | Canonical Docs | High-level philosophy, design principles, and standing repo rules (e.g. `AGENTS.md`). |
| **Enforceable Rules** | Config / Checks | Policy that can be machine-read or verified (e.g. `.agentic-workspace/config.toml`, `scripts/check/`). |

## Workflow Steps

### 1. Capture (During Task)
Record new insights in the `Iterative Follow-Through` or `Discovered implications` field of the active execplan. Use `.agentic-workspace/planning/execplans/TEMPLATE.plan.json` as the machine-first template when creating a new plan.

### 2. Verify (Task Closure)
During the "Proof Report" phase, evaluate which captured insights meet the promotion thresholds.

### 3. Promote (Post-Execution)
- **To Memory**: Add a new note or update an existing one in the relevant memory path.
- **To Docs**: Update the relevant markdown file (e.g. `docs/design-principles.md`).
- **To Config**: Update `.agentic-workspace/config.toml` or equivalent.

### 4. Record Closure
In the `Execution Summary` of the archived plan, record where the knowledge was promoted in the `Knowledge promoted` field.

## Guardrails

- **Do not over-specify**: Keep Memory focused on interpretive value, not a copy of the source code.
- **Do not hide friction**: Knowledge promotion should explain *how* to handle friction, not hide the fact that the friction exists.
- **Prefer Repo-Native**: Always prefer checked-in docs/config over Memory when the knowledge is stable enough to be a hard rule.

## Refactoring Facts

Promote a refactoring discovery to Memory only when it will prevent expensive
rediscovery in future work. Good Memory candidates include:

- non-obvious behavior that must be preserved;
- legacy quirks with a business or domain rationale;
- dependency, runtime, or migration constraints discovered during the refactor;
- tests, fixtures, snapshots, or verification protocols that protect important behavior;
- dead-code or unused-path findings that are not yet safe to remove;
- anti-rediscovery warnings for future agents.

Reject transient observations such as "I read this file", raw test output,
one-off implementation notes, or guesses about business behavior without
evidence. A useful refactoring Memory note should include a compact summary,
evidence/source refs, `use_when`, `stale_when`, confidence, and retention or
promotion expectation. When the lesson becomes stable policy, promote it onward
to docs, config, checks, or tests instead of letting Memory become hidden
business-logic authority.

Example Memory-worthy refactoring fact:

```markdown
---
use_when: "Touching parser normalization or replacing parser fixtures"
stale_when: "The parser fixture suite is replaced or malformed-input behavior is documented in canonical parser docs"
evidence: ["tests/fixtures/parser/valid_cases.json", "verification:parser_refactor_2026_06"]
authority: "Memory is advisory context; parser docs/tests own enforceable behavior"
owner: "parser-review"
retention: "retain until promoted to parser docs/tests or superseded by a documented behavior change"
---

The parser accepts a legacy trailing delimiter because importer v1 emitted it.
Keep the fixture and do not simplify it away during helper extraction without
parser-review acceptance.
```

Good candidates include a non-obvious behavior invariant, a legacy quirk with a
domain rationale, a dependency/runtime constraint, a fixture or protocol that
protects important behavior, a dead-code candidate that is not yet safe to
remove, or an anti-rediscovery warning for future agents. Do not promote
transient observations, execution logs, raw transcripts, broad task chatter,
"I looked at this file" notes, or unverified guesses. If the only fact is that
this run had no durable lesson, record that in Planning closeout instead of
creating a Memory note.
