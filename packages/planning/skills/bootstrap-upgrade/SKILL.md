---
name: bootstrap-upgrade
description: Upgrade an existing planning bootstrap install using the packaged CLI and rerun package-native validation.
---

# Bootstrap Upgrade

1. Run `agentic-planning-bootstrap doctor --target <repo>` first so you can inspect the recorded source in `.agentic-planning/UPGRADE-SOURCE.toml` and any age-based refresh warning.
2. Run `agentic-planning-bootstrap upgrade --target <repo>`.
3. Run `agentic-planning-bootstrap render-agent-docs --target <repo>`.
4. Run `agentic-planning-bootstrap check-planning-surfaces --target <repo>`.
5. Report any manual-review items that were intentionally preserved.
