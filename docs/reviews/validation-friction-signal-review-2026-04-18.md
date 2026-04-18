# Validation Friction Signal Review

Date: 2026-04-18

## Scope

Apply the new `validation_friction` repo-friction signal to recent workspace work in this repo.

## Signal Definition

Count something as `validation_friction` only when otherwise straightforward work keeps stalling at validation because seams, tranche boundaries, proof expectations, or rerun/re-entry paths stay unclear.

Do not count:

- ordinary bug-fixing with a clear failing check and expected fix
- one-off broken tests or environment failures
- genuinely difficult domains where the hard part is the domain logic itself

## Recent Examples

### Example 1: Cross-surface workspace/reporting changes

- Slice shape: workspace reporting and defaults changes that touched docs, report payloads, and tests together.
- Observation: the implementation work itself was straightforward, but the proving lane can become unclear because the slice spans canonical docs, defaults payloads, and report output together.
- Classification: `validation_friction`
- Why: this is a compact example of `unclear_proof_contract`. The hard part is not the code change itself; it is making the narrowest sufficient proof boundary obvious and repeatable.

### Example 2: Commit-hook rerun after a local style failure

- Slice shape: a bounded change was ready, but the commit hook initially failed on unrelated line wrapping that had to be corrected before commit.
- Classification: not `validation_friction`
- Why: this was ordinary repo hygiene, not a repeated seam or proof-boundary problem. The fix path was obvious once the failure surfaced.

### Example 3: Package/root refresh after shipped-surface changes

- Slice shape: changes affected package source, package payload, and the root install together.
- Observation: the operational validation path exists, but when the slice boundary is vague it is easy to bounce between package-local checks, root refresh, and repo-wide checks.
- Classification: `validation_friction`
- Why: this is a compact example of `validation_bounce_reentry` and sometimes `bad_tranche_boundary`. The friction is about repeatable rerun/re-entry fit, not the domain logic.

### Example 4: Narrow docs-only review clarification

- Slice shape: bounded docs changes with direct test updates in one owned surface.
- Classification: not `validation_friction`
- Why: the validating lane stayed obvious and narrow. There was no repeated bounce or unclear proof contract.

## Conclusion

The signal is worth keeping, but only as compact repo-friction evidence. In this repo, the useful cases are:

- `unclear_proof_contract`
- `validation_bounce_reentry`
- `bad_tranche_boundary`

Use `weak_seam` when validation pain comes from a real repo seam that keeps forcing cross-surface proving work. Keep the class evidence-only and report-shaped rather than turning it into a new analyzer or state store.
