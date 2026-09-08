# Native configuration residuals

The native pre-state reader already checks the exact supported
`cli_compatibility.contract_schema`. Successful admission consumes that field;
it must not then become a second unresolved configuration blocker. Invalid or
unsupported schemas, forward reader epochs and missing reader capabilities stop
before domain source interpretation, including under advisory enforcement.
Other compatibility controls retain their existing unresolved blockers: native
resource availability, source class, target relation and resolution-policy
observations have not been established. Advisory configuration is not permission
to discard required checks.

Remaining concrete owner gaps:

- `modules.enabled` is projected but not consumed by native domain dispatch.
  In particular, an explicit empty array currently escapes residual detection
  while domain readers still run. This is an unresolved enablement bug, not proof
  of disabled-owner behavior. Acquisition or suppression must preserve existing
  source obligations; this correction does not change module availability.
- `payload.policy="required-before-work"`, `target_release="source-current"`
  and installed capabilities still need the existing payload provenance/currentness
  owner. A native executable or matching package version alone is insufficient.
- `system_intent.sources` and `preferred_source` declare retained source authority
  used by the existing durable-intent owner. Native has no complete consumer for
  its current source records and interpreted intent. Preserve the source-backed
  unresolved consequence; do not classify prose lexically, discard governing
  intent, or rebuild its former mirror merely to remove a blocker.

These findings belong to #2613/#2767 and their current domain owners. They do not
establish ordinary configured-checkout completion or independent acceptance.
