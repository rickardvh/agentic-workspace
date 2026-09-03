<!-- GENERATED FILE: edit the source contracts and rerun `make render-schema-reference`. -->
# Current CLI Catalogue

Exact current command values generated from `cli_commands.json` and `cli_option_groups.json`. The schema-shape references remain at `cli-commands.md` and `cli-option-groups.md`.

- Contract digest: `sha256:85d5ab201a3c4d9bb92ab8474c9a73e85b0a1fa21bd7e7167d3a73ab852635e6`
- Program: `agentic-workspace`
- Command/subcommand count: 130

Shared-state mutability and ignored local diagnostics are separate. A `no` below means the command contract does not mutate shared workspace state. When local session logging is enabled, any command may still write ignored machine-local diagnostics:

- Condition: .agentic-workspace/config.local.toml enables session_logging
- Possible effects: append an ignored machine-local command/session record, update ignored local diagnostic indexes or caches
- Authority: `diagnostic-only` — Possible local diagnostics do not make a shared read-only command mutating and never become proof or semantic authority by existence alone.

## Command index

| Command | Role | Audience | Shared mutation | Options | Description |
| --- | --- | --- | --- | ---: | --- |
| `agentic-workspace modules` | `module_delegation_front_door` | `advanced_host_repo` | no | 3 | Show module inventory as explicit drill-down; ordinary agents should start from start/report routing. |
| `agentic-workspace instructions` | `core_context_router` | `ordinary_host_repo` | yes | 0 | Create, validate, and explain scoped Markdown instructions through generated operations. |
| `agentic-workspace instructions list` | `core_context_router` | `ordinary_host_repo` | no | 2 | List scoped instructions without loading irrelevant bodies. |
| `agentic-workspace instructions new` | `core_context_router` | `ordinary_host_repo` | yes | 4 | Scaffold one global or path-scoped Markdown instruction. |
| `agentic-workspace instructions check` | `core_context_router` | `ordinary_host_repo` | no | 2 | Validate instruction syntax and references without executing checks. |
| `agentic-workspace instructions explain` | `core_context_router` | `ordinary_host_repo` | no | 5 | Explain task-specific applicability in repository vocabulary. |
| `agentic-workspace instructions routes` | `core_context_router` | `ordinary_host_repo` | no | 4 | Discover repo-owned semantic task routes one branch or leaf at a time. |
| `agentic-workspace instructions select-route` | `core_context_router` | `ordinary_host_repo` | yes | 7 | Select existing semantic route facts for the resolved current work. |
| `agentic-workspace instructions migrate` | `core_context_router` | `ordinary_host_repo` | no | 3 | Give non-destructive incremental migration guidance. |
| `agentic-workspace summary` | `core_context_router` | `ordinary_host_repo` | no | 6 | Show the active execution summary from the planning module. |
| `agentic-workspace planning` | `core_context_router` | `ordinary_host_repo` | no | 2 | Show planning workflow help or run Planning operations through the workspace front door. |
| `agentic-workspace planning new-plan` | `core_context_router` | `ordinary_host_repo` | yes | 12 | Create a schema-valid execplan scaffold and optionally register it. |
| `agentic-workspace planning targeted-write` | `core_context_router` | `ordinary_host_repo` | yes | 8 | Preview or apply a guarded patch to exactly one canonical execplan. |
| `agentic-workspace planning promote-to-plan` | `core_context_router` | `ordinary_host_repo` | yes | 5 | Promote a planning item into an execplan scaffold. |
| `agentic-workspace planning owner-select` | `core_context_router` | `ordinary_host_repo` | yes | 10 | Select an existing Planning owner without creating or overwriting it. |
| `agentic-workspace planning decomposition-create` | `core_context_router` | `ordinary_host_repo` | yes | 7 | Create a first-class Planning decomposition record. |
| `agentic-workspace planning lane-create` | `core_context_router` | `ordinary_host_repo` | yes | 11 | Create a first-class Planning lane record. |
| `agentic-workspace planning lane-promote` | `core_context_router` | `ordinary_host_repo` | yes | 5 | Promote a decomposition candidate lane into a first-class lane record. |
| `agentic-workspace planning lane-activate` | `core_context_router` | `ordinary_host_repo` | yes | 5 | Mark a lane record active and optionally select its current slice. |
| `agentic-workspace planning lane-close` | `core_context_router` | `ordinary_host_repo` | yes | 9 | Record lane proof aggregation, residual work, and parent contribution. |
| `agentic-workspace planning lane-archive` | `core_context_router` | `ordinary_host_repo` | yes | 4 | Archive a closed lane record and remove its live state projection. |
| `agentic-workspace planning intake-artifact` | `core_context_router` | `ordinary_host_repo` | yes | 11 | Route a freehand planning artifact into a canonical Planning surface. |
| `agentic-workspace planning archive-plan` | `core_context_router` | `ordinary_host_repo` | yes | 19 | Close a completed execplan or parent lane after distillation. |
| `agentic-workspace planning closeout` | `core_context_router` | `ordinary_host_repo` | yes | 15 | Close out a completed execplan through one command-owned writer. |
| `agentic-workspace planning close-item` | `core_context_router` | `ordinary_host_repo` | yes | 6 | Close completed planning residue by id without hand-editing checked-in state. |
| `agentic-workspace planning create-review` | `core_context_router` | `ordinary_host_repo` | yes | 8 | Create a schema-valid planning review record skeleton. |
| `agentic-workspace planning delegation-decision` | `core_context_router` | `ordinary_host_repo` | yes | 11 | Record the delegation route chosen for the active execplan before mechanical lane work proceeds. |
| `agentic-workspace planning handoff` | `core_context_router` | `ordinary_host_repo` | no | 5 | Emit the compact delegated-worker handoff derived from active planning state. |
| `agentic-workspace planning report` | `core_context_router` | `ordinary_host_repo` | no | 5 | Report compact planning module state. |
| `agentic-workspace planning reconcile` | `core_context_router` | `ordinary_host_repo` | yes | 12 | Preview or apply bounded Planning reconciliation transactions. |
| `agentic-workspace memory` | `core_context_router` | `ordinary_host_repo` | no | 2 | Show memory workflow help or run Memory operations through the workspace front door. |
| `agentic-workspace memory route` | `core_context_router` | `ordinary_host_repo` | no | 7 | Suggest the smallest relevant durable note set for touched files or surfaces. |
| `agentic-workspace memory sync-memory` | `core_context_router` | `ordinary_host_repo` | yes | 4 | Suggest memory updates for changed work. |
| `agentic-workspace memory promotion-report` | `core_context_router` | `ordinary_host_repo` | no | 5 | Suggest memory notes that should be promoted or eliminated. |
| `agentic-workspace memory capture-note` | `core_context_router` | `ordinary_host_repo` | yes | 10 | Recommend whether durable learning should update or create a Memory note. |
| `agentic-workspace memory create-note` | `core_context_router` | `ordinary_host_repo` | yes | 19 | Create a repo-shared or local-only Memory note. |
| `agentic-workspace memory report` | `core_context_router` | `ordinary_host_repo` | no | 3 | Report compact memory module state. |
| `agentic-workspace evaluation` | `core_lifecycle` | `ordinary_host_repo` | yes | 2 | Manage local-first workspace evaluations. |
| `agentic-workspace evaluation register` | `core_lifecycle` | `ordinary_host_repo` | yes | 12 | Register or update one evaluation definition. |
| `agentic-workspace evaluation observe` | `core_lifecycle` | `ordinary_host_repo` | yes | 10 | Append one local observation. |
| `agentic-workspace evaluation authority-refresh` | `core_lifecycle` | `ordinary_host_repo` | yes | 4 | Refresh observation authority from the current public assignment or explicit active Planning owner and admitted proof receipt. |
| `agentic-workspace evaluation status` | `core_lifecycle` | `ordinary_host_repo` | no | 4 | Inspect derived evaluation status. |
| `agentic-workspace evaluation report-preview` | `core_lifecycle` | `ordinary_host_repo` | no | 4 | Compile the current evaluation report authority without claiming external delivery. |
| `agentic-workspace evaluation local-delivery` | `core_lifecycle` | `ordinary_host_repo` | yes | 4 | Record a local report compilation receipt without claiming external sink delivery. |
| `agentic-workspace evaluation external-request` | `core_lifecycle` | `ordinary_host_repo` | no | 4 | Create the current per-sink external delivery request. |
| `agentic-workspace evaluation external-host-result-import` | `core_lifecycle` | `advanced_host_repo` | yes | 5 | Import a provider-owned external adapter host result by opaque reference. |
| `agentic-workspace evaluation external-adapter-receipt` | `core_lifecycle` | `advanced_host_repo` | yes | 14 | Record a producer-owned external adapter attempt/result receipt. |
| `agentic-workspace evaluation external-delivery` | `core_lifecycle` | `ordinary_host_repo` | yes | 5 | Admit one external delivery result from a current producer-owned adapter receipt. |
| `agentic-workspace evaluation delivery-status` | `core_lifecycle` | `ordinary_host_repo` | no | 4 | Project per-sink report delivery status from admitted receipts. |
| `agentic-workspace evaluation retry` | `core_lifecycle` | `ordinary_host_repo` | no | 4 | Return the current retryable external delivery request for pending or failed sinks. |
| `agentic-workspace evaluation transition` | `core_lifecycle` | `ordinary_host_repo` | yes | 6 | Move an evaluation through a validated lifecycle transition. |
| `agentic-workspace evaluation prune` | `core_lifecycle` | `ordinary_host_repo` | yes | 4 | Prune or compact local evaluation observation history. |
| `agentic-workspace checkpoint` | `core_context_router` | `ordinary_host_repo` | yes | 2 | Create or update ignored local chat continuity checkpoints. |
| `agentic-workspace checkpoint write` | `core_context_router` | `ordinary_host_repo` | yes | 11 | Write or refresh .agentic-workspace/local/chat-checkpoint.json. |
| `agentic-workspace final-response` | `core_context_router` | `ordinary_host_repo` | yes | 2 | Admit model-authored final responses at the host boundary. |
| `agentic-workspace final-response admit` | `core_context_router` | `ordinary_host_repo` | yes | 11 | Admit or reject a model-authored final response attempt. |
| `agentic-workspace autopilot` | `core_context_router` | `ordinary_host_repo` | yes | 5 | Run the ordinary AW executor loop through final-response admission. |
| `agentic-workspace work-thread` | `core_context_router` | `ordinary_host_repo` | yes | 2 | Manage ignored local work-thread continuation handles. |
| `agentic-workspace work-thread select` | `core_context_router` | `ordinary_host_repo` | yes | 3 | Select an ignored local work-thread continuation handle. |
| `agentic-workspace work-thread carry-inspect` | `core_context_router` | `ordinary_host_repo` | no | 3 | Inspect decision-point intent carries by exact current-work ownership. |
| `agentic-workspace work-thread carry-select` | `core_context_router` | `ordinary_host_repo` | yes | 3 | Select one exact decision-point carry for closeout or stale recovery. |
| `agentic-workspace work-thread carry-prune` | `core_context_router` | `ordinary_host_repo` | yes | 6 | Mark one exactly selected stale decision-point carry without archiving its owner. |
| `agentic-workspace work-thread prune` | `core_context_router` | `ordinary_host_repo` | yes | 5 | Prune ignored local work-thread records already classified as safe candidates. |
| `agentic-workspace session-log` | `reusable_host_repo_diagnostics` | `local_only` | yes | 2 | Inspect or annotate ignored local AW session logs. |
| `agentic-workspace session-log status` | `reusable_host_repo_diagnostics` | `local_only` | no | 2 | Report local AW session logging status. |
| `agentic-workspace session-log new-session` | `reusable_host_repo_diagnostics` | `local_only` | yes | 2 | Start a new ignored local AW session log. |
| `agentic-workspace session-log note` | `reusable_host_repo_diagnostics` | `local_only` | yes | 3 | Append an optional note to the current ignored local AW session log. |
| `agentic-workspace session-log signal` | `reusable_host_repo_diagnostics` | `local_only` | yes | 12 | Capture compact workaround or opportunity evidence for the existing improvement intake. |
| `agentic-workspace session-log analyze` | `reusable_host_repo_diagnostics` | `local_only` | no | 6 | Analyze an ignored local AW session log into counts, repeated commands, failures, artifacts, packet kinds, and friction candidates. |
| `agentic-workspace session-log repair` | `reusable_host_repo_diagnostics` | `local_only` | yes | 4 | Repair or backfill a partial local session-log index from its Markdown entries. |
| `agentic-workspace session-log export` | `reusable_host_repo_diagnostics` | `local_only` | yes | 5 | Export an existing local session log as a local diagnostic bundle with known local paths normalized. |
| `agentic-workspace start` | `core_context_router` | `ordinary_host_repo` | no | 6 | Return the minimum safe startup context for beginning work in a target repository. |
| `agentic-workspace implement` | `core_context_router` | `ordinary_host_repo` | no | 7 | Return a cheap-implementer context for a bounded changed-path scope. |
| `agentic-workspace defaults` | `core_context_router` | `ordinary_host_repo` | no | 4 | Show the machine-readable default-route contract for startup, lifecycle, skills, validation, and combined installs. |
| `agentic-workspace proof` | `core_context_router` | `ordinary_host_repo` | yes | 38 | Show the canonical proof routes and current workspace proof summary. |
| `agentic-workspace setup` | `reusable_host_repo_diagnostics` | `advanced_host_repo` | no | 4 | Show the bounded post-bootstrap setup guidance for a mature repository. |
| `agentic-workspace ownership` | `core_context_router` | `ordinary_host_repo` | no | 4 | Show the canonical ownership and authority mapping for the target repository. |
| `agentic-workspace config` | `core_context_router` | `ordinary_host_repo` | no | 4 | Show the resolved repo-owned workspace config layered onto product defaults. |
| `agentic-workspace config-policy` | `core_context_router` | `advanced_host_repo` | yes | 6 | Apply one structured shared or local workspace policy decision without replacing unrelated configuration. |
| `agentic-workspace system-intent` | `core_context_router` | `ordinary_host_repo` | no | 3 | Show or refresh the workspace-owned compiled system-intent declaration. |
| `agentic-workspace note-delegation-outcome` | `reusable_host_repo_diagnostics` | `local_only` | yes | 14 | Append one local-only delegation outcome record for target-profile tuning. |
| `agentic-workspace skills` | `module_delegation_front_door` | `ordinary_host_repo` | no | 4 | List registered workspace skills from installed package registries and repo-owned skill registries. |
| `agentic-workspace report` | `core_context_router` | `ordinary_host_repo` | no | 11 | Show a compact combined workspace report for installed modules, mixed-agent posture, and next-action guidance. |
| `agentic-workspace reconcile` | `reusable_host_repo_diagnostics` | `advanced_host_repo` | yes | 4 | Show stale planning state against provider-agnostic external work evidence. |
| `agentic-workspace external-evidence-submit` | `reusable_host_repo_diagnostics` | `advanced_host_repo` | no | 4 | Submit an external proof candidate by opaque signed host-result reference. |
| `agentic-workspace external-evidence-query` | `reusable_host_repo_diagnostics` | `advanced_host_repo` | no | 4 | Query and revalidate one admitted external proof result. |
| `agentic-workspace external-intent` | `reusable_host_repo_diagnostics` | `advanced_host_repo` | no | 0 | Refresh optional provider-agnostic external intent evidence through adapter subcommands. |
| `agentic-workspace external-intent refresh-github` | `reusable_host_repo_diagnostics` | `advanced_host_repo` | yes | 9 | Refresh external intent evidence from GitHub issues through the optional gh CLI adapter. |
| `agentic-workspace preflight` | `core_context_router` | `ordinary_host_repo` | no | 5 | Get compact takeover-safe context: startup defaults + resolved config + active planning state in one call. |
| `agentic-workspace install` | `core_lifecycle` | `ordinary_host_repo` | yes | 15 | Bootstrap selected modules into a target repository. |
| `agentic-workspace init` | `core_lifecycle` | `ordinary_host_repo` | yes | 15 | Bootstrap selected modules into a target repository. |
| `agentic-workspace prompt` | `core_lifecycle` | `ordinary_host_repo` | no | 0 | Print a ready-to-paste workspace lifecycle handoff prompt. |
| `agentic-workspace prompt init` | `core_lifecycle` | `ordinary_host_repo` | no | 6 | Print the workspace bootstrap handoff prompt. |
| `agentic-workspace prompt upgrade` | `core_lifecycle` | `ordinary_host_repo` | no | 4 | Print the workspace upgrade handoff prompt. |
| `agentic-workspace prompt uninstall` | `core_lifecycle` | `ordinary_host_repo` | no | 4 | Print the workspace uninstall handoff prompt. |
| `agentic-workspace status` | `core_lifecycle` | `advanced_host_repo` | no | 6 | Show installed-module health for lifecycle checks; ordinary agents should use start/report routing first. |
| `agentic-workspace doctor` | `core_lifecycle` | `advanced_host_repo` | no | 6 | Show drift diagnostics for recovery or remediation; ordinary agents should use start/report routing first. |
| `agentic-workspace upgrade` | `core_lifecycle` | `ordinary_host_repo` | yes | 17 | Refresh managed surfaces for selected installed modules. |
| `agentic-workspace uninstall` | `core_lifecycle` | `ordinary_host_repo` | yes | 9 | Remove managed surfaces conservatively for selected installed modules. |
| `agentic-workspace agent-guidance` | `reusable_host_repo_diagnostics` | `ordinary_host_repo` | no | 0 | Promote and mutate local target guidance through generated operations. |
| `agentic-workspace agent-guidance promote` | `reusable_host_repo_diagnostics` | `ordinary_host_repo` | yes | 14 | Promote one authorised guidance candidate into its lifecycle store. |
| `agentic-workspace agent-guidance edit` | `reusable_host_repo_diagnostics` | `ordinary_host_repo` | yes | 14 | Edit one guidance record while preserving provenance and revision history. |
| `agentic-workspace agent-guidance merge` | `reusable_host_repo_diagnostics` | `ordinary_host_repo` | yes | 14 | Merge guidance records and preserve source lineage. |
| `agentic-workspace agent-guidance split` | `reusable_host_repo_diagnostics` | `ordinary_host_repo` | yes | 14 | Split one guidance record into replacement records. |
| `agentic-workspace agent-guidance suppress` | `reusable_host_repo_diagnostics` | `ordinary_host_repo` | yes | 14 | Suppress guidance without deleting provenance. |
| `agentic-workspace agent-guidance revalidate` | `reusable_host_repo_diagnostics` | `ordinary_host_repo` | yes | 14 | Revalidate guidance against the current target identity. |
| `agentic-workspace agent-guidance weaken` | `reusable_host_repo_diagnostics` | `ordinary_host_repo` | yes | 14 | Weaken guidance to advisory-only routing. |
| `agentic-workspace agent-guidance supersede` | `reusable_host_repo_diagnostics` | `ordinary_host_repo` | yes | 14 | Supersede guidance with a replacement record. |
| `agentic-workspace agent-guidance retire` | `reusable_host_repo_diagnostics` | `ordinary_host_repo` | yes | 14 | Retire guidance from future routing. |
| `agentic-workspace agent-guidance delete` | `reusable_host_repo_diagnostics` | `ordinary_host_repo` | yes | 14 | Delete guidance routing while retaining mutation receipt provenance. |
| `agentic-workspace assignment` | `core_context_router` | `advanced_host_repo` | no | 2 | Execute public assignment/run lifecycle operations. |
| `agentic-workspace assignment admit` | `core_context_router` | `advanced_host_repo` | no | 11 | Run assignment.admit. |
| `agentic-workspace assignment cleanup` | `core_context_router` | `advanced_host_repo` | no | 6 | Run assignment.cleanup. |
| `agentic-workspace assignment status` | `reusable_host_repo_diagnostics` | `advanced_host_repo` | no | 1 | Run assignment.status. |
| `agentic-workspace assignment close` | `core_context_router` | `advanced_host_repo` | no | 6 | Run assignment.close. |
| `agentic-workspace assignment dispatch` | `core_context_router` | `advanced_host_repo` | no | 1 | Run assignment.dispatch. |
| `agentic-workspace assignment export` | `core_context_router` | `advanced_host_repo` | no | 6 | Run assignment.export. |
| `agentic-workspace assignment import` | `core_context_router` | `advanced_host_repo` | no | 6 | Run assignment.import. |
| `agentic-workspace assignment integrate` | `core_context_router` | `advanced_host_repo` | no | 6 | Run assignment.integrate. |
| `agentic-workspace assignment override` | `core_context_router` | `advanced_host_repo` | no | 6 | Run assignment.override. |
| `agentic-workspace assignment reassign` | `core_context_router` | `advanced_host_repo` | no | 6 | Run assignment.reassign. |
| `agentic-workspace assignment reject` | `core_context_router` | `advanced_host_repo` | no | 6 | Run assignment.reject. |
| `agentic-workspace assignment repair` | `core_context_router` | `advanced_host_repo` | no | 6 | Run assignment.repair. |
| `agentic-workspace correction-event` | `reusable_host_repo_diagnostics` | `ordinary_host_repo` | no | 0 | Submit, query, and compact local correction events through generated operations. |
| `agentic-workspace correction-event identity-init` | `reusable_host_repo_diagnostics` | `ordinary_host_repo` | yes | 6 | Initialize one stable configured target identity in ignored local config. |
| `agentic-workspace correction-event submit` | `reusable_host_repo_diagnostics` | `ordinary_host_repo` | yes | 28 | Submit a correction event through the public local operation boundary. |
| `agentic-workspace correction-event query` | `reusable_host_repo_diagnostics` | `ordinary_host_repo` | no | 25 | Query admitted and low-authority correction events from bounded local storage. |
| `agentic-workspace correction-event correct-dispute` | `reusable_host_repo_diagnostics` | `ordinary_host_repo` | yes | 25 | Record a dispute/correction transition for a prior correction event. |
| `agentic-workspace correction-event withdraw-supersede` | `reusable_host_repo_diagnostics` | `ordinary_host_repo` | yes | 25 | Withdraw or supersede a prior correction event. |
| `agentic-workspace correction-event prune-compact` | `reusable_host_repo_diagnostics` | `ordinary_host_repo` | yes | 25 | Compact bounded local correction-event storage while preserving lineage. |

