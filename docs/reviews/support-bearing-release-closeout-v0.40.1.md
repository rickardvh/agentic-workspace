# Support-bearing release closeout: v0.40.1

Status: complete  
Release: [v0.40.1][release]  
Published: 2026-08-14T16:55:21Z  
Protected source commit: `ddd9812dd6ac455ca546bc38568e8c68a26e6ed4`

This is closeout evidence for issues #2448 and #2452. It does not replace the
release-owned receipts or add a parallel promotion authority.

## Composed promotion result

The dereferenced `v0.40.1` tag and the release manifest identify the same source
commit as
[`support-bearing-promotion.json`](https://github.com/rickardvh/agentic-workspace/releases/download/v0.40.1/support-bearing-promotion.json).
The promotion result is `passed`, has no failures, and admits these exact-subject
domains:

- server promotion: passed;
- runtime support: passed;
- generated semantic conformance: passed;
- install identity: passed;
- redistribution and license: passed;
- security and supply chain: ready.

The promotion artifact map binds the published Python wheels and sdists, npm
tarballs, semantic-conformance receipts, install and redistribution receipts,
SBOM, and security receipt by SHA-256. GitHub's published asset digests match
those promotion subjects. The coordinated release manifest references the
promotion receipt and the same source commit, so the manifest remains the
release index and the composed result remains the promotion authority.

## Public distribution rehearsal

The published
[`distribution-install-readiness.json`](https://github.com/rickardvh/agentic-workspace/releases/download/v0.40.1/distribution-install-readiness.json)
provides a versioned root-wheel URL and SHA-256 requirement. On 2026-08-14, that
requirement was installed into a clean CPython 3.14 environment after the
release process had completed. Resolution installed only the coordinated,
project-controlled distributions at version 0.40.1:

The bounded machine-readable result is retained in
[`public-install-rehearsal-v0.40.1.json`](../maintainer/public-install-rehearsal-v0.40.1.json).
It binds the readiness receipt and root wheel by URL and SHA-256, records the
exact four controlled distributions and their same-release hashes, and retains
the later-process result separately from bootstrap.

- `agentic-workspace`;
- `agentic-workspace-memory`;
- `agentic-workspace-planning`;
- `agentic-workspace-verification`.

The resolver obtained each coordinated module from an exact same-release GitHub
asset URL with its declared SHA-256 digest; neither `agentic-memory` nor
`agentic-planning` entered the graph. After that bootstrap process exited, a
fresh process invoked the installed `agentic-workspace` executable against a new
host directory. `start` returned `startup-context/v1` successfully. No
machine-local executable path was written as the durable distribution identity.

## Lane reconciliation

The bounded release-critical issues #2449 through #2462 are closed, except
issue #2452, whose final public-release and second-process evidence is recorded
here and in the retained rehearsal receipt.
The feature branch therefore proposes closing the #2448 Planning lane on the
admitted merge branch through
`.agentic-workspace/planning/integration-proposals/issue-2448-public-release-rehearsal-close-owner.integration-proposal.json`.

The release risks eliminated by the lane are accidental third-party Python
resolution, mutable-branch support installs, unproven runnable generated
targets, source-only artifact claims, missing install/reference closure,
unlicensed or contradictory package metadata, unprotected promotion, incomplete
runtime claims, and missing supply-chain admission.

The npm package names remain intentionally unpublished. Their supported posture
is explicit release-asset-only distribution; npm registry installation is not
advertised. The project remains classified Alpha, which is a maturity statement
and does not weaken or bypass the support-bearing promotion gate.

Closure is honest because a public protected-commit release exercised the same
promotion decision and exact artifacts that publication consumed, and the last
distribution slice succeeded from clean resolution through a later process.

[release]: https://github.com/rickardvh/agentic-workspace/releases/tag/v0.40.1
