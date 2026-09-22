# Testing Strategy

Use this guide before adding or pruning tests in this repository. The goal is to preserve behaviour contracts with fewer one-off regressions and less implementation-shape lock-in.

## Evidence design, current validation, and permanent retention

Treat these as separate decisions, not three new durable artefacts:

1. **Evidence design:** name the bounded claim, the material failure/authority
   classes that could falsify it, and the observation that would expose each.
   Inspect relevant existing stable owner/contract evidence first and factor
   shared evidence across criteria. Lowest sufficient means a stable behavioural
   contract, not merely the nearest private implementation function.
2. **Current patch validation:** obtain or reuse current evidence for those risks,
   stating what each observation does and does not establish. Temporary
   characterisation or an incident reproduction may validate this patch without
   becoming a permanent test. Testing proof-governance machinery is necessary
   when it changes, but does not establish that an unrelated patch applied the
   strategy correctly.
3. **Permanent retention:** retain new executable evidence only for a distinct
   durable failure class not already sufficiently represented. Prefer reuse,
   extension, consolidation or conversion of existing owner/scenario/conformance
   cases; no permanent addition is a valid outcome. An incident reproduction,
   including a test that fails before the fix, is not itself retention
   justification. Shape a newly discovered missing class around its stable
   behaviour rather than preserving incident-specific history. Selecting a command
   for this patch does not make it a permanent test; retaining a test does not
   make it an ordinary-CI constituent.

The default is not `fix -> add permanent regression`. Preserve binding source-owned
coverage, safety, authority and review floors. Commands and fixtures are replaceable
methods unless the governing source explicitly requires that method itself.

Closeout must give a bounded **stop/escalate** rationale: identify the claim, the
risks addressed, evidence contribution and limits, and any named material residual
risk. Stop when the current evidence satisfies the bounded claim and mandatory
floors with no material unresolved risk; absence of an unspecified broader suite
is not unfinished work. Escalate through the existing proof owner only when a
named remaining risk requires additional evidence, explaining the observation
sought and the boundary at which to stop. Missing required proof cannot be waived
by a stop rationale. These are compact reasoning prompts, not a scoring model,
mandatory schema, new ledger or replacement for Verification/proof selection.

## Test and CI delta disposition

When changing behaviour, executable tests or ordinary CI, apply the lifecycle above
and the contract ladder below
before writing permanent tests. Include a compact disposition in the PR description
or implementation closeout: durable behavior/claim; lowest sufficient owner and
contract level; reason for any higher-level or repeated public-surface case;
duplicate/subsumed evidence merged or removed; and recurring CI cost and failure
localisation relative to the merge claim, with the stop/escalate rationale above.
A short paragraph or small table suffices;
do not add a per-test ledger or a second proof-selection mechanism.

Repeated adapters are justified by distinct transport/serialization/packaging risk,
not by the number of supported entrypoints. Prefer the existing native contract
and conformance evidence for shared semantics. Permanent test and CI names describe
durable owners or behaviour, never a temporary issue or priority batch. Name and
bound expensive CI constituents so a timeout identifies the affected claim.

A material violation blocks independent approval unless a distinct durable claim
justifies the additional proof level, repetition or cost. Passing tests alone do
not justify retaining them. Broad validation remains available through the current
Verification/proof-selection path for a stated cross-cutting or high-risk claim;
a passing narrow check does not automatically require all broader suites.

### Controlled review examples

- **Block:** a PR adds the same stale-source assertion to four public adapters,
  while core currentness and existing adapter conformance already prove it, and
  wires the new issue-named suite into every PR. The disposition names no distinct
  transport risk. Require consolidation at the currentness owner and removal of
  the recurring duplicate. Shape the issue around stale-authority rejection,
  sharing one owner-level observation across the acceptance examples. Reproduce
  the incident temporarily, then reuse or extend the existing behaviour-class
  case instead of retaining another regression. Stop after current rejection and
  required parity evidence; escalate only if a named adapter boundary remains
  unproven. Review blocks permanent duplication even if every new test passes.
- **Accept this test delta:** a PR fixes CLI forwarding of repeated `--changed`
  values and Python/Node encoding of a Unicode request. Keep small adapter cases
  for those distinct boundaries, referencing existing core source-currentness
  proof. A single bounded native mutation/recovery journey may remain for the
  cross-owner composition that primitives cannot prove. Acceptance of this
  disposition grants neither independent review authority nor whole-PR approval.
  If existing evidence does not cover lossy Unicode argument transport, shape
  that as a new durable failure class, validate it on the current patch and retain
  the minimal adapter case. Factor core source-currentness evidence out of the
  surface examples. Review accepts the additional case for its distinct risk;
  stop once argument fidelity and binding floors are proven, or escalate to an
  affected platform only if its encoding behaviour remains materially unresolved.

