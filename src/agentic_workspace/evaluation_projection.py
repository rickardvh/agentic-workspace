from __future__ import annotations

import hashlib
import json
from typing import Any, Mapping

SPECIALIST_EVALUATION_PROJECTION_KIND = "agentic-workspace/specialist-evaluation-projection/v1"


def specialist_evaluation_projection(
    *,
    domain: str,
    producer: str,
    source_identity: str,
    source_ref: str,
    criterion: str,
    result: str,
    facts: Mapping[str, Any],
) -> dict[str, Any]:
    """Build the lossless shared-Evaluation view of a specialist producer result."""
    identity_source = {
        "domain": domain,
        "producer": producer,
        "source_identity": source_identity,
        "source_ref": source_ref,
    }
    observation_id = (
        "specialist:" + hashlib.sha256(json.dumps(identity_source, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()[:24]
    )
    return {
        "kind": SPECIALIST_EVALUATION_PROJECTION_KIND,
        "observation_id": observation_id,
        "domain": domain,
        "producer": producer,
        "source_identity": source_identity,
        "source_ref": source_ref,
        "criterion": criterion,
        "result": result,
        "facts": dict(facts),
        "lifecycle_owner": "evaluation.observe",
        "delivery_owner": "evaluation report/delivery operations",
        "specialist_authority": "canonical source facts and domain-specific analysis only",
        "residue_policy": "projection is embedded in the canonical producer result; admission creates only the Evaluation observation",
    }
