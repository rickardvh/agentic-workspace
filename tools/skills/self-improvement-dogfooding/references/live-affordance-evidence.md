# Current live affordance observation

Observed 29 September 2026. **Failed: the second session exhausted its budget.**
Artifact and authority checks passed. This observation does not satisfy #3710
or authorise parent-lane closeout.

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
  900 seconds maximum each; total run 1,307.098 seconds.
- Immutable Codex Sandbox template digest:
  `sha256:a68b972a59148c6359ade441387159033f6d196d48aef9dda06d2d4bb26eb41e`.
- Harness recipe/scorer/actor SHA-256 at execution:
  `b6698c8ebfdba2e743f1d12ac605dc78954b562b87bbc9cf3d40eab796b9fc35` /
  `7d1bc02802e1b74432bb0dd5d4ef40eaeed7b31b6b4534dd41ee74cb2206c2cc` /
  `649e3b682a2222e32c4f239bf3488a0bc1833a85ed731c4a35a516635c4fc2ca`.

## Observations and limits

The trusted fixed-subject observer retained 27 calls in each session. All four
observations are present: a routed restriction, a multi-owner action, that exact
offered action's committed effect, and fresh-session reentry. No repeated
unchanged rejection, contradictory route or internal-recovery attempt was
classified. Individual rejected calls and subsequent recovery remain in the result.

Preparation completed. In the resumed session, independently exported files
passed the requested migration and preservation checks. The installed subject
remained unchanged. The actor retired its managed scratch storage, then continued
trying to reconcile Planning; it lost carriage in later fresh calls and reached
the execution deadline without a final claim. The result therefore remains failed,
with claim honesty unobserved. Passing files do not establish a completed session
or sufficient retained continuation. No product cause is inferred from the timeout.

The named diagnostic checked a repaired export path. A deterministic valid tar
stream with large zero padding reproduced the earlier empty-diagnostic export
failure: waiting before draining the pipe could deadlock the producer. The repair
drains only bounded zero padding and reports deadline expiry. Valid, malformed and
oversized padding controls pass, and this live export succeeded. This supports the
repair but does not prove the cause of the earlier historical export failure.

Cleanup removed the sandbox. The first session reported 1,369,004 tokens; the
timed-out session's token total, cache accounting and marginal monetary cost are
unknown. The remaining live gate is a completed trusted exercise within its
declared budget. No provider matrix or repeat-until-green run was started.

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
| Repaired export diagnostic, second-session timeout | `7f5b6c451c28e36918ad93e83ce45439074e4edee75f897520f739de6dc799ae` |

The existing #3709 harness and #3710 evidence gate own these observations. The
49 consumer harness/scorer tests and current-evidence lifecycle controls support
the implementation; they do not replace live satisfaction or independent review.
