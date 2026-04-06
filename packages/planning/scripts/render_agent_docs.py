from __future__ import annotations

import importlib.util
from pathlib import Path

MODULE_SCRIPT = Path(__file__).resolve().parents[1] / ".agentic-workspace" / "planning" / "scripts" / "render_agent_docs.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("workspace_planning_render_agent_docs", MODULE_SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load planning render module from {MODULE_SCRIPT}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_MODULE = _load_module()
load_manifest = _MODULE.load_manifest
render_quickstart = _MODULE.render_quickstart
render_routing = _MODULE.render_routing
main = _MODULE.main


if __name__ == "__main__":
    raise SystemExit(main())
