from __future__ import annotations

import tempfile
from pathlib import Path

from generate_contracts import generate

GENERATED_PATHS = (
    Path("src/agentic_workspace/generated_semantics.py"),
    Path("src/agentic_workspace/semantic-ir.json"),
    Path("typescript/dist/index.js"),
    Path("typescript/dist/index.d.ts"),
    Path("typescript/package.json"),
    Path("typescript/semantic-ir.json"),
)


def main() -> int:
    root = Path.cwd().resolve()
    with tempfile.TemporaryDirectory(prefix="aw-generated-") as raw:
        generated = Path(raw)
        generate(root, output_root=generated)
        stale = [
            path.as_posix() for path in GENERATED_PATHS if (root / path).read_bytes() != (generated / path).read_bytes()
        ]
    if stale:
        for path in stale:
            print(f"stale generated contract: {path}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
