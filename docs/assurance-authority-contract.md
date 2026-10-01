# Repository assurance decisions

Some repositories have additional rules that decide whether a change needs a
particular review, check or restriction. AW can read those rules from repository
configuration or from a repository-owned classifier.

The result does not itself grant permission to change files, waive a requirement,
prove that a test passed or decide that the task is complete.

## What AW checks

The implementation has four responsibilities:

1. tie each assurance requirement to the repository source and inputs it depends on;
2. accept only complete decisions produced from the current source/input revisions;
3. keep waivers or dismissals valid only within the scope, revision, expiry and
   review conditions they were created for;
4. verify externally produced evidence before using it.

If a source, input or required identity changes, AW should report that the earlier
decision no longer applies and provide the next supported step.

## External evidence

Repository declarations for trusted external evidence live in
`.agentic-workspace/verification/manifest.toml`:

```toml
[evidence_authorities.acme_unit]
producer_id = "ci/acme"
issuer_id = "github-actions"
proof_route = "authoritative_validation"
evidence_class = "test-result"
result_contract = "pytest/v1"
allowed_results = ["passed", "failed"]
```

The field names above are exact configuration identifiers.

A host stores the provider result in its protected storage and gives AW only the
reference it needs. AW then checks the issuer signature, validity window,
audience, producer/result data, configured evidence rule, and the exact code or
inputs covered by the result.

Caller-supplied fields such as `authenticated=true` do not make evidence trusted.
Repository-local keys do not replace the package-pinned issuer checks.

## Current use

The normal AW result may include a repository assurance decision when one applies
to the task. An invalid decision becomes a specific blocker. A valid decision adds
the repository requirements that the agent must respect.

If no repository classifier is configured, ordinary work remains unchanged.
