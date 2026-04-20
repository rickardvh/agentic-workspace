# Extraction, Discovery, and Declarative Boundary

This contract defines the policy for identifying new capabilities, extracting them into packages, and maintaining the boundary between declarative and procedural state.

## 1. Discovery and Findings

### Setup Findings

- **Purpose**: Captures advisory findings during `init`, `setup`, or `doctor` passes.
- **Triage**: Findings should be triaged into:
  - **Dismiss**: Duplicate or out of scope.
  - **Planning Candidate**: Promotion to `todo.active_items` or `roadmap` in `.agentic-workspace/planning/state.toml`.
  - **Durable Residue**: Capture in Memory or canonical docs.
- **Storage**: Optional findings live in `tools/setup-findings.json`. This file is transient and should be removed once findings are promoted or dismissed.

### Skill Discovery

- Use for identifying reusable agent skills and registry-backed workflows.
- Skills should be discovered and registered rather than remaining ad hoc script snippets.

---

## 2. Extraction Policy

Extract a new package only when:

- **Stable Boundary**: The ownership is clear and doesn't overlap with existing modules.
- **Explicit Seams**: The capability exposes manifests, schemas, or generated artifacts.
- **Independent Utility**: The package is useful on its own in selective-adoption repos.
- **Maintenance Friction**: Dogfooding shows that staying in the root or a module is causing friction.

### Workspace Thinness

- New module-specific logic belongs in the package CLI first.
- The root workspace layer only centralizes composition, reporting, and shared lifecycle orchestration.

---

## 3. Declarative Contract Boundary

### Purpose

- Keep stable metadata (selectors, schemas, route IDs) inspectable without reading Python code.
- Avoid turning the workspace into a heavy workflow engine.

### Classification Rule

- **Declarative**: Data is stable, versioned, and inspectable (e.g. selector metadata, proof route IDs).
- **Procedural**: Logic depends on live repo state, dynamic branching, or complex reconciliation.
- **Derived**: Payload is assembled from stable manifests plus live state (e.g. `agentic-workspace report`).

---

## 4. Source, Payload, and Install Boundaries

This monorepo maintains four distinct layers to separate the shipped product from operational usage and repo-local configuration:

| Layer | Purpose | Paths | Direction of Change |
| --- | --- | --- | --- |
| **Source Code** | Procedural Python logic, CLI commands, and installer logic. | `packages/*/src/` | Authority for tool behavior. |
| **Shipped Product** | Authoritative contracts, templates, and default skills (the "Bootstrap"). | `packages/*/bootstrap/` | **Primary Source of Truth** for shipped content. Edit here first. |
| **Installed Product** | The operational installation of the shipped product into this repo. | `docs/`, `AGENTS.md`, `.agentic-workspace/planning/state.toml`, etc. | **Dogfooding layer.** Update via `upgrade` command after editing the Payload. |
| **Repo-Specific Files**| Metadata unique to this monorepo's identity, build, and environment. | `pyproject.toml`, `README.md`, `Makefile` | **Local configuration.** Entirely separate from shipped logic. |

### Operational Hygiene

- **Edit Payload First**: Changes to distributed contracts (e.g., `docs/*-contract.md`) must be made in the `packages/*/bootstrap/` payload.
- **Upgrade to Dogfood**: After editing the payload, run the package's `upgrade` command (e.g., `uv run agentic-planning-bootstrap upgrade`) to apply the changes to the monorepo root.
- **Template Separation**: To prevent confusion, generic tracking files in the payload are named with a `.template.md` suffix (e.g., `TODO.template.md`). The installer strips this suffix during deployment to ensure the target repo receives standard operational filenames.
- **Do not patch root alone**: Do not patch the root operational install alone if a package upgrade would overwrite it or if the change is intended for distribution.

---

## 5. Ownership Tests

| Component | Authority |
| --- | --- |
| **Memory** | Durable knowledge (facts, decisions, failure modes). |
| **Planning** | Active execution state (tasks, milestones, next actions). |
| **Routing** | Guidance on what to read, trust, and run. |
| **Checks** | Liveness and drift validation. |
| **Workspace** | Lifecycle orchestration and module composition. |

---

## 5. Relationship to Tooling

- `agentic-workspace setup --target ./repo --format json`: Discovery entrypoint.
- `scripts/check/check_contract_tooling_surfaces.py`: Validation for declarative manifests.
