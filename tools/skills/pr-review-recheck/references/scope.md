# Establish scope and intent

Prepare current evidence with [trusted preparation](recheck.md#trusted-executable-preparation), then identify the PR's
claimed intent from its body, linked issues, closure claims and requested fixes.
The helper collects facts; it does not interpret those claims or establish
eligibility, correctness, proof sufficiency or a verdict.

Audit the linked issue's system-shaping assumptions against current evidence, system intent, and domain ownership:

- distinguish `PR violates a sound issue requirement` from `PR reveals that the issue requirement is wrong or too strong`;
- distinguish a useful slice from satisfaction of the underlying intent;
- check whether the PR adds machinery only to satisfy an over-specified mechanism when a smaller owner-aligned result serves the invariant;
- refine the issue before forcing harmful acceptance when the human-owned why is unchanged; ask the human or domain owner when changing the issue would change that why.

Use the prepared complete changed-file set before opening broad files.

For first review, compare the diff against the linked issue's final intended outcome, non-solutions, and evidence requirements after the assumption and closure-shape audits.

## Assumption audit example

If an issue requires every selector to be cheaper than every default projection, but a selector intentionally requests extra enrichment, do not demand caching machinery solely to satisfy that impossible absolute. Recommend refining the issue to require query-shaped dependencies and attributable extra work, then review the PR against that invariant. This challenges the proposed mechanism without silently replacing the human-owned goal of bounded projection cost.
