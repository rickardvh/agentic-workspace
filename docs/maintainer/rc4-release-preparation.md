# RC4 release preparation

Target: `v1.0.0-rc.4`, following the published RC3. This document prepares the
next candidate; it does not announce publication or stable support.

## Changes since RC3

- Use absolute GitHub documentation and license links in the shared README so
  the packaged description works on PyPI, npm, and crates.io.
- Include that README in the staged npm package and therefore the universal
  six-platform npm archive.
- Use the same product summary for Python and npm. Cargo retains the descriptions
  of its separate core and CLI packages.

## Version and publication

After this PR merges, use the existing `scripts/release/preview_release.py`
preparer with `--rc v1.0.0-rc.4` and the accepted merged source commit. Its native
resource procedure supplies any required isolation admission. The preparer
creates the release-only artifact commit and coordinates Python `1.0.0rc4`
with npm and Cargo `1.0.0-rc.4`, lockfiles, payload identity, and generated
release notes. Do not merge those artifact-only version changes into the source
branch or reuse the RC3 tag or package versions.

The existing release workflow builds all six declared native targets, checks
compiler-free Python/npm installs, and publishes the admitted GitHub artifacts
to the registries. Registry credentials use the configured trusted publishers
and existing environment approvals.

Before publication, inspect the final npm tarball's `package/README.md`, the
Python wheel's description metadata, and both Cargo archives' `README.md`.
After publication, check that each registry renders the description and its
documentation links. Update the repository's RC3 download notice to RC4 only
once the RC4 GitHub release is available.
