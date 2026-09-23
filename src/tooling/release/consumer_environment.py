"""Disposable installed consumers shared by release checks and actor drivers.

The controller may use Python; Docker consumers receive only admitted artifacts
and fixture data. Native preparation reports PATH isolation, never tool absence
or an actor sandbox. Target and artifact authority stays in platform_release.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import tomllib
import uuid
import zipfile
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import quote

import cargo_release
import coordinated_release
import platform_release
from current_install import REPOSITORY, fetch, projection

ROOT = platform_release.ROOT
DOCKERFILE = ROOT / "src/tooling/model-cli-harness/sandbox/consumer/Dockerfile"
PROFILES = {
    "node": (("git", "node", "npm", "pnpm"), ("python", "python3", "cargo", "rustc", "cc", "gcc", "agentic-workspace")),
    "python": (("git", "python3", "uv"), ("node", "npm", "cargo", "rustc", "cc", "gcc", "agentic-workspace")),
    "standalone": (("git",), ("python", "python3", "node", "npm", "cargo", "rustc", "cc", "gcc", "agentic-workspace")),
    "cargo": (("git", "cargo", "rustc"), ("python", "python3", "node", "npm", "agentic-workspace")),
}


def run(argv, **kwargs):
    return subprocess.run([str(v) for v in argv], check=True, capture_output=True, text=True, timeout=kwargs.pop("timeout", 120), **kwargs)


@dataclass(frozen=True)
class Subject:
    mode: str
    directory: Path
    inventory: dict

    @classmethod
    def candidate(cls, directory: Path):
        directory = directory.resolve()
        return cls("candidate", directory, platform_release.load(directory))

    @classmethod
    def public(cls, version: str, directory: Path):
        """Freeze one published, admitted stable; a missing route never falls back."""
        if not re.fullmatch(r"\d+\.\d+\.\d+", version):
            raise ValueError("Public subject requires an exact stable version")
        release = json.loads(fetch(f"https://api.github.com/repos/{REPOSITORY}/releases/tags/v{version}"))
        base = f"https://github.com/{REPOSITORY}/releases/download/v{version}/"
        promotion = json.loads(fetch(base + "support-bearing-promotion.json"))
        admitted = projection(release, fetch(base + "distribution-install-readiness.json"), promotion, promotion["source_commit"])
        raw = fetch(base + platform_release.MANIFEST)
        inventory = json.loads(raw)
        if inventory["version"] != admitted["version"] or inventory["source_commit"] != admitted["source_commit"]:
            raise ValueError("Public inventory does not match accepted release")
        expected = promotion["artifacts"].get(platform_release.MANIFEST)
        if expected != "sha256:" + hashlib.sha256(raw).hexdigest():
            raise ValueError("Public inventory is outside release admission")
        directory.mkdir(parents=True, exist_ok=False)
        (directory / platform_release.MANIFEST).write_bytes(raw)
        for item in [*platform_release.entries(inventory), inventory["npm"]]:
            name = item["asset"]
            if Path(name).name != name or "/" in name or "\\" in name:
                raise ValueError("Unsafe public asset name")
            content = fetch(base + name)
            if hashlib.sha256(content).hexdigest() != item["sha256"]:
                raise ValueError("Public artifact digest mismatch")
            (directory / name).write_bytes(content)
        cargo_raw = fetch(base + "cargo-release-manifest.json")
        if promotion["artifacts"].get("cargo-release-manifest.json") != "sha256:" + hashlib.sha256(cargo_raw).hexdigest():
            raise ValueError("Cargo inventory is outside release admission")
        (directory / "cargo-release-manifest.json").write_bytes(cargo_raw)
        for crate in json.loads(cargo_raw)["packages"]:
            name = crate["asset"]
            if Path(name).name != name or "/" in name or "\\" in name:
                raise ValueError("Unsafe crate asset")
            content = fetch(base + name)
            if hashlib.sha256(content).hexdigest() != crate["sha256"]:
                raise ValueError("Cargo digest mismatch")
            (directory / name).write_bytes(content)
        return cls("public", directory.resolve(), platform_release.load(directory))

    def row(self, target: str):
        return next(row for row in self.inventory["platforms"] if row["target"] == target)

    def identity(self):
        return {
            "mode": self.mode,
            "version": self.inventory["version"],
            "source_commit": self.inventory["source_commit"],
            "inventory_sha256": platform_release.digest(self.directory / platform_release.MANIFEST),
        }


def registry_package(subject, profile, row):
    """Authenticate registry packaging separately from the native execution floor."""
    version = subject.inventory["version"]
    if profile == "node":
        version = coordinated_release.npm_version(version)
        item = subject.inventory["npm"]
        metadata = json.loads(fetch(f"https://registry.npmjs.org/@agentic-workspace%2fworkspace-cli/{quote(version)}"))
        content = fetch(metadata["dist"]["tarball"])
        if hashlib.sha256(content).hexdigest() != item["sha256"]:
            raise ValueError("Public npm bytes differ from selected subject")
        return f"@agentic-workspace/workspace-cli@{version}"
    item = row["wheel"]
    metadata = json.loads(fetch(f"https://pypi.org/pypi/agentic-workspace/{version}/json"))
    published = next((entry for entry in metadata["urls"] if entry["filename"] == item["asset"]), None)
    if published is None or published["digests"]["sha256"] != item["sha256"]:
        raise ValueError("Public wheel missing or different")
    return published["url"]


def safe_native_archive(archive: Path, destination: Path, subject: Subject, target: str):
    suffix = ".exe" if "windows" in target else ""
    with zipfile.ZipFile(archive) as packed:
        identity = json.loads(packed.read("artifact.json"))
        if (
            identity["rust_host"] != target
            or identity["source_head"] != subject.inventory["source_commit"]
            or identity["package_version"] != subject.inventory["version"]
            or identity["source_dirty"]
        ):
            raise ValueError("Native archive subject mismatch")
        destination.mkdir(parents=True, exist_ok=False)
        for name, field in (("agentic-workspace", "cli_sha256"), ("agentic-workspace-core", "sha256")):
            data = packed.read(name + suffix)
            if hashlib.sha256(data).hexdigest() != identity[field]:
                raise ValueError("Native archive executable digest mismatch")
            path = destination / (name + suffix)
            path.write_bytes(data)
            path.chmod(0o755)
        (destination / "artifact.json").write_text(json.dumps(identity), encoding="utf-8")
    return identity


def build_image(profile: str, target: str) -> str:
    row = next(row for row in platform_release.platforms() if row["target"] == target)
    if profile not in PROFILES or row["node_platform"] != "linux":
        raise ValueError("Unsupported Docker profile/target")
    platform = "linux/" + {"x64": "amd64", "arm64": "arm64"}[row["node_arch"]]
    rust = tomllib.loads((ROOT / "rust-toolchain.toml").read_text())["toolchain"]["channel"]
    # Capture the immutable resulting image ID; tags are never result identity.
    tag = f"aw-consumer-{profile}-{row['node_arch']}"
    run(
        [
            "docker",
            "build",
            "--platform",
            platform,
            "--target",
            profile,
            "--build-arg",
            f"RUST_VERSION={rust}",
            "-t",
            tag,
            str(DOCKERFILE.parent),
        ],
        timeout=900,
    )
    return run(["docker", "image", "inspect", "--format", "{{.Id}}", tag]).stdout.strip()


class DockerConsumer:
    """No host bind mounts, inherited environment, credentials or Docker socket."""

    def __init__(self, subject: Subject, profile: str, target: str, image: str):
        row = subject.row(target)
        if row["node_platform"] != "linux" or profile not in PROFILES or not re.fullmatch(r"sha256:[a-f0-9]{64}", image):
            raise ValueError("Unsupported or unfrozen consumer environment")
        self.subject, self.profile, self.target, self.image = subject, profile, target, image
        self.name = "aw-consumer-" + uuid.uuid4().hex
        self.command = []
        self.observation = {
            "backend": "docker",
            "target": target,
            "profile": profile,
            "image": image,
            "recipe_sha256": platform_release.digest(DOCKERFILE),
            "isolation": "container-no-host-mounts",
        }
        self.cleanup = "not-started"

    def __enter__(self):
        try:
            run(
                [
                    "docker",
                    "create",
                    "--name",
                    self.name,
                    "--label",
                    "aw.consumer=true",
                    "--init",
                    "--cap-drop=ALL",
                    "--security-opt=no-new-privileges",
                    "--pids-limit=128",
                    "--memory=2g",
                    "--cpus=2",
                    "--workdir=/home/consumer",
                    self.image,
                    "sleep",
                    "infinity",
                ]
            )
            run(["docker", "start", self.name])
            run(["docker", "exec", self.name, "mkdir", "-p", "/home/consumer/repo", "/home/consumer/input", "/home/consumer/tmp"])
            self.exec(["git", "init", "-q"])
            self.observe_tools()
            return self
        except BaseException:
            self.close()
            raise

    def exec(self, argv, *, timeout=120):
        return run(
            ["docker", "exec", "--workdir=/home/consumer/repo", "--env", "TMPDIR=/home/consumer/tmp", self.name, *argv], timeout=timeout
        )

    def copy_in(self, source: Path, destination: str):
        # No added root capabilities: copy through world-readable container /tmp,
        # then create consumer-owned files as the unprivileged consumer.
        incoming = "/tmp/input-" + uuid.uuid4().hex
        run(["docker", "cp", str(source.resolve()), f"{self.name}:{incoming}"])
        self.exec(["cp", "-R", incoming, destination])

    def observe_tools(self):
        required, forbidden = PROFILES[self.profile]
        inventory = {}
        for tool in (*required, *forbidden):
            result = self.exec(["sh", "-c", 'command -v "$1" || true', "sh", tool]).stdout.strip()
            inventory[tool] = result or None
            if (tool in required and not result) or (tool in forbidden and result):
                raise ValueError(f"Consumer tool boundary failed: {tool}")
        self.observation["tools"] = inventory
        self.observation["versions"] = {tool: self.exec([tool, "--version"]).stdout[:500] for tool in required}
        machine = self.exec(["uname", "-m"]).stdout.strip()
        expected = "aarch64" if self.subject.row(self.target)["node_arch"] == "arm64" else "x86_64"
        if machine != expected:
            raise ValueError("Container architecture mismatch")

    def install(self, *, manager="npm"):
        if platform_release.load(self.subject.directory) != self.subject.inventory:
            raise ValueError("Frozen subject changed before installation")
        row = self.subject.row(self.target)
        if self.profile == "standalone":
            with tempfile.TemporaryDirectory() as tmp:
                native = Path(tmp) / "native"
                identity = safe_native_archive(self.subject.directory / row["native_archive"]["asset"], native, self.subject, self.target)
                binaries = "/home/consumer/native" + "-" + self.subject.identity()["inventory_sha256"][:12]
                self.copy_in(native, binaries)
            self.command = [binaries + "/agentic-workspace"]
        elif self.profile == "node":
            if manager not in {"npm", "pnpm"}:
                raise ValueError("Unsupported Node manager")
            item = self.subject.inventory["npm"]
            package = "/home/consumer/input/" + item["asset"]
            self.copy_in(self.subject.directory / item["asset"], package)
            self.exec(["sh", "-c", "printf '{\"private\":true}' > package.json"])
            if self.subject.mode == "public":
                package = registry_package(self.subject, "node", row)
            self.exec([manager, "install", "--ignore-scripts", package])
            self.command = [manager, "exec", *(["--no", "--"] if manager == "npm" else []), "agentic-workspace"]
            binaries = f"node_modules/@agentic-workspace/workspace-cli/src/native/bin/linux-{row['node_arch']}"
            identity = json.loads(self.exec(["cat", binaries + "/artifact.json"]).stdout)
        elif self.profile == "python":
            item = row["wheel"]
            package = "/home/consumer/input/" + item["asset"]
            self.copy_in(self.subject.directory / item["asset"], package)
            self.exec(["uv", "venv", "--allow-existing", "--python", "python3", ".venv"])
            options = ["--no-index"]
            if self.subject.mode == "public":
                package, options = registry_package(self.subject, "python", row), []
            self.exec(["uv", "pip", "install", "--python", ".venv/bin/python", *options, "--no-deps", package])
            self.command = ["/home/consumer/repo/.venv/bin/agentic-workspace"]
            identity = json.loads(
                self.exec(
                    [
                        ".venv/bin/python",
                        "-I",
                        "-c",
                        "import agentic_workspace,pathlib; print((pathlib.Path(agentic_workspace.__file__).parent/'_native/artifact.json').read_text())",
                    ]
                ).stdout
            )
            binaries = self.exec(
                [
                    ".venv/bin/python",
                    "-I",
                    "-c",
                    "import agentic_workspace,pathlib; print(pathlib.Path(agentic_workspace.__file__).parent/'_native')",
                ]
            ).stdout.strip()
        else:
            ownership = coordinated_release.load_ownership()
            admission = cargo_release.admitted_manifest(
                self.subject.directory, ownership, self.subject.inventory["source_commit"], self.subject.inventory["version"]
            )
            if admission is None:
                raise ValueError("No admitted Cargo subject")
            for crate in admission["packages"]:
                command = ["cargo", "install", "--locked", "--root", "/home/consumer/installed"]
                if self.subject.mode == "public":
                    if cargo_release.observe(crate) != "matching":
                        raise ValueError("Public Cargo route absent")
                    command += [crate["name"], "--version", "=" + crate["version"], "--registry", "crates-io"]
                else:
                    destination = "/home/consumer/input/" + crate["asset"]
                    self.copy_in(self.subject.directory / crate["asset"], destination)
                    # Only admitted release crate archives enter the container.
                    self.exec(["tar", "xf", destination, "-C", "/home/consumer/input"])
                    command += ["--path", f"/home/consumer/input/{crate['name']}-{crate['version']}"]
                self.exec(command, timeout=900)
            self.command = ["/home/consumer/installed/bin/agentic-workspace"]
            identity = {
                "package_version": self.subject.inventory["version"],
                "source_head": self.subject.inventory["source_commit"],
                "rust_host": self.target,
                "compiled_from": admission,
            }
        if self.profile != "cargo":
            with tempfile.TemporaryDirectory() as tmp:
                expected = safe_native_archive(
                    self.subject.directory / row["native_archive"]["asset"], Path(tmp) / "native", self.subject, self.target
                )
            for name, field in (("agentic-workspace", "cli_sha256"), ("agentic-workspace-core", "sha256")):
                actual = self.exec(["sha256sum", binaries + "/" + name]).stdout.split()[0]
                if actual != expected[field] or identity[field] != expected[field]:
                    raise ValueError("Installed executable bytes differ from admitted subject")
        if (
            identity["package_version"] != self.subject.inventory["version"]
            or identity["source_head"] != self.subject.inventory["source_commit"]
            or identity["rust_host"] != self.target
        ):
            raise ValueError("Installed package identity mismatch")
        self.observation["installed"] = identity
        self.observation["requested"] = self.subject.identity()
        self.observation["route"] = (
            "candidate-asset"
            if self.subject.mode == "candidate"
            else {"node": "npm-registry", "python": "pypi", "cargo": "crates-io", "standalone": "public-release-asset"}[self.profile]
        )
        self.exec([*self.command, "--help"])
        return self.command

    def close(self):
        try:
            run(["docker", "rm", "--force", self.name])
            self.cleanup = "removed"
        except subprocess.CalledProcessError as error:
            self.cleanup = "failed"
            raise RuntimeError(f"Consumer cleanup failed: {self.name}") from error

    def __exit__(self, *exc):
        self.close()


def private_native_environment(root: Path, tool_directories: list[Path]):
    """Explicitly narrower PATH-only evidence, suitable for deterministic CI."""
    env = {key: os.environ[key] for key in ("SystemRoot", "WINDIR", "COMSPEC") if key in os.environ}
    for name in ("home", "tmp", "cache"):
        (root / name).mkdir(parents=True, exist_ok=False)
    env.update(
        HOME=str(root / "home"),
        USERPROFILE=str(root / "home"),
        TMP=str(root / "tmp"),
        TEMP=str(root / "tmp"),
        TMPDIR=str(root / "tmp"),
        XDG_CACHE_HOME=str(root / "cache"),
        GIT_CONFIG_NOSYSTEM="1",
        GIT_CONFIG_GLOBAL=os.devnull,
        npm_config_cache=str(root / "cache/npm"),
        UV_CACHE_DIR=str(root / "cache/uv"),
        PATH=os.pathsep.join(str(path) for path in tool_directories),
    )
    if shutil.which("agentic-workspace", path=env["PATH"]):
        raise ValueError("Global AW contaminates repository-local consumer")
    return env


class NativeConsumer:
    """Fresh deterministic consumer on its declared native target, without host claims."""

    def __init__(self, subject: Subject, profile: str, target: str, parent: Path):
        if platform_release.current_platform()["target"] != target or profile not in {"standalone", "node", "python"}:
            raise ValueError("Unsupported native target/profile")
        self.subject, self.profile, self.target, self.parent = subject, profile, target, parent
        self.command = []
        self.cleanup = "not-started"

    def __enter__(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="consumer-", dir=self.parent)
        self.root = Path(self.temporary.name)
        self.repo = self.root / "repo"
        self.repo.mkdir()
        try:
            names = ["git", *({"node": ["node", "npm"], "python": ["uv"], "standalone": []}[self.profile])]
            self.tools = {name: shutil.which(name) for name in names}
            if not all(self.tools.values()):
                raise ValueError("Native consumer prerequisites unavailable")
            directories = list(dict.fromkeys(Path(path).parent for path in self.tools.values()))
            directories += [Path(os.environ["SystemRoot"]) / "System32"] if os.name == "nt" else [Path("/bin")]
            self.env = private_native_environment(self.root, directories)
            self.observation = {
                "backend": "native",
                "target": self.target,
                "profile": self.profile,
                "isolation": "private-state-and-path-only",
                "runner_image": {key: os.environ.get(key) for key in ("ImageOS", "ImageVersion", "RUNNER_ARCH", "RUNNER_OS")},
                "tools": {
                    name: shutil.which(name, path=self.env["PATH"]) for name in (*PROFILES[self.profile][0], *PROFILES[self.profile][1])
                },
                "versions": {name: run([path, "--version"], env=self.env).stdout[:500] for name, path in self.tools.items()},
                "actor_containment": "unsupported",
            }
            self.observation["forbidden_visible"] = [name for name in PROFILES[self.profile][1] if self.observation["tools"][name]]
            self.observation["physical_absence"] = "not-claimed"
            self.exec([self.tools["git"], "init", "-q"])
            return self
        except BaseException:
            self.__exit__(None, None, None)
            raise

    def exec(self, argv, *, timeout=120):
        return run(argv, cwd=self.repo, env=self.env, timeout=timeout)

    def install(self):
        if platform_release.load(self.subject.directory) != self.subject.inventory:
            raise ValueError("Frozen subject changed before installation")
        row = self.subject.row(self.target)
        suffix = ".exe" if os.name == "nt" else ""
        native = self.root / ("native-" + self.subject.identity()["inventory_sha256"][:12])
        expected = safe_native_archive(self.subject.directory / row["native_archive"]["asset"], native, self.subject, self.target)
        if self.profile == "standalone":
            binaries = native
            self.command = [str(binaries / ("agentic-workspace" + suffix))]
        elif self.profile == "node":
            (self.repo / "package.json").write_text('{"private":true}', encoding="utf-8")
            package = str(self.subject.directory / self.subject.inventory["npm"]["asset"])
            if self.subject.mode == "public":
                package = registry_package(self.subject, "node", row)
            self.exec([self.tools["npm"], "install", "--ignore-scripts", "--no-audit", "--no-fund", package])
            binaries = self.repo / f"node_modules/@agentic-workspace/workspace-cli/src/native/bin/{row['node_platform']}-{row['node_arch']}"
            self.command = [self.tools["npm"], "exec", "--no", "--", "agentic-workspace"]
        else:
            self.exec([self.tools["uv"], "venv", "--allow-existing", "--python", sys.executable, ".venv"])
            python = self.repo / ".venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
            package = str(self.subject.directory / row["wheel"]["asset"])
            options = ["--no-index"]
            if self.subject.mode == "public":
                package, options = registry_package(self.subject, "python", row), ["--only-binary=:all:"]
            self.exec([self.tools["uv"], "pip", "install", "--python", str(python), "--no-deps", *options, package])
            binaries = next((self.repo / ".venv").rglob("agentic_workspace/_native/artifact.json")).parent
            self.command = [str(python.parent / ("agentic-workspace" + suffix))]
        identity = json.loads((binaries / "artifact.json").read_text())
        for key in ("source_head", "package_version", "rust_host", "cli_sha256", "sha256"):
            if identity[key] != expected[key]:
                raise ValueError("Installed native subject mismatch")
        for name, field in (("agentic-workspace", "cli_sha256"), ("agentic-workspace-core", "sha256")):
            if platform_release.digest(binaries / (name + suffix)) != expected[field]:
                raise ValueError("Installed executable bytes mismatch")
        self.observation.update(requested=self.subject.identity(), installed=identity)
        self.exec([*self.command, "--help"])
        return self.command

    def __exit__(self, *exc):
        try:
            self.temporary.cleanup()
            self.cleanup = "removed"
        except OSError:
            self.cleanup = "failed"
            raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    subject = parser.add_mutually_exclusive_group(required=True)
    subject.add_argument("--candidate", type=Path)
    subject.add_argument("--public-version")
    parser.add_argument("--profile", choices=PROFILES, required=True)
    parser.add_argument("--target", choices=[row["target"] for row in platform_release.platforms()], required=True)
    parser.add_argument("--backend", choices=["docker", "native"], required=True)
    parser.add_argument("--image", help="Existing immutable Docker image ID; otherwise build the declared recipe")
    parser.add_argument("--scratch", type=Path, required=True, help="Existing run-owned scratch container")
    parser.add_argument("--result", type=Path, required=True)
    args = parser.parse_args()
    if args.result.exists():
        parser.error("Result already exists; preserve the initial attempt")
    started = time.monotonic()
    record = {
        "kind": "agentic-workspace/consumer-environment/v1",
        "status": "assigned",
        "executed": False,
        "target": args.target,
        "profile": args.profile,
        "backend": args.backend,
        "cleanup": "not-started",
    }
    consumer = None
    try:
        with tempfile.TemporaryDirectory(prefix="subject-", dir=args.scratch) as root:
            subject = Subject.candidate(args.candidate) if args.candidate else Subject.public(args.public_version, Path(root) / "public")
            record["requested"] = subject.identity()
            if args.backend == "docker":
                image = args.image or build_image(args.profile, args.target)
                consumer = DockerConsumer(subject, args.profile, args.target, image)
            else:
                consumer = NativeConsumer(subject, args.profile, args.target, args.scratch)
            with consumer:
                record["executed"] = True
                consumer.install()
                record.update(status="passed", observation=consumer.observation)
    except (Exception, KeyboardInterrupt) as error:
        record.update(status="failed", error=str(error)[:2000], failure_class="environment-or-installation")
    finally:
        record["elapsed_seconds"] = round(time.monotonic() - started, 3)
        record["cleanup"] = consumer.cleanup if consumer else "no-consumer-created"
        args.result.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(record))
    return 0 if record["status"] == "passed" and record["cleanup"] == "removed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
