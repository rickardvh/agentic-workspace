# Judge closure honestly

Identify the linked issue's closure shape independently of its bug/direction/review kind:

- **parent outcome / direction** — a PR may satisfy one child or disposition, but parent closure is administrative and requires all current bounded children/dispositions plus immediate aggregate proof to establish the parent outcome. Do not demand one giant parent-closing PR.
- **bounded implementation leaf** — a PR claiming closure must make the whole bounded leaf true and provide its immediate deterministic/integration proof. A knowingly partial PR cannot manufacture honest closure by creating follow-ups after the fact.
- **later evidence / review** — no product-code PR is required merely to close the evidence issue. Review the stated evidence/currentness/independence criteria; route concrete implementation findings to the smallest bounded owner instead of growing the evidence issue into a backlog.

Check closure honesty:

- what landed;
- what intent it serves;
- what remains unresolved;
- whether the PR may honestly close each linked issue under that issue's closure shape;
- whether later evidence explicitly owned elsewhere is being incorrectly used to keep an otherwise-complete bounded implementation leaf open.

For PRs that use longitudinal evaluation as part of issue closure, check the split explicitly:

- deterministic implementation behavior still needs present-tense proof and cannot be deferred into an evaluation;
- the evaluation must have owner, criteria, evidence sources, report sinks, collection policy, conclusion policy, and a fresh/current admitted result unless the PR only claims definition setup;
- known defects, failed or stale proof, vague future-evidence text, superseded results, or missing current authority block closure;
- direct deterministic work should remain directly closable when proof and intent are satisfied; do not add evaluation ceremony where no future-evidence uncertainty exists;
- when longitudinal evidence is explicitly owned by a separate later-evidence issue, absence of that future observation is not a blocker for a bounded implementation leaf whose present behavior and proof are complete.

## Closure-shape examples

- A delegation parent may remain open after a correct worker-entry leaf merges; review that leaf against its whole bounded worker-entry outcome rather than demanding provider replacement or later real-provider economics in the same PR.
- A bounded adaptation leaf with current authority/application/currentness fixtures may close while a separate later-evidence issue continues to observe repository-lifetime payoff. Do not convert the leaf into a months-long evidence queue.
