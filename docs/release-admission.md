# V1 release admission

A v1 release is admissible only when `make release-check` succeeds from a clean
checkout. The gate builds the wheel and source distribution, installs the wheel
in a fresh virtual environment, and exercises the installed product outside the
source checkout.

The gate proves:

- the artifacts contain one runtime and no generated host state, package
  workspace, or checked-in `.agentic-workspace` payload;
- the CLI and Python API compile the same decision from the same source input;
- direct work is stateless;
- local maintainer session logging is absent by default and captured only after
  explicit opt-in;
- pre-v1 removal is a bounded typed operation that preserves unknown content;
- planning cannot become terminal until declared verification succeeds;
- a separately packaged module can compile a bounded child operation for a
  Planning-owned parent, reconcile structured worker evidence, reject stale
  child work, replay completed work without re-execution, and return control to
  the parent's ordinary proof/completion path through the same entry-point seam
  as first-party modules;
- operation results carry the next decision, including the terminal answer; and
- uninstall removes the executable without deleting repository-owned content.

## Contraction measurements

The v1 branch changes the review surface from four Python distributions to one,
from 129 public command routes to two, and from 4,134 tracked files to 44. It
removes the 809-file generated tree, the 1,903-file installed host payload, all
258 sibling-package files, and more than 1.19 million tracked lines. The complete
surface and ownership disposition is recorded in `docs/v1-disposition.md`.
These measurements are review aids; the executable admission gate is the release
authority.

## Review boundary

The release PR must be reviewed independently of the implementation author. A
reviewer should evaluate the machine-readable conformance result, the supported
surface in `docs/compatibility-policy.md`, and the stacked diffs before approving
the release. A green gate is required but does not substitute for that review.
