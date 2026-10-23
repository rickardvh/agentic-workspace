# Verification

Verification is AW's component for reusable checking procedures, saved test or
review results, and known gaps.

For when to use Verification, see the
[component guide](package/modules.md#verification). For choosing and interpreting
checks on your own work, see [Everyday use](everyday-use.md#check-the-result).

For ordinary work, follow the current `start` result. If Verification has
something relevant, AW returns the specific request or action needed. The
[native CLI catalogue](reference/cli-catalogue.md) lists the executable
commands.

Verification's implementation lives in
[`src/core/src/modules/verification/`](../src/core/src/modules/verification/). Repository
configuration and saved verification records live under
`.agentic-workspace/verification/` when that component is enabled.

A saved passing result supports only the code, inputs and environment it actually
checked. It does not by itself prove that the whole task is complete or that a
later change still passes.
