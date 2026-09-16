"""Admit a PyPI Linux wheel tag without changing the proven native binary pair."""

from __future__ import annotations

import argparse
import re
import subprocess
from pathlib import Path


def admit(directory):
    wheels = list(directory.glob("agentic_workspace-*-linux_x86_64.whl"))
    if len(wheels) != 1:
        raise ValueError("Expected one hosted Linux x86_64 wheel before admission")
    wheel = wheels[0]
    audit = subprocess.check_output(["uvx", "--from", "auditwheel==6.4.2", "auditwheel", "show", str(wheel)], text=True)
    match = re.search(r'following platform tag:\s*"(manylinux_2_([0-9]+)_x86_64)"', audit)
    if not match or int(match[2]) > 39:
        raise ValueError("Wheel does not meet the admitted manylinux_2_39_x86_64 ABI; no relabel or repair allowed")
    # wheel tags rewrites only wheel metadata/RECORD. No patchelf repair is used:
    # Python, npm and native archive must still contain byte-identical executables.
    subprocess.run(
        ["uvx", "--from", "wheel==0.45.1", "wheel", "tags", "--platform-tag", "manylinux_2_39_x86_64", "--remove", str(wheel)], check=True
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("artifact_dir", type=Path)
    admit(parser.parse_args().artifact_dir)
