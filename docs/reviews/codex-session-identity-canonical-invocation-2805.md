# Codex session identity canonical-invocation dogfood (#2805)

Observed at `2026-08-29T09:05:48.5498653Z`.

The canonical configured repository launcher ran `session-log status` against a fresh ignored target-local session with the real host-provided Codex identity available and no portable identity pre-seeded by the caller.

Observed result:

- status: `ready`
- logical-session resolution: `identity-registry`
- identity source inside AW: `AW_SESSION_LOGICAL_IDENTITY`
- capture posture: `ready`
- missing-identity invocation count: `0` (the ready posture omits the counter because no capture gap exists)
- raw logical-session identity stored: `false`
- first command captured: `true`

Only boolean availability and normalized AW status fields were retained here. The raw provider identity, logical identity value, physical session id, and local paths were excluded.

The existing long-lived thread target retained its truthful recovered gap and was not reset, rewritten, or backfilled. A fresh target-local session was used so first-command behavior could be observed without destroying earlier diagnostic evidence.
