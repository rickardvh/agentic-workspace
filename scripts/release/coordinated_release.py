from __future__ import annotations

import argparse
import hashlib
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
    return subprocess.run(args, cwd=ROOT, check=check, capture_output=True, text=True, encoding="utf-8")


def load_ownership() -> dict[str, Any]:
    return json.loads(OWNERSHIP_PATH.read_text(encoding="utf-8"))


def changeset_dir(ownership: dict[str, Any]) -> Path:
    path = ownership.get("changeset_dir", ".release/changes")
    return ROOT / str(path)


def package_pyprojects(ownership: dict[str, Any]) -> list[Path]:
    return [ROOT / package["pyproject"] for package in ownership["packages"]]


def typescript_package_jsons(ownership: dict[str, Any]) -> list[Path]:
    return [ROOT / package["package_json"] for package in ownership["typescript_packages"]]


def cargo_manifests(ownership: dict[str, Any]) -> list[Path]:
    return [ROOT / package["path"] / "Cargo.toml" for package in ownership.get("cargo_packages", [])]


def cargo_lockfiles(ownership: dict[str, Any]) -> list[Path]:
    return [ROOT / path for path in ownership.get("cargo_lockfiles", ["Cargo.lock"])] if ownership.get("cargo_packages") else []


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
    if re.fullmatch(r"v1\.0\.0-rc\.[1-9][0-9]*", tag):
        return "release-candidate", Version(1, 0, 0)
    if tag.startswith(PREVIEW_TAG_PREFIX):
        version_text = tag.removeprefix(PREVIEW_TAG_PREFIX)
        release_class = "preview"
    elif tag.startswith("v"):
        version_text = tag.removeprefix("v")
        release_class = "stable"
    else:
        raise ValueError(f"Unsupported Agentic Workspace release tag {tag!r}")
    version = Version.parse(version_text)
    if min(version.major, version.minor, version.patch) < 0:
        raise ValueError(f"Negative release version: {tag!r}")
    canonical = f"{PREVIEW_TAG_PREFIX if release_class == 'preview' else 'v'}{version}"
    if tag != canonical:
        raise ValueError(f"Release tag must be canonical, got {tag!r}; expected {canonical!r}")
    return release_class, version


def release_identity(tag: str) -> dict[str, Any]:
    release_class, version = parse_release_tag(tag)
    if release_class == "release-candidate":
        number = int(tag.rsplit(".", 1)[1])
        return {
            "release_class": release_class,
            "support_bearing": False,
            "tag": tag,
            "version": f"1.0.0rc{number}",
            "target_stable_tag": "v1.0.0",
            "package_versions": {"python": f"1.0.0rc{number}", "npm": f"1.0.0-rc.{number}", "cargo": f"1.0.0-rc.{number}"},
        }
    return {
        "release_class": release_class,
        "support_bearing": release_class == "stable",
        "tag": tag,
        "version": str(version),
        **(
            {"package_versions": {ecosystem: str(version) for ecosystem in ("python", "npm", "cargo")}} if release_class == "stable" else {}
        ),
    }


def npm_version(python_version: str) -> str:
    match = re.fullmatch(r"1\.0\.0rc([1-9][0-9]*)", python_version)
    if match:
        return f"1.0.0-rc.{match[1]}"
    version = Version.parse(python_version)
    if str(version) != python_version or min(version.major, version.minor, version.patch) < 0:
        raise ValueError(f"Noncanonical package version: {python_version!r}")
    return python_version


def validate_next_rc(ownership: dict[str, Any], *, tag: str, source_commit: str) -> None:
    """Reserve contiguous names; existing tags are handled by immutable recovery."""
    number = int(tag.rsplit(".", 1)[1])
    tags = _run(["git", "tag", "--list", "v1.0.0*"], check=False).stdout.splitlines()
    if "v1.0.0" in tags:
        raise SystemExit("v1.0.0 already exists; the first-stable RC lane is closed")
    prior = []
    for existing in tags:
        if re.fullmatch(r"v1\.0\.0-rc\.[1-9][0-9]*", existing):
            prior.append(int(existing.rsplit(".", 1)[1]))
    if number != max(prior, default=0) + 1:
        raise SystemExit("RC progression must be contiguous; retry the existing immutable tag for recovery")
    if prior:
        previous = verify_preview_release(ownership, tag=f"v1.0.0-rc.{max(prior)}", artifact_commit=_tag_target(f"v1.0.0-rc.{max(prior)}"))
        old_source = previous["reconstruction_source_commit"]
        if old_source == source_commit or _run(["git", "diff", "--quiet", old_source, source_commit], check=False).returncode == 0:
            raise SystemExit("A new RC requires a new candidate source; recover the prior RC instead")
        if _run(["git", "merge-base", "--is-ancestor", old_source, source_commit], check=False).returncode:
            raise SystemExit("A new RC must continue the prior candidate source")


