# CLI Boundary Tests

> Maintainer contract at a compatibility path. This page is not public product doctrine; it remains here because generated-behavior contracts name it as the wrapper-test owner.

CLI boundary tests are wrapper tests. They prove that a shell-facing command faithfully presents and delegates to an already-tested operation layer; they are not the default place to prove operation semantics.

## Boundary

Operation conformance owns:

- JSON input, output, and structured error behaviour;
- operation contracts and schema-coupled expectations;
- generated or compiled implementation artefacts;
- direct function/module adapters when an implementation artefact is importable;
- cross-artefact or cross-target parity after declared normalisation.

CLI boundary tests own:

- argv parsing and option wiring;
- help text and user-facing error text;
- exit codes;
- stdout and stderr presentation;
- JSON/text mode wrapping at the shell boundary;
- command-name dispatch to the operation adapter;
- a small number of wrapper-to-operation smoke paths.

## Migration Rule

When a direct implementation adapter exists, operation behaviour should run through operation conformance cases, not through a CLI subprocess. The CLI wrapper may keep one narrow smoke test proving that the command delegates to the operation artefact, but it should not duplicate the operation case matrix through argv.

Wrapper tests can assert that a command maps argv into the expected operation input and renders the returned result or structured error correctly. They should not repeat lower-level primitive assertions or every success/error/parity case already owned by operation conformance.

## Current State

The current operation conformance manifest uses direct `python.function` and `typescript.function` artefacts for `defaults.report` cases that have generated operation callables. Those artefacts are the semantic proof route for the migrated defaults behaviour.

Remaining `cli.process` artefacts are explicitly marked `wrapper-smoke`. They prove wrapper presentation, transport, mutation-effect boundaries, or transitional cases that do not yet have direct operation artefacts. When generated packages expose additional `python.function` or `typescript.function` artefacts, promote the affected cases to direct operation adapters and keep CLI coverage boundary-only.

## Closeout Rule

Before removing or retaining an existing CLI-heavy regression, classify it as one of:

- operation semantic behaviour to migrate to operation conformance;
- CLI wrapper behaviour to retain as a small boundary test;
- adapter mechanics that belongs in command-generation or the adapter owner;
- duplicated regression bulk to delete with replacement evidence.

Closeout should name the retained owner. A broad statement that a CLI test "covers behavior" is not enough if the behaviour belongs to operation conformance.
