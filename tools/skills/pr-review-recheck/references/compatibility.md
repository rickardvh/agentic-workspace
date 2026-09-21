# Judge compatibility and material risk

Compare the claimed public boundary with the actual changed inputs, outputs,
errors, effects, packaging and supported consumers. Distinguish an additive
application of existing contracts from a change to their meaning or guarantees.
Classify from source and evidence, not a task keyword, filename or numerical risk
score. Preserve uncertainty when the affected consumer cannot be observed.

Use the repository's current compatibility policy and release identity. A passing
example cannot certify an untested support boundary; a prerelease history cannot
silently excuse a breaking change to a stable contract. Route a demonstrated
generic defect to its smallest responsible owner rather than hiding it in a
repository-specific method or making every future application a release gate.

For a stack, assess the introducing layer's exact base/head. A downstream repair
does not make the lower layer independently correct. Follow [proof](proof.md) for
the observation that resolves the named risk, then stop or escalate at that bound.
This judgement does not itself change policy, evidence sufficiency or release
admission.