PROMOTION_RECORD = ".release/promotions/v1.0.0.json"


def _proof_reconciliation(verified: dict[str, Any], preparation_source: str) -> dict[str, str] | None:
    """Consume source-owned, exact-commit admission; never infer acceptance from paths."""
    source = verified["reconstruction_source_commit"]
    if preparation_source == source:
        return None
    path = f".release/proof-reconciliations/{verified['tag']}.json"
    if not (ROOT / path).is_file():
        raise SystemExit("Post-RC source requires an explicit proof reconciliation admission")
    raw = (ROOT / path).read_text(encoding="utf-8").encode("utf-8")
    admission = json.loads(raw)
    keys = {
        "kind",
        "rc_tag",
        "rc_artifact_commit",
        "product_source_commit",
        "reconciliation_commit",
        "release_tooling_commit",
        "reconciliation_paths",
        "release_tooling_paths",
        "acceptance_reference",
    }
    if set(admission) != keys or admission["kind"] != "agentic-workspace/rc-proof-reconciliation/v1":
        raise SystemExit("Invalid proof reconciliation admission")
    if (
        admission["rc_tag"] != verified["tag"]
        or admission["rc_artifact_commit"] != verified["artifact_commit"]
        or admission["product_source_commit"] != source
        or not isinstance(admission["acceptance_reference"], str)
        or not admission["acceptance_reference"].strip()
    ):
        raise SystemExit("Proof reconciliation does not bind the exact accepted RC")
    proof = admission["reconciliation_commit"]
    tooling = admission["release_tooling_commit"]
    for commit in (source, proof, tooling, preparation_source):
        if not isinstance(commit, str) or not re.fullmatch(r"[0-9a-f]{40}", commit):
            raise SystemExit("Proof reconciliation requires full immutable commit identities")
        if _run(["git", "rev-parse", f"{commit}^{{commit}}"], check=False).stdout.strip() != commit:
            raise SystemExit("Proof reconciliation commit is unavailable")
    tooling_paths = {
        "scripts/release/coordinated_release.py",
        "tests/test_release_candidate.py",
        "docs/release-and-versioning.md",
    }
    for before, after, field in (
        (source, proof, "reconciliation_paths"),
        (proof, tooling, "release_tooling_paths"),
    ):
        if _run(["git", "merge-base", "--is-ancestor", before, after], check=False).returncode:
            raise SystemExit("Proof reconciliation ancestry mismatch")
        declared = admission[field]
        changed = _run(["git", "diff", "--name-only", "--no-renames", before, after]).stdout.splitlines()
        if not isinstance(declared, list) or not declared or declared != sorted(set(changed)):
            raise SystemExit("Proof reconciliation delta does not match its finite admitted path set")
        for changed_path in declared:
            changeset = re.fullmatch(r"\.release/changes/[a-zA-Z0-9_-]+\.toml", changed_path)
            proof_path = (
                changed_path == "Makefile"
                or re.fullmatch(r"docs/reference/[a-zA-Z0-9_-]+\.md", changed_path)
                or re.fullmatch(r"(?:packages/(?:memory|planning|verification)/)?tests/test_[a-zA-Z0-9_]+\.py", changed_path)
                or changed_path == "packages/planning/scripts/check/check_planning_surfaces.py"
            )
            if not (changeset or (proof_path if field == "reconciliation_paths" else changed_path in tooling_paths)):
                raise SystemExit(f"Product path cannot be admitted as proof reconciliation: {changed_path}")
            for commit in (before, after):
                entry = _run(["git", "ls-tree", commit, "--", changed_path]).stdout
                if entry and not entry.startswith("100644 blob "):
                    raise SystemExit(f"Proof reconciliation changed file custody/mode: {changed_path}")
    if _run(["git", "merge-base", "--is-ancestor", tooling, preparation_source], check=False).returncode:
        raise SystemExit("Preparation source does not descend from admitted release tooling")
    # The admission is committed AFTER the revisions it pins. This avoids a self-hash
    # and accepts a merge of that exact tree, but no intervening maintenance/product edit.
    delta = _run(["git", "diff", "--name-status", "--no-renames", tooling, preparation_source]).stdout.strip()
    if delta != f"A\t{path}":
        raise SystemExit("Unadmitted post-RC source drift after pinned release tooling")
    entry = _run(["git", "ls-tree", preparation_source, "--", path]).stdout
    committed = _run(["git", "show", f"{preparation_source}:{path}"]).stdout
    if not entry.startswith("100644 blob ") or committed != raw.decode("utf-8"):
        raise SystemExit("Preparation admission differs from the current release owner's admission")
    return {
        "preparation_source_commit": preparation_source,
        "reconciliation_commit": proof,
        "release_tooling_commit": tooling,
        "admission_path": path,
        "admission_sha256": hashlib.sha256(raw).hexdigest(),
    }


