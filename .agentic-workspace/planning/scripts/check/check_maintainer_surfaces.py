#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
from pathlib import Path

MODULE_SCRIPT = Path(__file__).resolve().with_name("check_planning_surfaces.py")


def _load_module():
    spec = importlib.util.spec_from_file_location("workspace_maintainer_checker", MODULE_SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load maintainer checker module from {MODULE_SCRIPT}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_MODULE = _load_module()
REPO_ROOT = _MODULE.REPO_ROOT
PlanningWarning = _MODULE.PlanningWarning
gather_maintainer_warnings = _MODULE.gather_planning_warnings
gather_maintainer_summary = _MODULE.gather_planning_summary
main = _MODULE.main


if __name__ == "__main__":
    raise SystemExit(main())