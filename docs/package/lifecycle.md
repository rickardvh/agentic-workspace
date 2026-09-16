# Repository integration lifecycle

Configuration owns first adoption, refresh, removal, and interrupted recovery through current requests and actions returned by `start`. The native CLI catalogue remains the command authority; historical `init`, `install`, `upgrade`, and `uninstall` are not public commands.

In a plain Git working tree, resolve `start` and follow Configuration's `repository_adoption_request`. Select its exact adoption request, inspect the proposed files and preserved state, supply the authorization judgment, and invoke the returned action. Existing user instructions remain outside the managed fence. No config, optional modules, Planning, Memory, or Verification state is created.

Repeat adoption to converge the same public footprint. A current footprint is a no-op. A stale request or modified owned surface requires fresh resolution; unknown and edited content is preserved. Retired source-maintenance payload is removed only when its bytes match the contract's exact known preimage.

Removal uses the same discovery and exact removal request, with an explicit preserve disposition for independent repository, domain, and local state. Remove authenticated native skill-discovery links through their existing Configuration requests first. Removal preserves unknown files and all text outside the managed instruction fence. It does not reset domain history or delete the `.agentic-workspace` tree recursively.

An interrupted effect exposes an exact recovery request bound to its original custody and preimages. Recovery accepts only the recorded preimage or intended postimage. A conflicting edit is preserved. After removal, deliberate adoption works again without a tombstone reset.

See the [public surface catalogue](../reference/installed-surface-catalogue.md) for current file ownership and the [source-maintenance inventory](../reference/source-maintenance-surface-catalogue.md) for historical maintenance profiles. Those profiles do not describe the public host contract.
