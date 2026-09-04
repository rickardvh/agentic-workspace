# Agentic Workspace

Agentic Workspace v1 gives repository agents one source-first operating
decision and one typed operation transport.

```console
pip install agentic-workspace
agentic-workspace start --target . --task "fix the failing test"
agentic-workspace invoke --target . --invocation '<primary_action JSON>'
npm install @rickardvh/agentic-workspace
```

`start` reads only relevant source owners and returns one of five states:
`direct`, `actionable`, `decision`, `blocked`, or `terminal`. A `decision`
contains one owner-, revision-, and authority-bound human/domain question whose
answer is admitted through its declared operation. An actionable decision carries
the exact operation ID, typed values, effects, authority, current input revision,
and idempotency key. `invoke` executes that envelope directly and returns the
next decision after source-owner reconciliation.

Effectful invocation is serialized across processes, journaled before execution,
and replayed from a durable receipt. Interrupted effects use an owner-specific
recovery function or fail closed with the exact recovery owner. State files are
managed only after atomic creation, current-owner confirmation, or explicit
`workspace.transfer-ownership`; unknown and repo-authored content is preserved.

Planning, Memory, and Verification are logical modules delivered in the root
Python distribution. Third-party modules use the same
`agentic_workspace.modules` entry-point contract. Irrelevant modules contribute
nothing and do not appear in the decision.

Repository-scoped controls, selective anti-rediscovery Memory, semantic Planning
custody, Verification-owned proof strategy, and per-owner conclusion reuse are
described in [source-owner batteries](docs/source-owner-batteries.md).
Optional best-fit routing and host/shared-worktree handoff semantics are described
in [assignment and delegation](docs/assignment-and-delegation.md).

See [the v1 contract](docs/v1-contract.md), [module API](docs/module-api.md), and
[generated two-language contract](docs/generated-contract.md). Python,
TypeScript, and the JSON CLI project one semantic authority; external adapters
consume that boundary without registration or telemetry inside AW. See also the
[1.x compatibility policy](docs/compatibility-policy.md).

Repository maintainers can explicitly opt in to ignored, local CLI session
logs using `AW_SESSION_LOG`; see
[maintainer session logging](docs/maintainer-session-logging.md).
