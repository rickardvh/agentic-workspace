# Decisions

Use this folder for historical architectural or operational context that is still worth keeping but is not part of live operational memory.

Good candidates:

- major trade-offs with lasting consequences
- rationale that is repeatedly revisited
- architecture background that would clutter a current operational note
- decisions that are no longer active enough for `memory/current/active-decisions.md` but are still worth keeping
- rejected-path boundaries that still matter for future choices

Do not store routine runbook steps, implementation residue, subsystem behaviour, or meeting history here unless the context still encodes a consequence-bearing boundary that future work needs to respect.
Move a decision out of `memory/current/active-decisions.md` once it no longer changes implementation choices and is only worth keeping as durable rationale.
