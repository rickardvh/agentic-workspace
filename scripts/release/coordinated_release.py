from __future__ import annotations

import argparse
import json
import re
import subprocess
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
OWNERSHIP_PATH = ROOT / ".github" / "release-ownership.json"
CHANGESET_SCHEMA = "agentic-workspace/release-change/v1"
BUMP_ORDER = {"patch": 0, "minor": 1, "major": 2}


@dataclass(frozen=True, order=True)
class Version:
    major: int
    minor: int
    patch: int

    @classmethod
    def parse(cls, text: str) -> "Version":
        parts = text.split(".")
        if len(parts) != 3:
            raise ValueError(f"Version must be MAJOR.MINOR.PATCH, got {text!r}")
        try:
            major, minor, patch = (int(part) for part in parts)
        except ValueError as exc:
            raise ValueError(f"Version must be numeric semver, got {text!r}") from exc
        return cls(major, minor, patch)

    def bump(self, bump: str) -> "Version":
        if bump == "major":
            return Version(self.major + 1, 0, 0)
        if bump == "minor":
            return Version(self.major, self.minor + 1, 0)
        if bump == "patch":
            return Version(self.major, self.minor, self.patch + 1)
        raise ValueError(f"Unsupported release bump {bump!r}")

    def __str__(self) -> str:
        return f"{self.major}.{self.minor}.{self.patch}"


@dataclass(frozen=True)
class Changeset:
    path: Path
    bump: str
    summary: str


