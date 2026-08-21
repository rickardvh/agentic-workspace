# Scoped repository instructions

Put ordinary repository guidance in `.agentic-workspace/instructions/`. A plain
Markdown file applies globally. Add `paths` when it should apply only to part of
the repository; optionally add `read`, `use`, `checks`, or `protect`.

```console
agentic-workspace instructions new authentication --paths "src/auth/**"
```

```markdown
---
paths:
  - src/auth/**
read:
  - docs/security/authentication.md
use:
  - security-review
checks:
  - run: pytest tests/auth -q
protect:
  - generated/**
---

# Authentication

Preserve compatibility with existing tokens. Never log raw credentials.
```

Then validate and explain the result:

```console
agentic-workspace instructions check
agentic-workspace instructions explain --task "Update auth tokens" --changed src/auth/token.py
```

`check` is static and never runs declared commands. `explain` reports matching
instructions and their context, procedure, check, and protection consequences
in repository language. Add `--verbose` only when exact internal compiler input
is needed.

## Migration

Use `agentic-workspace instructions migrate --from AGENTS.md` for a
non-destructive heading inventory and review sequence. Choose and move one
coherent block at a time, validate it, and explain representative positive and
negative paths before deleting the old block. Keep `AGENTS.md` as a thin startup
adapter; do not generate a mirror of all scoped bodies back into it.

The public five-field format compiles through the bounded instruction clause IR
and the existing operating decision. Instruction files cannot grant authority,
execute callbacks, or introduce new effect kinds.
