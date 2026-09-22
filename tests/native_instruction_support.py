import subprocess
from pathlib import Path

INSTRUCTION_DIR = Path(".agentic-workspace/instructions")


def _write(root: Path, name: str, text: str) -> Path:
    path = root / INSTRUCTION_DIR / f"{name}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def _admit(root: Path) -> str:
    subprocess.run(["git", "init", "-q", str(root)], check=True, capture_output=True)
    subprocess.run(["git", "add", "."], cwd=root, check=True, capture_output=True)
    subprocess.run(
        [
            "git",
            "-c",
            "user.name=Source owner",
            "-c",
            "user.email=owner@example.test",
            "-c",
            "commit.gpgsign=false",
            "commit",
            "-qm",
            "Admit exact instruction snapshot",
        ],
        cwd=root,
        check=True,
        capture_output=True,
    )
    revision = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip()
    (root / ".agentic-workspace/config.toml").write_text(f'[assurance]\ninstruction_revision = "{revision}"\n', encoding="utf-8")
    return revision
