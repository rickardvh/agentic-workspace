from __future__ import annotations

import os
import secrets
import time


def allocate_validation_run_id() -> str:
    """Return an opaque identity for one automatically owned local validation run."""
    return f"local-{time.time_ns():x}-{os.getpid():x}-{secrets.token_hex(8)}"


if __name__ == "__main__":
    print(allocate_validation_run_id())
