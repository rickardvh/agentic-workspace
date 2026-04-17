# Planning Routing Contract

Planning stays quiet when newly discovered work has one obvious checked-in home.

Use this page to decide where work belongs when it appears during execution, review, setup, or dogfooding.

## Primary Hierarchy

Planning keeps three primary execution layers plus one bounded analysis layer:

- `ROADMAP.md`: inactive broader direction and grouped deferred lanes
- `TODO.md`: active chunk plus the smallest near-term same-thread queue that should not be lost
- `docs/execplans/`: execution contract for the active chunk
- `docs/reviews/`: bounded analysis artifacts that are not active execution yet

Do not treat these as peer backlogs.
`ROADMAP.md` owns direction, `TODO.md` owns activation, execplans own execution, and reviews own bounded inspection before promotion.

## Routing Rules

Route discovered work by the smallest durable home that matches its current state:

- Use `docs/execplans/` when the work changes the current active chunk's scope, validation story, blockers, or completion path.
- Keep the current TODO row when the active chunk is still the right owner and only the active pointer needs to stay visible.
- Add one near-term TODO item when the next same-thread chunk is concrete enough that it should follow the current active chunk soon, but should not widen the current execplan.
- Use `ROADMAP.md` when the work is accepted future direction, grouped deferred work, or a broader follow-on lane rather than the next concrete chunk.
- Use `docs/reviews/` when the signal still needs bounded analysis before planning should own it.

## TODO Boundary

`TODO.md` is not a backlog.
It may hold:

- one active chunk
- zero or a few near-term queued chunks that are concrete enough to execute soon after the active chunk

Do not use `TODO.md` for:

- broad future direction
- grouped deferred work
- review artifacts
- long execution detail that belongs in an execplan
- completed-work logs

If the queued item would still need a roadmap lane, issue thread, or review artifact to explain why it exists, it probably belongs outside `TODO.md`.

## Execplan Boundary

An execplan stays chunk-level.

Use the current execplan for:

- current milestone sequencing
- blockers
- validation scope
- completion criteria
- bounded carry-forward for the broader intended outcome

Do not widen one execplan into a project container just because the broader lane remains active.
Route the broader line of work through `ROADMAP.md` and, when helpful, `Parent lane` in `Intent Continuity`.

## Machine-Readable Companions

`agentic-planning-bootstrap summary --format json` should answer the compact hierarchy question without rereading the raw files:

- active chunk
- near-term TODO queue
- parent lane
- next likely chunk
- continuation owner
- proof state

`agentic-planning-bootstrap report --format json` may expose the same information more compactly for module-state inspection.
