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
        if "expected_revision" in payload:
            args = [str(native), "resources", "--input", "-"]
            payload = context
    elif surface == "json":
        args = [str(binary)]
        payload = {"resources": context}
    elif surface == "python":
        args = [
            sys.executable,
            "-c",
            "import json,sys; from agentic_workspace import resources; print(json.dumps(resources(json.load(sys.stdin))))",
        ]
        payload = context
    else:
        url = (ROOT / "src/cli/typescript/semantic-decision.mjs").as_uri()
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
        (path / "new.txt").write_text("Temporary bytes remain container-owned")
        assert call("scratch-remove", path=proposal["action"]["request"]["path"])["revision"] == removal["revision"]
        marker = path / ".aw-scratch.json"
        body = json.loads(marker.read_text())
        body["retention_reason"] = "Changed custody invalidates proposed cleanup"
        marker.write_text(json.dumps(body))
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


def resource_skill(root):
    for reference in [".agentic-workspace/skills/REGISTRY.json", ".agentic-workspace/skills/workspace-resources/SKILL.md"]:
        path = root / reference
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes((ROOT / reference).read_bytes())


def test_resource_exact_actions_scratch_and_fresh_recovery(tmp_path, shared_core_binary, native_cli):
    context = {"target": str(tmp_path), "task": "Scratch owner sequence"}

    def call(operation, **extra):
        proposal = resource("json", shared_core_binary, native_cli, {**context, "request": {"operation": operation, **extra}})
        return resource("json", shared_core_binary, native_cli, proposal["action"]) if "action" in proposal else proposal

    # Direct owners work without an optional skill and revalidate every effect.
    created = call("scratch-create")
    assert created["effect_outcome"] == "committed"
    path = Path(created["path"])
    (path / "temporary.txt").write_text("Recover me after response loss")
    # Every call is a new process. Repeating intent reobserves the same container.
    recovered = call("scratch-create")
    assert recovered["path"] == created["path"] and (path / "temporary.txt").exists()
    relative = path.relative_to(path.parents[3]).as_posix()
    retained = call("scratch-retain", path=relative, reason="Unfinished evidence")
    assert retained["effect_outcome"] == "committed"
    blocked = call("scratch-remove", path=relative)
    assert blocked["blockers"] and path.exists() and "action" not in blocked
    call("scratch-release", path=relative, reason="Evidence disposition settled")
    # Content volume and shape do not grant or revoke container disposal custody.
    nested = path / "nested/build-output"
    nested.mkdir(parents=True)
    with (nested / "large.bin").open("wb") as file:
        file.truncate(160 * 1024 * 1024)
    for index in range(2050):
        (nested / str(index)).touch()
    with pytest.raises(AssertionError, match="unknown resource operation"):
        call("scratch-prune", path=relative)
    removed = call("scratch-remove", path=relative)
    assert removed["effect_outcome"] == "committed" and not path.exists()
    with pytest.raises(AssertionError):
        call("scratch-create", expected_revision="old-effect")


def test_resource_procedure_yields_isolation_judgment_and_preserves_dirty_work(tmp_path, shared_core_binary, native_cli):
    repo = tmp_path / "repo"
    repo.mkdir()
    repository(repo)
    resource_skill(repo)
    path = tmp_path / "isolated"
    context = {"target": str(repo), "task": "Isolated destructive validation"}

    def call(operation, **extra):
        proposal = resource(
            "json", shared_core_binary, native_cli, {**context, "request": {"operation": operation, "path": str(path), **extra}}
        )
        return resource("json", shared_core_binary, native_cli, proposal["action"]) if "action" in proposal else proposal

    proposal = call("worktree-create")
    assert proposal["blockers"] and not path.exists()
    judgment = {
        "need": "destructive-validation",
        "reason": "Validation changes tracked fixtures",
        "policy_revision": proposal["policy_revision"],
        "policy_answer": "permits-isolation",
    }
    policy = repo / ".agentic-workspace/instructions/isolation.md"
    policy.parent.mkdir(parents=True)
    policy.write_text("Preserve the ordinary checkout; only necessary isolation is permitted.")
    stale = call("worktree-create", **judgment)
    assert stale["blockers"] and not path.exists()
    judgment["policy_revision"] = stale["policy_revision"]
    created = call("worktree-create", **judgment, disposable_outputs=["target"])
    assert created["effect_outcome"] == "committed"
    assert created["build_environment"]
    (path / "untracked.txt").write_text("Must preserve")
    blocked = call("worktree-remove")
    assert blocked["blockers"] and (path / "untracked.txt").exists()
    (path / "untracked.txt").unlink()
    assert call("worktree-remove")["effect_outcome"] == "committed"
    assert not path.exists()


