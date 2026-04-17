from __future__ import annotations

import json
from pathlib import Path
from typing import Any

REPO_FRICTION_LARGE_FILE_THRESHOLD = 400
REPO_FRICTION_CONCEPT_SURFACE_THRESHOLD = 200
REPO_FRICTION_MAX_HOTSPOTS = 5
REPO_FRICTION_SCAN_SUFFIXES = {
    ".md",
    ".py",
    ".toml",
    ".json",
    ".yaml",
    ".yml",
    ".txt",
}
REPO_FRICTION_SKIP_DIRS = {
    ".git",
    ".hg",
    ".svn",
    "__pycache__",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".venv",
    "node_modules",
    "dist",
    "build",
}

STANDING_INTENT_CANONICAL_DOC = "docs/standing-intent-contract.md"


def output_contract_payload(
    *,
    optimization_bias: str,
    optimization_bias_source: str,
    bias_payload: dict[str, Any],
    surface: str,
) -> dict[str, Any]:
    return {
        "owner_surface": "workspace",
        "surface": surface,
        "optimization_bias": optimization_bias,
        "optimization_bias_source": optimization_bias_source,
        "rule": (
            "Optimization bias may change rendering density and residue style only; "
            "it must not change execution method or canonical state semantics."
        ),
        "applies_to": [
            "derived reporting density",
            "rendered human-facing view density",
            "durable residue style when truth stays unchanged",
        ],
        "surface_boundary": bias_payload["surface_boundary"],
        "report_density": bias_payload["report_density"],
        "residue_density": bias_payload["residue_density"],
        "rendered_view_style": bias_payload["rendered_view_style"],
        "must_not_change": list(bias_payload["does_not_affect"]),
    }


def standing_intent_payload(
    *,
    target_root: Path,
    config_policy: dict[str, Any],
    active_planning: dict[str, Any] | None,
    memory_installed: bool,
) -> dict[str, Any]:
    classes = [
        _standing_intent_class_payload(
            intent_class="config_policy",
            summary="Stable repo policy that should be queryable and preferably machine-readable.",
            default_owner="agentic-workspace.toml",
            authoritative_kind="policy",
            durable_when=[
                "the guidance should survive startup without rereading prose",
                "the repo benefits from a compact machine-readable policy surface",
            ],
            transient_when=[
                "the guidance is only local execution choreography",
                "the rule is still too vague to encode as repo policy safely",
            ],
            stronger_home="config plus checks when verification is needed",
        ),
        _standing_intent_class_payload(
            intent_class="repo_doctrine",
            summary="Broad repo doctrine or design constraints that explain how the repo should be run.",
            default_owner="AGENTS.md or docs/design-principles.md",
            authoritative_kind="doctrine",
            durable_when=[
                "the guidance is repo-wide rather than task-local",
                "the guidance should remain legible as shared doctrine rather than a toggle",
            ],
            transient_when=[
                "the guidance only matters for the current active slice",
                "the better owner is actually config, Memory, or checks",
            ],
            stronger_home="config policy or enforceable workflow when prose becomes too weak",
        ),
        _standing_intent_class_payload(
            intent_class="durable_understanding",
            summary="Repo-specific interpretive understanding that lowers rediscovery cost without becoming hard policy.",
            default_owner="Memory",
            authoritative_kind="interpretive-understanding",
            durable_when=[
                "future work would pay rediscovery cost without the note",
                "the content explains repo-specific understanding rather than a hard rule",
            ],
            transient_when=[
                "a canonical doc or stronger owner now explains it better",
                "the note is only a local convenience or stale residue",
            ],
            stronger_home="canonical docs, config, or checks when the understanding becomes shared rule rather than interpretation",
        ),
        _standing_intent_class_payload(
            intent_class="active_directional_intent",
            summary="Bounded current direction that should steer work now without being mistaken for timeless doctrine.",
            default_owner="TODO.md or docs/execplans/",
            authoritative_kind="active-direction",
            durable_when=[
                "the direction still matters after the immediate chat turn",
                "the repo needs a bounded active owner surface for continuation",
            ],
            transient_when=[
                "the direction ends with the current local step",
                "the work has already been completed or archived",
            ],
            stronger_home="doctrine, policy, or checks only after the direction stops being lane-local",
        ),
        _standing_intent_class_payload(
            intent_class="enforceable_workflow",
            summary="Guidance that should be verified through checks, validation commands, or workflow tooling instead of prose alone.",
            default_owner="scripts/check/, validation workflows, or config plus checks",
            authoritative_kind="enforceable",
            durable_when=[
                "the guidance should be verifiable rather than merely remembered",
                "drift should be detectable through checks or validation",
            ],
            transient_when=[
                "the guidance is still exploratory and not ready for enforcement",
                "prose remains the strongest justified home for now",
            ],
            stronger_home="checks or validation workflows with doctrine left as explanation only",
        ),
        _standing_intent_class_payload(
            intent_class="temporary_local_guidance",
            summary="Useful local guidance that should stay transient unless repetition proves broader durable value.",
            default_owner="current execution context only",
            authoritative_kind="temporary",
            durable_when=[
                "none by default; promote only after repeated reminder cost or broader impact appears",
            ],
            transient_when=[
                "the guidance ends with the current bounded step",
                "the guidance is tool- or model-specific convenience only",
            ],
            stronger_home="reclassify into one of the durable standing-intent classes when warranted",
        ),
    ]

    effective_items = [
        _config_policy_effective_item(config_policy=config_policy),
        _repo_doctrine_effective_item(target_root=target_root),
        _durable_understanding_effective_item(memory_installed=memory_installed),
        _active_directional_intent_effective_item(active_planning=active_planning),
        _enforceable_workflow_effective_item(target_root=target_root),
    ]
    in_force_count = sum(1 for item in effective_items if item["status"] == "present")
    return {
        "canonical_doc": STANDING_INTENT_CANONICAL_DOC,
        "schema_version": "standing-intent-report/v1",
        "promotion_rule": ("Promote durable repo-wide guidance into the strongest existing owner surface instead of leaving it in chat."),
        "precedence_order": _standing_intent_precedence_order(),
        "supersession_rules": _standing_intent_supersession_rules(),
        "stronger_home_model": _standing_intent_stronger_home_model(
            target_root=target_root,
            config_policy=config_policy,
        ),
        "classes": classes,
        "effective_view": {
            "conflict_rule": (
                "Explicit current human instruction outranks all durable standing intent. Within durable repo state, "
                "active lane-local direction may narrow broader doctrine for the current slice, but checked-in policy "
                "and enforceable workflow still outrank broader interpretive guidance."
            ),
            "sources_considered": [
                "agentic-workspace.toml",
                "AGENTS.md",
                "docs/design-principles.md",
                "TODO.md and docs/execplans/",
                "Memory report/install state",
                "scripts/check/",
            ],
            "in_force_count": in_force_count,
            "items": effective_items,
        },
    }


