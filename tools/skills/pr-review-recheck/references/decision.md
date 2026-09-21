# Report the bounded review outcome

Decide the action:

- approve / ready when intent, proof, CI, labels, and closure all line up;
- if an eligible independent review approves a PR that is still draft, mark it **ready for review as part of the approval action** unless the user has explicitly required it to remain draft; do not leave an approved PR draft by default;
- comment with a blocker when the ordinary path would be wrong after merge;
- comment with non-blocking suggestions only when they should not delay merge;
- merge only when the user explicitly asks or the current instruction permits it.

## Blockers

Treat these as blockers unless the human explicitly accepts the underlying product risk; the independent-review eligibility boundary itself is not waivable by the implementing agent:

- the current reviewer materially shaped the PR patch, descends from the implementation agent's delegated review lineage, or its independence is unclear;
- a bounded implementation leaf would close without its whole stated outcome and immediate proof being true;
- a knowingly partial implementation uses after-the-fact follow-ups to evade the original bounded leaf outcome rather than a genuine transparent reshaping;
- a parent is claimed complete from one useful child/slice while current containing intent remains unresolved;
- a later-evidence issue is being used as an implementation backlog instead of routing a concrete defect to a bounded owner;
- longitudinal evaluation is used to substitute for unfinished implementation, missing present proof, known defects, vague future evidence, stale/superseded results, or absent current evaluation authority;
- proof is missing, stale, too narrow, or contradicted by the diff;
- a material test/CI delta lacks its testing-strategy disposition or retains duplicate semantic proof, implementation-shaped residue, unjustified public-surface repetition, temporary batch taxonomy, opaque unbounded constituents, or recurring cost unsupported by a distinct durable merge claim;
- incident-driven permanent regression growth lacks a missing durable failure class, or the proof argument lacks a defensible bounded stop/escalate rationale;
- checked-in Planning, Memory, payload, or generated state is stale after the claimed closeout;
- package-affecting changes lack exactly one semver label;
- a shipped payload mirror is out of sync with the source surface;
- an independently approved draft PR is left draft without an explicit hold reason.

## Output

Report in this shape:

- `decision`: approve / ready / comment / block / merge-ready / not-ready
- `closure_shape`: parent outcome / bounded implementation leaf / later evidence / other
- `what_landed`: concise summary of the actual change
- `intent_served`: which issue or product intent is served
- `proof`: CI, validation, focused checks, or missing proof; for test/CI changes, include the testing-strategy disposition and any violation or justified exception
- `unresolved`: blockers or remaining non-blocking risks
- `closure_honest`: yes / no / partial, with issue refs and any evaluation-boundary reason
- `next_action`: comment, approve, mark ready, wait, request fix, label, or merge

## Rules

- Eligibility comes before procedure. **Never use this skill as permission for an implementation agent, or any reviewer it spawns or controls, to review its own patch.**
- Independence is a custody/authority property, not a process, model, account, or context property. A child/subagent cannot manufacture independent review for its parent implementation agent.
- Skill availability, routing, a user request, passing CI, implementation completion, or a fresh reviewer context does not manufacture independent review authority.
- Implementation-spawned reviewer agents may provide non-authoritative critique only; their verdict is not independent approval.
- Prefer evidence from the current PR head over stale prior comments.
- Do not infer merge readiness from passing CI alone.
- When an eligible independent reviewer approves a draft PR, mark it ready for review in the same review pass unless explicitly instructed to keep it draft.
- Do not require a giant PR to close a broad parent; review bounded children on their own full outcomes and let the parent close administratively when its current graph is satisfied.
- Do not hold a complete bounded implementation leaf open for future evidence explicitly owned elsewhere.
- Keep comments focused on actionable blockers or durable suggestions.
- When an independent reviewer shares the PR author's GitHub account and cannot submit a formal review, report the review as an ordinary PR comment identifying the reviewed head. No custom marker, App provenance or check publication is required.
