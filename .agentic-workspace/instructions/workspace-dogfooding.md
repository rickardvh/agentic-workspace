---
paths:
  - .agentic-workspace/**
  - src/agentic_workspace/**
  - packages/**
  - scripts/**
  - tests/**
  - docs/maintainer/**
checks:
  - requirement:typed_cli_selector_contract
  - requirement:proof_execution_integrity
  - requirement:direct_no_signal
  - requirement:selected_planning_read_budget
  - requirement:selected_planning_scaling_budget
  - requirement:invalid_selector_rejection_budget
  - requirement:selected_proof_residue_budget
  - requirement:total_completion_cost
  - requirement:query_shaped_operation
  - requirement:stronger_owner_correction
---

# Agentic Workspace dogfooding

Actively dogfood Agentic Workspace during maintainer and self-improvement work. Look for weak routing, friction, noise, avoidable rereads, unclear claim/proof boundaries, and opportunities to make agent work safer, cheaper, quieter, or more effective.

Fix immediate blockers when they are in scope. Route durable findings into narrow preliminary/draft GitHub issues with concrete evidence and the smallest useful intended outcome instead of leaving the learning only in chat.

Use the named repo requirements above as the durable acceptance boundary. Hard requirements constrain only their declared paths, tasks, and completion claim; measurable requirements reuse current source-owned evidence; guidelines influence preference without blocking unrelated work. The maintained rationale, thresholds, and disposition live in `docs/maintainer/repo-evidence-requirements.md#initial-dogfood-policy`.
