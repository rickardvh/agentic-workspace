---
name: bootstrap-upgrade
description: Upgrade an existing planning bootstrap install through the root workspace lifecycle path, with package CLI fallback for debugging.
---

# Bootstrap Upgrade

1. Run `agentic-workspace upgrade --target <repo> --dry-run --format json` first and inspect selected modules, planned changes, review items, and the next safe command.
2. Resolve any review items before applying changes.
3. Run `agentic-workspace upgrade --target <repo> --format json`.
4. Run `agentic-workspace doctor --target <repo> --format json`.
5. Use `agentic-workspace doctor --target <repo> --modules planning` or `agentic-workspace upgrade --target <repo> --modules planning` for ordinary host-repo work; use the package-local Planning CLI only for package-local debugging when the root command cannot run.
6. Report any manual-review items that were intentionally preserved.
