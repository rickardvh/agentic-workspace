"""Package the existing Rust pair as self-contained, coordinated Cargo sources.

The staging projection relocates compile-time includes without changing their
bytes or expressions. It is not another runtime or crate/version authority.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import tarfile
import tempfile
import tomllib
from pathlib import Path

import coordinated_release
from first_contact import journey
from registry_release import fetch, json_response, sha256

ROOT = Path(__file__).resolve().parents[3]
INCLUDE = re.compile(r'(include_(?:str|bytes)!\(\s*)"([^"]+)"(\s*\))')


def stage_crate(root, crate, destination, source):
    origin = root / crate["path"]
    shutil.copytree(origin / "src", destination / "src")
    manifest = (origin / "Cargo.toml").read_text()
    manifest = manifest.replace("[lints]\nworkspace = true", '[lints.rust]\nunsafe_code = "forbid"')
    manifest += "\n[workspace]\n"
    (destination / "Cargo.toml").write_text(manifest)
    shutil.copy2(root / "Cargo.lock", destination / "Cargo.lock")
    shutil.copy2(root / "LICENSE", destination / "LICENSE")
    shutil.copy2(root / "README.md", destination / "README.md")
    inputs = {}

    def copy_input(path):
        path = path.resolve()
        relative = path.relative_to(root.resolve())
        target = destination / "_inputs" / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, target)
        inputs[relative.as_posix()] = sha256(path)
        return target

    for source_file in origin.rglob("*.rs"):
        relative = source_file.relative_to(origin)

        # Crate-local producer identity strings remain literal source text.
        def relocate(match):
            dependency = (source_file.parent / match[2]).resolve()
            if dependency.is_relative_to(origin.resolve()) and dependency.suffix != ".rs":
                # Only src/ is copied wholesale. Crate-local contracts outside
                # that subtree still need an explicit compile-input projection.
                if (destination / dependency.relative_to(origin.resolve())).is_file():
                    return match[0]
            target = copy_input(dependency)
            relocated = os.path.relpath(target, (destination / relative).parent).replace("\\", "/")
            return match[1] + json.dumps(relocated) + match[3]

        text = INCLUDE.sub(relocate, source_file.read_text())
        if relative.as_posix() == "build.rs":
            old = '.join("../..")'
            if text.count(old) != 1:
                raise ValueError("Unknown Cargo payload build layout")
            text = text.replace(old, '.join("_inputs")')
            declaration = root / "src/core/contracts/workspace_surfaces.json"
            copy_input(declaration)
            contract = json.loads(declaration.read_text())
            for reference in contract["payload_files"]:
                copy_input(root / "src/core/payload" / reference)
            for reference in contract["derivation"]["portable_sources"]:
                copy_input(root / reference)
        output = destination / relative
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(text)
    (destination / "release-source.json").write_text(
        json.dumps(
            {
                "kind": "agentic-workspace/cargo-source/v1",
                "source_commit": source,
                "crate": crate["name"],
                "compile_inputs": inputs,
                "projection_sha256": sha256(Path(__file__)),
            },
            indent=2,
            sort_keys=True,
        )
        + "\n"
    )
    # Explicit inclusion preserves hidden .agentic-workspace compile resources;
    # Cargo's implicit inventory intentionally excludes hidden directories.
    files = sorted(path.relative_to(destination).as_posix() for path in destination.rglob("*") if path.is_file())
    manifest = manifest.replace("[lints.rust]", "include = " + json.dumps(files) + "\n\n[lints.rust]")
    (destination / "Cargo.toml").write_text(manifest)
    subprocess.run(
        ["cargo", "metadata", "--offline", "--format-version", "1", "--manifest-path", str(destination / "Cargo.toml")],
        check=True,
        capture_output=True,
    )

    # Cargo prunes the workspace lock for a standalone crate. It may not change
    # a third-party version/source/checksum during that packaging projection.
    def dependencies(path):
        return {
            (row["name"], row["version"], row["source"], row.get("checksum"))
            for row in tomllib.loads(path.read_text())["package"]
            if "source" in row
        }

    if not dependencies(destination / "Cargo.lock").issubset(dependencies(root / "Cargo.lock")):
        raise ValueError("Standalone crate changed locked third-party resolution")


def build(output, staging, *, verify=True):
    ownership = coordinated_release.load_ownership()
    version = coordinated_release.npm_version(tomllib.loads((ROOT / "pyproject.toml").read_text())["project"]["version"])
    source = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    subprocess.run(["cargo", "fetch", "--locked"], cwd=ROOT, check=True)
    staging.mkdir()
    output.mkdir(exist_ok=True)
    entries = []
    for crate in ownership["cargo_packages"]:
        destination = staging / crate["name"]
        if tomllib.loads((ROOT / crate["path"] / "Cargo.toml").read_text())["package"]["version"] != version:
            raise ValueError("Cargo version diverges from coordinated release")
        stage_crate(ROOT, crate, destination, source)
        args = ["cargo", "package", "--locked", "--allow-dirty", "--manifest-path", str(destination / "Cargo.toml")]
        if not verify:
            args.append("--no-verify")
        subprocess.run(args, check=True)
        target = Path(os.environ.get("CARGO_TARGET_DIR", destination / "target"))
        archive = target / "package" / f"{crate['name']}-{version}.crate"
        final = output / archive.name
        if final.exists() and sha256(final) != sha256(archive):
            raise ValueError("Refusing to replace different admitted Cargo bytes")
        shutil.copyfile(archive, final)
        entries.append({"name": crate["name"], "version": version, "asset": final.name, "sha256": sha256(final), "binary": crate["binary"]})
    receipt = {
        "kind": "agentic-workspace/cargo-release/v1",
        "source_commit": source,
        "version": version,
        "package_build": "passed" if verify else "not-run",
        "paired_install": "not-run",
        "packages": entries,
    }
    (output / "cargo-release-manifest.json").write_text(json.dumps(receipt, indent=2) + "\n")
    return receipt


def admitted_manifest(dist, ownership, source, version):
    if not ownership.get("cargo_packages"):
        return None
    receipt = json.loads((dist / "cargo-release-manifest.json").read_text())
    if receipt["source_commit"] != source or receipt["version"] != coordinated_release.npm_version(version):
        raise ValueError("Cargo archive subject/version mismatch")
    if receipt["package_build"] != "passed" or receipt["paired_install"] != "passed":
        raise ValueError("Cargo package/build and paired installation proof required")
    if [p["name"] for p in receipt["packages"]] != [p["name"] for p in ownership["cargo_packages"]]:
        raise ValueError("Unexpected Cargo package set/order")
    for crate in receipt["packages"]:
        if (
            crate["version"] != receipt["version"]
            or Path(crate["asset"]).name != crate["asset"]
            or sha256(dist / crate["asset"]) != crate["sha256"]
        ):
            raise ValueError("Cargo package identity/digest mismatch")
    return {
        "manifest": {"asset": "cargo-release-manifest.json", "sha256": sha256(dist / "cargo-release-manifest.json")},
        "packages": receipt["packages"],
    }


def observe(crate, *, get=json_response, download=fetch):
    metadata = get(f"https://crates.io/api/v1/crates/{crate['name']}/{crate['version']}")
    if metadata is None:
        return "absent"
    version = metadata["version"]
    if (
        version["crate"] != crate["name"]
        or version["num"] != crate["version"]
        or version["checksum"] != crate["sha256"]
        or version.get("yanked")
    ):
        raise ValueError("Immutable crates.io identity/checksum conflict")
    data = download(f"https://static.crates.io/crates/{crate['name']}/{crate['name']}-{crate['version']}.crate")
    if hashlib.sha256(data).hexdigest() != crate["sha256"]:
        raise ValueError("Public crate bytes do not match admitted source archive")
    return "matching"


def install_pair(packages, home, *, staging=None):
    env = {key: value for key, value in os.environ.items() if key not in {"AGENTIC_WORKSPACE_CORE_BINARY", "CARGO_REGISTRY_TOKEN"}}
    env["CARGO_HOME"] = str(home / "cargo-home")
    for crate in packages:
        command = ["cargo", "install", "--locked", "--root", str(home / "installed")]
        if staging:
            command += ["--path", str(staging / f"{crate['name']}-{crate['version']}")]
        else:
            command += [crate["name"], "--version", "=" + crate["version"], "--registry", "crates-io"]
        subprocess.run(command, check=True, env=env)
        if staging is None:
            archives = list((home / "cargo-home/registry/cache").glob(f"*/{crate['asset']}"))
            if len(archives) != 1 or sha256(archives[0]) != crate["sha256"]:
                raise ValueError("Cargo installed source bytes differ from admitted archive")
    consumer = home / "consumer"
    consumer.mkdir()
    suffix = ".exe" if os.name == "nt" else ""
    binaries = home / "installed/bin"
    assert all((binaries / (crate["binary"] + suffix)).is_file() for crate in packages)
    subprocess.run(["git", "init", "-q", str(consumer)], check=True, env=env)
    journey([str(binaries / ("agentic-workspace" + suffix))], consumer, env)
    env["PATH"] = ""
    result = subprocess.check_output(
        [str(binaries / ("agentic-workspace" + suffix)), "start", "--target", str(consumer), "--task", "Inspect", "--format", "json"],
        env=env,
        text=True,
    )
    if json.loads(result)["decision_packet"]["status"] != "direct":
        raise ValueError("Installed Cargo pair did not execute native startup")
    rejected = subprocess.run(
        [str(binaries / ("agentic-workspace" + suffix)), "invoke", "--target", str(consumer), "--input", "-"],
        input="{}",
        text=True,
        capture_output=True,
        env=env,
    )
    if rejected.returncode != 0 or json.loads(rejected.stdout).get("effect_outcome", {}).get("status") != "rejected-before-effect":
        raise ValueError("Cargo pair accepted an invalid invocation")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("operation", choices=["build", "publish", "verify", "install-staged"])
    parser.add_argument("--artifact-dir", type=Path, required=True)
    parser.add_argument("--staging", type=Path)
    parser.add_argument("--tag")
    parser.add_argument("--no-verify", action="store_true", help="Repackage for pre-upload byte comparison only; grants no build proof")
    args = parser.parse_args()
    if args.operation == "build":
        build(args.artifact_dir.resolve(), args.staging.resolve(), verify=not args.no_verify)
        return
    manifest = json.loads((args.artifact_dir / "cargo-release-manifest.json").read_text())
    if args.operation == "install-staged":
        with tempfile.TemporaryDirectory(prefix="aw-cargo-install-") as home:
            home = Path(home)
            sources = home / "sources"
            sources.mkdir()
            for crate in manifest["packages"]:
                archive = args.artifact_dir / crate["asset"]
                if sha256(archive) != crate["sha256"]:
                    raise ValueError("Cargo archive changed before installation")
                with tarfile.open(archive) as bundle:
                    bundle.extractall(sources, filter="data")
            install_pair(manifest["packages"], home, staging=sources)
        manifest["paired_install"] = "passed"
        (args.artifact_dir / "cargo-release-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
        return
    # Reuse the language publisher's exact release/security/support admission;
    # Cargo is an additional artifact projection of that same release subject.
    from registry_release import admitted_artifacts

    source = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    identity, _ = admitted_artifacts(args.artifact_dir, args.tag, source)
    ownership = coordinated_release.load_ownership()
    admitted_manifest(args.artifact_dir, ownership, source, identity["version"])
    if (
        manifest["source_commit"] != source
        or manifest["version"] != identity["package_versions"]["cargo"]
        or manifest["package_build"] != "passed"
    ):
        raise ValueError("Cargo proof is not for the admitted release subject")
    if [row["name"] for row in manifest["packages"]] != [row["name"] for row in ownership["cargo_packages"]]:
        raise ValueError("Cargo publication order/set differs from release ownership")
    for crate in manifest["packages"]:
        if sha256(args.artifact_dir / crate["asset"]) != crate["sha256"]:
            raise ValueError("Cargo artifact changed after admission")
    # Check all conflicts before the first possible upload.
    state = [observe(crate) for crate in manifest["packages"]]
    if args.operation == "publish":
        for index, (crate, status) in enumerate(zip(manifest["packages"], state, strict=True)):
            if status == "matching":
                continue
            if any(observe(prior) != "matching" for prior in manifest["packages"][:index]):
                raise ValueError("Required paired predecessor is not publicly available")
            stage = args.staging / crate["name"]
            # Repackage first and compare before a credential-bearing operation.
            subprocess.run(
                ["cargo", "package", "--locked", "--allow-dirty", "--no-verify", "--manifest-path", str(stage / "Cargo.toml")], check=True
            )
            target = Path(os.environ.get("CARGO_TARGET_DIR", stage / "target"))
            if sha256(target / "package" / crate["asset"]) != crate["sha256"]:
                raise ValueError("Publication packaging changed admitted crate bytes")
            subprocess.run(
                ["cargo", "publish", "--locked", "--allow-dirty", "--no-verify", "--manifest-path", str(stage / "Cargo.toml")], check=True
            )
            if observe(crate) != "matching":
                raise ValueError("Partial publication: exact predecessor not yet visible; reobserve before continuing")
    else:
        if "absent" in state:
            raise ValueError("Cargo registry publication incomplete")
        with tempfile.TemporaryDirectory(prefix="aw-public-cargo-") as home:
            install_pair(manifest["packages"], Path(home))
        (args.artifact_dir / "cargo-registry-publication.json").write_text(
            json.dumps(
                {
                    "kind": "agentic-workspace/cargo-registry-publication/v1",
                    "status": "passed",
                    **identity,
                    "source_commit": source,
                    "packages": manifest["packages"],
                    "clean_public_install": "passed",
                },
                indent=2,
            )
            + "\n"
        )


if __name__ == "__main__":
    main()