## `agentic-workspace modules`

module inventory drill-down for explicit module inspection; not required for ordinary startup

| Flags | Required | Default | Choices | Action / nargs | Description |
| --- | --- | --- | --- | --- | --- |
| `--format` | no | `text` | text, json | `value` | Output format. |
| `--target` | no | `—` | — | `value` | Optional repository path used to report installed modules. |
| `--verbose` | no | `—` | — | `store_true` | Emit full module registry and component detail. Prefer the default output for ordinary routing. |

## `agentic-workspace instructions`

target-neutral scoped Markdown instruction authoring and inspection

| Flags | Required | Default | Choices | Action / nargs | Description |
| --- | --- | --- | --- | --- | --- |
| — | — | — | — | — | No declared options. |

## `agentic-workspace instructions list`

progressive-disclosure instruction inventory

| Flags | Required | Default | Choices | Action / nargs | Description |
| --- | --- | --- | --- | --- | --- |
| `--format` | no | `text` | text, json | `value` | Output format. |
| `--target` | no | `—` | — | `value` | Target repository path. Defaults to current directory. |

## `agentic-workspace instructions new`

no-overwrite instruction scaffold creation

| Flags | Required | Default | Choices | Action / nargs | Description |
| --- | --- | --- | --- | --- | --- |
| `--format` | no | `text` | text, json | `value` | Output format. |
| `--name` | yes | `—` | — | `value` | Lowercase instruction identity used as the filename stem. |
| `--paths` | no | `—` | — | `append` | Repository-relative applicability pattern. Repeat for multiple patterns. |
| `--target` | no | `—` | — | `value` | Target repository path. Defaults to current directory. |

## `agentic-workspace instructions check`

static instruction validation

| Flags | Required | Default | Choices | Action / nargs | Description |
| --- | --- | --- | --- | --- | --- |
| `--format` | no | `text` | text, json | `value` | Output format. |
| `--target` | no | `—` | — | `value` | Target repository path. Defaults to current directory. |

## `agentic-workspace instructions explain`

task-scoped instruction applicability explanation

| Flags | Required | Default | Choices | Action / nargs | Description |
| --- | --- | --- | --- | --- | --- |
| `--format` | no | `text` | text, json | `value` | Output format. |
| `--task` | no | `—` | — | `value` | Optional task text used during applicability explanation. |
| `--changed` | no | `—` | — | `append` | Changed or target path. Repeat for multiple paths. |
| `--verbose` | no | `—` | — | `store_true` | Include the compiled instruction program. |
| `--target` | no | `—` | — | `value` | Target repository path. Defaults to current directory. |

## `agentic-workspace instructions routes`

progressive semantic task-route discovery

| Flags | Required | Default | Choices | Action / nargs | Description |
| --- | --- | --- | --- | --- | --- |
| `--format` | no | `text` | text, json | `value` | Output format. |
| `--parent` | no | `—` | — | `value` | Optional route branch to expand one level. |
| `--exact` | no | `—` | — | `value` | Optional known route leaf to inspect directly. |
| `--target` | no | `—` | — | `value` | Target repository path. Defaults to current directory. |

## `agentic-workspace instructions select-route`

authority-neutral current-task route fact selection

| Flags | Required | Default | Choices | Action / nargs | Description |
| --- | --- | --- | --- | --- | --- |
| `--format` | no | `text` | text, json | `value` | Output format. |
| `--posture` | yes | `—` | selected, none, unresolved | `value` | Explicit semantic applicability posture. |
| `--route` | no | `—` | — | `append` | Existing route leaf. Repeat for multiple facets. |
| `--current-work-id` | no | `—` | — | `value` | Optional exact current-work guard. |
| `--expect-source-revision` | yes | `—` | — | `value` | Exact source revision returned by route discovery. |
| `--dry-run` | no | `—` | — | `store_true` | Validate the selection without writing local state. |
| `--target` | no | `—` | — | `value` | Target repository path. Defaults to current directory. |

## `agentic-workspace instructions migrate`

non-destructive static-instruction migration advice

| Flags | Required | Default | Choices | Action / nargs | Description |
| --- | --- | --- | --- | --- | --- |
| `--format` | no | `text` | text, json | `value` | Output format. |
| `--from` | yes | `—` | — | `value` | Repository-relative instruction source to inspect. |
| `--target` | no | `—` | — | `value` | Target repository path. Defaults to current directory. |

## `agentic-workspace summary`

compact active planning and handoff state

| Flags | Required | Default | Choices | Action / nargs | Description |
| --- | --- | --- | --- | --- | --- |
| `--format` | no | `text` | text, json | `value` | Output format. |
| `--target` | no | `—` | — | `value` | Optional repository path to read summary from. |
| `--select` | no | `—` | — | `value` | Return only comma-separated top-level or dotted JSON fields from the full command payload. Prefer this over --verbose when one or a few fields are needed. |
| `--verbose` | no | `—` | — | `store_true` | Emit full planning summary detail. Prefer selectors/default routing for ordinary startup. |
| `--task` | no | `—` | — | `value` | Optional task text used to return a task-scoped compact summary. |
| `--changed` | no | `—` | — | `extend; nargs=*` | Optional changed paths used to scope compact summary output. |

## `agentic-workspace planning`

planning lifecycle help and schema-owned mutation guidance

| Flags | Required | Default | Choices | Action / nargs | Description |
| --- | --- | --- | --- | --- | --- |
| `--format` | no | `text` | text, json | `value` | Output format. |
| `--target` | no | `—` | — | `value` | Optional repository path used in example commands. |

## `agentic-workspace planning new-plan`

Planning mutation front door

| Flags | Required | Default | Choices | Action / nargs | Description |
| --- | --- | --- | --- | --- | --- |
| `--format` | no | `text` | text, json | `value` | Output format. |
| `--id` | yes | `—` | — | `value` | Stable slug/id for the plan; used as the .plan.json filename. |
| `--title` | yes | `—` | — | `value` | Human-readable plan title. |
| `--source` | no | `—` | — | `value` | Optional source reference such as an issue URL or chat-intake summary. |
| `--target` | no | `—` | — | `value` | Optional repository path. |
| `--activate` | no | `—` | — | `store_true` | Register the new plan in todo.active_items. |
| `--queue` | no | `—` | — | `store_true` | Register the new plan in todo.queued_items. |
| `--switch-active` | no | `—` | — | `store_true` | When used with --activate, demote existing active items into the queue before registering the new active plan. |
| `--lane` | no | `—` | — | `value` | Explicit active lane that owns this plan; requires --activate. |
| `--prep-only` | no | `—` | — | `store_true` | Mark this scaffold as a planning-only handoff slice. |
| `--overwrite` | no | `—` | — | `store_true` | Replace an existing scaffold with the same id. |
| `--dry-run` | no | `—` | — | `store_true` | Show planned changes without mutating files. |

## `agentic-workspace planning targeted-write`

Revision-guarded Planning owner mutation front door

| Flags | Required | Default | Choices | Action / nargs | Description |
| --- | --- | --- | --- | --- | --- |
| `--format` | no | `text` | text, json | `value` | Output format. |
| `--plan` | yes | `—` | — | `value` | Exact live execplan id or repo-relative owner path. |
| `--patch` | yes | `—` | — | `value` | JSON object containing only supported owner-scoped fields. |
| `--expect-planning-revision` | no | `—` | — | `value` | Optional low-level Planning revision guard; ordinary semantic mutation resolves current owner authority internally. |
| `--expect-owner-revision` | no | `—` | — | `value` | Optional low-level execplan owner revision guard; omit with the other guards for ordinary semantic mutation. |
| `--expect-lane-revision` | no | `—` | — | `value` | Optional low-level lane revision guard; ordinary semantic mutation resolves the current bound lane internally. |
| `--apply` | no | `—` | — | `store_true` | Apply after rerunning the operation's sealed internal preflight. |
| `--target` | no | `—` | — | `value` | Optional repository path. |

## `agentic-workspace planning promote-to-plan`

Planning mutation front door

| Flags | Required | Default | Choices | Action / nargs | Description |
| --- | --- | --- | --- | --- | --- |
| `--format` | no | `text` | text, json | `value` | Output format. |
| `--item-id` | yes | `—` | — | `value` | Planning item id to promote. |
| `--target` | no | `—` | — | `value` | Optional repository path. |
| `--plan-slug` | no | `—` | — | `value` | Optional generated plan slug override. |
| `--dry-run` | no | `—` | — | `store_true` | Show planned changes without mutating files. |

## `agentic-workspace planning owner-select`

Existing Planning owner selection front door

| Flags | Required | Default | Choices | Action / nargs | Description |
| --- | --- | --- | --- | --- | --- |
| `--format` | no | `text` | text, json | `value` | Output format. |
| `--owner` | no | `—` | — | `value` | Stable existing owner id. |
| `--owner-ref` | no | `—` | — | `value` | Explicit repo-relative existing owner reference. |
| `--target` | no | `—` | — | `value` | Optional repository path. |
| `--mode` | no | `local` | local, shared | `value` | Selection scope; local is advisory and current-work scoped. |
| `--reason` | no | `—` | — | `value` | Required reason for explicit shared checked-in selection. |
| `--current-work-id` | no | `—` | — | `value` | Stable current-work context id; defaults to the local context. |
| `--expect-planning-revision` | no | `—` | — | `value` | Optimistic Planning revision id. |
| `--expect-current-work-revision` | no | `—` | — | `value` | Optimistic current-work selection revision. |
| `--dry-run` | no | `—` | — | `store_true` | Return the exact proposed delta without writing files. |

## `agentic-workspace planning decomposition-create`

Planning decomposition artifact mutation front door

| Flags | Required | Default | Choices | Action / nargs | Description |
| --- | --- | --- | --- | --- | --- |
| `--format` | no | `text` | text, json | `value` | Output format. |
| `--id` | yes | `—` | — | `value` | Stable decomposition id. |
| `--title` | yes | `—` | — | `value` | Human-readable decomposition title. |
| `--outcome` | yes | `—` | — | `value` | Larger intended outcome. |
| `--promotion-rule` | no | `Promote a candidate lane only after its scope, owner surface, and proof are ready.` | — | `value` | Candidate-lane promotion rule. |
| `--target` | no | `—` | — | `value` | Optional repository path. |
| `--dry-run` | no | `—` | — | `store_true` | Show planned changes without mutating files. |

## `agentic-workspace planning lane-create`

Planning lane artifact mutation front door

| Flags | Required | Default | Choices | Action / nargs | Description |
| --- | --- | --- | --- | --- | --- |
| `--format` | no | `text` | text, json | `value` | Output format. |
| `--id` | yes | `—` | — | `value` | Stable lane id; used as the .lane.json filename. |
| `--title` | no | `—` | — | `value` | Human-readable lane title. |
| `--parent-decomposition` | no | `—` | — | `value` | Optional parent decomposition record path. |
| `--outcome` | no | `—` | — | `value` | Lane-level outcome. |
| `--purpose` | no | `—` | — | `value` | How this lane advances the parent decomposition. |
| `--proof-strategy` | no | `—` | — | `value` | How slice proofs aggregate into lane proof. |
| `--bind-execplan` | no | `—` | — | `value` | Existing execplan owner to bind atomically as a child of the created or reused lane. |
| `--source-ref` | no | `—` | — | `value` | External parent identity recorded on a newly created lane for deterministic reuse. |
| `--target` | no | `—` | — | `value` | Optional repository path. |
| `--dry-run` | no | `—` | — | `store_true` | Show planned changes without mutating files. |

## `agentic-workspace planning lane-promote`

Planning lane artifact mutation front door

| Flags | Required | Default | Choices | Action / nargs | Description |
| --- | --- | --- | --- | --- | --- |
| `--format` | no | `text` | text, json | `value` | Output format. |
| `--lane` | yes | `—` | — | `value` | Decomposition candidate lane id to promote. |
| `--target` | no | `—` | — | `value` | Optional repository path. |
| `--alternate-lane-id` | no | `—` | — | `value` | Use this lane record id when the default owner surface is already owned by incompatible provenance. |
| `--dry-run` | no | `—` | — | `store_true` | Show planned changes without mutating files. |

## `agentic-workspace planning lane-activate`

Planning lane artifact mutation front door

| Flags | Required | Default | Choices | Action / nargs | Description |
| --- | --- | --- | --- | --- | --- |
| `--format` | no | `text` | text, json | `value` | Output format. |
| `--lane` | yes | `—` | — | `value` | Lane id to activate. |
| `--current-slice` | no | `—` | — | `value` | Optional lane slice id to mark active. |
| `--target` | no | `—` | — | `value` | Optional repository path. |
| `--dry-run` | no | `—` | — | `store_true` | Show planned changes without mutating files. |

