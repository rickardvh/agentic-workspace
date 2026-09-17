# Evidence and support

Agentic Workspace keeps several claims deliberately separate:

1. **source/conformance evidence** — what the current source and deterministic contracts prove;
2. **published release evidence** — what an exact immutable release proves about its artifacts and support boundary;
3. **live-agent evidence** — what observed models/hosts actually did under a bounded setup.

A strong result in one class does not silently promote another. Source tests do not publish a release; a published prerelease is not stable support; deterministic conformance does not guarantee model obedience; one successful provider run does not establish universal provider support.

## Published release evidence

Use the selected immutable release as the public evidence subject.

### Stable releases

A support-bearing stable release must carry the coordinated evidence required by the release owner for that exact source and artifact set. The generated [support-bearing install projection](reference/support-bearing-install.md) identifies the current stable release and its exact installation receipt.

Release evidence can include:

- `distribution-install-readiness.json` for exact install identity and artifact binding;
- support-bearing promotion evidence;
- redistribution/package-readiness evidence;
- security and supply-chain checks;
- SBOM, provenance, and artifact digests;
- native/generated-target conformance;
- registry publication receipts for exact PyPI/npm projections when those registries are part of the release;
- coordinated Cargo publication evidence when Cargo artifacts are part of the release.

The release receipts, not a conceptual documentation page, own the exact version, digest, and publication status.

### Release candidates and previews

Release candidates and exploratory previews are immutable prerelease evidence subjects but remain **non-support-bearing**.

An RC can exercise near-final package topology and public journeys without establishing the later stable release. A preview can prove useful packaged behavior without establishing stable compatibility, registry availability, or production support.

Use the exact prerelease's own manifest and install-readiness receipt. Do not transfer evidence from a newer source checkout or another prerelease merely because the interfaces look similar.

See [Installation and adoption](agentic-workspace-install.md) for the release-class selection rules.

## Deterministic source evidence

Source validation covers classes such as:

- operation/schema and parser/command conformance;
- shared Rust semantic authority and thin binding/projection parity;
- package and clean-install topology;
- installed-footprint/reference closure;
- currentness, stale-action, interruption, recovery, and idempotency fixtures;
- Planning, Memory, Verification, Assignment, delegation, correction, and repository-control owner behavior;
- generated-reference and package-contract drift checks;
- weak/negative cases where a route is ignored, evidence is stale, or a partial slice is incorrectly presented as broader completion.

Deterministic proof supports only its exact subject and declared claim. A source checkout may be ahead of the latest published release. Passing source validation therefore does not establish that those capabilities are publicly available in older installed bytes or that a support-bearing release exists.

The native architecture has one ordinary deterministic semantic/effect authority in the Rust core. Native, Python, TypeScript, and JSON-facing surfaces project or bind that authority; separate source-development module packages are development/migration fixtures rather than independent shipped semantic runtimes.

## Live-agent evidence

Live-agent runs test a different question: whether a model/host actually discovers and uses the available context and control cheaply and correctly.

Representative observations have included:

- clean startup with compact routed context;
- correct claim boundaries after failed or partial proof;
- relevant Memory/skill selection;
- continuation across sessions;
- bounded worker/delegation handoff;
- cases where models ignored routed guidance, produced incomplete handoffs, created unexpected residue, or required steering.

These observations are bounded by model, host, source/release revision, scenario, and available integrations. They are evidence, not universal compatibility guarantees.

Maintainer evaluation material lives under the [external-agent evaluation harness](../tools/model-cli-harness/external-agent-evaluation/README.md) and dated review/maintainer reports. Historical runs keep their original subject rather than becoming current product doctrine.

## Current support boundary

The selected release owns exact public support. The [installation and adoption guide](agentic-workspace-install.md) owns the current native prerequisite model and points to the immutable release evidence that can make a support-bearing claim.

General boundaries remain:

- AW is not a sandbox, credential host, CI provider, compliance certification, or guarantee of model obedience;
- repository-configured commands inherit caller filesystem and credential authority;
- unknown OS, architecture, provider, agent-host, runner, or runtime behavior remains unknown until source-bound/release-bound evidence promotes it;
- registry availability does not imply broader semantic or platform support than the admitted release;
- a repository-only read path cannot establish live runtime state, fresh proof, or effect permission;
- a passing check supports only the claim that check and its owner actually establish.

See the [Threat model](security/threat-model.md) for the execution and supply-chain boundary.

## Evidence about first-stable development

The repository retains detailed evidence from the native migration and first-stable preparation. That material remains useful for explaining why current architecture and release gates exist, but it is not the ordinary public support owner.

Examples include:

- exact native artifact admission and independent review around [#2990](https://github.com/rickardvh/agentic-workspace/issues/2990);
- candidate/conformance reports under `docs/maintainer/` and `docs/reviews/`;
- release-topology, support-promotion, and public-smoke evidence;
- bounded cost/continuation measurements and weak-case ledgers.

Once behavior is published, the immutable release receipts for those bytes are the public evidence subject. Historical source candidate reports do not retroactively change an older preview or stable release and do not need to be copied into first-contact documentation.

## How to interpret a claim

When evaluating a statement about AW, identify all four parts:

1. **subject** — source revision, release tag, artifact digest, provider/model run, or repository state;
2. **claim** — compatibility, correctness, support, model behavior, performance, or completion;
3. **owner/evidence** — deterministic test, release receipt, runtime result, review, or live-agent observation;
4. **limits** — excluded platforms, stale dependencies, weak cases, unavailable providers, or unsupported effects.

If any of these are missing, narrow the claim rather than filling the gap from nearby evidence.

See [Maturity model](maturity-model.md), [Installation and adoption](agentic-workspace-install.md), [Documentation status](documentation-status.md), and the [Threat model](security/threat-model.md).
