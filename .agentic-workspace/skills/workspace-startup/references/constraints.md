# Interpret current restrictions

Use this reference when a result blocks an action or completion claim. Read its
`affects`, `message`, `owner` and revision, then the supplied request or recovery
path. Identify what is forbidden, what remains allowed, and what fact or decision
would remove this particular block.

## Continue outside AW

An AW refusal constrains its own operation or claim. It does not decide whether
the user, repository and host independently permit another way to finish the
task. Prefer a supported exact AW recovery when cheap and useful. If it is absent,
unusable or disproportionate, an already authorized actor may choose ordinary
tools outside AW without asking for AW permission or retrying unchanged state.
If a real repository, host or user rule forbids the alternative, preserve that
restriction; only its authorized owner can change it. A required independent
review, uncertain effect custody or missing credential does not disappear.

Leave a short exception in the existing task, PR, issue, commit or handoff:
**actor + blocked AW action/reason; task/scope; independent authority and chosen
alternative; AW evidence, ownership or claim still unestablished**. If storage is
unavailable, state it visibly to the user. Saving this note needs no AW call,
managed record or special format, and the note supplies no permission.
Keep it concise; omit secrets, full logs and personal machine paths.

For example, an authorized agent can run a bounded read-only parser check with
ordinary host tools when AW cannot provide isolated `proof.report`. Its task note
states the missing executor, tested scope and direct result, while explicitly
leaving the AW receipt and independent review unestablished. It must not launch
the guarded AW action through an unsafe executor or write a separately protected
source. Keep useful unrelated Planning, Memory and Verification available;
whole-workspace disablement is a separate last-resort choice.

On AW reentry, submit the actual changed scope and reobserve current sources and
requirements. Distinguish external edits/results from authenticated AW custody.
Never fabricate a receipt, backfill an AW effect or replay an uncertain write.
An exception does not satisfy the preserved AW restriction or authorize closure.

## Follow an AW recovery

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
`current-owner-route` means current owner work is available through the matching
`consequence_recovery` entry. Follow its exact reference with the same work context
and prior answers. An owner-nominated request addresses this consequence; a
selection-required route asks you to establish that relationship before choosing
a request. Sharing an owner alone does not make a request a recovery. Neither
route availability nor selection resolves the restriction.
`owner-resolution-unavailable` means no supported recovery is currently supplied.
Keep the affected AW operation or claim blocked, report the missing resolution,
and use the non-AW continuation above when independently authorized. Do not invent
a route or a permission question.
Human assent cannot
supply executor isolation, current evidence, source custody or independent
review. Ask a human only when the owner returns a separate bounded human request
that the user has not already answered for the exact proposed action.

Use the named owner/request to obtain the missing fact or resolve the decision.
Keep allowed direct work moving. Capability absence supplies no permission;
follow the [unavailable-runtime boundary](unavailable.md). Prefer exact selectors
to reconstructing broad state. Preserve current forbidden AW actions until their
owner supersedes them, and preserve independent repository/host/user restrictions
on any alternative. One owner's permission never supplies another's authority.

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