## `agentic-workspace planning lane-close`

Planning lane artifact mutation front door

| Flags | Required | Default | Choices | Action / nargs | Description |
| --- | --- | --- | --- | --- | --- |
| `--format` | no | `text` | text, json | `value` | Output format. |
| `--lane` | yes | `—` | — | `value` | Lane id to close. |
| `--proof` | no | `—` | — | `value` | Lane-level proof evidence to aggregate. |
| `--residual-work` | no | `—` | — | `value` | Residual lane work or known proof gap. |
| `--parent-contribution` | no | `—` | — | `value` | How this lane advances the parent epic. |
| `--parent-close-permission` | no | `may-advance-parent` | do-not-close-parent, may-advance-parent, may-close-parent-after-human-confirmation, may-close-parent | `value` | Whether this lane permits parent advancement or closure. |
| `--next-owner` | no | `—` | — | `value` | Owner for residual lane or parent work. |
| `--target` | no | `—` | — | `value` | Optional repository path. |
| `--dry-run` | no | `—` | — | `store_true` | Show planned changes without mutating files. |

## `agentic-workspace planning lane-archive`

Planning lane artifact mutation front door

| Flags | Required | Default | Choices | Action / nargs | Description |
| --- | --- | --- | --- | --- | --- |
| `--format` | no | `text` | text, json | `value` | Output format. |
| `--lane` | yes | `—` | — | `value` | Closed lane id to archive. |
| `--target` | no | `—` | — | `value` | Optional repository path. |
| `--dry-run` | no | `—` | — | `store_true` | Show planned changes without mutating files. |

## `agentic-workspace planning intake-artifact`

Planning freehand artifact intake front door

| Flags | Required | Default | Choices | Action / nargs | Description |
| --- | --- | --- | --- | --- | --- |
| `--format` | no | `text` | text, json | `value` | Output format. |
| `--artifact` | yes | `—` | — | `value` | Freehand planning artifact path inside the target repository. |
| `--route` | no | `auto` | auto, execplan, decomposition | `value` | Canonical Planning surface to route the artifact into. |
| `--id` | no | `—` | — | `value` | Optional target id or slug for the canonical Planning surface. |
| `--title` | no | `—` | — | `value` | Optional title when routing to an execplan scaffold. |
| `--target` | no | `—` | — | `value` | Optional repository path. |
| `--activate` | no | `—` | — | `store_true` | Register an execplan route in todo.active_items. |
| `--queue` | no | `—` | — | `store_true` | Register an execplan route in todo.queued_items. |
| `--switch-active` | no | `—` | — | `store_true` | When used with --activate, demote existing active items before registering the new active plan. |
| `--remove-source` | no | `—` | — | `store_true` | Remove the original artifact after successful canonical intake. |
| `--dry-run` | no | `—` | — | `store_true` | Show planned changes without mutating files. |

## `agentic-workspace planning archive-plan`

Planning closeout front door

| Flags | Required | Default | Choices | Action / nargs | Description |
| --- | --- | --- | --- | --- | --- |
| `--format` | no | `text` | text, json | `value` | Output format. |
| `--plan` | no | `—` | — | `value` | Plan path, slug, or id to archive. |
| `--target` | no | `—` | — | `value` | Optional repository path. |
| `--dry-run` | no | `—` | — | `store_true` | Show planned changes without mutating files. |
| `--apply-cleanup` | no | `—` | — | `store_true` | Apply narrow cleanup tied to the archived plan. |
| `--prepare-closeout` | no | `—` | — | `store_true` | Write package-normalized closeout fields before archive validation runs. |
| `--retain-archive` | no | `—` | — | `store_true` | Keep a completed execplan record under execplans/archive. |
| `--compact-retained` | no | `—` | — | `store_true` | Replace an already-retained archive (or --plan all-archived) with a compact Git receipt after reversible export; requires --apply-cleanup to mutate. |
| `--export-dir` | no | `—` | — | `value` | Export directory for full retained evidence; defaults to ignored local Planning exports and must be outside checked-in Planning state. |
| `--parent-lane-closeout` | no | `—` | — | `value` | Close a parent lane from structured planning state. |
| `--closure-decision` | no | `—` | archive-and-close, archive-but-keep-lane-open | `value` | Closeout decision to write when --prepare-closeout is used. |
| `--intent-satisfied` | no | `—` | yes, no, true, false | `value` | Whether the larger original intent is fully satisfied. |
| `--unsolved-intent` | no | `—` | — | `value` | Continuation owner for unsolved larger intent. |
| `--intent-evidence` | no | `—` | — | `value` | Evidence of intent satisfaction for prepared closeout. |
| `--closure-reason` | no | `—` | — | `value` | Why the prepared closure decision is honest. |
| `--closure-evidence` | no | `—` | — | `value` | Evidence carried forward by the prepared closure. |
| `--reopen-trigger` | no | `—` | — | `value` | Reopen trigger for the prepared closure. |
| `--discard-summary` | no | `—` | — | `value` | Closeout distillation discard bucket summary. |
| `--continuation-summary` | no | `—` | — | `value` | Closeout distillation continuation bucket summary. |

## `agentic-workspace planning closeout`

Planning command-owned closeout writer

| Flags | Required | Default | Choices | Action / nargs | Description |
| --- | --- | --- | --- | --- | --- |
| `--format` | no | `text` | text, json | `value` | Output format. |
| `--target` | no | `—` | — | `value` | Optional repository path. |
| `--claim-level` | no | `slice` | slice, lane, epic | `value` | Scope claimed by this closeout. |
| `--intent-status` | no | `satisfied` | satisfied, partial, unsatisfied, deferred-with-owner | `value` | Intent result for the closeout claim. |
| `--residue` | no | `none` | none, memory, planning, docs, tests, contracts, issue, dismissed | `value` | Durable residue route for follow-up or learning. |
| `--proof-from` | no | `last` | — | `value` | Use existing proof with 'last' or record the supplied proof command/text. |
| `--proof-file` | no | `—` | — | `value` | Read closeout proof text from a repo-contained file instead of a shell-sensitive argument. |
| `--residue-owner` | no | `—` | — | `value` | Canonical owner for non-empty residue or deferred intent. |
| `--what-happened` | no | `—` | — | `value` | Finished-run summary to write when the execplan still has placeholder execution evidence. |
| `--scope-touched` | no | `—` | — | `value` | Concrete scope touched by the finished run. |
| `--changed-surfaces` | no | `—` | — | `value` | Concrete files or surfaces changed by the finished run. |
| `--review-summary` | no | `—` | — | `value` | Closeout review summary for scope and intent reconciliation. |
| `--outcome-summary` | no | `—` | — | `value` | Outcome delivered summary for the finished run. |
| `--dry-run` | no | `—` | — | `store_true` | Show closeout actions without mutating files. |
| `--discard-archive` | no | `—` | — | `store_true` | Do not retain the archived execplan record after cleanup. |

## `agentic-workspace planning close-item`

Planning generic closeout front door

| Flags | Required | Default | Choices | Action / nargs | Description |
| --- | --- | --- | --- | --- | --- |
| `--format` | no | `text` | text, json | `value` | Output format. |
| `--item` | yes | `—` | — | `value` | Planning item id to close. |
| `--target` | no | `—` | — | `value` | Optional repository path. |
| `--reason` | no | `—` | — | `value` | Optional closure reason to record in the action detail. |
| `--issue` | no | `—` | — | `value` | Optional upstream issue reference tied to the closeout. |
| `--dry-run` | no | `—` | — | `store_true` | Show planned changes without mutating files. |

## `agentic-workspace planning create-review`

Planning review mutation front door

| Flags | Required | Default | Choices | Action / nargs | Description |
| --- | --- | --- | --- | --- | --- |
| `--format` | no | `text` | text, json | `value` | Output format. |
| `--slug` | yes | `—` | — | `value` | Stable review record slug. |
| `--title` | yes | `—` | — | `value` | Human-readable review title. |
| `--target` | no | `—` | — | `value` | Optional repository path. |
| `--scope` | no | `—` | — | `value` | Review scope summary. |
| `--classification` | no | `review` | — | `value` | Review classification. |
| `--render-markdown` | no | `—` | — | `store_true` | Also render the derived markdown companion. |
| `--dry-run` | no | `—` | — | `store_true` | Show planned changes without mutating files. |

## `agentic-workspace planning delegation-decision`

Planning delegation decision front door

| Flags | Required | Default | Choices | Action / nargs | Description |
| --- | --- | --- | --- | --- | --- |
| `--format` | no | `text` | text, json | `value` | Output format. |
| `--target` | no | `—` | — | `value` | Optional repository path. |
| `--plan` | no | `—` | — | `value` | Plan path, slug, or id; defaults to the active execplan. |
| `--route` | yes | `—` | keep-local, delegate-exploration, delegate-implementation, delegate-validation, escalate-review, no-safe-route | `value` | Delegation route chosen for this slice. |
| `--skipped-reason` | no | `—` | — | `value` | Required explanation when route is keep-local. |
| `--expected-savings` | no | `—` | — | `value` | Expected time or token savings. |
| `--actual-friction` | no | `—` | — | `value` | Observed delegation friction. |
| `--proof-result` | no | `—` | — | `value` | Proof or validation result for the delegation decision. |
| `--quality-concern` | no | `—` | — | `value` | Any quality concern from delegation or skipping it. |
| `--decomposition-adjustment` | no | `—` | — | `value` | Any follow-up adjustment needed in the decomposition. |
| `--dry-run` | no | `—` | — | `store_true` | Show planned changes without mutating files. |

## `agentic-workspace planning handoff`

Planning handoff front door

| Flags | Required | Default | Choices | Action / nargs | Description |
| --- | --- | --- | --- | --- | --- |
| `--format` | no | `text` | text, json | `value` | Output format. |
| `--target` | no | `—` | — | `value` | Optional repository path. |
| `--scope` | no | `—` | — | `value` | Current handoff scope used by proof-route transition gates. |
| `--changed-surfaces` | no | `—` | — | `value` | Changed surfaces used to scope proof-route transition gates. |
| `--current-work-id` | no | `—` | — | `value` | Current work identity used to scope proof-route transition gates. |

## `agentic-workspace planning report`

Planning report front door

| Flags | Required | Default | Choices | Action / nargs | Description |
| --- | --- | --- | --- | --- | --- |
| `--format` | no | `text` | text, json | `value` | Output format. |
| `--target` | no | `—` | — | `value` | Optional repository path. |
| `--verbose` | no | `—` | — | `store_true` | Emit broad diagnostic report detail. |
| `--audit-cursor` | no | `—` | — | `value` | Opaque cursor returned by a previous audit page. |
| `--audit-page-size` | no | `25` | — | `value` | Maximum closeout records to load for this audit page. |

## `agentic-workspace planning reconcile`

Planning owner-specific reconciliation front door

| Flags | Required | Default | Choices | Action / nargs | Description |
| --- | --- | --- | --- | --- | --- |
| `--format` | no | `text` | text, json | `value` | Output format. |
| `--target` | no | `—` | — | `value` | Target repository path. Defaults to the current directory. |
| `--dry-run` | no | `—` | — | `store_true` | Preview --apply-safe-prune without writing files. |
| `--lane` | no | `—` | — | `value` | Lane id whose machine-readable child outcomes should be reconciled. |
| `--apply-lane-current-slice-reconcile` | no | `—` | — | `store_true` | Apply one owner-specific current-slice lane reconciliation transaction. |
| `--owner-surface` | no | `—` | — | `value` | Repo-relative owner surface guarded by current-slice reconciliation. |
| `--relation-identity` | no | `—` | — | `value` | Expected lane current-slice relation identity. |
| `--subject` | no | `—` | — | `value` | Expected current-slice subject id. |
| `--expect-lane-revision` | no | `—` | — | `value` | Current lane-record revision required before applying current-slice reconciliation. |
| `--transition` | no | `—` | restore, relink, supersede, cancel, human | `value` | Requested current-slice reconciliation transition. |
| `--expected-execplan` | no | `—` | — | `value` | Repo-relative execplan source: required for relink/supersede, optional for restore, and not used by cancel/human. |
| `--expect-planning-revision` | no | `—` | — | `value` | Planning revision returned by preview and required before applying current-slice reconciliation. |

## `agentic-workspace memory`

memory lifecycle help and route guidance

| Flags | Required | Default | Choices | Action / nargs | Description |
| --- | --- | --- | --- | --- | --- |
| `--format` | no | `text` | text, json | `value` | Output format. |
| `--target` | no | `—` | — | `value` | Optional repository path used in example commands. |

## `agentic-workspace memory route`

Memory routing front door

| Flags | Required | Default | Choices | Action / nargs | Description |
| --- | --- | --- | --- | --- | --- |
| `--format` | no | `text` | text, json | `value` | Output format. |
| `--target` | no | `—` | — | `value` | Optional repository path. |
| `--files` | no | `—` | — | `value; nargs=*` | Touched file paths to route from. |
| `--surface` | no | `—` | — | `value; nargs=*` | Explicit routing surfaces. |
| `--pending-command` | no | `—` | — | `value` | Pending local command to route as structured execution-surface context before running it. |
| `--task` | no | `—` | — | `value` | Task text for route context. Task prose is not routing authority. |
| `--stage` | no | `—` | startup, implement, closeout, report | `value` | Structured workflow stage to use as an explicit routing surface. |

## `agentic-workspace memory sync-memory`

Memory update front door

| Flags | Required | Default | Choices | Action / nargs | Description |
| --- | --- | --- | --- | --- | --- |
| `--format` | no | `text` | text, json | `value` | Output format. |
| `--target` | no | `—` | — | `value` | Optional repository path. |
| `--files` | no | `—` | — | `value; nargs=*` | Changed file paths to inspect. |
| `--notes` | no | `—` | — | `value; nargs=*` | Explicit memory notes to review. |

## `agentic-workspace memory promotion-report`

Memory promotion front door

| Flags | Required | Default | Choices | Action / nargs | Description |
| --- | --- | --- | --- | --- | --- |
| `--format` | no | `text` | text, json | `value` | Output format. |
| `--target` | no | `—` | — | `value` | Optional repository path. |
| `--notes` | no | `—` | — | `value; nargs=*` | Explicit memory notes to inspect. |
| `--mode` | no | `all` | all, remediation | `value` | Report all candidates or only remediation candidates. |
| `--verbose` | no | `—` | — | `store_true` | Emit broad diagnostic report detail. |

## `agentic-workspace memory capture-note`

Memory capture front door

| Flags | Required | Default | Choices | Action / nargs | Description |
| --- | --- | --- | --- | --- | --- |
| `--format` | no | `text` | text, json | `value` | Output format. |
| `--slug` | no | `—` | — | `value` | Suggested note slug. |
| `--summary` | no | `—` | — | `value` | Memory learning summary. |
| `--files` | no | `—` | — | `value; nargs=*` | Changed files associated with the learning. |
| `--surface` | no | `—` | — | `value; nargs=*` | Explicit routing surfaces. |
| `--task` | no | `—` | — | `value` | Task text for capture context. |
| `--stage` | no | `—` | startup, implement, closeout, report | `value` | Structured workflow stage associated with the learning. |
| `--existing-note` | no | `—` | — | `value` | Existing note path to update. |
| `--force-new-reason` | no | `—` | — | `value` | Reason a new note is required. |
| `--target` | no | `—` | — | `value` | Optional repository path. |

## `agentic-workspace memory create-note`

Memory note creation front door

| Flags | Required | Default | Choices | Action / nargs | Description |
| --- | --- | --- | --- | --- | --- |
| `--format` | no | `text` | text, json | `value` | Output format. |
| `--slug` | no | `—` | — | `value` | Memory note slug to create. |
| `--title` | no | `—` | — | `value` | Memory note title. Defaults to a title derived from the slug. |
| `--folder` | no | `domains` | — | `value` | Repo Memory folder under .agentic-workspace/memory/repo. |
| `--note-type` | no | `domain` | — | `value` | Repo Memory note type recorded in the manifest. |
| `--summary` | no | `—` | — | `value` | Short note summary. |
| `--local` | no | `—` | — | `store_true` | Create an ignored local-only note under .agentic-workspace/local/memory without updating the repo manifest. |
| `--local-reason` | no | `—` | — | `value` | Reason this note is machine-local rather than repo-shared. |
| `--applies-to` | no | `—` | — | `value; nargs=*` | Repo paths or surfaces this note applies to. |
| `--use-when` | no | `—` | — | `value; nargs=*` | Routing hints for when to use this note. |
| `--routes-from` | no | `—` | — | `value; nargs=*` | Surfaces or files that should route to this note. |
| `--stale-when` | no | `—` | — | `value; nargs=*` | Conditions that make this note stale. |
| `--evidence` | no | `—` | — | `value; nargs=*` | Evidence references supporting this note. |
| `--memory-role` | no | `—` | — | `value` | Memory role metadata. |
| `--promotion-target` | no | `—` | — | `value` | Optional durable promotion target. |
| `--promotion-trigger` | no | `—` | — | `value` | Optional promotion trigger. |
| `--retention-after-promotion` | no | `—` | — | `value` | Retention policy after promotion. |
| `--dry-run` | no | `—` | — | `store_true` | Show planned changes without writing files. |
| `--target` | no | `—` | — | `value` | Optional repository path. |

