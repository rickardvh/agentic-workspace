# Anchored YAML for AW responses

The benchmark exercises the Node package's optional agent view. It displays one AW response as YAML 1.2, keeps the first occurrence of a repeated value in place, and reuses it through document-local aliases. Hosts can also issue short selections and retain exact native values. The [package guide](../../../../docs/package/output-profiles.md#render-one-yaml-format-for-an-agent) covers both entry points. The broader work is tracked in [AW #3957](https://github.com/rickardvh/agentic-workspace/issues/3957).

## Try it

Run the filter from the AW source checkout with Node 22.12 or newer and the paired native binaries built.

```powershell
$prototype = 'src/tooling/model-cli-harness/anchored-yaml'
npm ci --prefix $prototype --ignore-scripts
uv run python src/tooling/run_agentic_workspace.py start --target . --task "Inspect current restrictions" |
    node "$prototype/render.mjs"
```

The current renderer considers repeated values of at least 24 UTF-16 code units in compact JSON, uses short alphabetic anchor names, and puts short scalar lists on one line. It checks expansion with the standard YAML parser before printing. Structures exceeding the parser's alias limit fall back to ordinary YAML. The filter preserves native 64-bit integers and negative zero. The benchmark-only `pair` mode retains compact JSON and the original 48-unit anchored layout as controls.

## Hosted selections · 20 November 2026

The final comparison used 16 fresh Terra/medium sessions across four native workflows, with two trials per presentation and alternating order. Both arms received the same new native hint identifying the exact answer for a bounded choice. Each started from byte-matched native inputs. Terminal success required the actual native outcome and, where relevant, file readback. The deferral case required stopping before any invocation.

| Workflow | Original YAML layout, provider tokens per success | Tighter YAML with hosted selections, provider tokens per success |
| --- | ---: | ---: |
| Inspect live checkout restrictions and read Configuration | 24,978 | 23,263 |
| Authorize, commit and read back a configuration write | 22,015 | 19,990 |
| Recover after a stale write and preserve a concurrent edit | 18,683 | 17,926 |
| Prepare a deferral and leave configuration untouched | 21,979 | 20,028 |

Each arm finished **8/8 on the first attempt**. Hosted selections reduced AW payload from 64,018 to 54,110 tokens (15.5%) and total provider input plus output from 175,308 to 162,412 (7.4%). Both arms reported 52,096 cached input tokens. Billing was unobserved. The earlier write sessions consistently needed a correction, while all writes here succeeded on the first attempt. The native hint and benchmark instructions changed between experiments, so the earlier comparison cannot isolate their individual effects. [Final session records](terra-selections.json)

We also ran an earlier 12-session candidate that shortened evidence metadata. It completed all tasks, but the large checkout view grew because equivalent records appeared in different forms and could no longer share YAML anchors. The final host adapter shortens only recognized selection fields and preserves evidence and owner material. These two-trial samples cover bounded workflows and host-assisted dispatch. [Earlier candidate records](terra-hosted.json)

## Terra pilot · 20 November 2026

Twelve fresh ephemeral `gpt-6.1-terra` sessions at medium reasoning effort completed three native workflows, twice per format. Each pair received the same task and byte-matched source responses. The harness alternated the format order on the second trial. It supplied a typed reply schema and performed the operations the agent selected. One corrective turn per task was available after a mismatch.

| Workflow | Compact JSON tokens per success | Anchored YAML tokens per success | Reduction | First-pass successes, JSON / YAML |
| --- | ---: | ---: | ---: | ---: |
| Identify the implementation restriction and its entire scope, then select and read current Configuration in the live checkout | 53,024 | 24,996 | 52.9% | 2/2 · 2/2 |
| Authorize a shared configuration write, select its exact action, commit it and read the TOML back | 33,865 | 32,617 | 3.7% | 0/2 · 0/2 |
| Handle a stale write, reenter from the returned context, read the current value and preserve a maintainer's concurrent edit | 19,753 | 18,695 | 5.4% | 2/2 · 2/2 |
| **All tasks, equally represented** | **35,547** | **25,436** | **28.4%** | **4/6 · 4/6** |

The unit above is the sum of provider-reported input and output tokens across all turns and retries, divided by successful tasks. Both arms finished 6/6. The large checkout read accounted for 92% of the total token difference. All four write sessions initially returned a serialized proposal in the answer field. AW needed the scalar `authorize-write`. All four corrected it on the next turn.

| Total over six sessions | JSON | YAML |
| --- | ---: | ---: |
| AW payload tokens presented once per stage, locally counted with `o200k_base` | 112,952 | 53,776 |
| Provider input, including conversation history | 212,103 | 151,391 |
| Cached input, already included in provider input | 106,368 | 68,096 |
| Provider output | 1,181 | 1,224 |
| Provider input + output | 213,284 | 152,615 |

Payload fell 52.4%, total provider tokens 28.4%, and uncached input 21.2%. Cache hits differed by trial and format. Billing was unobserved. Two of the three tasks ran on disposable repositories using the actual native AW binary. The task mix, host-assisted envelope submission and small number of repetitions limit generalization to open-ended agent work.

A preliminary shakedown exposed a scoring bug in the checkout case. The checker compared a nested policy object to a string after a correct Configuration read. In that batch the four stale-read sessions passed, both JSON writes passed and one of two YAML writes passed. That batch lacked a complete paired cost record. The table uses the fresh 12-session run after the checker was corrected. Its detailed counters, input fingerprints and mismatched answers are in [terra-medium.json](terra-medium.json).

## Reproduce

The checkout case targets an active AW source checkout with the binding Assignment policy and matching implementation restriction. The fixture cases create temporary repositories outside the source checkout. The runner needs a signed-in Codex CLI that supports Terra, medium effort and ephemeral app-server sessions. The recorded run used Codex CLI 0.170.0 and AW source `766cfc91f6a793a602134ab065eac4ad1c714ae2`.

Run these commands from the repository root.

```powershell
cargo build --locked --workspace --bins
$prototype = 'src/tooling/model-cli-harness/anchored-yaml'
npm ci --prefix $prototype --ignore-scripts
node --test "$prototype/render.test.mjs" "$prototype/host.test.mjs"
uv run python "$prototype/benchmark.py" --check --compare yaml-hosted
uv run python "$prototype/benchmark.py" --compare yaml-hosted --repeats 2 --out "$env:TEMP/terra-yaml-rerun.json"
```

The `--check` command exercises the selected cases with known-good answers before spending model tokens. The last command repeats this preflight and runs 16 sessions. Choose `--compare json-yaml` for the three-task JSON and original-layout comparison. The runner checkpoints after each session and verifies matching native response fingerprints before setting `complete` to true. Costs include retries. Absolute paths and fresh response bindings can change individual payload sizes between runs.
