"""Repository-owned release stages; GitHub supplies runners and publication identity."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

import cargo_release
import coordinated_release
import preview_release
import registry_release
import stable_manifest

ROOT = Path(__file__).resolve().parents[3]
IDENTITY_FILE = "release-identity.json"
BUNDLE_NAME = "verified-release-bundle"


def write_json(path, value):
    Path(path).write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def download_run_artifact(repository, run_id, name, directory):
    artifacts = api(repository, f"actions/runs/{run_id}/artifacts?per_page=100")["artifacts"]
    matches = [a for a in artifacts if a["name"] == name]
    if not matches:
        return False
    if len(matches) != 1 or matches[0].get("expired"):
        raise ValueError(f"Recovery gap: retained {name} for run {run_id} is unavailable")
    run("gh", "run", "download", str(run_id), "--repo", repository, "--name", name, "--dir", str(directory))
    return True


def publication_receipts(repository, tag, source, directory):
    """Use public receipts, or the original successful legacy publisher's retained receipts."""
    directory = Path(directory)
    paths = [directory / "registry-publication.json", directory / "cargo-registry-publication.json"]
    if not all(p.is_file() for p in paths):
        runs = api(repository, "actions/workflows/release.yml/runs?status=success&per_page=100")["workflow_runs"]
        for candidate in runs:
            if candidate.get("event") != "workflow_dispatch" or candidate.get("head_branch") != "master":
                continue
            with tempfile.TemporaryDirectory() as temporary:
                temp = Path(temporary)
                if not download_run_artifact(repository, candidate["id"], "language-registry-publication", temp):
                    continue
                receipt = json.loads((temp / "registry-publication.json").read_text())
                if receipt.get("tag") != tag or receipt.get("source_commit") != source:
                    continue
                if not download_run_artifact(repository, candidate["id"], "cargo-registry-publication", temp):
                    return False
                for path in paths:
                    path.write_bytes((temp / path.name).read_bytes())
                break
    if not all(p.is_file() for p in paths):
        return False
    for path in paths:
        receipt = json.loads(path.read_text())
        if receipt.get("status") != "passed" or receipt.get("tag") != tag or receipt.get("source_commit") != source:
            raise ValueError(f"Conflicting publication receipt: {path.name}")
    return True


def completed_release(repository, tag, source, *, allow_yanked=False):
    """Verify historical publication bytes even when the recorded release is yanked."""
    response = subprocess.run(["gh", "api", f"repos/{repository}/releases/tags/{tag}"], capture_output=True, text=True)
    if response.returncode:
        if "HTTP 404" not in response.stderr:
            raise ValueError("Unknown remote release state: " + response.stderr)
        return None
    release = json.loads(response.stdout)
    if release.get("draft") or release.get("prerelease"):
        return None
    with tempfile.TemporaryDirectory() as temporary:
        dist = Path(temporary) / "dist"
        registry_release.fetch_admitted(dist, tag, repository)
        identity, artifacts = registry_release.admitted_artifacts(dist, tag, source)
        if not publication_receipts(repository, tag, source, dist):
            return None
        statuses = [registry_release.observe(a, dist, allow_yanked=allow_yanked) for a in artifacts]
        cargo = json.loads((dist / "cargo-release-manifest.json").read_text())
        statuses.extend(cargo_release.observe(a, allow_yanked=allow_yanked) for a in cargo["packages"])
        if any(status != "matching" for status in statuses):
            return None
        return {**identity, "source_commit": source}


