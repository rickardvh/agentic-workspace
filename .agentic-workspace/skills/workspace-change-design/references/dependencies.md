# Choose and maintain dependencies

Use this reference with the [change-design method](../SKILL.md) before a
material package or toolchain decision. Revisit the affected choice if the
source, trust or support assumptions change during work.

- **Compare ways to meet the need.** Check what an existing dependency, the
  platform or a small local implementation can do. Compare a maintained package
  where it offers needed capability, expertise or future fixes. A built-in CSV
  parser may already handle the input. A maintained implementation can be the
  simpler choice for a specialist format or security-sensitive protocol.
- **Follow the dependency through the system.** Identify whether it runs in
  production, at build or test time, or only with an optional feature. Inspect
  relevant transitive dependencies, platform support, resource costs and
  distribution effects. Build and test tools can execute with substantial
  local access. Declare direct use as the ecosystem requires.
- **Establish identity and trust.** For a new source or changed trust boundary,
  verify the actual project and authoritative distribution channel. Consult
  current sources for applicable licences, runtime support, maintenance,
  advisories and any relevant install hooks, network access or executable
  effects. Popularity and activity provide limited evidence. If an unresolved
  identity or trust fact changes the decision, state the gap and preserve the
  applicable permission boundary.
- **Use the repository's dependency model.** Check its manager, manifests,
  groups, supported toolchain and lockfile conventions. A library's supported
  version range and an application's resolved versions can serve different
  purposes. Use the established tool to keep declarations, resolutions, build
  configuration and generated outputs consistent. Review relevant solver
  changes, including coupled updates, and keep unrelated upgrades out of scope.
- **Plan for updates and removal.** Choose versions from the task, supported
  environments and relevant security information. Read the meaningful changes
  for an update and account for coupled packages. Urgent security work may
  need a bounded update path within existing authority and required checks.
  Before removal, check actual users and remove obsolete declarations,
  resolutions and build or documentation steps. Keep user data intact.
  Preserve a bridge only for an actual transition. Vendored code still needs
  maintenance, provenance and licence handling.

Prepare the environment using the repository's established method. If a known
prerequisite does not reach its consumer, use the [working-rule procedure](../../workspace-setup-jumpstart/references/working-rules.md)
to connect it. Use [proof selection](../../workspace-proof-selection/references/select.md)
to verify the changed capability and material installation, packaging or runtime
effects. Successful resolution establishes that the manager found an environment.
Exercise the feature separately when its behaviour is the claim.
