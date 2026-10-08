# Publish and inspect one instruction

1. Read the existing source when revising it. Keep its unrelated text and current
   requirements. Shared custom sources are direct `*.md` files under
   `.agentic-workspace/instructions/`; machine-local sources are direct `*.md`
   files under `.agentic-workspace/local/instructions/`. Local destinations must
   already be untracked and gitignored. A missing ignore rule needs the host's
   authorised policy path, not a silent ignore edit. Choose a descriptive filename
   for a new source; directory layout does not provide applicability.
2. Use the configured invocation and current `start` context for the real task and
   affected paths. Take the matching `instructions.authoring.requests` entry with
   request kind `instructions/edit-source/v1`. Supply its `source` and complete
   proposed `content`, then submit the exact request through `start`. The installed
   `.agentic-workspace/skills/workspace-startup/references/owners.md` explains
   exact request and invocation carriage, including file-backed JSON input.
   Drafting and proposal inspection are read-only. Check the returned postimage,
   metadata and intended scope against the request before authorising it. Invalid
   syntax must be diagnosed; do not guess how malformed input should become policy.
3. Answer the current instruction-write authorisation question with the ordinary
   semantic answer `authorize-write` only when the exact content and scope are
   authorised. An explicit request to save this bounded rule may already supply
   that authority; do not prescribe another human roundtrip. Use `defer` when the
   write is not authorised. Current protection and source checks still apply.
   Submit the exact returned answer and invoke the unchanged returned action.
   Do not construct authority, revision or admission fields yourself.
4. If source or policy changes, obtain a fresh proposal. If a write may have
   happened but its result is uncertain, preserve that uncertainty and use the
   exact `instructions.authoring.recovery_requests` from a current observation.
   Do not repeat a possibly completed write to recover its reply.
5. Observe relevant work from a fresh process through public `start`, with actual
   changed paths and any current semantic route selection. Inspect the source
   identity, metadata, `applicability`, delivered `guidance`, `binding_admission`
   and applicable Verification requirements. Inspect unrelated work too: it should
   not receive this scoped guidance or its obligations. Report unresolved scope
   separately from a demonstrated non-match. A governing-source change can make
   its consumer scope relevant even when no consumer path was edited.
6. Continue through current Verification requests for required checks or source
   consistency judgements. Publication admits a declaration; it does not run a
   check, satisfy governance, execute a preferred skill or prove obedience. Report
   the retained source, lifetime, intended scope, observed effect and any exact
   remaining admission or evidence gap.

Publication is not a Git commit. Shared sources can travel through normal version
control, but publication custody in this checkout is not portable source admission.
Use the receiving checkout's existing Git/source admission; never copy local
custody or advance its trust revision automatically. Local sources stay local and
cannot waive shared protections. Package refresh or removal preserves these
host-owned rules, even though they live inside the AW directory.

Subsequent maintenance uses the same create/revise path. An authorised revision
that withdraws a requirement must satisfy the existing owner and policy checks;
unadmitted withdrawal preserves prior governance. The current owner supports
write and interrupted-write recovery, not general deletion or renaming. Report
that unsupported lifecycle request rather than unlinking a file to erase a rule.
Removing the installed authoring bundle is separate from removing custom rules.
