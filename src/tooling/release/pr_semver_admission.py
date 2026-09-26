"""Repository-owned PR semver admission; Actions supplies event and run identity."""

import json
import os
import subprocess
import sys
import tomllib
from pathlib import Path

sys.path.insert(0, "src/tooling")
from release.pr_semver_integration import MAX_ARTIFACT_BYTES, admit_exact_tree_integration, make_admission
from release.release_ownership import classify_changed_paths


def admit(*, event_path, base_ref, head_ref, admission_path, run_id, attempt):
    with open(event_path, encoding="utf-8") as handle:
        event = json.load(handle)
    pr = event["pull_request"]

    def record_admission(payloads, label, mode):
        record = make_admission(
            root=Path.cwd(),
            event=event,
            payloads=payloads,
            label=label,
            mode=mode,
            run_id=run_id,
            attempt=attempt,
        )
        encoded = json.dumps(record, sort_keys=True).encode("utf-8")
        if len(encoded) > MAX_ARTIFACT_BYTES:
            raise SystemExit("Semver admission exceeds the bounded artifact size.")
        Path(admission_path).write_bytes(encoded)

    ownership = json.loads(Path(".github/release-ownership.json").read_text(encoding="utf-8"))
    semver_labels = set(ownership["semver_labels"])
    changeset_dir = ownership["changeset_dir"].rstrip("/")
    release_pr_branch = ownership["release_pr_branch"]
    semver_to_bump = {
        "semver:major": "major",
        "semver:minor": "minor",
        "semver:patch": "patch",
    }

    subprocess.run(
        ["git", "fetch", "origin", f"{base_ref}:refs/remotes/origin/{base_ref}"],
        check=True,
    )
    base = subprocess.run(
        ["git", "merge-base", pr["base"]["sha"], pr["head"]["sha"]],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    changed = subprocess.run(
        ["git", "diff", "--name-only", f"{base}...{pr['head']['sha']}"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.splitlines()
    path_classification = classify_changed_paths(changed, ownership)
    package_changed = path_classification["package_affecting"]

    if not package_changed:
        record_admission({}, None, "not-required")
        print("No package-affecting changes detected; semver label not required.")
        raise SystemExit(0)

    if head_ref == release_pr_branch:
        subprocess.run(["python", "src/tooling/release/coordinated_release.py", "verify"], check=True)
        record_admission({}, None, "release")
        print("Release PR version state accepted.")
        raise SystemExit(0)

    labels = {label["name"] for label in event["pull_request"].get("labels", [])}
    selected = sorted(labels & semver_labels)

    if len(selected) != 1:
        print(
            "Package-affecting PRs must have exactly one semver label: " + ", ".join(sorted(semver_labels)),
            file=sys.stderr,
        )
        print(f"Current semver labels: {selected or 'none'}", file=sys.stderr)
        print("Changed package paths:", file=sys.stderr)
        for path in path_classification["package_affecting_paths"]:
            print(f"  {path}", file=sys.stderr)
        raise SystemExit(1)

    changesets = [Path(path) for path in changed if path.startswith(f"{changeset_dir}/") and path.endswith(".toml")]
    if not changesets:
        print(
            f"Package-affecting PRs must add a release changeset under {changeset_dir}/.",
            file=sys.stderr,
        )
        raise SystemExit(1)

    expected_bump = semver_to_bump[selected[0]]
    payloads = {
        path.as_posix(): tomllib.loads(
            subprocess.run(
                ["git", "show", f"{pr['head']['sha']}:{path.as_posix()}"],
                check=True,
                capture_output=True,
                encoding="utf-8",
            ).stdout
        )
        for path in changesets
    }
    integration = None
    if any(payload.get("bump") != expected_bump for payload in payloads.values()):
        try:
            integration = admit_exact_tree_integration(
                root=Path.cwd(),
                event=event,
                expected_bump=expected_bump,
                changesets={path: payload.get("bump") for path, payload in payloads.items()},
            )
        except (ValueError, subprocess.CalledProcessError, subprocess.TimeoutExpired) as error:
            print(f"Exact-tree integration not admitted: {error}", file=sys.stderr)
            raise SystemExit(1)
    for changeset in changesets:
        payload = payloads[changeset.as_posix()]
        if payload.get("schema_version") != "agentic-workspace/release-change/v1":
            print(f"{changeset} has an invalid release changeset schema.", file=sys.stderr)
            raise SystemExit(1)
        if payload.get("bump") != expected_bump and integration is None:
            print(
                f"{changeset} declares bump={payload.get('bump')!r}, but the PR label requires bump={expected_bump!r}.",
                file=sys.stderr,
            )
            raise SystemExit(1)
        if not str(payload.get("summary", "")).strip():
            print(f"{changeset} must include a non-empty summary.", file=sys.stderr)
            raise SystemExit(1)

    if integration is not None:
        print("Exact-tree integration admitted: " + json.dumps(integration, sort_keys=True))
    record_admission(payloads, selected[0], "integration" if integration is not None else "ordinary")
    print(f"Semver label accepted: {selected[0]}")


def main():
    admit(
        event_path=os.environ["EVENT_PATH"],
        base_ref=os.environ["BASE_REF"],
        head_ref=os.environ["HEAD_REF"],
        admission_path=os.environ["SEMVER_ADMISSION_PATH"],
        run_id=int(os.environ["GITHUB_RUN_ID"]),
        attempt=int(os.environ["GITHUB_RUN_ATTEMPT"]),
    )


if __name__ == "__main__":
    main()
