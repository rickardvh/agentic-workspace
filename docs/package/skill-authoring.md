# Author a repository skill

A skill supplies a reusable method. Start with Markdown; add AW-assisted branch
delivery only when selecting detail helps. Neither a skill nor its branch answer
grants permission, admits evidence or replaces required review.

This reference describes the post-contraction source contract. Check the selected
[installation and release evidence](../agentic-workspace-install.md) before using
it with an older artifact. The [integration record](../reviews/powerskill-p1-integration.md)
separates source, installed-artifact and observed host evidence.

## Start with an ordinary skill

Create `tools/skills/change-note/SKILL.md` in your repository:

```markdown
---
name: change-note
description: Draft a change note from an observed patch; never publish it.
---

Compare the patch with the accepted intent. Describe observable changes to public
results, inputs, errors or interactions. For an internal refactor, explain what
preserves public behavior. If evidence is missing, ask for it. Return a draft;
do not publish or modify repository state.
```

Ask your agent: “Read `tools/skills/change-note/SKILL.md` and draft a note for this
patch.” This known-file path needs no AW registry, route, helper or module.
Repository-owned `tools/skills/` is distinct from installed, package-managed
`.agentic-workspace/skills/`. Use your host's supported skill exposure to make a
repository bundle discoverable; merely creating a directory does not establish
host activation. Instruction `use` is a preference, not guaranteed activation.

