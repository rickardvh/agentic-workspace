# Agent Aids Storage

Agent-created aids are reusable helpers that reduce recurring operating cost: scripts, skills, runbooks, prompts, checks, templates, wrappers, or small workflow shims.

This storage model is repo-, agent-, tool-, and language-agnostic. It defines ownership boundaries only; manifest, safety, discovery, and promotion rules are separate contracts.

## Creation Affordance

Agents may create bounded aids for themselves when doing so reduces repeated work, parsing cost, handoff cost, or error risk. This is an expected use of the package, not an exception. Common triggers are repeated command bundles, noisy command output where only pass/fail plus a failure tail is needed, handoff or closeout steps reconstructed across turns, or a small template, prompt, runbook, wrapper, or shim that would prevent rediscovery.

Create the smallest aid that removes the friction:

- Use local-only storage for machine-specific or runtime-specific aids.
- Use checked-in candidate storage for repo-shared aids that are still proving value.
- Prefer checked-in candidate aids when the solution benefits any agent working in the repo, is portable enough to review and run in ordinary repo environments, or captures repo-specific workflow knowledge that should survive machines and sessions.
- Prefer local-only aids when the solution depends on a specific agent runtime, subscription, account, credential, path, shell setup, or private machine-local state.
- Promote only after repeated usefulness or clear repo-general value.
- Keep candidate and local aids advisory; they must not silently become required workflow.
- Preserve evidence with compact agent-facing output plus inspectable logs, artifacts, manifests, or source files.

The existing root `Makefile` demonstrates the preferred command-wrapper pattern:

```make
COMPACT_RUN = uv run python scripts/check/run_compact_command.py
```

`scripts/check/run_compact_command.py` prints compact success output such as `[ok] <label> (<duration>)`, prints a tailed failure or timeout on error, and stores full logs under `scratch/command-logs`. Reuse this runner, or the same compact-output/full-log pattern, when a recurring command is too noisy for ordinary agent loops. For long checks, pass `--timeout-seconds <seconds>` with a value below the outer tool timeout so the runner can emit compact timeout evidence, write a log, and stop the command tree before the shell is killed externally.

## Storage Classes

### Local-Only

Root: `.agentic-workspace/local/integrations/<vendor-or-runtime>/`

Use this for machine-specific or runtime-specific helpers. Local-only aids are ignored by git, non-authoritative, optional, and safe to delete. They must not become required workflow state.

### Checked-In Candidate

Root: `.agentic-workspace/agent-aids/`

Use this for repo-shared aids that are still proving value. Suggested subfolders are `scripts/`, `skills/`, `runbooks/`, `prompts/`, `checks/`, and `templates/`.

Checked-in candidate aids are reviewable repo state. Put each aid in its own directory under the relevant subfolder and add `manifest.json` beside the aid files. The manifest kind is `agentic-workspace/agent-aid/v1`; it records type, status, scope, portability, owner, why it exists, when to use it, entrypoint, safety, validation, promotion, and retirement criteria.

Use `authority_boundary` when an aid is provider-specific, tracker-specific, or close to workflow routing. Advisory aids should declare `runtime_authority: none` or `advisory-only` and name the owner surface for behavior-relevant facts, such as external-intent evidence, Planning state, Memory, docs contracts, or host config. This makes the aid's boundary explicit without making the aid a package-owned policy source.

Run `python scripts/check/check_agent_aids.py` or `make agent-aids` to validate checked-in aid manifests and ensure aid files are covered by nearby metadata.

Run `agentic-workspace report --target . --section agent_aids --format json` to list checked-in and local-only aids without scanning the repo. Run `agentic-workspace skills --target . --task "<task>" --format json` when the question is task-specific aid or skill recommendation.

Executable aid types are `script` and `check`. They must declare nonblank validation commands that reference the aid entrypoint, not only an absent-reason. Runtime-specific or platform-specific checked-in aids must include `portability_justification`; platform-specific repo-shared or module-owned aids also need `checked_in_scope_justification` explaining why they are checked in instead of local-only. Repo-general validation should prefer cross-platform wrappers. Aids that write to the repo, use the network, or perform destructive actions must set `requires_review = true`, and `hidden_required_workflow` must be false. Candidate and advisory aids are not canonical proof routes or required workflow entrypoints; `proof_role = "canonical-proof"` is reserved for promoted aids.

### Promoted Repo-Native

Root: the host repo's ordinary command, check, skill, runbook, prompt, template, or documentation surface.

Use this when an aid is stable enough that candidate storage is no longer the right home. Promotion should make the aid discoverable through the promoted surface's normal route and should retire or shrink the candidate copy. Candidate manifests declare `promotion.target_kind`, `promotion.target`, `promotion.discovery_route`, `promotion.trigger`, and `promotion.retention_after_promotion`; supported target kinds are command, check, skill, runbook, prompt, template, module-component, and docs-contract. Repo-shared executable aids that become canonical proof must be cross-platform.

### Package-Owned

Root: package source or installed package payload surfaces.

Use this only for aids that are part of the shipped package. Host-repo custom aids do not belong here.

### Source-Checkout-Only

Root: maintainer tooling in the package source checkout.

Use this for package-maintainer aids that should not appear as host-repo workflow requirements.

## Boundary Rules

- Local-only helpers stay local and non-authoritative.
- Candidate aids stay under `.agentic-workspace/agent-aids/` until promoted or retired.
- Promoted aids move to the strongest ordinary repo-native surface.
- Package-owned aids are shipped product surfaces, not host-repo custom aids.
- Source-checkout-only maintainer aids must not be required in ordinary host repos.