@pytest.mark.parametrize("surface", ["native", "json"])
def test_worktree_policy_necessity_clean_teardown_and_integrity(tmp_path, shared_core_binary, native_cli, surface):
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
        return resource(surface, shared_core_binary, native_cli, {**context, "request": {"operation": op, "path": str(path), **extra}})

    quiet = call("worktree-create")
    assert "action" not in quiet and not path.exists()
    request = {
        "need": "destructive-validation",
        "reason": "Validation rewrites tracked fixtures and conflicts with current implementation work",
        "policy_revision": quiet["policy_revision"],
        "policy_answer": "permits-isolation",
    }
    proposal = call("worktree-create", **request)
    missing_policy = json.loads(json.dumps(proposal["action"]))
    missing_policy["request"]["policy_answer"] = None
    blocked = resource(surface, shared_core_binary, native_cli, missing_policy)
    assert blocked["blockers"] and "action" not in blocked and not path.exists()
    created = resource(surface, shared_core_binary, native_cli, proposal["action"])
    assert created["effect_outcome"] == "committed"
    assert path.exists()
    (path / "untracked.txt").write_text("must preserve")
    protected = call("worktree-remove")
    assert protected["blockers"] and "action" not in protected
    (path / "untracked.txt").unlink()
    remove = call("worktree-remove")
    assert resource(surface, shared_core_binary, native_cli, remove["action"])["effect_outcome"] == "committed"
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


def test_scratch_retention_and_missing_custody_preservation(tmp_path, shared_core_binary, native_cli):
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
    path.mkdir()  # Missing custody cannot authenticate even an empty directory.
    assert "action" not in call("scratch-remove")
    assert path.exists()
    with pytest.raises(AssertionError, match="one exact task container"):
        call("scratch-remove", path=".agentic-workspace/local/instructions")
    with pytest.raises(AssertionError, match="absolute external resource"):
        call("worktree-create", path=str(tmp_path))


def test_scratch_create_recovers_only_its_exact_empty_interruption(tmp_path, shared_core_binary, native_cli):
    context = {"target": str(tmp_path), "task": "Recover interrupted creation"}

    def call(operation, **extra):
        return resource("native", shared_core_binary, native_cli, {**context, "request": {"operation": operation, **extra}})

    proposal = call("scratch-create")
    path = Path(proposal["path"])
    path.mkdir(parents=True)  # Simulate a crash between mkdir and marker publication.
    assert "action" not in call("scratch-remove")
    recovery = call("scratch-create")  # Each public invocation uses a fresh process.
    assert recovery["snapshot"]["status"] == "empty-interrupted"
    assert recovery["path"] == proposal["path"]
    unknown = path / "unknown.txt"
    unknown.write_text("Do not adopt unauthenticated contents")
    for operation in ("scratch-create", "scratch-remove"):
        with pytest.raises(AssertionError):
            call(operation)
    with pytest.raises(AssertionError):
        resource("native", shared_core_binary, native_cli, recovery["action"])
    assert unknown.read_text() == "Do not adopt unauthenticated contents"
    unknown.unlink()  # Dispose only the test-created negative fixture.
    relative = recovery["action"]["request"]["path"]
    other = {**context, "task": "Another task", "request": {"operation": "scratch-create", "path": relative}}
    with pytest.raises(AssertionError, match="derived from the explicit current work"):
        resource("native", shared_core_binary, native_cli, other)
    fresh = call("scratch-create")
    created = resource("native", shared_core_binary, native_cli, fresh["action"])
    assert created["effect_outcome"] == "committed" and created["path"] == proposal["path"]
    assert json.loads((path / ".aw-scratch.json").read_text())["task"] == context["task"]
    resource("native", shared_core_binary, native_cli, call("scratch-remove")["action"])
    assert not path.exists()


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


def test_scratch_teardown_rechecks_custody_policy_and_siblings(tmp_path, shared_core_binary, native_cli):
    context = {"target": str(tmp_path), "task": "Container ownership"}

    def call(operation, **extra):
        return resource("native", shared_core_binary, native_cli, {**context, "request": {"operation": operation, **extra}})

    proposal = call("scratch-create")
    resource("native", shared_core_binary, native_cli, proposal["action"])
    path = Path(proposal["path"])
    sibling = path.parent / "unowned"
    sibling.mkdir()
    (sibling / "keep.txt").write_text("Unowned material")
    removal = call("scratch-remove")
    marker = path / ".aw-scratch.json"
    original = marker.read_bytes()
    marker.rename(path / "old-marker")
    marker.write_bytes(original)
    with pytest.raises(AssertionError, match="changed"):
        resource("native", shared_core_binary, native_cli, removal["action"])
    removal = call("scratch-remove")
    instructions = tmp_path / ".agentic-workspace/instructions"
    instructions.mkdir(parents=True)
    protection = instructions / "protect.md"
    protection.write_text("---\nprotect: [.agentic-workspace/local/scratch/**]\n---\nKeep this resource.\n")
    blocked = resource("native", shared_core_binary, native_cli, removal["action"])
    assert "action" not in blocked and blocked["effect_outcome"] == "not-invoked"
    assert path.exists()
    protection.unlink()
    # Every public invocation runs in a fresh process; current reentry is sufficient.
    fresh = call("scratch-remove")
    resource("native", shared_core_binary, native_cli, fresh["action"])
    assert not path.exists() and (sibling / "keep.txt").read_text() == "Unowned material"


