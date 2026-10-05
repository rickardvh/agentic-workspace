# Judge compatibility and material risk

Compare the claimed public boundary with the actual changed inputs, outputs,
errors, effects, packaging and supported consumers. Distinguish an additive
application of existing contracts from a change to their meaning or guarantees.
Classify from source and evidence, not a task keyword, filename or numerical risk
score. Preserve uncertainty when the affected consumer cannot be observed.

Apply the [package compatibility boundary](../../../../docs/release-and-versioning.md#package-compatibility-boundary):
identify the supported consumer-owned input/code or durable state that must change,
whether normal refresh or deterministic migration preserves meaning and authority,
and whether the changed interface is a named stable API, the current capability
discovery/carriage contract or runtime-owned protocol. Do not infer a major from a
typed result identity, serialised field or public Rust symbol alone. Rust embedding
through `operating::{start, invoke}` and its declared `CoreError` contract is stable;
other public implementation symbols are not automatically covered. Judge current
request schemas and operation `semantic_revision` declarations without inventing
retired profile/fingerprint negotiation. A real incompatible
supported migration remains major even when an agent could manually repair it.

Use the current release identity. A passing
example cannot certify an untested support boundary; a prerelease history cannot
silently excuse a breaking change to a stable contract. Route a demonstrated
generic defect to its smallest responsible owner rather than hiding it in a
repository-specific method or making every future application a release gate.

For a stack, assess the introducing layer's exact base/head. A downstream repair
does not make the lower layer independently correct. Follow [proof](proof.md) for
the observation that resolves the named risk, then stop or escalate at that bound.
This judgement does not itself change policy, evidence sufficiency or release
admission.
