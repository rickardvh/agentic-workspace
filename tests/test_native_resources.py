"""Native resource ownership and real Git lifecycle composition."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
from tests.test_native_public_cli import ROOT
from tests.test_native_public_cli import native_cli as native_cli


def resource(surface, binary, native, context):
    env = dict(os.environ, AGENTIC_WORKSPACE_CORE_BINARY=str(binary))
    if surface == "native":
        args = [str(native), "resources", "--target", context["target"], "--task", context.get("task", ""), "--input", "-"]
        for path in context.get("changed", []):
            args += ["--changed", path]
        payload = context["request"]
    elif surface == "json":
        args = [str(binary)]
        payload = {"resources": context}
    elif surface == "python":
        args = [
            sys.executable,
            "-c",
            "import json,sys; from agentic_workspace.decision import resources; print(json.dumps(resources(json.load(sys.stdin))))",
        ]
        payload = context
    else:
        url = (ROOT / "bindings/node/semantic-decision.mjs").as_uri()
        args = [
            "node",
            "--input-type=module",
            "-e",
            f'import {{resources}} from {json.dumps(url)}; let s=""; for await (const c of process.stdin) s+=c; console.log(JSON.stringify(resources(JSON.parse(s))));',
        ]
        payload = context
    result = subprocess.run(args, input=json.dumps(payload), text=True, capture_output=True, env=env, cwd=ROOT)
    assert result.returncode == 0, result.stdout + result.stderr
    return json.loads(result.stdout)


def test_task_scratch_reentry_cleanup_and_owner_preservation(tmp_path, shared_core_binary, native_cli):
    root = tmp_path / ".agentic-workspace/local"
    (root / "instructions").mkdir(parents=True)
    (root / "instructions/policy.md").write_text("Structured policy, not scratch")
    (root / "current-task-routes.json").write_text("{}")
    (root / "loose.json").write_text("Preserve unknown referenced material")

    def call(operation, **extra):
        return resource(
            "json",
            shared_core_binary,
            native_cli,
            {"target": str(tmp_path), "task": "Bounded task", "request": {"operation": operation, **extra}},
        )

    audit = call("audit")
    classes = {r["path"].split("/")[-1]: r["class"] for r in audit["entries"]}
    assert classes["instructions"] == "structured-owner-state"
    assert classes["current-task-routes.json"] == "structured-owner-state"
    assert classes["loose.json"] == "unowned-residue"
    for _ in range(2):
        proposal = call("scratch-create")
        created = resource("json", shared_core_binary, native_cli, proposal["action"])
        assert created["effect_outcome"] == "committed"
        path = Path(created["path"])
        (path / "draft.json").write_text('{"temporary":true}')
        # Fresh consumer recovers exactly the interrupted task's disposable container.
        removal = call("scratch-remove", path=proposal["action"]["request"]["path"])
        (path / "new.txt").write_text("New material invalidates proposed cleanup")
        with pytest.raises(AssertionError, match="changed"):
            resource("json", shared_core_binary, native_cli, removal["action"])
        fresh = call("scratch-remove", path=proposal["action"]["request"]["path"])
        assert resource("json", shared_core_binary, native_cli, fresh["action"])["effect_outcome"] == "committed"
        assert not path.exists()
    assert (root / "instructions/policy.md").read_text() == "Structured policy, not scratch"
    assert (root / "loose.json").exists()
    assert list((root / "scratch").iterdir()) == []


def git(root, *args):
    return subprocess.check_output(["git", "-C", str(root), *args], text=True).strip()


def repository(root):
    git(root, "init", "-q")
    (root / "source.txt").write_text("initial")
    git(root, "add", ".")
    git(root, "-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid", "commit", "-qm", "baseline")


def test_worktree_policy_necessity_clean_teardown_and_integrity(tmp_path, shared_core_binary, native_cli):
    repo = tmp_path / "repo"
    repo.mkdir()
    repository(repo)
    instructions = repo / ".agentic-workspace/instructions"
    instructions.mkdir(parents=True)
    (instructions / "local.md").write_text("Use the existing checkout unless a real conflict requires isolation.")
    original = {p: git(repo, *args) for p, args in {"head": ("rev-parse", "HEAD"), "bare": ("rev-parse", "--is-bare-repository")}.items()}
    context = {"target": str(repo), "task": "Isolated destructive validation"}
    path = tmp_path / "isolated"

    def call(op, **extra):
        return resource("json", shared_core_binary, native_cli, {**context, "request": {"operation": op, "path": str(path), **extra}})

    quiet = call("worktree-create")
    assert "action" not in quiet and not path.exists()
    request = {
        "need": "destructive-validation",
        "reason": "Validation rewrites tracked fixtures and conflicts with current implementation work",
        "policy_revision": quiet["policy_revision"],
        "policy_answer": "permits-isolation",
    }
    proposal = call("worktree-create", **request)
    created = resource("json", shared_core_binary, native_cli, proposal["action"])
    assert created["effect_outcome"] == "committed"
    assert path.exists()
    (path / "untracked.txt").write_text("must preserve")
    protected = call("worktree-remove")
    assert protected["blockers"] and "action" not in protected
    (path / "untracked.txt").unlink()
    remove = call("worktree-remove")
    assert resource("json", shared_core_binary, native_cli, remove["action"])["effect_outcome"] == "committed"
    assert not path.exists() and str(path).replace("\\", "/") not in git(repo, "worktree", "list", "--porcelain")
    assert git(repo, "rev-parse", "HEAD") == original["head"]
    assert git(repo, "rev-parse", "--is-bare-repository") == original["bare"]


@pytest.mark.parametrize("policy_scope", ["checked-in", "machine-local"])
def test_worktree_interrupted_unlock_unique_commits_and_stale_registration(tmp_path, shared_core_binary, native_cli, policy_scope):
    repo = tmp_path / "repo"
    repo.mkdir()
    repository(repo)
    policy = repo / (
        ".agentic-workspace/instructions/isolation.md"
        if policy_scope == "checked-in"
        else ".agentic-workspace/local/instructions/isolation.md"
    )
    policy.parent.mkdir(parents=True)
    policy.write_text("Use the existing checkout by default. Isolate only destructive validation that would disturb current work.")
    if policy_scope == "checked-in":
        git(repo, "add", ".")
        git(repo, "-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid", "commit", "-qm", "repository policy")
    else:
        (repo / ".git/info/exclude").write_text(".agentic-workspace/local/\n")
    git(repo, "config", "core.bare", "false")
    git(repo, "config", "core.worktree", str(repo))
    index = (repo / ".git/index").read_bytes()
    config = (repo / ".git/config").read_bytes()
    head = (repo / ".git/HEAD").read_bytes()
    path = tmp_path / "isolated"
    context = {"target": str(repo), "task": "Validate destructive experiment"}

    def call(op, **kw):
        return resource("json", shared_core_binary, native_cli, {**context, "request": {"operation": op, "path": str(path), **kw}})

    quiet = call("worktree-create")
    assert any(r["guidance"] == policy.read_text() for r in quiet["policy"]["instructions"])
    assert "action" not in quiet
    request = dict(
        need="destructive-validation",
        reason="The test replaces tracked source files",
        policy_revision=quiet["policy_revision"],
        policy_answer="permits-isolation",
    )
    proposal = call("worktree-create", **request)
    policy.write_text(policy.read_text() + " Preserve evidence before teardown.")
    stale = resource("json", shared_core_binary, native_cli, proposal["action"])
    assert stale["blockers"] and not path.exists()
    request["policy_revision"] = stale["policy_revision"]
    resource("json", shared_core_binary, native_cli, call("worktree-create", **request)["action"])
    # Simulate process loss after unlock: fresh recovery uses the selected Git registration.
    git(repo, "worktree", "unlock", str(path))
    (path / "source.txt").write_text("valuable unintegrated experiment")
    git(path, "add", ".")
    git(path, "-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid", "commit", "-qm", "unique result")
    blocked = call("worktree-remove")
    assert any("unique commits" in b for b in blocked["blockers"])
    assert path.exists()
    # Explicit retention under a branch makes terminal teardown safe.
    git(repo, "branch", "retained-result", git(path, "rev-parse", "HEAD"))
    resource("json", shared_core_binary, native_cli, call("worktree-remove")["action"])
    assert not path.exists()
    assert call("worktree-remove")["snapshot"]["registration"] is None
    # Create a second resource, then simulate a directory removed outside AW.
    request["policy_revision"] = call("worktree-create")["policy_revision"]
    resource("json", shared_core_binary, native_cli, call("worktree-create", **request)["action"])
    import shutil

    shutil.rmtree(path)  # Exact test-owned fixture; simulates the reported external deletion.
    stale_registration = call("worktree-remove")
    assert stale_registration["snapshot"]["exists"] is False
    resource("json", shared_core_binary, native_cli, stale_registration["action"])
    assert str(path).replace("\\", "/") not in git(repo, "worktree", "list", "--porcelain")
    assert (repo / ".git/config").read_bytes() == config
    assert (repo / ".git/HEAD").read_bytes() == head
    assert (repo / ".git/index").read_bytes() == index


def test_scratch_retention_and_empty_interruption_recovery(tmp_path, shared_core_binary, native_cli):
    context = {"target": str(tmp_path), "task": "Keep interrupted evidence"}

    def call(op, **kw):
        return resource("json", shared_core_binary, native_cli, {**context, "request": {"operation": op, **kw}})

    created = call("scratch-create")
    path = Path(created["path"])
    resource("json", shared_core_binary, native_cli, created["action"])
    (path / "evidence.txt").write_text("required interrupted result")
    resource(
        "json", shared_core_binary, native_cli, call("scratch-retain", reason="Evidence is still required for reconciliation")["action"]
    )
    assert "action" not in call("scratch-remove")
    resource("json", shared_core_binary, native_cli, call("scratch-release", reason="Result transferred to its durable owner")["action"])
    resource("json", shared_core_binary, native_cli, call("scratch-remove")["action"])
    assert not path.exists()
    path.mkdir()  # Crash after mkdir, before marker publication, or after final marker removal.
    assert call("scratch-remove")["snapshot"]["status"] == "empty-interrupted"
    resource("json", shared_core_binary, native_cli, call("scratch-remove")["action"])
    assert not path.exists()
    with pytest.raises(AssertionError, match="one exact task container"):
        call("scratch-remove", path=".agentic-workspace/local/instructions")
    with pytest.raises(AssertionError, match="absolute external resource"):
        call("worktree-create", path=str(tmp_path))


def test_protected_resource_write_and_malformed_configuration_preserve_state(tmp_path, shared_core_binary, native_cli):
    context = {"target": str(tmp_path), "task": "Temporary material", "request": {"operation": "scratch-create"}}
    folder = tmp_path / ".agentic-workspace/instructions"
    folder.mkdir(parents=True)
    source = folder / "protected.md"
    source.write_text(
        "---\npaths: [.agentic-workspace/local/scratch/**]\nprotect: [.agentic-workspace/local/scratch/**]\n---\nPreserve scratch"
    )
    blocked = resource("json", shared_core_binary, native_cli, context)
    assert "action" not in blocked
    assert any("protects" in b for b in blocked["blockers"])
    source.unlink()
    config = tmp_path / ".agentic-workspace/config.toml"
    config.write_text("invalid = [")
    with pytest.raises(AssertionError, match="configuration"):
        resource("json", shared_core_binary, native_cli, context)
    assert not (tmp_path / ".agentic-workspace/local").exists()


def test_scratch_current_owner_reference_blocks_cleanup(tmp_path, shared_core_binary, native_cli):
    context = {"target": str(tmp_path), "task": "Material with a live owner reference"}

    def call(op):
        return resource("json", shared_core_binary, native_cli, {**context, "request": {"operation": op}})

    proposal = call("scratch-create")
    resource("json", shared_core_binary, native_cli, proposal["action"])
    path = Path(proposal["path"])
    (path / "needed.md").write_text("Owner still consumes this evidence")
    instructions = tmp_path / ".agentic-workspace/instructions"
    instructions.mkdir(parents=True)
    reference = proposal["action"]["request"]["path"] + "/needed.md"
    source = instructions / "reader.md"
    source.write_text(f"---\nread: [{reference}]\n---\nRead the needed result.")
    blocked = call("scratch-remove")
    assert "action" not in blocked and any("owner references" in b for b in blocked["blockers"])
    assert (path / "needed.md").exists()


def test_malformed_scratch_custody_is_preserved(tmp_path, shared_core_binary, native_cli):
    context = {"target": str(tmp_path), "task": "Preserve malformed material"}
    proposal = resource("json", shared_core_binary, native_cli, {**context, "request": {"operation": "scratch-create"}})
    resource("json", shared_core_binary, native_cli, proposal["action"])
    path = Path(proposal["path"])
    marker = path / ".aw-scratch.json"
    body = json.loads(marker.read_text())
    body["retain"] = "false"
    marker.write_text(json.dumps(body))
    with pytest.raises(AssertionError, match="custody differs"):
        resource("json", shared_core_binary, native_cli, {**context, "request": {"operation": "scratch-remove"}})
    assert json.loads(marker.read_text()) == body


def test_owned_build_outputs_are_removed_but_unknown_ignored_material_is_preserved(tmp_path, shared_core_binary, native_cli):
    repo = tmp_path / "repo"
    repo.mkdir()
    repository(repo)
    (repo / ".gitignore").write_text("/target/\n/.pytest_cache/\n/.venv/\n/.private/\n")
    (repo / "Cargo.toml").write_text('[package]\nname="resource-fixture"\nversion="0.1.0"\nedition="2021"\n')
    (repo / "Cargo.lock").write_text('version = 3\n[[package]]\nname="resource-fixture"\nversion="0.1.0"\n')
    (repo / "src").mkdir()
    (repo / "src/lib.rs").write_text("pub fn value() -> u32 { 42 }\n")
    (repo / "test_value.py").write_text("def test_value():\n    assert 42 == 42\n")
    git(repo, "add", ".")
    git(repo, "-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid", "commit", "-qm", "validation fixture")
    path = tmp_path / "isolated"
    context = {"target": str(repo), "task": "Validate in necessary isolation"}

    def call(operation, **kw):
        return resource("json", shared_core_binary, native_cli, {**context, "request": {"operation": operation, "path": str(path), **kw}})

    initial = call("worktree-create")
    proposal = call(
        "worktree-create",
        need="destructive-validation",
        reason="The validation subject must not replace the current checkout",
        policy_revision=initial["policy_revision"],
        policy_answer="permits-isolation",
        disposable_outputs=["target", ".pytest_cache", ".venv"],
    )
    created = resource("json", shared_core_binary, native_cli, proposal["action"])
    environment = {**os.environ, **created["build_environment"]}
    subprocess.run(["cargo", "build", "--locked", "--offline"], cwd=path, env=environment, check=True, capture_output=True)
    subprocess.run([sys.executable, "-m", "pytest", "-q", "test_value.py"], cwd=path, env=environment, check=True, capture_output=True)
    subprocess.run([sys.executable, "-m", "venv", "--without-pip", ".venv"], cwd=path, env=environment, check=True, capture_output=True)
    assert (path / "target/debug").is_dir() and (path / ".pytest_cache").is_dir() and (path / ".venv/pyvenv.cfg").exists()
    unknown = path / ".private/important.txt"
    unknown.parent.mkdir()
    unknown.write_text("Meaningful ignored user data")
    assert "action" not in call("worktree-remove")
    assert unknown.read_text() == "Meaningful ignored user data"
    # Remove only this test-created negative fixture; leased caches remain populated.
    unknown.unlink()
    unknown.parent.rmdir()
    removal = call("worktree-remove")
    assert removal["snapshot"]["status"] == ""
    # Fresh-process cleanup after interruption at unlock retains the output leases.
    git(repo, "worktree", "unlock", str(path))
    removal = call("worktree-remove")
    resource("json", shared_core_binary, native_cli, removal["action"])
    assert not path.exists() and str(path).replace("\\", "/") not in git(repo, "worktree", "list", "--porcelain")
    assert not (repo / "target").exists()


def test_unleased_or_tracked_tool_roots_cannot_be_adopted_for_cleanup(tmp_path, shared_core_binary, native_cli):
    repo = tmp_path / "repo"
    repo.mkdir()
    repository(repo)
    (repo / ".gitignore").write_text("/target/\n")
    git(repo, "add", ".")
    git(repo, "-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid", "commit", "-qm", "ignore tools")
    path = tmp_path / "isolated"
    context = {"target": str(repo), "task": "Preserve unleased artifacts"}

    def call(op, **kw):
        return resource("json", shared_core_binary, native_cli, {**context, "request": {"operation": op, "path": str(path), **kw}})

    first = call("worktree-create")
    proposal = call(
        "worktree-create",
        need="destructive-validation",
        reason="Separate mutable fixture",
        policy_revision=first["policy_revision"],
        policy_answer="permits-isolation",
    )
    resource("json", shared_core_binary, native_cli, proposal["action"])
    (path / "target").mkdir()
    (path / "target/valuable.txt").write_text("Not owned by the resource lifecycle")
    assert "action" not in call("worktree-remove")
    with pytest.raises(AssertionError, match="never adopted"):
        call("worktree-remove", disposable_outputs=["target"])
    assert (path / "target/valuable.txt").exists()
    (repo / "target").mkdir()
    (repo / "target/source.txt").write_text("Tracked source, not output")
    git(repo, "add", "-f", "target/source.txt")
    git(repo, "-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid", "commit", "-qm", "tracked root")
    path = tmp_path / "other"
    blocked = call(
        "worktree-create",
        need="destructive-validation",
        reason="A real need cannot dispose of source",
        policy_revision=first["policy_revision"],
        policy_answer="permits-isolation",
        disposable_outputs=["target"],
    )
    assert "action" not in blocked and any("source tree" in b for b in blocked["blockers"])
    assert not path.exists()
