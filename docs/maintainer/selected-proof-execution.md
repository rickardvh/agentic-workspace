# Selected proof with protected files

Verification can execute a selected command while Instructions protects repository
files. Configure `execution` in `.agentic-workspace/verification/manifest.toml`:

```toml
[execution]
kind = "docker-readonly-source-v1"
inputs = ["src", "tests", "pyproject.toml", "uv.lock"]
scratch_paths = ["target"]

[execution.environment]
RUSTUP_TOOLCHAIN = "1.98.1"
```

Pin an available Linux Docker image with `execution.image`, or use Configuration's
`proof_execution.image` choice in `config.local.toml` for a machine-local pin.
Use an immutable `sha256:<digest>` or `repository@sha256:<digest>`. The image must
contain the command's offline dependencies, `/bin/sh`, `/usr/bin/env`,
`/usr/bin/timeout`, and `/usr/bin/setpriv`. Images with declared volumes are refused.
The existing consumer-image preparation under
`src/tooling/model-cli-harness/sandbox/consumer/` supplies tool-specific starting
points. Preparing an image does not execute or admit the selected proof.

## Enforced boundary

The native owner reads the declared regular files through a confined directory,
rejects links and special files, and binds their exact bytes into the proof
subject. The snapshot is bounded to 128 MiB and 20,000 entries. Directories are
expanded within those bounds. Inputs must include the dependencies that the
selected command needs; missing inputs cause a failed command or capability gap.

A stopped staging container receives the snapshot in a new private Docker
volume. It never runs repository code. The proof mounts that volume read-only,
with a read-only root filesystem, no network, and no host directories, Docker
socket, or inherited host credentials. The image and Docker transport are observed
alongside the source snapshot. The Docker daemon and pinned image are trusted
execution prerequisites; the repository command is the confined workload.

The command runs as UID/GID 10001 with no supplemental groups or capabilities.
A root deadline supervisor bounds execution even if the native caller is killed;
the command cannot signal that supervisor. Source-declared environment values are
applied after privileges are dropped. `/tmp` has 512 MiB of temporary storage.
At most two empty repository paths may receive 2 GiB temporary mounts each; they
cannot cover snapshot inputs. These mounts permit build outputs without changing
source. The container is limited to 128 processes, 4 GiB memory and two CPUs.

The native owner removes its containers and volume before publishing success.
Failed cleanup or an interrupted attempt remains uncertain and cannot rerun the
command. A killed caller can leave bounded stopped containers or its private
volume for inspection; none supplies reusable proof. Snapshot bytes travel
directly from memory, without an intermediate mutable archive.
Existing attempt custody and publication recovery remain authoritative.

## Separate admission checks

An unavailable enforced executor produces a capability gap and no executable
selection. A human answer cannot supply a filesystem boundary. The existing
unrestricted shell remains available only where applicable file protection does
not require confinement.

Instructions also checks the native owner's publication footprint: receipt/index
replacement and retirement, run journals, attempt custody and the source
reconciliation lock. Child isolation does not authorize those host writes.
Protection overlapping that footprint blocks publication before owner entry.

Selection, invocation and receipt reuse bind the current image, transport, source
snapshot and command. Source or runtime drift invalidates the old selection.
Failed commands produce failed evidence. Replay returns the retained result;
uncertain effects never trigger automatic command execution. A passing receipt
establishes command evidence only, with task completion and independent review
remaining separate decisions.

## Evidence boundary

The native producer test owns the safe-read, denied-write, protected-publication,
forged-invocation and unavailable-capability controls. Existing producer tests own
command tampering, changed inputs, timeout, interruption and replay. The hosted
merge lane requires Docker for the new execution controls; other adapters continue
to consume the same native producer rather than duplicating sandbox policy.

The Docker merge step covers a distinct recurring failure class: actual daemon,
mount and process isolation can fail while Rust-only admission tests pass. It
reuses the producer cases and runs once in the merge lane, with no additional
adapter matrix. Its registry pull and tests share a five-minute deadline so an
unavailable registry or stalled daemon cannot consume the whole job timeout.
Failure is localised to this named executor step. Stop after these controls and
required checks pass; the lived-in protected native run remains separate evidence
for the configured repository image and its offline dependencies.
