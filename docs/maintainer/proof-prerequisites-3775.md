# Declared isolated proof prerequisites: #3775 evidence

On 2 October 2026, the candidate native producer on Windows selected real isolated
proofs against the prepared immutable Linux image already used by #3773. The
executor preserved read-only source and image, disabled networking, dropped
privileges and retained its existing writable scratch boundary.

The image identity was
`sha256:664812a80e822cf8a41798b18b7b4f2990da1d0d340247a2c65306f9bf322dab`.
Its genuine Git subject in the image's prepared repository was
`b4838e325757e523edbdccc51c27a769b8293f43`. Git bytes remained in the image,
outside each bounded source snapshot.

## Focused pass and failure observations

The finite fixture declared exact source files, an image executable and the Git
subject. Native Verification selected the route, returned the existing
`proof.report` action only when constructible, and published normal process
evidence after execution. Timings below measure native selection separately from
the selected command; they include source snapshot and Docker observation costs.

| Case | Selection time | Selected command | Command time |
| --- | ---: | --- | ---: |
| Omitted declared source | 204 ms | Not launched; named missing file | — |
| Missing image runtime | 1,335 ms | Not launched; named missing executable | — |
| Missing Git subject | 1,972 ms | Not launched; named path and revision | — |
| Complete environment | 2,054 ms | Passed | 290 ms |
| Complete environment, explicit failing assertion | 2,048 ms | Failed, exit 7 | 270 ms |

The failure was a real launched shell assertion. Constructibility did not turn
it into success or a missing-capability result. Rejection cases returned no
selected action and executed no selected command. Fixed capability probes may
run before selection; they never execute source scripts or the selected command.

## Original startup/Memory command

The second fixture used the repository's existing bounded `execution.inputs`,
prepared native pair and Python runtime, and declared the same exact Git subject.
It ran this original command with every assertion unchanged:

```shell
uv run pytest tests/test_native_memory_declarations.py tests/test_native_startup_adapter.py -q
```

An omitted exact source requirement blocked selection in 2,062 ms. Substituting
an unavailable declared Git revision blocked it in 2,288 ms. Neither launched the
suite. With complete prerequisites, selection took 4,432 ms and the command took
93,731 ms: **32 passed**, including the formerly failing admitted-Git-source case.
The process artefact had SHA-256
`f34d3a7ad14f5ea31712a30f0aa7d0273efde4d6b61afbf9c4bbc151ba21ebbd`.

The fixture controller retained a real admitted archive outside its snapshot and
installed the candidate package through native setup. Its configuration retained
the original CLI invocation, startup instruction filename, decision revision and
required payload policy consumed by the suite. This exercise did not substitute
host test results for isolated execution.

Two incomplete controller configurations were retained as failed evidence:
omitting payload policy produced 31 passes and one failure in 88,453 ms; restoring
that policy while still omitting the startup instruction filename produced the
same count in 89,323 ms. These undeclared configuration-content requirements were
normal runtime assertion failures. They are not counted as pre-launch success;
the executor checks declared capabilities and does not infer arbitrary test intent.
Earlier setup restrictions also prevented launch and were preserved.

## Validation and retention

The existing proof-producer suite passed **34 cases**, including actual Docker
confinement, source/runtime freshness, replay, failed commands and interruption.
Its existing isolated read case now covers omitted source, runtime and Git
requirements plus the complete environment. The existing source-transfer unit
test covers membership and confined path rejection. No provider/OS matrix,
repository-specific preflight or separate proof engine was added.

Focused domain-proof and declaration coverage passed 15 cases; the selected
test-evidence strategy command passed 25 cases in isolation. The current native
pair built successfully; Clippy and generation parity passed. This evidence
supports the declared pre-launch boundary, not complete inference of dependencies,
independent review or universal cost savings. The existing currentness checks
revalidate changing material automatically through the selected-proof lifecycle.

The one-off controllers, raw selections and native process artefacts remain in
task-owned scratch `5450a90060156dbc06e596469e4954e7f32db2b8e18f0d40fbbcfa2a89d7fe82`
for review. They are not new ordinary CI tests. No broader execution is needed
for this boundary without a named uncovered failure.
