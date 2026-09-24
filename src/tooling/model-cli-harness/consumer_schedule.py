"""Finite selection and reporting around the existing consumer runner; no publisher."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import platform
import signal
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "release"))
import platform_release  # noqa: E402
from consumer_environment import Subject, cleanup_remaining  # noqa: E402
from current_install import REPOSITORY, fetch  # noqa: E402
from run_model_cli_harness import run_case  # noqa: E402

ROOT = Path(__file__).resolve().parents[3]


def harness_identity():
    paths = [
        Path(__file__),
        Path(__file__).with_name("consumer_agent.py"),
        Path(__file__).with_name("consumer_outcomes.py"),
        Path(__file__).with_name("run_model_cli_harness.py"),
        Path(__file__).with_name("run_sbx_codex_adapter.py"),
        ROOT / "src/tooling/release/consumer_environment.py",
        ROOT / "src/tooling/release/consumer_journeys.py",
    ]
    # Git may check the same trusted text out with CRLF on a native Windows job.
    return {
        str(path.relative_to(ROOT)).replace("\\", "/"): hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()
        for path in paths
    }


PROFILES = ("standalone", "node", "python", "cargo")
# (platform-index, profile, scenario, reserved sessions). All target identities
# come from the release owner. Reservations count fresh continuation phases too.
ROTATION = (
    ((0, "standalone", "first-contact", 1), (0, "python", "maintenance", 2)),
    ((0, "node", "continuation", 2), (0, "cargo", "upgrade", 1)),
    ((0, "python", "readoption", 3),),
    ((0, "standalone", "interruption", 2), (0, "node", "local-independence", 1)),
    ((1, "standalone", "first-contact", 1), (2, "node", "first-contact", 1), (3, "python", "first-contact", 1)),
    ((4, "standalone", "first-contact", 1), (5, "python", "first-contact", 1), (0, "cargo", "first-contact", 1)),
    ((0, "node", "first-contact", 1), (0, "python", "first-contact", 1), (0, "standalone", "first-contact", 1)),
)


def selection(day, *, skip_macos=True, deterministic_only=False):
    rows = platform_release.platforms()
    live = []
    for index, (target, profile, family, sessions) in enumerate(ROTATION[day % 7]):
        row = rows[target]
        live.append(
            {
                **row,
                "id": f"live-{index}",
                "profile": profile,
                "family": family,
                "sessions": sessions,
                "backend": "sandbox" if row["node_platform"] == "linux" else "native",
                "disposition": "skipped-by-user" if skip_macos and row["node_platform"] == "darwin" else "assigned",
            }
        )
    native = rows[day % len(rows)]
    deterministic = [{**rows[0], "id": "docker", "backend": "docker", "profile": PROFILES[day % 4], "family": "first-contact"}]
    if not (skip_macos and native["node_platform"] == "darwin"):
        deterministic.append({**native, "id": "native", "backend": "native", "profile": "standalone", "family": "first-contact"})
    return {
        "day": day % 7,
        "live": [] if deterministic_only else live,
        "deterministic": deterministic,
        "session_limit": 3,
        "seconds_per_session": 900,
        "macos": "skipped-by-user" if skip_macos else "assigned",
    }


def freeze(destination, *, version=None, previous=None, day=None, skip_macos=True, deterministic_only=False):
    destination.mkdir(parents=True, exist_ok=False)
    if version is None:
        version = json.loads(fetch(f"https://api.github.com/repos/{REPOSITORY}/releases/latest"))["tag_name"].removeprefix("v")
    if previous is None:
        releases = json.loads(fetch(f"https://api.github.com/repos/{REPOSITORY}/releases?per_page=100"))
        candidates = [r["tag_name"].removeprefix("v") for r in releases if not r["draft"] and not r["prerelease"]]
        candidates = [
            v
            for v in candidates
            if len(v.split(".")) == 3
            and all(p.isdigit() for p in v.split("."))
            and tuple(map(int, v.split("."))) < tuple(map(int, version.split(".")))
        ]
        if not candidates:
            raise ValueError("No previously published stable available; no synthetic upgrade pin")
        previous = max(candidates, key=lambda v: tuple(map(int, v.split("."))))
    current = Subject.public(version, destination / "current")
    prior = Subject.public(previous, destination / "previous")
    plan = selection(
        dt.datetime.now(dt.timezone.utc).weekday() if day is None else day,
        skip_macos=skip_macos,
        deterministic_only=deterministic_only,
    )
    plan.update(
        kind="agentic-workspace/consumer-plan/v1",
        current=current.identity(),
        previous=prior.identity(),
        created_at=dt.datetime.now(dt.timezone.utc).isoformat(),
        harness_commit=subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        harness_sources=harness_identity(),
        attempt="initial",
        model="gpt-5.6-luna",
        reasoning="medium",
        billing="subscription",
        template=os.environ.get("CONSUMER_TEMPLATE")
        or "docker.io/docker/sandbox-templates:codex@sha256:a68b972a59148c6359ade441387159033f6d196d48aef9dda06d2d4bb26eb41e",
    )
    (destination / "plan.json").write_text(json.dumps(plan, indent=2) + "\n", encoding="utf-8")
    return plan


def frozen_subject(directory, plan, key):
    subject = Subject("public", directory / key, platform_release.load(directory / key))
    if subject.identity() != plan[key]:
        raise ValueError("Frozen subject changed; no fallback")
    return subject


def unavailable(case, reason, *, status="unavailable"):
    return {
        "kind": "agentic-workspace/consumer-run/v1",
        "case_id": case["id"],
        "family": case["family"],
        "target": case["target"],
        "profile": case["profile"],
        "status": status,
        "executed": False,
        "failure_class": reason,
        "sessions_started": 0,
        "tokens": None,
        "cost": None,
        "cleanup": "not-started",
    }


def execute_plan(directory, output, scratch, *, kind, case_id=None, template=None, live_ready=False, sbx="sbx"):
    plan = json.loads((directory / "plan.json").read_text())
    if plan.get("harness_sources") != harness_identity():
        raise ValueError("Harness differs from the frozen plan")
    if plan["session_limit"] != 3 or not 1 <= plan["seconds_per_session"] <= 900 or sum(c["sessions"] for c in plan["live"]) > 3:
        raise ValueError("Invalid daily session budget")
    if template and template != plan["template"]:
        raise ValueError("Template differs from the frozen plan")
    template = plan["template"]
    output.mkdir(parents=True, exist_ok=True)
    scratch.mkdir(parents=True, exist_ok=True)
    current, previous = (frozen_subject(directory, plan, key) for key in ("current", "previous"))
    cases = plan[kind]
    if case_id is not None:
        cases = [case for case in cases if case["id"] == case_id]
        if not cases:
            raise ValueError("Assigned case not found")
    used = 0
    for case in cases:
        path = output / (case["id"] + ".json")
        if path.exists():
            raise ValueError("Preserve first failure: result already exists")
        reason = None
        if case.get("disposition") == "skipped-by-user":
            reason = "user-skipped-macos"
        elif kind == "live" and not live_ready:
            reason = "provider-runner-unavailable"
        elif kind == "live" and case["backend"] != "sandbox":
            reason = "native-actor-containment-unavailable"
        elif kind == "live" and used + case["sessions"] > plan["session_limit"]:
            reason = "session-budget-exhausted"
        elif kind == "live" and ((platform.machine().lower() in {"arm64", "aarch64"}) != (case["node_arch"] == "arm64")):
            reason = "native-architecture-unavailable"
        if reason:
            result = unavailable(case, reason)
            path.write_text(json.dumps(result, indent=2), encoding="utf-8")
            continue
        args = SimpleNamespace(
            family=case["family"],
            driver="agent" if kind == "live" else "deterministic",
            backend=case["backend"],
            profile=case["profile"],
            target=case["target"],
            model=plan["model"],
            reasoning=plan["reasoning"],
            billing=plan["billing"],
            seconds=plan["seconds_per_session"],
            token_ceiling=None,
            sbx=sbx,
            template=template,
            candidate=None,
            public_version=plan["current"]["version"],
            previous_public_version=plan["previous"]["version"],
            image=None,
            scratch=scratch,
            result=path,
        )
        run_case(args, frozen_subject=current, frozen_previous=previous)
        result = json.loads(path.read_text())
        used += result.get("sessions_started", 0)
    return used


def summary(plan, paths):
    observed = {}
    for path in paths:
        if path.stat().st_size > 1024 * 1024:
            raise ValueError("Oversized result")
        row = json.loads(path.read_text())
        if path.stem in observed:
            raise ValueError("Duplicate initial result")
        observed[path.stem] = row
    rows = []
    for kind in ("deterministic", "live"):
        for case in plan[kind]:
            row = observed.get(case["id"], unavailable(case, "missing-execution-result"))
            if row.get("status") == "passed" and (not row.get("executed") or row.get("requested") != plan["current"]):
                row = unavailable(case, "missing-or-mismatched-subject-witness")
            rows.append(
                {
                    "id": case["id"],
                    "driver": kind,
                    "target": case["target"],
                    "profile": case["profile"],
                    "family": case["family"],
                    "status": row.get("status", "unavailable"),
                    "executed": row.get("executed", False),
                    "failure_class": row.get("failure_class"),
                    "cleanup": row.get("cleanup"),
                    "tokens": row.get("tokens"),
                    "cost": row.get("cost"),
                }
            )
    age = (dt.datetime.now(dt.timezone.utc) - dt.datetime.fromisoformat(plan["created_at"])).total_seconds()
    return {
        "kind": "agentic-workspace/consumer-summary/v1",
        "subject": plan["current"],
        "scope": "deterministic-and-live" if plan["live"] else "deterministic-only",
        "harness_commit": plan["harness_commit"],
        "evidence_age_seconds": max(0, age),
        "stale": age > 48 * 3600,
        "attempt": plan["attempt"],
        "macos": plan["macos"],
        "assigned": len(rows),
        "executed": sum(bool(r["executed"]) for r in rows),
        "passed": sum(r["status"] == "passed" for r in rows),
        "cases": rows,
        "status": "passed" if rows and all(r["status"] == "passed" for r in rows) else "incomplete-or-failed",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("operation", choices=["freeze", "run", "summary", "cleanup"])
    parser.add_argument("--directory", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--scratch", type=Path)
    parser.add_argument("--version")
    parser.add_argument("--previous")
    parser.add_argument("--day", type=int, choices=range(7))
    parser.add_argument("--include-macos", action="store_true")
    parser.add_argument("--deterministic-only", action="store_true", help="Freeze only deterministic assignments for hosted execution")
    parser.add_argument("--kind", choices=["deterministic", "live"])
    parser.add_argument("--case-id")
    parser.add_argument("--template")
    parser.add_argument("--live-ready", action="store_true")
    args = parser.parse_args()

    def cancelled(*_):
        raise KeyboardInterrupt("Consumer workflow cancelled")

    signal.signal(signal.SIGTERM, cancelled)
    if args.operation == "cleanup":
        cleanup_remaining(args.scratch)
        return 0
    if args.operation == "freeze":
        try:
            plan = freeze(
                args.directory,
                version=args.version,
                previous=args.previous,
                day=args.day,
                skip_macos=not args.include_macos,
                deterministic_only=args.deterministic_only,
            )
        except Exception as error:
            args.directory.mkdir(parents=True, exist_ok=True)
            failure = {
                "status": "unavailable",
                "failure_class": "public-subject-unavailable",
                "executed": False,
                "error": str(error)[:1000],
            }
            (args.directory / "failure.json").write_text(json.dumps(failure), encoding="utf-8")
            if os.environ.get("GITHUB_STEP_SUMMARY"):
                with open(os.environ["GITHUB_STEP_SUMMARY"], "a", encoding="utf-8") as out:
                    out.write("Public consumer subject unavailable before execution. No older release was substituted; see failure.json.\n")
            return 1
        if os.environ.get("GITHUB_OUTPUT"):
            with open(os.environ["GITHUB_OUTPUT"], "a", encoding="utf-8") as out:
                out.write("matrix=" + json.dumps({"include": plan["deterministic"]}) + "\n")
        print(json.dumps(plan))
    elif args.operation == "run":
        execute_plan(
            args.directory,
            args.output,
            args.scratch,
            kind=args.kind,
            case_id=args.case_id,
            template=args.template,
            live_ready=args.live_ready,
        )
        return 0 if all(json.loads(path.read_text()).get("status") == "passed" for path in args.output.glob("*.json")) else 1
    else:
        plan = json.loads((args.directory / "plan.json").read_text())
        if (args.output / "summary.json").exists():
            raise ValueError("Preserve initial summary; use a separate diagnostic directory")
        args.output.mkdir(parents=True, exist_ok=True)
        result = summary(plan, list(args.output.rglob("*.json")))
        (args.output / "summary.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
        if os.environ.get("GITHUB_STEP_SUMMARY"):
            with open(os.environ["GITHUB_STEP_SUMMARY"], "a", encoding="utf-8") as out:
                out.write(
                    f"Consumer evidence: {result['status']}; {result['executed']}/{result['assigned']} executed, {result['passed']} passed.\n\n"
                )
                out.write(
                    f"Exact public subject: {plan['current']['version']}; harness `{plan['harness_commit']}`; macOS: {plan['macos']}.\n\n"
                )
                for case in result["cases"]:
                    out.write(
                        f"- {case['id']}: {case['target']} / {case['profile']} / {case['family']}: **{case['status']}** ({case['failure_class'] or 'checked outcomes'}).\n"
                    )
        print(json.dumps(result))
        return 0 if result["status"] == "passed" else 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