def setup_discovery_payload(
    *,
    target_root: Path,
    status_payload: dict[str, Any],
    active_todo_surface: str | None,
) -> dict[str, list[dict[str, Any]]]:
    memory_candidates: list[dict[str, Any]] = []
    planning_candidates: list[dict[str, Any]] = []
    ambiguous: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()

    def _add_candidate(
        bucket: list[dict[str, Any]],
        *,
        surface: str,
        reason: str,
        confidence: float,
        refs: list[str],
    ) -> None:
        key = (surface, reason)
        if key in seen:
            return
        seen.add(key)
        bucket.append(
            {
                "surface": surface,
                "reason": reason,
                "confidence": confidence,
                "refs": refs,
            }
        )

    for surface, reason, confidence, refs in (
        (
            "docs/delegated-judgment-contract.md",
            "bounded human/agent decision boundaries",
            0.94,
            ["docs/delegated-judgment-contract.md"],
        ),
        (
            "docs/resumable-execution-contract.md",
            "restart and continuation boundaries",
            0.91,
            ["docs/resumable-execution-contract.md"],
        ),
        (
            "docs/capability-aware-execution.md",
            "task-shape and capability-fit rules",
            0.89,
            ["docs/capability-aware-execution.md"],
        ),
        (
            "docs/execution-summary-contract.md",
            "compact execution outcome and follow-through shape",
            0.87,
            ["docs/execution-summary-contract.md"],
        ),
    ):
        if (target_root / surface).exists():
            _add_candidate(memory_candidates, surface=surface, reason=reason, confidence=confidence, refs=refs)

    if (target_root / "TODO.md").exists():
        _add_candidate(
            planning_candidates,
            surface="TODO.md",
            reason="active queue carries the current work slice",
            confidence=0.94,
            refs=["TODO.md"],
        )
    if active_todo_surface and active_todo_surface != "TODO.md" and (target_root / active_todo_surface).exists():
        _add_candidate(
            planning_candidates,
            surface=active_todo_surface,
            reason="active execplan carries the current bounded work slice",
            confidence=0.96,
            refs=[active_todo_surface, "TODO.md"],
        )

    if (target_root / "ROADMAP.md").exists():
        _add_candidate(
            ambiguous,
            surface="ROADMAP.md",
            reason="long-horizon follow-ons should not be seeded without promotion",
            confidence=0.82,
            refs=["ROADMAP.md"],
        )

    for warning in status_payload.get("warnings", []):
        if isinstance(warning, dict):
            surface = str(warning.get("path") or "workspace")
            message = str(warning.get("message") or "requires review")
        else:
            surface = "workspace"
            message = str(warning)
        _add_candidate(
            ambiguous,
            surface=surface,
            reason=message,
            confidence=0.5,
            refs=[surface],
        )

    return {
        "memory_candidates": memory_candidates,
        "planning_candidates": planning_candidates,
        "ambiguous": ambiguous,
    }


