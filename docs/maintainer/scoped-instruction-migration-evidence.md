# Scoped instruction migration evidence

The repository's root `AGENTS.md` previously contained the generic Workspace
startup adapter plus a globally loaded repository-specific dogfooding rule. The
adapter remains unchanged inside its managed fence. The dogfooding rule now
lives in `.agentic-workspace/instructions/workspace-dogfooding.md` and is scoped
to Workspace implementation, package, script, test, and maintainer-document
paths.

| Scenario | Before | After |
| --- | --- | --- |
| edit `src/agentic_workspace/operating_decision.py` | adapter plus dogfooding prose | thin adapter plus matched dogfooding instruction |
| edit `tests/test_workspace_cli.py` | adapter plus dogfooding prose | thin adapter plus matched dogfooding instruction |
| edit `README.md` in an unrelated host task | adapter plus dogfooding prose | thin adapter; dogfooding body remains unloaded |
| edit `docs/maintainer/control-input-disposition.md` | adapter plus dogfooding prose | thin adapter plus matched dogfooding instruction |

The migration is intentionally human-reviewed. The CLI reports source headings
and verification steps but does not infer scope or rewrite prose. The scoped
instruction body is not regenerated into `AGENTS.md`.
