# Recover bounded or interrupted resources

Preserve the exact path after interruption. Reobserve it from a fresh process;
never retry an old expected_revision or create a replacement to recover uncertainty.
Known committed effects stay committed even if delivery fails. Missing native
runtime grants no alternate cleanup implementation.

Propose `scratch-remove` for the same exact task container. Its current custody,
retention, policy and owner references determine whether terminal cleanup is
permitted; temporary content size and file count do not. Carry the exact returned
action. Missing or invalid custody stays preserved for owner reconciliation.
There is no selected-file pruning step or alternate manual deletion procedure.

For `empty-interrupted` creation, reissue `scratch-create` with the same task and
exact derived path. The owner may finish marker publication only while that
directory remains empty. Missing custody never authorizes removal, and a
non-empty markerless directory remains preserved.
