# Troubleshooting

Start with the symptom you can observe. Preserve existing files while investigating; reinstalling the executable or deleting AW state is not a general repair for an interrupted operation.

## The agent does not use AW

Ask it to read `AGENTS.md`, then `.agentic-workspace/skills/workspace-startup/SKILL.md`. The managed entry section should point to that skill.

If the entry or skill is missing, check whether the repository was [adopted](agentic-workspace-install.md#2-add-aw-to-the-repository), not merely whether the executable was installed. Do not copy package files by hand to fill the gap.

If direct reading works but native skill discovery does not, inspect the host's discovery configuration. The `AGENTS.md` route remains usable without discovery links. A model can also ignore valid guidance; distinguish that behaviour from missing integration in a bug report.

## The command cannot be found or the core cannot start

Run this in the same environment the agent uses:

```sh
agentic-workspace --help
```

Check the executable search path and any repository-local invocation override. A command working in your terminal does not establish that a sandboxed agent can launch it.

Standalone installs need both executables from the same release, kept together. A binary mismatch or unsupported platform is not repaired by switching to a retired Python host. Reinstall the matching distribution using [Getting started](agentic-workspace-install.md). Cargo/Git installs require the source toolchain; prebuilt installs do not.

## A rule or lesson is missing or appears on the wrong task

Ask the agent to name the saved source, its scope and the current task/path it used. Check whether the change was retained at all, whether it was shared or local, and whether its path conditions match the actual work.

For direct inspection:

```sh
agentic-workspace start --target . --task "Inspect guidance for this API change" --changed src/api/users.py --projection full --format json
```

Replace the task and path. Full output should expose the applicable sources or a concrete gap. An irrelevant rule should not be forced into every startup response. A lesson whose assumptions changed needs reconsideration, not automatic promotion into a rule.

Use [configuration](customization.md) to correct the existing source. A chat promise or a similarly named file is not proof that the intended behaviour was saved.

## An operation is rejected as stale or unauthorised

Resolve the current task again. A returned request is tied to the sources and permissions under which it was prepared. Changing the task, policy, target or relevant source can invalidate it.

Use the new request or explain the remaining decision. Do not edit hashes, broaden permissions or substitute a different target to make an old action pass. A successful read does not authorise a write.

## An operation stopped and I do not know whether it completed

Keep its output and local recovery evidence. Ask the agent to inspect the current result and use the returned recovery request.

There are two separate questions: did the change take effect, and did AW produce the next response? A failed continuation can follow a successful change. Repeating the original action without resolving that uncertainty risks applying it twice.

Recovery may establish that the effect completed, that it did not start, or that a specific piece of evidence is missing. Report the unresolved case rather than calling it a successful retry.

## Updating or removing AW reports conflicting files

If a payload update stopped between a registry and its procedure sources, ordinary
startup may report `activation index stale`. Run `agentic-workspace setup --dry-run`
to inspect the current Configuration proposal, then `setup --yes` to authorize it.
If setup reports an interrupted adoption, inspect `setup --recover --dry-run` and
use `setup --recover --yes` to finish that exact publication. Setup can reach the
repair owner without evaluating activation against partially updated procedures;
repository policy and preservation checks still apply. Re-enter ordinary startup
after repair. Do not roll back files or replay consumed write requests.

Inspect the exact paths in the proposal. Preserve edits to package-managed files and move useful project-specific meaning into project-owned instructions or skills before approving replacement.

Use the same Configuration refresh/removal path again after resolving the conflict. Do not recursively delete the enclave or `.agents/skills/`. Unknown files and independently owned plans, lessons and settings are not package garbage. See [Your repository and data](package/installed-surfaces.md).

## A repository-only reader says its profile is stale

`READING.json` must describe the current `OWNERSHIP.toml`. Ask a runtime-capable agent to refresh the integration/profile through Configuration. Do not edit the recorded identity to make the warning disappear.

Until repaired, a reviewer can report directly observed repository facts, but cannot infer current permissions or executable results from a stale profile.

## Report a problem

Use the [bug template](https://github.com/rickardvh/agentic-workspace/issues/new/choose). Include the release and installation route, operating system/architecture, relevant command or prompt, expected result, actual result and the smallest reproduction you can share.

Include the reported source or action identity when it explains the failure. Remove secrets and private project material from output before posting. An isolated reproduction is more useful than an entire session transcript.
