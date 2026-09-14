"""Install-time serialization of ownership descriptors; never a static runtime."""

from __future__ import annotations

import hashlib
import json
import tomllib

LEDGER = ".agentic-workspace/OWNERSHIP.toml"
PROFILE = ".agentic-workspace/READING.json"


def render(ledger_text: str) -> str:
    """Copy only declared read metadata, not repository/domain state."""
    canonical = ledger_text.replace("\r\n", "\n").encode("utf-8")
    ledger = tomllib.loads(canonical.decode())
    if ledger.get("schema_version") != 1:
        raise ValueError("Unsupported ownership ledger; preserve the source and restore a compatible installed profile.")
    entries = [
        {"concern": row["concern"], "owner": row["owner"], **row["read"]} for row in ledger.get("authority_surfaces", []) if "read" in row
    ]
    return (
        json.dumps(
            {
                "kind": "agentic-workspace/repository-read-profile/v1",
                "source": {
                    "path": LEDGER,
                    "git_blob_sha1": hashlib.sha1(b"blob " + str(len(canonical)).encode() + b"\0" + canonical).hexdigest(),
                },
                "authority": "orientation-only; no mutation, effect, proof, completion or issue-close authority",
                "currentness": "Read one repository revision; record each selected path and provider blob identity. Reconsider changed selected sources/dependencies; unrelated blobs do not invalidate the reading. Source identity is not truth or runtime admission.",
                "recovery": "If kind/source identity is absent, incompatible or stale, or a selected ref is missing/malformed, keep only directly observed repository facts. Follow the exact owner ref in OWNERSHIP.toml; ask a runtime-capable maintainer to restore the generated profile or reconcile the source. Do not guess an operating decision.",
                "entries": entries,
            },
            indent=2,
        )
        + "\n"
    )
