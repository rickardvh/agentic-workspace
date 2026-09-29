# Validate the release replacement

Issue [#3719](https://github.com/rickardvh/agentic-workspace/issues/3719) replaces
release-only Git history with a source commit, deterministic stamping inputs and
an admitted artifact inventory. Independent review and hosted evidence remain
required before closure.

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
                                  └─ source and installed-owner checks
              → Cargo source packages and package/security checks
              → retained verified bundle → source tag and GitHub upload
                                        ├─ PyPI/npm publication and verification
                                        └─ Cargo publication and verification
              → coordinated completion receipts
```

One broad qualification path replaces the prepare/candidate/post-merge cycles.
The generated branch, release commit, release PR and follow-up dispatches are
removed. Runtime rows consume assembled artifacts instead of rebuilding wheels
and npm packages. Cargo publication sends the admitted archive through the
[registry API](https://doc.rust-lang.org/cargo/reference/registry-web-api.html#publish).

The platform rows, Python runtime rows, Node semantic majors, source-package
rebuilds, installed-owner tests, isolated consumers and security checks remain.
Staging is checked before packaging and after qualification. Build jobs have
read-only permissions. Publishing jobs hold their own destination authority.

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
in a fresh isolated Python process. Final run observations are linked from the PR.

Final hosted handoffs, timings and external independent acceptance remain
required before completion. No production release is required solely for
validation.