def verify_normalization_delta(
    ownership: dict[str, Any], *, source: str, subject: str, version: str, metadata_paths: set[str]
) -> list[str]:
    """Check values as well as paths; lock changes cannot alter third-party resolution."""
    changed = _run(["git", "diff", "--name-only", "--no-renames", source, subject]).stdout.splitlines()
    pyprojects = {str(p["pyproject"]) for p in ownership["packages"]}
    node_projects = {str(p["package_json"]) for p in ownership["typescript_packages"]}
    cargo_projects = {_repo_path(path) for path in cargo_manifests(ownership)}
    cargo_names = {p["name"] for p in ownership.get("cargo_packages", [])}
    provenance = {str(p["payload_provenance"]) for p in ownership["packages"] if p.get("payload_provenance")}
    names = {str(p["name"]) for p in ownership["packages"]}
    for path in changed:
        # Git file modes are product semantics too, even when parsed content agrees.
        before_mode = _run(["git", "ls-tree", source, "--", path]).stdout.split(" ", 1)[0]
        after_mode = _run(["git", "ls-tree", subject, "--", path]).stdout.split(" ", 1)[0]
        if version == "1.0.0" and path.startswith(".release/changes/") and path.endswith(".toml") and not after_mode:
            old = tomllib.loads(_run(["git", "show", f"{source}:{path}"]).stdout)
            if before_mode != "100644" or old.get("schema_version") != CHANGESET_SCHEMA:
                raise SystemExit(f"Invalid consumed release changeset: {path}")
            continue
        if path in metadata_paths:
            if before_mode or after_mode != "100644":
                raise SystemExit(f"Release metadata must be a new regular file: {path}")
            continue
        if before_mode != "100644" or after_mode != "100644":
            raise SystemExit(f"Release normalization changed file custody/mode: {path}")
        before_text = _run(["git", "show", f"{source}:{path}"]).stdout
        after_text = _run(["git", "show", f"{subject}:{path}"]).stdout
        if path in pyprojects:
            before, after = tomllib.loads(before_text), tomllib.loads(after_text)
            before["project"]["version"] = version
        elif path in node_projects:
            before, after = json.loads(before_text), json.loads(after_text)
            before["version"] = npm_version(version)
        elif path in cargo_projects:
            before, after = tomllib.loads(before_text), tomllib.loads(after_text)
            before["package"]["version"] = npm_version(version)
        elif path in {_repo_path(lock) for lock in cargo_lockfiles(ownership)}:
            before, after = tomllib.loads(before_text), tomllib.loads(after_text)
            for package in before.get("package", []):
                if package.get("name") in cargo_names and "source" not in package:
                    package["version"] = npm_version(version)
        elif path in provenance:
            before, after = normalized_payload_provenance(json.loads(before_text), version), json.loads(after_text)
        elif path == "uv.lock":
            before, after = tomllib.loads(before_text), tomllib.loads(after_text)
            for package in before.get("package", []):
                if package.get("name") in names and package.get("source", {}).get("editable") is not None:
                    package["version"] = version
        elif path in {f"generated/workspace/{lang}/external_contract_bundle.json" for lang in ("python", "typescript")}:
            before, after = json.loads(before_text), json.loads(after_text)
            before["versions"]["client_package"] = version
            before["versions"]["python_package"]["version"] = version
            before["versions"]["typescript_package"]["version"] = npm_version(version)
        elif path in {
            f"generated/{owner}/.agentic-workspace-cli-fingerprint.json" for owner in ("workspace", "memory", "planning", "verification")
        }:
            before, after = json.loads(before_text), json.loads(after_text)
            if not re.fullmatch(r"[0-9a-f]{64}", str(after.get("fingerprint", ""))):
                raise SystemExit(f"Invalid regenerated fingerprint: {path}")
            before["fingerprint"] = after["fingerprint"]
        else:
            raise SystemExit(f"Product-semantic delta is not release normalization: {path}")
        if before != after:
            raise SystemExit(f"Non-version release normalization delta: {path}")
    return changed


