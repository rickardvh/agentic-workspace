## Answer the current question or invoke its action

A returned request asks for input; an action describes an operation that can
have effects. For a compact question, use its exact `reference`, the returned
`reentry`, and an `answer` containing only the requested semantic fields. Keep
the updated reentry after each answer: it preserves earlier work-bound answers.
Do not copy or edit owner identity, revision or custody fields.

For Assignment, answer `assignment_context.next_step`. For retained work, answer
`planning_context.next_step` with only changed material. For setup, choose the
job in `setup_context` and answer its bounded question. Native owners preserve
the rest and revalidate current sources. If a dependency changes, use the returned
current question or recovery; discarded answers do not regain authority by replay.

For substantial structured input, use a file-writing tool to save UTF-8 JSON in
one bounded task scratch file and submit it with `start --input <path>`. Put the
complete reentry, reference and answer in that file. Keep its task, target,
changed paths and projection together; do not also pass conflicting context flags
or construct nested semantic JSON in a shell command. Simple answers need no
scratch file; the supported reference/answer inputs remain sufficient.

Invoke only the exact admitted action. A complete invocation input contains
`target`, `task`, `changed` and the unchanged returned `invocation`; include
`changed: []` for an empty scope. An action alone cannot reconstruct its work
context. Use the repository's configured invocation through native `invoke`.
Preserve the whole effect result and owner-specific next requests. Follow a
current continuation directly; another startup call solely for ceremony adds no
authority. Native checks carry receipts and still require semantic sufficiency.

For a claim, answer the exact current question in `decision_packet.decision_request`
or `pending_consequences.decisions`. Its material states the proposed judgment,
scope, obligations and evidence gaps. Load `material.proposal_detail.reference`
only for a needed binding detail. Keep peer restrictions visible; an answer cannot
replace independent review.

If execution may have happened but its reply or continuation is missing, preserve
the uncertainty and any confirmed effect. Use exact recovery or fresh current
observation; never repeat an effect to recover context. Changed task/target/scope
needs fresh resolution. Source delivery suppression is valid only while the
current source text remains available; after context loss reacquire it.

Use [task resources](../../workspace-resources/SKILL.md) for temporary transport
files and remove them when no longer needed. Transport is not retained task
meaning or permission. A recurring transport correction belongs in its controlling
source through the [correction procedure](../../workspace-instruction-correction/SKILL.md).

Load [client transport detail](transport.md) only when implementing an integration
or handling a host that must store carriage outside its model-visible result.
Ordinary answers use the returned reentry and references directly.
