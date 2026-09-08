# Native selected proof execution

Verification offers `verification/execute-selected/v1` only with exact commands from currently applicable manifest routes. The public request chooses a route and its declared command. The resulting `proof.report` operation explicitly declares process execution and receipt publication effects; it does not inherit the read-only report boundary.

The native adapter resolves the supported host shell, records the actual native executable and shell content identities, and uses the existing Rust proof-subject and receipt admission owners. Current selected strategy and exact declared source dependencies participate in freshness. Legacy Python receipts retain their Python recorder identity; native code does not substitute its executable or launch a receipt-selected interpreter.

Execution uses the existing proof-run and attempt-store contracts. Admission and completion carriers are immutable. Missing completion after interruption is uncertain, so retry never blindly runs a potentially non-idempotent command. A current committed invocation returns its exact effect result and freshly resolves continuation. Windows job objects and Unix process groups bound normal execution, timeout, and error cleanup; abrupt host loss still leaves an uncertain external effect rather than a guessed success.

The first native publication acquires an absent canonical receipt index exclusively. A pre-existing index without retained native mutation custody is preserved and blocks this execution route. A concurrent index winner is preserved after execution, leaving an honest unpublished result. No transfer or general index update mechanism is supplied here.

Ordinary results contain bounded process facts and an exact hashed artifact reference; output detail remains in the existing local run artifact. Process exit never produces task judgment, human acceptance, or independent review. Native freshness proves the declared source/command and observed producer/shell scope only. Nested tool environments, unresolved dependency selectors, and unsupported strategy obligations remain explicit gaps. Thus selected-command coverage is not complete strategy or claim sufficiency.

## Proof boundary

`tests/test_native_proof_producer.py` exercises native CLI, Python, Node, and JSON entry points, actual execution, immutable publication, fresh-process replay, current-source invalidation, exact command and runtime tampering rejection, existing index preservation, real interrupted execution, and failed/timeout retention. These deterministic host fixtures do not prove independent acceptance or the configured checkout's complete stateful Verification lifecycle. They do not establish that validation is cheaper than recomputation for a real expensive proof; that measurement remains required by #2981.

## Current compatibility and cost limits

The current native runtime identity includes the actual core executable hash and location. Reuse requires that exact currently observed runtime; no recorded executable path is read to manufacture compatibility.

Freshness records `validation_duration_us` separately from the execution's `duration_ms`. Hashing the current binary during selection and admission is real validation work. The fixtures prove reuse and scope rejection, not a net saving for their deliberately small commands.


The native CLI is an argv/JSON transport to its exact colocated
`agentic-workspace-core` executable. Python, Node and JSON consumers of that
same executable can reuse current command evidence and replay current committed
invocations without re-executing the command. The CLI does not link owner semantics,
search PATH, honor an alternate core environment override, or build a missing core.
Source development builds must build both binaries with
`cargo build --locked --workspace --bins`; wheel staging already includes both.
Windows uses a Job Object for child lifetime; Unix replaces the CLI process with
the core after preparing anonymous JSON stdin, without exposing packets in argv.

Executable location remains part of proof runtime identity. Byte-identical copies
at different installation paths remain explicitly incompatible in this slice;
package version equality never substitutes for actual executable identity. The
supported positive is one actual core executable across adapters, not arbitrary
independently built or relocated packages. A changed core at the same path stales
prior command proof and invocation replay. Process evidence still grants neither
task judgment nor independent acceptance.
