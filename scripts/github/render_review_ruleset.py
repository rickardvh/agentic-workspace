"""Render the ruleset with an explicitly selected dedicated review App identity.

Read-only GitHub lookup; emits JSON to stdout, never applies repository settings.
The checked-in template is intentionally not an API-ready name-only rule.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
from copy import deepcopy
from pathlib import Path
from typing import Any

TEMPLATE = Path(__file__).resolve().parents[2] / ".github/rulesets/master-support-bearing.json"


def render_ruleset(template: dict[str, Any], app: dict[str, Any]) -> dict[str, Any]:
    app_id = app.get("id")
    if type(app_id) is not int or app_id <= 0 or app_id == 15368 or app.get("slug") == "github-actions":
        raise ValueError("Select a dedicated GitHub App, not the generic GitHub Actions publisher")
    if app.get("permissions", {}).get("checks") != "write":
        raise ValueError("Selected App must have checks:write permission")
    if app.get("permissions", {}).get("statuses") != "write":
        raise ValueError("Selected App must declare statuses:write for required-check expected-source selection")
    result = deepcopy(template)
    checks = [
        check
        for rule in result["rules"]
        if rule["type"] == "required_status_checks"
        for check in rule["parameters"]["required_status_checks"]
        if check["context"] == "Review approval"
    ]
    if len(checks) != 1 or checks[0].get("integration_id") != "REVIEW_PUBLISHER_APP_ID":
        raise ValueError("Expected exactly one unbound dedicated review publisher template slot")
    checks[0]["integration_id"] = app_id
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--app-slug", required=True, help="Independently selected publisher App slug")
    args = parser.parse_args()
    if not re.fullmatch(r"[a-zA-Z0-9-]+", args.app_slug):
        parser.error("Expected a GitHub App slug")
    response = subprocess.run(["gh", "api", f"apps/{args.app_slug}"], check=True, text=True, capture_output=True)
    print(json.dumps(render_ruleset(json.loads(TEMPLATE.read_text()), json.loads(response.stdout)), indent=2))


if __name__ == "__main__":
    main()
