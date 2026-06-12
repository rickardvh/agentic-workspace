# CLI Boundary Tests

CLI boundary tests are wrapper tests. They prove that a shell-facing command faithfully presents and delegates to an already-tested operation layer; they are not the default place to prove operation semantics.

## Boundary

Operation conformance owns:

- JSON input, output, and structured error behavior;
- operation contracts and schema-coupled expectations;
- generated or compiled implementation artifacts;
- direct function/module adapters when an implementation artifact is importable;
- cross-artifact or cross-target parity after declared normalization.

CLI boundary tests own:

- argv parsing and option wiring;
- help text and user-facing error text;
- exit codes;
- stdout and stderr presentation;
- JSON/text mode wrapping at the shell boundary;
- command-name dispatch to the operation adapter;
- a small number of wrapper-to-operation smoke paths.

## Migration Rule

When a direct implementation adapter exists, operation behavior should run through operation conformance cases, not through a CLI subprocess. The CLI wrapper may keep one narrow smoke test proving that the command delegates to the operation artifact, but it should not duplicate the operation case matrix through argv.

Wrapper tests can assert that a command maps argv into the expected operation input and renders the returned result or structured error correctly. They should not repeat lower-level primitive assertions or every success/error/parity case already owned by operation conformance.

## Current State

The current operation conformance manifest still uses `cli.process` artifacts for migrated AW cases because the generated packages do not yet expose real importable operation functions for those cases. Those artifacts are explicitly marked `wrapper-smoke`; they are transitional proof surfaces, not the preferred semantic route.

When generated packages expose `python.function` or `typescript.function` artifacts, promote the affected cases to direct operation adapters and demote CLI coverage to boundary-only tests.

## Closeout Rule

Before removing or retaining an existing CLI-heavy regression, classify it as one of:

- operation semantic behavior to migrate to operation conformance;
- CLI wrapper behavior to retain as a small boundary test;
- adapter mechanics that belongs in command-generation or the adapter owner;
- duplicated regression bulk to delete with replacement evidence.

Closeout should name the retained owner. A broad statement that a CLI test "covers behavior" is not enough if the behavior belongs to operation conformance.
