# Instruction topology migration

This record is the closure map for issues #2624 and #2629. The authoritative ordinary path is the compiled operating decision; this document records what happened to the older generic control surfaces so they are not recreated as another phase model.

## SkillSpec topology

| Former contract | Final disposition | Preserved behavior |
| --- | --- | --- |
| `startup-to-work` / `workspace` | Removed. Startup reads the current operating decision and its typed `next_safe_action`; the startup SkillSpec remains a routed consumer contract. | Exact next action, forbidden effects, proof and completion boundaries, and bounded no-CLI fallback. |
| `work-to-planning` / `planning` | Domain-owned procedure. Planning is discoverable through the decision's skill/operation route, not a main-loop slot. | Planning mutation authority and active-owner protection remain in Planning's route decision and skill. |
| `work-to-proof` / `workspace.proof` | Domain-owned procedure plus clause effects. Proof selection remains specialized; evidence-before-claim constraints compile as `require` effects. | Required evidence, claim blocking, and typed repair routes. |
| `work-to-memory-residue` / `memory` | Domain-owned procedure. Memory contributes source-owned facts and a routed skill only when relevant. | Memory authority, freshness, promotion, and residue rules remain with Memory. |
| `proof-to-closeout` / `planning.closeout` | Domain-owned procedure plus clause effects. Closeout is selected by its owner; applicable workflow obligations compile to `require` effects on the completion claim. | Closeout trust, parent/lane claim boundaries, and explicit disposition requirements. |
| Generic `resolve-current-contract`, `act-through-route`, `reconcile-result` gates | Removed. These labels describe how to consume a decision; they are not machine gates or hook types. | The canonical skill still teaches the small loop without making it an authority peer. |

`module_slots`, `transition_gates`, and `next_safe_action.module_slot` are removed from the shipped schemas and runtime projection. Specialized owners are discovered from exact skill, operation, resource, and source-owner references.

## Generic mechanism subtraction

| Previous mechanism | Disposition |
| --- | --- |
| Scoped instruction routing | Specialized authoring sugar compiled to `surface`. |
| Skill recommendation | Advisory source projection compiled to `prefer`; it cannot grant permission. |
| Assurance/evidence requirement | Source-owned requirement compiled to `require` with an evidence satisfier. |
| Claim restriction | Compatibility input compiled to `restrict`; blocked-claim output is derived from the clause result. |
| Workflow obligation `stage + force + commands` | Workspace-config authoring remains temporarily compatible. Applicability is compiled to `surface` or completion-claim `require`; command strings remain owner metadata and never become action identity. |
| `task_posture_packet` allowed/forbidden/proof/closeout fields | Bounded compatibility projection. They remain selector/detail output for existing consumers while the operating decision owns action and claim authority; removal is permitted after those consumers use decision/clause fields directly. |
| Module startup/report/closeout metadata | Legacy module descriptors remain a compatibility path. Public module capabilities and contributions are the admitted extension contract; out-of-tree conformance proves no first-party identity branch is required. |

## Removal boundary

No new consumer may depend on a module slot, SkillSpec transition gate, or command string as semantic action identity. Compatibility fields may only project consequences already owned by a source fact, clause effect, capability, or typed operating decision. Tests cover topology absence, workflow-obligation effect compilation, hard restriction no-divergence, generated/payload parity, direct work, and an out-of-tree module.
