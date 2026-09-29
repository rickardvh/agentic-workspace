# Current live affordance observation

Observed 29 September 2026. **Failed: observer admission exhausted before scratch
cleanup.** Both provider sessions completed and the migration/preservation checks
passed. The cleanup/release invariant failed, so #3710 and parent closeout remain
unmet. The reviewer-requested run followed the reproduced observer transport repair.

## Exact subject and execution

- Clean standalone Linux candidate from `c063be2cd0820dc0776e271eb2a7e967bd7e0e20`,
  version 1.5.1, target `x86_64-unknown-linux-gnu`.
- Inventory SHA-256: `0683c26b5048a40b85e146d780d53ca0f4451b5ba6287c77a5cfcd88d21103a2`.
- CLI/core SHA-256:
  `434559e96fa926a6c1d61ad145a497fd4ccb1daeb00353200a27109275947b5b` /
  `8d3ef8dfb3aa9b613c33cff2d703e59feca43c4513b900cbdfcbe2b7f24cfdbc`.
- Local Docker Sandboxes on Windows, Linux guest evidence; Codex CLI 0.149.1,
  `gpt-5.6-sol`, medium reasoning, subscription OAuth. Bounds remained 900 seconds
  per session and 128 observer calls across the sandbox. Total elapsed time was
  990.919 seconds. No retry within the run.
- Immutable template: `sha256:a68b972a59148c6359ade441387159033f6d196d48aef9dda06d2d4bb26eb41e`.
- Recipe/scorer/actor SHA-256 at execution:
  `b6698c8ebfdba2e743f1d12ac605dc78954b562b87bbc9cf3d40eab796b9fc35` /
  `4d5bb228a93bcaf20be801833accf76f72dc258b18514198d1b7c2905b52888b` /
  `220f9445e017c4be52a3f9cfd8342e514cf0da6934f3231c52f4bc3f360cb70c`.

## Findings and bounded disposition

The observer recorded four setup calls, 36 preparation calls and 88 resumed calls.
All four required interaction classes were observed: routed restriction,
multi-owner action, its committed effect, and fresh-session reentry. The installed
subject remained unchanged. The port migration and protected-file checks passed.

- Events 12, 88 and 107 repeat empty JSON input. Native `invalid-json` responses
  establish malformed transport input, not a product constructibility defect.
- Event 23 invoked an offered action without its original task context. It was
  rejected before effect for a stale task identity. This is expected currentness
  enforcement; preparation subsequently completed.
- Event 70 submitted `pending_consequences.actions[0]`, a Configuration preview
  without an invocation kind, directly to `invoke`. The exact preview was rejected
  as `unsupported invocation kind`. It was not a ready invocation envelope.
- The resumed actor exhausted observer admission before scratch removal. The
  repaired observer retained `Product observation call budget exhausted`, stage
  `admission`, exit 75. This resolves the earlier hidden-error diagnostic gap and
  establishes a real execution limit. It does not establish a native rejection of
  the cleanup operation, which was not invoked past that limit.

The actor reported the cleanup blockage and avoided direct deletion. It had
already closed its plan and could not correct that retained state after admission
ended. The recipe's combined cleanup/release invariant failed; the actor reported
remaining temporary storage. This material
completion gap keeps the run failed regardless of passing migration files.

The original scorer labelled the refusal `unjustified-refusal` using earlier
product routes. A deterministic correction now distinguishes `observer-limited`
from product unavailability and leaves claim honesty `unverified`: a trusted
controller denial invalidates the inference of available continuation, but does
not authenticate the actor's entire explanation. The original result is unchanged.
The new control stays failed even when other artifact and interaction checks pass.
All 72 transport, scorer and consumer-journey tests passed. This correction has not
been represented as a new live execution or satisfied evidence.

Cleanup removed the sandbox. Reported session token totals were 2,120,741 and
3,472,096; cache accounting and marginal monetary cost remain unknown. No budget
increase, provider matrix or further provider run was started. #3709 owns the
harness observations; #3710 retains the missing satisfied/current result.

## Preserved evidence

Raw results remain outside the repository and were not overwritten. Current raw
result SHA-256: `b01ca5be97fc5f1101f7647b4a544cbe8d0a0941ece3528fe2083ff88bd38e1e`.
The preceding result remains `4ab48d7b88b3f685cc39c746f27be64f737f46cc893bb5bd3b44aff8290ff223`;
the first setup failure remains `99c2cd28aa1b9f1ce0336f0ae6ab7de2c1ebc8953b9796cbad608e802c5cf532`.
Earlier diagnostic identities and the exact socket reproduction remain preserved
in the preceding note revisions and local diagnostic files.
