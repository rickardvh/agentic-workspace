# Learn how a repository works

Treat every repository as unfamiliar until its own files and successful commands
show otherwise. A filename or language marker can suggest what to inspect, but it
does not by itself establish the project's build, test, release or workflow rules.

## Classify what you learn

Use these states when recording a repository-specific lesson:

- **candidate** — a clue worth checking, such as `pyproject.toml`, `tests/` or
  `package.json`;
- **confirmed** — the repository currently declares or successfully demonstrates
  the behaviour;
- **stale** — the lesson no longer matches the repository;
- **negative** — a plausible command or assumption was checked and found not to
  apply;
- **superseded** — a newer project rule, test or document has replaced the lesson.

Do not turn a guess into project policy simply because it looks conventional for
the language or framework.

## Save the lesson where it will be used

Prefer an existing project home:

- **Memory** for useful repository facts, recurring traps and confirmed or failed
  command choices that would otherwise be rediscovered;
- **configuration** for stable AW settings;
- **project documentation** for human-facing build, test, release and workflow
  guidance;
- **tests and checks** when the lesson can be enforced automatically;
- **Planning** for unfinished follow-up work;
- **GitHub issues** for improvements that need review or prioritisation;
- **local scratch** for machine-specific probe output that should not be shared.

Do not create another AW record when the repository already has a clearer source.

## Choose checks from repository evidence

A file such as `pyproject.toml` or a `tests/` directory may suggest Python
testing, but it does not prove that `uv run pytest` is the right command.

Use a command when the repository provides evidence for it, for example:

- test configuration;
- a declared dependency;
- a package-manager script;
- a Make target;
- an AW Verification definition;
- a previously confirmed repository-specific lesson that still applies.

If no executable check is established, report that gap instead of inventing one.
Record a failed command as a reusable negative lesson only when there was a real
repository-specific reason to try it.

## Keep useful command lessons compact

Memory may keep a machine-readable line so later agents can reuse an observed
check without rereading the surrounding narrative:

```text
agentic-workspace-proof-route: {"state":"confirmed","intent_type":"behavior-test","candidate_command":"npm test","source":"memory","confidence":"high","requires_live_confirmation":false,"scope":"repo","owner":"Memory","provenance":"npm test passed during setup","learned_at":"2026-06-02"}
```

The field names above are exact data identifiers. In prose, interpret them simply:

- `candidate_command` is the command that was tried;
- `state` says whether it worked or should be avoided;
- `scope` says where the lesson applies;
- `provenance` records how it was learned;
- `learned_at` records when.

If required fields are missing, treat the record as incomplete rather than as
permission to run the command. Recheck a lesson when relevant repository files or
tooling have changed.

## Turn repeated lessons into stronger project mechanisms

When a lesson becomes stable:

- put required or forbidden checks in configuration or Verification;
- put human workflow guidance in project documentation;
- turn mechanical rules into tests or checks where that is clearer;
- remove older Memory advice once the stronger project mechanism makes it
  redundant.

The point is to reduce future rediscovery, not to accumulate more layers of advice.
