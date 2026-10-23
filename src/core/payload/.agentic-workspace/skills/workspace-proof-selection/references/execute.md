# Execute the selected native check

Reuse an exact current Verification request set already delivered for this work.
Resolve through `start` when that request or a material prerequisite is missing
or changed. Carry only the returned authorized `proof.report` action through
`invoke`; do not execute an unrelated primary action or reconstruct an envelope. Preserve semantic scope and strategy
requests in caller carriage. Owners revalidate current sources and publication.

```agentic-owner-reference
{"kind":"action","owner":"verification","id":"proof.report"}
```

Inspect the effect separately from continuation. A committed check stays committed.
Use the [recorded observation](receipt.md), including its original subject and
current-use limits. If continuation fails, use [effect recovery](recovery.md)
when it can resolve a needed fact. Recording a known result is separate from
permission to launch a new invocation. No automatic batch, retry or sufficiency answer.

To deliberately measure the same current command again after a completed result,
inspect that observation in Verification's current evidence. Select its
`repeat_requests` entry from `/verification` detail and replace `repeat.reason`
with the question another measurement will answer. Resolve that exact request
through `start` and invoke the new action. Verification derives one successor
from the authenticated terminal receipt; a changed reason cannot mint another
attempt. Use the new receipt as predecessor for a further intentional measurement.
Both results remain evidence, and a later pass does not dismiss an earlier failure.
For an interrupted or uncertain effect, recover its original exact action first.

For isolated proof, `[execution].inputs` accepts repository-relative literal
files/directories and `*`, `?`, or bracket patterns such as `tests/*.py` and
`src/**`. Matching follows scoped-instruction fnmatch rules: `*` spans `/`,
`**` has the same meaning as `*`, and Windows matches case-insensitively.
Literal directories include descendants; patterns select each matching regular
file, including nested files when the pattern matches their full path. Selection
includes tracked and untracked files, sorted and deduplicated. Git internals,
AW local directories, `.agentic-workspace/config.local.toml` and the legacy
`agentic-workspace.local.toml` are private state. Their directories are never
traversed, and an input matching private state is rejected. Links and special
files are rejected.
Expansion stops after 50,000 visited entries; snapshots retain their 20,000-entry,
128 MiB and 64-component limits. Narrow `execution.inputs` when an input is
unmatched, unsafe or exceeds a bound. Membership, bytes and executable modes are
reobserved before execution and evidence reuse. Per-command
`execution_prerequisites.source_inputs` still names exact required files.
