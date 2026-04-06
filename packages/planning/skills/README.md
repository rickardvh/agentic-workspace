# Skills Catalogue

This directory contains the product's bundled skills.

These skills are part of the package distribution and should be available to runtimes that support packaged skill discovery without a second installation step.

If a bundled skill is not already visible, prefer the installed `agentic-planning-bootstrap` command or the repo's checked-in `.agentic-planning/UPGRADE-SOURCE.toml` as the source of truth for any remote `uvx` or `pipx` runner spec.

For maintainers of this repository, `skills/` is the canonical source of truth. Any bundled copy inside an installed package is only a runtime copy for packaging or install-path testing and may be stale until the package is reinstalled.

## Available skills

- `bootstrap-adoption`
  - introduce the planning bootstrap into an existing repository conservatively
- `bootstrap-upgrade`
  - upgrade planning bootstrap files for an already bootstrapped repository safely
- `bootstrap-uninstall`
  - finish bootstrap removal conservatively after the CLI removes safe managed files
- `planning-autopilot`
  - execute one bounded planning milestone at a time from the checked-in planning surfaces

These bundled skills cover bootstrap lifecycle work and the bounded planning execution operator.
