# Signal Hygiene Contract

This contract defines the repository's adaptive discipline: how structural signals (friction, proof reports, knowledge promotion) should be captured and used to steer repository improvement.

## Core Principle: Workspace Adapts First

The primary response to friction is local adaptation within the workspace.
- **Rule**: Adapt inside the workspace when that is the honest cheap fix.
- **Rule**: Only promote repo-directed improvement when the root problem is genuinely external and the workspace can no longer honestly compensate for it.

## Repeated-Evidence Threshold

Repo-directed improvement requires repeated shared evidence that the repository is the real friction source.
- **Threshold**: At least two independent occurrences of the same friction pattern, or one occurrence combined with explicit maintainer direction.
- **Evidence Class**: Friction must be structural (unclear seams, bad tranche boundaries, weak proof contracts) rather than semantic (difficult domain logic).
- **Non-Evidence**: One-off agent preference, local taste, or friction the workspace can still remove honestly inside its own surfaces.

## Anti-Concealment Guardrails

Agents must not hide repository friction behind "clever" local hacks.
- **Guardrail**: If repeated friction points to repo-owned seams, tranche boundaries, or ownership problems, the workspace must preserve that evidence in reporting instead of hiding it.
- **Guardrail**: Concealing structural friction to force "quiet" execution of an otherwise flawed repo state is a contract violation.

## Proof Reports

Every completed task or milestone should produce a compact "Proof Report" preserved in the planning residue.
- **Requirement**: Named validation proof (logs, command output, or screenshots).
- **Purpose**: Prevent re-derivation cost during handoff and provide durable evidence for the "Proof achieved" state.

## Signal Promotion Path

1. **Friction Capture**: Recorded as `repo_friction` in `agentic-workspace report`.
2. **Evidence Accumulation**: Repeated signals in archived execplans or review artifacts.
3. **Knowledge Promotion**: Interpretive findings move to Memory; stable rules move to Docs or Config.
4. **Structural Remediation**: The roadmap prioritizes friction-backed improvements over speculative ones.
