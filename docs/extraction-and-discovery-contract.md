# Extraction, Discovery, and Declarative Boundary

This contract defines the policy for identifying new capabilities, extracting them into packages, and maintaining the boundary between declarative and procedural state.

## 1. Discovery and Findings

### Setup Findings
- **Purpose**: Captures advisory findings during `init`, `setup`, or `doctor` passes.
- **Triage**: Findings should be triaged into:
  - **Dismiss**: Duplicate or out of scope.
  - **Planning Candidate**: Promotion to `TODO.md` or `ROADMAP.md`.
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

This monorepo maintains three distinct layers for package-related work:

| Layer | Purpose | Paths |
| --- | --- | --- |
| **Source** | Reusable logic and tests. | `packages/*/src/` |
| **Payload** | Files installed into a target repo. | `packages/*/bootstrap/` |
| **Operational** | Live surfaces used by this monorepo. | `AGENTS.md`, `.agentic-workspace/`, etc. |

### Default Rule
- Fix the authoritative layer (Source or Payload) first.
- Do not patch the root operational install alone if a package upgrade would overwrite it.
- Keep source and payload aligned before or alongside the root install.

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