## Current Inventory

The June 15, 2026 inventory for #1521 was refreshed after the first reduction slices with:

- root workspace: 613 collected tests / 34 files
- planning package: 248 collected tests
- memory package: 246 collected tests
- verification package: 11 collected tests
- total: 1,118 collected tests / 57 files

Collection is fast, so the immediate problem is not raw collection time. A full root duration pass exceeded 10 minutes during #1521 measurement, so the current pressure is both runtime hotspots and a growing pile of narrow regression tests around broad workflow surfaces.

The largest current executable clusters by collected test count are:

- `tests/test_generated_tool_conformance.py` (91)
- `packages/memory/tests/test_install.py` (79)
- `packages/planning/tests/test_archive.py` (64)
- `tests/test_workspace_implement_cli.py` (61)
- `tests/test_workspace_proof_cli.py` (56)
- `tests/test_generated_command_package_proof_runner.py` (56)
- `tests/test_workspace_config_cli.py` (50)
- `packages/planning/tests/test_install.py` (47)
- `packages/memory/tests/test_doctor.py` (45)
- `packages/memory/tests/test_routing.py` (44)
- `packages/planning/tests/test_check_planning_surfaces.py` (43)

These current clusters are not automatically bad. Treat them as the first places to look for scenario consolidation, table-driven structure, or contract-owned conformance cases when related work changes them.

Retired legacy clusters from the #1536/#1537/#1538/#1539/#1540/#1541 finish-lane slice are no longer current executable hotspots: `tests/test_model_cli_harness.py`, `tests/test_workspace_report_cli.py`, `tests/test_workspace_start_preflight_cli.py`, `packages/planning/tests/test_summary.py`, `tests/test_contract_tooling.py`, and `tests/test_workspace_lifecycle_cli.py`. Their migration records live in `docs/maintainer/test-knowledge-inventory.md`; new work should use focused current evidence rather than reviving those broad files.

The first #1521 reduction slice consolidated repeated packaging builds in `tests/test_workspace_packaging.py`, `packages/memory/tests/test_packaging.py`, and `packages/planning/tests/test_packaging.py`. Those tests now reuse module-scoped wheel and sdist artefacts while preserving the same inventory, import, workflow, and install assertions. The packaging subset passes in about 20 seconds on the local Windows checkout.

The #1524 workflow-cluster slice merged the live-checkout active-only and verbose preflight mode checks in `tests/test_workspace_start_preflight_cli.py` into one scenario-matrix test. The affected `tests/test_workspace_report_cli.py` plus `tests/test_workspace_start_preflight_cli.py` subset moved from 234 collected tests / 139.18 seconds to 233 collected tests / 133.93 seconds while retaining the active-state, full-takeover, startup-guidance, and resolved-config assertions.

The #1526 ownership slice reviewed root lifecycle/module orchestration against Memory and Planning package-local install/current-state tests. The package-local install/current-memory subset moved from 143 tests / 3.33 seconds to 142 tests / 2.98 seconds by merging duplicate generated `current show` JSON/text view tests in `packages/memory/tests/test_current_memory.py`; the remaining current-memory tests are retained as explicit Memory residue, migration, and stale-active-state guard coverage.

The #1531/#1532/#1533 follow-up slice merged narrow duplicate scenario groups in the largest remaining root clusters: report section aliases, model CLI harness raw-read warning variants, and static generated-package completion-gate evidence checks. The affected report/start-preflight, model harness, and generated proof-runner subset moved from 433 collected tests to 428 collected tests while retaining high-risk workflow, scorer-warning, and proof/checker coverage.

The #1535 Verification dogfood slice added the host-neutral `evidence_strategy` diagnostic report and used it to classify #1534 hotspot files before further reduction. The dogfood pass found 7 high-confidence merge candidates across 710 hotspot tests under the conservative exact-prefix heuristic, then merged the clearest model-harness, generated proof-runner, implement-context, and planning cleanup/routing groups. A follow-up reduction pass broadened that same scenario-matrix approach to adapter rendering, quality-signal, execution-warning, and generated-proof acceptance variants. The review fix tightened the Verification authority boundary so strategy prose is surfaced for agent judgement rather than interpreted by string matching.

The #1536/#1537/#1538/#1539/#1540/#1541 finish-lane slice added the `test-knowledge-inventory.md` migration record, extended Verification with inventory review questions, and consolidated more ordinary regressions into behaviour-class matrices. A first pass moved the full `tests packages` inventory from 1,710 collected tests to 1,698 collected tests while adding durable knowledge records and keeping scenario labels for generated proof-runner static-surface failures, generated operation CLI input proof, model-harness native-plan bridge failures, and planning archive cleanup pointer variants.

