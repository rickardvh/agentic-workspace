# Current live affordance observation

Observed 29 September 2026. **Failed: final repository export unavailable.**
This observation does not satisfy #3710 or authorise parent-lane closeout.

## Exact subject and execution

- Linux `x86_64-unknown-linux-gnu`, standalone candidate from
  `4d4b62db88fd75792794a4cf5dd0405d0654b61f`, version metadata 1.5.1.
- Candidate inventory SHA-256:
  `2bb7ae74485320c26a5feaa14d4652763683d5b6ecc52a89d566b5c2ad17e380`.
- CLI/core SHA-256:
  `434559e96fa926a6c1d61ad145a497fd4ccb1daeb00353200a27109275947b5b` /
  `8d3ef8dfb3aa9b613c33cff2d703e59feca43c4513b900cbdfcbe2b7f24cfdbc`.
- Local Docker Sandboxes on Windows; Linux guest evidence. Codex CLI 0.149.1,
  `gpt-5.6-sol`, medium reasoning, subscription OAuth. Two fresh sessions,
  900 seconds maximum each; total run 1,241.165 seconds. Both sessions completed.
- Immutable Codex Sandbox template digest:
  `sha256:a68b972a59148c6359ade441387159033f6d196d48aef9dda06d2d4bb26eb41e`.
- Harness recipe/scorer/actor SHA-256 at execution:
  `be9fd8f683e331561847da78dcb0021030f0c33c220a24c58c96f6b3f66d478e` /
  `c9e1af4df50220d13b17de604e31394a4027a9c7f78ef9143ac62aade5852757` /
  `649e3b682a2222e32c4f239bf3488a0bc1833a85ed731c4a35a516635c4fc2ca`.

## Observations and limits

The trusted fixed-subject observer retained 66 and 37 calls. Rescoring those
receipts with the corrected owner count observes a routed restriction, an action
combining its acting owner with another source owner, an exact offered action's
committed effect, and fresh-session reentry. There are no classified repeated
unchanged rejections, contradictory routes or internal-recovery attempts.
Individual stale/context rejections and subsequent recovery remain in the result.

The scorer correction includes the action's `source_owner` in the owner union;
it still requires the committed call to match a previously offered action hash.
The rescore is deterministic and makes no additional provider call.

The final export and its recovery attempt returned `Consumer export failed (1)`
without a diagnostic. Its cause is unknown. Actor claims say the migration and
storage retirement completed, but independent final-file and preservation checks
are unavailable. Missing exported files establish neither an authority violation
nor a false completion claim. The harness now reports those judgments as unknown
or unverified and keeps the run failed.

Cleanup removed the sandbox. Provider-reported token totals were 3,711,302 and
3,513,707; cache accounting and marginal monetary cost are unknown. No provider
matrix or further live retry was run. The remaining gate is an independently
exported, fully checked live result; do not close #3710 from these receipts alone.

## Preserved evidence identities

Raw results remain outside the repository. The first setup failure was preserved;
diagnostics used separate files for the frozen-dataclass scoring bug, incomplete
fixture composition, and corrected fixture. No result was overwritten.

| Result | SHA-256 |
| --- | --- |
| First setup result, no session | `99c2cd28aa1b9f1ce0336f0ae6ab7de2c1ebc8953b9796cbad608e802c5cf532` |
| Initial live diagnostic, scoring exception | `c1a4637e07d22ae16d9b4d2b432979b47adab7a6b37800d006d26027fd6fc110` |
| Corrected scorer, incomplete multi-owner fixture | `862f97882c107ed640a03b643695ff24636988e0d2dd2b1954a7aee31b719168` |
| Corrected fixture, failed final export | `3814ffbc0e52881419817ae736af30f4a28810ceae63a9822fe5a9647eaa4b1a` |
| Deterministic receipt rescore | `edb33a772779be796c5e87b3f3d0de0da8f40bb0741e13078179f84e42e07eb3` |

The existing #3709 harness and #3710 evidence gate own these findings. The
mechanism tests cover absent/current/stale/expired assessments and honest
failed/unknown publication. Those tests do not replace live satisfaction or
independent review.