The [Agent Skills specification](https://agentskills.io/specification) requires
`name` and `description` metadata. Keep the name aligned with the directory,
lowercase and hyphenated, and describe when the method applies. Bundle-relative
links can reach references, assets and optional scripts. A host may load the full
selected `SKILL.md`; AW cannot retract that text. Metadata discovery also costs
context. Keep the entry short and move large alternatives into separate files.

## Add a semantic question without custom code

Use the same maintained Markdown for AW and direct reading. Replace the entry's
body with:

```markdown
Read [the question](procedure.md), compare the patch and intent, and follow only
the applicable linked branch. Defer when evidence is insufficient. With AW,
select `example/change-note`, carry the semantic answer, then request the returned
resource. Without AW, read the same question and branch directly.
```

Create `procedure.md` beside `SKILL.md` with the following complete content:

````markdown
# Change visibility

Compare the observed patch with the stated intent. A change to a public result,
input, error or interaction is user-visible. A refactor preserving those is
internal. If evidence is insufficient, return unknown and request the missing
information instead of guessing.

```agentic-procedure
{"kind":"agentic-workspace/procedure/v1","id":"visibility","question":"Does the observed change alter behavior visible to a user?","branches":[{"id":"visible","description":"Public behavior changes","next":"user-note.md"},{"id":"internal","description":"Behavior is preserved","next":"internal-note.md"}]}
```

Manual alternatives: [user-visible](user-note.md), [internal](internal-note.md).
````

Create `user-note.md`: “State the observable before/after behavior and any action
the user needs to take. Return the draft to the caller. Do not publish or mutate
repository state.” Create `internal-note.md`: “Describe the implementation change
and the evidence that public behavior remains the same. Return the draft to the
caller. Do not publish or mutate repository state.”

These are the [neutral fixture's](../../tests/fixtures/change-note/SKILL.md)
procedural meanings. A leaf is a resource, not another globally registered skill.
The question resource contains exactly one `agentic-procedure` JSON fence. Its
optional `context` list names files needed to judge the question. Context and
`next` paths are relative to that resource, confined within the skill bundle;
do not use absolute paths, `..` or executable expressions. Natural language
criteria are judged by the agent, not converted into Boolean predicates.

For optional meaning-based discovery, create or extend `tools/skills/REGISTRY.json`:

```json
{"skills":[{"id":"change-note","path":"change-note/SKILL.md","semantic_routes":["example/change-note"],"procedure_resource":"procedure.md"}]}
```

This is the supported subset needed by the example, not a requirement to copy
internal package metadata. A known ordinary file reference needs no semantic
route. This AW example uses one to obtain its exact qualified selection request.

## Try, inspect and answer

Use the configured AW invocation in place of `agentic-workspace`. Keep the task
and target unchanged through these calls:

```sh
agentic-workspace start --target . --task "Draft a note for a total-format change" --projection full --format json
```

1. Copy the returned `semantic_routes.requests` discovery request. Set
   `arguments.parent` to `example/change-note`, save it as `request.json`, and
   repeat that command with `--input request.json`.
2. Inspect `semantic_routes.discovery.detail`. Copy its result's top-level
   `procedure.requests` selection request and return it through the same command.
   This selected read statically validates the question declaration; malformed
   or unavailable material yields diagnostics, not an execution action. There is
   no separate public procedure-validator command to invent.
3. Inspect `procedure`: its source identity/revision, selected question,
   alternatives and request explain what is being asked and what branch resource
   the answer affects. Open the named source for the full criteria. This explains
   provenance and consequence, not hidden model reasoning.
4. Copy the returned `procedure/answer/v1` request, preserving its identity fields.
   Set only `arguments.answer` to the agent's judgment, then return it through
   `start --input request.json` again.

For a patch showing `format_total(12)` change from `"12"` to `"$12"`, with an
accepted intent to add the currency symbol, an answer is:

```json
{"disposition":"answered","branches":["visible"],"material":{"summary":"Receipt totals now include the dollar symbol.","basis":"Observed public output changes from 12 to $12, matching the stated intent."}}
```

Expect a current answer and only the selected `user-note.md` reference in `next`.
Set the earlier discovery request's `arguments.resource` to that exact returned
reference to request its body. Draft: “Receipt totals now include the dollar
symbol: for example, $12 instead of 12. No user action is required.” This is a
draft, not publication or proof of correctness. The untaken branch's body is not
read or hashed merely to admit this answer.

If no patch was supplied, answer instead:

```json
{"disposition":"unknown","branches":[],"material":{"missing":"No observed patch yet; intent alone does not establish changed public output."}}
```

Expect no next resource. `status: current` may describe a current **unknown**
answer; inspect `answer.disposition` separately. `defer`, `no-match` and `conflict`
also remain unresolved rather than choosing a default. Use nonempty valid branch
IDs only for `answered`. Material is bounded semantic information, never a bare
action envelope, public request or arbitrary shell command.

## Keep meaning and currentness separate

Carry the exact qualified selection and answer request across re-entry, including
its task, route, source, skill, question, revision and instance. The initial
instance is caller-owned so two same-task uses can be distinct; after selection
the answer is bound to it. Identical question text in another skill is not the
same identity. Do not recreate identity fields from prose or a branch name.

For evidence-dependent answers, add `evidence` inside the answer, with entries
`{"reference":"patch.txt","revision":"sha256:<64 lowercase hex characters>"}`.
The reference is repository-relative. Compute the revision from UTF-8 text after
normalizing CRLF to LF, for example with Python's normal text read:

```python
from hashlib import sha256
from pathlib import Path
print("sha256:" + sha256(Path("patch.txt").read_text(encoding="utf-8").encode("utf-8")).hexdigest())
```

Carry the same answer on unchanged re-entry: a current answered judgment avoids
redundant questioning. Change the evidence to an internal refactor preserving
`"12"`, then re-enter with that retained answer: its evidence revision is stale,
so reconsider and answer `internal` from the new evidence. A hash establishes
currentness of declared reliance, not semantic truth or test success. Undeclared
facts do not acquire freshness merely by appearing in the agent's reasoning.

Changed question/context, identity or relevant evidence invalidates reuse. A
selected destination becomes a dependency when selected; changing an untaken
body alone does not stale an otherwise valid question answer. If the answer is
lost at handoff, ask again; AW does not reconstruct it from an invented cursor.
Navigation is disposable. Durable unfinished work belongs with its existing
continuity owner, not a new workflow state store in the skill.

For an owner-dependent fragment, use the existing `agentic-owner-reference`
fence with `kind` (`request`, `action` or `question`), `owner` and exact `id`.
Resolve its returned exact reference with `start --reference <reference>`;
the response has `status` and `value`. Resolution never executes an action.
Return only the current owner-issued request/action through the ordinary
`start`/`invoke` path. Missing, ambiguous or stale references remain unresolved.
Without that owner/runtime the corresponding effect, proof or recovery is
unavailable; reading Markdown does not permit manual managed-state edits.

## An optional deterministic helper

A helper can compare numeric totals or prepare patch statistics; it cannot decide
whether a public change is acceptable. Ordinary scripts work without AW-specific
metadata. To expose selected helper material, add this optional `executable`
object to the same registry row:

```json
{"entrypoint":{"kind":"file","path":"tools/skills/change-note/scripts/compare.py"},"dependencies":["docs/receipt-format.md"]}
```

Unlike branch links, these are exact **repository-relative** paths. Create both
files before declaring them. A minimal `scripts/compare.py` is:

```python
import json
import sys
if len(sys.argv) != 3:
    raise SystemExit("usage: compare.py BEFORE AFTER")
print(json.dumps({"before": sys.argv[1], "after": sys.argv[2],
                  "equal": sys.argv[1] == sys.argv[2]}))
```

Run `python tools/skills/change-note/scripts/compare.py 12 '$12'` only with the
host's normal execution authority. Python must actually be available. The helper
can use ordinary control flow and runs with host permissions; discovery does not
execute it or sandbox it. Selected detail reports declared material revisions;
an external file helper can have `material_status: current` while runtime status
is unknown and executable status unavailable. Establish runtime availability at
invocation. Do not label a present script an admitted effect or turn its output
into constructed owner actions. Missing dependencies require repair or the same
manual method, with unavailable runtime guarantees left unavailable.

## Customize and repair

Edit your repository-owned bundle and registry together; remove its row when
removing the bundle. Reobserve selected detail after changes. Keep package-owned
bundles under their package lifecycle instead of editing them in place. A local
host exposure is not an override of shared policy. To replace a preferred method,
publish a repository-owned skill with a distinct ID and deliberately update the
preference through its source owner. Required review, evidence and human decisions
survive substitution or removal.

Use returned qualified route/source references where names collide. Do not rely
on registry order or an unqualified name silently winning. Add a distinct route
when the meanings differ; retain an explicit ambiguity when they cannot be
resolved honestly.

| Observation | Next action |
| --- | --- |
| Malformed JSON, extra fence, duplicate branch ID or unsafe path | Correct the selected source, then repeat the same selected read. |
| Missing question/context | Restore the named file or repair the declaration; do not invent its contents. |
| Missing selected leaf | Restore that destination; admission of the question did not pre-read every leaf. |
| Multiple sources for a route | Select a returned qualified identity or clarify the intended source. |
| Stale answer/evidence | Reobserve the change and supply a fresh judgment through the current request. |
| Lost carriage | Re-select and answer from current sources; no cursor reconstruction. |
| Runtime unavailable | Read the same Markdown and draft with available tools; leave owner effects/proof unresolved. |

The live [integration walkthrough](../reviews/powerskill-p1-integration.md) exercised
unknown, visible, changed evidence and internal outcomes. It also records native
call and source-read costs. The simple draft-only baseline needs no native calls;
branch delivery is an option whose coordination benefit must earn its cost.
