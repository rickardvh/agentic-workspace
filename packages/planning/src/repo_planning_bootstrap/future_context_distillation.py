"""Owner-backed future-context dispositions for Planning closeout."""

from __future__ import annotations

from typing import Any

CLOSEOUT_DISTILLATION_BUCKETS = (
    "discard",
    "continuation",
    "memory",
    "config_check",
    "docs",
    "issue_follow_up",
    "stronger_owner",
    "unresolved",
)


def empty_closeout_distillation_buckets() -> dict[str, list[dict[str, str]]]:
    return {bucket: [] for bucket in CLOSEOUT_DISTILLATION_BUCKETS}


def future_context_distillation_buckets(signals: Any) -> dict[str, list[dict[str, str]]]:
    buckets = empty_closeout_distillation_buckets()
    if not isinstance(signals, list):
        return buckets
    for raw_signal in signals:
        if not isinstance(raw_signal, dict) or raw_signal.get("relevant") is False:
            continue
        disposition = raw_signal.get("disposition", {})
        disposition = disposition if isinstance(disposition, dict) else {}
        outcome = str(disposition.get("outcome", "unresolved")).strip().lower().replace("_", "-")
        owner = str(disposition.get("owner") or raw_signal.get("owner") or "").strip()
        rationale = str(disposition.get("rationale") or raw_signal.get("rationale") or "").strip()
        summary = str(raw_signal.get("summary") or raw_signal.get("signal_id") or "known future-context signal").strip()
        source = f"future_context_signals.{str(raw_signal.get('signal_id') or 'unknown')}"
        item = {"summary": summary, "owner": owner, "source": source, "rationale": rationale}
        if outcome in {"capture", "update-existing"}:
            owner_text = owner.lower()
            bucket = (
                "memory"
                if "memory" in owner_text
                else "docs"
                if "doc" in owner_text
                else "config_check"
                if any(term in owner_text for term in ("config", "check", "test", "contract", "proof", "code"))
                else "unresolved"
            )
        elif outcome in {"route-stronger", "already-absorbed"}:
            bucket = "stronger_owner" if owner and rationale else "unresolved"
        elif outcome == "dismiss":
            bucket = "discard" if rationale else "unresolved"
        else:
            bucket = "unresolved"
            item["next_action"] = str(disposition.get("next_action") or raw_signal.get("required_decision") or "").strip()
        buckets[bucket].append(item)
    return buckets
