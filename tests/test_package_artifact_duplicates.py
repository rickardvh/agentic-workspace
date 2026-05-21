from __future__ import annotations

import json
import sys
import tarfile
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from zipfile import ZipFile

CHECKER_PATH = Path(__file__).resolve().parents[1] / "scripts" / "check" / "check_package_artifact_duplicates.py"
SPEC = spec_from_file_location("check_package_artifact_duplicates", CHECKER_PATH)
assert SPEC is not None and SPEC.loader is not None
checker = module_from_spec(SPEC)
sys.modules[SPEC.name] = checker
SPEC.loader.exec_module(checker)


def test_duplicate_member_checker_flags_wheel_duplicate(tmp_path: Path) -> None:
    artifact = tmp_path / "dist" / "demo-0.1-py3-none-any.whl"
    artifact.parent.mkdir()
    with ZipFile(artifact, "w") as archive:
        archive.writestr("demo/__init__.py", "")
        archive.writestr("demo/__init__.py", "# duplicate")

    result = checker.check_artifacts(tmp_path, [artifact])

    assert result["status"] == "fail"
    assert result["findings"] == [
        {
            "path": "dist/demo-0.1-py3-none-any.whl",
            "duplicate_members": ["demo/__init__.py"],
            "duplicate_member_count": 1,
        }
    ]


def test_duplicate_member_checker_flags_sdist_duplicate(tmp_path: Path) -> None:
    source = tmp_path / "source.txt"
    source.write_text("content", encoding="utf-8")
    artifact = tmp_path / "dist" / "demo-0.1.tar.gz"
    artifact.parent.mkdir()
    with tarfile.open(artifact, "w:gz") as archive:
        archive.add(source, arcname="demo/source.txt")
        archive.add(source, arcname="demo/source.txt")

    assert checker.duplicate_members(artifact) == ["demo/source.txt"]


def test_duplicate_member_checker_json_main_reports_clean_artifact(tmp_path: Path, capsys) -> None:
    artifact = tmp_path / "dist" / "demo-0.1-py3-none-any.whl"
    artifact.parent.mkdir()
    with ZipFile(artifact, "w") as archive:
        archive.writestr("demo/__init__.py", "")

    assert checker.main(["--root", str(tmp_path), "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "pass"
    assert payload["artifact_count"] == 1
