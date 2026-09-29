---
name: workspace-dogfooding
description: Report a material AW product defect encountered in a repository that opted into anonymised upstream dogfooding.
---

# Report an AW product finding

Use this procedure when ordinary work exposes a material bug or repeated friction
in AW itself. Preserve the assigned task and continue it when safe. Cosmetic
preferences, expected failures and consumer-repository defects need no AW report.

First check repository-owned `.agentic-workspace/config.toml`:
`workspace.upstream_dogfooding = true` permits this reporting procedure. Absent or
false means stop quietly. Improvement latitude alone grants no publication consent.

Prepare a short anonymised report: affected public AW operation, sanitised symptom,
whether an effect occurred, expected behaviour, and a minimal synthetic or abstract
reproduction. Include exact AW version/commit, install channel and OS/runtime class
when known; label unknowns. A successful workaround does not prove the defect fixed.

Exclude consumer repository identity, private paths, source or code excerpts,
proprietary task text, credentials/tokens, personal data, raw prompts/transcripts
and unrelated logs. Never upload source files, patches or raw logs. Reconstruct
the example with invented names and synthetic data; do not merely hide the repo
name in an otherwise identifying excerpt. If safe abstraction is uncertain,
prepare only the safe facts and state which reproduction detail is missing.

For a suspected vulnerability, use AW's current
[security policy](https://github.com/rickardvh/agentic-workspace/security/policy)
and private reporting path. Do not publish a public issue. If the private path is
unavailable, return the safe report for private handoff.

Use only a host-provided, already authenticated GitHub capability. When search/read
is available, search open and closed issues in `rickardvh/agentic-workspace` for the
same failure. Update the smallest matching issue with new evidence; avoid duplicate
reports or comments when the current issue already covers the finding.

Publish the prepared report only when the opt-in is current, safe anonymisation is
established, and that host capability supports issue writes. If search, writing or
safe anonymisation is unavailable, return the exact safe report for maintainer
handoff. Do not discover alternative credentials, use browser automation or switch
to shell publication. This procedure grants no credentials, consumer mutations,
upstream code changes, proof, review or completion authority.

Stop after confirming the report/update and its issue link, confirming existing
coverage, or delivering the safe report with the precise handoff gap. Resume the
assigned task within its current restrictions.
