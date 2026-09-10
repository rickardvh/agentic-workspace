from __future__ import annotations

import argparse
import hashlib
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
    result = _git("rev-list", "-n", "1", f"refs/tags/{tag}", check=False)
    if result.returncode != 0:
        return None
    value = result.stdout.strip()
    return value or None


def _load_ownership(root: Path) -> dict[str, Any]:
    return json.loads((root / ".github/release-ownership.json").read_text(encoding="utf-8"))


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
    unexpected = [path for path in changed if not coordinated_release.preview_path_allowed(path, allowed)]
    if unexpected:
        raise SystemExit(f"Preview normalization changed non-release-only paths: {unexpected}")
    if not changed:
        raise SystemExit("Preview normalization produced no release-only changes")
    return changed


def _reconstruction_head_ref(reconstruction_ref: str) -> str:
    if reconstruction_ref.startswith("refs/heads/"):
        return reconstruction_ref
    if reconstruction_ref.startswith("refs/"):
        raise SystemExit(f"Preview reconstruction ref must be a branch ref, got {reconstruction_ref!r}")
    return f"refs/heads/{reconstruction_ref}"


def _remote_tracking_ref(remote: str, reconstruction_ref: str) -> str:
    branch = _reconstruction_head_ref(reconstruction_ref).removeprefix("refs/heads/")
    return f"refs/remotes/{remote}/{branch}"


def _fetch_reconstruction_ref(*, remote: str, reconstruction_ref: str) -> str:
    head_ref = _reconstruction_head_ref(reconstruction_ref)
    tracking_ref = _remote_tracking_ref(remote, reconstruction_ref)
    _git("fetch", remote, f"{head_ref}:{tracking_ref}", "--tags")
    return tracking_ref


def _assert_source_is_reconstruction_candidate(source_commit: str, *, remote: str, reconstruction_ref: str) -> None:
    remote_ref = _remote_tracking_ref(remote, reconstruction_ref)
    if _git("show-ref", "--verify", "--quiet", remote_ref, check=False).returncode != 0:
        raise SystemExit(f"Missing fetched reconstruction ref {remote_ref}")
    result = _git("merge-base", "--is-ancestor", source_commit, remote_ref, check=False)
    if result.returncode != 0:
        raise SystemExit(f"Preview source {source_commit} is not reachable from {remote}/{reconstruction_ref}")


def _verify_existing_preview(tag: str, source_commit: str | None = None) -> dict[str, Any]:
    artifact_commit = _tag_commit(tag)
    if artifact_commit is None:
        raise SystemExit(f"Preview tag {tag} does not exist")
    temporary_root = Path(tempfile.mkdtemp(prefix="aw-preview-verify-"))
    worktree = temporary_root / "subject"
    try:
        _git("worktree", "add", "--detach", str(worktree), artifact_commit)
        # Use the invoking verifier, never execute code from an unverified tag.
        previous_root = coordinated_release.ROOT
        try:
            coordinated_release.ROOT = worktree
            return coordinated_release.verify_preview_release(_load_ownership(worktree), tag=tag, source_commit=source_commit)
        finally:
            coordinated_release.ROOT = previous_root
    finally:
        if worktree.exists():
            _git("worktree", "remove", "--force", str(worktree), check=False)
        shutil.rmtree(temporary_root, ignore_errors=True)


