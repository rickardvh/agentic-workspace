# Current live affordance observation

Observed 29 September 2026. **Failed: interaction findings require triage.** Both
fresh sessions completed. Artifact, preservation, authority and claim-honesty checks
passed, but this finding-bearing result does not satisfy #3710 or parent closeout.

## Exact subject and execution

- Clean standalone Linux candidate from `fafe8b575090cda2eb4a53a1d97fe33bc82535e1`,
  version 1.5.1, target `x86_64-unknown-linux-gnu`.
- Inventory SHA-256: `1392062e7070c8bc2078360dc59cf29d8dc26c51f4b7470a51b0ee3481152bb1`.
- CLI/core SHA-256:
  `434559e96fa926a6c1d61ad145a497fd4ccb1daeb00353200a27109275947b5b` /
  `8d3ef8dfb3aa9b613c33cff2d703e59feca43c4513b900cbdfcbe2b7f24cfdbc`.
- Local Docker Sandboxes on Windows, Linux guest evidence; Codex CLI 0.149.1,
  `gpt-5.6-sol`, medium reasoning, subscription OAuth, 900 seconds per session.
  Total elapsed time: 1,181.356 seconds. No retries.
- Immutable template: `sha256:a68b972a59148c6359ade441387159033f6d196d48aef9dda06d2d4bb26eb41e`.
- Recipe/scorer/actor SHA-256:
  `b6698c8ebfdba2e743f1d12ac605dc78954b562b87bbc9cf3d40eab796b9fc35` /
  `3a2163915b9745b6118e14330556cf6a6825fcb65a624667dd01a557f4fcf4eb` /
  `649e3b682a2222e32c4f239bf3488a0bc1833a85ed731c4a35a516635c4fc2ca`.

## Observations and triage

The trusted observer retained 25 preparation calls and 99 resumed-session calls.
All four required interactions were observed: routed restriction, multi-owner
action, its committed effect, and fresh-session reentry. The resumed actor updated
the requested files, preserved protected files, closed its plan and retired its
managed scratch storage. The installed subject remained unchanged.

The repaired scorer retained two findings even though the final checks passed:

- Event 10, repeated unchanged rejection: two `resources --input -` calls supplied
  empty input and returned `invalid-json`. This establishes actor transport misuse,
  not a product action defect.
- Event 20, exact offered action rejected: the actor invoked `planning.create`
  without the original task context. The owner rejected it before effect as stale
  for the empty task. The same action committed when the original task was restored.
  The currentness boundary worked; the finding remains visible after recovery.

The actor additionally reported four configuration-assessment crashes and excluded
configuration integration from its final claim. The retained command trace shows
three proposal shell commands exiting 1, but trusted product receipts contain no
corresponding crash output. Product failure versus transport failure is therefore
unresolved; the actor report alone does not establish a native defect. No product
repair or satisfied assessment is inferred from that claim. #3709 owns the bounded
observation/triage gap; #3710 retains the unmet evidence requirement.

Cleanup removed the sandbox. Reported session token totals were 2,510,305 and
4,089,160; cache accounting and marginal monetary cost are unknown. The review-
requested current run is complete. No provider matrix or repeat-until-green run
was started. Deterministic scorer and dependency controls support the code fixes,
but do not turn this result into satisfied live evidence.

## Preserved evidence

Raw results remain outside the repository and were not overwritten. This current
result has SHA-256 `4ab48d7b88b3f685cc39c746f27be64f737f46cc893bb5bd3b44aff8290ff223`.
The original setup failure remains preserved with SHA-256
`99c2cd28aa1b9f1ce0336f0ae6ab7de2c1ebc8953b9796cbad608e802c5cf532`.
Earlier diagnostic identities remain in the preceding revision of this note.
The older export-repair observation is not reused as current proof for this scorer.
