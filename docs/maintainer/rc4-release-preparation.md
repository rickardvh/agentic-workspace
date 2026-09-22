# RC4 release preparation

Target: `v1.0.0-rc.4`, following the published RC3. This document prepares the
next candidate; it does not announce publication or stable support.

## Changes since RC3

- Use absolute GitHub documentation and licence links in the shared README so
  the packaged description works on PyPI, npm, and crates.io.
- Include that README in the staged npm package and therefore the universal
  six-platform npm archive.
- Use the same product summary for Python and npm. Cargo retains the descriptions
  of its separate core and CLI packages.
- Keep the shared release-candidate notice version-neutral and link to GitHub
  Releases. Immutable RC4 packages must not advertise RC3 or depend on a README
  update after publication.

## Version and publication

After this PR merges, use the existing `src/tooling/release/preview_release.py`
preparer with `--rc v1.0.0-rc.4` and the accepted merged source commit. Its native
resource procedure supplies any required isolation admission. The preparer
creates the release-only artefact commit and coordinates Python `1.0.0rc4`
with npm and Cargo `1.0.0-rc.4`, lockfiles, payload identity, and generated
release notes. Do not merge those artefact-only version changes into the source
branch or reuse the RC3 tag or package versions.

The existing release workflow builds all six declared native targets, checks
compiler-free Python/npm installs, and publishes the admitted GitHub artefacts
to the registries. Registry credentials use the configured trusted publishers
and existing environment approvals.

Before publication, inspect the final npm tarball's `package/README.md`, the
Python wheel's description metadata, and both Cargo archives' `README.md`.
After publication, check that each registry renders the description and its
documentation links. Keep numbered current-RC announcements in release pages,
not in this shared README: all three registries embed it before publication,
and changing the source branch afterward cannot repair those immutable bytes.
