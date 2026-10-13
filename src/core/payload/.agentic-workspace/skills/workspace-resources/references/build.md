# Reserve reproducible build output

For source-checkout proof in the existing checkout, reserve separate scratch
containers **before** compiling when receipts must outlive build/cache output.
Use `scratch-create` for the evidence task and for its distinct bounded compilation
subtask through [the resource operation](operation.md). Record each returned
path with its original target/task/changed context; different tasks have different
authenticated containers. A subtask must describe the real compilation work,
not fabricate a task identity to delete existing retained material.

Place Cargo's reproducible output in the compilation container, for example
`CARGO_HOME=<returned build path>/cargo-cache` and
`CARGO_TARGET_DIR=<returned build path>/linux-build`. Put command results,
failed-attempt evidence and any needed transport packets in the evidence
container. Use `scratch-retain` with the actual continuing need on that container.
After compilation/proof, propose `scratch-remove` for the exact compilation path
under its original context and invoke the returned action. Whole-container removal
owns those temporary directories; `scratch-prune` only selects bounded regular
files and cannot remove a build directory. Confirm output cleanup and preservation
of the evidence and its owner references before claiming separation succeeded.

The native read-only Docker proof already keeps its reproducible output in its
temporary volume and publishes receipts through Verification; use that existing
executor when selected. Do not add another scratch copy of its build output.
If an earlier run mixed retained evidence and build directories, preserve the
container until its current owner resolves retention; this preparation pattern
does not authorize moving references, sweeping directories or force deletion.

Before creating an isolated checkout used for build/test work, request
`disposable_outputs` with the exact reproducible output roots this task needs,
for example `dist` and `tool-cache/generated`. Declare at most sixteen normalized
repository-relative paths. Roots cannot overlap, traverse links, occupy protected
or tracked paths, or contain pre-existing material. AW establishes each root empty
at creation and binds its exact lifetime in the Git worktree custody. A cleanup
request cannot adopt an existing directory; ignored status supplies no authority.

Use returned `build_environment` conveniences when leasing `target` (Cargo and
Python bytecode) or `.venv` (uv). Leasing `.pytest_cache` covers pytest's ordinary
cache. Custom roots supply lifetime ownership, without invented environment
settings. Keep required outputs and user artifacts under their actual owner.

Terminal cleanup removes only these creation-leased reproducible roots before removing the clean worktree. Unknown ignored paths, tracked files added under output roots, and current owner references still block removal. A failed cleanup reobserves the same registration and remaining roots; it does not recreate the checkout or erase unowned output.
