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

The initial focused Windows run passed 55 cases in 6.14 seconds. This is local
deterministic evidence only. Real staged package builds, hosted handoffs, final
timings and independent acceptance remain to be recorded before completion.
No production release is required solely for validation.
