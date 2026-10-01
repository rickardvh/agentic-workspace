# Interrupted scratch removal evidence

On 2026-10-01, the current source-built native CLI exercised #3747 on Windows
through the public `resources` primitive. The fixture was a separate consumer
directory inside authenticated task scratch; it used no provider or credentials.

Resources created the consumer's exact scratch container. A descendant file was
opened with a Windows handle sharing reads and writes but denying deletion. A
fresh `scratch-remove` proposal was executed unchanged. The first effect failed
with `invalid-source-decision` and Windows `os error 32`. Read-only observation
confirmed that the container remained, its `.aw-scratch.json` marker was absent,
and an external exact removal attempt remained authenticated through Resources.
The failed result was preserved as failed; it supplied no committed outcome.

After the handle closed, a fresh CLI process proposed removal for the same task
and container. Another process executed its returned action and reported
`effect_outcome: committed`. The container was absent. The pending projection
and immutable attempt were removed; only the bounded Resources owner lock
remained under the consumer's local effects directory.

Deterministic Rust regressions inject interruption after removal custody is
retained and the in-tree marker is deleted, and after container absence but
before custody settlement. Separate child processes recover both cases. Focused
negatives preserve changed task/policy, altered projection or immutable attempt,
changed retention, replacement directories, and unowned markerless residue.
The existing Resources suite covers lifecycle, owner references, instruction
protection, currentness, links, and public action carriage.

This is a bounded local Windows observation plus owner-level regression proof,
not a hosted platform matrix or independent review. The historical markerless
container from #3744 predates external removal custody and remains preserved;
this fix does not reconstruct authority for it.
