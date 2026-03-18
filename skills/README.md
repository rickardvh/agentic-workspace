# Skills Catalogue

This directory contains the product's bundled skills.

These skills are not part of the mandatory bootstrap payload, but they are part of the product distribution. Runtimes that support packaged skill discovery should be able to use them without a second installation step.

For maintainers of this repository, `skills/` is the canonical source of truth. Any bundled copy inside an installed package is only a runtime copy for explicit packaging or install-path testing and may be stale until the package is reinstalled.

## Available skills

- `memory-hygiene`
  - review checked-in memory
  - run freshness checks
  - prune, merge, or mark stale notes
- `memory-capture`
  - capture durable lessons into the right checked-in memory note
- `memory-refresh`
  - inspect changed files and refresh affected memory notes
- `memory-router`
  - identify the smallest relevant memory set for the current work
- `bootstrap-adoption`
  - introduce the memory bootstrap into an existing repository conservatively
- `bootstrap-populate`
  - populate new current-memory files conservatively after adoption
  - leave `task-context.md` minimal when there is no clear active work worth preserving
- `bootstrap-upgrade`
  - upgrade an installed bootstrap safely without flattening local customisation

## Fallback installation

If your runtime does not auto-discover packaged skills, install them manually with the Codex skill-installer helper:

```bash
install-skill-from-github.py --repo Tenfifty/agentic-memory --path skills/memory-hygiene
install-skill-from-github.py --repo Tenfifty/agentic-memory --path skills/memory-capture
install-skill-from-github.py --repo Tenfifty/agentic-memory --path skills/memory-refresh
install-skill-from-github.py --repo Tenfifty/agentic-memory --path skills/memory-router
install-skill-from-github.py --repo Tenfifty/agentic-memory --path skills/bootstrap-adoption
install-skill-from-github.py --repo Tenfifty/agentic-memory --path skills/bootstrap-populate
install-skill-from-github.py --repo Tenfifty/agentic-memory --path skills/bootstrap-upgrade
```

Or install several at once:

```bash
install-skill-from-github.py --repo Tenfifty/agentic-memory --path skills/memory-hygiene --path skills/memory-capture --path skills/memory-refresh --path skills/memory-router --path skills/bootstrap-adoption --path skills/bootstrap-populate --path skills/bootstrap-upgrade
```

## Fallback install from a local clone

Copy the desired skill directory into your Codex skills directory:

- source: `skills/<skill-name>/`
- destination: `$CODEX_HOME/skills/<skill-name>/`

For example:

- `skills/memory-hygiene/` -> `$CODEX_HOME/skills/memory-hygiene/`

After manual installation, restart Codex so the new skills are loaded.

## Maintainer note

When developing skills in this repository:

- edit and validate the repo copies under `skills/`
- treat bundled copies inside an installed package as disposable test installs
- reinstall the package only when you want to test the packaging path or the runtime-visible copy
