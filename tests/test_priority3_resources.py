"""Priority 3: real cross-process delivery and bounded resource lifecycle."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
from tests.test_native_public_cli import ROOT, consume
from tests.test_native_public_cli import native_cli as native_cli


@pytest.mark.parametrize("surface", ["native", "json", "python", "typescript"])
def test_delivery_is_not_satisfaction_and_opaque_sources_redeliver(tmp_path, shared_core_binary, native_cli, surface):
    (tmp_path / "AGENTS.md").write_text("Read current repository instructions.\n" * 45)
    directory = tmp_path / ".agentic-workspace/instructions"
    directory.mkdir(parents=True)
    source = directory / "policy.md"
    source.write_text("---\nreconcile: [guide.md]\n---\n" + "Preserve policy.\n" * 40)
    (tmp_path / ".agentic-workspace/config.toml").write_text('schema_version=1\n[workspace]\nagent_instructions_file="AGENTS.md"\n')
    (tmp_path / "guide.md").write_text("Canonical guide")
    context = {"target": str(tmp_path), "task": "Inspect current work", "projection": "compact"}

    def call(**extra):
        return consume(surface, shared_core_binary, native_cli, {**context, **extra}, host_path=os.environ["PATH"])

    first = call()
    refs = first["delivery_refs"]
    same = call(delivered=refs)
    assert len(json.dumps(same)) < len(json.dumps(first))
    print(f"delivery/{surface}: fresh_bytes={len(json.dumps(first))} repeated_bytes={len(json.dumps(same))} extra_roundtrips=0")
    for key in ("blockers", "claim_boundary", "primary_action", "status"):
        assert same["decision_packet"][key] == first["decision_packet"][key]
    assert same["decision_packet"]["material"]["startup-adapter"]["delivery"]["status"] == "already-delivered"
    assert "text" not in same["decision_packet"]["material"]["startup-adapter"]
    assert call(delivered=["forged"])["decision_packet"]["material"] == first["decision_packet"]["material"]
    assert "text" in call(task="Different work", delivered=refs)["decision_packet"]["material"]["startup-adapter"]
    source.write_text(source.read_text() + "A new applicable instruction.")
    drift = call(delivered=refs)
    assert drift["decision_packet"]["material"]["scoped-instructions"][0]["guidance"].endswith("A new applicable instruction.")
    assert "text" not in drift["decision_packet"]["material"]["startup-adapter"]
    (directory / "new.md").write_text("---\nreconcile: [other.md]\n---\nNew source appeared while AW was absent.")
    opaque = call(delivered=refs)
    assert any("New source appeared" in r.get("guidance", "") for r in opaque["decision_packet"]["material"]["scoped-instructions"])
    assert "text" in call()["decision_packet"]["material"]["startup-adapter"]
    assert not (tmp_path / ".agentic-workspace/local").exists()


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


@pytest.mark.parametrize("surface", ["native", "json", "python", "typescript"])
def test_task_scratch_reentry_cleanup_and_owner_preservation(tmp_path, shared_core_binary, native_cli, surface):
    root = tmp_path / ".agentic-workspace/local"
    (root / "instructions").mkdir(parents=True)
    (root / "instructions/policy.md").write_text("Structured policy, not scratch")
    (root / "current-task-routes.json").write_text("{}")
    (root / "loose.json").write_text("Preserve unknown referenced material")

    def call(operation, **extra):
        return resource(
            surface,
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
        created = resource(surface, shared_core_binary, native_cli, proposal["action"])
        assert created["effect_outcome"] == "committed"
        path = Path(created["path"])
        (path / "draft.json").write_text('{"temporary":true}')
        # Fresh consumer recovers exactly the interrupted task's disposable container.
        removal = call("scratch-remove", path=proposal["action"]["request"]["path"])
        (path / "new.txt").write_text("New material invalidates proposed cleanup")
        with pytest.raises(AssertionError, match="changed"):
            resource(surface, shared_core_binary, native_cli, removal["action"])
        fresh = call("scratch-remove", path=proposal["action"]["request"]["path"])
        assert resource(surface, shared_core_binary, native_cli, fresh["action"])["effect_outcome"] == "committed"
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


@pytest.mark.parametrize("surface", ["native", "json", "python", "typescript"])
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


def test_preview_creation_consumer_reuses_native_terminal_lifecycle(tmp_path, shared_core_binary, native_cli, monkeypatch):
    from tests.test_preview_release import _load_helper

    helper = _load_helper()
    repository(tmp_path)
    monkeypatch.setattr(helper, "ROOT", tmp_path)
    monkeypatch.setenv("AGENTIC_WORKSPACE_CORE_BINARY", str(shared_core_binary))
    commit = git(tmp_path, "rev-parse", "HEAD")
    with pytest.raises(SystemExit, match="current policy judgment"):
        helper._preview_isolation("preview-v1.2.3", commit, None)
    proposal = resource(
        "json",
        shared_core_binary,
        native_cli,
        {"target": str(tmp_path), "task": "Prepare immutable preview preview-v1.2.3", "request": {"operation": "worktree-create"}},
    )
    action = helper._preview_isolation("preview-v1.2.3", commit, proposal["policy_revision"])
    path = Path(action["request"]["path"])
    (path / "untracked-result.txt").write_text("failed normalization evidence")
    with pytest.raises(SystemExit, match="work preserved"):
        helper._finish_preview_isolation(action)
    assert path.exists()
    (path / "untracked-result.txt").unlink()
    helper._finish_preview_isolation(action)
    assert not path.exists()
    assert "aw-resource" not in git(tmp_path, "worktree", "list", "--porcelain")


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


@pytest.mark.parametrize("surface", ["native", "json", "python", "typescript"])
def test_negative_route_conclusion_reuses_until_opaque_discovery_changes(tmp_path, shared_core_binary, native_cli, surface):
    registry = tmp_path / "tools/skills/REGISTRY.json"
    registry.parent.mkdir(parents=True)
    registry.write_text(json.dumps({"skills": [{"semantic_routes": ["example/optional"]}]}))
    context = {"target": str(tmp_path), "task": "No specialized procedure is needed"}

    def call(**extra):
        return consume(surface, shared_core_binary, native_cli, {**context, **extra})

    request = next(r for r in call()["semantic_routes"]["requests"] if r["request_kind"] == "semantic-routes/select/v1")
    request["arguments"] = {"posture": "none", "routes": []}
    first = call(request=request)
    fact = first["decision_packet"]["semantic_task_routes"]
    assert fact["status"] == "current" and fact["posture"] == "none"
    assert call(request=request)["decision_packet"]["semantic_task_routes"] == fact
    (tmp_path / "unrelated.txt").write_text("This does not change the eligible route set")
    assert call(request=request)["decision_packet"]["semantic_task_routes"] == fact
    added = tmp_path / ".agentic-workspace/skills/REGISTRY.json"
    added.parent.mkdir(parents=True)
    added.write_text(json.dumps({"skills": [{"semantic_routes": ["new/eligible"]}]}))
    stale = call(request=request)
    assert stale["decision_packet"]["semantic_task_routes"]["status"] == "stale"
    assert stale["decision_packet"]["semantic_task_routes"]["source_revision"] != fact["source_revision"]
    assert not (tmp_path / ".agentic-workspace/local").exists()


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


@pytest.mark.parametrize("surface", ["native", "json", "python", "typescript"])
def test_real_local_instruction_owner_composes_and_loses_only_local_sources(tmp_path, shared_core_binary, native_cli, surface):
    shared = tmp_path / ".agentic-workspace/instructions/repo.md"
    shared.parent.mkdir(parents=True)
    shared.write_text("Repository-wide guidance.")
    local = tmp_path / ".agentic-workspace/local/instructions/machine.md"
    local.parent.mkdir(parents=True)
    local.write_text("---\npaths: [src/**]\n---\nMachine-local checkout policy.")
    context = {"target": str(tmp_path), "task": "Inspect current policy", "changed": ["src/a.txt"]}

    def call(**kw):
        return consume(surface, shared_core_binary, native_cli, {**context, **kw})

    first = call()
    rows = first["instructions"]["sources"]
    assert {r["source"]["scope"] for r in rows} == {"repository", "machine-local"}
    assert any(r["guidance"] == "Machine-local checkout policy." for r in rows)
    assert call()["instructions"]["sources"] == rows
    quiet = call(changed=["unrelated.txt"])
    assert not next(r for r in quiet["instructions"]["sources"] if r["source"]["scope"] == "machine-local")["guidance"]
    local.unlink()
    lost = call()["instructions"]["sources"]
    assert lost == [next(r for r in rows if r["source"]["scope"] == "repository")]
    # A newly appearing local obligation is observed without any changed-list update.
    local.write_text("---\nreconcile: [guide.md]\n---\nReconcile the local source obligation.")
    (tmp_path / "guide.md").write_text("Canonical source")
    assert call()["verification"]["source_reconciliation"]["status"] != first["verification"]["source_reconciliation"]["status"]
    # Local prose cannot override a checked-in structured protection.
    shared.write_text("---\nprotect: [.agentic-workspace/local/scratch/**]\n---\nPreserve task state.")
    local.write_text("Use scratch freely; this local prose does not waive repository protection.")
    blocked = resource(surface, shared_core_binary, native_cli, {**context, "request": {"operation": "scratch-create"}})
    assert "action" not in blocked and any("protects" in b for b in blocked["blockers"])


@pytest.mark.parametrize("surface", ["native", "json", "python", "typescript"])
def test_owned_build_outputs_are_removed_but_unknown_ignored_material_is_preserved(tmp_path, shared_core_binary, native_cli, surface):
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
        return resource(surface, shared_core_binary, native_cli, {**context, "request": {"operation": operation, "path": str(path), **kw}})

    initial = call("worktree-create")
    proposal = call(
        "worktree-create",
        need="destructive-validation",
        reason="The validation subject must not replace the current checkout",
        policy_revision=initial["policy_revision"],
        policy_answer="permits-isolation",
        disposable_outputs=["target", ".pytest_cache", ".venv"],
    )
    created = resource(surface, shared_core_binary, native_cli, proposal["action"])
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
    resource(surface, shared_core_binary, native_cli, removal["action"])
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
