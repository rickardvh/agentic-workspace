# Modules

[Try repository customization before adding a domain owner](../customization.md) with the receipt-format example.

Modules own domain facts, typed requests, operations and results. Skills supply
optional method. Read the [native module contract](../module-capability-contract.md)
for the exact supported authoring path and [extension boundary](../extension-boundary.md)
for repository customization and adapters.

Planning, Memory and Verification are bundled first-party examples, not required
extension slots. A neutral read-only owner needs no publication, action hook or
workflow phase. An effectful owner declares its domain effect and returns a prepared
operation; native core and repository admission retain authority and recovery.

Linking a module makes code available. Configuration separately admits exact
revision, scope, reads, settings and grants. A module may ship ordinary skills and
relative resources through passive discovery, without native name registration.
It may also ship none. Direct clients use current owner requests and exact actions.
