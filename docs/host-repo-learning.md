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
- Host config and proof profiles can require, add, or disallow routes.
- Live target capabilities can select commands when the repo currently exposes them.
- Language/project markers alone remain discovery candidates.

For Python repos, `pyproject.toml` and `tests/` are not enough to require `uv run pytest`. Pytest proof requires confirmed repo evidence such as pytest configuration or a declared pytest dependency. If no executable route is confirmed, proof selection must ask for manual verification and expose any absent command as negative evidence to route into Memory, config, docs/checks, Planning, or an issue.
