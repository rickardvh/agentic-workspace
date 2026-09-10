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
PREVIEW_TAG_PREFIX = "preview-v"


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
    path = ownership.get("release_notes_dir", ".release/releases")
    return ROOT / str(path)


def release_note_path(ownership: dict[str, Any], version: str) -> Path:
    return release_notes_dir(ownership) / f"v{version}.md"


def preview_metadata_dir(ownership: dict[str, Any]) -> Path:
    path = ownership.get("preview_metadata_dir", ".release/previews")
    return ROOT / str(path)


def parse_release_tag(tag: str) -> tuple[str, Version]:
    if tag.startswith(PREVIEW_TAG_PREFIX):
        version_text = tag.removeprefix(PREVIEW_TAG_PREFIX)
        release_class = "preview"
    elif tag.startswith("v"):
        version_text = tag.removeprefix("v")
        release_class = "stable"
    else:
        raise ValueError(f"Unsupported Agentic Workspace release tag {tag!r}")
    version = Version.parse(version_text)
    canonical = f"{PREVIEW_TAG_PREFIX if release_class == 'preview' else 'v'}{version}"
    if tag != canonical:
        raise ValueError(f"Release tag must be canonical, got {tag!r}; expected {canonical!r}")
    return release_class, version


def preview_release_note_path(ownership: dict[str, Any], tag: str) -> Path:
    release_class, _ = parse_release_tag(tag)
    if release_class != "preview":
        raise ValueError(f"Preview release tag required, got {tag!r}")
    return release_notes_dir(ownership) / f"{tag}.md"


def preview_metadata_path(ownership: dict[str, Any], tag: str) -> Path:
    release_class, _ = parse_release_tag(tag)
    if release_class != "preview":
        raise ValueError(f"Preview release tag required, got {tag!r}")
    return preview_metadata_dir(ownership) / f"{tag}.json"


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


def _tag_declares_coordinated_release_version(ownership: dict[str, Any], *, tag: str, version: Version) -> bool:
    target = _run(["git", "rev-list", "-n", "1", tag], check=False)
    if target.returncode != 0:
        return False
    commit = target.stdout.strip()
    if not commit:
        return False
    expected = str(version)
    owned_python_packages = {
        str(package.get("name") or "").strip() for package in ownership["packages"] if str(package.get("name") or "").strip()
    }
    for path in version_file_paths(ownership):
        result = _run(["git", "show", f"{commit}:{_repo_path(path)}"], check=False)
        if result.returncode != 0:
            return False
        try:
            if path.name == "package.json":
                declared = str(json.loads(result.stdout)["version"])
            else:
                payload = tomllib.loads(result.stdout)
                package_name = str(payload.get("project", {}).get("name") or "").strip()
                if owned_python_packages and package_name not in owned_python_packages:
                    return False
                declared = str(payload["project"]["version"])
        except (KeyError, json.JSONDecodeError, tomllib.TOMLDecodeError):
            return False
        if declared != expected:
            return False
    return True


def existing_release_versions(ownership: dict[str, Any]) -> list[Version]:
    result = _run(
        [
            "git",
            "tag",
            "--list",
            "v[0-9]*.[0-9]*.[0-9]*",
            "preview-v[0-9]*.[0-9]*.[0-9]*",
        ],
        check=False,
    )
    versions: list[Version] = []
    if result.returncode != 0:
        return versions
    for tag in result.stdout.splitlines():
        try:
            _, version = parse_release_tag(tag)
        except ValueError:
            continue
        if _tag_declares_coordinated_release_version(ownership, tag=tag, version=version):
            versions.append(version)
    return versions


def highest_bump(changesets: list[Changeset]) -> str:
    return sorted((changeset.bump for changeset in changesets), key=BUMP_ORDER.__getitem__)[-1]


def plan_release(ownership: dict[str, Any], *, include_git_tags: bool = True) -> dict[str, Any]:
    changesets = parse_changesets(ownership)
    package_versions = current_package_versions(ownership)
    tag_versions = existing_release_versions(ownership) if include_git_tags else []
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
            {"path": _repo_path(changeset.path), "bump": changeset.bump, "summary": changeset.summary} for changeset in changesets
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


def set_workspace_payload_release_identity(ownership: dict[str, Any], version: str, *, tag: str | None = None) -> None:
    Version.parse(version)
    release_tag = tag or f"v{version}"
    release_class, tag_version = parse_release_tag(release_tag)
    if str(tag_version) != version:
        raise SystemExit(f"Release tag {release_tag!r} does not match workspace version {version!r}")
    if release_class not in {"stable", "preview"}:
        raise AssertionError(release_class)
    workspace_package = next(
        (package for package in ownership["packages"] if package.get("name") == "agentic-workspace"),
        None,
    )
    if workspace_package is None:
        raise SystemExit("Release ownership must declare the agentic-workspace package")
    provenance_ref = str(workspace_package.get("payload_provenance") or "").strip()
    if not provenance_ref:
        raise SystemExit("Release ownership must declare the agentic-workspace payload_provenance path")
    provenance_path = ROOT / provenance_ref
    payload = json.loads(provenance_path.read_text(encoding="utf-8"))
    installed_by = payload.get("installed_by")
    release_identity = payload.get("release_identity")
    if not isinstance(installed_by, dict) or not isinstance(release_identity, dict):
        raise SystemExit(f"{_repo_path(provenance_path)} must declare installed_by and release_identity objects")
    installed_by["version"] = version
    release_identity["version"] = version
    release_identity["tag"] = release_tag
    provenance_path.write_text(json.dumps(payload, indent=2, sort_keys=False) + "\n", encoding="utf-8")


