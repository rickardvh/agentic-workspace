# Check whether a saved lesson actually helped

Use this reference when evaluating whether guidance saved by Memory, repository
instructions or another AW feature improved later work.

A later result must identify the exact saved lesson and revision it is evaluating.
Do not create a universal “learning score” or another central history just to
measure this.

| Where the lesson was saved | Identity used for comparison | Useful later evidence | Where to act on the result |
| --- | --- | --- | --- |
| Shared Memory | `fact_id` + `fact_revision` | Human/reviewer judgement, tests or current repository evidence | Update or remove the Memory fact; move it into a stronger project mechanism when justified |
| Target or agent guidance | `guidance_id` + `guidance_revision` | Later task result, evaluation or review | Update the guidance or its suitability rules |
| Repository improvement candidate | `candidate_id` + candidate/action revision | Evaluation plus relevant checks | Update the improvement or the source responsible for it |
| Agent aid or shortcut | `aid_id` + `aid_revision` | Comparable successful uses | Keep, revise or replace the aid |

Keep each component's existing identifiers. AW only needs enough information to
match later evidence to the exact lesson that was used.

A lesson should be reconsidered when:

- its saved revision changed;
- the repository rule or code it depended on changed;
- the later task did not actually use it;
- repeated cost shows that the underlying tool or project rule should be fixed
  instead of repeating advice.

An agent saying “this helped” is not enough on its own.

Treat success conservatively too. Seeing guidance once or observing one successful
task does not justify a permanent success record. Prefer independent evidence from
at least two comparable later uses before treating an aid or shortcut as reliably
useful.

Once the underlying problem is fixed, the lesson is replaced, or the advice no
longer saves meaningful rediscovery, stop surfacing it.
