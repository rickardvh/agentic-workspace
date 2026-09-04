from __future__ import annotations

import sys
from pathlib import Path

SOURCE_ROOT = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SOURCE_ROOT))

from agentic_workspace.cli import main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main())
