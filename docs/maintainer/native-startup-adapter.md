# Native startup adapter source

Use this reference when integrating delivery of repository instructions with
native startup. It explains when the consumer must read the selected source and
which changes invalidate that delivery.

`workspace.agent_instructions_file` selects existing startup text. Native resolution
returns its exact reference, content revision and a current public read request.
Ordinary entry delivers the required current source text before affected work;
continued consumers can carry the exact delivery reference to suppress unchanged
prose. This creates no generated adapter or durable read ledger.
An absent explicit selection stays quiet; this reader does not infer source
authority from arbitrary repository Markdown.

Configured source context must be delivered before affected implementation or
completion judgement. The restriction uses existing `effect:implementation`,
`claim:complete` and each currently declared owner operation's effect boundaries,
including Planning state writes and Verification command execution. Source reads
and recovery remain available. Missing
or unreadable text also retains the exact `effect:write:<path>` source boundary.
Reading delivers context for the current request; it does not prove compliance
with that text, grant proof or acceptance, or establish mutation custody. Neither
a generated fence nor a recognisable adapter authorises overwriting surrounding
repository-owned content.

The request binds the current task, changed paths, source, configuration and
combined capability revision. Reads recheck source and configuration currentness.
After delivery, returned actions retain the exact source request in their common
`source_requests` dependency. A fresh invocation revalidates that explicit request
through its current source owner; omission, alteration and source drift fail
closed. This field does not assert that any rule was satisfied. No read ledger or
durable permission is created: independent fresh work obtains current source
context itself. Installer/update custody remains with the existing lifecycle owner.
