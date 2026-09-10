from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

import coordinated_release

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_RECONSTRUCTION_REF = "reconstruct/first-stable"
DEFAULT_REMOTE = "origin"


def _run(
    args: list[str],
    *,
    cwd: Path = ROOT,
    check: bool = True,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, cwd=cwd, check=check, capture_output=True, text=True)


def _git(*args: str, cwd: Path = ROOT, check: bool = True) -> subprocess.CompletedProcess[str]:
    return _run(["git", *args], cwd=cwd, check=check)


def _resolve_commit(ref: str, *, cwd: Path = ROOT) -> str:
    return _git("rev-parse", f"{ref}^{{commit}}", cwd=cwd).stdout.strip()


def _tag_commit(tag: str) -> str | None:
    result = _git("rev-list", "-n", "1", tag, check=False)
    if result.returncode != 0:
        return None
    value = result.stdout.strip()
    return value or None


def _load_ownership(root: Path) -> dict[str, Any]:
    return json.loads((root / ".github/release-ownership.json").read_text(encoding="utf-8"))


def _path_allowed(path: str, allowed: list[str]) -> bool:
    for candidate in allowed:
        normalized = candidate.rstrip("/")
        if path == normalized or (candidate.endswith("/") and path.startswith(candidate)):
            return True
    return False


def _changed_paths(worktree: Path) -> list[str]:
    result = _git("status", "--porcelain=v1", "--untracked-files=all", cwd=worktree)
    paths: list[str] = []
    for line in result.stdout.splitlines():
        if not line:
            continue
        payload = line[3:]
        if " -> " in payload:
            _, payload = payload.split(" -> ", 1)
        paths.append(payload)
    return sorted(set(paths))


def _verify_release_only_paths(worktree: Path, ownership: dict[str, Any]) -> list[str]:
    allowed = [str(path) for path in ownership.get("preview_release_commit_allowed_paths", [])]
    if not allowed:
        raise SystemExit("release ownership must declare preview_release_commit_allowed_paths")
    changed = _changed_paths(worktree)
    unexpected = [path for path in changed if not _path_allowed(path, allowed)]
    if unexpected:
        raise SystemExit(f"Preview normalization changed non-release-only paths: {unexpected}")
    if not changed:
        raise SystemExit("Preview normalization produced no release-only changes")
    return changed


def _assert_source_is_reconstruction_candidate(source_commit: str, *, remote: str, reconstruction_ref: str) -> None:
    remote_ref = f"refs/remotes/{remote}/{reconstruction_ref}"
    if _git("show-ref", "--verify", "--quiet", remote_ref, check=False).returncode != 0:
        raise SystemExit(f"Missing fetched reconstruction ref {remote_ref}")
    result = _git("merge-base", "--is-ancestor", source_commit, remote_ref, check=False)
    if result.returncode != 0:
        raise SystemExit(f"Preview source {source_commit} is not reachable from {remote}/{reconstruction_ref}")


def _verify_existing_preview(tag: str, source_commit: str) -> dict[str, Any]:
    artifact_commit = _tag_commit(tag)
    if artifact_commit is None:
        raise SystemExit(f"Preview tag {tag} does not exist")
    temporary_root = Path(tempfile.mkdtemp(prefix="aw-preview-verify-"))
    worktree = temporary_root / "subject"
    try:
        _git("worktree", "add", "--detach", str(worktree), artifact_commit)
        command = [
            sys.executable,
            "scripts/release/coordinated_release.py",
            "verify-preview",
            "--tag",
            tag,
            "--source-commit",
            source_commit,
        ]
        result = _run(command, cwd=worktree)
        return json.loads(result.stdout)
    finally:
        if worktree.exists():
            _git("worktree", "remove", "--force", str(worktree), check=False)
        shutil.rmtree(temporary_root, ignore_errors=True)