def _repo_path(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def _run(args: list[str], *, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, cwd=ROOT, check=check, capture_output=True, text=True)


def load_ownership() -> dict[str, Any]:
    return json.loads(OWNERSHIP_PATH.read_text(encoding="utf-8"))


def changeset_dir(ownership: dict[str, Any]) -> Path:
    path = ownership.get("changeset_dir", ".release/changes")
    return ROOT / str(path)


def package_pyprojects(ownership: dict[str, Any]) -> list[Path]:
    return [ROOT / package["pyproject"] for package in ownership["packages"]]


def typescript_package_jsons(ownership: dict[str, Any]) -> list[Path]:
    return [ROOT / package["package_json"] for package in ownership["typescript_packages"]]


def version_file_paths(ownership: dict[str, Any]) -> list[Path]:
    return [*package_pyprojects(ownership), *typescript_package_jsons(ownership)]


def release_notes_dir(ownership: dict[str, Any]) -> Path:
    return ROOT / str(ownership.get("release_notes_dir", ".release/releases"))


def release_note_path(ownership: dict[str, Any], version: str) -> Path:
    return release_notes_dir(ownership) / f"v{version}.md"


def parse_changesets(ownership: dict[str, Any]) -> list[Changeset]:
    directory = changeset_dir(ownership)
    if not directory.exists():
        return []
    changesets: list[Changeset] = []
    for path in sorted(directory.glob("*.toml")):
        payload = tomllib.loads(path.read_text(encoding="utf-8"))
        if payload.get("schema_version") != CHANGESET_SCHEMA:
            raise SystemExit(f"{_repo_path(path)} must set schema_version = {CHANGESET_SCHEMA!r}")
        bump = payload.get("bump")
        if bump not in BUMP_ORDER:
            raise SystemExit(f"{_repo_path(path)} must set bump to one of: major, minor, patch")
        summary = str(payload.get("summary", "")).strip()
        if not summary:
            raise SystemExit(f"{_repo_path(path)} must set a non-empty summary")
        changesets.append(Changeset(path=path, bump=str(bump), summary=summary))
    return changesets


def current_package_versions(ownership: dict[str, Any]) -> list[Version]:
    versions: list[Version] = []
    for path in package_pyprojects(ownership):
        declared = tomllib.loads(path.read_text(encoding="utf-8"))["project"]["version"]
        versions.append(Version.parse(declared))
    for path in typescript_package_jsons(ownership):
        declared = json.loads(path.read_text(encoding="utf-8"))["version"]
        versions.append(Version.parse(declared))
    return versions


def current_workspace_version(ownership: dict[str, Any]) -> str:
    version_texts = sorted({str(version) for version in current_package_versions(ownership)})
    if len(version_texts) != 1:
        raise SystemExit(f"All release package manifests must use one version, got {version_texts}")
    return version_texts[0]


def existing_release_versions() -> list[Version]:
    result = _run(["git", "tag", "--list", "v[0-9]*.[0-9]*.[0-9]*"], check=False)
    versions: list[Version] = []
    if result.returncode != 0:
        return versions
    for tag in result.stdout.splitlines():
        try:
            versions.append(Version.parse(tag.removeprefix("v")))
        except ValueError:
            continue
    return versions


def highest_bump(changesets: list[Changeset]) -> str:
    return sorted((changeset.bump for changeset in changesets), key=BUMP_ORDER.__getitem__)[-1]


def plan_release(ownership: dict[str, Any], *, include_git_tags: bool = True) -> dict[str, Any]:
    changesets = parse_changesets(ownership)
    package_versions = current_package_versions(ownership)
    tag_versions = existing_release_versions() if include_git_tags else []
    floor = max([*package_versions, *tag_versions])

    if not changesets:
        return {
            "kind": "agentic-workspace/coordinated-release-plan/v1",
            "release_required": False,
            "current_floor": str(floor),
            "package_versions": sorted({str(version) for version in package_versions}),
            "existing_release_floor": str(max(tag_versions)) if tag_versions else "",
            "changesets": [],
        }

    bump = highest_bump(changesets)
    version = floor.bump(bump)
    return {
        "kind": "agentic-workspace/coordinated-release-plan/v1",
        "release_required": True,
        "bump": bump,
        "version": str(version),
        "tag": f"v{version}",
        "current_floor": str(floor),
        "package_versions": sorted({str(version) for version in package_versions}),
        "existing_release_floor": str(max(tag_versions)) if tag_versions else "",
        "changesets": [
            {"path": _repo_path(changeset.path), "bump": changeset.bump, "summary": changeset.summary}
            for changeset in changesets
        ],
    }


def set_workspace_version(ownership: dict[str, Any], version: str) -> None:
    Version.parse(version)
    for path in package_pyprojects(ownership):
        text = path.read_text(encoding="utf-8")
        updated = re.sub(r'^version = "[^"]+"$', f'version = "{version}"', text, count=1, flags=re.MULTILINE)
        if updated == text:
            raise SystemExit(f"{_repo_path(path)} does not contain a project version assignment")
        path.write_text(updated, encoding="utf-8")
    for path in typescript_package_jsons(ownership):
        payload = json.loads(path.read_text(encoding="utf-8"))
        payload["version"] = version
        path.write_text(json.dumps(payload, indent=2, sort_keys=False) + "\n", encoding="utf-8")


def write_release_note(ownership: dict[str, Any], *, version: str, changesets: list[Changeset]) -> Path:
    path = release_note_path(ownership, version)
    if path.exists():
        raise SystemExit(f"{_repo_path(path)} already exists; refusing to duplicate release-note summaries")
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [f"# Release v{version}", "", "## Changes", ""]
    lines.extend(f"- {changeset.summary}" for changeset in changesets)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def prepare_release(ownership: dict[str, Any]) -> dict[str, Any]:
    plan = plan_release(ownership)
    if not plan["release_required"]:
        return plan
    version = str(plan["version"])
    changesets = parse_changesets(ownership)
    set_workspace_version(ownership, version)
    note_path = write_release_note(ownership, version=version, changesets=changesets)
    for changeset in changesets:
        changeset.path.unlink()
    plan["release_note"] = _repo_path(note_path)
    return plan


def verify_workspace_versions(ownership: dict[str, Any], *, tag: str | None = None) -> dict[str, Any]:
    versions = current_package_versions(ownership)
    version = current_workspace_version(ownership)
    if tag and tag != f"v{version}":
        raise SystemExit(f"Release tag {tag!r} must match workspace version {version!r}")
    release_versions = existing_release_versions()
    target = Version.parse(version)
    higher_or_equal = [release_version for release_version in release_versions if release_version >= target]
    if tag is None and higher_or_equal:
        raise SystemExit(
            f"Workspace release version {version} must be greater than existing tags; "
            f"highest existing tag is v{max(release_versions)}"
        )
    return {
        "kind": "agentic-workspace/coordinated-release-verification/v1",
        "version": version,
        "tag": f"v{version}",
        "package_count": len(versions),
    }


def _tag_target(tag: str) -> str:
    return _run(["git", "rev-list", "-n", "1", tag]).stdout.strip()


def _commit_exists(ref: str) -> bool:
    return _run(["git", "cat-file", "-e", f"{ref}^{{commit}}"], check=False).returncode == 0


def _commit_file_text(commit: str, path: Path) -> str:
    return _run(["git", "show", f"{commit}:{_repo_path(path)}"]).stdout


def _version_text_from_commit(commit: str, path: Path) -> str:
    text = _commit_file_text(commit, path)
    if path.name == "package.json":
        return str(json.loads(text)["version"])
    return str(tomllib.loads(text)["project"]["version"])


def _release_commit_for_version(ownership: dict[str, Any], version: str) -> str:
    relative_paths = [_repo_path(path) for path in version_file_paths(ownership)]
    result = _run(["git", "log", "-n", "1", "--format=%H", "--", *relative_paths])
    commit = result.stdout.strip()
    if not commit:
        raise SystemExit("Could not find a release commit that touched coordinated version files")
    mismatches = [
        _repo_path(path)
        for path in version_file_paths(ownership)
        if _version_text_from_commit(commit, path) != version
    ]
    if mismatches:
        raise SystemExit(f"Release commit {commit} does not declare {version} in {mismatches}")
    note_path = release_note_path(ownership, version)
    if _run(["git", "cat-file", "-e", f"{commit}:{_repo_path(note_path)}"], check=False).returncode != 0:
        raise SystemExit(f"Release commit {commit} must include {_repo_path(note_path)}")
    return commit


def pending_tag_plan(ownership: dict[str, Any]) -> dict[str, Any]:
    if parse_changesets(ownership):
        return {
            "kind": "agentic-workspace/coordinated-release-tag-plan/v1",
            "tag_needed": False,
            "publish_candidate": False,
            "reason": "pending-changesets-require-release-pr",
        }
    version = current_workspace_version(ownership)
    target = Version.parse(version)
    tag = f"v{version}"
    existing = _run(["git", "rev-parse", "--verify", "--quiet", f"refs/tags/{tag}"], check=False)
    release_versions = existing_release_versions()
    if existing.returncode != 0 and release_versions and target <= max(release_versions):
        return {
            "kind": "agentic-workspace/coordinated-release-tag-plan/v1",
            "tag_needed": False,
            "publish_candidate": False,
            "reason": f"version-not-newer-than-existing-tag-floor-v{max(release_versions)}",
            "version": version,
            "tag": tag,
        }
    release_commit = _release_commit_for_version(ownership, version)
    if existing.returncode == 0:
        tag_target = _tag_target(tag)
        if tag_target != release_commit:
            raise SystemExit(f"Release tag {tag} already exists at {tag_target}, not release commit {release_commit}")
        return {
            "kind": "agentic-workspace/coordinated-release-tag-plan/v1",
            "tag_needed": False,
            "publish_candidate": True,
            "reason": "tag-already-points-at-release-commit",
            "version": version,
            "tag": tag,
            "release_commit": release_commit,
            "release_note": _repo_path(release_note_path(ownership, version)),
        }
    if _commit_exists("origin/master") and _run(
        ["git", "merge-base", "--is-ancestor", release_commit, "origin/master"],
        check=False,
    ).returncode != 0:
        raise SystemExit(f"Release commit {release_commit} is not reachable from origin/master")
    return {
        "kind": "agentic-workspace/coordinated-release-tag-plan/v1",
        "tag_needed": True,
        "publish_candidate": True,
        "version": version,
        "tag": tag,
        "release_commit": release_commit,
        "release_note": _repo_path(release_note_path(ownership, version)),
    }


def write_github_output(plan: dict[str, Any], output_path: Path) -> None:
    lines = [
        f"release_required={str(plan.get('release_required', False)).lower()}",
        f"version={plan.get('version', '')}",
        f"tag={plan.get('tag', '')}",
        f"bump={plan.get('bump', '')}",
    ]
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_tag_github_output(plan: dict[str, Any], output_path: Path) -> None:
    lines = [
        f"tag_needed={str(plan.get('tag_needed', False)).lower()}",
        f"publish_candidate={str(plan.get('publish_candidate', False)).lower()}",
        f"version={plan.get('version', '')}",
        f"tag={plan.get('tag', '')}",
        f"release_commit={plan.get('release_commit', '')}",
        f"reason={plan.get('reason', '')}",
    ]
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    plan_parser = subparsers.add_parser("plan")
    plan_parser.add_argument("--github-output", type=Path)
    plan_parser.add_argument("--ignore-git-tags", action="store_true")

    subparsers.add_parser("prepare")

    verify_parser = subparsers.add_parser("verify")
    verify_parser.add_argument("--tag")

    tag_parser = subparsers.add_parser("tag-plan")
    tag_parser.add_argument("--github-output", type=Path)

    args = parser.parse_args(argv)
    ownership = load_ownership()

    if args.command == "plan":
        plan = plan_release(ownership, include_git_tags=not args.ignore_git_tags)
        if args.github_output:
            write_github_output(plan, args.github_output)
        print(json.dumps(plan, indent=2, sort_keys=True))
        return 0
    if args.command == "prepare":
        print(json.dumps(prepare_release(ownership), indent=2, sort_keys=True))
        return 0
    if args.command == "verify":
        print(json.dumps(verify_workspace_versions(ownership, tag=args.tag), indent=2, sort_keys=True))
        return 0
    if args.command == "tag-plan":
        tag_plan = pending_tag_plan(ownership)
        if args.github_output:
            write_tag_github_output(tag_plan, args.github_output)
        print(json.dumps(tag_plan, indent=2, sort_keys=True))
        return 0
    raise AssertionError(args.command)


if __name__ == "__main__":
    raise SystemExit(main())
