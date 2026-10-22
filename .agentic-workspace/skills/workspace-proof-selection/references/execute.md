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