def _standing_intent_class_payload(
    *,
    intent_class: str,
    summary: str,
    default_owner: str,
    authoritative_kind: str,
    durable_when: list[str],
    transient_when: list[str],
    stronger_home: str,
) -> dict[str, Any]:
    return {
        "class": intent_class,
        "summary": summary,
        "default_owner": default_owner,
        "authoritative_kind": authoritative_kind,
        "durable_when": durable_when,
        "transient_when": transient_when,
        "stronger_home": stronger_home,
    }


def _standing_intent_precedence_order() -> list[dict[str, Any]]:
    return [
        {
            "rank": 1,
            "source": "explicit_current_human_instruction",
            "authority": "human-current-intent",
            "rule": "Current explicit user direction outranks durable standing intent when they conflict.",
        },
        {
            "rank": 2,
            "source": "active_directional_intent",
            "authority": "current-lane-direction",
            "rule": "Active planning direction governs the current bounded slice unless it conflicts with checked-in hard policy.",
        },
        {
            "rank": 3,
            "source": "config_policy",
            "authority": "checked-in-policy",
            "rule": "Checked-in config policy outranks broader doctrine and interpretive understanding.",
        },
        {
            "rank": 4,
            "source": "enforceable_workflow",
            "authority": "verified-workflow",
            "rule": "Checks and validation rules enforce standing guidance once the repo chooses verification over prose-only handling.",
        },
        {
            "rank": 5,
            "source": "repo_doctrine",
            "authority": "standing-doctrine",
            "rule": "Broad doctrine guides normal work unless a higher-precedence surface narrows or replaces it.",
        },
        {
            "rank": 6,
            "source": "durable_understanding",
            "authority": "interpretive-understanding",
            "rule": "Memory and similar durable understanding inform interpretation but should not override clearer policy or doctrine.",
        },
        {
            "rank": 7,
            "source": "superseded_residue",
            "authority": "historical-only",
            "rule": "Older superseded residue may remain as explanation or archive context but should not govern current work.",
        },
    ]


def _standing_intent_supersession_rules() -> list[dict[str, Any]]:
    return [
        {
            "rule": "newer_same_owner_replaces_older",
            "summary": (
                "When two standing instructions live in the same owner surface for the same concern, "
                "the newer or more specific checked-in instruction replaces the older one."
            ),
        },
        {
            "rule": "stronger_home_replaces_weaker_for_same_concern",
            "summary": (
                "When the same concern moves from doctrine or understanding into config or enforceable "
                "workflow, the stronger home becomes authoritative and the older prose becomes "
                "explanatory or should shrink."
            ),
        },
        {
            "rule": "active_lane_direction_is_slice_scoped",
            "summary": (
                "Active directional intent may narrow broader doctrine for the current slice, but it "
                "should not silently rewrite repo-wide policy beyond that slice."
            ),
        },
        {
            "rule": "superseded_residue_should_stop_governing",
            "summary": (
                "Archived or explicitly superseded residue may remain for history, but reporting should "
                "treat it as non-authoritative once a clearer current owner exists."
            ),
        },
    ]