def observe_stable(repository):
    """A reserved tag and a completed release answer different questions."""
    tags = api(repository, "git/matching-refs/tags/")
    versions = []
    stable = []
    reservations = []
    for row in tags:
        tag = row["ref"].removeprefix("refs/tags/")
        try:
            channel, version = coordinated_release.parse_release_tag(tag)
        except ValueError:
            continue
        versions.append(str(version))
        reservations.append((str(version), tag))
        if channel == "stable":
            stable.append((version, tag))
    if not stable:
        raise ValueError("No completed stable boundary; use the exceptional first-stable recovery procedure")
    correction = coordinated_release.version_line_correction(git("rev-parse", "HEAD").strip())
    withdrawn = None
    if correction:
        if any(version == correction["withdrawn"]["version"] and tag != correction["withdrawn"]["tag"] for version, tag in reservations):
            raise ValueError("Version-line correction conflicts with another reservation at 2.0.0")
        for key in ("previous", "withdrawn"):
            subject = correction[key]
            if api(repository, f"commits/{subject['tag']}")["sha"] != subject["source_commit"]:
                raise ValueError("Version-line correction conflicts with immutable remote source")
        subject = correction["withdrawn"]
        if subject["tag"] not in {tag for _, tag in stable}:
            raise ValueError("Version-line correction lacks the reserved withdrawn tag")
        withdrawn = completed_release(repository, subject["tag"], subject["source_commit"], allow_yanked=True)
        if withdrawn is None or withdrawn.get("version") != subject["version"]:
            raise ValueError("Version-line correction requires verified completed original publication")
    completed = None
    partial = []
    for _, tag in sorted(stable, reverse=True):
        if correction and tag == correction["withdrawn"]["tag"]:
            continue
        source = api(repository, f"commits/{tag}")["sha"]
        completed = completed_release(repository, tag, source)
        if completed is None:
            partial.append(tag)
            continue
        if correction and coordinated_release.Version.parse(completed["version"]) <= coordinated_release.Version.parse(
            correction["previous"]["version"]
        ):
            completed = withdrawn
        break
    if completed is None:
        raise ValueError("No verified completed stable boundary; recover " + ", ".join(partial))
    if correction:
        completed["version_line_correction"] = correction
    # Public versions may be reserved without a Git tag. Unknown metadata fails closed.
    ownership = coordinated_release.load_ownership()
    documents = []
    for package in ownership["packages"]:
        data = registry_release.json_response(f"https://pypi.org/pypi/{package['name']}/json")
        if data is None:
            raise ValueError("Missing existing PyPI package evidence")
        documents.extend(data["releases"])
    for package in ownership["typescript_packages"]:
        data = registry_release.json_response("https://registry.npmjs.org/" + package["name"].replace("/", "%2f"))
        if data is None:
            raise ValueError("Missing existing npm package evidence")
        documents.extend(data["versions"])
    for package in ownership["cargo_packages"]:
        data = registry_release.json_response(f"https://crates.io/api/v1/crates/{package['name']}")
        if data is None:
            raise ValueError("Missing existing Cargo package evidence")
        documents.extend(row["num"] for row in data["versions"])
    for version in documents:
        if re.fullmatch(r"\d+\.\d+\.\d+", version):
            versions.append(version)
            if (
                coordinated_release.Version.parse(version)
                > coordinated_release.Version.parse(
                    correction["previous"]["version"]
                    if correction and completed["tag"] == correction["withdrawn"]["tag"]
                    else completed["version"]
                )
                and "v" + version not in partial
                and not (correction and version == correction["withdrawn"]["version"])
            ):
                partial.append("v" + version)
    return completed, versions, partial


