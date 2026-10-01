# Disabled workspace consumer evidence

On 2026-10-01, a fresh Codex CLI 0.159.0 session exercised #3748 on Windows.
The configured model was `gpt-6.1-sol`; the session used the normal authenticated
Codex provider, with no copied credentials or provider fixtures.

The consumer was an isolated Git repository inside task scratch. Native
Configuration adopted the repository and installed the current startup skill.
Its returned edit actions configured the source-built native CLI invocation and
set effective local `workspace.enabled=false`. This proves installed repository
guidance with the current source-built native runtime; it is not a published
distribution acceptance claim.

The ordinary task asked only to correct `Helo world` in `greeting.txt` and verify
the resulting file. The repository entry required the installed startup skill,
one startup observation, and preservation of the greeting's newline.

The fresh agent read the startup skill and configuration, invoked `start` once,
received `status: inactive` with `configuration.enabled: false`, then corrected
and verified the bytes of `Hello world\n`. It neither retried startup nor requested
enablement or a waiver. Codex exited successfully. The host emitted unrelated
warnings about user-installed skill metadata and PowerShell snapshots; those did
not prevent the exercise.

Focused native/public tests cover inactive full/compact/carried projections,
uninterpreted malformed module sources, ordinary AW request rejection, enabled
operation, local enablement overriding shared disablement, invalid configuration,
and existing disabled setup, refresh and interrupted-publication recovery.
These observations establish opt-out behavior without claiming independent
review or waiving repository-owned requirements.
