# Contribute to AW

Use this guide to change Agentic Workspace itself. To configure AW in another
project, use the [user guide](../index.md). Agents contributing here must also read
[AGENTS.md](../../AGENTS.md) and the applicable repository instructions.

## Prepare a checkout

You need Git, the Rust toolchain pinned by `rust-toolchain.toml`, Python and `uv`.
Node is needed for the TypeScript binding and cross-language checks. The
[Rust toolchain guide](rust-toolchain.md) explains the compiler requirement.

```bash
git clone https://github.com/rickardvh/agentic-workspace.git
cd agentic-workspace/
make setup
cargo build --locked --workspace --bins
```

`make setup` synchronizes the shared environment and installs this checkout's Git
hooks. The Cargo command builds both native executables; keep them together.
Rebuild after changing Rust code or bundled contracts/resources. Imports must not
silently build Cargo or fall back to the former Python command host.

The root dependency lock covers the source workspace. Prefer its frozen setup
rather than refreshing dependencies as a side effect of unrelated work.
[Maintainer commands](maintainer-commands.md) lists focused setup and checking commands.

## Find the right implementation

Start with the behavior being changed, then locate its responsible component:

| Change | Start here |
| --- | --- |
| Current context, authorization, state or effects | `crates/agentic-workspace-core/` |
| CLI options or forwarding | `crates/agentic-workspace-cli/` and the native CLI contract |
| Python / TypeScript transport | `bindings/python/` / `bindings/node/` |
| Human instructions and examples | The relevant user, reference or contributor page |
| Generated schemas or catalogues | Their named source contract, not the generated output |
| Repository-maintainer workflow | `tools/skills/` and its current procedure |

Read the [architecture](../architecture.md) when a change crosses those boundaries.
The `packages/` trees and other Python source retain maintenance/development work;
do not infer installed APIs from their presence. Current package topology is
specified in the [distribution reference](native-release-topology.md).

Repository state under `.agentic-workspace/` is not freehand implementation scratch.
Use the responsible AW operation for interpreted state and use the canonical source
for generated or packaged material. A change to README or another declared intent
source needs its source reconciliation on the introducing PR, not a later repair.

## Make a bounded change

Describe the problem and expected result before choosing a mechanism. Keep the
patch independently understandable: the relevant implementation, documentation
and present-tense evidence should agree on what it establishes.

For documentation, [write for the reader's next question](../documentation-status.md).
Introduce purpose and subject before specialized terms; separate examples from
general behavior. For runtime work, preserve the agent's judgment and the current
source ownership rather than adding a competing control path.

If the work uses Planning, update its progress through Planning's owner. Do not
create plans or memory entries merely to demonstrate use of AW. Preserve useful
continuation before stopping; one-off narration can stay in the PR or Git history.

## Validate the claim

Read the [testing strategy](testing-strategy.md) before changing behavior, tests or
CI. Name the failure classes the patch could introduce, reuse current evidence,
and choose the lowest sufficient stable contract to test. An incident does not
automatically justify another permanent regression.

Typical starting points are focused Cargo tests for shared behavior, focused
Python or Node tests for transport, and links/examples/freshness checks for docs.
Use [Maintainer commands](maintainer-commands.md) for exact commands. Changes to
contracts or bundled resources also require the applicable generated/payload
refresh and validation.

The ordinary hosted job is **Merge sufficiency**. Broad artifact, runtime-matrix
and support-promotion proof is a separate explicit escalation; do not call skipped
jobs passing. Record the commands, subject and limits of your actual evidence.
State why proof can stop or the named remaining risk that needs more checking.

For behavior, test or CI changes, include the testing strategy's compact delta
disposition: retained claim, evidence level, duplication removed or justified, and
recurring CI cost. Documentation cleanup must not silently weaken those floors.

## Open the PR

Use the [PR template](../../.github/PULL_REQUEST_TEMPLATE.md). State what changed,
why it serves the intended outcome, what was validated and what remains unresolved.
Choose the required semver classification when package behavior or shipped content
changes; a documentation change is not a release or support promotion.

Keep stacked PRs independently truthful at their own base and head. A downstream
fix does not repair an invalid lower layer.

An agent that implemented or materially changed the patch must not approve or
independently review it, nor direct a child agent to supply that approval. Mark it
**ready for independent review** and leave review to an externally initiated
reviewer using the [review skill](../../tools/skills/pr-review-recheck/SKILL.md).
The implementer can continue other authorized work; review is not automatically
a gate on implementing the next stack layer.

Use the [issue-shaping skill](../../tools/skills/github-issue-shaping/SKILL.md) and
[issue-creation skill](../../tools/skills/github-issue-creation/SKILL.md) when filing
follow-up work. For observed product friction, start with
[dogfooding feedback](dogfooding-feedback.md).
