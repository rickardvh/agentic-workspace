# Reserve reproducible build output

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
