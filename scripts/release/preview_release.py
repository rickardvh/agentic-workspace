from __future__ import annotations

import argparse
import hashlib
import json
import os
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
    environment: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, cwd=cwd, check=check, capture_output=True, text=True, env=environment)


def _git(*args: str, cwd: Path = ROOT, check: bool = True, environment: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    return _run(["git", *args], cwd=cwd, check=check, environment=environment)


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
    # Exact Git objects need no checkout, index mutation or temporary repository.
    ownership = json.loads(_git("show", f"{artifact_commit}:.github/release-ownership.json").stdout)
    return coordinated_release.verify_preview_release(ownership, tag=tag, source_commit=source_commit, artifact_commit=artifact_commit)


def admit_preview_subject(*, tag: str, artifact_commit: str) -> dict[str, Any]:
    """Run from the trusted dispatch checkout; inspect P without executing it."""
    release_class, _ = coordinated_release.parse_release_tag(tag)
    if release_class != "preview":
        raise SystemExit("Publication admission requires a canonical preview tag")
    if len(artifact_commit) != 40 or any(character not in "0123456789abcdef" for character in artifact_commit):
        raise SystemExit("Publication admission requires an exact artifact commit SHA")
    _fetch_reconstruction_ref(remote=DEFAULT_REMOTE, reconstruction_ref=DEFAULT_RECONSTRUCTION_REF)
    if _tag_commit(tag) != artifact_commit:
        raise SystemExit("Remote preview tag does not match the requested artifact commit")
    verified = _verify_existing_preview(tag)
    if verified["artifact_commit"] != artifact_commit:
        raise SystemExit("Preview tag changed during admission")
    _assert_source_is_reconstruction_candidate(
        verified["reconstruction_source_commit"], remote=DEFAULT_REMOTE, reconstruction_ref=DEFAULT_RECONSTRUCTION_REF
    )
    return verified


def _recover_publisher(*, remote: str, verified: dict[str, Any]) -> dict[str, Any]:
    """Dispatch current reconstruction authority for the same immutable subject."""
    tag, artifact = verified["tag"], verified["artifact_commit"]
    remote_url = _git("remote", "get-url", remote).stdout.strip()
    repo = _run(["gh", "repo", "view", remote_url, "--json", "nameWithOwner", "--jq", ".nameWithOwner"]).stdout.strip()
    if verify_published_preview(repo=repo, verified=verified):
        return {"publication_status": "publisher-complete", "publisher_head_sha": artifact}
    # Never move or recreate a tag to manufacture an event. Dispatch inputs bind
    # the trusted branch workflow to P; admission independently verifies them.
    refs = _git("ls-remote", remote, f"refs/tags/{tag}", f"refs/tags/{tag}^{{}}").stdout.splitlines()
    targets = {line.split()[1]: line.split()[0] for line in refs}
    if targets.get(f"refs/tags/{tag}^{{}}", targets.get(f"refs/tags/{tag}")) != artifact:
        raise SystemExit("Remote preview tag no longer matches the verified artifact commit")
    _run(
        [
            "gh",
            "workflow",
            "run",
            "preview-release.yml",
            "--repo",
            repo,
            "--ref",
            DEFAULT_RECONSTRUCTION_REF,
            "-f",
            f"preview_tag={tag}",
            "-f",
            f"artifact_commit={artifact}",
        ]
    )
    return {"publication_status": "publisher-dispatch-requested", "publisher_head_sha": artifact}


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
        native = manifest["native_archive"]
        required.add(native["asset"])
        if entries.get(native["asset"]) != native["sha256"]:
            raise SystemExit("Preview native archive manifest/checksum mismatch")
        required.update(item["asset"] for item in manifest["semantic_conformance"]["receipts"])
        if set(entries) != required:
            raise SystemExit("Preview checksum inventory does not cover the exact manifest assets")
        return not release.get("draft") and all((downloaded / name).is_file() for name in required)


def _resource(context: dict[str, Any]) -> dict[str, Any]:
    """Thin transport to the same native resource owner used by agent skills."""
    suffix = ".exe" if os.name == "nt" else ""
    native = os.environ.get("AGENTIC_WORKSPACE_CORE_BINARY") or str(ROOT / f"target/debug/agentic-workspace-core{suffix}")
    result = subprocess.run([native], input=json.dumps({"resources": context}), cwd=ROOT, text=True, capture_output=True)
    if result.returncode:
        raise SystemExit(f"Native resource owner unavailable or rejected the operation: {result.stderr or result.stdout}")
    return json.loads(result.stdout)


def _preview_isolation(tag: str, source_commit: str, policy_revision: str | None) -> dict[str, Any]:
    context = {
        "target": str(ROOT),
        "task": f"Prepare immutable preview {tag}",
        "request": {
            "operation": "worktree-create",
            "disposable_outputs": ["target", ".pytest_cache", ".venv"],
            "base": source_commit,
            "need": "destructive-validation",
            "reason": "Release normalization rewrites tracked versions while the reconstruction checkout must remain intact",
            "policy_revision": policy_revision,
            "policy_answer": "permits-isolation" if policy_revision else None,
        },
    }
    proposal = _resource(context)
    if "action" not in proposal:
        raise SystemExit(
            "Preview isolation requires current policy judgment; read the returned sources and pass their exact "
            "policy_revision with --isolation-policy-revision if they permit this concrete need:\n" + json.dumps(proposal)
        )
    result = _resource(proposal["action"])
    if result.get("effect_outcome") != "committed":
        raise SystemExit("Preview isolation was not created: " + json.dumps(result))
    return {**proposal["action"], "build_environment": result["build_environment"]}


def _finish_preview_isolation(context: dict[str, Any]) -> None:
    request = {"operation": "worktree-remove", "path": context["request"]["path"]}
    proposal = _resource({"target": context["target"], "task": context["task"], "changed": context["changed"], "request": request})
    if "action" not in proposal:
        raise SystemExit("Preview work preserved; reconcile the exact resource before teardown: " + json.dumps(proposal))
    result = _resource(proposal["action"])
    if result.get("effect_outcome") != "committed":
        raise SystemExit("Preview cleanup requires exact recovery: " + json.dumps(result))


def create_preview_subject(
    *,
    version: str,
    source_ref: str | None,
    remote: str,
    reconstruction_ref: str,
    push: bool,
    isolation_policy_revision: str | None = None,
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
            _git("push", remote, f"refs/tags/{tag}")
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
    isolation = _preview_isolation(tag, source_commit, isolation_policy_revision)
    worktree = Path(isolation["request"]["path"])
    environment = {**os.environ, **isolation["build_environment"]}
    tag_created = False
    try:
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
            environment=environment,
        )
        _run(["uv", "lock"], cwd=worktree, environment=environment)
        _run([sys.executable, "scripts/generate/generate_external_consumer_profile.py"], cwd=worktree, environment=environment)
        _run([sys.executable, "scripts/generate/generate_command_packages.py"], cwd=worktree, environment=environment)
        changed = _verify_release_only_paths(worktree, ownership)
        _git("diff", "--check", cwd=worktree, environment=environment)
        _git("add", "--", *changed, cwd=worktree, environment=environment)
        staged = _git("diff", "--cached", "--name-only", cwd=worktree, environment=environment).stdout.splitlines()
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
            environment=environment,
        )
        artifact_commit = _resolve_commit("HEAD", cwd=worktree)
        _git("tag", "-a", tag, artifact_commit, "-m", f"Preview {tag}", cwd=worktree, environment=environment)
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
                environment=environment,
            ).stdout
        )
        recovery = {}
        if push:
            _git("push", remote, f"refs/tags/{tag}")
            recovery = _recover_publisher(remote=remote, verified=verified)
        return {
            "kind": "agentic-workspace/preview-publication-subject/v1",
            "status": "created",
            **verified,
            **recovery,
            "release_only_paths": changed,
            "pushed": push,
        }
    except Exception:
        if tag_created and not push:
            _git("tag", "-d", tag, check=False)
        raise
    finally:
        _finish_preview_isolation(isolation)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Create an immutable release-only preview subject without modifying the reconstruction branch."
    )
    parser.add_argument(
        "--isolation-policy-revision", help="Exact current native resource policy read and judged to permit preview normalization isolation"
    )
    parser.add_argument("--version", help="Unused coordinated numeric package version, for example 0.52.0")
    parser.add_argument("--check-published", metavar="TAG")
    parser.add_argument("--admit-tag", metavar="TAG")
    parser.add_argument("--artifact-commit")
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
        help="Push only the immutable preview tag and dispatch the trusted reconstruction publisher; no branch is pushed.",
    )
    args = parser.parse_args(argv)

    if args.admit_tag:
        if not args.artifact_commit:
            parser.error("--admit-tag requires --artifact-commit")
        verified = admit_preview_subject(tag=args.admit_tag, artifact_commit=args.artifact_commit)
        print(f"tag={verified['tag']}")
        print(f"artifact_commit={verified['artifact_commit']}")
        return 0
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
        isolation_policy_revision=args.isolation_policy_revision,
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
