# Add a reusable capability

An AW module adds a domain that needs its own facts, operations or retained state.
Use one when a capability should be reusable across repositories. A project rule
or a procedure usually needs only [instructions or a skill](customization.md).
Connecting an existing AW operation to an editor instead needs an
[external integration](extension-boundary.md).

The supported independent-module interface is Rust:
`agentic_workspace_core::independent_owner`. A module is linked into a native core
assembly. It is not a Python plugin, a dynamically loaded script or a set of
workflow hooks. Python and TypeScript clients can use its admitted requests
through that assembled core.

## Start with a read-only capability

The [neutral example module](../tests/fixtures/native-independent-owner/src/lib.rs)
is a separate crate using the public interface, without adding its identity to
core dispatch. Use it as a working source example alongside the
[owner API](../crates/agentic-workspace-core/src/independent_owner.rs).

Begin with a capability that observes one exact repository source and reports a
bounded fact. That lets you establish discovery, repository authorisation and
source-change behaviour before adding writes.

The implementation has three parts:

| Part | What you provide |
| --- | --- |
| `Registration` | Owner name, implementation revision, API version, and the `describe` and `resolve` functions. |
| `Description` | The capability descriptor, optional settings schema and exact source paths it needs. |
| `Resolution` | Current facts, restrictions, request templates and, when applicable, a prepared operation. |

Register through the exported `submit!` macro. The assembly links the module crate
and calls the shared `transport::run_stdio`; the standard CLI runs beside that
core binary. Adding an independent module therefore requires rebuilding the
assembly. The default distribution contains no independently registered owners.

A facts-only implementation returns its facts and leaves the other `Resolution`
fields empty. It needs no dummy operation, output file or skill.

## Authorise use in a repository

Linking code makes it available; it does not give it access to every repository.
The repository separately authorises the exact implementation and descriptor,
scope, source reads, effects, claims, restrictions and durable settings through
`modules.independent`.

Use the current Configuration requests to inspect and propose that configuration.
Do not copy a grant from an unrelated example. Missing, changed or revoked
authorisation must remain visible rather than turning into an empty successful
result. Unrelated modules should stay out of the current query.

The core supplies `Context`: current work, admitted settings, freshly observed
sources and an optional typed request. Keep semantic decisions with the agent or
human. `resolve` interprets bounded domain inputs; it is not a callback for
choosing how the agent should perform a task.

## Add an operation only when needed

Declare its request and operation schemas, then return a `PreparedOperation`
when the current request supports it. The caller submits an intention; the module
prepares the exact action and result. The core checks the work, sources, settings,
authorisation and declared effects before execution.

For retained output, `Publication` supports immutable acquisition under the
owner's namespace. It does not permit replacing an arbitrary file, rewriting an
input source or modifying another module's state. Such changes need the relevant
owner's supported update operation. A read-only computation need not publish
anything.

For example, a module can return material suitable for a plan without creating a
Planning record. The caller then submits that material through Planning's own
creation request. This keeps the two capabilities independently responsible for
their state.

## Procedure, safety and validation

A module may include an ordinary `SKILL.md` and relative resources, discoverable
through the existing skill registry. It can also ship no skill. Removing or
bypassing a procedure must not remove the module's restrictions.

A linked native module is trusted executable code, not sandboxed code. Review it
before assembly. Publication constraints are not protection against malicious
Rust code running in the same process.

Validate ordinary observation, irrelevant/disabled absence, changed source or
authorisation, and malformed requests. An effectful module also needs evidence
for exact publication, collision preservation and interrupted recovery. Reuse
core contract coverage; add adapter tests only for distinct transport risks.

The [authoring and recovery reference](maintainer/independent-native-owners.md)
explains immutable publication and retained effects in more detail. The
[architecture](architecture.md) explains why modules share one execution boundary
without sharing ownership of each other's data.