def resolve_source(repository, source, tag, qualify_only):
    if not qualify_only and os.environ.get("GITHUB_REF") != "refs/heads/master":
        raise ValueError("Publication requires a dispatch on protected master")
    if not re.fullmatch(r"[0-9a-f]{40}", source):
        raise ValueError("A full pinned dispatch SHA is required")
    git("fetch", "origin", "refs/heads/master:refs/remotes/origin/master")
    if not qualify_only:
        git("merge-base", "--is-ancestor", source, "origin/master")
    run_id = os.environ["GITHUB_RUN_ID"]
    if download_run_artifact(repository, run_id, "release-identity", ROOT):
        identity = json.loads((ROOT / IDENTITY_FILE).read_text())
        if identity.get("dispatch_source") != source or identity.get("recovery_tag", "") != tag:
            raise ValueError("Retained run identity differs from this dispatch")
        identity["identity_reused"] = True
        if download_run_artifact(repository, run_id, BUNDLE_NAME, ROOT / "dist"):
            identity["build_required"] = False
            verify_bundle(ROOT / "dist", identity)
        elif download_run_artifact(repository, run_id, "recovered-release-bundle", ROOT / "dist"):
            identity["build_required"] = False
            identity["recovery_reused"] = True
            verify_bundle(ROOT / "dist", identity)
        elif identity.get("tag"):
            reserved = subprocess.run(["gh", "api", f"repos/{repository}/git/ref/tags/{identity['tag']}"], capture_output=True, text=True)
            if reserved.returncode == 0:
                raise ValueError("Recovery gap: tag is reserved but this run's verified bundle is missing; do not rebuild")
            if "HTTP 404" not in reserved.stderr:
                raise ValueError("Unknown reserved tag state: " + reserved.stderr)
        return identity
    if tag:
        # Recovery never rebuilds: retrieve the bundle named by the immutable annotation.
        commit = api(repository, f"commits/{tag}")["sha"]
        remote = api(repository, f"git/ref/tags/{tag}")
        if remote["object"]["type"] == "tag":
            annotation = api(repository, "git/tags/" + remote["object"]["sha"])["message"]
        else:
            annotation = ""
        try:
            retained = json.loads(annotation)
        except ValueError:
            retained = {}
        if retained.get("kind") == "agentic-workspace/release-tag/v1":
            if not download_run_artifact(repository, retained["run_id"], BUNDLE_NAME, ROOT / "dist"):
                raise ValueError("Recovery gap: original verified bundle is missing; do not rebuild published bytes")
            identity = json.loads((ROOT / "dist" / IDENTITY_FILE).read_text())
            if identity["source_commit"] != commit or identity["tag"] != tag:
                raise ValueError("Retained bundle conflicts with immutable tag")
            if registry_release.sha256(ROOT / "dist/SHA256SUMS") != retained["inventory_sha256"]:
                raise ValueError("Retained inventory differs from tag admission")
        else:
            registry_release.fetch_admitted(ROOT / "dist", tag, repository)
            model, _ = registry_release.admitted_artifacts(ROOT / "dist", tag, commit)
            identity = {**model, "source_commit": commit, "legacy": True, "release_required": True}
        identity.update(build_required=False, dispatch_source=source, recovery_tag=tag)
    else:
        completed, versions, partial = observe_stable(repository)
        identity = coordinated_release.select_release(
            coordinated_release.load_ownership(), source=source, completed=completed, reserved=versions, partial=partial
        )
        identity.update(build_required=identity["release_required"], dispatch_source=source, recovery_tag="")
    write_json(ROOT / IDENTITY_FILE, identity)
    return identity


def stage_identity(path, verify=False):
    identity = json.loads(Path(path).read_text())
    result = coordinated_release.stamp_release(coordinated_release.load_ownership(), identity, verify=verify)
    if not verify:
        write_json(path, result)
    return result


def verify_bundle(directory, identity):
    directory = Path(directory)
    seen = set()
    for line in (directory / "SHA256SUMS").read_text().splitlines():
        digest, name = line.split("  ", 1)
        if Path(name).name != name or name in seen or not re.fullmatch(r"[a-f0-9]{64}", digest):
            raise ValueError("Invalid admitted inventory")
        seen.add(name)
        if registry_release.sha256(directory / name) != digest:
            raise ValueError("Admitted artifact changed: " + name)
    registry_release.admitted_artifacts(directory, identity["tag"], identity["source_commit"])
    if not identity.get("legacy"):
        manifest = json.loads((directory / "agentic-workspace-release-manifest.json").read_text())
        staged = json.loads((directory / IDENTITY_FILE).read_text())
        for key in ("source_commit", "version", "tag", "changesets", "boundary", "transform", "version_line_correction"):
            if staged.get(key) != manifest["staging"].get(key):
                raise ValueError("Bundle staging identity mismatch")
        if staged["source_commit"] != identity["source_commit"] or staged["tag"] != identity["tag"]:
            raise ValueError("Bundle subject mismatch")
        ownership = coordinated_release.load_ownership()
        expected = coordinated_release.staging_files(ownership, staged["source_commit"], staged["version"])
        transform = [{"path": path, "sha256": hashlib.sha256(content.encode()).hexdigest()} for path, content in sorted(expected.items())]
        if staged["transform"] != transform or staged["changesets"] != coordinated_release.selected_changes(
            ownership, staged["boundary"]["source_commit"], staged["source_commit"]
        ):
            raise ValueError("Bundle differs from the deterministic source transformation")


