# Planning Decompositions

Use decomposition records for epic-shaped requests before implementation lanes exist.

An epic is a work-shape classification, not a freehand artifact type. A `planning-decomposition/v1` record captures the larger intended outcome, parent acceptance target, candidate lanes, dependency and parallelization assumptions, and high-level proof expectations. Ready implementation slices move into `.agentic-workspace/planning/execplans/*.plan.json`; this directory should not carry lane execution journals.

Use `parent_acceptance` to keep the user's full original intent separate from slice mechanics. Each lane should state how it advances the parent, what parent intent remains, and whether its proof is slice-only, parent-closing, or requires human confirmation.

Use the current native Planning owner to create or change managed decomposition records when product shaping is needed. The template describes record structure; it does not grant write or promotion authority.
