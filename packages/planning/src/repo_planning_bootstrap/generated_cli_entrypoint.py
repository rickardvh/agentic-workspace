"""Planning Python command entrypoint for the generated CLI package.

The generated package owns parser and dispatch selection. Hand-owned runtime
primitive implementations live in :mod:`repo_planning_bootstrap._runtime_cli`.
"""

from __future__ import annotations

from repo_planning_bootstrap._runtime_cli import main

if __name__ == "__main__":
    raise SystemExit(main())