def publish_github(repository, identity):
    verify_bundle(ROOT / "dist", identity)
    source, tag = identity["source_commit"], identity["tag"]
    git("fetch", "origin", "refs/heads/master:refs/remotes/origin/master")
    git("merge-base", "--is-ancestor", source, "origin/master")
    remote = subprocess.run(["gh", "api", f"repos/{repository}/git/ref/tags/{tag}"], capture_output=True, text=True)
    if remote.returncode:
        if "HTTP 404" not in remote.stderr:
            raise ValueError("Unknown tag state: " + remote.stderr)
        completed, versions, partial = observe_stable(repository)
        if partial:
            raise ValueError("Release state changed before publication; recover the reserved subject")
        current = coordinated_release.select_release(
            coordinated_release.load_ownership(), source=source, completed=completed, reserved=versions, partial=partial
        )
        if any(current.get(key) != identity.get(key) for key in ("tag", "changesets", "boundary", "version_line_correction")):
            raise ValueError("Reserved versions or completed source changed before publication")
        annotation = {
            "kind": "agentic-workspace/release-tag/v1",
            "run_id": os.environ["GITHUB_RUN_ID"],
            "source_commit": source,
            "tag": tag,
            "inventory_sha256": registry_release.sha256(ROOT / "dist/SHA256SUMS"),
        }
        git(
            "-c",
            "user.name=github-actions[bot]",
            "-c",
            "user.email=41898282+github-actions[bot]@users.noreply.github.com",
            "tag",
            "-a",
            tag,
            source,
            "-m",
            json.dumps(annotation, sort_keys=True),
        )
        run("gh", "auth", "setup-git")
        git("push", "origin", "refs/tags/" + tag)
    else:
        if api(repository, f"commits/{tag}")["sha"] != source:
            raise ValueError("Immutable tag has a conflicting source")
        if not identity.get("legacy"):
            reference = json.loads(remote.stdout)
            if reference["object"]["type"] != "tag":
                raise ValueError("Staged publication requires an annotated admission tag")
            annotation = json.loads(api(repository, "git/tags/" + reference["object"]["sha"])["message"])
            if (
                annotation.get("source_commit") != source
                or annotation.get("tag") != tag
                or annotation.get("inventory_sha256") != registry_release.sha256(ROOT / "dist/SHA256SUMS")
            ):
                raise ValueError("Immutable tag has a conflicting release identity")
    response = subprocess.run(["gh", "api", f"repos/{repository}/releases/tags/{tag}"], capture_output=True, text=True)
    if response.returncode:
        if "HTTP 404" not in response.stderr:
            raise ValueError("Unknown release state: " + response.stderr)
        command = [
            "gh",
            "release",
            "create",
            tag,
            "--repo",
            repository,
            "--verify-tag",
            "--title",
            tag,
            "--notes-file",
            "dist/release-notes.md",
        ]
        if identity.get("version_line_correction"):
            command.append("--latest")
        run(*command)
        release = api(repository, f"releases/tags/{tag}")
    else:
        release = json.loads(response.stdout)
    if (
        release.get("tag_name") != tag
        or release.get("prerelease") != (coordinated_release.release_identity(tag)["release_class"] != "stable")
        or release.get("draft")
    ):
        raise ValueError("Existing release identity conflicts")
    existing = {a["name"]: a for a in release["assets"]}
    names = ["SHA256SUMS", *(line.split("  ", 1)[1] for line in Path("dist/SHA256SUMS").read_text().splitlines())]
    for name in names:
        artifact = ROOT / "dist" / name
        if name in existing:
            data = registry_release.fetch(existing[name]["browser_download_url"])
            if hashlib.sha256(data).hexdigest() != registry_release.sha256(artifact):
                raise ValueError("Existing immutable asset conflict: " + name)
        else:
            run("gh", "release", "upload", tag, str(artifact), "--repo", repository)


SOURCE_CLAIMS = {
    "Merge sufficiency",
    "Support-bearing promotion",
    "workspace-checks",
    "planning-handoff-checks",
    "independent-owner-ingress",
}


def run(*command):
    subprocess.run(list(command), check=True, cwd=ROOT, stdout=sys.stderr)