def create_preview_subject(
    *,
    version: str,
    source_ref: str,
    remote: str,
    reconstruction_ref: str,
    push: bool,
) -> dict[str, Any]:
    version_obj = coordinated_release.Version.parse(version)
    tag = f"{coordinated_release.PREVIEW_TAG_PREFIX}{version_obj}"

    _git("fetch", remote, reconstruction_ref, "--tags")
    source_commit = _resolve_commit(source_ref)
    _assert_source_is_reconstruction_candidate(source_commit, remote=remote, reconstruction_ref=reconstruction_ref)

    existing = _tag_commit(tag)
    if existing is not None:
        verified = _verify_existing_preview(tag, source_commit)
        if push:
            _git("push", remote, f"refs/tags/{tag}")
        return {
            "kind": "agentic-workspace/preview-publication-subject/v1",
            "status": "existing-current",
            **verified,
            "pushed": push,
        }

    temporary_root = Path(tempfile.mkdtemp(prefix="aw-preview-create-"))
    worktree = temporary_root / "subject"
    tag_created = False
    try:
        _git("worktree", "add", "--detach", str(worktree), source_commit)
        ownership = _load_ownership(worktree)
        _run(
            [
                sys.executable,
                "scripts/release/coordinated_release.py",
                "prepare-preview",
                "--tag",
                tag,
                "--source-commit",
                source_commit,
            ],
            cwd=worktree,
        )
        _run(["uv", "lock"], cwd=worktree)
        changed = _verify_release_only_paths(worktree, ownership)
        _git("diff", "--check", cwd=worktree)
        _git("add", "--", *changed, cwd=worktree)
        staged = _git("diff", "--cached", "--name-only", cwd=worktree).stdout.splitlines()
        if sorted(staged) != changed:
            raise SystemExit(f"Preview staged path mismatch: staged={sorted(staged)} expected={changed}")
        _git(
            "-c",
            "user.name=github-actions[bot]",
            "-c",
            "user.email=41898282+github-actions[bot]@users.noreply.github.com",
            "commit",
            "-m",
            f"Preview {tag} from {source_commit}",
            cwd=worktree,
        )
        artifact_commit = _resolve_commit("HEAD", cwd=worktree)
        _git("tag", "-a", tag, artifact_commit, "-m", f"Preview {tag}", cwd=worktree)
        tag_created = True
        verified = json.loads(
            _run(
                [
                    sys.executable,
                    "scripts/release/coordinated_release.py",
                    "verify-preview",
                    "--tag",
                    tag,
                    "--source-commit",
                    source_commit,
                ],
                cwd=worktree,
            ).stdout
        )
        if push:
            _git("push", remote, f"refs/tags/{tag}")
        return {
            "kind": "agentic-workspace/preview-publication-subject/v1",
            "status": "created",
            **verified,
            "release_only_paths": changed,
            "pushed": push,
        }
    except Exception:
        if tag_created and not push:
            _git("tag", "-d", tag, check=False)
        raise
    finally:
        if worktree.exists():
            _git("worktree", "remove", "--force", str(worktree), check=False)
        shutil.rmtree(temporary_root, ignore_errors=True)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Create an immutable release-only preview subject without modifying the reconstruction branch."
    )
    parser.add_argument("--version", required=True, help="Unused coordinated numeric package version, for example 0.52.0")
    parser.add_argument("--source-commit", default="HEAD", help="Exact reconstruction commit/ref to preview (default: HEAD)")
    parser.add_argument("--remote", default=DEFAULT_REMOTE)
    parser.add_argument("--reconstruction-ref", default=DEFAULT_RECONSTRUCTION_REF)
    parser.add_argument(
        "--push",
        action="store_true",
        help="Push only the immutable preview tag. Tag push triggers the preview publisher; no branch is pushed.",
    )
    args = parser.parse_args(argv)

    result = create_preview_subject(
        version=args.version,
        source_ref=args.source_commit,
        remote=args.remote,
        reconstruction_ref=args.reconstruction_ref,
        push=args.push,
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
