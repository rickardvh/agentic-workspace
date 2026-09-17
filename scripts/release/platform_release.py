"""Build, combine and exercise the complete compiler-free release platform set."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import shutil
import subprocess
import sys
import tarfile
import tempfile
import tomllib
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = "platform-release-manifest.json"


def platforms():
    return json.loads((ROOT / ".github/release-platforms.json").read_text())["platforms"]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def asset(path):
    return {"asset": path.name, "sha256": digest(path)}


def run(args, **kwargs):
    args = [str(arg) for arg in args]
    args[0] = shutil.which(args[0]) or args[0]
    return subprocess.run(args, check=True, **kwargs)


def current_platform():
    node_os = {"Windows": "win32", "Darwin": "darwin", "Linux": "linux"}[platform.system()]
    arch = {"amd64": "x64", "x86_64": "x64", "arm64": "arm64", "aarch64": "arm64"}[platform.machine().lower()]
    return next(row for row in platforms() if row["node_platform"] == node_os and row["node_arch"] == arch)


def primary(paths):
    """The old singular manifest field remains the explicit Linux x64 projection."""
    paths = list(paths)
    if len(paths) > 1:
        paths = [p for p in paths if p.name.endswith(("manylinux_2_39_x86_64.whl", "x86_64-unknown-linux-gnu.zip"))]
    if len(paths) != 1:
        raise ValueError("Missing unique primary release artifact")
    return paths[0]


def load(directory, *, require=True):
    path = directory / MANIFEST
    if not path.exists() and not require:
        return None
    data = json.loads(path.read_text())
    if data.get("kind") != "agentic-workspace/platform-release/v1":
        raise ValueError("Unsupported platform inventory")
    rows = data["platforms"]
    if len(rows) != len(platforms()) or {r["target"] for r in rows} != {r["target"] for r in platforms()}:
        raise ValueError("Incomplete or duplicate release platform set")
    for row in rows:
        expected = next(p for p in platforms() if p["target"] == row["target"])
        if any(row.get(k) != v for k, v in expected.items()):
            raise ValueError("Platform declaration mismatch")
        for key in ("wheel", "native_archive"):
            item = row[key]
            if Path(item["asset"]).name != item["asset"] or digest(directory / item["asset"]) != item["sha256"]:
                raise ValueError("Platform artifact digest mismatch")
    item = data["npm"]
    if Path(item["asset"]).name != item["asset"] or digest(directory / item["asset"]) != item["sha256"]:
        raise ValueError("Universal npm artifact digest mismatch")
    return data


def entries(data):
    return [item for row in data["platforms"] for item in (row["wheel"], row["native_archive"])]


def build(directory):
    import stage_native_npm

    directory.mkdir(parents=True, exist_ok=True)
    row = current_platform()
    run(["uv", "build", "--wheel", "--out-dir", directory], cwd=ROOT)
    if row["node_platform"] == "linux":
        from admit_linux_wheel import admit

        admit(directory)
    if row["target"] == "x86_64-unknown-linux-gnu":
        run(["uv", "build", "--sdist", "--out-dir", directory], cwd=ROOT)
    with tempfile.TemporaryDirectory(prefix="aw-platform-stage-") as tmp:
        package = stage_native_npm.stage(Path(tmp) / "npm")
        native = package / "src/native/bin"
        manifest = json.loads((native / "artifact.json").read_text())
        if manifest["rust_host"] != row["target"]:
            raise ValueError("Build runner does not match declared platform")
        archive = directory / f"agentic-workspace-native-{manifest['package_version']}-{row['target']}.zip"
        with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as bundle:
            for path in sorted(native.iterdir()):
                bundle.write(path, path.name)
            bundle.write(ROOT / "LICENSE", "LICENSE")
        run(["npm", "pack", "--pack-destination", directory], cwd=package)


def assemble(inputs, directory):
    """No cross compilation: combine exact paired bytes from each native builder."""
    directory.mkdir(parents=True, exist_ok=True)
    version = tomllib.loads((ROOT / "pyproject.toml").read_text())["project"]["version"]
    source = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    records = []
    with tempfile.TemporaryDirectory(prefix="aw-universal-npm-") as tmp:
        package = Path(tmp) / "package"
        for row in platforms():
            folder = inputs / ("platform-" + row["target"])
            (wheel,) = folder.glob("*.whl")
            (archive,) = folder.glob("*.zip")
            (tarball,) = folder.glob("*.tgz")
            with zipfile.ZipFile(archive) as native, zipfile.ZipFile(wheel) as python, tarfile.open(tarball) as npm:
                identity = json.loads(native.read("artifact.json"))
                py_identity = json.loads(python.read("agentic_workspace/_native/artifact.json"))
                npm_identity = json.load(npm.extractfile("package/src/native/bin/artifact.json"))
                if identity != npm_identity or any(
                    identity[k] != py_identity[k]
                    for k in (
                        "rust_host",
                        "rust_target",
                        "source_head",
                        "source_dirty",
                        "sha256",
                        "cli_sha256",
                        "rust_toolchain",
                        "package_version",
                    )
                ):
                    raise ValueError("Language artifacts do not share exact native identity")
                if (
                    identity["rust_host"] != row["target"]
                    or identity["package_version"] != version
                    or identity["source_head"] != source
                    or identity["source_dirty"]
                ):
                    raise ValueError("Platform build has wrong source, version or target")
                if not package.exists():
                    npm.extractall(tmp, filter="data")
                    shutil.rmtree(package / "src/native/bin")
                dest = package / "src/native/bin" / f"{row['node_platform']}-{row['node_arch']}"
                dest.mkdir(parents=True)
                suffix = ".exe" if row["node_platform"] == "win32" else ""
                for name, key in (("agentic-workspace-core", "sha256"), ("agentic-workspace", "cli_sha256")):
                    name += suffix
                    data = native.read(name)
                    if (
                        hashlib.sha256(data).hexdigest() != identity[key]
                        or python.read("agentic_workspace/_native/" + name) != data
                        or npm.extractfile("package/src/native/bin/" + name).read() != data
                    ):
                        raise ValueError("Platform binary pair mismatch")
                    (dest / name).write_bytes(data)
                    (dest / name).chmod(0o755)
                (dest / "artifact.json").write_text(json.dumps(identity))
            for path in (wheel, archive, *folder.glob("*.tar.gz")):
                shutil.copy2(path, directory / path.name)
            records.append({**row, "wheel": asset(wheel), "native_archive": asset(archive)})
        metadata = json.loads((package / "package.json").read_text())
        metadata["os"] = ["linux", "darwin", "win32"]
        metadata["cpu"] = ["x64", "arm64"]
        metadata["agenticWorkspace"]["nativeRuntime"].update(
            manifest="src/native/bin/<platform>-<arch>/artifact.json", support="declared release platforms"
        )
        (package / "package.json").write_text(json.dumps(metadata, indent=2) + "\n")
        run(["npm", "pack", "--pack-destination", directory], cwd=package)
    (npm_path,) = directory.glob("*.tgz")
    (directory / MANIFEST).write_text(
        json.dumps(
            {
                "kind": "agentic-workspace/platform-release/v1",
                "version": version,
                "source_commit": source,
                "platforms": records,
                "npm": asset(npm_path),
            },
            indent=2,
        )
        + "\n"
    )
    load(directory)


def smoke(directory, receipt):
    """Consumer PATH contains Git and Node, but neither Cargo nor rustc."""
    data = load(directory)
    row = next(p for p in data["platforms"] if p["target"] == current_platform()["target"])
    uv, node, npm, git = (shutil.which(name) for name in ("uv", "node", "npm", "git"))
    if not all((uv, node, npm, git)):
        raise ValueError("Consumer probe requires uv, Node, npm and Git")
    with tempfile.TemporaryDirectory(prefix="aw-platform-consumer-") as tmp:
        root = Path(tmp)
        env = {k: v for k, v in os.environ.items() if not k.startswith(("AGENTIC_WORKSPACE_", "PYTHON", "UV_PROJECT_", "VIRTUAL_ENV"))}
        env["PATH"] = os.pathsep.join(
            dict.fromkeys(
                [
                    str(Path(node).parent),
                    str(Path(git).parent),
                    str(Path(uv).parent),
                    *([str(Path(os.environ["SystemRoot"]) / "System32")] if os.name == "nt" else ["/usr/bin", "/bin"]),
                ]
            )
        )
        if any(shutil.which(tool, path=env["PATH"]) for tool in ("rustc", "cargo")):
            raise ValueError("Consumer PATH still exposes Rust")
        python_repo = root / "python"
        python_repo.mkdir()
        run([git, "init", "-q"], cwd=python_repo, env=env)
        requirement = "agentic-workspace @ " + (directory / row["wheel"]["asset"]).as_uri()
        (python_repo / "pyproject.toml").write_text(
            '[project]\nname="consumer"\nversion="0.1.0"\nrequires-python=">=3.11"\ndependencies=[' + json.dumps(requirement) + "]\n"
        )
        run([uv, "sync", "--no-cache", "--python", sys.executable], cwd=python_repo, env=env)
        command = ["start", "--target", ".", "--task", "Verify compiler-free installation", "--format", "json"]
        run([uv, "run", "--no-sync", "agentic-workspace", *command], cwd=python_repo, env=env, stdout=subprocess.DEVNULL)
        npm_repo = root / "npm"
        npm_repo.mkdir()
        run([git, "init", "-q"], cwd=npm_repo, env=env)
        (npm_repo / "package.json").write_text('{"name":"consumer","version":"1.0.0","private":true}')
        run([npm, "install", "--ignore-scripts", directory / data["npm"]["asset"]], cwd=npm_repo, env=env)
        run(
            [node, npm_repo / "node_modules/@agentic-workspace/workspace-cli/src/cli.mjs", *command],
            cwd=npm_repo,
            env=env,
            stdout=subprocess.DEVNULL,
        )
        native_repo = root / "native"
        native_repo.mkdir()
        with zipfile.ZipFile(directory / row["native_archive"]["asset"]) as archive:
            archive.extractall(native_repo)
        for path in native_repo.glob("agentic-workspace*"):
            path.chmod(0o755)
        run([git, "init", "-q"], cwd=native_repo, env=env)
        run(
            [native_repo / ("agentic-workspace.exe" if os.name == "nt" else "agentic-workspace"), *command],
            cwd=native_repo,
            env=env,
            stdout=subprocess.DEVNULL,
        )
    receipt.write_text(
        json.dumps(
            {
                "kind": "agentic-workspace/platform-consumer/v1",
                "status": "passed",
                "target": row["target"],
                "source_commit": data["source_commit"],
                "inventory_sha256": digest(directory / MANIFEST),
                "rust_available": False,
                "checks": ["uv-sync", "npm-install", "native-start"],
            },
            indent=2,
        )
        + "\n"
    )


def verify_consumers(directory):
    data = load(directory)
    for row in data["platforms"]:
        receipt = json.loads((directory / f"platform-consumer-{row['target']}.json").read_text())
        if receipt != {
            "kind": "agentic-workspace/platform-consumer/v1",
            "status": "passed",
            "target": row["target"],
            "source_commit": data["source_commit"],
            "inventory_sha256": digest(directory / MANIFEST),
            "rust_available": False,
            "checks": ["uv-sync", "npm-install", "native-start"],
        }:
            raise ValueError("Missing, stale or failed compiler-free platform proof")
    return data


def extend_release(directory, tag):
    """Extend legacy singular install projections with the complete platform set."""
    data = verify_consumers(directory)
    (manifest_path,) = directory.glob("agentic-workspace*release-manifest.json")
    manifest = json.loads(manifest_path.read_text())
    if data["source_commit"] != manifest.get("artifact_commit", manifest.get("source_commit")) or data["version"] != manifest["version"]:
        raise ValueError("Platform evidence belongs to another release")
    manifest["platform_release"] = asset(directory / MANIFEST)
    manifest["platform_consumers"] = [asset(directory / f"platform-consumer-{p['target']}.json") for p in data["platforms"]]
    manifest["native_archives"] = [p["native_archive"] for p in data["platforms"]]
    next(p for p in manifest["packages"] if p["ecosystem"] == "python")["wheels"] = [p["wheel"] for p in data["platforms"]]
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")
    update_receipts(directory, tag)
    checksums = directory / "SHA256SUMS"
    names = {line.split("  ", 1)[1] for line in checksums.read_text().splitlines()}
    names.update(p["asset"] for p in entries(data))
    names.add(MANIFEST)
    names.update(p["asset"] for p in manifest["platform_consumers"])
    checksums.write_text("".join(f"{digest(directory / name)}  {name}\n" for name in sorted(names)))


def update_receipts(directory, tag):
    data = verify_consumers(directory)
    install_path = directory / "distribution-install-readiness.json"
    install = json.loads(install_path.read_text())
    base = f"https://github.com/rickardvh/agentic-workspace/releases/download/{tag}"
    install["platforms"] = []
    for row in data["platforms"]:
        wheel = row["wheel"]
        requirement = f"agentic-workspace @ {base}/{wheel['asset']}#sha256={wheel['sha256']}"
        install["platforms"].append({"target": row["target"], "artifact": wheel, "command": f'uv tool install "{requirement}"'})
    install_path.write_text(json.dumps(install, indent=2) + "\n")
    path = directory / "redistributable-package-readiness.json"
    receipt = json.loads(path.read_text())
    all_assets = {p["name"]: p for p in receipt["artifacts"]}
    all_assets.update({p["asset"]: {"name": p["asset"], "sha256": p["sha256"]} for p in entries(data)})
    receipt.update(artifacts=sorted(all_assets.values(), key=lambda p: p["name"]), artifact_count=len(all_assets))
    path.write_text(json.dumps(receipt, indent=2) + "\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("operation", choices=["matrix", "build", "assemble", "smoke", "verify", "extend", "receipts"])
    parser.add_argument("--artifact-dir", type=Path, default=Path("dist"))
    parser.add_argument("--inputs", type=Path)
    parser.add_argument("--receipt", type=Path)
    parser.add_argument("--tag")
    args = parser.parse_args()
    directory = args.artifact_dir.resolve()
    if args.operation == "matrix":
        print(json.dumps({"include": platforms()}))
    elif args.operation == "build":
        build(directory)
    elif args.operation == "assemble":
        assemble(args.inputs.resolve(), directory)
    elif args.operation == "smoke":
        smoke(directory, args.receipt)
    elif args.operation == "verify":
        verify_consumers(directory)
    elif args.operation == "receipts":
        update_receipts(directory, args.tag)
    else:
        extend_release(directory, args.tag)


if __name__ == "__main__":
    main()