def _standing_intent_stronger_home_model(*, target_root: Path, config_policy: dict[str, Any]) -> dict[str, Any]:
    examples: list[dict[str, Any]] = []
    if str(config_policy.get("improvement_latitude_source")) == "repo-config":
        examples.append(
            {
                "concern": "repo-friction improvement posture",
                "from_class": "repo_doctrine",
                "to_class": "config_policy",
                "current_owner": "agentic-workspace.toml",
                "status": "already-promoted",
                "why": "The repo's standing cleanup posture is now machine-readable policy instead of prose-only preference.",
                "refs": ["agentic-workspace.toml", "docs/standing-intent-contract.md"],
            }
        )
    if str(config_policy.get("optimization_bias_source")) == "repo-config":
        examples.append(
            {
                "concern": "output and residue preference",
                "from_class": "repo_doctrine",
                "to_class": "config_policy",
                "current_owner": "agentic-workspace.toml",
                "status": "already-promoted",
                "why": (
                    "The repo's reporting and residue preference is enforced through config-backed "
                    "defaults rather than reminder text alone."
                ),
                "refs": ["agentic-workspace.toml", "docs/reporting-contract.md"],
            }
        )
    for concern, path, refs in (
        (
            "planning surface integrity",
            "scripts/check/check_planning_surfaces.py",
            ["scripts/check/check_planning_surfaces.py", "docs/standing-intent-contract.md"],
        ),
        (
            "source/payload/root-install boundary drift",
            "scripts/check/check_source_payload_operational_install.py",
            ["scripts/check/check_source_payload_operational_install.py", "docs/source-payload-operational-install.md"],
        ),
    ):
        if (target_root / path).exists():
            examples.append(
                {
                    "concern": concern,
                    "from_class": "repo_doctrine",
                    "to_class": "enforceable_workflow",
                    "current_owner": path,
                    "status": "already-promoted",
                    "why": "This standing guidance is now detectable through a check instead of relying on prose alone.",
                    "refs": refs,
                }
            )

    return {
        "decision_test": {
            "promote_to_config_when": [
                "the standing guidance should be machine-readable and survive startup without rereading prose",
                "the repo needs a stable selectable default or policy mode rather than free-form explanation",
                "the concern changes repo-wide defaults more than it changes one local workflow",
            ],
            "promote_to_enforceable_workflow_when": [
                "drift should be detectable rather than merely remembered",
                "the repo needs repeatable validation or a failing/warning check for the concern",
                "a check, validation command, or workflow can verify the rule without building a generic automation system",
            ],
            "keep_as_doctrine_when": [
                "the guidance is still broad philosophy or boundary explanation rather than a stable toggle",
                "the stronger home would overfit or overspecify the current doctrine",
                "human legibility still matters more than machine-readable enforcement for the concern",
            ],
        },
        "candidate_classes": [
            {
                "class": "repo_doctrine",
                "preferred_stronger_homes": ["config_policy", "enforceable_workflow"],
                "rule": "Promote doctrine when the concern becomes a stable repo-wide default or a rule that should be verified.",
            },
            {
                "class": "active_directional_intent",
                "preferred_stronger_homes": ["repo_doctrine", "config_policy", "enforceable_workflow"],
                "rule": "Promote only after the direction stops being lane-local and survives beyond the current slice.",
            },
            {
                "class": "durable_understanding",
                "preferred_stronger_homes": ["repo_doctrine", "config_policy", "enforceable_workflow"],
                "rule": "Promote when the understanding has become shared rule or verifiable behavior rather than interpretive context.",
            },
        ],
        "examples": examples,
    }


def _config_policy_effective_item(*, config_policy: dict[str, Any]) -> dict[str, Any]:
    policy_items = [
        {
            "key": key,
            "value": value,
            "source": source,
        }
        for key, value, source in (
            (
                "improvement_latitude",
                str(config_policy["improvement_latitude"]),
                str(config_policy["improvement_latitude_source"]),
            ),
            (
                "optimization_bias",
                str(config_policy["optimization_bias"]),
                str(config_policy["optimization_bias_source"]),
            ),
            (
                "workflow_artifact_profile",
                str(config_policy["workflow_artifact_profile"]),
                str(config_policy["workflow_artifact_profile_source"]),
            ),
        )
    ]
    repo_owned_items = [item for item in policy_items if item["source"] == "repo-config"]
    status = "present" if repo_owned_items else "default-only"
    summary = "Workspace config carries stable repo policy currently in force."
    if status == "default-only":
        summary = "No repo-owned standing config policy is set yet; only product defaults are in force."
    return {
        "class": "config_policy",
        "status": status,
        "authority": "authoritative-policy",
        "owner_surface": "agentic-workspace.toml",
        "summary": summary,
        "items": policy_items,
    }


