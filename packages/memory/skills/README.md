# Skills Catalogue

This directory contains the product's bundled bootstrap-lifecycle skills.

These skills are not part of the mandatory bootstrap payload, but they are part of the product distribution. Runtimes that support packaged skill discovery should be able to use them without a second installation step.

`REGISTRY.json` is the explicit bundled bootstrap-skill registry for this package. Treat it as the machine-readable source of truth for bundled memory bootstrap skill discovery and task-matching hints.

If the bundled skill is not already visible, prefer the installed `agentic-memory-bootstrap` command or the repo's checked-in `.agentic-workspace/memory/UPGRADE-SOURCE.toml` as the source of truth for any remote `uvx` or `pipx` runner spec.

For maintainers of this repository, `skills/` is the canonical source of truth. Any bundled copy inside an installed package is only a runtime copy for explicit packaging or install-path testing and may be stale until the package is reinstalled.

## Available skills

- `bootstrap-adoption`
  - introduce the memory bootstrap into an existing repository conservatively
- `bootstrap-populate`
  - populate new current-memory files conservatively after adoption
  - leave `task-context.md` minimal when there is no clear active work worth preserving
- `bootstrap-upgrade`
  - upgrade memory for an already bootstrapped repository safely
  - determine the installation source automatically
  - acts as the packaged implementation behind the checked-in `memory-upgrade` skill
- `bootstrap-uninstall`
  - finish bootstrap removal conservatively after the CLI removes safe bootstrap-managed files

These bundled skills are for bootstrap lifecycle work only, not for general repo workflows.
Day-to-day memory skills are shipped as checked-in repo skills under `memory/skills/` in the bootstrap payload.
General non-memory skills do not belong under `memory/skills/`.
When both a checked-in repo skill and a runtime-local mirrored copy exist, treat the checked-in copy as authoritative.

## Fallback installation

If your runtime does not auto-discover packaged skills, install them manually with your runtime's preferred skill mechanism:

- install `skills/bootstrap-adoption/`
- install `skills/bootstrap-populate/`
- install `skills/bootstrap-upgrade/`
- install `skills/bootstrap-uninstall/`

## Fallback install from a local clone

Copy the desired bundled bootstrap skill directory into your runtime's local skills location if needed:

- source: `skills/<skill-name>/`
- destination: your runtime's local skill path

For example:

- `skills/bootstrap-upgrade/` -> your runtime's local skill path for `bootstrap-upgrade`

After manual installation, refresh or restart your runtime so the new skills are loaded.

## Maintainer note

When developing skills in this repository:

- edit and validate the repo copies under `skills/` for bundled bootstrap skills and `memory/skills/` for checked-in core memory skills
- treat packaged copies and runtime-local mirrors as disposable test installs
- reinstall the package only when you want to test the packaging path or the runtime-visible copy
