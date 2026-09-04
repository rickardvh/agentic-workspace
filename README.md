# Agentic Workspace

Agentic Workspace v1 gives repository agents one source-first operating
decision and one typed operation transport.

```console
pip install agentic-workspace
agentic-workspace start --target . --task "fix the failing test"
agentic-workspace invoke --target . --invocation '<primary_action JSON>'
```

`start` reads only relevant source owners and returns one of four states:
`direct`, `actionable`, `blocked`, or `terminal`. An actionable decision carries
the exact operation ID, typed values, effects, authority, current input revision,
and idempotency key. `invoke` executes that envelope directly and returns the
next decision after source-owner reconciliation.

Planning, Memory, and Verification are logical modules delivered in the root
Python distribution. Third-party modules use the same
`agentic_workspace.modules` entry-point contract. Irrelevant modules contribute
nothing and do not appear in the decision.

See [the v1 contract](docs/v1-contract.md), [module API](docs/module-api.md), and
[1.x compatibility policy](docs/compatibility-policy.md).