def _repo_doctrine_effective_item(*, target_root: Path) -> dict[str, Any]:
    refs = [path for path in ("AGENTS.md", "docs/design-principles.md") if (target_root / path).exists()]
    status = "present" if refs else "absent"
    summary = "Repo-owned startup guidance and design doctrine carry standing explanatory intent."
    if status == "absent":
        summary = "No canonical repo-doctrine surface was found."
    return {
        "class": "repo_doctrine",
        "status": status,
        "authority": "authoritative-doctrine",
        "owner_surface": refs[0] if refs else "docs/design-principles.md",
        "summary": summary,
        "refs": refs,
    }


def _durable_understanding_effective_item(*, memory_installed: bool) -> dict[str, Any]:
    return {
        "class": "durable_understanding",
        "status": "present" if memory_installed else "absent",
        "authority": "interpretive-understanding",
        "owner_surface": "memory/",
        "summary": (
            "Memory remains the durable-understanding home for repo-specific interpretive knowledge."
            if memory_installed
            else "Memory is not installed, so durable-understanding guidance has no dedicated owner surface yet."
        ),
        "refs": (
            [
                "memory/",
                "agentic-memory-bootstrap report --target ./repo --format json",
            ]
            if memory_installed
            else []
        ),
    }


def _active_directional_intent_effective_item(*, active_planning: dict[str, Any] | None) -> dict[str, Any]:
    if not active_planning:
        return {
            "class": "active_directional_intent",
            "status": "absent",
            "authority": "active-direction",
            "owner_surface": "TODO.md",
            "summary": "No active planning slice is in force right now.",
            "refs": ["TODO.md", "docs/execplans/"],
        }
    refs = [ref for ref in active_planning.get("refs", []) if isinstance(ref, str) and ref]
    return {
        "class": "active_directional_intent",
        "status": "present",
        "authority": "active-direction",
        "owner_surface": str(active_planning.get("owner_surface") or "TODO.md"),
        "summary": str(active_planning.get("summary") or "Active planning carries the current bounded direction."),
        "requested_outcome": str(active_planning.get("requested_outcome") or ""),
        "refs": refs,
    }


def _enforceable_workflow_effective_item(*, target_root: Path) -> dict[str, Any]:
    refs = [
        path
        for path in (
            "scripts/check/check_planning_surfaces.py",
            "scripts/check/check_source_payload_operational_install.py",
        )
        if (target_root / path).exists()
    ]
    status = "present" if refs else "absent"
    summary = "Checks and validation scripts provide enforceable workflow homes for standing guidance."
    if status == "absent":
        summary = "No enforceable workflow surface was found."
    return {
        "class": "enforceable_workflow",
        "status": status,
        "authority": "enforceable",
        "owner_surface": refs[0] if refs else "scripts/check/",
        "summary": summary,
        "refs": refs,
    }


def repo_friction_payload(
    *,
    target_root: Path,
    improvement_latitude: str,
    improvement_latitude_source: str,
    policy_payload: dict[str, Any],
    boundary_test_payload: dict[str, Any],
    external_setup_findings_payload: dict[str, Any] | None,
) -> dict[str, Any]:
    hotspots = _repo_friction_hotspots(target_root=target_root)
    large_file_hotspots = [item.copy() for item in hotspots if int(item["line_count"]) >= REPO_FRICTION_LARGE_FILE_THRESHOLD][
        :REPO_FRICTION_MAX_HOTSPOTS
    ]
    concept_hotspots = [item.copy() for item in hotspots if item["kind"] in {"docs", "config"}][:REPO_FRICTION_MAX_HOTSPOTS]
    external_evidence: list[dict[str, Any]] = []
    external_codebase_map = _repo_friction_external_codebase_map_payload(target_root=target_root)
    if external_codebase_map is not None:
        external_evidence.append(external_codebase_map)
    if external_setup_findings_payload is not None:
        external_evidence.append(external_setup_findings_payload)
    evidence_classes = ["large_file_hotspots", "concept_surface_hotspots"]
    if external_evidence:
        evidence_classes.append("external_evidence")
    return {
        "owner_surface": "workspace",
        "owner_rule": (
            "Repo-friction policy and evidence stay workspace-level shared surfaces unless a future "
            "independent lifecycle justifies a new module."
        ),
        "policy_mode": improvement_latitude,
        "policy_source": improvement_latitude_source,
        "initiative_posture": policy_payload["initiative_posture"],
        "rule": policy_payload["reporting_rule"],
        "reporting_destinations": policy_payload["reporting_destinations"],
        "decision_test": boundary_test_payload,
        "evidence_classes": evidence_classes,
        "large_file_hotspots": {
            "threshold_lines": REPO_FRICTION_LARGE_FILE_THRESHOLD,
            "count": len(large_file_hotspots),
            "items": large_file_hotspots,
        },
        "concept_surface_hotspots": {
            "threshold_lines": REPO_FRICTION_CONCEPT_SURFACE_THRESHOLD,
            "count": len(concept_hotspots),
            "items": concept_hotspots,
        },
        "external_evidence": external_evidence,
    }