## `agentic-workspace memory report`

Memory report front door

| Flags | Required | Default | Choices | Action / nargs | Description |
| --- | --- | --- | --- | --- | --- |
| `--format` | no | `text` | text, json | `value` | Output format. |
| `--target` | no | `—` | — | `value` | Optional repository path. |
| `--verbose` | no | `—` | — | `store_true` | Emit broad diagnostic report detail. |

## `agentic-workspace evaluation`

local-first workspace evaluation lifecycle front door

| Flags | Required | Default | Choices | Action / nargs | Description |
| --- | --- | --- | --- | --- | --- |
| `--format` | no | `text` | text, json | `value` | Output format. |
| `--target` | no | `—` | — | `value` | Repository path. |

## `agentic-workspace evaluation register`

evaluation definition registration writes the local evaluation ledger

| Flags | Required | Default | Choices | Action / nargs | Description |
| --- | --- | --- | --- | --- | --- |
| `--target` | no | `—` | — | `value` | Repository path. |
| `--evaluation-id` | yes | `—` | — | `value` | — |
| `--question` | yes | `—` | — | `value` | — |
| `--subject` | no | `{"type":"workspace-task"}` | — | `value` | — |
| `--criteria` | yes | `—` | — | `value` | JSON object keyed by criterion id. |
| `--decision-owner` | yes | `—` | — | `value` | JSON object with id and class. |
| `--evidence-sources` | yes | `—` | — | `value` | Comma-separated evidence source ids. |
| `--report-sinks` | yes | `—` | — | `value` | Comma-separated report sink ids. |
| `--selectors` | no | `{}` | — | `value` | — |
| `--collection-policy` | no | `{}` | — | `value` | — |
| `--conclusion-policy` | no | `{}` | — | `value` | — |
| `--action-policy` | no | `{}` | — | `value` | — |

## `agentic-workspace evaluation observe`

local observation append for evaluation evidence collection

| Flags | Required | Default | Choices | Action / nargs | Description |
| --- | --- | --- | --- | --- | --- |
| `--target` | no | `—` | — | `value` | Repository path. |
| `--evaluation-id` | yes | `—` | — | `value` | — |
| `--criterion` | yes | `—` | — | `value` | — |
| `--result` | yes | `—` | supports, contradicts, mixed, not-applicable, unknown | `value` | — |
| `--evidence-refs` | no | `—` | — | `value` | — |
| `--confidence` | no | `medium` | low, medium, high | `value` | — |
| `--burden` | no | `medium` | low, medium, high | `value` | — |
| `--context` | no | `{}` | — | `value` | — |
| `--finding` | no | `—` | — | `value` | — |
| `--recommended-action` | no | `—` | — | `value` | — |

## `agentic-workspace evaluation authority-refresh`

repair local evaluation observation authority from current public owner receipts

| Flags | Required | Default | Choices | Action / nargs | Description |
| --- | --- | --- | --- | --- | --- |
| `--format` | no | `text` | text, json | `value` | Output format. |
| `--target` | no | `—` | — | `value` | Repository path. |
| `--evaluation-id` | yes | `—` | — | `value` | — |
| `--active-planning-owner` | no | `—` | — | `store_true` | Use the explicitly selected active Planning owner when no current delegated assignment exists. |

## `agentic-workspace evaluation status`

read-only derived evaluation status report

| Flags | Required | Default | Choices | Action / nargs | Description |
| --- | --- | --- | --- | --- | --- |
| `--format` | no | `text` | text, json | `value` | Output format. |
| `--target` | no | `—` | — | `value` | Repository path. |
| `--evaluation-id` | no | `—` | — | `value` | — |
| `--select` | no | `—` | — | `value` | Expand one or more comma-separated evaluation status detail fields, or full. |

## `agentic-workspace evaluation report-preview`

read-only report authority preview compiled from current admitted evaluation state

| Flags | Required | Default | Choices | Action / nargs | Description |
| --- | --- | --- | --- | --- | --- |
| `--format` | no | `text` | text, json | `value` | Output format. |
| `--target` | no | `—` | — | `value` | Repository path. |
| `--evaluation-id` | yes | `—` | — | `value` | — |
| `--explicit` | no | `no` | — | `store_true` | — |

## `agentic-workspace evaluation local-delivery`

local report compilation receipt with external delivery explicitly unattempted

| Flags | Required | Default | Choices | Action / nargs | Description |
| --- | --- | --- | --- | --- | --- |
| `--format` | no | `text` | text, json | `value` | Output format. |
| `--target` | no | `—` | — | `value` | Repository path. |
| `--evaluation-id` | yes | `—` | — | `value` | — |
| `--explicit` | no | `no` | — | `store_true` | — |

## `agentic-workspace evaluation external-request`

read-only current external delivery request requiring producer-owned adapter receipts

| Flags | Required | Default | Choices | Action / nargs | Description |
| --- | --- | --- | --- | --- | --- |
| `--format` | no | `text` | text, json | `value` | Output format. |
| `--target` | no | `—` | — | `value` | Repository path. |
| `--evaluation-id` | yes | `—` | — | `value` | — |
| `--explicit` | no | `no` | — | `store_true` | — |

## `agentic-workspace evaluation external-host-result-import`

provider-owned host result import/admission by opaque reference

| Flags | Required | Default | Choices | Action / nargs | Description |
| --- | --- | --- | --- | --- | --- |
| `--format` | no | `text` | text, json | `value` | Output format. |
| `--target` | no | `—` | — | `value` | Repository path. |
| `--provider-result-ref` | yes | `—` | — | `value` | — |
| `--expected-result-digest` | no | `—` | — | `value` | — |
| `--capability-revision` | no | `—` | — | `value` | — |

## `agentic-workspace evaluation external-adapter-receipt`

producer-owned external delivery attempt/result receipt indexed before admission

| Flags | Required | Default | Choices | Action / nargs | Description |
| --- | --- | --- | --- | --- | --- |
| `--format` | no | `text` | text, json | `value` | Output format. |
| `--target` | no | `—` | — | `value` | Repository path. |
| `--delivery-id` | yes | `—` | — | `value` | — |
| `--sink-id` | yes | `—` | — | `value` | — |
| `--producer` | yes | `—` | — | `value` | — |
| `--attempt-revision` | yes | `—` | — | `value` | — |
| `--receipt-revision` | yes | `—` | — | `value` | — |
| `--capability-revision` | yes | `—` | — | `value` | — |
| `--capability-status` | no | `current` | current, fresh, accepted | `value` | — |
| `--status-owner` | no | `provider-adapter` | provider-adapter, external-operation-adapter | `value` | — |
| `--status` | yes | `—` | delivered, failed | `value` | — |
| `--detail` | no | `—` | — | `value` | — |
| `--supersedes` | no | `—` | — | `value` | — |
| `--host-result-ref` | yes | `—` | — | `value` | — |

## `agentic-workspace evaluation external-delivery`

admit delivery status only from a current indexed producer-owned adapter receipt

| Flags | Required | Default | Choices | Action / nargs | Description |
| --- | --- | --- | --- | --- | --- |
| `--format` | no | `text` | text, json | `value` | Output format. |
| `--target` | no | `—` | — | `value` | Repository path. |
| `--evaluation-id` | yes | `—` | — | `value` | — |
| `--adapter-receipt-ref` | yes | `—` | — | `value` | — |
| `--explicit` | no | `no` | — | `store_true` | — |

## `agentic-workspace evaluation delivery-status`

read-only delivery status derived from local and provider-owned receipts

| Flags | Required | Default | Choices | Action / nargs | Description |
| --- | --- | --- | --- | --- | --- |
| `--format` | no | `text` | text, json | `value` | Output format. |
| `--target` | no | `—` | — | `value` | Repository path. |
| `--evaluation-id` | yes | `—` | — | `value` | — |
| `--explicit` | no | `no` | — | `store_true` | — |

## `agentic-workspace evaluation retry`

read-only retry projection; actual success still requires a fresh adapter receipt

| Flags | Required | Default | Choices | Action / nargs | Description |
| --- | --- | --- | --- | --- | --- |
| `--format` | no | `text` | text, json | `value` | Output format. |
| `--target` | no | `—` | — | `value` | Repository path. |
| `--evaluation-id` | yes | `—` | — | `value` | — |
| `--sink-id` | no | `—` | — | `value` | — |

## `agentic-workspace evaluation transition`

validated lifecycle transition writes the local evaluation ledger

| Flags | Required | Default | Choices | Action / nargs | Description |
| --- | --- | --- | --- | --- | --- |
| `--format` | no | `text` | text, json | `value` | Output format. |
| `--target` | no | `—` | — | `value` | Repository path. |
| `--evaluation-id` | yes | `—` | — | `value` | — |
| `--lifecycle` | yes | `—` | collecting, enough-signal, satisfied, contradicted, inconclusive, paused, superseded, archived | `value` | — |
| `--expected-revision` | no | `—` | — | `value` | — |
| `--reason` | no | `—` | — | `value` | — |

## `agentic-workspace evaluation prune`

local evaluation observation retention compaction

| Flags | Required | Default | Choices | Action / nargs | Description |
| --- | --- | --- | --- | --- | --- |
| `--format` | no | `text` | text, json | `value` | Output format. |
| `--target` | no | `—` | — | `value` | Repository path. |
| `--evaluation-id` | yes | `—` | — | `value` | — |
| `--dry-run` | no | `no` | — | `store_true` | — |

## `agentic-workspace checkpoint`

local-only continuity helper for compressed or fresh sessions

| Flags | Required | Default | Choices | Action / nargs | Description |
| --- | --- | --- | --- | --- | --- |
| `--format` | no | `text` | text, json | `value` | Output format. |
| `--target` | no | `—` | — | `value` | Optional repository path. |

## `agentic-workspace checkpoint write`

ignored local checkpoint writer; not durable closure evidence

| Flags | Required | Default | Choices | Action / nargs | Description |
| --- | --- | --- | --- | --- | --- |
| `--format` | no | `text` | text, json | `value` | Output format. |
| `--target` | no | `—` | — | `value` | Optional repository path. |
| `--task` | no | `—` | — | `value` | Short current task summary. |
| `--issue` | no | `—` | — | `append` | Current issue reference, such as #1680. May be repeated. |
| `--pr` | no | `—` | — | `value` | Current pull request number or URL. |
| `--durable-source` | no | `—` | — | `append` | Durable source to reread on resume. May be repeated. |
| `--last-proof` | no | `—` | — | `append` | Proof command or receipt summary. May be repeated. |
| `--next-safe-command` | no | `—` | — | `value` | Next safe command to run after resume. |
| `--open-blocker` | no | `—` | — | `append` | Short blocker summary. May be repeated. |
| `--dirty-state-summary` | no | `—` | — | `value` | Short local dirty-state summary. |
| `--replace` | no | `—` | — | `store_true` | Replace mergeable list values instead of preserving existing checkpoint values. |

## `agentic-workspace final-response`

host final-response admission boundary

| Flags | Required | Default | Choices | Action / nargs | Description |
| --- | --- | --- | --- | --- | --- |
| `--format` | no | `text` | text, json | `value` | Output format. |
| `--target` | no | `—` | — | `value` | Optional repository path. |

## `agentic-workspace final-response admit`

host final-response admission and local continuation checkpointing

| Flags | Required | Default | Choices | Action / nargs | Description |
| --- | --- | --- | --- | --- | --- |
| `--format` | no | `text` | text, json | `value` | Output format. |
| `--target` | no | `—` | — | `value` | Optional repository path. |
| `--task` | no | `—` | — | `value` | Exact direct-work task identity used to reconcile bounded closeout proof. |
| `--changed` | no | `—` | — | `extend; nargs=*` | Repo-relative direct-work paths whose selected proof receipts must reconcile before bounded admission. |
| `--residue` | no | `—` | — | `value` | Structured direct-work residue kind: docs, issue, memory, planning, or review. |
| `--residue-owner` | no | `—` | — | `value` | Structured continuation owner for the still-open larger intent. |
| `--attempt` | no | `—` | — | `value` | The model-authored final response text submitted for host admission. |
| `--attempt-file` | no | `—` | — | `value` | Path to a file containing the model-authored final response text submitted for host admission. |
| `--executor-command` | no | `—` | — | `value` | Vendor-neutral command that emits the next model-authored final response attempt on stdout; rejected CONTINUE attempts re-enter the command with custody metadata. |
| `--source` | no | `model-authored-final-response` | — | `value` | Source label for the final response attempt. |
| `--after-compaction` | no | `—` | — | `store_true` | Mark that the attempt happened after a compaction or resume boundary. |

## `agentic-workspace autopilot`

ordinary autopilot execution boundary with conservative executor-mode effects

| Flags | Required | Default | Choices | Action / nargs | Description |
| --- | --- | --- | --- | --- | --- |
| `--format` | no | `text` | text, json | `value` | Output format. |
| `--target` | no | `—` | — | `value` | Optional repository path. |
| `--executor-command` | yes | `—` | — | `value` | Vendor-neutral command that emits the next model-authored final response attempt on stdout; rejected CONTINUE attempts re-enter the command with custody metadata. |
| `--source` | no | `autopilot-executor-stdout` | — | `value` | Source label for the executor final response attempt. |
| `--after-compaction` | no | `—` | — | `store_true` | Mark that the first attempt happened after a compaction or resume boundary. |

## `agentic-workspace work-thread`

local-only work-thread cleanup helper

| Flags | Required | Default | Choices | Action / nargs | Description |
| --- | --- | --- | --- | --- | --- |
| `--format` | no | `text` | text, json | `value` | Output format. |
| `--target` | no | `—` | — | `value` | Optional repository path. |

## `agentic-workspace work-thread select`

ignored local work-thread selection; not durable closure evidence

| Flags | Required | Default | Choices | Action / nargs | Description |
| --- | --- | --- | --- | --- | --- |
| `--format` | no | `text` | text, json | `value` | Output format. |
| `--thread-id` | no | `—` | — | `value` | Local work-thread id to select. |
| `--target` | no | `—` | — | `value` | Optional repository path. |

## `agentic-workspace work-thread carry-inspect`

read-only local carry ownership and lifecycle inspection

| Flags | Required | Default | Choices | Action / nargs | Description |
| --- | --- | --- | --- | --- | --- |
| `--format` | no | `text` | text, json | `value` | Output format. |
| `--target` | no | `—` | — | `value` | Optional repository path. |
| `--key` | no | `—` | — | `value` | Optional exact carry key to inspect. |

## `agentic-workspace work-thread carry-select`

exact ignored-local carry selection; not Planning owner selection

| Flags | Required | Default | Choices | Action / nargs | Description |
| --- | --- | --- | --- | --- | --- |
| `--format` | no | `text` | text, json | `value` | Output format. |
| `--target` | no | `—` | — | `value` | Optional repository path. |
| `--key` | yes | `—` | — | `value` | Exact active carry key to select. |

## `agentic-workspace work-thread carry-prune`

exact ignored-local carry lifecycle repair; never archives Planning

| Flags | Required | Default | Choices | Action / nargs | Description |
| --- | --- | --- | --- | --- | --- |
| `--format` | no | `text` | text, json | `value` | Output format. |
| `--target` | no | `—` | — | `value` | Optional repository path. |
| `--key` | yes | `—` | — | `value` | Exact selected carry key to mark stale. |
| `--expect-context-id` | yes | `—` | — | `value` | Optimistic current-work context id returned by carry-select. |
| `--reason` | yes | `—` | — | `value` | Concrete evidence that the selected carry is stale. |
| `--dry-run` | no | `—` | — | `store_true` | Report the exact mutation without changing the carry. |

## `agentic-workspace work-thread prune`

ignored local work-thread cleanup; not durable closure evidence

| Flags | Required | Default | Choices | Action / nargs | Description |
| --- | --- | --- | --- | --- | --- |
| `--format` | no | `text` | text, json | `value` | Output format. |
| `--target` | no | `—` | — | `value` | Optional repository path. |
| `--thread-id` | no | `—` | — | `append` | Local work-thread id to prune. May be repeated. |
| `--all-candidates` | no | `—` | — | `store_true` | Prune all current safe local work-thread candidates. |
| `--dry-run` | no | `—` | — | `store_true` | Report candidates without deleting local files. |

## `agentic-workspace session-log`

local-only session log helper; not durable proof

| Flags | Required | Default | Choices | Action / nargs | Description |
| --- | --- | --- | --- | --- | --- |
| `--format` | no | `text` | text, json | `value` | Output format. |
| `--target` | no | `—` | — | `value` | Optional repository path. |

## `agentic-workspace session-log status`

local-only session logging status; not durable proof

| Flags | Required | Default | Choices | Action / nargs | Description |
| --- | --- | --- | --- | --- | --- |
| `--format` | no | `text` | text, json | `value` | Output format. |
| `--target` | no | `—` | — | `value` | Optional repository path. |

## `agentic-workspace session-log new-session`

local-only session log rotation; not durable proof

| Flags | Required | Default | Choices | Action / nargs | Description |
| --- | --- | --- | --- | --- | --- |
| `--format` | no | `text` | text, json | `value` | Output format. |
| `--target` | no | `—` | — | `value` | Optional repository path. |

## `agentic-workspace session-log note`

local-only session log note; not durable proof

| Flags | Required | Default | Choices | Action / nargs | Description |
| --- | --- | --- | --- | --- | --- |
| `--format` | no | `text` | text, json | `value` | Output format. |
| `--target` | no | `—` | — | `value` | Optional repository path. |
| `--text` | yes | `—` | — | `value` | Note text to append. |

