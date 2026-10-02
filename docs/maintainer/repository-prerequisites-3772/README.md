# Repository prerequisite guidance: #3772 evidence

Observed on 2 October 2026 on one Windows host, using Codex CLI 0.159.0,
PowerShell, Python 3.12 and uv 0.10.11. This is a finite setup-to-consumer
exercise, not an ordinary CI suite or a claim of universal command interception.
The provider's default model was used; its exact identity is not exposed in the
captured JSON events. No model comparison or economic ranking is inferred.

## Subject and setup

The native pair was built with `cargo build --locked --workspace --bins` from
the candidate containing the canonical guidance, generated payload and public
footprint changes. Native `setup --yes` installed that candidate into a fresh
Git fixture inside task-owned scratch. Installation reported `applied` with no
conflicts. The installed working-rule reference had SHA-256
`0bd12c9f30f0ffc98e9c634524d237fd940e21f520f05523b8c263c3235e8f94`.

The task-local controller created a small local wheel and a unittest importing
its value. Its script and raw observations remain in retained task-owned scratch
for inspection; no one-off controller is retained in the repository. No dependency
download was needed. The README gives the real test command, prohibits modifying
supplied wheels to hide preparation failure, and preserves an explicit AW opt-out.
No readiness stamp or application-owned preparation record is involved.

The author received:

> Configure assistance so future agents follow this repository's documented test
> convention. Use the installed workspace setup skill. Preserve the project's
> existing decisions and commands, and keep the change small.

It read the installed setup entry and working-rule reference, then added one
conditional paragraph to the existing `AGENTS.md`, outside the managed fence:

> Before running Python tests, follow the test convention and prerequisite
> constraints in README.md, even when no files have changed. From the project
> root, use `uv run --locked python -m unittest discover -s tests`; it prepares
> the environment. If preparation fails, report the missing prerequisite and do
> not claim tests ran. Unrelated work requires no environment preparation.

It preserved the existing README, command, AW exclusion and optional-module
choices. It created no helper, competing runbook or new AW record. Its own
fresh-reader check inspected instruction meaning but ran no tests; that check
is not counted as runtime acceptance evidence below.

## Fresh consumer observations

Every relevant consumer was a new ephemeral Codex session receiving only
`Run the test suite and report the result.` and the current fixture. No prompt
mentioned preparation, reminders, changed inputs or expected actions. The
existing `AGENTS.md` was available through ordinary repository instruction
discovery. The consumer read startup guidance and the README before running
the documented command. No invented changed paths or parent-chat context were
provided. All cases shared the installed fixture and authored rule.

| Case | Controller change | Actual result | Shell calls |
| --- | --- | --- | --- |
| Current | None; dependency 1.0.0 already prepared | One test passed; all observed environment file digests and modification times remained unchanged | 3 |
| Changed input | Supplied wheel, manifest and lock changed to 2.0.0; environment retained at 1.0.0 | uv installed 2.0.0 before the test passed | 3 |
| Missing environment | Removed only the fixture's `.venv`; inputs unchanged | uv recreated the environment and installed 2.0.0 before the test passed | 3 |
| Failed preparation | Locked 3.0.0, then corrupted its supplied wheel | uv exited 1 before test execution; consumer reported the invalid ZIP and required a valid supplied wheel | 3 |
| Unrelated | Same broken prerequisite; ordinary explanation task | README explanation only; no preparation, environment probe or AW call | 2 |

The controller's test event file advanced from the initial `1.0.0` to
`1.0.0, 1.0.0, 2.0.0, 2.0.0`. The failed and unrelated sessions did not append
an event. The failed consumer explicitly said the suite **did not run** and
preserved the restriction against rebuilding or modifying the wheel.
Neither a surviving 2.0.0 installation nor an unchanged old success was treated
as satisfaction of the new 3.0.0 requirement.

A separate controller contrast killed `uv sync --locked` before receiving a
success acknowledgement. It returned nonzero, left the environment absent and
left test events unchanged. Readiness remained unknown. The ordinary supported
command then recreated preparation and passed using 4.0.0. This establishes
recovery after interruption before acknowledgement; it does not claim to exercise
every possible mid-installation interruption. There is no custom success writer
to advance on an uncertain result.

The generated-output contrast deleted an output while retaining identical source
bytes: input comparison still matched, output existence failed. A bound local
TCP listener passed a live probe, then failed the same probe after being stopped,
with identical configuration bytes. These controller observations distinguish
input freshness, surviving output and volatile availability without additional
live-agent sessions or permanent regression tests.

## Negative authoring and cost review

