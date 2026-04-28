# Agent Aids Storage

Agent-created aids are reusable helpers that reduce recurring operating cost: scripts, skills, runbooks, prompts, checks, templates, wrappers, or small workflow shims.

This storage model is repo-, agent-, tool-, and language-agnostic. It defines ownership boundaries only; manifest, safety, discovery, and promotion rules are separate contracts.

## Storage Classes

### Local-Only

Root: `.agentic-workspace/local/integrations/<vendor-or-runtime>/`

Use this for machine-specific or runtime-specific helpers. Local-only aids are ignored by git, non-authoritative, optional, and safe to delete. They must not become required workflow state.

### Checked-In Candidate

Root: `.agentic-workspace/agent-aids/`

Use this for repo-shared aids that are still proving value. Suggested subfolders are `scripts/`, `skills/`, `runbooks/`, `prompts/`, `checks/`, and `templates/`.

Checked-in candidate aids are reviewable repo state. Put each aid in its own directory under the relevant subfolder and add `manifest.json` beside the aid files. The manifest kind is `agentic-workspace/agent-aid/v1`; it records type, status, scope, portability, owner, why it exists, when to use it, entrypoint, safety, validation, promotion, and retirement criteria.

Run `python scripts/check/check_agent_aids.py` or `make agent-aids` to validate checked-in aid manifests and ensure aid files are covered by nearby metadata.

### Promoted Repo-Native

Root: the host repo's ordinary command, check, skill, runbook, prompt, template, or documentation surface.

Use this when an aid is stable enough that candidate storage is no longer the right home. Promotion should make the aid discoverable through the promoted surface's normal route and should retire or shrink the candidate copy.

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
