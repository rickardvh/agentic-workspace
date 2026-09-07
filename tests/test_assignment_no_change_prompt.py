"""Public worker packets explain truthful empty returns without relaxing admission."""

from pathlib import Path

import pytest
from tests.test_external_operation_clients import _prepare_shared_worktree_assignment, _run_typescript_assignment

from agentic_workspace.generated_operations import assignment_export


@pytest.mark.parametrize("language", ["python", "typescript"])
def test_public_worker_prompt_explains_empty_patch(tmp_path: Path, language: str) -> None:
    identity, invocation, _ = _prepare_shared_worktree_assignment(tmp_path, run_id="no-change-prompt")
    args = {
        "assignment_id": "assign-shared",
        "assignment_revision": identity["revision"],
        "run_id": "no-change-prompt",
        "target_name": "worker",
        "transport": "internal",
    }
    result = (
        _run_typescript_assignment(tmp_path, "export", args)
        if language == "typescript"
        else assignment_export(args, target=tmp_path, invocation=invocation)
    )
    assert result["status"] == "handoff-prepared", result
    prompt_ref = next(ref for ref in result["artifact_refs"] if ref.endswith("prompt.md"))
    prompt = (tmp_path / prompt_ref).read_text().replace("`", "")
    assert 'When no changes are returned, set changed_paths to [] and patch to "".' in prompt
    assert "read-only, no-change, or stopped work" in prompt
    assert "report findings or blockers in summary and stop_conditions_hit; never invent a diff" in prompt
    assert "When changes are returned, the patch must be a complete git-compatible unified diff" in prompt