def _repo_friction_kind_for_path(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix in {".md", ".txt", ".text"}:
        return "docs"
    if suffix in {".toml", ".json", ".yaml", ".yml", ".ini", ".cfg"}:
        return "config"
    return "code"


def _repo_friction_surface_role(relative_path: str) -> str:
    if relative_path in {
        "AGENTS.md",
        "TODO.md",
        "ROADMAP.md",
        "llms.txt",
        "agentic-workspace.toml",
    }:
        return "front-door"
    if relative_path.startswith("docs/execplans/"):
        return "planning-state"
    if relative_path.startswith("docs/"):
        return "canonical-doc"
    if relative_path.startswith("tools/"):
        return "generated-maintainer-surface"
    if relative_path.startswith(".agentic-workspace/"):
        return "managed-surface"
    return "repo-surface"


def _repo_friction_hotspots(*, target_root: Path) -> list[dict[str, Any]]:
    hotspots: list[dict[str, Any]] = []
    for path in sorted(target_root.rglob("*")):
        if not path.is_file():
            continue
        if any(part in REPO_FRICTION_SKIP_DIRS or part.startswith(".uv-cache") for part in path.parts):
            continue
        if path.suffix.lower() not in REPO_FRICTION_SCAN_SUFFIXES:
            continue
        try:
            line_count = sum(1 for _ in path.open("r", encoding="utf-8"))
        except (UnicodeDecodeError, OSError):
            continue
        if line_count < REPO_FRICTION_CONCEPT_SURFACE_THRESHOLD:
            continue
        relative = path.relative_to(target_root).as_posix()
        hotspots.append(
            {
                "path": relative,
                "line_count": line_count,
                "kind": _repo_friction_kind_for_path(path),
                "surface_role": _repo_friction_surface_role(relative),
            }
        )
    hotspots.sort(key=lambda item: (-int(item["line_count"]), str(item["path"])))
    return hotspots


def _int_or_none(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str) and value.strip().isdigit():
        return int(value.strip())
    return None


def _repo_friction_external_codebase_map_payload(*, target_root: Path) -> dict[str, Any] | None:
    path = target_root / "tools" / "codebase-map.json"
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return {
            "kind": "codebase-map",
            "path": "tools/codebase-map.json",
            "status": "unreadable",
            "items": [],
        }
    if not isinstance(payload, dict):
        return {
            "kind": "codebase-map",
            "path": "tools/codebase-map.json",
            "status": "unsupported-shape",
            "items": [],
        }

    candidate_lists: list[Any] = []
    for key in ("large_modules", "hotspots", "modules"):
        value = payload.get(key)
        if isinstance(value, list):
            candidate_lists.append(value)

    items: list[dict[str, Any]] = []
    for candidate_list in candidate_lists:
        for entry in candidate_list:
            if not isinstance(entry, dict):
                continue
            path_value = entry.get("path") or entry.get("module") or entry.get("name")
            if not isinstance(path_value, str) or not path_value.strip():
                continue
            line_count = _int_or_none(entry.get("line_count"))
            if line_count is None:
                line_count = _int_or_none(entry.get("lines"))
            normalized: dict[str, Any] = {
                "path": path_value.strip().replace("\\", "/"),
                "line_count": line_count,
            }
            function_count = _int_or_none(entry.get("function_count"))
            if function_count is None:
                function_count = _int_or_none(entry.get("functions"))
            if function_count is not None:
                normalized["function_count"] = function_count
            class_count = _int_or_none(entry.get("class_count"))
            if class_count is None:
                class_count = _int_or_none(entry.get("classes"))
            if class_count is not None:
                normalized["class_count"] = class_count
            items.append(normalized)

    items.sort(
        key=lambda item: (
            -(item["line_count"] if isinstance(item.get("line_count"), int) else -1),
            str(item["path"]),
        )
    )
    return {
        "kind": "codebase-map",
        "path": "tools/codebase-map.json",
        "status": "loaded",
        "items": items[:REPO_FRICTION_MAX_HOTSPOTS],
    }
