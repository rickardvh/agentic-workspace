# Maintainer session logging

Session logging is available as explicitly enabled, local maintainer
instrumentation. It is disabled by default and does not create Workspace state
during ordinary `start` or `invoke` calls.

Set `AW_SESSION_LOG` to a stable session identifier before running the CLI:

```console
AW_SESSION_LOG=release-check agentic-workspace start --target . --task "check the release"
```

PowerShell:

```powershell
$env:AW_SESSION_LOG = "release-check"
agentic-workspace start --target . --task "check the release"
```

Each CLI result is appended as JSON Lines to
`.agentic-workspace/local/logs/aw-session-<id>.jsonl` under the target. The
directory remains ignored by Git. Reuse the same identifier across `start` and
`invoke` calls to keep one chronological session log. Optional
`AW_SESSION_LOG_PARENT_EVENT` and `AW_SESSION_LOG_CORRELATION` values associate
host-managed parent/child work without teaching AW provider identity.

The raw log contains CLI arguments and bounded result payloads. Larger results
retain only size, digest, kind, and status. Treat raw logs as private local
diagnostic evidence.

Analyze or create a normalized share-safe export through the maintainer module,
which is deliberately separate from the two-command public CLI:

```console
python -m agentic_workspace.session_logging analyze --target . --session release-check
python -m agentic_workspace.session_logging export --target . --session release-check
```

Analysis reports failures, repeated invocations/results, slow commands, large
outputs, and explicit capture gaps. Record a known gap with `gap --reason ...`
or `AW_SESSION_LOG_GAP`; no missing chronology is fabricated. Share-safe exports
omit raw arguments and payloads, normalize target/home paths, and state their
coverage and omissions.

Logging is best effort and never supplies Planning, Memory, Verification,
operation, claim, or decision authority. A logging error is written to stderr
but cannot change an otherwise valid command result. Unset `AW_SESSION_LOG` to
disable capture.
