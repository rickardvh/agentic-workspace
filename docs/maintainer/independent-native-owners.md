# Independent native owners

An independent owner supplies deterministic Rust semantics through
`agentic_workspace_core::independent_owner`. The product still has one executable
authority. Python, TypeScript, JSON and the native CLI project that same runtime.
The separate crate in `tests/fixtures/native-independent-owner` exercises this
boundary without putting its owner names in product dispatch.

## Installation and admission

A Rust crate registers a compact `Registration` using the exported `submit!`
macro. Its assembly links the crate and calls the shared `transport::run_stdio`;
the standard native CLI runs beside that assembled core binary. This requires
rebuilding the native assembly. It does not load Python entry points or execute
schemas as policy. The default product assembly contains no independent owners.

Linking makes an implementation available. The repository separately admits its
revision, exact descriptor digest, reads, effects, exclusive claims, restrictions,
scope and durable settings in `modules.independent`. Declared capabilities do
not supply these grants. Current Configuration requests read and propose changes
to that source; settings requirements return that same owner route. Configuration
retains its exact bounded human-answer authorization for a write.

First-line discovery inspects compact identities and admitted scopes. A relevant
changed path or explicit current owner request selects detail; other installed
owners do not load their schemas or resolve. Detailed sources are bounded exact
references, reobserved on every entry, including absence. Task prose does not
select a module. Explicit requests for removed, unadmitted or incompatible owners
fail closed with a restoration/admission explanation.

## Owned operations

An owner describes its public request schemas and operation contracts, and
resolves bounded current values in Rust. Core binds the returned request and
prepared operation to current work, source observations, settings and admission.
Clients return the typed intention and invoke the exact resulting action.
Unknown request kinds, altered identities, extra actor labels and manufactured
invocations cannot replace current owner admission.

The existing capability compiler checks domains, effects, exclusive claims and
restriction grants. An independent domain is its owner identity. The publication
adapter confines immutable material to that owner's module directory; it never
hands the implementation a target directory capability. Startup and applicable
scoped instructions govern the resulting publication and custody writes.

This is a boundary between admitted native implementations, not an operating
system sandbox for malicious Rust code. A module must be reviewed as executable
code before assembly admission. No registration or publication receipt implies
authenticated human identity or human deciding authority.

## Publication and return

Read-only results create no durable state. Effectful results use immutable
owner-namespaced sources and the existing attempt store. The complete carrier is
bounded before effect admission. Publication acquires an absent destination;
foreign content is preserved. Exact prepared and published carriers retain the
original attempt through finalization and replay. A committed source that has
disappeared requires an owner restoration decision. An interrupted admission
without a complete carrier remains explicit uncertainty; a guessed filename or
client-supplied custody label cannot repair it.

This adapter supports immutable output acquisition. It rejects publication over
a declared input source before admission. Mutable source updates and ownership
transfer need the responsible owner's update/reconciliation contract; they are
not inferred from a directory or a prior publication.

Foreign-domain material is returned as evidence. For example, the fixture can
return Planning material without creating a Plan. The caller must submit that
material through Planning's current creation request and invoke Planning's own
action. The independent result grants neither Planning custody nor Verification
claims.

This advances #2606/#2986 under #2983/#3020. It does not establish cumulative
parent acceptance, external platform support or release admission.
