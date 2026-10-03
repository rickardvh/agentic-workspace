"""Project admitted RC/stable artifacts into registries without rebuilding them.

Only a registry 404 establishes absence. Transport failures and mismatched immutable
bytes stop recovery. Upload credentials and effects belong to the workflow jobs.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import quote, urlparse
from urllib.request import Request, urlopen

import coordinated_release
from first_contact import journey


def fetch(url, *, missing=False, accept=None):
    headers = {"User-Agent": "agentic-workspace-release (github.com/rickardvh/agentic-workspace)"}
    if accept:
        headers["Accept"] = accept
    request = Request(url, headers=headers)
    try:
        with urlopen(request, timeout=60) as response:
            return response.read()
    except HTTPError as error:
        if error.code == 404 and missing:
            return None
        raise


def json_response(url, *, accept=None):
    data = fetch(url, missing=True, accept=accept)
    return None if data is None else json.loads(data)


def verify_public_install(release, receipt_bytes, promotion, *, version, source, repository):
    """Verify immutable stable install admission without creating a latest projection."""
    tag = f"v{version}"
    identity = coordinated_release.release_identity(tag)
    if (
        identity["release_class"] != "stable"
        or release.get("tag_name") != tag
        or release.get("draft") is not False
        or release.get("prerelease") is not False
    ):
        raise ValueError("Public subject requires the selected published stable release")
    receipt = json.loads(receipt_bytes)
    admitted = promotion.get("artifacts", {})
    if (
        promotion.get("kind") != "agentic-workspace/support-bearing-promotion/v1"
        or promotion.get("status") != "passed"
        or promotion.get("source_commit") != source
        or admitted.get("distribution-install-readiness.json") != "sha256:" + hashlib.sha256(receipt_bytes).hexdigest()
        or receipt.get("kind") != "agentic-workspace/distribution-install-readiness/v1"
        or receipt.get("status") != "passed"
        or receipt.get("version") != version
    ):
        raise ValueError("Public release identity or accepted install receipt mismatch")
    artifact = receipt.get("artifact", {})
    name = artifact.get("name", "")
    base = f"https://github.com/{repository}/releases/download/{tag}/"
    if (
        not name
        or Path(name).name != name
        or "/" in name
        or "\\" in name
        or artifact.get("url") != base + name
        or admitted.get(name) != "sha256:" + str(artifact.get("sha256"))
        or name not in {item["name"] for item in release["assets"]}
    ):
        raise ValueError("Install artifact is not in the accepted public release")


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def fetch_admitted(dist, tag, repository):
    """Recover immutable GitHub bytes and their original publisher before credentials."""
    identity = coordinated_release.release_identity(tag)
    dist.mkdir()
    subprocess.run(["gh", "release", "download", tag, "--repo", repository, "--dir", str(dist)], check=True, stdout=sys.stderr)
    manifest_name = (
        "agentic-workspace-release-manifest.json" if identity["support_bearing"] else "agentic-workspace-preview-release-manifest.json"
    )
    manifest = json.loads((dist / manifest_name).read_text())
    legacy = "release.yml" if identity["support_bearing"] else "preview-release.yml"
    publisher = manifest.get("publisher_workflow", legacy)
    allowed = {"release.yml"} if identity["support_bearing"] else {"release.yml", "preview-release.yml"}
    if publisher not in allowed:
        raise ValueError("Unrecognized immutable release publisher")
    # The manifest is itself attested by the same narrowly admitted producer.
    subjects = [p for p in dist.iterdir() if p.suffix in {".whl", ".gz", ".tgz", ".crate"} or p.name.endswith("release-manifest.json")]
    for artifact in subjects:
        subprocess.run(
            [
                "gh",
                "attestation",
                "verify",
                str(artifact),
                "--repo",
                repository,
                "--signer-workflow",
                f"{repository}/.github/workflows/{publisher}",
            ],
            check=True,
            stdout=sys.stderr,
        )


def npm_dist_tag(identity):
    """Keep the newest admitted RC as the default until stable v1 replaces it."""
    if identity["release_class"] not in {"release-candidate", "stable"}:
        raise ValueError("Exploratory previews are not npm registry releases")
    return "latest"


def admitted_artifacts(dist, tag, source):
    identity = coordinated_release.release_identity(tag)
    if identity["release_class"] not in {"stable", "release-candidate"}:
        raise ValueError("Exploratory previews are not registry releases")
    manifest_name = (
        "agentic-workspace-release-manifest.json" if identity["support_bearing"] else "agentic-workspace-preview-release-manifest.json"
    )
    manifest = json.loads((dist / manifest_name).read_text())
    if manifest.get("tag") != tag or manifest.get("version") != identity["version"]:
        raise ValueError("Registry subject does not match release identity")
    if manifest.get("source_commit", manifest.get("artifact_commit")) != source:
        raise ValueError("Registry source does not match admitted subject")
    if identity["support_bearing"]:
        promotion = json.loads((dist / "support-bearing-promotion.json").read_text())
        if promotion.get("status") != "passed" or promotion.get("source_commit") != source:
            raise ValueError("Stable registry publication requires exact support admission")
    elif manifest.get("support_bearing") is not False or (dist / "support-bearing-promotion.json").exists():
        raise ValueError("RC registry subject must remain non-support-bearing")
    security = json.loads((dist / "security-supply-chain-readiness.json").read_text())
    if security.get("status") != "ready" or security.get("subject", {}).get("source_identity") != source:
        raise ValueError("Missing successful security admission")
    checksums = {}
    for line in (dist / "SHA256SUMS").read_text().splitlines():
        digest, name = line.split("  ", 1)
        if Path(name).name != name or name in checksums:
            raise ValueError("Unsafe or duplicate checksum asset")
        checksums[name] = digest
    for name, digest in checksums.items():
        if sha256(dist / name) != digest:
            raise ValueError(f"Admitted asset changed: {name}")
    for name in (
        manifest_name,
        "security-supply-chain-readiness.json",
        "distribution-install-readiness.json",
        "redistributable-package-readiness.json",
    ):
        if name not in checksums:
            raise ValueError(f"Missing admitted receipt: {name}")
    packages = {(p["ecosystem"], p["name"]): p for p in manifest["packages"]}
    if len(manifest["packages"]) != 2 or set(packages) != {("python", "agentic-workspace"), ("npm", "@agentic-workspace/workspace-cli")}:
        raise ValueError("Registry projection requires exactly the two shipped language packages")
    result = []
    for (ecosystem, name), package in packages.items():
        if package["version"] != identity["package_versions"][ecosystem]:
            raise ValueError("Package version diverges from canonical ecosystem mapping")
        artifacts = [*package.get("wheels", [package.get("wheel")]), package["sdist"]] if ecosystem == "python" else [package["tarball"]]
        for artifact in artifacts:
            if checksums.get(artifact["asset"]) != artifact["sha256"]:
                raise ValueError("Package digest not admitted by release manifest")
            result.append({"ecosystem": ecosystem, "name": name, "version": package["version"], **artifact})
    for row in result:
        row["release_assets"] = sorted(other["asset"] for other in result if other["ecosystem"] == row["ecosystem"])
    return identity, result


def observe(artifact, dist, *, get=json_response, download=fetch):
    name, version = artifact["name"], artifact["version"]
    if artifact["ecosystem"] == "python":
        metadata = get(f"https://pypi.org/pypi/{quote(name, safe='')}/{quote(version, safe='')}/json")
        if metadata is None:
            return "absent"
        if metadata["info"]["name"] != name or metadata["info"]["version"] != version:
            raise ValueError("PyPI immutable identity mismatch")
        if any(row["filename"] not in artifact["release_assets"] for row in metadata["urls"]):
            raise ValueError("PyPI version contains artifacts outside the admitted release")
        files = [row for row in metadata["urls"] if row["filename"] == artifact["asset"]]
        if not files:
            return "absent"
        if len(files) != 1 or files[0].get("yanked") or files[0]["digests"]["sha256"] != artifact["sha256"]:
            raise ValueError("PyPI immutable file conflict")
        url, host = files[0]["url"], "files.pythonhosted.org"
    else:
        metadata = get(f"https://registry.npmjs.org/{quote(name, safe='')}/{quote(version, safe='')}")
        if metadata is None:
            return "absent"
        expected_integrity = "sha512-" + base64.b64encode(hashlib.sha512((dist / artifact["asset"]).read_bytes()).digest()).decode()
        if metadata.get("name") != name or metadata.get("version") != version or metadata["dist"].get("integrity") != expected_integrity:
            raise ValueError("npm immutable identity/integrity conflict")
        url, host = metadata["dist"]["tarball"], "registry.npmjs.org"
    parsed = urlparse(url)
    if parsed.scheme != "https" or parsed.hostname != host or parsed.username or parsed.password:
        raise ValueError("Unexpected registry artifact origin")
    if hashlib.sha256(download(url)).hexdigest() != artifact["sha256"]:
        raise ValueError("Public registry bytes differ from admitted artifact")
    return "matching"


def python_index_ready(artifacts, *, get=None):
    """The release JSON API and installer index can propagate independently."""
    python = [row for row in artifacts if row["ecosystem"] == "python"]
    if not python:
        return True
    get = get or json_response
    index = get(f"https://pypi.org/simple/{quote(python[0]['name'], safe='')}/", accept="application/vnd.pypi.simple.v1+json")
    if index is None:
        return False
    ready = True
    for artifact in python:
        files = [row for row in index["files"] if row["filename"] == artifact["asset"]]
        if not files:
            ready = False
        elif len(files) != 1 or files[0].get("yanked") or files[0]["hashes"].get("sha256") != artifact["sha256"]:
            raise ValueError("PyPI installer index conflicts with admitted artifact")
    return ready


def smoke(identity):
    with tempfile.TemporaryDirectory(prefix="aw-registry-consumer-") as directory:
        workspace = Path(directory)
        root = workspace / "node-consumer"
        root.mkdir()
        env = {
            key: value
            for key, value in os.environ.items()
            if key not in {"PYTHONPATH", "AGENTIC_WORKSPACE_CORE_BINARY", "NODE_AUTH_TOKEN", "NPM_TOKEN"}
        }
        # Installation storage is outside every repository scored by the journey.
        env["NPM_CONFIG_CACHE"] = str(workspace / "npm-cache")
        env["UV_TOOL_DIR"] = str(workspace / "tools")
        env["UV_TOOL_BIN_DIR"] = str(workspace / "tool-bin")
        python = workspace / "tools/agentic-workspace" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
        subprocess.run(
            [
                shutil.which("uv"),
                "tool",
                "install",
                "--python",
                sys.executable,
                "--no-cache",
                "--no-build",
                "--index-url",
                "https://pypi.org/simple",
                "agentic-workspace==" + identity["package_versions"]["python"],
            ],
            check=True,
            env=env,
        )
        subprocess.run(
            [
                str(python),
                "-I",
                "-c",
                "from agentic_workspace import start, invoke\nassert start({'target':'.'})['decision_packet']['status']=='direct'\nassert invoke({'target':'.','invocation':{}})['effect_outcome']['status']=='rejected-before-effect'",
            ],
            cwd=root,
            env=env,
            check=True,
        )
        (root / "package.json").write_text('{"private":true}')
        subprocess.run(
            [
                shutil.which("npm"),
                "install",
                "--ignore-scripts",
                "--no-audit",
                "--no-fund",
                "--registry=https://registry.npmjs.org",
                "@agentic-workspace/workspace-cli@" + identity["package_versions"]["npm"],
            ],
            cwd=root,
            env=env,
            check=True,
        )
        subprocess.run(
            [
                shutil.which("node"),
                "--input-type=module",
                "-e",
                "import {start,invoke} from '@agentic-workspace/workspace-cli'; if(start({target:'.'}).decision_packet.status!=='direct') throw Error('native start failed'); if(invoke({target:'.',invocation:{}}).effect_outcome.status!=='rejected-before-effect') throw Error('invalid invocation accepted');",
            ],
            cwd=root,
            env=env,
            check=True,
        )
        # Reuse these already-installed public packages for the human journey.
        subprocess.run(["git", "init", "-q", str(root)], check=True, env=env)
        npm = shutil.which("npm")
        local_env = dict(env)
        local_env["PATH"] = os.pathsep.join([str(Path(shutil.which("node")).parent), str(Path(shutil.which("git")).parent)])
        if shutil.which("agentic-workspace", path=local_env["PATH"]):
            raise ValueError("npm-local journey exposes a global AW executable")
        journey([npm, "exec", "--no", "--", "agentic-workspace"], root, local_env)
        python_repo = workspace / "python-consumer"
        python_repo.mkdir()
        subprocess.run(["git", "init", "-q", str(python_repo)], check=True, env=env)
        executable = python.parent / ("agentic-workspace.exe" if os.name == "nt" else "agentic-workspace")
        journey([str(executable)], python_repo, env)
        prefix = workspace / "npm-global"
        subprocess.run(
            [
                npm,
                "install",
                "--global",
                "--prefix",
                str(prefix),
                "--ignore-scripts",
                "--no-audit",
                "--no-fund",
                "@agentic-workspace/workspace-cli@" + identity["package_versions"]["npm"],
            ],
            check=True,
            env=env,
        )
        global_repo = workspace / "global-consumer"
        global_repo.mkdir()
        subprocess.run(["git", "init", "-q", str(global_repo)], check=True, env=env)
        global_env = dict(local_env)
        global_env["PATH"] = str(prefix if os.name == "nt" else prefix / "bin") + os.pathsep + local_env["PATH"]
        executable = shutil.which("agentic-workspace", path=global_env["PATH"])
        if not executable or not Path(executable).is_relative_to(prefix):
            raise ValueError("Global invocation did not resolve to the isolated public install")
        journey([executable], global_repo, global_env)


def converge(
    artifacts, dist, *, timeout=300, observe_artifact=observe, channel_ready=None, index_ready=None, clock=time.monotonic, sleep=time.sleep
):
    """Wait for immutable bytes and public indexes; conflicts and transport errors fail immediately."""
    if timeout < 0 or timeout > 900:
        raise ValueError("Registry convergence timeout must be between zero and 900 seconds")
    deadline = clock() + timeout
    delay = 2
    while True:
        observations = [{**row, "status": observe_artifact(row, dist)} for row in artifacts]
        absent = [row["asset"] for row in observations if row["status"] == "absent"]
        channel_matches = channel_ready is None or channel_ready()
        index_matches = index_ready is None or index_ready()
        if not absent and channel_matches and index_matches:
            return observations
        diagnostic = (
            f"absent artifacts: {absent}; channel matching: {channel_matches}; "
            f"installer index matching: {index_matches}"
        )
        remaining = deadline - clock()
        if remaining <= 0:
            raise ValueError(f"Registry convergence timed out; {diagnostic}")
        print(f"Registry propagation pending; {diagnostic}", file=sys.stderr)
        sleep(min(delay, remaining))
        delay = min(delay * 2, 30)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tag", required=True)
    parser.add_argument("--source", required=True)
    parser.add_argument("--artifact-dir", type=Path, required=True)
    parser.add_argument("--pending", type=Path)
    parser.add_argument("--verify", action="store_true")
    parser.add_argument("--receipt", type=Path)
    parser.add_argument("--convergence-seconds", type=int, default=900)
    parser.add_argument("--fetch", action="store_true")
    parser.add_argument("--repository", default=os.environ.get("GITHUB_REPOSITORY"))
    args = parser.parse_args()
    if args.fetch:
        fetch_admitted(args.artifact_dir, args.tag, args.repository)
        admitted_artifacts(args.artifact_dir, args.tag, args.source)
        return
    identity, artifacts = admitted_artifacts(args.artifact_dir, args.tag, args.source)
    # Observe every package before staging any upload; a conflict cannot leave a
    # partially populated upload directory that a later step might consume.
    if args.verify:
        npm_tag = npm_dist_tag(identity)

        def channel_ready():
            tags = json_response("https://registry.npmjs.org/-/package/%40agentic-workspace%2Fworkspace-cli/dist-tags")
            return bool(tags and tags.get(npm_tag) == identity["package_versions"]["npm"])

        observations = converge(
            artifacts,
            args.artifact_dir,
            timeout=args.convergence_seconds,
            channel_ready=channel_ready,
            index_ready=lambda: python_index_ready(artifacts),
        )
        smoke(identity)
        receipt = {
            "kind": "agentic-workspace/registry-publication/v1",
            "status": "passed",
            **identity,
            "source_commit": args.source,
            "artifacts": observations,
            "clean_public_install": "passed",
        }
        args.receipt.write_text(json.dumps(receipt, indent=2) + "\n")
    else:
        observations = [{**row, "status": observe(row, args.artifact_dir)} for row in artifacts]
        absent = [row for row in observations if row["status"] == "absent"]
        args.pending.mkdir()  # Fresh per attempt; never reuse stale pending uploads.
        for ecosystem in ("python", "npm"):
            (args.pending / ecosystem).mkdir()
        for row in absent:
            shutil.copyfile(args.artifact_dir / row["asset"], args.pending / row["ecosystem"] / row["asset"])
        print("python_pending=" + str(any(row["ecosystem"] == "python" for row in absent)).lower())
        print("npm_pending=" + str(any(row["ecosystem"] == "npm" for row in absent)).lower())
        print("npm_tag=" + npm_dist_tag(identity))


if __name__ == "__main__":
    main()
