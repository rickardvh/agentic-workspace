# Standing repository obligations

Verification can retain a current assessment of a repository condition that
outlives one task. Declare only conditions the repository has chosen to maintain.
There are no default chores, scheduled runs or automatic issues.

## Declare a condition

Extend an existing `current-evidence` assurance requirement in
`.agentic-workspace/verification/manifest.toml`:

```toml
[assurance.requirements.usage_example]
requirement_class = "current-evidence"
level = "medium"
force = "required-before-closeout"
source_intent_ref = "contracts/interface.json"
source_intent_revision = "interface-v1"
notes = "The usage example follows the supported interface"
detail_route = "verification:usage-example"
evidence_owner = "verification:usage-example"
required_evidence = ["A recorded comparison of the example and interface"]
blocking_claims = ["claim-work-complete"]

[assurance.requirements.usage_example.freshness]
procedure = "docs/maintainer/check-usage-example.md"
max_age_seconds = 604800
dependencies = ["docs/usage-example.md", "contracts/interface.json"]
disposition = "route"
```

The identity is a lowercase identifier of at most 64 characters. A manifest may
declare at most 32 requirements with freshness. Each entry names one procedure, up to 24 exact
repository dependencies, a positive freshness interval and the evidence needed
to judge the condition. The interval is measured from the recorded observation,
not from the next read. Paths must remain inside the repository and outside local
runtime storage and the assessment source itself.

`freshness.procedure` is the repository file to read when assessing the condition.
Its contents participate in assessment currentness. The existing `detail_route`
keeps its evidence-detail or recovery meaning, including owner routes such as
`measurement:latency` and commands such as `uv run pytest tests/test_latency.py`.
Freshness does not open that route as a file or execute it.

`freshness.disposition` records the intended response: `report`, `route` or `work`. It grants
no execution permission. Ordinary-entry routing is a separate consumer of this
declaration; this lifecycle exposes the callable Verification operations.

## Inspect and assess

Read the native Verification view's `current_evidence` detail and the corresponding
`assurance_applicability.requirements` row. Each assessment is
`due`, `satisfied` or `unknown`, with a reason. Follow its exact returned request
through the normal owner interaction procedure. Read the named procedure and
dependencies, perform the authorised check and supply:

- `outcome`: `satisfied`, `failed` or `unknown`;
- `observed_at`: the observation time as Unix seconds;
- `reason`: the bounded semantic judgement;
- `evidence_refs`: up to six exact repository evidence files.

An exit code or a caller's assertion is insufficient. A satisfied assessment needs
present evidence and dependencies, plus the exact returned decision response or
an existing policy delegation covering the manifest, procedure, dependencies and
evidence. A declaration does not create such a delegation. The action remains
subject to current effect admission and scoped write restrictions.

The published assessment is a repository-owned semantic judgement. Its hashes
establish currentness, not the identity or honesty of its author. It is not an
authenticated command receipt, independent review, or permission to complete work.
Use Verification's existing proof and review admission for those claims.

## Currentness and recovery

The current source is
`.agentic-workspace/proof/current/current-evidence.json`. It contains at most
one assessment per assurance requirement. Replacing an assessment does not append a public
run history. A new task or unrelated file change alone preserves satisfaction.
Changes to the requirement, procedure, dependencies, evidence, producer or applicable decision authority
require a new assessment. Expiry and failed assessments are due; missing evidence,
future observation times and unresolved assessments remain unknown.

Publication uses the existing native attempt custody and an atomic current-source
replacement. If publication succeeds but its result is interrupted, the owner
offers a recovery request and reports satisfaction as unknown. Recovery checks
the exact postimage, custody, policy and assessed sources before retaining the
result; it does not publish the assessment again. Conflicting material is
preserved for investigation.

Removing a declaration exposes an explicit retirement request. Retirement removes
only Verification's entries for removed obligations. Referenced evidence files
and other owners' state are preserved. Local attempt custody has the existing
runtime lifetime; it is separate from the bounded repository assessment map.

## Existing owner audit for #3680

The assurance requirement already owns identity, source intent and its revision,
evidence owner and expectation, detail route, force and affected claims. Those
fields remain authoritative. The only new declaration is `freshness`, which adds
age, a repository procedure reference, exact dependencies and intended disposition. A peer obligation registry is
unnecessary and is not accepted by the manifest.

The existing measurement admission consumes authenticated native command output
and numerical conditions. It has no replaceable repository semantic assessment
that can remain current across tasks and checkouts. Source reconciliation handles
instruction-governed source relationships rather than assurance requirements.
Neither contract can simply be relabelled as satisfaction of a requirement.

The current-evidence helper therefore extends Verification with exact assessment,
replacement and retirement requests. It uses the existing dependency observer,
decision delegation, current projection, attempt custody and effect revalidation.
It exposes the result on the existing assurance row and evidence gap. Measurement
and independent-review requirements keep their separate admission; semantic
satisfaction cannot discharge them or confer task completion.
