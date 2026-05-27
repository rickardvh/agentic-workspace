# Agent Instructions

Authority marker:

- authority: repo-owned
- canonical_source: `packages/verification/src/`
- safe_to_edit: true
- refresh_command: null

Module-local contract for work under `packages/verification/`.

- This module workspace contains the reusable `agentic-verification` source and tests.
- Verification-specific manifest parsing, report projection, and evidence
  semantics belong here.
- The AW package root may adapt or compose these outputs, but should not
  become the long-term owner of Verification policy.

Prefer focused validation for module changes:

```text
uv run pytest packages/verification/tests -q
uv run ruff check packages/verification
```