## `agentic-workspace session-log signal`

local-only improvement-signal observation; candidate evidence only and never mutation authority

| Flags | Required | Default | Choices | Action / nargs | Description |
| --- | --- | --- | --- | --- | --- |
| `--format` | no | `text` | text, json | `value` | Output format. |
| `--target` | no | `—` | — | `value` | Optional repository path. |
| `--kind` | no | `workaround` | workaround, opportunity | `value` | Observation class. |
| `--symptom` | yes | `—` | — | `value` | Observed workaround, friction, or concrete opportunity. |
| `--cost` | yes | `—` | — | `value` | Concrete current or future repository cost. |
| `--expected-benefit` | no | `—` | — | `value` | Expected future-cost or operability benefit; required for opportunities. |
| `--evidence-class` | no | `agent_observed` | agent_observed, machine_observed, human_confirmed, review_derived | `value` | Evidence provenance class. |
| `--owner-hint` | no | `unknown` | — | `value` | Suspected repository or AW owner. |
| `--scope-relation` | no | `current-scope` | current-scope, adjacent-scope, standalone-repo, aw-internal | `value` | Relation to the current task scope. |
| `--recurrence` | no | `first_seen` | first_seen, repeated, human_confirmed | `value` | Observed recurrence state. |
| `--evidence-ref` | no | `—` | — | `append` | Compact evidence reference; repeat for multiple references. |
| `--likely-remediation` | no | `unknown` | — | `value` | Likely existing remediation class. |

## `agentic-workspace session-log analyze`

local-only session log analysis; not durable proof

| Flags | Required | Default | Choices | Action / nargs | Description |
| --- | --- | --- | --- | --- | --- |
| `--format` | no | `text` | text, json | `value` | Output format. |
| `--target` | no | `—` | — | `value` | Optional repository path. |
| `--path` | no | `—` | — | `value` | Optional repo-relative session log path; defaults to the current session pointer. |
| `--id` | no | `—` | — | `value` | Optional session id or aw-session-<id> directory name to analyze. |
| `--segment` | no | `—` | — | `value` | Optional segment id to analyze; the response still lists all discovered segments. |
| `--origin` | no | `agent` | agent, all, test, synthetic, unknown | `value` | Origin scope for operational conclusions; defaults to live agent traffic. |

## `agentic-workspace session-log repair`

local-only idempotent session-log index repair; not durable proof

| Flags | Required | Default | Choices | Action / nargs | Description |
| --- | --- | --- | --- | --- | --- |
| `--format` | no | `text` | text, json | `value` | Output format. |
| `--target` | no | `—` | — | `value` | Optional repository path. |
| `--path` | no | `—` | — | `value` | Optional repo-relative session log path; defaults to the current session pointer. |
| `--id` | no | `—` | — | `value` | Optional session id or aw-session-<id> directory name to repair. |

## `agentic-workspace session-log export`

explicit local session log export; not durable proof

| Flags | Required | Default | Choices | Action / nargs | Description |
| --- | --- | --- | --- | --- | --- |
| `--format` | no | `text` | text, json | `value` | Output format. |
| `--target` | no | `—` | — | `value` | Optional repository path. |
| `--path` | no | `—` | — | `value` | Optional repo-relative session log path; defaults to the current session pointer. |
| `--id` | no | `—` | — | `value` | Optional session id or aw-session-<id> directory name to export. |
| `--no-artifacts` | no | `—` | — | `store_true` | Exclude raw-output artifacts from the exported bundle. |

## `agentic-workspace start`

ordinary first-contact startup context

| Flags | Required | Default | Choices | Action / nargs | Description |
| --- | --- | --- | --- | --- | --- |
| `--format` | no | `text` | text, json | `value` | Output format. |
| `--target` | no | `—` | — | `value` | Optional repository path for startup context (defaults to current workspace). |
| `--changed` | no | `—` | — | `extend; nargs=*` | Optional repo-relative changed paths used to include a proof recommendation. |
| `--task` | no | `—` | — | `value` | Optional task description used to include task-specific skill recommendations in startup context. |
| `--select` | no | `—` | — | `value` | Comma-separated startup fields to return, such as cli_invocation,durable_intent,skill_routing. |
| `--verbose` | no | `—` | — | `store_true` | Emit broad diagnostic startup output. Prefer --select for ordinary detail. |

## `agentic-workspace implement`

bounded implementer context over changed paths

| Flags | Required | Default | Choices | Action / nargs | Description |
| --- | --- | --- | --- | --- | --- |
| `--format` | no | `text` | text, json | `value` | Output format. |
| `--target` | no | `—` | — | `value` | Optional repository path for implementer context (defaults to current workspace). |
| `--changed` | no | `—` | — | `extend; nargs=*` | Repo-relative changed paths used to select inspect scope, boundary warnings, and proof commands. |
| `--task` | no | `—` | — | `value` | Optional task text used to route broad external-work requests before implementation. |
| `--task-file` | no | `—` | — | `value` | Optional repo-local file containing task text; use this instead of repeating long task prompts. |
| `--select` | no | `—` | — | `value` | Return only comma-separated top-level or dotted JSON fields from the implementer context. Prefer this when one or a few fields are needed. |
| `--verbose` | no | `—` | — | `store_true` | Emit full implementer context. Prefer the default output for ordinary bounded implementation. |

## `agentic-workspace defaults`

queryable default policy and routing contracts

| Flags | Required | Default | Choices | Action / nargs | Description |
| --- | --- | --- | --- | --- | --- |
| `--format` | no | `text` | text, json | `value` | Output format. |
| `--verbose` | no | `—` | — | `store_true` | Emit the complete default-route contract. Prefer --section or default output for ordinary lookup. |
| `--section` | no | `—` | — | `value` | Return only one top-level defaults section in the compact contract profile. |
| `--select` | no | `—` | — | `value` | Return only comma-separated top-level or dotted JSON fields from the defaults payload. Prefer this over --verbose when one or a few fields are needed. |

## `agentic-workspace proof`

changed-path proof routing, authority checks, and explicit proof receipt recording

| Flags | Required | Default | Choices | Action / nargs | Description |
| --- | --- | --- | --- | --- | --- |
| `--format` | no | `text` | text, json | `value` | Output format. |
| `--target` | no | `—` | — | `value` | Optional repository path used to inspect installed modules and proof state. |
| `--task` | no | `—` | — | `value` | Optional task description used to keep changed-path proof selection aligned with the active task context. |
| `--route` | no | `—` | — | `value` | Return one proof route by id instead of the full proof surface. |
| `--current` | no | `—` | — | `store_true` | Return only the current proof summary. |
| `--changed` | no | `—` | — | `extend; nargs=*` | Return required proof commands for the provided repo-relative changed paths. |
| `--execute-selected` | no | `—` | — | `store_true` | Execute and reconcile the currently selected changed-path proof set as one resumable operation. |
| `--proof-run-id` | no | `—` | — | `value` | Optional existing proof run identity to resume; stale subject identities fail closed. |
| `--proof-timeout-seconds` | no | `600` | — | `value` | Per-command timeout budget for selected proof execution. |
| `--proof-cancel-file` | no | `—` | — | `value` | Optional cancellation sentinel checked before each selected proof command. |
| `--record-receipt` | no | `—` | — | `store_true` | Record a compact proof receipt from an actually run validation command. |
| `--receipt-command` | no | `—` | — | `value` | Validation command or evidence to store in the proof receipt. |
| `--receipt-result` | no | `—` | — | `value` | Validation result to store in the proof receipt, such as passed or failed. |
| `--receipt-plan` | no | `—` | — | `value` | Optional planning id that the proof receipt applies to. |
| `--receipt-log` | no | `—` | — | `value` | Optional repo-local log path or short excerpt used to attach a compact failed-proof summary. |
| `--receipt-route-id` | no | `—` | — | `value` | Structured proof route identity for the executed receipt. |
| `--receipt-command-id` | no | `—` | — | `value` | Structured command identity for the executed receipt. |
| `--receipt-duration-seconds` | no | `—` | — | `value` | Seconds-normalized execution duration for the receipt. |
| `--receipt-timeout` | no | `—` | — | `store_true` | Record that the validation execution timed out. |
| `--receipt-exit-state` | no | `—` | — | `value` | Structured exit state for the validation execution. |
| `--receipt-environment` | no | `—` | — | `value` | JSON object describing the execution environment or resource posture. |
| `--receipt-claim-sufficiency` | no | `—` | — | `value` | Independent claim sufficiency review: sufficient, insufficient, or not-reviewed. |
| `--receipt-route-budget-seconds` | no | `—` | — | `value` | Route-specific duration budget in seconds, when declared by route authority. |
| `--receipt-repair-finding-id` | no | `—` | — | `value` | Stable proof-route finding id retired by this validation receipt. |
| `--receipt-repair-authority-revision` | no | `—` | — | `value` | Verified proof-route authority revision after applying the repair. |
| `--receipt-repair-disposition` | no | `—` | — | `value` | Disposition for the repaired proof-route finding. |
| `--receipt-repair-idempotency-key` | no | `—` | — | `value` | Idempotency key from the proof-route repair operation. |
| `--route-repair-mode` | no | `—` | — | `value` | Preview or apply a guarded proof-route authority repair. |
| `--route-repair-finding-id` | no | `—` | — | `value` | Stable proof-route finding id being repaired. |
| `--route-repair-authority-path` | no | `—` | — | `value` | Single repo-relative authority path to update. |
| `--route-repair-field-selector` | no | `—` | — | `value` | Single authority field selector scoped by the repair. |
| `--route-repair-expected-revision` | no | `—` | — | `value` | Expected proof-route authority revision before apply. |
| `--route-repair-delta-json` | no | `—` | — | `value` | Machine-readable field-scoped repair delta JSON. |
| `--route-repair-disposition` | no | `—` | — | `value` | Disposition to associate with the repaired finding. |
| `--route-repair-idempotency-key` | no | `—` | — | `value` | Idempotency key for the guarded proof-route repair apply. |
| `--dry-run` | no | `—` | — | `store_true` | Show the receipt payload without writing it. |
| `--select` | no | `—` | — | `value` | Return exact comma-separated field paths from the proof answer. |
| `--verbose` | no | `—` | — | `store_true` | Emit all proof routing detail. Prefer the default changed-path proof answer for ordinary validation. |

## `agentic-workspace setup`

post-bootstrap setup findings and guidance

| Flags | Required | Default | Choices | Action / nargs | Description |
| --- | --- | --- | --- | --- | --- |
| `--format` | no | `text` | text, json | `value` | Output format. |
| `--target` | no | `—` | — | `value` | Target repository path. Defaults to the current directory. |
| `--modules` | no | `—` | — | `value` | Comma-separated module selection, or 'none'. |
| `--non-interactive` | no | `—` | — | `store_true` | Require prompt-free lifecycle behavior and handoff guidance suitable for unattended agents. |

## `agentic-workspace ownership`

ownership and authority routing

| Flags | Required | Default | Choices | Action / nargs | Description |
| --- | --- | --- | --- | --- | --- |
| `--format` | no | `text` | text, json | `value` | Output format. |
| `--target` | no | `—` | — | `value` | Optional repository path used to inspect the ownership ledger. |
| `--concern` | no | `—` | — | `value` | Return one authority-surface answer by concern. |
| `--path` | no | `—` | — | `value` | Return the ownership answer for one repo-relative path. |

## `agentic-workspace config`

resolved repo and local configuration posture

| Flags | Required | Default | Choices | Action / nargs | Description |
| --- | --- | --- | --- | --- | --- |
| `--format` | no | `text` | text, json | `value` | Output format. |
| `--target` | no | `—` | — | `value` | Optional repository path used to resolve repo-owned config. |
| `--select` | no | `—` | — | `value` | Return only comma-separated top-level or dotted JSON fields from the full command payload. Prefer this over --verbose when one or a few fields are needed. |
| `--verbose` | no | `—` | — | `store_true` | Emit full resolved config detail. Prefer default output or targeted fields for ordinary posture checks. |

## `agentic-workspace config-policy`

revision-bound application of an authorised bounded workspace policy decision

| Flags | Required | Default | Choices | Action / nargs | Description |
| --- | --- | --- | --- | --- | --- |
| `--format` | no | `text` | text, json | `value` | Output format. |
| `--target` | no | `—` | — | `value` | Optional repository path containing the owned config surface. |
| `--decision-json` | yes | `—` | — | `value` | Authorised agentic-workspace/config-policy-decision/v1 JSON object. |
| `--expect-config-revision` | yes | `—` | — | `value` | Exact sha256 revision reported for the selected shared or local config surface. |
| `--expect-setup-identity` | yes | `—` | — | `value` | Exact setup readiness identity against which the decision was made. |
| `--dry-run` | no | `—` | — | `store_true` | Validate and preview the bounded policy effects without writing. |

## `agentic-workspace system-intent`

compiled system-intent declaration and sync route

| Flags | Required | Default | Choices | Action / nargs | Description |
| --- | --- | --- | --- | --- | --- |
| `--format` | no | `text` | text, json | `value` | Output format. |
| `--target` | no | `—` | — | `value` | Optional repository path used to inspect system intent. |
| `--sync` | no | `—` | — | `store_true` | Refresh source discovery metadata and create the compiled system-intent declaration if it is missing. |

## `agentic-workspace note-delegation-outcome`

local-only delegation calibration record

| Flags | Required | Default | Choices | Action / nargs | Description |
| --- | --- | --- | --- | --- | --- |
| `--format` | no | `text` | text, json | `value` | Output format. |
| `--target` | no | `—` | — | `value` | Optional repository path used to record the local outcome. |
| `--delegation-target` | yes | `—` | — | `value` | Local delegation target alias. |
| `--task-class` | yes | `—` | — | `value` | Bounded task class label for this delegated run. |
| `--scope-class` | yes | `—` | — | `value` | Independent bounded scope class for this delegated run. |
| `--operation` | no | `submit` | submit, correct-or-dispute, supersede, prune-or-compact | `value` | Evidence lifecycle operation. |
| `--predecessor-id` | no | `—` | — | `value` | Existing record id required for lifecycle transition operations. |
| `--authority` | no | `local-outcome-ledger` | — | `value` | Authority class for the admitted evidence. |
| `--confidence` | no | `medium` | low, medium, high | `value` | Confidence classification for the admitted evidence. |
| `--context-cost-json` | no | `—` | — | `value` | Provider-neutral assignment context-cost observation encoded as JSON. |
| `--outcome` | yes | `—` | SUPPORTED_DELEGATION_OUTCOMES | `value` | High-level delegated execution outcome. |
| `--handoff-sufficiency` | no | `sufficient` | SUPPORTED_HANDOFF_SUFFICIENCY | `value` | Whether the checked-in handoff was enough for the delegated worker. |
| `--review-burden` | no | `normal` | SUPPORTED_REVIEW_BURDENS | `value` | How much review/rework burden remained after delegation. |
| `--escalation-required` | no | `—` | — | `store_true` | Record that the delegated run had to stop and escalate. |

## `agentic-workspace skills`

registered package and repo skill routing

| Flags | Required | Default | Choices | Action / nargs | Description |
| --- | --- | --- | --- | --- | --- |
| `--format` | no | `text` | text, json | `value` | Output format. |
| `--target` | no | `—` | — | `value` | Optional repository path used to inspect installed and repo-owned skills. |
| `--task` | no | `—` | — | `value` | Optional task description used to recommend likely skills. |
| `--select` | no | `—` | — | `value` | Comma-separated JSON fields to return, such as recommendations,warnings or top_recommendations,warnings. |

## `agentic-workspace report`

combined compact workspace router and selected diagnostics

| Flags | Required | Default | Choices | Action / nargs | Description |
| --- | --- | --- | --- | --- | --- |
| `--format` | no | `text` | text, json | `value` | Output format. |
| `--target` | no | `—` | — | `value` | Target repository path. Defaults to the current directory. |
| `--modules` | no | `—` | — | `value` | Comma-separated module selection, or 'none'. |
| `--non-interactive` | no | `—` | — | `store_true` | Require prompt-free lifecycle behavior and handoff guidance suitable for unattended agents. |
| `--startup` | no | `—` | — | `store_true` | Return the high-signal orientation block for fresh agents. |
| `--verbose` | no | `—` | — | `store_true` | Emit the full combined workspace report. Prefer default router output or --section for ordinary inspection. |
| `--section` | no | `—` | — | `value` | Return one top-level full-report section in the compact contract profile. |
| `--changed` | no | `—` | — | `extend; nargs=*` | Optional repo-relative changed paths used by task-scoped report sections such as closeout_trust. |
| `--task` | no | `—` | — | `value` | Optional task description used by task-scoped report sections such as closeout_trust. |
| `--select` | no | `—` | — | `value` | Comma-separated JSON fields to return from the selected report payload, such as answer.closeout_protocol. |
| `--fail-on` | no | `—` | strict-current | `value` | Assert the named versioned health policy and exit non-zero when current state violates it. |

## `agentic-workspace reconcile`

provider-agnostic external-work reconciliation

| Flags | Required | Default | Choices | Action / nargs | Description |
| --- | --- | --- | --- | --- | --- |
| `--format` | no | `text` | text, json | `value` | Output format. |
| `--target` | no | `—` | — | `value` | Optional repository path used to reconcile planning state. |
| `--apply-safe-prune` | no | `—` | — | `store_true` | Apply only reconcile cleanup targets that are already marked safe_to_prune. |
| `--dry-run` | no | `—` | — | `store_true` | Preview --apply-safe-prune without writing files. |

