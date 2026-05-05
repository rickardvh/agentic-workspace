# Planning CLI Naming

`agentic-planning-bootstrap` and `agentic-memory-bootstrap` are historical public command names. They began as install/adopt helpers, but the module commands now also own ongoing lifecycle operations such as `new-plan`, `promote-to-plan`, `archive-plan`, `summary`, `report`, `reconcile`, `handoff`, Memory routing, Memory reports, and note capture.

The name is therefore incomplete: agents can wrongly infer that the CLI is only for initial bootstrap, or that all lifecycle work should be described as bootstrap work. The current compatibility decision is:

- prefer `agentic-planning` and `agentic-memory` in new docs and workflow guidance;
- keep existing `*-bootstrap` commands as stable compatibility aliases;
- clarify in help output that `*-bootstrap` names are aliases, not the preferred mental model;
- use command names, documentation, and workflow guidance to distinguish install/adopt bootstrap from ongoing module lifecycle;
- defer package/module import renames until public aliases have proven usable.

Possible target names for a future migration:

- `agentic-planning` for the planning module lifecycle CLI;
- `agentic-memory` for the memory module lifecycle CLI;
- keep Python package/module names stable until public CLI aliases have proven usable.

Do not rename public commands abruptly. Prefer aliases first, document the preferred names, keep compatibility for existing repos, and only then consider deprecation language.
