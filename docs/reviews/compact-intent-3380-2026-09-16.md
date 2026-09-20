# Compact/carried System Intent disposition (#3380)

**NO_PRODUCT_GAP** for the bounded current-master journey. The existing public
path produced an exact invokable action and a current continuation. No product
protocol change or permanent regression case is justified by this evidence.

Observed on Windows/PowerShell against freshly fetched master
`178e2b0f6ee176496df0756885c5154e032a0bfc`. Both native binaries were built together
with `cargo build --locked --workspace --bins`. The configured invocation was
`uv run --frozen --active --no-sync python scripts/run_agentic_workspace.py`.
This observation predates the implementation stack; it does not rely on #3375's
publication-custody change.

The disposable Git fixture declared only `SYSTEM_INTENT.md`, containing
“Preserve human intent and keep tools quiet.” Its retained interpretation had an
older summary and no current source records. Every request retained the task
“Reconcile the retained interpretation with the current human intent” and the
changed path `SYSTEM_INTENT.md`.

| Boundary | Observation |
| --- | --- |
| Default compact start | Reported `retained-interpretation-source-currentness-unproven` and an exact lazy System Intent detail reference. |
| Targeted owner detail | Returned exact read requests for the governing source and retained interpretation, plus `system-intent/edit-source/v1`. No unrelated owner detail or full projection was fetched. |
| Source reads and semantic proposal | Read both exact owner requests. Supplied only content, `judgment=revised`, and a reason. The complete postimage added the preferred source and its normalised-text SHA-256 record. |
| Compact and carried authorisation | Both exposed the bounded `intent-write-authorization` response request. Only its answer was changed to `authorize-write`; current context came from carriage. |
| Selected carried action | `system-intent.write`, action view transport `use-exact-carried-envelope`, reference `sha256:935528a872142c9facb1ea5f42f70085428ca8595151e61a0916cce4df5ea805`. |
| Stale-task negative | Changing the carriage context's task returned `effect_outcome.status=rejected-before-effect`, `effects=[]`, and `altered carried envelope`. No effect was attempted. |
| Exact invocation | Passing the unmodified carriage and returned action reference committed `system-intent-source`; owner status was `applied`. |
| Continuation | `status=current`, `retry_effect=false`. This establishes only the bounded reconciliation, not task completion, independent review, or release admission. |

The committed result revision was
`sha256:c7b9ec36ee9c7c4bf67afaf90f680d5b303b4deec0603a6407e0a37f4e4bcd69`.
The postimage revision was
`sha256:ec696ce47eb9a7297caa48990b7d48c0399ccd47e98205f9c1703554ca563eca`.
Target-dependent identities above identify this observation, not replay authority.

There were operator errors during this investigation: a plain context object was
initially supplied where the CLI accepts an owner request, and a carried action
view was initially treated as an invocation. The public action view explicitly
names its transport and reference. The correct carried invocation is:

```text
agentic-workspace invoke --input <carriage-file> --reference <returned-action-reference> --format json
```

The negative assertion initially confused process success with effect success.
`invoke` can successfully return a structured rejection; inspect
`effect_outcome`, not just exit status. The final negative changed the actual
carried context, rather than adding a CLI task flag alongside authoritative
carriage. No immutable invocation fields were reconstructed or copied by hand.
No Rust implementation or test inspection was required during this reproducer.

The owning procedure already explains exact owner requests and carried
currentness. This report retains the bounded disposition and transport distinction
to prevent rediscovery. Disposable fixture/transcript data is not a new product
artefact or a permanent test. Other task/posture combinations and historical
incidents remain outside this observation.