## `agentic-workspace external-evidence-submit`

provider-neutral external proof submission through package-trusted host custody

| Flags | Required | Default | Choices | Action / nargs | Description |
| --- | --- | --- | --- | --- | --- |
| `--format` | no | `text` | text, json | `value` | Output format. |
| `--target` | no | `—` | — | `value` | Repository path. |
| `--candidate-json` | yes | `—` | — | `value` | Provider-neutral external evidence candidate JSON. |
| `--host-result-ref` | yes | `—` | — | `value` | Opaque package-trusted host result reference. |

## `agentic-workspace external-evidence-query`

provider-neutral current external proof query

| Flags | Required | Default | Choices | Action / nargs | Description |
| --- | --- | --- | --- | --- | --- |
| `--format` | no | `text` | text, json | `value` | Output format. |
| `--target` | no | `—` | — | `value` | Repository path. |
| `--candidate-json` | yes | `—` | — | `value` | Provider-neutral external evidence candidate JSON. |
| `--host-result-ref` | yes | `—` | — | `value` | Opaque package-trusted host result reference. |

## `agentic-workspace external-intent`

optional external evidence adapter front door

| Flags | Required | Default | Choices | Action / nargs | Description |
| --- | --- | --- | --- | --- | --- |
| — | — | — | — | — | No declared options. |

## `agentic-workspace external-intent refresh-github`

optional GitHub adapter for provider-agnostic external evidence

| Flags | Required | Default | Choices | Action / nargs | Description |
| --- | --- | --- | --- | --- | --- |
| `--format` | no | `text` | text, json | `value` | Output format. |
| `--target` | no | `—` | — | `value` | Optional repository path whose external intent evidence should be refreshed. |
| `--repo` | no | `—` | — | `value` | GitHub repository in owner/name form. Defaults to the gh repository for the target. |
| `--state` | no | `—` | open, closed, all | `value` | GitHub issue state to import. Defaults to open; closed or all are explicit audit scopes. |
| `--issue` | no | `—` | — | `append` | Specific GitHub issue number or reference to import via gh issue view. May be repeated. |
| `--limit` | no | `—` | — | `value` | Maximum number of GitHub issues to import. Defaults to 1000. |
| `--storage` | no | `cache` | cache, planning | `value` | Where to write refreshed evidence. Defaults to ignored local cache; planning writes the legacy planning evidence path explicitly. |
| `--dry-run` | no | `—` | — | `store_true` | Preview refresh counts without writing external intent evidence. |
| `--verbose` | no | `—` | — | `store_true` | Include candidate, grouping, cache, and reconciliation detail for an issue-scoped refresh. |

## `agentic-workspace preflight`

takeover-safe compact startup plus active state

| Flags | Required | Default | Choices | Action / nargs | Description |
| --- | --- | --- | --- | --- | --- |
| `--format` | no | `text` | text, json | `value` | Output format. |
| `--target` | no | `—` | — | `value` | Optional repository path for preflight context (defaults to current workspace). |
| `--active-only` | no | `—` | — | `store_true` | Return only active planning state without startup defaults and config. |
| `--task` | no | `—` | — | `value` | Optional task description used to include task-specific skill recommendations in preflight context. |
| `--verbose` | no | `—` | — | `store_true` | Emit complete takeover/recovery context. Prefer default output for ordinary recovery routing. |

## `agentic-workspace install`

module install lifecycle mutation

| Flags | Required | Default | Choices | Action / nargs | Description |
| --- | --- | --- | --- | --- | --- |
| `--format` | no | `text` | text, json | `value` | Output format. |
| `--target` | no | `—` | — | `value` | Target repository path. Defaults to the current directory. |
| `--modules` | no | `—` | — | `value` | Comma-separated module selection, or 'none'. |
| `--non-interactive` | no | `—` | — | `store_true` | Require prompt-free lifecycle behavior and handoff guidance suitable for unattended agents. |
| `--strict-preflight` | no | `—` | — | `store_true` | Require a fresh --preflight-token before running high-risk mutating commands. |
| `--preflight-token` | no | `—` | — | `value` | Token emitted by 'agentic-workspace preflight --format json'. |
| `--preflight-max-age-seconds` | no | `preflight_policy.default_max_age_seconds` | — | `value` | Maximum token age when --strict-preflight is enabled (default: {default}). |
| `--local-only` | no | `—` | — | `store_true` | Install in the normal repository layout while recording `.agentic-workspace/` in git-local exclude metadata. |
| `--agent-instructions-file` | no | `—` | — | `value` | Canonical startup instructions filename to use for this repo (for example AGENTS.md or GEMINI.md). |
| `--adopt` | no | `—` | — | `store_true` | Force conservative adopt behavior. |
| `--mirror-payload` | no | `—` | — | `store_true` | Opt in to checking in the full generic package payload mirror instead of the ordinary necessary-surface footprint. |
| `--verbose` | no | `—` | — | `store_true` | Show the full lifecycle, module, configuration, and provenance payload instead of the ordinary decision envelope. |
| `--dry-run` | no | `—` | — | `store_true` | Show planned changes without mutating files. |
| `--print-prompt` | no | `—` | — | `store_true` | Print the generated handoff prompt. |
| `--write-prompt` | no | `—` | — | `value` | Write the generated handoff prompt to a file. |

## `agentic-workspace init`

conservative bootstrap/adopt lifecycle mutation

| Flags | Required | Default | Choices | Action / nargs | Description |
| --- | --- | --- | --- | --- | --- |
| `--format` | no | `text` | text, json | `value` | Output format. |
| `--target` | no | `—` | — | `value` | Target repository path. Defaults to the current directory. |
| `--modules` | no | `—` | — | `value` | Comma-separated module selection, or 'none'. |
| `--non-interactive` | no | `—` | — | `store_true` | Require prompt-free lifecycle behavior and handoff guidance suitable for unattended agents. |
| `--strict-preflight` | no | `—` | — | `store_true` | Require a fresh --preflight-token before running high-risk mutating commands. |
| `--preflight-token` | no | `—` | — | `value` | Token emitted by 'agentic-workspace preflight --format json'. |
| `--preflight-max-age-seconds` | no | `preflight_policy.default_max_age_seconds` | — | `value` | Maximum token age when --strict-preflight is enabled (default: {default}). |
| `--local-only` | no | `—` | — | `store_true` | Install in the normal repository layout while recording `.agentic-workspace/` in git-local exclude metadata. |
| `--agent-instructions-file` | no | `—` | — | `value` | Canonical startup instructions filename to use for this repo (for example AGENTS.md or GEMINI.md). |
| `--adopt` | no | `—` | — | `store_true` | Force conservative adopt behavior. |
| `--mirror-payload` | no | `—` | — | `store_true` | Opt in to checking in the full generic package payload mirror instead of the ordinary necessary-surface footprint. |
| `--verbose` | no | `—` | — | `store_true` | Show the full lifecycle, module, configuration, and provenance payload instead of the ordinary decision envelope. |
| `--dry-run` | no | `—` | — | `store_true` | Show planned changes without mutating files. |
| `--print-prompt` | no | `—` | — | `store_true` | Print the generated handoff prompt. |
| `--write-prompt` | no | `—` | — | `value` | Write the generated handoff prompt to a file. |

## `agentic-workspace prompt`

lifecycle handoff prompt renderer

| Flags | Required | Default | Choices | Action / nargs | Description |
| --- | --- | --- | --- | --- | --- |
| — | — | — | — | — | No declared options. |

## `agentic-workspace prompt init`

bootstrap handoff prompt renderer

| Flags | Required | Default | Choices | Action / nargs | Description |
| --- | --- | --- | --- | --- | --- |
| `--format` | no | `text` | text, json | `value` | Output format. |
| `--target` | no | `—` | — | `value` | Target repository path. Defaults to the current directory. |
| `--modules` | no | `—` | — | `value` | Comma-separated module selection, or 'none'. |
| `--non-interactive` | no | `—` | — | `store_true` | Require prompt-free lifecycle behavior and handoff guidance suitable for unattended agents. |
| `--agent-instructions-file` | no | `—` | — | `value` | Canonical startup instructions filename to use for this repo (for example AGENTS.md or GEMINI.md). |
| `--adopt` | no | `—` | — | `store_true` | Force conservative adopt behavior. |

## `agentic-workspace prompt upgrade`

upgrade handoff prompt renderer

| Flags | Required | Default | Choices | Action / nargs | Description |
| --- | --- | --- | --- | --- | --- |
| `--format` | no | `text` | text, json | `value` | Output format. |
| `--target` | no | `—` | — | `value` | Target repository path. Defaults to the current directory. |
| `--modules` | no | `—` | — | `value` | Comma-separated module selection, or 'none'. |
| `--non-interactive` | no | `—` | — | `store_true` | Require prompt-free lifecycle behavior and handoff guidance suitable for unattended agents. |

## `agentic-workspace prompt uninstall`

uninstall handoff prompt renderer

| Flags | Required | Default | Choices | Action / nargs | Description |
| --- | --- | --- | --- | --- | --- |
| `--format` | no | `text` | text, json | `value` | Output format. |
| `--target` | no | `—` | — | `value` | Target repository path. Defaults to the current directory. |
| `--modules` | no | `—` | — | `value` | Comma-separated module selection, or 'none'. |
| `--non-interactive` | no | `—` | — | `store_true` | Require prompt-free lifecycle behavior and handoff guidance suitable for unattended agents. |

## `agentic-workspace status`

read-only lifecycle health drill-down for explicit lifecycle or remediation checks

| Flags | Required | Default | Choices | Action / nargs | Description |
| --- | --- | --- | --- | --- | --- |
| `--format` | no | `text` | text, json | `value` | Output format. |
| `--target` | no | `—` | — | `value` | Target repository path. Defaults to the current directory. |
| `--modules` | no | `—` | — | `value` | Comma-separated module selection, or 'none'. |
| `--non-interactive` | no | `—` | — | `store_true` | Require prompt-free lifecycle behavior and handoff guidance suitable for unattended agents. |
| `--verbose` | no | `—` | — | `store_true` | Emit all module lifecycle status detail. Prefer default output for ordinary health routing. |
| `--select` | no | `—` | — | `value` | Return only comma-separated top-level or dotted JSON fields from the full command payload. Prefer this over --verbose when one or a few fields are needed. |

## `agentic-workspace doctor`

read-only recovery diagnostic drill-down; not an ordinary first-contact route

| Flags | Required | Default | Choices | Action / nargs | Description |
| --- | --- | --- | --- | --- | --- |
| `--format` | no | `text` | text, json | `value` | Output format. |
| `--target` | no | `—` | — | `value` | Target repository path. Defaults to the current directory. |
| `--modules` | no | `—` | — | `value` | Comma-separated module selection, or 'none'. |
| `--non-interactive` | no | `—` | — | `store_true` | Require prompt-free lifecycle behavior and handoff guidance suitable for unattended agents. |
| `--verbose` | no | `—` | — | `store_true` | Emit all diagnostic detail. Prefer default output for ordinary remediation routing. |
| `--select` | no | `—` | — | `value` | Return only comma-separated top-level or dotted JSON fields from the full command payload. Prefer this over --verbose when one or a few fields are needed. |

## `agentic-workspace upgrade`

module upgrade lifecycle mutation

| Flags | Required | Default | Choices | Action / nargs | Description |
| --- | --- | --- | --- | --- | --- |
| `--format` | no | `text` | text, json | `value` | Output format. |
| `--target` | no | `—` | — | `value` | Target repository path. Defaults to the current directory. |
| `--modules` | no | `—` | — | `value` | Comma-separated module selection, or 'none'. |
| `--non-interactive` | no | `—` | — | `store_true` | Require prompt-free lifecycle behavior and handoff guidance suitable for unattended agents. |
| `--strict-preflight` | no | `—` | — | `store_true` | Require a fresh --preflight-token before running high-risk mutating commands. |
| `--preflight-token` | no | `—` | — | `value` | Token emitted by 'agentic-workspace preflight --format json'. |
| `--preflight-max-age-seconds` | no | `preflight_policy.default_max_age_seconds` | — | `value` | Maximum token age when --strict-preflight is enabled (default: {default}). |
| `--verbose` | no | `—` | — | `store_true` | Emit full lifecycle and per-file detail. The default upgrade output is compact and decision-first. |
| `--select` | no | `—` | — | `value` | Return selected fields from the full upgrade payload. |
| `--dry-run` | no | `—` | — | `store_true` | Show planned changes without mutating files. |
| `--legacy-scratch-cleanup` | no | `—` | — | `store_true` | Run the explicit legacy AW local scratch cleanup route. Defaults to dry-run unless --apply-legacy-scratch-cleanup is also set. |
| `--apply-legacy-scratch-cleanup` | no | `—` | — | `store_true` | Apply the explicit legacy AW local scratch cleanup after reviewing the dry-run output. |
| `--repair-managed-local-instructions` | no | `—` | — | `store_true` | Refresh only the workspace-managed .agentic-workspace local agent instructions file. |
| `--repair-root-startup-pointer` | no | `—` | — | `store_true` | Patch only the managed workflow pointer fence in the configured root startup file. |
| `--adopt-local-only` | no | `—` | — | `store_true` | Transition a local-only Agentic Workspace install to checked-in mode while preserving durable AW state. |
| `--to-payload-target` | no | `—` | — | `store_true` | Read [payload] from repo config and sync managed payload/provenance to the declared target. |
| `--to-necessary-surfaces` | no | `—` | — | `store_true` | Migrate legacy checked-in AW package payload to necessary repo surfaces while preserving durable Planning, Memory, and Verification state. |

## `agentic-workspace uninstall`

conservative lifecycle removal mutation

| Flags | Required | Default | Choices | Action / nargs | Description |
| --- | --- | --- | --- | --- | --- |
| `--format` | no | `text` | text, json | `value` | Output format. |
| `--target` | no | `—` | — | `value` | Target repository path. Defaults to the current directory. |
| `--modules` | no | `—` | — | `value` | Comma-separated module selection, or 'none'. |
| `--non-interactive` | no | `—` | — | `store_true` | Require prompt-free lifecycle behavior and handoff guidance suitable for unattended agents. |
| `--strict-preflight` | no | `—` | — | `store_true` | Require a fresh --preflight-token before running high-risk mutating commands. |
| `--preflight-token` | no | `—` | — | `value` | Token emitted by 'agentic-workspace preflight --format json'. |
| `--preflight-max-age-seconds` | no | `preflight_policy.default_max_age_seconds` | — | `value` | Maximum token age when --strict-preflight is enabled (default: {default}). |
| `--dry-run` | no | `—` | — | `store_true` | Show planned changes without mutating files. |
| `--local-only` | no | `—` | — | `store_true` | Remove the local-only workspace state from the normal repository layout. |

## `agentic-workspace agent-guidance`

local agent guidance lifecycle operation front door

| Flags | Required | Default | Choices | Action / nargs | Description |
| --- | --- | --- | --- | --- | --- |
| — | — | — | — | — | No declared options. |

## `agentic-workspace agent-guidance promote`

agent guidance lifecycle subcommand

| Flags | Required | Default | Choices | Action / nargs | Description |
| --- | --- | --- | --- | --- | --- |
| `--format` | no | `text` | text, json | `value` | Output format. |
| `--target` | no | `—` | — | `value` | Target repository path. Defaults to current directory. |
| `--guidance-id` | no | `—` | — | `value` | Guidance lifecycle record id. |
| `--expected-revision` | no | `—` | — | `value` | Expected current record revision for transition operations. |
| `--expected-record-revisions-json` | no | `—` | — | `value` | JSON object of related guidance ids to expected revisions. |
| `--reason` | no | `—` | — | `value` | Human-readable lifecycle transition reason. |
| `--instruction` | no | `—` | — | `value` | Replacement instruction for edit operations. |
| `--replacement-guidance-id` | no | `—` | — | `value` | Replacement guidance id for supersede operations. |
| `--merge-guidance-id` | no | `—` | — | `append` | Guidance id to merge into the selected record. Repeat for multiple ids. |
| `--split-instruction` | no | `—` | — | `append` | Replacement instruction for split operations. Repeat at least twice. |
| `--task-class` | no | `—` | — | `value` | Promotion task class filter. |
| `--scope-class` | no | `—` | — | `value` | Promotion scope class filter. |
| `--explicit-remember` | no | `—` | — | `store_true` | Request immediate remember promotion; ignored without a trusted remember receipt. |
| `--dry-run` | no | `—` | — | `store_true` | Report without mutation. |

## `agentic-workspace agent-guidance edit`

agent guidance lifecycle subcommand

| Flags | Required | Default | Choices | Action / nargs | Description |
| --- | --- | --- | --- | --- | --- |
| `--format` | no | `text` | text, json | `value` | Output format. |
| `--target` | no | `—` | — | `value` | Target repository path. Defaults to current directory. |
| `--guidance-id` | no | `—` | — | `value` | Guidance lifecycle record id. |
| `--expected-revision` | no | `—` | — | `value` | Expected current record revision for transition operations. |
| `--expected-record-revisions-json` | no | `—` | — | `value` | JSON object of related guidance ids to expected revisions. |
| `--reason` | no | `—` | — | `value` | Human-readable lifecycle transition reason. |
| `--instruction` | no | `—` | — | `value` | Replacement instruction for edit operations. |
| `--replacement-guidance-id` | no | `—` | — | `value` | Replacement guidance id for supersede operations. |
| `--merge-guidance-id` | no | `—` | — | `append` | Guidance id to merge into the selected record. Repeat for multiple ids. |
| `--split-instruction` | no | `—` | — | `append` | Replacement instruction for split operations. Repeat at least twice. |
| `--task-class` | no | `—` | — | `value` | Promotion task class filter. |
| `--scope-class` | no | `—` | — | `value` | Promotion scope class filter. |
| `--explicit-remember` | no | `—` | — | `store_true` | Request immediate remember promotion; ignored without a trusted remember receipt. |
| `--dry-run` | no | `—` | — | `store_true` | Report without mutation. |

