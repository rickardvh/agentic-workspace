#!/usr/bin/env python3
"""Compatibility wrapper for the package-owned planning surface checker."""

from __future__ import annotations

import runpy
from pathlib import Path

CHECKER = Path(__file__).resolve().parents[2] / "packages" / "planning" / "scripts" / "check" / "check_planning_surfaces.py"

if __name__ == "__main__":
    runpy.run_path(str(CHECKER), run_name="__main__")
