# Manual Delegation

Use this only when a current assignment permits manual transport.

Manual transport is a prepared assignment step, not a clarification prompt and
not permission for the orchestrator to implement the worker slice locally.

1. Resolve the assignment policy and manual-transport admission before rendering a handoff.
2. Export the current assignment packet through the canonical assignment export operation; do not copy planning prose as a substitute.
3. Import a returned packet into `received/awaiting-admission`; import never proves, admits, integrates, or closes work.
4. Follow `planning-returned-result` to admit, reject, repair, reassign, supersede, or integrate the return.
5. Keep worker claims separate from AW proof, intent satisfaction, and closeout authority.
6. If the binding assignment forbids the current target, stop after export or
   import; only an authorised structured override can change that gate.

If transport is disabled, do not render or copy a handoff. Use the assignment policy recovery route instead.

## Bounded native worker context

For an exported native Assignment packet, the configured AW invocation exposes
`worker --input <json> --format json`. A thin host holds the exact packet; the
model receives only the `view` from `{action: "entry", packet}`. Small captured
inputs are inline. Read every required lazy input using `{action: "expand",
packet, reference: <detail_ref>}` before doing the assigned work. Expansion
returns exact captured bytes, not fresh repository admission.

Return only new `summary`, `changed_paths`, `patch`, `stop_conditions_hit` and,
when needed, `result_delivery` material through `{action: "return", packet,
material}`. The host submits the returned exact `reentry` to `start` at the
current repository target. Assignment still validates source, identity, scope
and result shape; presentation and matching seals never prove acceptance.

If carriage is lost, reconstruct/export through the current Assignment and
Planning owners. Do not repeat target selection or startup onboarding when the
current assignment still binds, and never repeat an uncertain launch to replace
missing transport. A re-export is not an executed result. Keep returned or
integration-pending work with Planning until responsible owner consumption.

The helper reports known serialized presentation/packet bytes and zero helper
writes. Host-injected skills, actual semantic turns, user steering, repairs and
elapsed time are unknown unless the consumer observes them; do not report unknown
cost as zero. This surface does not add host-native launch or provider economics.