def git(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()


def operation(script, *arguments):
    run(sys.executable, str(ROOT / "src/tooling" / script), *arguments)


def release_model(tag, release_class):
    identity = coordinated_release.release_identity(tag)
    if identity["release_class"] != release_class:
        raise ValueError("Explicit release class does not match the immutable tag")
    return {
        **identity,
        "registries": release_class in {"stable", "release-candidate"},
        "manifest": "agentic-workspace-release-manifest.json"
        if identity["support_bearing"]
        else "agentic-workspace-preview-release-manifest.json",
    }


def inspect_publication(tag, source, release_class, repository, artifact_dir=None):
    """Missing assets permit recovery; changed immutable assets never permit overwrite."""
    model = release_model(tag, release_class)
    if not model["support_bearing"]:
        verified = coordinated_release.verify_preview_release(coordinated_release.load_ownership(), tag=tag)
        return preview_release.verify_published_preview(repo=repository, verified=verified, artifact_dir=artifact_dir)
    result = subprocess.run(["gh", "api", f"repos/{repository}/releases/tags/{tag}"], capture_output=True, text=True)
    if result.returncode:
        if "HTTP 404" in result.stderr:
            return False
        raise ValueError(f"Cannot inspect immutable publication: {result.stderr}")
    release = json.loads(result.stdout)
    if release.get("tag_name") != tag or release.get("prerelease") is not False:
        raise ValueError("Existing release has a different identity or release class")
    with tempfile.TemporaryDirectory(prefix="aw-release-recovery-") as directory:
        dist = Path(directory)
        if release.get("assets"):
            run("gh", "release", "download", tag, "--repo", repository, "--dir", directory)
        for remote in dist.iterdir():
            if artifact_dir is not None:
                local = artifact_dir / remote.name
                if not local.is_file() or registry_release.sha256(local) != registry_release.sha256(remote):
                    raise ValueError(f"Existing immutable release asset differs: {remote.name}")
        manifest = dist / model["manifest"]
        checksums = dist / "SHA256SUMS"
        if not manifest.exists() or not checksums.exists():
            return False
        declared = json.loads(manifest.read_text())
        if declared.get("source_commit") != source or declared.get("tag") != tag:
            raise ValueError("Published manifest has a different immutable subject")
        names = []
        for line in checksums.read_text().splitlines():
            digest, name = line.split("  ", 1)
            if Path(name).name != name or name in names or not re.fullmatch(r"[0-9a-f]{64}", digest):
                raise ValueError("Invalid immutable checksum inventory")
            names.append(name)
            if (dist / name).exists() and registry_release.sha256(dist / name) != digest:
                raise ValueError(f"Published checksum conflict: {name}")
        if any(not (dist / name).is_file() for name in names):
            return False
        stable_manifest.verify(dist)
        registry_release.admitted_artifacts(dist, tag, source)
        return not release.get("draft")


def admit(tag, source, release_class, repository):
    if os.environ.get("GITHUB_EVENT_NAME") == "workflow_dispatch" and os.environ.get("GITHUB_REF") != "refs/heads/master":
        raise ValueError("Release dispatch requires trusted master workflow authority")
    if os.environ.get("GITHUB_EVENT_NAME") == "workflow_dispatch" and not source:
        raise ValueError("Release dispatch requires an exact source commit")
    model = release_model(tag, release_class)
    if source and not re.fullmatch(r"[0-9a-f]{40}", source):
        raise ValueError("Release source must be a full commit SHA")
    git("fetch", "origin", "refs/heads/master:refs/remotes/origin/master", "--tags")
    commit = git("rev-parse", f"refs/tags/{tag}^{{commit}}")
    if source and source != commit:
        raise ValueError("Release tag does not match the requested immutable source")
    if not model["support_bearing"]:
        # Verify with trusted dispatch code before checking out any preview bytes.
        if not source:
            raise ValueError("Preview admission requires an exact artifact commit")
        preview_release.admit_preview_subject(tag=tag, artifact_commit=source)
    else:
        git("merge-base", "--is-ancestor", commit, "refs/remotes/origin/master")
    git("checkout", "--detach", commit)
    if model["support_bearing"]:
        ownership = coordinated_release.load_ownership()
        if any(package.get("release_policy") != "coordinated-public-registry" for package in ownership["typescript_packages"]):
            raise ValueError("Source packages must declare coordinated public registry publication")
        coordinated_release.verify_workspace_versions(ownership, tag=tag)
        if tag == "v1.0.0":
            operation("release/coordinated_release.py", "verify-rc-promotion", "--require-published", "--repo", repository)
        operation(
            "release/support_bearing_promotion.py",
            "github-checks",
            "--repository",
            repository,
            "--commit",
            commit,
            "--output",
            "server-promotion-receipt.json",
            "--wait-seconds",
            "900",
        )
    else:
        coordinated_release.verify_preview_release(coordinated_release.load_ownership(), tag=tag)
    platforms = json.loads(subprocess.check_output([sys.executable, "src/tooling/release/platform_release.py", "matrix"], cwd=ROOT))
    policy = json.loads((ROOT / ".github/support-bearing-promotion.json").read_text())
    complete = inspect_publication(tag, commit, release_class, repository)
    if os.environ.get("REGISTRIES_ONLY") == "true" and (not complete or not model["registries"]):
        raise ValueError("Registry-only recovery requires complete admitted GitHub assets")
    return {
        **model,
        "source_commit": commit,
        "platforms": platforms,
        "runtimes": {"include": policy["runtime_matrix"]},
        "build_required": not complete,
    }


def build(tag, release_class):
    model = release_model(tag, release_class)
    operation("release/platform_release.py", "verify", "--artifact-dir", "dist")
    staging = str(Path(os.environ["RUNNER_TEMP"]) / "aw-cargo")
    operation("release/cargo_release.py", "build", "--artifact-dir", "dist", "--staging", staging)
    operation("release/cargo_release.py", "install-staged", "--artifact-dir", "dist", "--staging", staging)
    args = ["--artifact-dir", "dist", "--require-exact-urls"]
    if model["support_bearing"]:
        args.append("--write-receipts")
    operation("check/check_package_identity.py", *args)
    if model["support_bearing"]:
        operation("release/platform_release.py", "receipts", "--artifact-dir", "dist", "--tag", tag)


def compose(tag, release_class):
    model = release_model(tag, release_class)
    ownership = coordinated_release.load_ownership()
    receipts = []
    for major in ownership["semantic_conformance"]["runtime_majors"]:
        receipt = f"dist/generated-command-conformance-node{major}.json"
        operation(
            "check/check_native_release_topology.py",
            "--verify-receipt",
            receipt,
            "--artifact-dir",
            "dist",
            "--expected-node-major",
            str(major),
            "--expected-execution-context",
            "hosted-ci",
        )
        receipts.extend(["--semantic-receipt", receipt])
    operation(
        "check/check_security_supply_chain.py",
        "--format",
        "json",
        "--source-identity",
        git("rev-parse", "HEAD"),
        "--artifact-dir",
        "dist",
        "--output",
        "dist/security-supply-chain-readiness.json",
    )
    if model["support_bearing"]:
        operation(
            "release/support_bearing_promotion.py",
            "compose",
            "--commit",
            git("rev-parse", "HEAD"),
            "--artifact-dir",
            "dist",
            "--server-receipt",
            "promotion-inputs/server/server-promotion-receipt.json",
            "--runtime-receipt-dir",
            "promotion-inputs/runtime",
            *receipts,
            "--output",
            "dist/support-bearing-promotion.json",
        )
        operation("release/stable_manifest.py", "generate")
    else:
        if Path("dist/support-bearing-promotion.json").exists():
            raise ValueError("Preview cannot carry stable support admission")
        operation("release/preview_manifest.py", "--tag", tag, "--artifact-dir", "dist")
    operation("release/platform_release.py", "extend", "--artifact-dir", "dist", "--tag", tag)
    if model["support_bearing"]:
        operation("release/stable_manifest.py", "verify")


def api(repository, endpoint):
    return json.loads(subprocess.check_output(["gh", "api", f"repos/{repository}/{endpoint}"], text=True))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "stage",
        choices=(
            "admit",
            "observe",
            "resolve",
            "stamp",
            "verify-stage",
            "verify-bundle",
            "publish",
            "complete",
            "build",
            "compose",
            "check-published",
        ),
    )
    parser.add_argument("--identity", type=Path, default=Path(IDENTITY_FILE))
    parser.add_argument("--qualify-only", action="store_true")
    parser.add_argument("--tag", default=os.environ.get("RELEASE_TAG"))
    parser.add_argument("--source", default=os.environ.get("EXPECTED_SOURCE_COMMIT", ""))
    parser.add_argument("--release-class", default=os.environ.get("RELEASE_CLASS", "stable"))
    parser.add_argument("--repository", default=os.environ.get("GITHUB_REPOSITORY"))
    parser.add_argument("--github-output", type=Path)
    args = parser.parse_args()
    if args.stage == "observe":
        import contextlib

        with contextlib.redirect_stdout(sys.stderr):
            completed, versions, partial = observe_stable(args.repository)
        print(json.dumps({"completed": completed, "reserved": versions, "partial": partial}))
    elif args.stage == "resolve":
        result = resolve_source(args.repository, args.source or os.environ["GITHUB_SHA"], args.tag or "", args.qualify_only)
        result["platforms"] = json.loads(
            subprocess.check_output([sys.executable, "src/tooling/release/platform_release.py", "matrix"], cwd=ROOT)
        )
        result["runtimes"] = {"include": json.loads((ROOT / ".github/support-bearing-promotion.json").read_text())["runtime_matrix"]}
        write_json(args.identity, result)
        if result["release_required"] and result["build_required"]:
            stage_identity(args.identity)
        if args.github_output:
            with args.github_output.open("a", encoding="utf-8") as handle:
                for key in (
                    "release_required",
                    "build_required",
                    "identity_reused",
                    "recovery_reused",
                    "source_commit",
                    "tag",
                    "version",
                    "platforms",
                    "runtimes",
                ):
                    value = result.get(key, "")
                    handle.write(f"{key}={value if isinstance(value, str) else json.dumps(value, separators=(',', ':'))}\n")
        if summary := os.environ.get("GITHUB_STEP_SUMMARY"):
            with Path(summary).open("a", encoding="utf-8") as handle:
                handle.write(
                    f"## Source and version\n\nSource: `{result['source_commit']}`\n\n"
                    + (
                        f"Release: `{result['tag']}`\n"
                        if result["release_required"]
                        else "No unconsumed release intent. Nothing to release.\n"
                    )
                )
    elif args.stage in {"stamp", "verify-stage"}:
        stage_identity(args.identity, verify=args.stage == "verify-stage")
    elif args.stage in {"verify-bundle", "publish", "complete"}:
        identity = json.loads(args.identity.read_text())
        if args.stage == "verify-bundle":
            verify_bundle(ROOT / "dist", identity)
        elif args.stage == "publish":
            publish_github(args.repository, identity)
        else:
            verify_bundle(ROOT / "dist", identity)
            if not publication_receipts(args.repository, identity["tag"], identity["source_commit"], ROOT / "dist"):
                raise ValueError("Coordinated publication remains partial")
            for name in ("registry-publication.json", "cargo-registry-publication.json"):
                release = api(args.repository, f"releases/tags/{identity['tag']}")
                existing = next((a for a in release["assets"] if a["name"] == name), None)
                local = ROOT / "dist" / name
                if existing:
                    saved = json.loads(registry_release.fetch(existing["browser_download_url"]))
                    if saved != json.loads(local.read_text()):
                        raise ValueError("Conflicting completion receipt: " + name)
                else:
                    run("gh", "release", "upload", identity["tag"], str(local), "--repo", args.repository)
    elif args.stage == "admit":
        result = admit(args.tag, args.source, args.release_class, args.repository)
        lines = []
        for key in ("tag", "source_commit", "release_class", "support_bearing", "registries", "platforms", "runtimes", "build_required"):
            value = result[key]
            lines.append(f"{key}={json.dumps(value, separators=(',', ':')) if not isinstance(value, str) else value}")
        if args.github_output:
            with args.github_output.open("a", encoding="utf-8") as handle:
                handle.write("\n".join(lines) + "\n")
        else:
            print("\n".join(lines))
    elif args.stage == "check-published":
        inspect_publication(args.tag, git("rev-parse", "HEAD"), args.release_class, args.repository, Path("dist"))
    else:
        {"build": build, "compose": compose}[args.stage](args.tag, args.release_class)
        if args.stage == "compose" and args.github_output:
            assets = ["dist/SHA256SUMS"]
            for line in Path("dist/SHA256SUMS").read_text().splitlines():
                _, name = line.split("  ", 1)
                if Path(name).name != name:
                    raise ValueError("Unsafe publication asset")
                assets.append(f"dist/{name}")
            with args.github_output.open("a", encoding="utf-8") as handle:
                handle.write("assets<<AW_RELEASE_ASSETS\n" + "\n".join(assets) + "\nAW_RELEASE_ASSETS\n")


if __name__ == "__main__":
    main()