def prepare_rc_promotion(ownership: dict[str, Any], *, rc_tag: str) -> dict[str, Any]:
    if parse_release_tag(rc_tag)[0] != "release-candidate":
        raise SystemExit("Stable promotion requires a canonical RC")
    verified = verify_preview_release(ownership, tag=rc_tag, artifact_commit=_tag_target(rc_tag))
    source = verified["reconstruction_source_commit"]
    preparation_source = _run(["git", "rev-parse", "HEAD"]).stdout.strip()
    reconciliation = _proof_reconciliation(verified, preparation_source)
    if _run(["git", "status", "--porcelain"]).stdout.strip():
        raise SystemExit("Prepare promotion from a clean admitted source checkout")
    if _run(["git", "show-ref", "--verify", "--quiet", "refs/tags/v1.0.0"], check=False).returncode == 0:
        raise SystemExit("Stable v1.0.0 already exists; use its existing publication recovery")
    record = {
        "kind": "agentic-workspace/rc-stable-promotion/v1",
        "rc_tag": rc_tag,
        "rc_artifact_commit": verified["artifact_commit"],
        "source_commit": source,
        "stable_tag": "v1.0.0",
        "rc_package_versions": release_identity(rc_tag)["package_versions"],
    }
    if reconciliation:
        record["proof_reconciliation"] = reconciliation
    path = ROOT / PROMOTION_RECORD
    if path.exists():
        raise SystemExit("Refusing to replace an existing promotion record")
    set_workspace_version(ownership, "1.0.0")
    set_workspace_payload_release_identity(ownership, "1.0.0")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    changesets = parse_changesets(ownership)
    write_release_note(
        ownership,
        version="1.0.0",
        changesets=changesets,
        introduction=(
            f"Promotes {rc_tag} from exact source `{source}`.\n\n"
            + (
                f"Admitted proof/repo-maintenance preparation source: `{preparation_source}`; product source remains unchanged.\n\n"
                if reconciliation
                else ""
            )
            + "Stable support remains conditional on fresh exact-subject admission."
        ),
    )
    for changeset in changesets:
        changeset.path.unlink()
    return record


def verify_rc_promotion(ownership: dict[str, Any], *, subject: str | None = None) -> dict[str, Any]:
    subject = subject or _run(["git", "rev-parse", "HEAD"]).stdout.strip()
    record = json.loads(_run(["git", "show", f"{subject}:{PROMOTION_RECORD}"]).stdout)
    rc_tag = record.get("rc_tag", "")
    if parse_release_tag(rc_tag)[0] != "release-candidate":
        raise SystemExit("Stable promotion requires an RC identity")
    verified = verify_preview_release(ownership, tag=rc_tag, artifact_commit=_tag_target(rc_tag))
    expected = {
        "kind": "agentic-workspace/rc-stable-promotion/v1",
        "rc_tag": rc_tag,
        "rc_artifact_commit": verified["artifact_commit"],
        "source_commit": verified["reconstruction_source_commit"],
        "stable_tag": "v1.0.0",
        "rc_package_versions": release_identity(rc_tag)["package_versions"],
    }
    preparation_source = verified["reconstruction_source_commit"]
    if "proof_reconciliation" in record:
        carried = record["proof_reconciliation"]
        if not isinstance(carried, dict):
            raise SystemExit("Invalid carried proof reconciliation")
        preparation_source = carried.get("preparation_source_commit", "")
        expected["proof_reconciliation"] = _proof_reconciliation(verified, preparation_source)
    if record != expected:
        raise SystemExit("Stable promotion record does not match the exact immutable RC")
    source = preparation_source
    if _run(["git", "merge-base", "--is-ancestor", source, subject], check=False).returncode:
        raise SystemExit("Stable subject does not descend from the accepted RC source")
    changed = verify_normalization_delta(
        ownership,
        source=source,
        subject=subject,
        version="1.0.0",
        metadata_paths={PROMOTION_RECORD, _repo_path(release_note_path(ownership, "1.0.0"))},
    )
    for path in package_pyprojects(ownership):
        if tomllib.loads(_run(["git", "show", f"{subject}:{_repo_path(path)}"]).stdout)["project"]["version"] != "1.0.0":
            raise SystemExit("Stable promotion requires normalized package versions")
    return {**record, "stable_commit": subject, "normalization_paths": changed, "support_bearing_admission": "required-separately"}


def plan_rc_promotion(ownership: dict[str, Any], *, rc_tag: str) -> dict[str, Any]:
    verified = verify_preview_release(ownership, tag=rc_tag, artifact_commit=_tag_target(rc_tag))
    prepared = (ROOT / PROMOTION_RECORD).exists()
    if prepared:
        promotion = verify_rc_promotion(ownership)
        if promotion["rc_tag"] != rc_tag:
            raise SystemExit("Prepared stable subject belongs to a different accepted RC")
    else:
        _proof_reconciliation(verified, _run(["git", "rev-parse", "HEAD"]).stdout.strip())
    return {"release_required": not prepared, "version": "1.0.0", "tag": "v1.0.0", "bump": "major", "changesets": []}