def _recover_publisher(*, remote: str, verified: dict[str, Any]) -> dict[str, Any]:
    """Rerun only the existing tag-push run for the verified immutable commit."""
    tag, artifact = verified["tag"], verified["artifact_commit"]
    remote_url = _git("remote", "get-url", remote).stdout.strip()
    repo = _run(["gh", "repo", "view", remote_url, "--json", "nameWithOwner", "--jq", ".nameWithOwner"]).stdout.strip()
    complete = verify_published_preview(repo=repo, verified=verified)
    if complete:
        return {"publication_status": "publisher-complete", "publisher_head_sha": artifact}
    workflow = ".github/workflows/preview-release.yml"
    runs = json.loads(
        _run(
            [
                "gh",
                "api",
                "--method",
                "GET",
                f"repos/{repo}/actions/workflows/preview-release.yml/runs",
                "-f",
                f"head_sha={artifact}",
                "-f",
                "event=push",
                "-f",
                "per_page=100",
            ]
        ).stdout
    )["workflow_runs"]
    exact = [
        run
        for run in runs
        if run.get("head_sha") == artifact
        and run.get("head_branch") == tag
        and run.get("event") == "push"
        and run.get("path") == workflow
        and run.get("repository", {}).get("full_name") == repo
    ]
    if not exact:
        raise SystemExit(f"No exact tag-push publisher run found for {tag} at {artifact}; tag retained, no substitute run created")
    run = max(exact, key=lambda item: item["id"])
    status = "publisher-active"
    if run["status"] == "completed":
        if run["conclusion"] == "success":
            raise SystemExit("Publisher succeeded but exact complete release assets are missing; tag retained")
        elif run["conclusion"] in {"failure", "cancelled"}:
            # Re-read the remote ref immediately before the effect. Never force,
            # delete, or recreate a tag to manufacture a new push event.
            refs = _git("ls-remote", remote, f"refs/tags/{tag}", f"refs/tags/{tag}^{{}}").stdout.splitlines()
            targets = {line.split()[1]: line.split()[0] for line in refs}
            if targets.get(f"refs/tags/{tag}^{{}}", targets.get(f"refs/tags/{tag}")) != artifact:
                raise SystemExit("Remote preview tag no longer matches the verified artifact commit")
            _run(["gh", "api", "--method", "POST", f"repos/{repo}/actions/runs/{run['id']}/rerun"])
            status = "publisher-rerun-requested"
        else:
            raise SystemExit(f"Publisher conclusion {run['conclusion']!r} is not recoverable automatically; tag retained")
    return {"publication_status": status, "publisher_run_id": run["id"], "publisher_head_sha": artifact}


def verify_published_preview(*, repo: str, verified: dict[str, Any], artifact_dir: Path | None = None) -> bool:
    """Check existing bytes before any publication effect; never overwrite assets."""
    tag = verified["tag"]
    result = _run(["gh", "api", f"repos/{repo}/releases/tags/{tag}"], check=False)
    if result.returncode:
        if "HTTP 404" in result.stderr:
            return False
        raise SystemExit(f"Cannot inspect existing preview release: {result.stderr}")
    release = json.loads(result.stdout)
    if release.get("tag_name") != tag or release.get("prerelease") is not True:
        raise SystemExit("Existing release is not the exact preview prerelease")
    with tempfile.TemporaryDirectory(prefix="aw-preview-assets-") as directory:
        downloaded = Path(directory)
        if release.get("assets"):
            _run(["gh", "release", "download", tag, "--repo", repo, "--dir", directory])
        manifest_path = downloaded / "agentic-workspace-preview-release-manifest.json"
        if manifest_path.exists():
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            expected = {key: verified[key] for key in ("tag", "version", "artifact_commit", "reconstruction_source_commit")}
            expected.update(release_class="preview", support_bearing=False)
            if any(manifest.get(key) != value for key, value in expected.items()):
                raise SystemExit("Published preview manifest does not match exact source/artifact identity")
            ownership = _load_ownership(ROOT)
            expected_packages = {item["name"] for item in ownership["packages"] + ownership["typescript_packages"]}
            packages = manifest.get("packages", [])
            if len(packages) != len(expected_packages) or {item["name"] for item in packages} != expected_packages:
                raise SystemExit("Published preview manifest omits or adds coordinated packages")
            if any(item.get("version") != verified["version"] for item in packages):
                raise SystemExit("Published preview package version mismatch")
            expected_receipts = {
                f"generated-command-conformance-node{major}.json" for major in ownership["semantic_conformance"]["runtime_majors"]
            }
            if {item["asset"] for item in manifest["semantic_conformance"]["receipts"]} != expected_receipts:
                raise SystemExit("Published preview manifest omits required runtime proof")
        for path in downloaded.iterdir():
            if artifact_dir is not None:
                local = artifact_dir / path.name
                if not local.is_file() or local.read_bytes() != path.read_bytes():
                    raise SystemExit(f"Existing immutable preview asset differs: {path.name}; refusing overwrite")
        checksums = downloaded / "SHA256SUMS"
        if not manifest_path.exists() or not checksums.exists():
            return False
        entries = {}
        for line in checksums.read_text(encoding="utf-8").splitlines():
            digest, name = line.split("  ", 1)
            if Path(name).name != name or name in entries or len(digest) != 64:
                raise SystemExit("Malformed preview checksum inventory")
            entries[name] = digest
        for name, digest in entries.items():
            path = downloaded / name
            if path.exists() and hashlib.sha256(path.read_bytes()).hexdigest() != digest:
                raise SystemExit(f"Published preview checksum mismatch: {name}")
        required = {
            manifest_path.name,
            "distribution-install-readiness.json",
            "redistributable-package-readiness.json",
            "security-supply-chain-readiness.json",
            "agentic-workspace.spdx.json",
        }
        for package in manifest["packages"]:
            for key in ("wheel", "sdist", "tarball"):
                if key in package:
                    item = package[key]
                    required.add(item["asset"])
                    if entries.get(item["asset"]) != item["sha256"]:
                        raise SystemExit("Preview package manifest/checksum mismatch")
        required.update(item["asset"] for item in manifest["semantic_conformance"]["receipts"])
        if set(entries) != required:
            raise SystemExit("Preview checksum inventory does not cover the exact manifest assets")
        return not release.get("draft") and all((downloaded / name).is_file() for name in required)


