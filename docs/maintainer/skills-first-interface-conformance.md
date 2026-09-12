# Skills-first interface conformance

PR #3228 is the cumulative C53 interface lane under #3207. This report separates
implemented behavior from parent completion and platform evidence.

## Source and derivation

`AGENTS.md` contains checkout preparation and a small managed pointer to
`.agentic-workspace/skills/workspace-startup/SKILL.md`. The skill owns procedure;
instructions/config own policy, domain records own state/evidence, and Rust owns
exact semantics and effects. `WORKFLOW.md` is a compatibility pointer.

`scripts/generate/generate_agent_interface.py` derives shipped payload bytes from
the exact source paths declared in `workspace_surfaces.json`. Its `--check` mode
and the ordinary CI guard reject drift. The Rust build embeds those payloads.
The source maintenance bootstrap and ownership generators produce the same
skills-first shape. Lifecycle tests cover init, repeated upgrade, uninstall,
repository prose preservation, and retirement of the duplicate generic skill.
Retirement accepts only its recorded package hash; edited, malformed or linked
sources remain for manual review. Uninstall removes only an exact managed pointer.

These are source maintenance lifecycle tests, not a claim that the former Python
host is an installed public runtime. Public native install/upgrade ownership and
installed platform admission are outside this lane's evidence.

## Executable route and consumer evidence

`tests/test_skills_first_interface.py` uses fresh temporary repositories and the
real native CLI, JSON core, Python binding and TypeScript/Node binding. It proves:

- tiny bootstrap plus canonical skill, a direct query, and an exact Configuration
  request/answer/action mutation with a committed outcome and no effect retry;
- direct known-leaf selection returns current procedure references in full,
  compact and carried views, without ancestry traversal or another detail call;
- the shared resolved route fact validates against
  `semantic_task_routes.schema.json#/$defs/resolved_task_fact` on every surface;
- instructions and Memory consume that fact; task words alone activate neither;
- fresh processes and same-work carriage preserve applicability, while changed
  work/catalogue invalidate selection and changed procedure bytes invalidate old
  detail carriage. Catalogue identity and fresh procedure-byte identity have
  separate lifetimes. A route never attests that old procedure bytes remain current;
- no read-only local residue or new action/proof authority is created.

The existing `test_public_semantic_route_*` tests in `test_shared_core.py` exercise
the shared typed selection request, bounded complete pagination, cross-surface
equality, stale work/source/removed routes and forged authority rejection.
`test_repo_decision_consumes_public_route_without_path_match` proves the repository
decision owner consumes the same route mechanism (including its Memory archive
fallback), and exact path scope still applies when the semantic route is stale.
The native instruction and former-route suites cover real repository procedures,
custom registry admission, missing procedure refs, and preserved former state.
This reuses the existing Rust route owner; there is no second selector or session
registry. The legacy persisted-input schema remains distinct from the normalized
currentness result, and neither is an effect authority.

The fixtures are executable consumer journeys, not a controlled model-quality
experiment, release installation matrix, independent review, or merge readiness.

## Measured interface inventory

Baseline: `efc18f52719bb69f652ef4bf2fa2c4826f05619b`, before the seed interface
commit. Counts are UTF-8 bytes with LF newlines; the bootstrap count includes only
its managed fence. Compare `git show <baseline>:<path>` with the current source.

| Generic surface | Before | After |
| --- | ---: | ---: |
| Managed root bootstrap | 3,046 | 558 |
| Canonical startup skill | 9,329 | 8,706 |
| Duplicate operating-loop skill | 5,418 | 0 |
| Workflow compatibility surface | 2,429 | 661 |
| Total declared generic text | 20,222 | 9,925 |

The bootstrap shrinks 81.7%; the generic text inventory shrinks 50.9%. The ordinary
bootstrap plus main skill is 9,264 bytes; the compatibility pointer need not be
loaded. These are source inventory counts, not measured model tokens or proof that
every historical journey read every surface. Once a current known leaf is selected,
the new full/compact/carried result exposes its procedure refs in that response;
the previous implementation required an additional discovery request.

## Bounded no-runtime disposition and closure honesty

#3217 receives the bounded C53 disposition permitted by #3207. The same main skill
uses `OWNERSHIP.toml` for selective repository-source orientation. It requires exact
source paths/revisions, keeps runtime/local/live facts unknown, and grants no
managed mutation, proof or completion authority. Missing, stale, malformed or
insufficient sources narrow conclusions rather than synthesize an operating decision.

This does not demonstrate the full #3217 GitHub/tree-only black-box journey with
no executable dependencies, all selective owner journeys, or its full revision and
recovery matrix. That issue stays open. #3223 remains the broader parent outcome.
#3224 and #2930 have the executable C53 evidence above; wider fresh-agent burden
and full issue completion are not inferred from these fixtures. Leave their
closure to full acceptance reconciliation. This PR remains draft at the user's
request; hosted merge-sufficiency is draft-gated, and independent review is separate.