def test_scratch_boundary_and_contained_directory_links(tmp_path, shared_core_binary, native_cli):
    context = {"target": str(tmp_path), "task": "Confined container cleanup"}

    def call(operation):
        return resource("json", shared_core_binary, native_cli, {**context, "request": {"operation": operation}})

    def directory_link(target, link):
        if os.name == "nt":
            import _winapi

            _winapi.CreateJunction(str(target), str(link))
        else:
            link.symlink_to(target, target_is_directory=True)

    proposal = call("scratch-create")
    resource("json", shared_core_binary, native_cli, proposal["action"])
    path = Path(proposal["path"])
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "keep.txt").write_text("Outside ownership boundary")
    directory_link(outside, path / "external-link")
    removal = call("scratch-remove")
    resource("json", shared_core_binary, native_cli, removal["action"])
    assert not path.exists() and (outside / "keep.txt").exists()
    directory_link(outside, path)
    with pytest.raises(AssertionError, match="link"):
        call("scratch-remove")
    assert (outside / "keep.txt").exists()
    # Remove only the test-created link, never its destination.
    path.rmdir() if os.name == "nt" else path.unlink()


@pytest.mark.parametrize("damage", ["missing", "oversized", "path", "target", "task"])
def test_scratch_custody_damage_preserves_container(tmp_path, shared_core_binary, native_cli, damage):
    context = {"target": str(tmp_path), "task": "Exact custody"}
    proposal = resource("json", shared_core_binary, native_cli, {**context, "request": {"operation": "scratch-create"}})
    resource("json", shared_core_binary, native_cli, proposal["action"])
    path = Path(proposal["path"])
    marker = path / ".aw-scratch.json"
    if damage == "missing":
        marker.unlink()
    elif damage == "oversized":
        marker.write_bytes(b" " * 16385)
    else:
        body = json.loads(marker.read_text())
        body[damage] = "mismatched"
        marker.write_text(json.dumps(body))
    removal = {**context, "request": {"operation": "scratch-remove"}}
    if damage == "missing":
        assert "action" not in resource("json", shared_core_binary, native_cli, removal)
    else:
        with pytest.raises(AssertionError):
            resource("json", shared_core_binary, native_cli, removal)
    assert path.exists()


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


@pytest.mark.parametrize("surface", ["native", "json"])
def test_resource_route_applicability_matches_ordinary_and_composed_entry(tmp_path, shared_core_binary, native_cli, surface):
    from tests.test_native_public_cli import consume

    for ref in [".agentic-workspace/skills/REGISTRY.json", ".agentic-workspace/skills/workspace-resources/SKILL.md"]:
        dest = tmp_path / ref
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes((ROOT / ref).read_bytes())
    registry = tmp_path / "tools/skills/REGISTRY.json"
    registry.parent.mkdir(parents=True)
    registry.write_text(json.dumps({"skills": [{"id": "sample", "semantic_routes": ["sample/protected"]}]}))
    source = tmp_path / ".agentic-workspace/instructions/resource.md"
    source.parent.mkdir(parents=True)
    policy = "---\npaths: [.agentic-workspace/local/scratch/**]\nroutes: [sample/protected]\nprotect: [.agentic-workspace/local/scratch/**]\n---\nPreserve the selected resource.\n"
    source.write_text(policy)
    context = {"target": str(tmp_path), "task": "Prepare temporary analysis material"}

    def call(**material):
        return resource(surface, shared_core_binary, native_cli, {**context, "request": {"operation": "scratch-create", **material}})

    unresolved = call()
    assert "action" not in unresolved and any("applicability" in b for b in unresolved["blockers"])
    selected = next(r for r in unresolved["route_requests"] if r["request_kind"] == "semantic-routes/select/v1")
    selected["arguments"] = {"posture": "selected", "routes": ["sample/protected"]}
    assert "action" not in call(route_request=selected)
    # Declared path AND route remains conjunctive: an unrelated path is quiet.
    ordinary = consume("json", shared_core_binary, native_cli, {**context, "request": selected})
    assert ordinary["instructions"]["sources"][0]["applicable"] is False
    source.write_text(policy.replace("paths: [.agentic-workspace/local/scratch/**]\n", ""))
    ordinary = consume("json", shared_core_binary, native_cli, {**context, "request": selected})
    assert ordinary["instructions"]["sources"][0]["applicable"] is True
    assert "action" not in call(route_request=selected)
    selected["arguments"] = {"posture": "none", "routes": []}
    proposal = call(route_request=selected)
    assert "action" in proposal
    (tmp_path / "unrelated.txt").write_text("irrelevant")
    assert call(route_request=selected)["revision"] == proposal["revision"]
    # Route discovery drift cannot reuse a settled negative to waive protection.
    registry.write_text(json.dumps({"skills": [{"id": "sample", "semantic_routes": ["sample/protected", "sample/new"]}]}))
    assert "action" not in call(route_request=selected)
    fresh = call()
    negative = next(r for r in fresh["route_requests"] if r["request_kind"] == "semantic-routes/select/v1")
    negative["arguments"] = {"posture": "none", "routes": []}
    proposed = call(route_request=negative)
    created = resource(surface, shared_core_binary, native_cli, proposed["action"])
    assert created["effect_outcome"] == "committed"
    assert proposed["action"]["request"]["route_request"] == negative
    removed = resource(
        surface,
        shared_core_binary,
        native_cli,
        {
            **context,
            "request": {
                "operation": "scratch-remove",
                "path": proposed["action"]["request"]["path"],
                "route_request": negative,
            },
        },
    )
    assert resource(surface, shared_core_binary, native_cli, removed["action"])["effect_outcome"] == "committed"