## `agentic-workspace agent-guidance merge`

agent guidance lifecycle subcommand

| Flags | Required | Default | Choices | Action / nargs | Description |
| --- | --- | --- | --- | --- | --- |
| `--format` | no | `text` | text, json | `value` | Output format. |
| `--target` | no | `—` | — | `value` | Target repository path. Defaults to current directory. |
| `--guidance-id` | no | `—` | — | `value` | Guidance lifecycle record id. |
| `--expected-revision` | no | `—` | — | `value` | Expected current record revision for transition operations. |
| `--expected-record-revisions-json` | no | `—` | — | `value` | JSON object of related guidance ids to expected revisions. |
| `--reason` | no | `—` | — | `value` | Human-readable lifecycle transition reason. |
| `--instruction` | no | `—` | — | `value` | Replacement instruction for edit operations. |
| `--replacement-guidance-id` | no | `—` | — | `value` | Replacement guidance id for supersede operations. |
| `--merge-guidance-id` | no | `—` | — | `append` | Guidance id to merge into the selected record. Repeat for multiple ids. |
| `--split-instruction` | no | `—` | — | `append` | Replacement instruction for split operations. Repeat at least twice. |
| `--task-class` | no | `—` | — | `value` | Promotion task class filter. |
| `--scope-class` | no | `—` | — | `value` | Promotion scope class filter. |
| `--explicit-remember` | no | `—` | — | `store_true` | Request immediate remember promotion; ignored without a trusted remember receipt. |
| `--dry-run` | no | `—` | — | `store_true` | Report without mutation. |

## `agentic-workspace agent-guidance split`

agent guidance lifecycle subcommand

| Flags | Required | Default | Choices | Action / nargs | Description |
| --- | --- | --- | --- | --- | --- |
| `--format` | no | `text` | text, json | `value` | Output format. |
| `--target` | no | `—` | — | `value` | Target repository path. Defaults to current directory. |
| `--guidance-id` | no | `—` | — | `value` | Guidance lifecycle record id. |
| `--expected-revision` | no | `—` | — | `value` | Expected current record revision for transition operations. |
| `--expected-record-revisions-json` | no | `—` | — | `value` | JSON object of related guidance ids to expected revisions. |
| `--reason` | no | `—` | — | `value` | Human-readable lifecycle transition reason. |
| `--instruction` | no | `—` | — | `value` | Replacement instruction for edit operations. |
| `--replacement-guidance-id` | no | `—` | — | `value` | Replacement guidance id for supersede operations. |
| `--merge-guidance-id` | no | `—` | — | `append` | Guidance id to merge into the selected record. Repeat for multiple ids. |
| `--split-instruction` | no | `—` | — | `append` | Replacement instruction for split operations. Repeat at least twice. |
| `--task-class` | no | `—` | — | `value` | Promotion task class filter. |
| `--scope-class` | no | `—` | — | `value` | Promotion scope class filter. |
| `--explicit-remember` | no | `—` | — | `store_true` | Request immediate remember promotion; ignored without a trusted remember receipt. |
| `--dry-run` | no | `—` | — | `store_true` | Report without mutation. |

## `agentic-workspace agent-guidance suppress`

agent guidance lifecycle subcommand

| Flags | Required | Default | Choices | Action / nargs | Description |
| --- | --- | --- | --- | --- | --- |
| `--format` | no | `text` | text, json | `value` | Output format. |
| `--target` | no | `—` | — | `value` | Target repository path. Defaults to current directory. |
| `--guidance-id` | no | `—` | — | `value` | Guidance lifecycle record id. |
| `--expected-revision` | no | `—` | — | `value` | Expected current record revision for transition operations. |
| `--expected-record-revisions-json` | no | `—` | — | `value` | JSON object of related guidance ids to expected revisions. |
| `--reason` | no | `—` | — | `value` | Human-readable lifecycle transition reason. |
| `--instruction` | no | `—` | — | `value` | Replacement instruction for edit operations. |
| `--replacement-guidance-id` | no | `—` | — | `value` | Replacement guidance id for supersede operations. |
| `--merge-guidance-id` | no | `—` | — | `append` | Guidance id to merge into the selected record. Repeat for multiple ids. |
| `--split-instruction` | no | `—` | — | `append` | Replacement instruction for split operations. Repeat at least twice. |
| `--task-class` | no | `—` | — | `value` | Promotion task class filter. |
| `--scope-class` | no | `—` | — | `value` | Promotion scope class filter. |
| `--explicit-remember` | no | `—` | — | `store_true` | Request immediate remember promotion; ignored without a trusted remember receipt. |
| `--dry-run` | no | `—` | — | `store_true` | Report without mutation. |

## `agentic-workspace agent-guidance revalidate`

agent guidance lifecycle subcommand

| Flags | Required | Default | Choices | Action / nargs | Description |
| --- | --- | --- | --- | --- | --- |
| `--format` | no | `text` | text, json | `value` | Output format. |
| `--target` | no | `—` | — | `value` | Target repository path. Defaults to current directory. |
| `--guidance-id` | no | `—` | — | `value` | Guidance lifecycle record id. |
| `--expected-revision` | no | `—` | — | `value` | Expected current record revision for transition operations. |
| `--expected-record-revisions-json` | no | `—` | — | `value` | JSON object of related guidance ids to expected revisions. |
| `--reason` | no | `—` | — | `value` | Human-readable lifecycle transition reason. |
| `--instruction` | no | `—` | — | `value` | Replacement instruction for edit operations. |
| `--replacement-guidance-id` | no | `—` | — | `value` | Replacement guidance id for supersede operations. |
| `--merge-guidance-id` | no | `—` | — | `append` | Guidance id to merge into the selected record. Repeat for multiple ids. |
| `--split-instruction` | no | `—` | — | `append` | Replacement instruction for split operations. Repeat at least twice. |
| `--task-class` | no | `—` | — | `value` | Promotion task class filter. |
| `--scope-class` | no | `—` | — | `value` | Promotion scope class filter. |
| `--explicit-remember` | no | `—` | — | `store_true` | Request immediate remember promotion; ignored without a trusted remember receipt. |
| `--dry-run` | no | `—` | — | `store_true` | Report without mutation. |

## `agentic-workspace agent-guidance weaken`

agent guidance lifecycle subcommand

| Flags | Required | Default | Choices | Action / nargs | Description |
| --- | --- | --- | --- | --- | --- |
| `--format` | no | `text` | text, json | `value` | Output format. |
| `--target` | no | `—` | — | `value` | Target repository path. Defaults to current directory. |
| `--guidance-id` | no | `—` | — | `value` | Guidance lifecycle record id. |
| `--expected-revision` | no | `—` | — | `value` | Expected current record revision for transition operations. |
| `--expected-record-revisions-json` | no | `—` | — | `value` | JSON object of related guidance ids to expected revisions. |
| `--reason` | no | `—` | — | `value` | Human-readable lifecycle transition reason. |
| `--instruction` | no | `—` | — | `value` | Replacement instruction for edit operations. |
| `--replacement-guidance-id` | no | `—` | — | `value` | Replacement guidance id for supersede operations. |
| `--merge-guidance-id` | no | `—` | — | `append` | Guidance id to merge into the selected record. Repeat for multiple ids. |
| `--split-instruction` | no | `—` | — | `append` | Replacement instruction for split operations. Repeat at least twice. |
| `--task-class` | no | `—` | — | `value` | Promotion task class filter. |
| `--scope-class` | no | `—` | — | `value` | Promotion scope class filter. |
| `--explicit-remember` | no | `—` | — | `store_true` | Request immediate remember promotion; ignored without a trusted remember receipt. |
| `--dry-run` | no | `—` | — | `store_true` | Report without mutation. |

## `agentic-workspace agent-guidance supersede`

agent guidance lifecycle subcommand

| Flags | Required | Default | Choices | Action / nargs | Description |
| --- | --- | --- | --- | --- | --- |
| `--format` | no | `text` | text, json | `value` | Output format. |
| `--target` | no | `—` | — | `value` | Target repository path. Defaults to current directory. |
| `--guidance-id` | no | `—` | — | `value` | Guidance lifecycle record id. |
| `--expected-revision` | no | `—` | — | `value` | Expected current record revision for transition operations. |
| `--expected-record-revisions-json` | no | `—` | — | `value` | JSON object of related guidance ids to expected revisions. |
| `--reason` | no | `—` | — | `value` | Human-readable lifecycle transition reason. |
| `--instruction` | no | `—` | — | `value` | Replacement instruction for edit operations. |
| `--replacement-guidance-id` | no | `—` | — | `value` | Replacement guidance id for supersede operations. |
| `--merge-guidance-id` | no | `—` | — | `append` | Guidance id to merge into the selected record. Repeat for multiple ids. |
| `--split-instruction` | no | `—` | — | `append` | Replacement instruction for split operations. Repeat at least twice. |
| `--task-class` | no | `—` | — | `value` | Promotion task class filter. |
| `--scope-class` | no | `—` | — | `value` | Promotion scope class filter. |
| `--explicit-remember` | no | `—` | — | `store_true` | Request immediate remember promotion; ignored without a trusted remember receipt. |
| `--dry-run` | no | `—` | — | `store_true` | Report without mutation. |

## `agentic-workspace agent-guidance retire`

agent guidance lifecycle subcommand

| Flags | Required | Default | Choices | Action / nargs | Description |
| --- | --- | --- | --- | --- | --- |
| `--format` | no | `text` | text, json | `value` | Output format. |
| `--target` | no | `—` | — | `value` | Target repository path. Defaults to current directory. |
| `--guidance-id` | no | `—` | — | `value` | Guidance lifecycle record id. |
| `--expected-revision` | no | `—` | — | `value` | Expected current record revision for transition operations. |
| `--expected-record-revisions-json` | no | `—` | — | `value` | JSON object of related guidance ids to expected revisions. |
| `--reason` | no | `—` | — | `value` | Human-readable lifecycle transition reason. |
| `--instruction` | no | `—` | — | `value` | Replacement instruction for edit operations. |
| `--replacement-guidance-id` | no | `—` | — | `value` | Replacement guidance id for supersede operations. |
| `--merge-guidance-id` | no | `—` | — | `append` | Guidance id to merge into the selected record. Repeat for multiple ids. |
| `--split-instruction` | no | `—` | — | `append` | Replacement instruction for split operations. Repeat at least twice. |
| `--task-class` | no | `—` | — | `value` | Promotion task class filter. |
| `--scope-class` | no | `—` | — | `value` | Promotion scope class filter. |
| `--explicit-remember` | no | `—` | — | `store_true` | Request immediate remember promotion; ignored without a trusted remember receipt. |
| `--dry-run` | no | `—` | — | `store_true` | Report without mutation. |

## `agentic-workspace agent-guidance delete`

agent guidance lifecycle subcommand

| Flags | Required | Default | Choices | Action / nargs | Description |
| --- | --- | --- | --- | --- | --- |
| `--format` | no | `text` | text, json | `value` | Output format. |
| `--target` | no | `—` | — | `value` | Target repository path. Defaults to current directory. |
| `--guidance-id` | no | `—` | — | `value` | Guidance lifecycle record id. |
| `--expected-revision` | no | `—` | — | `value` | Expected current record revision for transition operations. |
| `--expected-record-revisions-json` | no | `—` | — | `value` | JSON object of related guidance ids to expected revisions. |
| `--reason` | no | `—` | — | `value` | Human-readable lifecycle transition reason. |
| `--instruction` | no | `—` | — | `value` | Replacement instruction for edit operations. |
| `--replacement-guidance-id` | no | `—` | — | `value` | Replacement guidance id for supersede operations. |
| `--merge-guidance-id` | no | `—` | — | `append` | Guidance id to merge into the selected record. Repeat for multiple ids. |
| `--split-instruction` | no | `—` | — | `append` | Replacement instruction for split operations. Repeat at least twice. |
| `--task-class` | no | `—` | — | `value` | Promotion task class filter. |
| `--scope-class` | no | `—` | — | `value` | Promotion scope class filter. |
| `--explicit-remember` | no | `—` | — | `store_true` | Request immediate remember promotion; ignored without a trusted remember receipt. |
| `--dry-run` | no | `—` | — | `store_true` | Report without mutation. |

## `agentic-workspace assignment`

public adapter-neutral assignment/run lifecycle front door

| Flags | Required | Default | Choices | Action / nargs | Description |
| --- | --- | --- | --- | --- | --- |
| `--format` | no | `text` | text, json | `value` | Output format. |
| `--target` | no | `—` | — | `value` | Target repository path. Defaults to the current directory. |

## `agentic-workspace assignment admit`

assignment lifecycle subcommand

| Flags | Required | Default | Choices | Action / nargs | Description |
| --- | --- | --- | --- | --- | --- |
| `--format` | no | `text` | text, json | `value` | Output format. |
| `--assignment-gate-json` | no | `—` | — | `value` | Serialized current assignment gate authority. |
| `--assignment-policy-json` | no | `—` | — | `value` | Serialized current assignment policy authority. |
| `--delegation-decision-json` | no | `—` | — | `value` | Serialized current delegation decision authority. |
| `--aw-proof-receipt-json` | no | `—` | — | `value` | Serialized AW proof receipt authority. |
| `--run-state-json` | no | `—` | — | `value` | Serialized current assignment run state authority. |
| `--review-result-json` | no | `—` | — | `value` | Serialized producer-owned independent-review result envelope. |
| `--review-result-ref` | no | `—` | — | `value` | Repo-relative independent-review result envelope to admit. |
| `--host-result-ref` | no | `—` | — | `value` | Opaque host/adapter independent-review result ref to import and admit; a protected host/adapter resolver must supply the admission verdict. |
| `--required-mode` | no | `—` | fresh-context, separate-actor, distinct-provider, human | `value` | Required independent-review separation mode. |
| `--changed` | no | `—` | — | `extend; nargs=*` | Changed paths whose review scope must match the admitted result. |

## `agentic-workspace assignment cleanup`

assignment lifecycle subcommand

| Flags | Required | Default | Choices | Action / nargs | Description |
| --- | --- | --- | --- | --- | --- |
| `--format` | no | `text` | text, json | `value` | Output format. |
| `--assignment-gate-json` | no | `—` | — | `value` | Serialized current assignment gate authority. |
| `--assignment-policy-json` | no | `—` | — | `value` | Serialized current assignment policy authority. |
| `--delegation-decision-json` | no | `—` | — | `value` | Serialized current delegation decision authority. |
| `--aw-proof-receipt-json` | no | `—` | — | `value` | Serialized AW proof receipt authority. |
| `--run-state-json` | no | `—` | — | `value` | Serialized current assignment run state authority. |

## `agentic-workspace assignment status`

read-only exact assignment/run inspection

| Flags | Required | Default | Choices | Action / nargs | Description |
| --- | --- | --- | --- | --- | --- |
| `--format` | no | `text` | text, json | `value` | Output format. |

## `agentic-workspace assignment close`

assignment lifecycle subcommand

| Flags | Required | Default | Choices | Action / nargs | Description |
| --- | --- | --- | --- | --- | --- |
| `--format` | no | `text` | text, json | `value` | Output format. |
| `--assignment-gate-json` | no | `—` | — | `value` | Serialized current assignment gate authority. |
| `--assignment-policy-json` | no | `—` | — | `value` | Serialized current assignment policy authority. |
| `--delegation-decision-json` | no | `—` | — | `value` | Serialized current delegation decision authority. |
| `--aw-proof-receipt-json` | no | `—` | — | `value` | Serialized AW proof receipt authority. |
| `--run-state-json` | no | `—` | — | `value` | Serialized current assignment run state authority. |

## `agentic-workspace assignment dispatch`

assignment lifecycle subcommand

| Flags | Required | Default | Choices | Action / nargs | Description |
| --- | --- | --- | --- | --- | --- |
| `--format` | no | `text` | text, json | `value` | Output format. |

## `agentic-workspace assignment export`

assignment lifecycle subcommand

| Flags | Required | Default | Choices | Action / nargs | Description |
| --- | --- | --- | --- | --- | --- |
| `--format` | no | `text` | text, json | `value` | Output format. |
| `--assignment-gate-json` | no | `—` | — | `value` | Serialized current assignment gate authority. |
| `--assignment-policy-json` | no | `—` | — | `value` | Serialized current assignment policy authority. |
| `--delegation-decision-json` | no | `—` | — | `value` | Serialized current delegation decision authority. |
| `--aw-proof-receipt-json` | no | `—` | — | `value` | Serialized AW proof receipt authority. |
| `--run-state-json` | no | `—` | — | `value` | Serialized current assignment run state authority. |

## `agentic-workspace assignment import`

assignment lifecycle subcommand

