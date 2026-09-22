"""Source-checkout diagnostic reader; not an installed AW command."""

from __future__ import annotations

import argparse
import json

from aw_maintainer.session_diagnostics import analyze_session_log, export_session_log, load_state_for_argv


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("operation", choices=["analyze", "export"])
    parser.add_argument("--target", default=".")
    parser.add_argument("--id", default="")
    parser.add_argument("--path", default="")
    parser.add_argument("--origin", choices=["agent", "test", "synthetic", "unknown", "all"], default="all")
    parser.add_argument("--detail", choices=["summary", "entries", "segments", "episodes", "contexts", "candidates"], default="summary")
    parser.add_argument("--page", type=int, default=1)
    parser.add_argument("--page-size", type=int, default=25)
    parser.add_argument("--format", choices=["json"], default="json")
    parser.add_argument("--no-artifacts", action="store_true")
    args = parser.parse_args()
    state = load_state_for_argv(["--target", args.target])
    selection = {"state": state, "session_id": args.id, "path": args.path}
    if args.operation == "analyze":
        result = analyze_session_log(**selection, origin_scope=args.origin, detail=args.detail, page=args.page, page_size=args.page_size)
    else:
        result = export_session_log(**selection, include_artifacts=not args.no_artifacts)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
