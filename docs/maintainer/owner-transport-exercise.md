# Owner input and correction exercise

This records author validation for #3658. The task is to create, select and
substantially update a Planning record after canonical AW entry, verify its saved
fields, answer a simple choice, and disposition a trusted recurring correction.
The supplied host rejection has an unknown cause. These exercises do not grant
independent review or issue completion.

## Changes prompted by the exercise

Resolved owner requests now link directly to the existing owner procedure. Its
first decision distinguishes a direct small answer from substantial structured
material, which belongs in a UTF-8 JSON file. The procedure covers an opaque
pre-execution rejection and routes a recurring correction to source disposition.
Existing currentness, exact-envelope and effect-recovery rules remain binding.

The first candidate exposed a CLI defect: a complete context containing `target`,
`task` and `reference` was mistaken for a bare public request unless it contained
an unrelated optional field. The CLI now recognises that context directly and
still rejects explicit flags that conflict with the file. The existing CLI
transport test includes this failure class and a bare-request control.

The exercise also omitted `lifecycle` and `phase` from update material. Planning's
continuation reference now tells the caller to start with the selected record,
keep fields admitted by the current schema, and preserve those two current values.

## Observations

The first candidate used a captured binary before the CLI context repair. It
created, selected and updated the record, with each effect committed once. The
saved revision 2 matched all 15 proposed material fields, including paragraph
strings. A simple `continue-selected` answer succeeded. The trusted correction
was supplied as current material; comparison with the existing owner procedure
supported an already-current/no-change disposition. No reminder was needed for
correction disposition or readback.

That candidate made 18 operating calls plus one help invocation, over roughly
35 tool exchanges. It encountered the context-classification defect, then lost
the target while trying a flag-based workaround. It also omitted required creation
and update fields, lost context on a bare action invocation, and attempted a
dependent script after a failed proposal. Native validation rejected the invalid
inputs before effects; the missing output file caused no AW call. The PATH Python
alias and several guessed search paths also failed. These are recorded costs,
not successful proof observations.

An earlier exercise read both source versions during a parent rebuild. It made
approximately 27 native calls and verified the same 15-field postimage, but its
mixed timing excludes it from a before/after comparison. Separate stable before
and final-candidate runs are required to assess that comparison.

The stable before run read revision `7f4565d53` and used a copied baseline binary.
It completed creation, selection, update and selector reconciliation, verifying
revision 2 and the submitted paragraphs and three acceptance conditions. Its
identical-update control returned `unchanged`. Approximately 30 native calls and
29 tool turns were needed, with roughly 20,000 visible tool-output tokens; these
are agent estimates, inflated by one broad output. Errors included a null carrier
from a detail response, conflicting projection, lost invocation context, stale
action and omitted update fields. Committed creation was not replayed. No external
reminder was needed. The correction was supplied to AW but future method repair
remained an explicit package-source gap. The fixture had no installed procedure
registry, so this run does not establish activation-registry behaviour.

No actual host-policy rejection or interrupted commit was induced. The supplied
`CreateProcess blocked by policy` observation supports only a pre-execution
rejection with unknown cause. Recovery reasoning in the agent exercises is
separate from executed deterministic currentness and custody tests.

## Deterministic evidence and remaining work

Eight existing operating tests pass, including exact request resolution, stale
references, peer restrictions and multiple action construction. Two focused
carriage cases pass for prior-answer preservation and the owner effect boundary.
All six CLI unit/transport cases pass after the context repair. Generated payloads
match their canonical sources. No wording assertion was added.

Final fresh-agent observations, current source reconciliation and required hosted
checks remain pending. Broader adapter repetition is unwarranted: the changed
transport is the native CLI, and the shared owner semantics are unchanged.
