# Agentic Workspace 1.x compatibility policy

The supported 1.x surface is the contract proven by the release conformance
suite:

- the `start` and `invoke` CLI commands;
- `Workspace.start` and `Workspace.invoke`;
- the generated `agentic-workspace` Python package and
  `@rickardvh/agentic-workspace` TypeScript package projections;
- the implementation-independent semantic IR kinds, contribution dimensions,
  operation identities, currentness/effect rules, and additive-field behavior;
- canonical decision, revision, and idempotency identity using the packaged IR;
- bounded decision requests and owner-admitted, stale-safe responses;
- process-safe durable commit/replay and acquired state-path ownership semantics;
- the operating decision, operation invocation, and operation result v1 shapes;
- the `agentic_workspace.modules` entry-point seam;
- preservation of unknown repository-owned content during removal.

Pre-v1 state, commands, package names, generated runtimes, import facades, and
migration readers are unsupported. Recognizable package-managed pre-v1 markers
produce one typed `workspace.remove-legacy` action. That operation removes only
known package-managed markers and preserves unknown content. Reinstalling the
current package is the recovery path for a missing or incompatible runtime.

Within 1.x, normalized unknown additive fields remain compatible. Unknown
required capabilities or semantic variants fail closed with an exact upgrade
route. Incompatible changes to the supported surface require a deprecation
period and a new schema or operation version. Internal file layout, rendered
detail, and undocumented implementation symbols are not compatibility promises.
