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
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import quote, urlparse
from urllib.request import Request, urlopen

import coordinated_release


def fetch(url, *, missing=False):
    request = Request(url, headers={"User-Agent": "agentic-workspace-release (github.com/rickardvh/agentic-workspace)"})
    try:
        with urlopen(request, timeout=60) as response:
            return response.read()
    except HTTPError as error:
        if error.code == 404 and missing:
            return None
        raise


def json_response(url):
    data = fetch(url, missing=True)
    return None if data is None else json.loads(data)


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


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


def smoke(identity):
    with tempfile.TemporaryDirectory(prefix="aw-registry-consumer-") as directory:
        root = Path(directory)
        env = {
            key: value
            for key, value in os.environ.items()
            if key not in {"PYTHONPATH", "AGENTIC_WORKSPACE_CORE_BINARY", "NODE_AUTH_TOKEN", "NPM_TOKEN"}
        }
        env["NPM_CONFIG_CACHE"] = str(root / "npm-cache")
        subprocess.run([sys.executable, "-m", "venv", str(root / "venv")], check=True)
        python = root / "venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
        subprocess.run(
            [
                str(python),
                "-m",
                "pip",
                "--isolated",
                "install",
                "--no-cache-dir",
                "--no-deps",
                "--only-binary=:all:",
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


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tag", required=True)
    parser.add_argument("--source", required=True)
    parser.add_argument("--artifact-dir", type=Path, required=True)
    parser.add_argument("--pending", type=Path)
    parser.add_argument("--verify", action="store_true")
    parser.add_argument("--receipt", type=Path)
    args = parser.parse_args()
    identity, artifacts = admitted_artifacts(args.artifact_dir, args.tag, args.source)
    # Observe every package before staging any upload; a conflict cannot leave a
    # partially populated upload directory that a later step might consume.
    observations = [{**row, "status": observe(row, args.artifact_dir)} for row in artifacts]
    absent = [row for row in observations if row["status"] == "absent"]
    if args.verify:
        if absent:
            raise ValueError("Registry publication is incomplete; reobserve before retrying upload")
        npm_tag = "rc" if identity["release_class"] == "release-candidate" else "latest"
        tags = json_response("https://registry.npmjs.org/-/package/%40agentic-workspace%2Fworkspace-cli/dist-tags")
        if not tags or tags.get(npm_tag) != identity["package_versions"]["npm"]:
            raise ValueError("npm channel differs from this release; inspect channel history before a separate tag repair")
        if npm_tag == "rc" and tags.get("latest") == identity["package_versions"]["npm"]:
            raise ValueError("RC must not be npm latest")
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
        args.pending.mkdir()  # Fresh per attempt; never reuse stale pending uploads.
        for ecosystem in ("python", "npm"):
            (args.pending / ecosystem).mkdir()
        for row in absent:
            shutil.copyfile(args.artifact_dir / row["asset"], args.pending / row["ecosystem"] / row["asset"])
        print("python_pending=" + str(any(row["ecosystem"] == "python" for row in absent)).lower())
        print("npm_pending=" + str(any(row["ecosystem"] == "npm" for row in absent)).lower())
        print("npm_tag=" + ("rc" if identity["release_class"] == "release-candidate" else "latest"))


if __name__ == "__main__":
    main()
