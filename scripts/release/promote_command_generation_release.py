from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
GITHUB_API_RELEASES = "https://api.github.com/repos/rickardvh/command-generation/releases"
DOCKERFILE_REFS = (
    "generated/python/Dockerfile.conformance",
    "generated/python/Dockerfile.primitive-conformance",
    "generated/typescript.conformance.Dockerfile",
)
DEPENDENCY_PATTERN = re.compile(
    r"command-generation @ (?P<url>https://github\.com/rickardvh/command-generation/[^\"]+|git\+https://github\.com/rickardvh/command-generation\.git@[0-9a-f]{40})"
)
DOCKER_DEPENDENCY_PATTERN = re.compile(
    r"command-generation @ (?P<url>https://github\.com/rickardvh/command-generation/[^\"]+|git\+https://github\.com/rickardvh/command-generation\.git@[0-9a-f]{40})"
)


@dataclass(frozen=True)
class CommandGenerationRelease:
    version: str
    wheel_url: str
    sha256: str

    @property
    def dependency_url(self) -> str:
        return f"{self.wheel_url}#sha256={self.sha256}"

    @property
    def dependency_spec(self) -> str:
        return f"command-generation @ {self.dependency_url}"


@dataclass(frozen=True)
class PromotionResult:
    changed_paths: tuple[str, ...]
    stale_paths: tuple[str, ...]
    dependency_spec: str
    lock_refreshed: bool


def _fetch_json(url: str) -> dict[str, Any]:
    request = urllib.request.Request(url, headers={"Accept": "application/vnd.github+json", "User-Agent": "agentic-workspace"})
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def _sha256_url(url: str) -> str:
    digest = hashlib.sha256()
    request = urllib.request.Request(url, headers={"User-Agent": "agentic-workspace"})
    with urllib.request.urlopen(request, timeout=120) as response:
        while chunk := response.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def _normalize_sha256(value: str) -> str:
    digest = value.removeprefix("sha256:").lower()
    if not re.fullmatch(r"[0-9a-f]{64}", digest):
        raise ValueError(f"invalid sha256 digest {value!r}")
    return digest


def _release_from_payload(payload: dict[str, Any], *, requested_version: str | None = None) -> CommandGenerationRelease:
    tag_name = str(payload.get("tag_name") or "").strip()
    version = requested_version or tag_name.removeprefix("v")
    if not version:
        raise ValueError("command-generation release payload does not include a version")
    expected_asset = f"command_generation-{version}-py3-none-any.whl"
    assets = payload.get("assets", [])
    for asset in assets if isinstance(assets, list) else []:
        if not isinstance(asset, dict) or asset.get("name") != expected_asset:
            continue
        wheel_url = str(asset.get("browser_download_url") or "").strip()
        if not wheel_url:
            raise ValueError(f"{expected_asset} is missing browser_download_url")
        digest = str(asset.get("digest") or "").strip()
        if digest.startswith("sha256:"):
            digest = digest.removeprefix("sha256:")
        if not digest:
            digest = _sha256_url(wheel_url)
        return CommandGenerationRelease(version=version, wheel_url=wheel_url, sha256=_normalize_sha256(digest))
    raise ValueError(f"command-generation release {tag_name or version!r} has no {expected_asset} asset")


def discover_release(*, version: str | None = None) -> CommandGenerationRelease:
    if version:
        payload = _fetch_json(f"{GITHUB_API_RELEASES}/tags/v{version}")
        return _release_from_payload(payload, requested_version=version)
    return _release_from_payload(_fetch_json(f"{GITHUB_API_RELEASES}/latest"))


def _replace_dependency(text: str, *, release: CommandGenerationRelease, pattern: re.Pattern[str]) -> str:
    replacement = release.dependency_spec
    updated, count = pattern.subn(replacement, text)
    if count != 1:
        raise ValueError("expected exactly one command-generation dependency reference")
    return updated


def _write_if_changed(path: Path, content: str, *, check: bool, changed: list[str], stale: list[str], repo_root: Path) -> None:
    current = path.read_text(encoding="utf-8")
    if current == content:
        return
    relative = path.relative_to(repo_root).as_posix()
    stale.append(relative)
    if check:
        return
    path.write_text(content, encoding="utf-8", newline="\n")
    changed.append(relative)


