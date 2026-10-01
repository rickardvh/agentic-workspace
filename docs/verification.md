# Verification

Verification is AW's component for reusable checking procedures, saved test or
review results, and known gaps.

The full component documentation lives in
[packages/verification/README.md](../packages/verification/README.md). This page
remains a short public link target rather than a second manual.

For ordinary work, follow the current `start` result. If Verification has
something relevant, AW returns the specific request or action needed. The
[native CLI catalogue](/docs/reference/cli-catalogue.md) lists the executable
commands.

Verification's implementation lives in `packages/verification/`. Repository
configuration and saved verification records live under
`.agentic-workspace/verification/` when that component is enabled.

A saved passing result supports only the code, inputs and environment it actually
checked. It does not by itself prove that the whole task is complete or that a
later change still passes.