def preview_release_note_path(ownership: dict[str, Any], tag: str) -> Path:
    release_class, _ = parse_release_tag(tag)
    if release_class not in {"preview", "release-candidate"}:
        raise ValueError(f"Preview release tag required, got {tag!r}")
    return release_notes_dir(ownership) / f"{tag}.md"


def preview_metadata_path(ownership: dict[str, Any], tag: str) -> Path:
    release_class, _ = parse_release_tag(tag)
    if release_class not in {"preview", "release-candidate"}:
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
            release_class, version = parse_release_tag(tag)
        except ValueError:
            continue
        # A canonical preview name reserves its version permanently, even when
        # its subject is invalid or future package topology no longer matches.
        # Reservation is not publication/admission verification.
        if release_class == "release-candidate":
            continue  # RC identity reserves its rc.N, never burns target stable v1.0.0.
        if release_class == "preview" or _tag_declares_coordinated_release_version(ownership, tag=tag, version=version):
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
    if version == Version(1, 0, 0) and "release_candidate" in ownership:
        return {
            "kind": "agentic-workspace/coordinated-release-plan/v1",
            "release_required": False,
            "reason": "first-stable-requires-explicit-accepted-rc",
            "changesets": [_repo_path(c.path) for c in changesets],
        }
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
    node_version = npm_version(version)
    for path in package_pyprojects(ownership):
        text = path.read_text(encoding="utf-8")
        updated = re.sub(r'^version = "[^"]+"$', f'version = "{version}"', text, count=1, flags=re.MULTILINE)
        if updated == text:
            raise SystemExit(f"{_repo_path(path)} does not contain a project version assignment")
        path.write_text(updated, encoding="utf-8")
    for path in typescript_package_jsons(ownership):
        payload = json.loads(path.read_text(encoding="utf-8"))
        payload["version"] = node_version
        path.write_text(json.dumps(payload, indent=2, sort_keys=False) + "\n", encoding="utf-8")
    for path in cargo_manifests(ownership):
        text = path.read_text(encoding="utf-8")
        path.write_text(re.sub(r'^version = "[^"]+"$', f'version = "{node_version}"', text, count=1, flags=re.MULTILINE), encoding="utf-8")
    for lock in cargo_lockfiles(ownership):
        text = lock.read_text()
        names = {package["name"] for package in ownership["cargo_packages"]}
        local_names = {package["name"] for package in tomllib.loads(text)["package"] if "source" not in package}
        for name in names & local_names:
            pattern = r'(\[\[package\]\]\nname = "' + re.escape(name) + r'"\nversion = ")[^"]+("\n)'
            text, count = re.subn(pattern, lambda match: match[1] + node_version + match[2], text)
            if count != 1:
                raise SystemExit("Missing unique coordinated Cargo lock identity")
        lock.write_text(text)


def normalized_payload_provenance(payload: Any, version: str) -> dict[str, Any]:
    """Normalize only the package version owned by native_payload.rs::shipped.

    Tags belong to release metadata/receipts. Preserve unrelated source fields;
    normalization cannot manufacture a missing or malformed payload identity.
    """
    npm_version(version)
    if not isinstance(payload, dict):
        raise SystemExit("Workspace payload provenance must be an object")
    identity = payload.get("release_identity")
    if (
        payload.get("kind") != "agentic-workspace/payload-provenance/v1"
        or payload.get("payload_schema") != "agentic-workspace/payload/v1"
        or not isinstance(identity, dict)
        or identity.get("package") != "agentic-workspace"
        or not isinstance(identity.get("version"), str)
        or not identity["version"]
        or any(
            not isinstance(payload.get(field), list)
            or not payload[field]
            or any(not isinstance(value, str) or not value for value in payload[field])
            for field in ("payload_files", "payload_capabilities")
        )
    ):
        raise SystemExit("Workspace payload provenance has an invalid native payload identity")
    return {**payload, "release_identity": {**identity, "version": version}}


def set_workspace_payload_release_identity(ownership: dict[str, Any], version: str) -> None:
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
    payload = normalized_payload_provenance(json.loads(provenance_path.read_text(encoding="utf-8")), version)
    provenance_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8", newline="\n")


def write_release_note(ownership: dict[str, Any], *, version: str, changesets: list[Changeset], introduction: str = "") -> Path:
    path = release_note_path(ownership, version)
    if path.exists():
        raise SystemExit(f"{_repo_path(path)} already exists; refusing to duplicate release-note summaries")
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [f"# Release v{version}", ""]
    if introduction:
        lines.extend([introduction, ""])
    lines.extend(["## Changes", ""])
    lines.extend(f"- {changeset.summary}" for changeset in changesets)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def prerelease_label(tag: str) -> str:
    release_class, _ = parse_release_tag(tag)
    if release_class not in {"preview", "release-candidate"}:
        raise ValueError(f"Prerelease tag required, got {tag!r}")
    return "Release candidate" if release_class == "release-candidate" else "Preview"


