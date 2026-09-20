# Standard skill exposure evidence (#3325)

## Boundary and implementation

Configuration exposes six current main/specialized product bundles selected from
its canonical registry. It offers exact read, proposal, authorisation, effect and
recovery requests through the existing `start`/`invoke` boundary and
`configuration-source` restriction scope. The same attempt store authenticates
link ownership. There is no new registry, CLI family, runtime detector or
activation grant. Bodies and resources stay canonical. All link destinations
are fixed by the native owner, never supplied by the caller.

Unix uses relative symlinks. On the development Windows NTFS host, symlink
creation failed with OS error 1314; junctions passed the lifecycle and genuine
host discovery tests. The Windows-only `junction` dependency provides the OS
operation; no shell interpolation or administrative privilege is required.
Parents containing links/reparse points are refused. Absolute Windows junctions
are intentionally not silently rebound when a repository moves.

Owned exposure is separately authenticated from its current content. Unknown
files, directories and links are preserved, including a link that happens to
point at the same source without custody. Canonical user edits are immediately
visible and survive removal. A fresh owner observation detects stale proposals.
Prepared/published interruption tests demonstrate re-entry versus committed
result recovery without replaying a published link operation. Repeated
expose/remove/expose in the same task acquires a distinct current lifetime.

## Current-host experiment, 2026-09-16

Host: Codex CLI/app-server **0.154.0**, Windows x64, NTFS, configured account/model
and tools. Two disposable nested Git repositories staged the canonical skill
payload; all six exposures were then created through native Configuration
requests/actions in fresh subprocesses. This is an adoption fixture, not evidence
for an unavailable whole-target bootstrap command.

Discovery used the host's actual JSON-RPC `skills/list`, with the fixture CWD and
`forceReload: true`, after `initialize`/`initialized`. Both arms discovered:

- workspace-startup
- workspace-intent-discovery
- workspace-proof-selection
- workspace-setup-jumpstart
- workspace-resources
- workspace-instruction-correction

Reference-only and repository maintainer skills were absent from the product
catalogue. One unrelated pre-existing user skill had invalid frontmatter; the
host reported its error independently and still discovered all six AW skills.
Discovery did not run a preparation script or native owner operation.

Each arm then ran the configured Codex CLI with `exec --ephemeral --sandbox
read-only --json`, the fixture CWD, and this ordinary prompt (no AW wording):

> Find where temporary analysis files should go in this repository and explain
> the safe cleanup procedure. Read only what you need; do not create or remove
> anything.

| Observation | No pointer | Minimal pointer |
| --- | --- | --- |
| Product skills discovered | 6 | 6 |
| Names + descriptions, characters | 1,177 | 1,177 |
| Serialised product metadata, UTF-8 bytes including fixture paths | 3,133 | 3,163 |
| Completed host tool calls | 4 | 3 |
| Actual selected reads | startup + resources through `.agents/skills` | canonical startup + resources |
| Total reported input tokens across the turn | 188,929 | 154,992 |
| Cached input tokens | 138,496 | 122,496 |
| Output tokens | 766 | 792 |
| Reasoning output tokens | 10 | 16 |

Both answers used the resource procedure to identify the task scratch container,
exact-path cleanup, blockers and no-runtime preservation fallback. Neither
mutated the fixture. The fixture deliberately lacked runtime configuration and
fallback owner files; their absence remained unknown/unverified, not fabricated
current owner facts. The host used its available programmatic filesystem tool
for reads. No issue review or independent acceptance was requested.

The one-line pointer was: “Use
`.agentic-workspace/skills/workspace-startup/SKILL.md` for repository procedure;
if native skill discovery is unavailable, read it directly.” This is also the
new managed fence. Its first clause preserves a canonical entrypoint hint and
its second supports mixed readers. The removed sentences repeated policy/owner
separation and runtime/fallback procedure already supplied by the skill.
Independent repository instructions outside the fence were preserved.

These are one trial per arm, not a causal token comparison or universal
activation guarantee. Large global host context contributes to repeated input;
metadata listing is not free and the model totals must not be attributed solely
to AW. Currency/model prices and complete infrastructure cost were not measured.
No ROI claim follows. The minimal shared fallback remains justified even though
this host selected the skills without it.

## Identity, executable resources and output

The exposed intent preparation script was actually executed with the paired
native CLI, a clear semantic judgement and the same target/task as a second call
through its canonical path. The entire JSON result and revision matched:
`prepared`, `direct`, procedure-only authority, no effects. Canonical/exposed
resource bytes and resolved directories matched. This exercises the script's
relative sibling material dependencies, not merely a `SKILL.md` existence check.
Native route identity continues to use the canonical registry/source; host
exposure does not introduce another route. Canonical body/resource changes are
visible through the same links without regeneration. Unrelated files do not
participate in a selected exposure proposal's revision.

One ordinary compact `start` on the fixture returned 2,887 UTF-8 bytes; it did not
contain the skill body or a copy of all six discovery descriptions. Full owner
detail is still explicitly available. The projection adds no catalogue/body to
ordinary startup. No helper executes during host listing.

CI exposed an old 100,000-character bound on the full diagnostic answer after
the added API schemas brought that fixture to 101,533 characters. The guard now
bounds complete schema introspection (76,000), owner state (28,000), and ordinary
compact output (6,000) separately. This permits explicit API declaration growth
and adds a direct ordinary-context guard; it does not claim that full
introspection got smaller. Former-route detail retains its own 8,000 bound.

## Validation and limits

Native tests exercise install, same-task repeated lifecycle, resources, canonical
edit preservation, stale proposals, unrelated skills, collision refusal, and
prepared/published interruption recovery. Existing Configuration effect and
instruction restrictions remain in force; link selection has no proof/claim
power. The full Rust run also exposed an older native-transport test fixture
missing the now-required command argv. That fixture was corrected against the
current schema, retaining separate missing-command and missing-parameters cases.

The native Rust suite passed 126 tests (three existing ignored tests), and the
current skills-first interface suite passed 18 tests. Source/payload boundary
checks reported no drift. An exploratory historical Python doctor/status suite
reported 23 failures and 39 passes alongside the issue-helper tests; its first
failure is the unchanged doctor validator reading the removed `optimization_bias`
schema field. Neither that validator nor its schema changed here. This legacy
lane is not claimed green; the current bootstrap/interface checks above passed.

Linux symlink code is platform-gated; local acceptance here is the Windows
junction path. CI must supply Linux compilation/execution evidence. Broader
host/platform support and richer-host execution are not inferred from this
smoke; #3267 owns the latter. This implementation is ready for independent
review, not self-approved issue completion or aggregate #3277 acceptance.

Sources: [Agent Skills format](https://agentskills.io/specification),
[Codex skill discovery](https://learn.chatgpt.com/docs/build-skills),
[junction OS helper](https://docs.rs/junction/2.0.0/junction/).
