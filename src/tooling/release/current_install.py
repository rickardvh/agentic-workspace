"""Refresh/check the existing install projection against accepted public release bytes."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[3]
PROJECTION = ROOT / "src/tooling/contracts/support_bearing_install.json"
REPOSITORY = "rickardvh/agentic-workspace"


def fetch(url: str) -> bytes:
    with urlopen(Request(url, headers={"User-Agent": "AW-install-currentness"}), timeout=60) as response:
        return response.read()


def projection(release: dict, receipt_bytes: bytes, promotion: dict, source_commit: str) -> dict:
    receipt = json.loads(receipt_bytes)
    version = release["tag_name"].removeprefix("v")
    if release["draft"] or release["prerelease"] or not all(part.isdigit() for part in version.split(".")) or len(version.split(".")) != 3:
        raise ValueError("Current install requires a published stable release")
    digest = hashlib.sha256(receipt_bytes).hexdigest()
    if (
        promotion.get("kind") != "agentic-workspace/support-bearing-promotion/v1"
        or promotion.get("status") != "passed"
        or promotion.get("source_commit") != source_commit
        or promotion.get("artifacts", {}).get("distribution-install-readiness.json") != "sha256:" + digest
        or receipt.get("kind") != "agentic-workspace/distribution-install-readiness/v1"
        or receipt.get("status") != "passed"
        or receipt.get("version") != version
    ):
        raise ValueError("Public release identity or accepted install receipt mismatch")
    base = f"https://github.com/{REPOSITORY}/releases/download/{release['tag_name']}/"
    artifact = receipt["artifact"]
    if (
        artifact["url"] != base + artifact["name"]
        or promotion["artifacts"].get(artifact["name"]) != "sha256:" + artifact["sha256"]
        or artifact["name"] not in {a["name"] for a in release["assets"]}
    ):
        raise ValueError("Install artifact is not in the accepted public release")
    return {
        "kind": "agentic-workspace/support-bearing-install-projection/v1",
        "version": version,
        "status": "passed",
        "published_at": release["published_at"],
        "release_url": release["html_url"],
        "source_commit": source_commit,
        "artifact": artifact,
        "install_command": receipt["install"]["command"],
        "receipt": {"kind": receipt["kind"], "sha256": digest, "url": base + "distribution-install-readiness.json"},
        "platforms": receipt.get("platforms", []),
    }


def check_current(actual: dict, expected: dict) -> None:
    if actual != expected:
        raise ValueError(
            f"Current install projection is stale: checked-in {actual.get('version')}, accepted public {expected['version']}. Run current_install.py --refresh and regenerate contract catalogues."
        )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--refresh", action="store_true")
    args = parser.parse_args()
    release = json.loads(subprocess.check_output(["gh", "api", f"repos/{REPOSITORY}/releases/latest"]))
    base = f"https://github.com/{REPOSITORY}/releases/download/{release['tag_name']}/"
    source = json.loads(subprocess.check_output(["gh", "api", f"repos/{REPOSITORY}/commits/{release['tag_name']}"]))["sha"]
    expected = projection(
        release, fetch(base + "distribution-install-readiness.json"), json.loads(fetch(base + "support-bearing-promotion.json")), source
    )
    if args.refresh:
        PROJECTION.write_text(json.dumps(expected, indent=2) + "\n", encoding="utf-8")
    else:
        check_current(json.loads(PROJECTION.read_text(encoding="utf-8")), expected)
    print(f"Accepted public install: {expected['version']} ({source})")


if __name__ == "__main__":
    main()
