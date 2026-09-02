---
routes:
  - github/pr/review
read:
  - .agentic-workspace/memory/repo/mistakes/recurring-failures.md
use:
  - pr-review-recheck
---

# Repository PR Review

This route makes the repository's PR-review eligibility procedure and recurring-failures anti-trap relevant. Selecting it does not grant review, approval, merge, proof, or completion authority. The `pr-review-recheck` procedure decides whether the current actor is eligible; implementation actors must obtain a distinct external reviewer.
