# Validate the release replacement

Issue [#3719](https://github.com/rickardvh/agentic-workspace/issues/3719) replaces
release-only Git history with a source commit, deterministic stamping inputs and
an admitted artifact inventory. The hosted evidence below is established;
external independent acceptance remains required before closure.

## Execution graph

Previously:

```text
prepare → source qualification → release PR → candidate dispatch
        → review and merge → second prepare → source qualification → tag
        → platform builds + replacement runtime builds → publish
```

Now:

```text
source/version → platform builds → assembled packages
                                  ├─ platform consumers
                                  ├─ runtime consumers
              → Cargo source packages and package/security checks
              → retained verified bundle → source tag and GitHub upload
                                        ├─ PyPI/npm publication and verification
                                        └─ Cargo publication and verification
              → coordinated completion receipts
```

Exact-source merge/security admission is reused before any release build.
The generated branch, release commit, release PR and follow-up dispatches are
removed. Runtime rows consume assembled artifacts instead of rebuilding wheels
and npm packages. Cargo publication sends the admitted archive through the
[registry API](https://doc.rust-lang.org/cargo/reference/registry-web-api.html#publish).

The platform rows, Python runtime rows, Node semantic majors, source-package
rebuilds, isolated installed-owner consumers and security checks remain.
Staging is checked before packaging and after qualification. Build jobs have
read-only permissions. Publishing jobs hold their own destination authority.

### Post-admission proof audit

The follow-up to [review comment 5905782679](https://github.com/rickardvh/agentic-workspace/pull/3721#issuecomment-5905782679)
removes the broad workspace, Planning handoff and independent-owner branches from
Release. Their source semantics remain covered by source CI. Runtime rows also
drop whole-workspace Cargo builds/tests, shared semantics, source adapters,
logging concurrency and source installation tests. Version staging does not add
a distinct failure class for those checks. The source-only Python import case
moves from release topology to the existing language-facade suite.

| Retained work | Distinct release failure it detects |
| --- | --- |
| Closed staging and final staging recheck | Wrong version or an unapproved source/dependency edit before or during packaging |
| Six native builds and compiler-free platform consumers | Missing host binaries, wrong architecture, or platform loader/install failures |
| Three Python/runtime artifact rows | Retained wheel/binding/subprocess incompatibility on supported interpreters; missing paired core and installed mutation transport |
| Node 20/24/25 exact-package conformance | Retained npm package import, CLI and subprocess incompatibility on supported Node versions |
| Cargo archive and sdist reconstruction/install | Missing build inputs or dependence on Git/repository state in published source packages |
| Package identity, SBOM, Rust dependency scan and evidence composition | Mismatched staged identities, missing or changed artifacts, or inadmissible packaged dependencies |
| Retained bundle and destination verification | Publication substitutes bytes or leaves coordinated destinations incomplete |

The extra standalone package smoke invocation is removed: exact-package
conformance already runs that suite and binds its receipt to the artifact digests.
No supported platform/runtime row or publication barrier is removed. The prior
28m15s run below establishes the earlier graph; it does not measure this reduced
graph. A no-publication hosted exercise will establish the changed handoffs.

## Evidence and stop condition

The release fixture covers two successive releases, legacy cutover, retained
fragments, cleanup, no-op replay, reserved versions, branch movement and identity
conflicts. Staging rejects code and third-party lock changes. Controlled GitHub
state interrupts publication before and after tagging and after an asset upload,
then checks unchanged digests on recovery. Existing registry cases cover partial
publication and uncertainty. A local HTTP endpoint verifies that Cargo uploads
the exact admitted archive.

Obsolete release-PR ordering and source-spelling assertions were removed.
Workflow tests retain pinned-source, publication-prerequisite and credential
boundaries. These tests extend existing suites rather than add a case per issue
bullet.

The actual cutover observation verified completed `v1.6.0`, source
`e927470be18c89638fa724d825cbb14eb72bff04`, with no partial stable release.
This used release attestations, retained completion receipts and matching public
registry bytes. The development manifest was not used as the version floor.

### Local staged exercise

At `307c2f1902359f27e5d412c1aa19bb0fe26b90ae`, an isolated Windows x64 checkout
was stamped from development `0.0.0.dev0` to release `1.7.0`. The native archive,
wheel, npm package, sdist and both Cargo archives built successfully. The native
artifact recorded the original source and verified staging transformation.

- Existing native installed-consumer tests: 6 passed in 21.82 seconds.
- Both Cargo archives passed package verification and isolated installation,
  including the first-contact journey and negative invocation/PATH checks.
- The sdist built an installed wheel in an isolated environment without Git
  metadata in 49.60 seconds; its first-contact journey passed in 4.73 seconds.
- The focused release/platform/registry/recovery suites passed 104 cases in
  12.82 seconds. Later staging-receipt checks passed 29 cases in 3.72 seconds.

These are local observations, not final-source hosted acceptance. Subsequent
changes bind hosted proof receipts to the verified staged diff and repair
development-version compatibility.

### Hosted exercise

The first source admission attempt exposed an invalid reusable CI job shape;
the dependent qualification was cancelled. The next CI attempt
([36628294055](https://github.com/rickardvh/agentic-workspace/actions/runs/36628294055))
exposed obsolete workflow assertions and development-version compatibility in
installed setup. Its waiting Release run was cancelled. Both defects were
repaired before starting the next exercise; no publisher ran.

At `ae05b9200`, merge proof, security, package checks and Planning handoff passed.
Admission then exposed an older skipped draft-PR check shadowing the successful
manual check for the same source. The checker now selects the newest attempt
independently of API ordering, with a regression that also rejects a newer failed
attempt. The waiting Release run was cancelled before builds or publication.

At `8ba123566`, source admission, all six staged platform builds, assembly and
all six compiler-free platform consumers passed in
[36631037294](https://github.com/rickardvh/agentic-workspace/actions/runs/36631037294).
The staged broad and Planning jobs exposed an import dependency in the test
artifact selector. Moving the first-contact import to its actual smoke-test
caller fixes that dependency; the inventory fixture now also exercises selection
in a fresh isolated Python process.

At `5ca807c1f3a618e018d533b94c2f422cb5ae3e24`,
[full CI](https://github.com/rickardvh/agentic-workspace/actions/runs/36632638924)
passed in 11m56s. The
[Release qualification](https://github.com/rickardvh/agentic-workspace/actions/runs/36632833911)
passed on attempt 2, retaining verified bundle `11064966084` with SHA-256
`3637aceefa9f0b8aa224e74c97279f0442f6ad604584b94aacc5c7757f3a0563`.
All six builds and compiler-free consumers, three runtime rows, broad workspace,
Planning handoff, independent-owner ingress, source-package and security checks
passed. The staged transformation was reverified after build and proof.
Publication jobs were skipped by `qualify_only`; no public delivery is claimed.

Attempt 1 stopped while observing completed `v1.6.0`. Fresh verification confirmed
all public package bytes and both completion receipts; a bounded failed-job retry
passed the unchanged admission check. The earlier failure remains in run history.

The successful attempt took 28m15s: source/version 1m19s; parallel platform builds
1m47s–5m56s; assembly 43s; longest staged consumer branch 12m59s; final package,
security and bundle qualification 6m57s. This records the bounded exercise, not a
historical speed ratio or production upload estimate. Three runtime replacement
builds are removed; those rows consume the six platform outputs. The two prepare
qualification passes and generated candidate dispatch are replaced by one staged
release qualification with exact-source merge admission reused.

Independent review identified recovery-guidance and current-continuation fixes
in [comment 5905350463](https://github.com/rickardvh/agentic-workspace/pull/3721#issuecomment-5905350463).
The follow-up is limited to that recovery helper, focused regression tests and
Planning/evidence reconciliation. The recorded hosted proof belongs to the exact
head above; the review calls for focused follow-up checks rather than repeating
the broad qualification. External independent acceptance remains outstanding.
