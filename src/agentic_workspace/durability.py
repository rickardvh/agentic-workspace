from __future__ import annotations

import json
import os
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator


def atomic_write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def atomic_create_json(path: Path, value: Any) -> None:
    """Create a path without overwriting content that appeared concurrently."""

    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.create")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    try:
        os.link(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def _process_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True


@contextmanager
def owner_process_lock(root: Path, owner: str, *, timeout: float = 30.0) -> Iterator[None]:
    """Serialize one effect owner across processes without locking reads."""

    safe_owner = "".join(character if character.isalnum() or character in "-." else "_" for character in owner)
    lock = root / ".agentic-workspace" / "local" / "locks" / f"{safe_owner}.lock"
    lock.parent.mkdir(parents=True, exist_ok=True)
    deadline = time.monotonic() + timeout
    while True:
        try:
            lock.mkdir()
            (lock / "owner.json").write_text(json.dumps({"pid": os.getpid()}), encoding="utf-8")
            break
        except FileExistsError:
            try:
                record = json.loads((lock / "owner.json").read_text(encoding="utf-8"))
                pid = int(record.get("pid", 0))
            except (OSError, ValueError, TypeError, json.JSONDecodeError):
                pid = 0
            try:
                lock_age = time.time() - lock.stat().st_mtime
            except OSError:
                lock_age = 0.0
            if pid <= 0 and lock_age < 2.0:
                if time.monotonic() >= deadline:
                    raise TimeoutError(f"effect owner is busy: {owner}; retry the same invocation")
                time.sleep(0.02)
                continue
            if not _process_alive(pid):
                try:
                    (lock / "owner.json").unlink(missing_ok=True)
                    lock.rmdir()
                except OSError:
                    pass
                continue
            if time.monotonic() >= deadline:
                raise TimeoutError(f"effect owner is busy: {owner}; retry the same invocation")
            time.sleep(0.02)
    try:
        yield
    finally:
        try:
            (lock / "owner.json").unlink(missing_ok=True)
            lock.rmdir()
        except OSError:
            pass