The follow-through pass then removed the largest legacy regression clusters after recording compact migration entries in `docs/maintainer/test-knowledge-inventory.md`: report CLI, model CLI harness, start/preflight CLI, planning summary, contract tooling, and workspace lifecycle. Those files no longer define permanent executable proof and are not retained as source archives. The executable suite now sits inside the advisory target range at 1,118 collected tests, and `make test-workspace` passed in 103.37 seconds on the local Windows checkout.

## Suite Budgets

These budgets are advisory until a maintainer chooses enforcement. Use them as closeout pressure against casual permanent regression growth:

| Surface | Current count | Target range | Runtime budget |
| --- | ---: | ---: | --- |
| Total `tests packages` suite | 1,118 | 900-1,200 | `make test-workspace` passed in 103.37 seconds after retiring legacy clusters. |
| Root workspace tests | 613 | 500-700 | Prefer root tests only for product orchestration, user-visible adapter behaviour, and high-risk workflow semantics. |
| Planning package tests | 248 | 250-325 | Slightly under target after retiring planning summary regressions; add package tests only for durable module contracts. |
| Memory package tests | 246 | 200-250 | Near target; avoid adding one-off migration regressions unless they cannot be represented as scenario rows. |
| Verification package tests | 11 | 40-80 | Expected to grow as Verification takes on evidence surfaces, but new cases should cover report contracts rather than host policy decisions. |

## Validation Runtime Composition

Ordinary non-draft PRs and `master` pushes run the single `Merge sufficiency`
CI job: frozen dependencies, Rust compile/format, Workspace lint/types, and
representative public integration and stage-policy contracts. Focused proof for
the changed owner or claim remains part of the existing AW/review evidence path;
the compact job does not replace it with another changed-path test router.

Exhaustive pre-merge proof is an explicit escalation. Dispatch `ci.yml` at the
intended ref with its exact `expected_head_sha` and a visible `reason` describing
the cross-cutting or high-risk claim. Only that event allocates the broad suites,
package builds/install proof, packed conformance, runtime matrix, and aggregate.
The coordinated release preparer supplies its release-candidate reason through
the same entrypoint. Preview and stable publishers independently prove their
actual candidate artefacts before publication; earlier PR checks cannot stand
in for that evidence.

Use setup-bearing public targets for ordinary local entrypoints and setup-free
`*-nosync` targets when a caller has already synchronised the environment.
This keeps validation observable without silently repeating dependency setup:

- `make check` performs root synchronisation once, then delegates to
  `check-nosync`.
- `make test`, `make lint`, `make typecheck`, `make format-check`, and
  `make verify` keep their public setup-bearing behaviour while exposing
  corresponding `*-nosync` constituents for CI and composed validation.
- CI jobs should run the narrow explicit sync step once, then call setup-free
  targets such as `make typecheck-nosync` or `make check-memory-nosync`.
- The compact command runner writes one versioned JSON result per constituent
  under `scratch/validation-results/<run-id>/` and prints the current
  constituent before waiting. Timeouts and failures must name the constituent
  and durable log/result locations.

Use `scripts/check/check_structured_file_inventory.py --changed <paths...>`
for focused changed-path proof. It escalates to the full inventory audit when
the inventory, schema, or matching implementation changes. The full
`make structured-file-inventory` audit remains the broad no-prune proof for
inventory coverage, schema validation, guardrails, generated mirror policy, and
staged-deletion safety.

Current validation composition is the Makefile and CI workflow. The Makefile
contract tests prove setup boundaries and complete, nonduplicated root test
partitioning; compact-runner tests prove fresh run identities, explicit joins,
retry reasons, timeout/failure results and rejection of conflicting writers.
The former #2435 package/generator graph and its timing evidence are historical,
not a current closeout gate. Do not silently attach that graph to new commands.
Explicit command identity, dependencies and proof purpose may be supplied to the
compact runner; its records do not themselves grant native proof authority.

`make memory-freshness-strict` audits retained Memory metadata and selected
freshness categories. It is a maintainer check; it does not admit native proof,
resolve semantic currentness or establish task completion.

Use `make check-bounded-parallel` for explicit full broad validation when the
runtime budget matters. It runs the same broad constituents as `check-nosync`
after one sync, but uses a named bounded resource posture: the long workspace
CLI partition runs first, then independent remaining constituents run under
Make `-j 4` with partition-specific pytest worker limits. Ordinary `make check`
remains serial and resource-conservative by default.

Before adding a permanent ordinary test, PR closeout should answer whether the evidence is behaviour-class coverage, temporary characterisation, conformance evidence, or historical regression residue. If it is historical residue, preserve the failure mode in `test-knowledge-inventory.md`, Memory, Verification evidence, or an issue/PR note before deleting the executable test.