def write_preview_release_note(ownership: dict[str, Any], *, tag: str, source_commit: str) -> Path:
    identity = release_identity(tag)
    label = prerelease_label(tag)
    version = identity["version"]
    path = preview_release_note_path(ownership, tag)
    if path.exists():
        raise SystemExit(f"{_repo_path(path)} already exists; refusing to replace preview release notes")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(
            [
                f"# {label} {tag}",
                "",
                f"> Non-support-bearing {label.lower()} for external testing. This is not a stable release or v1 admission.",
                "",
                f"- Package version: `{version}`",
                f"- Release identity: `{tag}`; npm version: `{npm_version(version)}`; target stable: `{identity.get('target_stable_tag', 'not release-bound')}`",
                f"- Reconstruction source commit: `{source_commit}`",
                f"- Stability/support: {label.lower()} only; interfaces and behavior may change before first stable.",
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
        **release_identity(tag),
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
    if release_class not in {"preview", "release-candidate"}:
        raise SystemExit(f"Preview preparation requires a {PREVIEW_TAG_PREFIX}MAJOR.MINOR.PATCH tag")
    actual_source = _run(["git", "rev-parse", "HEAD"]).stdout.strip()
    if actual_source != source_commit:
        raise SystemExit(f"Preview source checkout is {actual_source}, expected {source_commit}")

    if release_class == "release-candidate":
        validate_next_rc(ownership, tag=tag, source_commit=source_commit)
    else:
        existing_versions = existing_release_versions(ownership)
        current_versions = current_package_versions(ownership)
        public_floor = max([*current_versions, *existing_versions])
        if version <= public_floor:
            raise SystemExit(f"Preview version {version} must be greater than public/package version floor {public_floor}")
    package_version = release_identity(tag)["version"]

    pending_changesets = [_repo_path(changeset.path) for changeset in parse_changesets(ownership)]
    set_workspace_version(ownership, package_version)
    set_workspace_payload_release_identity(ownership, package_version)
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
        **release_identity(tag),
    }


def verify_preview_release(
    ownership: dict[str, Any], *, tag: str, source_commit: str | None = None, artifact_commit: str | None = None
) -> dict[str, Any]:
    def read(path: Path) -> str:
        if artifact_commit is not None:
            return _run(["git", "show", f"{artifact_commit}:{_repo_path(path)}"]).stdout
        return path.read_text(encoding="utf-8")

    release_class, version = parse_release_tag(tag)
    if release_class not in {"preview", "release-candidate"}:
        raise SystemExit(f"Preview verification requires a {PREVIEW_TAG_PREFIX}MAJOR.MINOR.PATCH tag")
    version = release_identity(tag)["version"]
    versions = [tomllib.loads(read(path))["project"]["version"] for path in package_pyprojects(ownership)]
    node_versions = [json.loads(read(path))["version"] for path in typescript_package_jsons(ownership)]
    cargo_versions = [tomllib.loads(read(path))["package"]["version"] for path in cargo_manifests(ownership)]
    if any(v != npm_version(version) for v in cargo_versions):
        raise SystemExit("Cargo versions do not match the canonical release mapping")
    if not versions or any(v != version for v in versions) or any(v != npm_version(version) for v in node_versions):
        raise SystemExit("Preview tag requires workspace version matching the explicit Python/npm version mapping")
    workspace_version = versions[0]
    if workspace_version != str(version):
        raise SystemExit(f"Preview tag {tag!r} requires workspace version {version}, got {workspace_version}")

    metadata_path = preview_metadata_path(ownership, tag)
    metadata = json.loads(read(metadata_path))
    expected_source = source_commit or str(metadata.get("reconstruction_source_commit") or "")
    expected_metadata = {
        "kind": "agentic-workspace/coordinated-preview-subject/v1",
        "release_class": "preview",
        "support_bearing": False,
        "tag": tag,
        "version": str(version),
        "reconstruction_source_commit": expected_source,
        **release_identity(tag),
    }
    if metadata != expected_metadata:
        raise SystemExit(f"Preview metadata mismatch at {_repo_path(metadata_path)}")
    if not expected_source:
        raise SystemExit("Preview metadata must identify the reconstruction source commit")

    provenance_ref = next(package["payload_provenance"] for package in ownership["packages"] if package["name"] == "agentic-workspace")
    payload = json.loads(read(ROOT / provenance_ref))
    if payload != normalized_payload_provenance(payload, str(version)):
        raise SystemExit("Workspace payload release identity does not match preview version")

    subject_commit = artifact_commit or _run(["git", "rev-parse", "HEAD"]).stdout.strip()
    parents = _run(["git", "rev-list", "--parents", "-n", "1", subject_commit]).stdout.strip().split()
    if len(parents) != 2 or parents[1] != expected_source:
        raise SystemExit(
            f"Preview artifact commit {subject_commit} must have exactly reconstruction source {expected_source} as its parent"
        )
    tag_target = _run(["git", "rev-list", "-n", "1", f"refs/tags/{tag}"], check=False)
    if tag_target.returncode != 0 or tag_target.stdout.strip() != subject_commit:
        raise SystemExit(f"Preview tag {tag} must resolve to exact artifact commit {subject_commit}")
    # Read the allowlist from the source, so the artifact cannot grant itself
    # permission to change publisher code or release authority.
    source_ownership = _run(["git", "show", f"{expected_source}:.github/release-ownership.json"])
    allowed = json.loads(source_ownership.stdout)["preview_release_commit_allowed_paths"]
    changed = _run(["git", "diff", "--name-only", "--no-renames", expected_source, subject_commit]).stdout.splitlines()
    unexpected = [path for path in changed if not preview_path_allowed(path, allowed)]
    if not allowed or not changed or unexpected:
        raise SystemExit(f"Preview artifact changed non-release-only paths or has no normalization delta: {unexpected}")
    for path in package_pyprojects(ownership):
        before = tomllib.loads(_run(["git", "show", f"{expected_source}:{_repo_path(path)}"]).stdout)
        after = tomllib.loads(read(path))
        before["project"]["version"] = str(version)
        if before != after:
            raise SystemExit(f"Preview changed non-version package metadata: {_repo_path(path)}")
    for path in typescript_package_jsons(ownership):
        before = json.loads(_run(["git", "show", f"{expected_source}:{_repo_path(path)}"]).stdout)
        before["version"] = npm_version(version)
        if before != json.loads(read(path)):
            raise SystemExit(f"Preview changed non-version package metadata: {_repo_path(path)}")
    for path in cargo_manifests(ownership):
        before = tomllib.loads(_run(["git", "show", f"{expected_source}:{_repo_path(path)}"]).stdout)
        before["package"]["version"] = npm_version(version)
        if before != tomllib.loads(read(path)):
            raise SystemExit(f"Preview changed non-version Cargo metadata: {_repo_path(path)}")
    for lock in cargo_lockfiles(ownership):
        before = tomllib.loads(_run(["git", "show", f"{expected_source}:{_repo_path(lock)}"]).stdout)
        names = {package["name"] for package in ownership["cargo_packages"]}
        for package in before["package"]:
            if package["name"] in names and "source" not in package:
                package["version"] = npm_version(version)
        if before != tomllib.loads(read(lock)):
            raise SystemExit("Preview changed third-party Cargo resolution")
    provenance_ref = next(package["payload_provenance"] for package in ownership["packages"] if package["name"] == "agentic-workspace")
    before = json.loads(_run(["git", "show", f"{expected_source}:{provenance_ref}"]).stdout)
    before = normalized_payload_provenance(before, str(version))
    if before != json.loads(read(ROOT / provenance_ref)):
        raise SystemExit("Preview changed non-release payload provenance")
    for language in ("python", "typescript"):
        relative = f"generated/workspace/{language}/external_contract_bundle.json"
        if relative not in allowed:
            continue
        before = json.loads(_run(["git", "show", f"{expected_source}:{relative}"]).stdout)
        before["versions"]["client_package"] = str(version)
        before["versions"]["python_package"]["version"] = str(version)
        before["versions"]["typescript_package"]["version"] = npm_version(version)
        if before != json.loads(read(ROOT / relative)):
            raise SystemExit(f"Preview changed non-version external contract: {relative}")
    note_path = preview_release_note_path(ownership, tag)
    if expected_source not in read(note_path):
        raise SystemExit(f"Preview release note {_repo_path(note_path)} must identify reconstruction source {expected_source}")
    if release_class == "release-candidate":
        number = int(tag.rsplit(".", 1)[1])
        prior_tags = _run(["git", "tag", "--list", "v1.0.0-rc.*"]).stdout.splitlines()
        numbers = sorted(
            int(t.rsplit(".", 1)[1])
            for t in prior_tags
            if re.fullmatch(r"v1\.0\.0-rc\.[1-9][0-9]*", t) and int(t.rsplit(".", 1)[1]) <= number
        )
        if len(numbers) != number or any(n != i for i, n in enumerate(numbers, 1)):
            raise SystemExit("RC admission requires contiguous immutable candidate identities")
        if number > 1:
            prior_tag = f"v1.0.0-rc.{number - 1}"
            prior_commit = _tag_target(prior_tag)
            prior_metadata = preview_metadata_path(ownership, prior_tag)
            prior = json.loads(_run(["git", "show", f"{prior_commit}:{_repo_path(prior_metadata)}"]).stdout)
            prior_source = prior["reconstruction_source_commit"]
            if (
                prior_source == expected_source
                or _run(["git", "diff", "--quiet", prior_source, expected_source], check=False).returncode == 0
            ):
                raise SystemExit("RC admission requires a new candidate source, not a retry identity")
            if _run(["git", "merge-base", "--is-ancestor", prior_source, expected_source], check=False).returncode:
                raise SystemExit("RC admission requires continuation of the preceding source")
        verify_normalization_delta(
            ownership,
            source=expected_source,
            subject=subject_commit,
            version=version,
            metadata_paths={_repo_path(note_path), _repo_path(metadata_path)},
        )

    return {
        "kind": "agentic-workspace/coordinated-preview-verification/v1",
        "release_class": "preview",
        "support_bearing": False,
        "version": str(version),
        "tag": tag,
        "reconstruction_source_commit": expected_source,
        "artifact_commit": subject_commit,
        "package_count": len(versions) + len(node_versions),
        "release_note": _repo_path(note_path),
        "preview_metadata": _repo_path(metadata_path),
        "release_only_paths": changed,
        **release_identity(tag),
    }


def preview_path_allowed(path: str, allowed: list[str]) -> bool:
    return any(path == entry.rstrip("/") or (entry.endswith("/") and path.startswith(entry)) for entry in allowed)


def verify_workspace_versions(ownership: dict[str, Any], *, tag: str | None = None) -> dict[str, Any]:
    versions = current_package_versions(ownership)
    version = current_workspace_version(ownership)
    for path in cargo_manifests(ownership):
        if tomllib.loads(path.read_text())["package"]["version"] != npm_version(version):
            raise SystemExit("Cargo package version differs from coordinated release")
    if tag and tag != f"v{version}":
        raise SystemExit(f"Release tag {tag!r} must match workspace version {version!r}")
    if tag == "v1.0.0" and "release_candidate" in ownership:
        verify_rc_promotion(ownership)
    for package in ownership["packages"]:
        if package.get("name") == "agentic-workspace" and package.get("payload_provenance"):
            payload = json.loads((ROOT / package["payload_provenance"]).read_text(encoding="utf-8"))
            if payload != normalized_payload_provenance(payload, version):
                raise SystemExit("Workspace payload version does not match coordinated package version")
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
    if version == "1.0.0" and "release_candidate" in ownership:
        verify_rc_promotion(ownership, subject=release_commit)
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
    plan_parser.add_argument("--from-rc")

    prepare_parser = subparsers.add_parser("prepare")
    prepare_parser.add_argument("--from-rc")

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

    promotion_prepare = subparsers.add_parser("prepare-rc-promotion")
    promotion_prepare.add_argument("--rc", required=True)
    promotion_verify = subparsers.add_parser("verify-rc-promotion")
    promotion_verify.add_argument("--require-published", action="store_true")
    promotion_verify.add_argument("--repo")

    args = parser.parse_args(argv)
    ownership = load_ownership()

    if args.command == "prepare-rc-promotion":
        print(json.dumps(prepare_rc_promotion(ownership, rc_tag=args.rc), indent=2))
        return 0
    if args.command == "verify-rc-promotion":
        result = verify_rc_promotion(ownership)
        if args.require_published:
            import preview_release

            if not args.repo:
                parser.error("--require-published needs --repo")
            verified = verify_preview_release(ownership, tag=result["rc_tag"], artifact_commit=result["rc_artifact_commit"])
            if not preview_release.verify_published_preview(repo=args.repo, verified=verified):
                raise SystemExit("Accepted RC publication is incomplete")
        print(json.dumps(result, indent=2))
        return 0

    if args.command == "plan":
        if args.from_rc:
            if parse_release_tag(args.from_rc)[0] != "release-candidate":
                parser.error("--from-rc requires a canonical RC")
            plan = plan_rc_promotion(ownership, rc_tag=args.from_rc)
        else:
            plan = plan_release(ownership, include_git_tags=not args.ignore_git_tags)
        if args.github_output:
            write_github_output(plan, args.github_output)
        print(json.dumps(plan, indent=2, sort_keys=True))
        return 0
    if args.command == "prepare":
        result = prepare_rc_promotion(ownership, rc_tag=args.from_rc) if args.from_rc else prepare_release(ownership)
        print(json.dumps(result, indent=2, sort_keys=True))
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
