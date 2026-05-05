# Planning CLI Naming

`agentic-planning` and `agentic-memory` are the public command names for the Planning and Memory package CLIs. The package CLIs began as install/adopt helpers, but now also own ongoing lifecycle operations such as `new-plan`, `promote-to-plan`, `archive-plan`, `summary`, `report`, `reconcile`, `handoff`, Memory routing, Memory reports, and note capture.

Older `*-bootstrap` compatibility names were incomplete: agents could wrongly infer that the CLI was only for initial bootstrap, or that all lifecycle work should be described as bootstrap work. The current naming decision is:

- prefer `agentic-planning` and `agentic-memory` in new docs and workflow guidance;
- do not ship `*-bootstrap` compatibility command names for non-bootstrap lifecycle CLIs;
- use command names, documentation, and workflow guidance to distinguish install/adopt bootstrap from ongoing module lifecycle;
- keep internal import package names stable until a separate migration is justified.

Possible target names for a future migration:

- `agentic-planning` for the planning module lifecycle CLI;
- `agentic-memory` for the memory module lifecycle CLI;
- keep Python import module names stable until a separate migration is justified.

Do not reintroduce `*-bootstrap` command aliases for ordinary lifecycle operations. Use bootstrap terminology only for actual install/adopt/upgrade payload lifecycle concepts.