Use this compact inventory when changing these clusters:

| Category | Current examples | Policy |
| --- | --- | --- |
| Keep ordinary | Report closeout trust, startup/preflight routing, proof selection, lifecycle mutation safety, package install behaviour | Keep standalone when the behaviour is high-risk semantic workflow coverage or transport-specific adapter behaviour. |
| Merge | Repeated mode, section, or branch-shape checks with shared setup | Prefer scenario matrices or shared fixtures when assertions prove the same contract. |
| Convert | Stable generated command output, deterministic primitive behaviour, reusable operation output examples | Move to native owner cases, retaining public transport proof where it establishes a distinct boundary. |
| Delete | Obsolete compatibility fallbacks, duplicate generated-output assertions, dead fixture-shape regressions | Delete only after equivalent coverage is recorded in the replacement inventory. |

## Native and binding ownership

Rust owner tests prove portable semantics and effects. Root Python tests exercise
the native public boundary, artifact isolation and maintainer/provider mechanics.
Planning, Memory and Verification are core modules, not separately installed
Python distributions. Use their native owner scenarios for state preservation,
mutation safety and migration evidence. Generated operation parity and former
Python dispatch are not alternative product authorities.

## Contract Ladder

Prefer testing behaviour at the lowest level that proves the intended contract without preserving accidental implementation shape:

- Primitive conformance: deterministic execution units and target parity.
- Fragment or subflow behaviour: reusable workflow patterns such as lifecycle mutation, validation, report shaping, and output rendering.
- Operation composition: command-facing contracts assembled from primitives and fragments.
- Representative command black-box behaviour: user-visible compatibility, high-risk workflows, and transport behaviour.

When a bug belongs to a reusable fragment, add or extend a fragment or operation case before adding several command-specific regressions. When the behaviour is transport-specific, keep the target adapter test small and point behaviour truth back to the operation contract.

## Contract-Owned Cases

The preferred long-term direction is contract-owned conformance:

- Operational contracts own canonical input/output or input/error cases.
- Rust owns semantic admission, outcomes and effects; tooling only invokes it.
- Rust CLI, Python and Node provide the current public transport surfaces.
- Adapters normalise invocation, result extraction, exit or error shape, and capability reporting.

The runner should remain simple: load contract cases, select a target adapter, run the declared operation with declared input and fixtures, normalise the result, and compare it with expected output or expected error.

## Add, Merge, Convert, Or Prune

Add a new test when the behaviour is new, the failure mode is not already represented, and the right contract surface does not yet have an equivalent case.

Merge tests when several narrow regressions assert the same contract through slightly different fixtures. Prefer table-driven scenarios when the setup is shared and the expected behaviour is easy to compare.

Convert tests when a command-level regression really belongs to a primitive, fragment, operation, or contract-owned conformance case. Keep one representative command black-box test if user-visible behaviour or transport compatibility is the risk.

Prune only when stronger or equivalent coverage remains and the removed test preserves implementation detail, duplicate fixture shape, or obsolete behaviour rather than a meaningful contract.

Do not prune coverage for historically fragile lifecycle, planning, archive, proof, generated-package freshness, or report/closeout behaviour until an equivalent contract-owned case or scenario matrix exists.

## No-Prune Areas

Treat these areas as high-risk until a stronger replacement exists:

- Planning archive, closeout, and active-state mutation safety.
- Startup, preflight, implementation, proof, and report routing.
- Native artifact identity, generated interface freshness and public transport parity.
- Schema/reference docs and structured inventory checks.
- Package install and payload boundary behaviour.

High-risk does not mean "add another one-off test by default." It means the replacement must be explicit, equivalent or stronger, and easy to review.

## Current Follow-Through

The #1373/#1374 migration lanes established the contract-owned conformance
direction and the AW-side generated-command inventory. Treat
[Contract-owned test replacement plan](contract-test-replacement-plan.md) and
[AW contract test replacement inventory](aw-contract-test-replacement-inventory.md)
as retained records, not open ownership claims.

New reductions should use the current owner map: keep high-risk root workflow
proof where it is the narrowest evidence, keep portable semantic cases with the Rust owner and use thin public-binding
cases for transport parity, and use Verification proof decisions or dispositions when changing
ordinary tests would otherwise leave the reasoning in chat or PR prose.

## Lazy frontier regression boundary

Use the construction and transport classes in [decision-frontier.md](decision-frontier.md)
for changes to compact/carried resolution, owner detail selection or post-effect
continuation. Keep the existing exact-carriage authority journeys; count actual
optional builders rather than treating smaller rendered JSON as avoided work.
The proof procedure is the branch-heavy consumer. Do not add a per-owner or host
matrix when these distinct currentness/effect/projection classes cover the change.
