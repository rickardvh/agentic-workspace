---
paths:
  - .agentic-workspace/**
  - src/**
  - tests/**
  - docs/maintainer/**
  - tools/skills/**
checks:
  - requirement:typed_cli_selector_contract
  - requirement:proof_execution_integrity
  - requirement:config_orthogonality_constructibility
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

During applicable repository work, treat material AW-caused retries, rereads,
redundant proof, route reversal, workaround or protocol work, noisy output, and
repeated human steering as observations even when the original task can succeed.
Judge material cost and attribution from the current evidence; neither command
counts nor eventual success determine whether a finding exists.

Before evidence or context disappears, nominate one bounded existing `material`
observation with truthful provenance through ordinary `start`, keeping the task
unchanged. Follow native activation to
`tools/skills/self-improvement-dogfooding/procedure.md` for bounded repair,
evidence/conformance repair, a distinct issue/follow-up, or human direction for a
genuine product-shaping choice. Do not require predicting recurrence or proving a
defect before nomination. Existing owners retain write, proof and publication
authority; consumer upstream reporting and its consent remain separate.

Before closeout, disposition material signals actually encountered as fixed,
already-owned/routed, deliberately dismissed/no-retention, or unresolved. A weak
cosmetic annoyance can be dismissed without creating an issue or Memory note.
When no material signal occurred, continue quietly: no extra scan, retained record
or AW call solely to establish its absence. Return to the original task after
bounded triage.

Use the named repo requirements above as the durable acceptance boundary. Hard requirements constrain only their declared paths, tasks, and completion claim; measurable requirements reuse current source-owned evidence; guidelines influence preference without blocking unrelated work. The maintained rationale, thresholds, and disposition live in `docs/maintainer/repo-evidence-requirements.md#initial-dogfood-policy`.