def promote_command_generation_release(
    *,
    repo_root: Path,
    release: CommandGenerationRelease,
    check: bool = False,
    refresh_lock: bool = True,
) -> PromotionResult:
    changed: list[str] = []
    stale: list[str] = []

    pyproject = repo_root / "pyproject.toml"
    pyproject_text = pyproject.read_text(encoding="utf-8")
    _write_if_changed(
        pyproject,
        _replace_dependency(pyproject_text, release=release, pattern=DEPENDENCY_PATTERN),
        check=check,
        changed=changed,
        stale=stale,
        repo_root=repo_root,
    )

    for relative in DOCKERFILE_REFS:
        path = repo_root / relative
        dockerfile_text = path.read_text(encoding="utf-8")
        _write_if_changed(
            path,
            _replace_dependency(dockerfile_text, release=release, pattern=DOCKER_DEPENDENCY_PATTERN),
            check=check,
            changed=changed,
            stale=stale,
            repo_root=repo_root,
        )

    lock_refreshed = False
    if refresh_lock and not check and stale:
        subprocess.run(["uv", "lock"], cwd=repo_root, check=True)
        changed.append("uv.lock")
        lock_refreshed = True

    return PromotionResult(
        changed_paths=tuple(dict.fromkeys(changed)),
        stale_paths=tuple(dict.fromkeys(stale)),
        dependency_spec=release.dependency_spec,
        lock_refreshed=lock_refreshed,
    )


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Promote AW's command-generation dependency pin to a released wheel.")
    parser.add_argument("--version", help="command-generation release version to promote, for example 1.1.0. Defaults to latest.")
    parser.add_argument("--wheel-url", help="Explicit wheel URL. Use with --sha256 to skip GitHub release discovery.")
    parser.add_argument("--sha256", help="Explicit wheel SHA-256. Use with --wheel-url to skip GitHub release discovery.")
    parser.add_argument(
        "--trust-supplied-sha256",
        action="store_true",
        help="Offline escape hatch: trust --sha256 without downloading and verifying the explicit --wheel-url bytes.",
    )
    parser.add_argument("--check", action="store_true", help="Fail if pyproject or generated Dockerfile refs do not match the release.")
    parser.add_argument("--no-lock", action="store_true", help="Do not run uv lock after updating pyproject.toml.")
    parser.add_argument("--format", choices=["text", "json"], default="text")
    return parser.parse_args(argv)


def _release_from_args(args: argparse.Namespace) -> CommandGenerationRelease:
    if bool(args.wheel_url) != bool(args.sha256):
        raise SystemExit("--wheel-url and --sha256 must be provided together")
    if args.wheel_url and args.sha256:
        version = args.version
        if not version:
            match = re.search(r"command_generation-(?P<version>[0-9][^-/]*)-py3-none-any\.whl", str(args.wheel_url))
            version = match.group("version") if match else ""
        if not version:
            raise SystemExit("--version is required when --wheel-url does not contain the wheel version")
        supplied_digest = _normalize_sha256(str(args.sha256))
        if not args.trust_supplied_sha256:
            computed_digest = _sha256_url(str(args.wheel_url))
            if computed_digest != supplied_digest:
                raise SystemExit(
                    "explicit command-generation wheel SHA-256 mismatch: "
                    f"supplied {supplied_digest}, computed {computed_digest}"
                )
        return CommandGenerationRelease(version=version, wheel_url=str(args.wheel_url), sha256=supplied_digest)
    return discover_release(version=args.version)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    release = _release_from_args(args)
    result = promote_command_generation_release(
        repo_root=REPO_ROOT,
        release=release,
        check=bool(args.check),
        refresh_lock=not bool(args.no_lock),
    )
    payload = {
        "kind": "agentic-workspace/command-generation-release-promotion/v1",
        "version": release.version,
        "dependency": result.dependency_spec,
        "changed_paths": list(result.changed_paths),
        "stale_paths": list(result.stale_paths),
        "lock_refreshed": result.lock_refreshed,
        "status": "stale" if args.check and result.stale_paths else "updated" if result.changed_paths else "current",
    }
    if args.format == "json":
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(f"command-generation {release.version}: {payload['status']}")
        for path in result.changed_paths or result.stale_paths:
            print(f"- {path}")
    return 1 if args.check and result.stale_paths else 0


if __name__ == "__main__":
    raise SystemExit(main())
