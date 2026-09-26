---
routes:
  - github/pr/review
read:
  - .agentic-workspace/memory/repo/mistakes/recurring-failures.md
use:
  - pr-review-recheck
---

# Repository PR custody and review

If you implemented or materially changed a PR, do not review or approve it
yourself and do not spawn or direct a reviewer to do so. Mark it `ready for
independent review`. Continue other authorised implementation work, including
remaining stacked PRs; independent review is not a gate on that work unless
explicitly required by a dependency or the user. Stop when the authorised
implementation work is complete. Leave review and approval to an externally
initiated reviewer using `tools/skills/pr-review-recheck/SKILL.md`.

Issue shaping and ordinary review feedback do not constitute implementation
custody. Selecting this route grants no review, approval, merge, proof or
completion authority. The review procedure decides whether the current actor
is eligible; implementation actors leave the review pending.