def test_cli_exact_resource_envelope_preserves_context_and_currentness(tmp_path, shared_core_binary, native_cli):
    import copy

    context = {"target": str(tmp_path), "task": "Bounded CLI lifecycle", "changed": ["source.txt"]}
    unrelated = tmp_path / "source.txt"
    unrelated.write_text("Preserve unrelated source")

    def propose(operation, **extra):
        return resource("native", shared_core_binary, native_cli, {**context, "request": {"operation": operation, **extra}})

    def execute(action, *flags):
        return subprocess.run(
            [str(native_cli), "resources", "--input", "-", *flags],
            input=json.dumps(action),
            text=True,
            capture_output=True,
            cwd=ROOT,
        )

    proposal = propose("scratch-create")
    action = proposal["action"]
    path = Path(proposal["path"])
    assert not path.exists()
    control = resource("json", shared_core_binary, native_cli, {**context, "request": {"operation": "scratch-create"}})
    assert control["action"] == action
    for flags in [("--target", str(ROOT)), ("--task", "other"), ("--changed", "other.txt")]:
        rejected = execute(action, *flags)
        assert rejected.returncode == 2 and "conflicts with the exact input envelope" in rejected.stderr
        assert not path.exists()
    for field, value in [("target", str(ROOT)), ("task", "other"), ("changed", ["other.txt"])]:
        forged = copy.deepcopy(action)
        forged[field] = value
        rejected = execute(forged)
        assert rejected.returncode != 0 or json.loads(rejected.stdout).get("effect_outcome") != "committed"
        assert not path.exists()
    # Matching flags, including native canonical-path spelling, assert rather than override.
    result = execute(action, "--target", str(tmp_path), "--task", context["task"], "--changed", "source.txt")
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)["effect_outcome"] == "committed" and path.is_dir()
    stale = execute(action)
    assert stale.returncode != 0 and "changed" in stale.stderr
    removal = propose("scratch-remove", path=action["request"]["path"])
    marker = path / ".aw-scratch.json"
    body = json.loads(marker.read_text())
    body["retention_reason"] = "Changed custody stales the cleanup proposal"
    marker.write_text(json.dumps(body))
    assert execute(removal["action"]).returncode != 0 and path.exists()
    fresh = propose("scratch-remove", path=action["request"]["path"])
    result = execute(fresh["action"])
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)["effect_outcome"] == "committed" and not path.exists()
    assert unrelated.read_text() == "Preserve unrelated source"

    # Policy drift cannot be bypassed by carrying an otherwise well-formed envelope.
    pending = propose("scratch-create")
    policy = tmp_path / ".agentic-workspace/instructions/resource.md"
    policy.parent.mkdir(parents=True)
    policy.write_text("---\nprotect: [.agentic-workspace/local/scratch/**]\n---\nPreserve resources.\n")
    rejected = execute(pending["action"])
    assert rejected.returncode != 0 or json.loads(rejected.stdout).get("effect_outcome") != "committed"
    assert not path.exists() and "action" not in propose("scratch-create")
