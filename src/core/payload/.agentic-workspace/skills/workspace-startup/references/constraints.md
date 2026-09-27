# Interpret current restrictions

Use this reference when a result blocks an action or completion claim. Read its
`affects`, `message`, `owner` and revision, then the supplied request or recovery
path. Identify what is forbidden, what remains allowed, and what fact or decision
would remove this particular block.

Read the returned `resolution` before involving the user. For
`bounded-human-answer`, relay the owner's `human_context`: the proposed action,
reason, concrete context, each choice's consequences, what deferring preserves,
and the authority boundary. Keep its exact response request for the answer.
The `human_eligibility` basis must identify a current Verification requirement
that explicitly requires human judgment, or an explicitly configured human task
owner. Missing delegation, machine capability or proof is never that basis.
Human-owned assignments use the existing sealed manual handoff and return contract.
If those semantics are missing, obtain a corrected owner request before asking;
do not invent the rationale from internal paths or raw state.

`bounded-domain-answer` requires the named domain judgment under its existing
authority rules; it does not itself require a human permission request.
`owner-recovery-required` identifies a blocker with a supplied recovery. Report
the missing capability or fact and follow that recovery.
`owner-resolution-unavailable` means no supported recovery is currently supplied.
Keep the affected action or claim blocked, report the missing resolution to its
owner, and continue unrelated work. Do not invent a route or a permission question.
Human assent cannot
supply executor isolation, current evidence, source custody or independent
review. Ask a human only when the owner returns a separate bounded human request
that the user has not already answered for the exact proposed action.

Use the named owner/request to obtain the missing fact or resolve the decision.
Keep allowed direct work moving. Capability absence supplies no permission;
follow the [unavailable-runtime boundary](unavailable.md). Prefer exact selectors
to reconstructing broad state. Preserve current forbidden actions until their
owner supersedes them, without widening one owner's permission to another.

A blocker must distinguish a supplied recovery from an unavailable resolution.
A pending bounded decision already constrains its affected action or claim; it
needs no second blocker promising a competing recovery. Use only the affected proof owner
when evidence matters. A local successful check, intended outcome and parent
completion are separate claims. Do not add proof ceremony merely because a proof
capability exists.

After taking the permitted action, inspect its result. Did the intended change
happen, and does the new result permit the dependent action or claim? Preserve a
confirmed write even if the next step fails. Report any remaining gap; do not
repeat a write merely to obtain its reply. Stop when the requested outcome and
required evidence are established. See [exact effects](owners.md) for transport
and [findings worth retaining](reconcile.md) for useful follow-through. A successful
transport is not accepted evidence, and a Memory note cannot publish a policy correction.
