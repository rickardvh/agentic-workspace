# Compact operation and exact carriage

This is the bounded first operation-efficiency slice for #2986/#2987/#3059,
aggregated by #2909. It preserves the integrated #3181–#3187 outcomes.

`start` defaults to a compact operating projection. The decision retains status,
selected consequence, blockers, peer questions/actions, material arguments,
semantic route and claim limits. Duplicate blockers and selected consequences
are removed; capability schemas, owner validation states and other owner detail
remain available with `--projection full`. The selected exact request/action is
included in ordinary compact output: executing it requires no detail fetch.

Consumers needing all former top-level owner views must explicitly request
`projection: "full"` (CLI `--projection full`). The native owner implementation
still computes the same full decision. This slice changes presentation and
transport, not owner selection, admission, effects, proof or recovery.

Questions can carry owner-supplied `material`, bound into question identity and
preserved in both projections. Native Planning supplies its selected subject;
Configuration, Memory/decision capture and source reconciliation supply the
before/after or publication proposal needed for judgment. The renderer never
dispatches on owner names. Owners must include material that changes judgment;
an opaque proposal digest alone is insufficient context for confirmation.

Owner contributions also carry current operating `material` in the shared
decision packet. Requested startup/System Intent source text and applicable
instruction guidance remain visible in every projection. Unrequested source
bodies stay lazy. Delivery still grants no acknowledgment, satisfaction, proof
or effect authority; a compact projection cannot silently discard a requested
source response and then call it delivered.
The required startup source-read request accompanies its source identity, so
obtaining that text needs no preparatory detail fetch.

## Thin host carriage

`projection: "carried"` returns two independent transport fields:

- `view`: model-facing compact decision, including exact references;
- `carriage`: the immutable issued envelopes and unchanged original context.

The host keeps `carriage` in its own local object or temporary file and delivers
only `view` to the model. Passing both fields to the model defeats the optimization.
There is no AW session, latest-action handle, durable registry or authority grant.
References bind the exact envelope, selector and original work context by digest.

The model returns only a `reference` and, for a question, its bounded `answer`.
Rust freshly resolves the original source-owner context, compares the complete
question, and calls the existing bounded-answer admission helper. Every supplied
owner argument is unchanged. Only an absent `answer` field is filled. Material
proposals and multi-field answer helpers remain owner-specific work; callers
cannot use this helper to replace a supplied field or invent authority.

Python, with the host retaining the object:

```python
from agentic_workspace.decision import start, answer_carried, invoke_carried

offered = start({"target": target, "task": task, "request": proposal,
                 "projection": "carried"})
# Deliver offered["view"] to the model. Its actual bounded reply supplies these:
answered = answer_carried(offered["carriage"], reply["reference"], reply["answer"])
# For this one already-authorized operation, carry its exact selected action:
action = answered["view"]["decision_packet"]["primary_action"]
# Invoke only when this concrete action is inside the host's authorized scope.
result = invoke_carried(answered["carriage"], action["reference"])
```

Node exposes `answerCarried` and `invokeCarried` over the same Rust entry point.
JSON transports use `start` with `{request: carriage, reference, answer}` or
`invoke` with `{invocation: carriage, reference}`. No language adapter evaluates
an owner schema, derives authority or decides the next semantic action.

The CLI uses the same object: the host writes only the returned `carriage` to an
ephemeral JSON file, then passes `--input carrier.json --reference <exact-ref>`.
For a decision, `start` also accepts `--answer '"choice-id"'` (JSON). A continued
`start --projection carried` returns a new exact pair. No target/task/changed
arguments need be repeated. Explicitly supplied context must match the carried
context; changing work requires a fresh start. References never mean “latest”.

Optional detail uses a returned `detail_refs` entry with `start --input
carrier.json --reference <detail-ref>`. Rust reobserves the original context and
requires exact equality before returning detail. Detail cannot answer or execute.
Currentness drift, corruption, unknown references and work changes fail closed.
Loss of the host object recovers through fresh `start` from current sources.

Hosts can connect a predetermined authorized operation after a bounded answer,
without a model turn to copy its envelope. They must return control for a new
question, changed currentness, unsupported capability, authority/proof judgment
or uncertainty. No general `while primary_action: invoke` loop is provided.

## Measurement and residual acceptance

`tests/test_native_operating_carriage.py` compares full and carried configuration
journeys across native CLI, JSON, Python and TypeScript. It measures UTF-8 JSON
bytes and an explicit interaction trace, not provider tokens or billing.
The baseline has separate model turns for the bounded answer and action-envelope
copy; the carried trace has one answer turn followed by one predetermined host
write. Both use the same Rust-issued action, no additional detail fetch, and
unchanged execution-time revalidation. The test prints measured protocol bytes.
Local carriage bytes and extra internal resolution are costs, not free savings:
the answer path reobserves the question before resolving the answered request.

Representative Windows debug-build fixture observation (2026-09-09; byte counts
include the fixture's target spelling and may vary with the temporary path):

| Observation | Full/manual carriage | Compact/host carriage |
| --- | ---: | ---: |
| Direct/no-signal model-visible JSON bytes | 82,556 | 2,762 |
| Configuration question model-visible JSON bytes | 101,914 | 4,432 |
| Model-generated answer plus action protocol bytes | 4,241 | 114 |
| Model turns: answer, then one known authorized write | 2 | 1 |
| Public calls through that write | 3 | 3 |
| Required detail fetches | 0 | 0 |
| Internal resolutions for the answer | 1 | 2 |
| Answer elapsed milliseconds, single sample | 108.7 | 196.2 |

The carried question uses 114,115 adapter-local bytes. The fixture observes zero
protocol repairs and one bounded human decision in both paths. It does not
measure provider tokens, hidden host context, source/procedure redelivery, worker
setup or a latency improvement. It does not remove the post-invoke resolve.

No parent closes from this slice. Remaining acceptance includes general bounded
material helpers, more aggressive owner-provided material summaries, truthful
post-effect continuation/uncertainty across every effect owner (#2986/#2947),
source-delivery and route continuation (#2661/#2930), profiled derivation reuse
(#2981), worker entry and effective host-context measurement (#2818/#2947), and
cumulative #2909/release admission. `invoke` retains its existing result and
recovery contract here; a committed effect is not evidence of parent completion.
