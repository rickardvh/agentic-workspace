---
paths:
  - .agentic-workspace/**
  - src/agentic_workspace/**
  - packages/**
  - scripts/**
  - tests/**
  - docs/**
  - crates/**
  - .github/**
read:
  - docs/maintainer/testing-strategy.md
protect:
  - .agentic-workspace/local/decision-point-intent/73a213e66cd48a33.json
---

# Workspace operating guidance

Start from the compact Agentic Workspace route before opening raw planning,
memory, verification, or configuration state. Use exact selectors and routed
owners before broad reads. Keep package boundaries explicit and do not treat a
successful focused action as proof of a broader completion claim.

Preserve the unresolved Planning decision-point source named above. Its bytes do
not yet have independently established source-owner custody/admission (#2970).
Do not infer ownership from its path, schema or inline owner strings. Remove or
revise this restriction only when that source-authority gate is actually resolved
and the repository owner admits the revised instruction. This rule supplies no
mutation, custody, or proof-success authority.

For changes to behavior, executable tests or ordinary CI, apply the testing strategy before
adding permanent evidence or choosing validation. Use its contract ladder,
add/merge/convert/prune rules, and test/CI delta disposition at closeout. This
includes tests embedded in Rust and package code. A material duplicate, temporary
batch taxonomy, or unjustified recurring cost must be resolved before presenting
the work for approval. Existing workspace-proof-selection and Verification remain
the proof owners; this instruction is repository review discipline, not a new
selector. Distinguish evidence design, current patch validation and permanent retention as
that strategy defines them. A fix or incident reproduction does not by itself
justify another permanent regression; inspect existing stable owner evidence
first. Closeout states why proof can stop or which named material risk requires
bounded escalation. Run broader proof only for that stated current claim.
