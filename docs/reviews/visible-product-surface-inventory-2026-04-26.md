# Visible Product Surface Inventory - 2026-04-26

Purpose: compact inventory for #352 so the next #230 subtraction slice can choose from checked-in evidence instead of rediscovering the visible product shape. This is review evidence, not an operating contract or startup surface.

Classification vocabulary used here: core entrypoint, generated adapter, secondary/deep surface, machine contract, local-only surface, review artifact, historical/compatibility residue, and candidate for compression/removal.

## Core Entrypoints

| Surface | Classification | Owner | Authority | Discovery | Value |
| --- | --- | --- | --- | --- |
| `AGENTS.md` | core entrypoint | repo | adapter to structured workspace surfaces | first file | Thin startup router into package queries. |
| `uv run agentic-workspace start --format json` | core entrypoint | workspace package | derived startup route | `AGENTS.md`, `llms.txt` | Ordinary compact path from repo entry to current action. |
| `uv run agentic-workspace summary --format json` | core entrypoint | planning package | derived current-work state | `start`, preflight | Active planning, roadmap readiness, and closeout reconciliation. |
| `uv run agentic-workspace proof --target . --changed <paths> --format json` | core entrypoint | workspace package | derived validation selector | workflow obligations | Chooses proof lanes and surface-value review for changed paths. |
| `uv run agentic-workspace report --target . --format json` | secondary/deep surface | workspace package | compact router | `start`, AGENTS | Health, current work, warnings, section hints, and deeper selectors. |

## Secondary Surfaces

| Surface | Classification | Owner | Authority | Discovery | Value |
| --- | --- | --- | --- | --- |
| `.agentic-workspace/WORKFLOW.md` | secondary/deep surface | repo | workflow adapter | `AGENTS.md` | Shared workflow rule pointer; not a full startup handbook. |
| `.agentic-workspace/config.toml` | secondary/deep surface | repo | canonical config | `config`, preflight | Repo-owned posture and workflow obligations. |
| `.agentic-workspace/OWNERSHIP.toml` | machine contract | repo | canonical ownership | `ownership`, doctor | Boundary and authority map source. |
| `.agentic-workspace/system-intent/intent.toml` | machine contract | repo | compiled intent mirror | `system-intent`, report | Directional pressure without becoming task state. |
| `.agentic-workspace/system-intent/` | secondary/deep surface | repo | durable intent inputs | `system-intent`, report | Read only for larger-direction or design-pull questions. |
| `.agentic-workspace/docs/` | secondary/deep surface | package/repo mix | contract docs | report/summary refs | Deep references after compact queries point there. |
| `.agentic-workspace/planning/` | secondary/deep surface | planning package/repo | active planning authority | `summary`, active execplan refs | Current work and historical proof; raw reads only when pointed there. |
| `.agentic-workspace/memory/` | secondary/deep surface | memory package/repo | durable knowledge | memory routing/report | Read only by route key or compact memory signal. |
| `.agentic-workspace/local/` | local-only surface | local runtime/user | advisory only | preflight/config | Machine-local aids; ignored by git and not shared authority. |

## Generated Adapters

| Surface | Classification | Owner | Authority | Discovery | Compression note |
| --- | --- | --- | --- | --- |
| `llms.txt` | generated adapter; candidate for compression/removal | workspace renderer | generated adapter | external-agent handoff | Candidate for compression: route to `AGENTS.md`, `start`, `summary`, and `proof`; avoid handbook prose. |
| `tools/AGENT_QUICKSTART.md` | generated adapter; candidate for compression/removal | planning renderer | generated adapter | optional weak-agent helper | Candidate for compression: route to `start`/`summary` without authority and escalation tables. |
| `tools/AGENT_ROUTING.md` | generated adapter; candidate for compression/removal | planning renderer | generated adapter | optional weak-agent helper | Candidate for compression: state precedence and compact queries without mirroring a larger table. |
| `tools/agent-manifest.json` | machine contract | planning renderer | generated structured mirror | generated docs | Keep machine-readable; ordinary agents should not read it unless they need a structured mirror. |
| Root/package `AGENTS.md` files | generated adapter / adapter | repo/package | startup/boundary adapters | file-local discovery | Keep thin; package-local files are read only when editing that package. |
| Package `bootstrap/` mirrors | historical/compatibility residue | packages | packaged payload | installer/upgrade | Hidden machinery for target installs, not this repo's active workflow truth. |

## Compatibility Or History Residue

| Surface | Classification | Why not first-line |
| --- | --- | --- |
| Archived execplans | historical/compatibility residue | Useful for recovery; closeout distillation should carry reusable learning. |
| `.agentic-workspace/planning/reviews/*.review.json` | review artifact | Useful for reconciliation; not ordinary startup reading. |
| `docs/reviews/*.md` | review artifact | Evidence/history for future issue creation and slice selection; not ordinary operating input. |
| Closed issue evidence in `.agentic-workspace/planning/external-intent-evidence.json` | machine contract | Used by reconcile/summary; not manually scanned by agents. |

## Package Machinery To Keep Hidden

| Surface | Classification | Route |
| --- | --- |
| `src/agentic_workspace/contracts/` | machine contract | Runtime/check consumption first; humans inspect only by proof, defaults, report, or ownership route. |
| `packages/*/bootstrap/**` | historical/compatibility residue | Package install/upgrade payload; not root operational truth. |
| `scripts/check/**` and renderer scripts | secondary/deep surface | Invoked by proof/maintainer commands, not first-contact docs. |

## Subtraction Candidates

1. Thin `llms.txt` so it says `AGENTS.md -> agentic-workspace start -> summary/proof` and stops restating config/lifecycle doctrine.
2. Compress `tools/AGENT_QUICKSTART.md` and `tools/AGENT_ROUTING.md` behind the same compact-query path: `start` first, summary/proof/config/report only when needed.
3. Add a report-router shape guard so new sections cannot silently make default report act like the full profile.
4. Keep historical review artifacts out of startup routing; use summary/reconcile counts and review selectors instead.
5. Keep `tools/agent-manifest.json` as machine-readable generated output, but avoid pointing ordinary agents to read it unless they need a structured mirror.

## Next Slice Recommendation

Start with generated-adapter compression and compact-report guard because both reduce repeated entry/review cost without deleting compatibility surfaces.
