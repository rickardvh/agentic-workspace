# Execute the selected native check

Resolve the selected exact request set through `start`. Carry only the returned
authorized `proof.report` action through `invoke`; do not execute an unrelated
primary action or reconstruct an envelope. Preserve semantic scope and strategy
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
Matched directories include descendants. Selection includes regular tracked
and untracked files, sorted and deduplicated. Git internals and AW local state
are outside the source universe and are never traversed; a scope explicitly
selecting their directories is rejected. Links and special files are rejected.
Expansion stops after 50,000 visited entries; snapshots retain their 20,000-entry,
128 MiB and 64-component limits. Narrow `execution.inputs` when an input is
unmatched, unsafe or exceeds a bound. Membership, bytes and executable modes are
reobserved before execution and evidence reuse. Per-command
`execution_prerequisites.source_inputs` still names exact required files.