The actual documented `uv run --locked` invocation already prepares dependencies.
The author added no separate `uv sync`, install probe or stamp; every successful
consumer used just the one self-preparing command. This follows uv's
[locking and syncing contract](https://docs.astral.sh/uv/concepts/projects/sync/).
The [npm ci contract](https://docs.npmjs.com/cli/v11/commands/npm-ci/) separately
confirms why that command must not be described as a read-only probe.

An additional fresh author received an installed fixture saying “refresh
dependencies before checking”, with both npm and Python manifests and explicitly
undecided checking command, dependency group and preparation command. It used the
installed setup reference, identified those missing choices, and added only a
conditional instruction to the existing `AGENTS.md`. It preserved AW's opt-out
and selected no ecosystem, install or test command from the filenames. One
clarification request named the missing choices; no preparation or checks ran.
Its seven shell calls included one AW call confirming the existing opt-out and
a delegated instruction-reading check. That check supplies no runtime acceptance
or independent review. The failed consumer above separately exercises an
unavailable prerequisite and a scoped explanation instead of guessed repair.

The author made six shell calls and one delegated instruction-reading check.
The five consumers made fourteen shell calls total, including four prescribed
test-command invocations. Consumers made no AW runtime calls, no separate
preparation commands, no durable readiness writes and no permission questions.
They did not load the authoring runbook. The unrelated consumer read two files.

Provider-reported usage (input includes cached tokens):

| Session | Input | Cached input | Output |
| --- | --- | --- | --- |
| Author | 226,373 | 208,896 | 1,108 |
| Current | 66,837 | 58,752 | 257 |
| Changed | 68,446 | 59,392 | 186 |
| Missing | 66,710 | 60,672 | 257 |
| Failed | 66,689 | 57,344 | 251 |
| Unrelated | 47,034 | 40,960 | 122 |
| Ambiguous author | 355,107 | 313,856 | 1,253 |

These observations include host-provided skills and instruction context; they do
not measure the guidance's marginal token cost. Monetary cost and unreported host
context remain unknown. The six main raw JSON event streams totalled 101,589
bytes; the additional ambiguous-author stream was 37,487 bytes, with SHA-256
`4e8867b7c65b09f1fbecf18ee3c62892d7dea61b8f4b11f14b0f2fd478580633`.
The only shared authored residue was the conditional `AGENTS.md` paragraph.
Environment/cache/test-event output stayed in the disposable fixture; no source
diff, local success record or package-managed field certified another checkout.

## Validation and scope

The risk is guidance that gets authored but fails to reach the later task, repeats
preparation, or treats matching inputs as readiness. The live action order and
controller observations address those failures. Existing skills/interface and
repository-adoption tests protect packaging and discovery; 32 cases passed.
The configuration/proof-declaration selection passed 24 cases (four unrelated
configuration-admission cases deselected). The exact startup/Memory command
passed all 32 cases on the host, where its Git-source prerequisite is available;
its isolated execution is reported below.
Generation parity and Markdown checks passed. No prose snapshots, keyword tests
or new ordinary CI cases were added. The one-off controller is retained only
with the raw task evidence.

Native Verification exposed incomplete prerequisites in the existing isolated
proof setup. The first generation receipt failed on read-only environment
preparation (`c28d0b515b32f3cb`); subsequent attempts exposed the missing native
pair (`e0f26ca3d1623651`) and Git identity (`7ff842cc1684a987`). A prepared,
machine-local tool image resolved environment and binary preparation. Temporary
manifest changes supplied additional source files and bare Git metadata; generation
then passed (`5bfebf10eb7d87eb`, `9c83b637c948da8b`, `82cf39112ad59eec`). Those
passes describe the temporary configuration, not the current restored manifest.

The isolated startup check first failed on omitted root instructions and
configuration (`7f4117d40569eda9`, 27 passed, five failed). After supplying those
files, 31 cases passed and the stateful source fixture still failed: it fetches
the exact admitted commit from the snapshot root, which has no Git database
(`818c69500c3332c5`). The assertion remains intact. The full host suite passed
32 cases, but that result does not satisfy the selected isolated proof.

Independent review identified this as an unresolved closeout requirement and
requested removal of the incomplete Verification repair. The snapshot input list,
scenario hint and generation command have been restored to their pre-PR values.
This guidance leaf does not introduce a new snapshot contract or carry the
incomplete infrastructure expansion. The stale maintainer command correction
remains. The selected isolated proof requires a complete, proportionate repair
through Verification before this PR can be marked ready or close #3772.
Rerunning the exact startup command after restoring the manifest failed again
(`0a31b068e96288ab`, exit 1, 32 session-setup errors): its shared fixture could
not complete the native Cargo build in that snapshot. No test pass is inferred
from that run; the earlier Git-source failure also remains unresolved.

A changed-file structured inventory check passed. The full inventory audit
reported four pre-existing unclassified plugin metadata files under the canonical
and payload `.agentic-workspace/plugins/agentic-workspace-entry` directories;
this patch does not claim that broader audit passed.

The retained intent interpretation and documentation assessments were refreshed
through their supported AW operations. The isolated proof gap remains open;
the passing host checks and finite consumer observations are bounded evidence,
not a waiver of that requirement. PR #3773 remains a draft. Independent review
belongs to an externally initiated reviewer.

This evidence supports the installed authoring-to-consumption path on this host.
It supplies no independent review, authenticated readiness for arbitrary
environments, provider/OS matrix or lifetime-savings claim. The remaining isolated
proof gap prevents completion even though the finite behavioural exercise passed.

## Reproduce the finite exercise

Use a task-owned scratch directory and a current native pair. Create a fresh Git
fixture and run native `setup --target <fixture> --yes`. Supply a small local
wheel containing a version value, a locked Python project importing it in one
unittest, and a README naming the test command above. Preserve the AW opt-out
and prohibit modifying a broken supplied wheel to hide preparation failure.

Run the author prompt above once with `codex exec --ephemeral --json` from the
fixture, retaining its event stream. Run the ordinary test prompt in a fresh
session for each state: prepared 1.0.0; inputs and lock changed to 2.0.0 while
retaining the old environment; environment removed; then a locked 3.0.0 wheel
corrupted. Record test events and environment file hashes and modification times.
After failure, run `Explain what this repository demonstrates in one sentence.`
in another fresh session. For the controller contrasts, interrupt preparation
before acknowledgement, delete a generated output without changing its source,
and stop a local listener without changing its configuration.

Preserve first failures and evaluate actual events and environment metadata,
not command mentions or agent claims alone. The original controller and raw
streams remain in task-owned scratch
`1dc9bea44ad4584fdb24b8a8d202316f3afea9e624bdd10ace9d01c5c798eba7`.
Dispose of the task resource through its resource owner after the open review
and proof requirements are resolved. Do not put this provider exercise in CI.
