from __future__ import annotations

import argparse
import json
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Any

import coordinated_release
import preview_release

ROOT = Path(__file__).resolve().parents[2]
MANIFEST_NAME = "agentic-workspace-preview-release-manifest.json"
READINESS_NAME = "distribution-install-readiness.json"
PROMOTION_RECEIPT = "support-bearing-promotion.json"


def _run(
    args: list[str],
    *,
    cwd: Path = ROOT,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, cwd=cwd, env=env, check=True, capture_output=True, text=True)


def _load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise SystemExit(f"{path.name} must contain a JSON object")
    return value


def _tree_sha(commit: str) -> str:
    return _run(["git", "rev-parse", f"{commit}^{{tree}}"]).stdout.strip()


def smoke_published_preview(*, repo: str, tag: str) -> dict[str, Any]:
    ownership = json.loads((ROOT / ".github/release-ownership.json").read_text(encoding="utf-8"))
    verified = coordinated_release.verify_preview_release(ownership, tag=tag)
    if not preview_release.verify_published_preview(repo=repo, verified=verified):
        raise SystemExit("Published preview is incomplete; public-byte smoke cannot begin")

    with tempfile.TemporaryDirectory(prefix="aw-preview-public-smoke-") as directory:
        root = Path(directory)
        assets = root / "assets"
        assets.mkdir()
        _run(["gh", "release", "download", tag, "--repo", repo, "--dir", str(assets)])
        asset_names = {path.name for path in assets.iterdir() if path.is_file()}
        if PROMOTION_RECEIPT in asset_names:
            raise SystemExit("Preview release must not expose a support-bearing promotion receipt")

        manifest = _load_json(assets / MANIFEST_NAME)
        readiness = _load_json(assets / READINESS_NAME)
        expected_identity = {
            "release_class": "preview",
            "support_bearing": False,
            "tag": verified["tag"],
            "version": verified["version"],
            "artifact_commit": verified["artifact_commit"],
            "reconstruction_source_commit": verified["reconstruction_source_commit"],
        }
        for key, expected in expected_identity.items():
            if manifest.get(key) != expected:
                raise SystemExit(f"Published preview manifest {key} does not match the admitted preview subject")
        for key in ("release_class", "support_bearing", "tag", "version"):
            if readiness.get(key) != expected_identity[key]:
                raise SystemExit(f"Published preview install receipt {key} does not match the admitted preview subject")
        if readiness.get("kind") != "agentic-workspace/distribution-install-readiness/v1" or readiness.get("status") != "passed":
            raise SystemExit("Published preview install receipt is not a passed distribution-install readiness receipt")
        if readiness.get("registry_resolution_used") is not False:
            raise SystemExit("Published preview install receipt must not use registry resolution")

        root_package = next(
            (
                package
                for package in manifest.get("packages", [])
                if package.get("ecosystem") == "python" and package.get("name") == "agentic-workspace"
            ),
            None,
        )
        if root_package is None or not isinstance(root_package.get("wheel"), dict):
            raise SystemExit("Published preview manifest is missing the root wheel identity")
        wheel = root_package["wheel"]
        expected_url = f"https://github.com/{repo}/releases/download/{tag}/{wheel['asset']}"
        expected_requirement = f"agentic-workspace @ {expected_url}#sha256={wheel['sha256']}"
        expected_command = f'uv tool install "{expected_requirement}"'
        if readiness.get("artifact") != {"name": wheel["asset"], "sha256": wheel["sha256"], "url": expected_url}:
            raise SystemExit("Published preview install receipt does not bind the manifest root wheel")
        if readiness.get("install") != {"requirement": expected_requirement, "command": expected_command}:
            raise SystemExit("Published preview install receipt does not carry the exact advertised install command")

        tool_dir = root / "tool"
        bin_dir = root / "bin"
        clean_env = {key: value for key, value in os.environ.items() if key != "PYTHONPATH"}
        clean_env.update(
            UV_TOOL_DIR=str(tool_dir),
            UV_TOOL_BIN_DIR=str(bin_dir),
            UV_NO_CACHE="1",
        )
        _run(["uv", "tool", "install", expected_requirement], cwd=root, env=clean_env)
        executable = bin_dir / ("agentic-workspace.exe" if os.name == "nt" else "agentic-workspace")
        if not executable.is_file():
            raise SystemExit("Exact preview install did not expose the agentic-workspace executable")

        host = root / "host"
        host.mkdir()
        _run(["git", "init", "-q"], cwd=host, env=clean_env)
        started = _run(
            [
                str(executable),
                "start",
                "--target",
                ".",
                "--task",
                "Verify the published reconstruction preview",
                "--format",
                "json",
                "--projection",
                "full",
            ],
            cwd=host,
            env=clean_env,
        )
        result = json.loads(started.stdout)
        observed = result.get("runtime_compatibility", {}).get("observed_runtime", {})
        if observed.get("version") != verified["version"]:
            raise SystemExit("Installed preview native runtime version does not match the public preview version")
        decision = result.get("decision_packet")
        if not isinstance(decision, dict) or not decision.get("status"):
            raise SystemExit("Installed preview native start did not return a valid decision packet")

    return {
        "kind": "agentic-workspace/preview-public-smoke/v1",
        "status": "passed",
        "release_class": "preview",
        "support_bearing": False,
        "tag": verified["tag"],
        "version": verified["version"],
        "reconstruction_source_commit": verified["reconstruction_source_commit"],
        "reconstruction_source_tree": _tree_sha(verified["reconstruction_source_commit"]),
        "artifact_commit": verified["artifact_commit"],
        "artifact_tree": _tree_sha(verified["artifact_commit"]),
        "root_wheel": readiness["artifact"],
        "install_command": readiness["install"]["command"],
        "start": {
            "decision_status": decision["status"],
            "runtime_version": observed["version"],
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Install and smoke an exact published preview from its public GitHub Release bytes.")
    parser.add_argument("--tag", required=True)
    parser.add_argument("--repo", required=True)
    args = parser.parse_args(argv)
    print(json.dumps(smoke_published_preview(repo=args.repo, tag=args.tag), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
