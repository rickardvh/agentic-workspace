# Planning CLI Naming

`agentic-planning-bootstrap` and `agentic-memory-bootstrap` are historical public command names. They began as install/adopt helpers, but the planning command now also owns ongoing lifecycle operations such as `new-plan`, `promote-to-plan`, `archive-plan`, `summary`, `report`, `reconcile`, and `handoff`.

The name is therefore incomplete: agents can wrongly infer that the CLI is only for initial bootstrap, or that all lifecycle work should be described as bootstrap work. The current compatibility decision is:

- keep existing `*-bootstrap` commands as stable public entrypoints;
- clarify in help output that the planning CLI also owns lifecycle operations;
- use command names, documentation, and workflow guidance to distinguish install/adopt bootstrap from ongoing planning lifecycle;
- defer any public rename to an alias-first migration where old commands continue to work.

Possible target names for a future migration:

- `agentic-planning` for the planning module lifecycle CLI;
- `agentic-memory` for the memory module lifecycle CLI;
- keep Python package/module names stable until public CLI aliases have proven usable.

Do not rename public commands abruptly. A future rename should add aliases, document the preferred names, keep compatibility for existing repos, and only then consider deprecation language.
