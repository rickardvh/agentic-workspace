"""Repository-owned release stages; GitHub supplies runners and publication identity."""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
import time
import uuid
from pathlib import Path

import coordinated_release
import preview_release
import registry_release
import stable_manifest

ROOT = Path(__file__).resolve().parents[3]
SOURCE_CLAIMS = {
    "Merge sufficiency",
    "Support-bearing promotion",
    "workspace-checks",
    "planning-handoff-checks",
    "independent-owner-ingress",
}


def run(*command):
    subprocess.run(list(command), check=True, cwd=ROOT)


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


def candidate_admission(repository, source, run_id):
    """Reuse source proof only for an exact normalization delta; changed product code fails closed."""
    if not re.fullmatch(r"[0-9a-f]{40}", source) or not str(run_id).isdigit():
        raise ValueError("Candidate admission requires exact source and qualification run")
    evidence = api(repository, f"actions/runs/{run_id}")
    if (
        evidence.get("head_sha") != source
        or evidence.get("conclusion") != "success"
        or evidence.get("path") != ".github/workflows/ci.yml"
        or evidence.get("event") != "workflow_dispatch"
        or not evidence.get("display_title", "").startswith(f"CI / release-source-{source}-")
        or (evidence.get("head_repository") or {}).get("full_name") != repository
    ):
        raise ValueError("Candidate lacks successful exact-source qualification")
    jobs = api(repository, f"actions/runs/{run_id}/jobs?per_page=100")["jobs"]
    if not SOURCE_CLAIMS <= {j["name"] for j in jobs if j.get("conclusion") == "success"}:
        raise ValueError("Candidate source proof lacks required claims")
    git("merge-base", "--is-ancestor", source, "HEAD")
    ownership = coordinated_release.load_ownership()
    verified = coordinated_release.verify_workspace_versions(ownership)
    metadata_paths = {f".release/releases/{verified['tag']}.md"}
    if verified["tag"] == "v1.0.0":
        coordinated_release.verify_rc_promotion(ownership)
        metadata_paths.add(coordinated_release.PROMOTION_RECORD)
    coordinated_release.verify_normalization_delta(
        ownership,
        source=source,
        subject=git("rev-parse", "HEAD"),
        version=verified["version"],
        metadata_paths=metadata_paths,
        consume_changesets=True,
    )


def qualify_source(repository, source, *, timeout=3600, clock=time.monotonic, sleep=time.sleep):
    """Require exact-source exhaustive CI before any candidate preparation effect."""
    if not re.fullmatch(r"[0-9a-f]{40}", source):
        raise ValueError("Source qualification requires a full commit SHA")
    reason = f"release-source-{source}-{uuid.uuid4().hex}"
    run(
        "gh",
        "workflow",
        "run",
        "ci.yml",
        "--repo",
        repository,
        "--ref",
        "master",
        "-f",
        f"expected_head_sha={source}",
        "-f",
        f"reason={reason}",
    )
    deadline = clock() + timeout
    while clock() < deadline:
        runs = api(repository, "actions/workflows/ci.yml/runs?event=workflow_dispatch&per_page=100")["workflow_runs"]
        matches = [
            r
            for r in runs
            if r.get("display_title") == f"CI / {reason}"
            and r.get("path") == ".github/workflows/ci.yml"
            and r.get("event") == "workflow_dispatch"
            and (r.get("head_repository") or {}).get("full_name") == repository
        ]
        if len(matches) > 1:
            raise ValueError("Ambiguous exact-source qualification run")
        if matches and matches[0].get("head_sha") != source:
            raise ValueError("Master moved before exact-source dispatch; no candidate generated")
        if matches and matches[0]["status"] == "completed":
            result = matches[0]
            if result["conclusion"] != "success":
                raise ValueError(f"Source qualification failed before candidate generation: {result['html_url']}")
            jobs = api(repository, f"actions/runs/{result['id']}/jobs?per_page=100")["jobs"]
            required = SOURCE_CLAIMS
            passed = {job["name"] for job in jobs if job.get("conclusion") == "success"}
            if not required <= passed:
                raise ValueError("Source qualification lacks required aggregate evidence")
            return {"source_commit": source, "run_id": result["id"], "url": result["html_url"], "status": "passed"}
        sleep(min(15, max(0, deadline - clock())))
    raise ValueError("Exact-source qualification timed out before candidate generation")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage", choices=("admit", "build", "compose", "check-published", "qualify-source", "candidate-admission"))
    parser.add_argument("--tag", default=os.environ.get("RELEASE_TAG"))
    parser.add_argument("--source", default=os.environ.get("EXPECTED_SOURCE_COMMIT", ""))
    parser.add_argument("--release-class", default=os.environ.get("RELEASE_CLASS", "stable"))
    parser.add_argument("--repository", default=os.environ.get("GITHUB_REPOSITORY"))
    parser.add_argument("--github-output", type=Path)
    parser.add_argument("--source-run-id", default=os.environ.get("SOURCE_RUN_ID"))
    args = parser.parse_args()
    if args.stage == "qualify-source":
        result = qualify_source(args.repository, args.source)
        print(json.dumps(result))
        if args.github_output:
            with args.github_output.open("a", encoding="utf-8") as handle:
                handle.write(f"source_run_id={result['run_id']}\n")
    elif args.stage == "candidate-admission":
        candidate_admission(args.repository, args.source, args.source_run_id)
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
