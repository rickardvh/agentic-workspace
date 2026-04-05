# Skills Catalogue

This directory contains the product's bundled bootstrap-lifecycle skills.

These skills are not part of the mandatory bootstrap payload, but they are part of the product distribution. Runtimes that support packaged skill discovery should be able to use them without a second installation step.

If the bundled skill is not already visible, prefer the installed `agentic-planning-bootstrap` command or the repo's checked-in `.agentic-planning/UPGRADE-SOURCE.toml` as the source of truth for any remote `uvx` or `pipx` runner spec.

For maintainers of this repository, `skills/` is the canonical source of truth. Any bundled copy inside an installed package is only a runtime copy for packaging or install-path testing and may be stale until the package is reinstalled.

## Available skills

- `bootstrap-adoption`
  - introduce the planning bootstrap into an existing repository conservatively
- `bootstrap-upgrade`
  - upgrade planning bootstrap files for an already bootstrapped repository safely
- `bootstrap-uninstall`
  - finish bootstrap removal conservatively after the CLI removes safe managed files

These bundled skills are for bootstrap lifecycle work only, not for day-to-day repo workflows. Day-to-day planning skills still belong in checked-in repo surfaces such as `tools/skills/`.
