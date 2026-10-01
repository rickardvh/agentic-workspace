# Add a reusable capability

Use a module when a reusable AW capability needs its own facts, operations or
saved records. A repository-specific rule normally belongs in
[instructions or a skill](customization.md). A host integration belongs in
[Integrate an agent or tool](extension-boundary.md).

The supported independent-module interface is Rust:
`agentic_workspace_core::independent_owner`. The exact API keeps its existing
names; this page explains how to use it.

## Start read-only

Begin with a capability that reads one exact repository source and reports a
useful fact. This establishes discovery, repository configuration and behaviour
when that source changes before you add writes.

A module registration provides:

| Part | Purpose |
| --- | --- |
| `Registration` | Name, implementation revision, API version, and functions |
| `Description` | What the module can do, settings it accepts, and exact sources it needs |
| `Resolution` | Current facts, restrictions, requests and any prepared operation |

The [neutral example module](../tests/fixtures/native-independent-owner/src/lib.rs)
shows the public interface in use.

A read-only module needs no fake output file, write operation or skill.

## Repository configuration controls availability

Linking a module into the Rust binary makes its code available. A repository
still has to configure that module before it can participate in that project's
work.

Configuration declares the exact implementation, settings, source reads and
allowed effects. Missing or changed configuration should be reported explicitly,
not turned into an empty success result.

The Rust core gives the module current task information, configured settings,
observed sources and any typed request. The module interprets its own domain
facts; it should not decide how the coding agent implements unrelated work.

## Add a write only when the capability needs one

When a module must change something, define the request and operation schemas and
return the exact prepared operation for that request.

The core checks the current task, relevant source revisions, repository settings
and declared effects before execution.

A module may publish files under its own namespace when its API supports that. It
must not rewrite arbitrary project files or another component's records merely
because it runs in the same process.

For example, a module may produce information useful to Planning without creating
a Planning record itself. The caller can pass that information to Planning
through Planning's own operation.

## Skills are optional

A module may include a normal `SKILL.md` and relative resources. It may also
ship no skill. Procedure text does not grant permissions or remove runtime
restrictions.

A linked Rust module is trusted executable code, not sandboxed code. Review it
before including it in an AW build.

## Validate the module

Test:

- ordinary read behaviour;
- irrelevant or disabled absence;
- behaviour after a relevant source or setting changes;
- malformed requests;
- exact file creation and collision handling when the module writes files;
- recovery after an interrupted write when applicable.

Reuse shared core tests for shared behaviour. Add host or language-adapter tests
only for failures those adapters can introduce independently.

For lower-level implementation details, see
[Independent Rust components](maintainer/independent-native-owners.md).
