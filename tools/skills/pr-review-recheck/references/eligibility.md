# Establish independent eligibility

Before using any review procedure below, establish that the current reviewer is independent of the PR patch **and independent of the implementation lineage that produced it**.

The current agent/session is **not eligible** if it did any of the following for the PR head or the patch now under review:

- wrote, edited, generated, or deleted code, tests, documentation, configuration, or other patch content;
- pushed, rebased, cherry-picked, merged, conflict-resolved, or otherwise changed the PR head;
- addressed review feedback or CI failures by mutating the patch;
- directed or delegated substantive patch mutation from within implementation custody, on the implementer's behalf;
- otherwise materially shaped the PR patch from within implementation custody.

Issue shaping and ordinary review feedback do not constitute implementation custody. An externally initiated reviewer does not become ineligible merely by defining or refining intent/acceptance criteria before implementation, identifying blockers, requesting fixes, or re-reviewing later revisions, even when the implementation follows that feedback. Independence is lost when the reviewer writes or edits patch content, changes the PR head, acts within the implementation lineage, or directs/delegates substantive patch mutation on the implementer's behalf. Review feedback is not such delegation; taking responsibility for executing the patch change is.

**Delegation does not create independence.** A reviewer is also **not eligible** when it is a child, subagent, delegated task, subprocess, nested session, or other reviewer instance spawned, selected, prompted, supervised, or controlled by an ineligible implementation agent for the purpose of approving that implementation agent's patch. This remains true even when the delegated reviewer:

- has a fresh context, separate process, different model, or separate account;
- did not itself edit the patch;
- is explicitly told to be "independent";
- is given only the PR URL and review skill;
- returns a technically sound review.

Such a delegated reviewer may provide **non-authoritative critique or preflight feedback** to the implementation agent, but it must not submit `APPROVE`, claim `merge-ready`, or be presented as the required independent review.

An authoritative review must enter from outside the implementation agent's review custody: for example, a human/maintainer starts the reviewer directly, an independently configured trusted review service is triggered by its normal repository event, or a separate reviewer session receives an independent review mandate without being spawned or directed by the implementation agent. An implementation agent may request that such an established external mechanism run, but it must not choose or manufacture the reviewing agent, prompt, authority, or verdict ad hoc.

If any disqualifying item is true, or independence is unclear, **stop before using this skill**. Do not submit `APPROVE`, do not claim `merge-ready`. Handoff to an externally initiated reviewer that neither materially shaped the patch nor descends from the implementation agent's delegated work.

A user asking the implementing agent to “review”, “recheck”, “approve”, or “merge” its own PR does **not** override this boundary. Human approval to continue implementation also does not create independent review authority. An implementation agent may report its fixes, evidence, and remaining uncertainty, but that report is not independent review.

A reviewer may share the GitHub account that opened the PR; that is only an account/API transport limitation. It does not permit the agent that implemented the patch to approve itself. A fresh chat or process is not sufficient by itself if it is merely continuing the implementation agent’s role, authorship, or delegated review lineage.
