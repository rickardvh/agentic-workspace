# Native command boundary

`agentic-workspace` is the ordinary Rust CLI over one shared Rust authority.
Build both source-checkout binaries with `cargo build --locked --workspace --bins`.
Installed wheel, npm and host-labelled native archives carry the paired CLI/core;
see [release topology](../maintainer/native-release-topology.md) for provenance
and the supported artefact boundary.

The [package compatibility policy](../release-and-versioning.md#package-compatibility-boundary)
protects the documented entrypoints and transport behaviour below. Current owner
requests/results travel with the installed runtime; serialisation alone does not
make their internal fields stable across package versions.

Run `agentic-workspace --version` to print the invoked executable's version as
one line of text. The native CLI uses SemVer spelling, so a development build
prints `agentic-workspace 0.0.0-dev.0` even when the Python distribution is
`0.0.0.dev0`.

The CLI owns argument parsing, JSON transport, rendering and exit codes. Its
public command and option declarations come from `source_decision_contract.json`:

| Command | Current purpose |
| --- | --- |
| `setup` | Propose repository adoption/refresh and obtain explicit authorisation; `--recover` selects interrupted custody. |
| `start` | Resolve current owner information, requests and available effects. |
| `invoke` | Execute an exact action returned by its current owner. |
| `worker` | Project sealed Assignment input or assemble unproven return re-entry. |
| `resources` | Inspect hygiene and propose or execute an admitted resource operation. |
| `activation-index` | Check or derive a repository registry from procedure sources; `--input` supplies `registry` and `mode` (`check` or `write`). |

`setup` reports `custody_recovery` when a fresh checkout lacks the local adoption
record and replacement is blocked. `prior-artifact-required` supplies an
untrusted former-package discovery hint and setup preview arguments;
`unavailable` lists the source differences or missing identity. Only a matching,
independently authenticated former artefact can reacquire local adoption through
normal authorised setup. Its preview must propose no tracked package changes.
Retry the selected new artefact afterwards. `--recover` remains limited to an
interrupted existing effect. See [setup conflicts](../troubleshooting.md#updating-or-removing-aw-reports-conflicting-files).

`start --target <repository> --task "<task>" --format json` reads current owner
sources. Repeated `--changed` arguments declare changed paths. Supply a returned
request through `--input <file>` or JSON stdin with `--input -`; a bounded array
can preserve distinct owner answers. `invoke` accepts a complete JSON envelope
containing `target`, `task`, `changed` and the exact returned `invocation`, or
`--input <carriage> --reference <action-reference>`. A bare action file requires
the original `--target`, `--task` and `--changed` flags. Use an envelope with
`changed: []` or carriage for an empty changed scope. Explicit context flags
must match the envelope or carriage. Missing context rejects before execution;
the CLI cannot reconstruct it from an action's identity.
Clients cannot invent source admission, custody, capability contracts or proof.

Python `agentic_workspace` and the installed npm root/`./operating` exports
project `start`, `invoke`, `resources` and the reference/carriage helpers.
JSON and native entry independently
consume the same Rust authority; no binding supplies a parallel domain runtime.
The native executable does not launch Python or Node to decide semantics.
Missing or incompatible paired cores fail explicitly, without source-build or
alternate-runtime fallback.

Compact, full and carried views preserve current requests, restrictions and
available effects. Owner details omit internal contribution objects; composed
blockers and actions identify their owner. Exact references and disposable
carriage avoid reconstructing hidden fields. Delivery suppresses unchanged
source prose only; it grants no compliance, mutation, proof or completion claim.

Current native owners cover configuration, instruction/source reconciliation,
Planning, Memory and repository decisions, Verification, Assignment and bounded
delegation. Read current capability dispositions rather than treating discovery,
owner quiescence or process success as completion. See
[execution configurations](../maintainer/native-execution-configurations.md),
[proof execution](../maintainer/native-proof-execution.md), and the canonical
[workspace procedure](../../.agentic-workspace/skills/workspace-startup/SKILL.md).
Unsupported transport/result classes remain explicit gaps. Semantic judgement,
independent review and human approval retain their own authority.

### Manual pull request review

When local safety or an applicable Verification protocol calls for manual PR
review, `start` exposes `manual_review` in compact output and
`verification.manual_review` in full output. Answer the returned request with the
canonical hosted `pull_request` URL, such as
`https://forge.example/owner/project/pull/17`. Use the forge's repository-qualified
pull or merge request path ending in the numeric ID. AW normalises host case,
default ports and trailing slashes, then observes the local Git commit and
separates pending review from current implementation and evidence gaps.
The PR reference is caller supplied. The checkout observation does not verify a
hosted PR's current head.

Review through the repository's usual process. To retain the outcome, answer the
request with the same `pull_request` and a `report` containing the external
`reference`, the exact `reviewed_revision` and a `disposition` of `approved`,
`changes-requested` or `rejected`. Invoke the offered record action. For a new
result on the same commit, supply a distinct external reference and set
`report.supersedes` to the current external review reference. An exact repeat
reuses the existing record.

The record is local to this checkout. Select the same PR again to read it.
A different checkout commit, pending tracked changes or selected uncommitted
inputs make the recorded review stale for the current work. Git flags that can
hide changes to selected inputs make currentness unverified. The repository owns
approval, and AW marks the review provenance as unverified. The record leaves
human-verification and reviewer-admission restrictions in force.

`tests/test_native_public_cli.py` and existing native owner scenarios exercise
fresh native/JSON/Python/TypeScript consumers, real former/current sources,
currentness, exact replay and claim-sensitive negatives. Exhaustive artefact mode
runs those consumers outside the checkout against one packaged set. Command proof
reuse additionally binds the actual core location: byte-identical installations
at different locations cannot silently inherit each other's receipts.
These checks do not grant independent acceptance, live-provider success or
first-stable admission.