def create_preview_subject(
    *,
    version: str,
    source_ref: str | None,
    remote: str,
    reconstruction_ref: str,
    push: bool,
) -> dict[str, Any]:
    version_obj = coordinated_release.Version.parse(version)
    tag = f"{coordinated_release.PREVIEW_TAG_PREFIX}{version_obj}"

    fetched_reconstruction_ref = _fetch_reconstruction_ref(remote=remote, reconstruction_ref=reconstruction_ref)
    existing = _tag_commit(tag)
    if existing is not None:
        # Recovery belongs to the immutable tag, not today's branch head.
        # The verifier binds its recorded source to its exact single parent.
        expected_source = _resolve_commit(source_ref) if source_ref is not None else None
        verified = _verify_existing_preview(tag, expected_source)
        _assert_source_is_reconstruction_candidate(
            verified["reconstruction_source_commit"], remote=remote, reconstruction_ref=reconstruction_ref
        )
        recovery = {}
        if push:
            already_remote = bool(_git("ls-remote", "--refs", remote, f"refs/tags/{tag}").stdout.strip())
            _git("push", remote, f"refs/tags/{tag}")
            if already_remote:
                recovery = _recover_publisher(remote=remote, verified=verified)
        return {
            "kind": "agentic-workspace/preview-publication-subject/v1",
            "status": "existing-current",
            **verified,
            "pushed": push,
            **recovery,
        }

    source_commit = _resolve_commit(source_ref or fetched_reconstruction_ref)
    _assert_source_is_reconstruction_candidate(source_commit, remote=remote, reconstruction_ref=reconstruction_ref)
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
        _run([sys.executable, "scripts/generate/generate_external_consumer_profile.py"], cwd=worktree)
        _run([sys.executable, "scripts/generate/generate_command_packages.py"], cwd=worktree)
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
    parser.add_argument("--version", help="Unused coordinated numeric package version, for example 0.52.0")
    parser.add_argument("--check-published", metavar="TAG")
    parser.add_argument("--repo")
    parser.add_argument("--artifact-dir", type=Path)
    parser.add_argument(
        "--source-commit",
        help="Exact reconstruction commit/ref to preview (default: freshly fetched reconstruction branch head)",
    )
    parser.add_argument("--remote", default=DEFAULT_REMOTE)
    parser.add_argument("--reconstruction-ref", default=DEFAULT_RECONSTRUCTION_REF)
    parser.add_argument(
        "--push",
        action="store_true",
        help="Push only the immutable preview tag. Tag push triggers the preview publisher; no branch is pushed.",
    )
    args = parser.parse_args(argv)

    if args.check_published:
        if not args.repo:
            parser.error("--check-published requires --repo")
        verified = coordinated_release.verify_preview_release(_load_ownership(ROOT), tag=args.check_published)
        complete = verify_published_preview(repo=args.repo, verified=verified, artifact_dir=args.artifact_dir)
        print(f"complete={'true' if complete else 'false'}")
        return 0
    if not args.version:
        parser.error("--version is required")

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
