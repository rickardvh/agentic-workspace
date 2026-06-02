# Host-Repo Learning

Agentic Workspace must treat every host repository as unfamiliar until repo evidence proves otherwise. Filenames, language markers, and AW source-repo conventions can suggest discovery questions, but they are not authority for build, test, proof, release, ownership, or workflow decisions.

## Evidence States

- `candidate`: a hint worth inspecting, such as `pyproject.toml`, `tests/`, `package.json`, or a setup/adopt proof-route hint.
- `confirmed`: evidence the target repo declares or exposes now, such as a configured proof profile, Make target, package script, declared test dependency, or successfully live-confirmed route hint.
- `stale`: previously learned evidence that no longer matches current repo affordances.
- `negative`: a failed or absent command, missing tool, invalid route, or disproved assumption that should not be reused as confirmed proof.
- `superseded`: an older lesson replaced by a stronger owner surface.

## Owner Routing

Use the strongest existing home before inventing a new surface:

- Memory: durable repo facts, recurring traps, operator runbooks, routing hints, and confirmed or negative proof-route lessons.
- Config: stable host policy, required proof profiles, and disallowed commands.
- Canonical docs: human-facing build, validation, release, ownership, or workflow policy.
- Tests/checks/contracts: lessons that can become enforceable validation.
- Planning: active or bounded future work that needs sequencing.
- Issue follow-up: product or repo improvements needing review and prioritization.
- Local-only scratch: machine-local probe output that is not shared authority.

## Proof Selection

Proof selection is one consumer of this posture:

- Generic changed-path rules create proof intent, not command authority.
- Setup/adopt proof-route hints are advisory until live-confirmed.
- Memory proof-route lessons can become durable confirmed or negative evidence when they carry scope, provenance, owner, and learned-at metadata.
- Host config and proof profiles can require, add, or disallow routes.
- Live target capabilities can select commands when the repo currently exposes them.
- Language/project markers alone remain discovery candidates.

For Python repos, `pyproject.toml` and `tests/` are not enough to require `uv run pytest`. Pytest proof requires confirmed repo evidence such as pytest configuration or a declared pytest dependency. If no executable route is confirmed, proof selection must ask for manual verification. An absent command becomes negative evidence only when the host repo, host config, proof profile, Memory note, or confirmed route hint made that command plausible first.

## Capturing Proof Lessons

When proof selection discovers a durable repo-specific lesson, capture it in the strongest existing owner:

- Put recurring confirmed or negative proof-route lessons in Memory first.
- Promote stable required or disallowed proof policy to config proof profiles.
- Promote human workflow policy to canonical docs.
- Promote enforceable lessons to tests, checks, or contracts.
- Route active follow-up to Planning or issues.

Memory notes can carry a compact machine-readable route line so proof selection can reuse the lesson later:

```text
agentic-workspace-proof-route: {"state":"confirmed","intent_type":"behavior-test","candidate_command":"npm test","source":"memory","confidence":"high","requires_live_confirmation":false,"scope":"repo","owner":"Memory","provenance":"npm test passed during setup","learned_at":"2026-06-02"}
```

Use `state:"negative"` for failed or absent commands that should not be selected again as confirmed proof. Negative lessons suppress matching candidate commands before selection. Confirmed lessons may add a route when generic discovery cannot infer it, but they must preserve provenance and scope so later agents can promote or retire them.