| Flags | Required | Default | Choices | Action / nargs | Description |
| --- | --- | --- | --- | --- | --- |
| `--format` | no | `text` | text, json | `value` | Output format. |
| `--assignment-gate-json` | no | `—` | — | `value` | Serialized current assignment gate authority. |
| `--assignment-policy-json` | no | `—` | — | `value` | Serialized current assignment policy authority. |
| `--delegation-decision-json` | no | `—` | — | `value` | Serialized current delegation decision authority. |
| `--aw-proof-receipt-json` | no | `—` | — | `value` | Serialized AW proof receipt authority. |
| `--run-state-json` | no | `—` | — | `value` | Serialized current assignment run state authority. |

## `agentic-workspace assignment integrate`

assignment lifecycle subcommand

| Flags | Required | Default | Choices | Action / nargs | Description |
| --- | --- | --- | --- | --- | --- |
| `--format` | no | `text` | text, json | `value` | Output format. |
| `--assignment-gate-json` | no | `—` | — | `value` | Serialized current assignment gate authority. |
| `--assignment-policy-json` | no | `—` | — | `value` | Serialized current assignment policy authority. |
| `--delegation-decision-json` | no | `—` | — | `value` | Serialized current delegation decision authority. |
| `--aw-proof-receipt-json` | no | `—` | — | `value` | Serialized AW proof receipt authority. |
| `--run-state-json` | no | `—` | — | `value` | Serialized current assignment run state authority. |

## `agentic-workspace assignment override`

assignment lifecycle subcommand

| Flags | Required | Default | Choices | Action / nargs | Description |
| --- | --- | --- | --- | --- | --- |
| `--format` | no | `text` | text, json | `value` | Output format. |
| `--assignment-gate-json` | no | `—` | — | `value` | Serialized current assignment gate authority. |
| `--assignment-policy-json` | no | `—` | — | `value` | Serialized current assignment policy authority. |
| `--delegation-decision-json` | no | `—` | — | `value` | Serialized current delegation decision authority. |
| `--aw-proof-receipt-json` | no | `—` | — | `value` | Serialized AW proof receipt authority. |
| `--run-state-json` | no | `—` | — | `value` | Serialized current assignment run state authority. |

## `agentic-workspace assignment reassign`

assignment lifecycle subcommand

| Flags | Required | Default | Choices | Action / nargs | Description |
| --- | --- | --- | --- | --- | --- |
| `--format` | no | `text` | text, json | `value` | Output format. |
| `--assignment-gate-json` | no | `—` | — | `value` | Serialized current assignment gate authority. |
| `--assignment-policy-json` | no | `—` | — | `value` | Serialized current assignment policy authority. |
| `--delegation-decision-json` | no | `—` | — | `value` | Serialized current delegation decision authority. |
| `--aw-proof-receipt-json` | no | `—` | — | `value` | Serialized AW proof receipt authority. |
| `--run-state-json` | no | `—` | — | `value` | Serialized current assignment run state authority. |

## `agentic-workspace assignment reject`

assignment lifecycle subcommand

| Flags | Required | Default | Choices | Action / nargs | Description |
| --- | --- | --- | --- | --- | --- |
| `--format` | no | `text` | text, json | `value` | Output format. |
| `--assignment-gate-json` | no | `—` | — | `value` | Serialized current assignment gate authority. |
| `--assignment-policy-json` | no | `—` | — | `value` | Serialized current assignment policy authority. |
| `--delegation-decision-json` | no | `—` | — | `value` | Serialized current delegation decision authority. |
| `--aw-proof-receipt-json` | no | `—` | — | `value` | Serialized AW proof receipt authority. |
| `--run-state-json` | no | `—` | — | `value` | Serialized current assignment run state authority. |

## `agentic-workspace assignment repair`

assignment lifecycle subcommand

| Flags | Required | Default | Choices | Action / nargs | Description |
| --- | --- | --- | --- | --- | --- |
| `--format` | no | `text` | text, json | `value` | Output format. |
| `--assignment-gate-json` | no | `—` | — | `value` | Serialized current assignment gate authority. |
| `--assignment-policy-json` | no | `—` | — | `value` | Serialized current assignment policy authority. |
| `--delegation-decision-json` | no | `—` | — | `value` | Serialized current delegation decision authority. |
| `--aw-proof-receipt-json` | no | `—` | — | `value` | Serialized AW proof receipt authority. |
| `--run-state-json` | no | `—` | — | `value` | Serialized current assignment run state authority. |

## `agentic-workspace correction-event`

local correction-event lifecycle and bounded storage diagnostic front door

| Flags | Required | Default | Choices | Action / nargs | Description |
| --- | --- | --- | --- | --- | --- |
| — | — | — | — | — | No declared options. |

## `agentic-workspace correction-event identity-init`

local target identity lifecycle subcommand

| Flags | Required | Default | Choices | Action / nargs | Description |
| --- | --- | --- | --- | --- | --- |
| `--format` | no | `text` | text, json | `value` | Output format. |
| `--target` | no | `—` | — | `value` | Target repository path. Defaults to current directory. |
| `--target-profile` | no | `—` | — | `value` | Configured profile name; defaults to the current target. |
| `--target-id` | no | `—` | — | `value` | Optional caller-selected stable local id; the generated collision-checked id is used by default. |
| `--expected-config-digest` | no | `—` | — | `value` | Optional config digest from a dry run for compare-and-swap admission. |
| `--dry-run` | no | `—` | — | `store_true` | Return the exact identity/config mutation without writing local config. |

## `agentic-workspace correction-event submit`

correction event lifecycle subcommand

| Flags | Required | Default | Choices | Action / nargs | Description |
| --- | --- | --- | --- | --- | --- |
| `--format` | no | `text` | text, json | `value` | Output format. |
| `--target` | no | `—` | — | `value` | Target repository path. Defaults to current directory. |
| `--event-json` | no | `—` | — | `value` | Serialized correction event JSON. |
| `--trusted-host-event-json` | no | `—` | — | `value` | Signed producer-owned host observation envelope; caller labels do not confer authority. |
| `--host-event-ref` | no | `—` | — | `value` | Opaque trusted-host observation reference for later normalization or disposition. |
| `--trusted-authority-receipt-ref` | no | `—` | — | `value` | Repo-relative AW/human authority receipt reference resolved by the host boundary. |
| `--idempotency-key` | no | `—` | — | `value` | Stable delivery idempotency key. |
| `--delivery-id` | no | `—` | — | `value` | Stable delivery id. |
| `--event-id` | no | `—` | — | `value` | Existing normalized correction event id for a route/disposition update. |
| `--target-identity-ref` | no | `—` | — | `value` | Target id/name/alias to resolve. |
| `--target-revision` | no | `—` | — | `value` | Submitted target revision. |
| `--source-ref` | no | `—` | — | `value` | Stable source reference. |
| `--source` | no | `—` | — | `value` | Submitted source label. |
| `--producer-class` | no | `—` | — | `value` | Submitted producer class; cannot upgrade authority without a trusted receipt. |
| `--producer-id` | no | `—` | — | `value` | Producer id. |
| `--authority` | no | `—` | — | `value` | Claimed authority; ignored for upgrade without trusted receipt. |
| `--desired-behavior` | no | `—` | — | `value` | Desired behavior. |
| `--replaced-behavior` | no | `—` | — | `value` | Replaced behavior. |
| `--invariant-id` | no | `—` | — | `value` | Structured invariant id. |
| `--behavior-class` | no | `—` | — | `value` | Structured behavior class. |
| `--task-class` | no | `—` | — | `value` | Task class applicability. |
| `--scope-class` | no | `—` | — | `value` | Scope class applicability. |
| `--route-decision` | no | `—` | — | `append` | Route decision. Repeat for multiple routes. |
| `--evidence-hash` | no | `—` | — | `value` | Evidence hash. |
| `--evidence-ref` | no | `—` | — | `value` | Evidence reference. |
| `--predecessor-event-id` | no | `—` | — | `value` | Predecessor event id for lifecycle transitions. |
| `--lifecycle-action` | no | `—` | withdraw, supersede | `value` | Withdraw/supersede action. |
| `--dry-run` | no | `—` | — | `store_true` | Report without mutation. |

## `agentic-workspace correction-event query`

correction event lifecycle subcommand

| Flags | Required | Default | Choices | Action / nargs | Description |
| --- | --- | --- | --- | --- | --- |
| `--format` | no | `text` | text, json | `value` | Output format. |
| `--target` | no | `—` | — | `value` | Target repository path. Defaults to current directory. |
| `--event-json` | no | `—` | — | `value` | Serialized correction event JSON. |
| `--trusted-authority-receipt-ref` | no | `—` | — | `value` | Repo-relative AW/human authority receipt reference resolved by the host boundary. |
| `--idempotency-key` | no | `—` | — | `value` | Stable delivery idempotency key. |
| `--delivery-id` | no | `—` | — | `value` | Stable delivery id. |
| `--target-identity-ref` | no | `—` | — | `value` | Target id/name/alias to resolve. |
| `--target-revision` | no | `—` | — | `value` | Submitted target revision. |
| `--source-ref` | no | `—` | — | `value` | Stable source reference. |
| `--source` | no | `—` | — | `value` | Submitted source label. |
| `--producer-class` | no | `—` | — | `value` | Submitted producer class; cannot upgrade authority without a trusted receipt. |
| `--producer-id` | no | `—` | — | `value` | Producer id. |
| `--authority` | no | `—` | — | `value` | Claimed authority; ignored for upgrade without trusted receipt. |
| `--desired-behavior` | no | `—` | — | `value` | Desired behavior. |
| `--replaced-behavior` | no | `—` | — | `value` | Replaced behavior. |
| `--invariant-id` | no | `—` | — | `value` | Structured invariant id. |
| `--behavior-class` | no | `—` | — | `value` | Structured behavior class. |
| `--task-class` | no | `—` | — | `value` | Task class applicability. |
| `--scope-class` | no | `—` | — | `value` | Scope class applicability. |
| `--route-decision` | no | `—` | — | `append` | Route decision. Repeat for multiple routes. |
| `--evidence-hash` | no | `—` | — | `value` | Evidence hash. |
| `--evidence-ref` | no | `—` | — | `value` | Evidence reference. |
| `--predecessor-event-id` | no | `—` | — | `value` | Predecessor event id for lifecycle transitions. |
| `--lifecycle-action` | no | `—` | withdraw, supersede | `value` | Withdraw/supersede action. |
| `--dry-run` | no | `—` | — | `store_true` | Report without mutation. |

## `agentic-workspace correction-event correct-dispute`

correction event lifecycle subcommand

| Flags | Required | Default | Choices | Action / nargs | Description |
| --- | --- | --- | --- | --- | --- |
| `--format` | no | `text` | text, json | `value` | Output format. |
| `--target` | no | `—` | — | `value` | Target repository path. Defaults to current directory. |
| `--event-json` | no | `—` | — | `value` | Serialized correction event JSON. |
| `--trusted-authority-receipt-ref` | no | `—` | — | `value` | Repo-relative AW/human authority receipt reference resolved by the host boundary. |
| `--idempotency-key` | no | `—` | — | `value` | Stable delivery idempotency key. |
| `--delivery-id` | no | `—` | — | `value` | Stable delivery id. |
| `--target-identity-ref` | no | `—` | — | `value` | Target id/name/alias to resolve. |
| `--target-revision` | no | `—` | — | `value` | Submitted target revision. |
| `--source-ref` | no | `—` | — | `value` | Stable source reference. |
| `--source` | no | `—` | — | `value` | Submitted source label. |
| `--producer-class` | no | `—` | — | `value` | Submitted producer class; cannot upgrade authority without a trusted receipt. |
| `--producer-id` | no | `—` | — | `value` | Producer id. |
| `--authority` | no | `—` | — | `value` | Claimed authority; ignored for upgrade without trusted receipt. |
| `--desired-behavior` | no | `—` | — | `value` | Desired behavior. |
| `--replaced-behavior` | no | `—` | — | `value` | Replaced behavior. |
| `--invariant-id` | no | `—` | — | `value` | Structured invariant id. |
| `--behavior-class` | no | `—` | — | `value` | Structured behavior class. |
| `--task-class` | no | `—` | — | `value` | Task class applicability. |
| `--scope-class` | no | `—` | — | `value` | Scope class applicability. |
| `--route-decision` | no | `—` | — | `append` | Route decision. Repeat for multiple routes. |
| `--evidence-hash` | no | `—` | — | `value` | Evidence hash. |
| `--evidence-ref` | no | `—` | — | `value` | Evidence reference. |
| `--predecessor-event-id` | no | `—` | — | `value` | Predecessor event id for lifecycle transitions. |
| `--lifecycle-action` | no | `—` | withdraw, supersede | `value` | Withdraw/supersede action. |
| `--dry-run` | no | `—` | — | `store_true` | Report without mutation. |

## `agentic-workspace correction-event withdraw-supersede`

correction event lifecycle subcommand

| Flags | Required | Default | Choices | Action / nargs | Description |
| --- | --- | --- | --- | --- | --- |
| `--format` | no | `text` | text, json | `value` | Output format. |
| `--target` | no | `—` | — | `value` | Target repository path. Defaults to current directory. |
| `--event-json` | no | `—` | — | `value` | Serialized correction event JSON. |
| `--trusted-authority-receipt-ref` | no | `—` | — | `value` | Repo-relative AW/human authority receipt reference resolved by the host boundary. |
| `--idempotency-key` | no | `—` | — | `value` | Stable delivery idempotency key. |
| `--delivery-id` | no | `—` | — | `value` | Stable delivery id. |
| `--target-identity-ref` | no | `—` | — | `value` | Target id/name/alias to resolve. |
| `--target-revision` | no | `—` | — | `value` | Submitted target revision. |
| `--source-ref` | no | `—` | — | `value` | Stable source reference. |
| `--source` | no | `—` | — | `value` | Submitted source label. |
| `--producer-class` | no | `—` | — | `value` | Submitted producer class; cannot upgrade authority without a trusted receipt. |
| `--producer-id` | no | `—` | — | `value` | Producer id. |
| `--authority` | no | `—` | — | `value` | Claimed authority; ignored for upgrade without trusted receipt. |
| `--desired-behavior` | no | `—` | — | `value` | Desired behavior. |
| `--replaced-behavior` | no | `—` | — | `value` | Replaced behavior. |
| `--invariant-id` | no | `—` | — | `value` | Structured invariant id. |
| `--behavior-class` | no | `—` | — | `value` | Structured behavior class. |
| `--task-class` | no | `—` | — | `value` | Task class applicability. |
| `--scope-class` | no | `—` | — | `value` | Scope class applicability. |
| `--route-decision` | no | `—` | — | `append` | Route decision. Repeat for multiple routes. |
| `--evidence-hash` | no | `—` | — | `value` | Evidence hash. |
| `--evidence-ref` | no | `—` | — | `value` | Evidence reference. |
| `--predecessor-event-id` | no | `—` | — | `value` | Predecessor event id for lifecycle transitions. |
| `--lifecycle-action` | no | `—` | withdraw, supersede | `value` | Withdraw/supersede action. |
| `--dry-run` | no | `—` | — | `store_true` | Report without mutation. |

## `agentic-workspace correction-event prune-compact`

correction event lifecycle subcommand

| Flags | Required | Default | Choices | Action / nargs | Description |
| --- | --- | --- | --- | --- | --- |
| `--format` | no | `text` | text, json | `value` | Output format. |
| `--target` | no | `—` | — | `value` | Target repository path. Defaults to current directory. |
| `--event-json` | no | `—` | — | `value` | Serialized correction event JSON. |
| `--trusted-authority-receipt-ref` | no | `—` | — | `value` | Repo-relative AW/human authority receipt reference resolved by the host boundary. |
| `--idempotency-key` | no | `—` | — | `value` | Stable delivery idempotency key. |
| `--delivery-id` | no | `—` | — | `value` | Stable delivery id. |
| `--target-identity-ref` | no | `—` | — | `value` | Target id/name/alias to resolve. |
| `--target-revision` | no | `—` | — | `value` | Submitted target revision. |
| `--source-ref` | no | `—` | — | `value` | Stable source reference. |
| `--source` | no | `—` | — | `value` | Submitted source label. |
| `--producer-class` | no | `—` | — | `value` | Submitted producer class; cannot upgrade authority without a trusted receipt. |
| `--producer-id` | no | `—` | — | `value` | Producer id. |
| `--authority` | no | `—` | — | `value` | Claimed authority; ignored for upgrade without trusted receipt. |
| `--desired-behavior` | no | `—` | — | `value` | Desired behavior. |
| `--replaced-behavior` | no | `—` | — | `value` | Replaced behavior. |
| `--invariant-id` | no | `—` | — | `value` | Structured invariant id. |
| `--behavior-class` | no | `—` | — | `value` | Structured behavior class. |
| `--task-class` | no | `—` | — | `value` | Task class applicability. |
| `--scope-class` | no | `—` | — | `value` | Scope class applicability. |
| `--route-decision` | no | `—` | — | `append` | Route decision. Repeat for multiple routes. |
| `--evidence-hash` | no | `—` | — | `value` | Evidence hash. |
| `--evidence-ref` | no | `—` | — | `value` | Evidence reference. |
| `--predecessor-event-id` | no | `—` | — | `value` | Predecessor event id for lifecycle transitions. |
| `--lifecycle-action` | no | `—` | withdraw, supersede | `value` | Withdraw/supersede action. |
| `--dry-run` | no | `—` | — | `store_true` | Report without mutation. |