def write_release_note(ownership: dict[str, Any], *, version: str, changesets: list[Changeset]) -> Path:
    path = release_note_path(ownership, version)
    if path.exists():
        raise SystemExit(f"{_repo_path(path)} already exists; refusing to duplicate release-note summaries")
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [f"# Release v{version}", "", "## Changes", ""]
    lines.extend(f"- {changeset.summary}" for changeset in changesets)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def write_preview_release_note(ownership: dict[str, Any], *, tag: str, source_commit: str) -> Path:
    _, version = parse_release_tag(tag)
    path = preview_release_note_path(ownership, tag)
    if path.exists():
        raise SystemExit(f"{_repo_path(path)} already exists; refusing to replace preview release notes")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(
            [
                f"# Preview {tag}",
                "",
                "> Non-support-bearing preview for external testing. This is not a stable release or v1 admission.",
                "",
                f"- Package version: `{version}`",
                f"- Reconstruction source commit: `{source_commit}`",
                "- Stability/support: preview only; interfaces and behavior may change before first stable.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    return path


def write_preview_metadata(ownership: dict[str, Any], *, tag: str, source_commit: str) -> Path:
    _, version = parse_release_tag(tag)
    path = preview_metadata_path(ownership, tag)
    if path.exists():
        raise SystemExit(f"{_repo_path(path)} already exists; refusing to replace preview identity")
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "kind": "agentic-workspace/coordinated-preview-subject/v1",
        "release_class": "preview",
        "support_bearing": False,
        "tag": tag,
        "version": str(version),
        "reconstruction_source_commit": source_commit,
    }
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def prepare_release(ownership: dict[str, Any]) -> dict[str, Any]:
    plan = plan_release(ownership)
    if not plan["release_required"]:
        return plan
    version = str(plan["version"])
    changesets = parse_changesets(ownership)
    set_workspace_version(ownership, version)
    set_workspace_payload_release_identity(ownership, version)
    note_path = write_release_note(ownership, version=version, changesets=changesets)
    for changeset in changesets:
        changeset.path.unlink()
    plan["release_note"] = _repo_path(note_path)
    return plan


def prepare_preview_release(ownership: dict[str, Any], *, tag: str, source_commit: str) -> dict[str, Any]:
    release_class, version = parse_release_tag(tag)
    if release_class != "preview":
        raise SystemExit(f"Preview preparation requires a {PREVIEW_TAG_PREFIX}MAJOR.MINOR.PATCH tag")
    actual_source = _run(["git", "rev-parse", "HEAD"]).stdout.strip()
    if actual_source != source_commit:
        raise SystemExit(f"Preview source checkout is {actual_source}, expected {source_commit}")

    existing_versions = existing_release_versions(ownership)
    current_versions = current_package_versions(ownership)
    public_floor = max([*current_versions, *existing_versions])
    if version <= public_floor:
        raise SystemExit(f"Preview version {version} must be greater than public/package version floor {public_floor}")

    pending_changesets = [_repo_path(changeset.path) for changeset in parse_changesets(ownership)]
    set_workspace_version(ownership, str(version))
    set_workspace_payload_release_identity(ownership, str(version), tag=tag)
    note_path = write_preview_release_note(ownership, tag=tag, source_commit=source_commit)
    metadata_path = write_preview_metadata(ownership, tag=tag, source_commit=source_commit)
    return {
        "kind": "agentic-workspace/coordinated-preview-prepare/v1",
        "release_class": "preview",
        "support_bearing": False,
        "version": str(version),
        "tag": tag,
        "reconstruction_source_commit": source_commit,
        "release_note": _repo_path(note_path),
        "preview_metadata": _repo_path(metadata_path),
        "preserved_changesets": pending_changesets,
    }


def _workspace_payload_release_identity(ownership: dict[str, Any]) -> dict[str, Any]:
    workspace_package = next(
        (package for package in ownership["packages"] if package.get("name") == "agentic-workspace"),
        None,
    )
    if workspace_package is None:
        raise SystemExit("Release ownership must declare the agentic-workspace package")
    provenance_path = ROOT / str(workspace_package["payload_provenance"])
    payload = json.loads(provenance_path.read_text(encoding="utf-8"))
    release_identity = payload.get("release_identity")
    if not isinstance(release_identity, dict):
        raise SystemExit(f"{_repo_path(provenance_path)} must declare release_identity")
    return release_identity


def verify_preview_release(ownership: dict[str, Any], *, tag: str, source_commit: str | None = None) -> dict[str, Any]:
    release_class, version = parse_release_tag(tag)
    if release_class != "preview":
        raise SystemExit(f"Preview verification requires a {PREVIEW_TAG_PREFIX}MAJOR.MINOR.PATCH tag")
    workspace_version = current_workspace_version(ownership)
    if workspace_version != str(version):
        raise SystemExit(f"Preview tag {tag!r} requires workspace version {version}, got {workspace_version}")

    metadata_path = preview_metadata_path(ownership, tag)
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    expected_source = source_commit or str(metadata.get("reconstruction_source_commit") or "")
    expected_metadata = {
        "kind": "agentic-workspace/coordinated-preview-subject/v1",
        "release_class": "preview",
        "support_bearing": False,
        "tag": tag,
        "version": str(version),
        "reconstruction_source_commit": expected_source,
    }
    if metadata != expected_metadata:
        raise SystemExit(f"Preview metadata mismatch at {_repo_path(metadata_path)}")
    if not expected_source:
        raise SystemExit("Preview metadata must identify the reconstruction source commit")

    release_identity = _workspace_payload_release_identity(ownership)
    if release_identity.get("version") != str(version) or release_identity.get("tag") != tag:
        raise SystemExit("Workspace payload release identity does not match preview tag/version")

    artifact_commit = _run(["git", "rev-parse", "HEAD"]).stdout.strip()
    parents = _run(["git", "rev-list", "--parents", "-n", "1", artifact_commit]).stdout.strip().split()
    if len(parents) != 2 or parents[1] != expected_source:
        raise SystemExit(
            f"Preview artifact commit {artifact_commit} must have exactly reconstruction source {expected_source} as its parent"
        )
    tag_target = _run(["git", "rev-list", "-n", "1", tag], check=False)
    if tag_target.returncode != 0 or tag_target.stdout.strip() != artifact_commit:
        raise SystemExit(f"Preview tag {tag} must resolve to exact artifact commit {artifact_commit}")
    note_path = preview_release_note_path(ownership, tag)
    if not note_path.is_file() or expected_source not in note_path.read_text(encoding="utf-8"):
        raise SystemExit(f"Preview release note {_repo_path(note_path)} must identify reconstruction source {expected_source}")

    return {
        "kind": "agentic-workspace/coordinated-preview-verification/v1",
        "release_class": "preview",
        "support_bearing": False,
        "version": str(version),
        "tag": tag,
        "reconstruction_source_commit": expected_source,
        "artifact_commit": artifact_commit,
        "package_count": len(current_package_versions(ownership)),
        "release_note": _repo_path(note_path),
        "preview_metadata": _repo_path(metadata_path),
    }


def verify_workspace_versions(ownership: dict[str, Any], *, tag: str | None = None) -> dict[str, Any]:
    versions = current_package_versions(ownership)
    version = current_workspace_version(ownership)
    if tag and tag != f"v{version}":
        raise SystemExit(f"Release tag {tag!r} must match workspace version {version!r}")
    release_versions = existing_release_versions(ownership)
    target = Version.parse(version)
    higher_or_equal = [release_version for release_version in release_versions if release_version >= target]
    if tag is None and higher_or_equal:
        raise SystemExit(
            f"Workspace release version {version} must be greater than existing AW public release tags; "
            f"highest existing AW release tag version is {max(release_versions)}"
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
    result = _run(["git", "log", "--first-parent", "-n", "1", "--format=%H", "--", *relative_paths])
    commit = result.stdout.strip()
    if not commit:
        raise SystemExit("Could not find a release commit that touched coordinated version files")
    mismatches = [_repo_path(path) for path in version_file_paths(ownership) if _version_text_from_commit(commit, path) != version]
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
    release_versions = existing_release_versions(ownership)
    if existing.returncode != 0 and release_versions and target <= max(release_versions):
        return {
            "kind": "agentic-workspace/coordinated-release-tag-plan/v1",
            "tag_needed": False,
            "publish_candidate": False,
            "reason": f"version-not-newer-than-existing-tag-floor-{max(release_versions)}",
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
    if (
        _commit_exists("origin/master")
        and _run(
            ["git", "merge-base", "--is-ancestor", release_commit, "origin/master"],
            check=False,
        ).returncode
        != 0
    ):
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

    preview_prepare_parser = subparsers.add_parser("prepare-preview")
    preview_prepare_parser.add_argument("--tag", required=True)
    preview_prepare_parser.add_argument("--source-commit", required=True)

    preview_verify_parser = subparsers.add_parser("verify-preview")
    preview_verify_parser.add_argument("--tag", required=True)
    preview_verify_parser.add_argument("--source-commit")

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
    if args.command == "prepare-preview":
        print(
            json.dumps(
                prepare_preview_release(ownership, tag=args.tag, source_commit=args.source_commit),
                indent=2,
                sort_keys=True,
            )
        )
        return 0
    if args.command == "verify-preview":
        print(
            json.dumps(
                verify_preview_release(ownership, tag=args.tag, source_commit=args.source_commit),
                indent=2,
                sort_keys=True,
            )
        )
        return 0
    raise AssertionError(args.command)


if __name__ == "__main__":
    raise SystemExit(main())
