# Standing Intent Contract

This page defines the first compact contract for classifying durable standing repo guidance and routing it into the strongest checked-in owner surface.

Use it when durable repo-wide guidance first appears in chat and the next question is not "should we remember this somehow?" but "what kind of standing intent is it, and where should it live?"

## Purpose

- recognize durable standing repo guidance before it disappears back into chat residue
- classify that guidance into a small number of owner-shaped intent classes
- route each class into the strongest existing durable home instead of a generic catch-all
- make the current durable standing guidance inspectable through one compact report view

## First Standing-Intent Classes

### `config_policy`

Use for stable repo policy that should be queryable and preferably machine-readable.

Default owner:

- `.agentic-workspace/config.toml`

Typical examples:

- improvement posture such as reporting-only versus proactive cleanup
- output or residue preferences such as `optimization_bias`
- other stable repo-level policy that should survive startup without prose rereads

### `repo_doctrine`

Use for broad standing doctrine, philosophy, or design constraints that explain how the repo should be run without becoming a narrow runtime policy switch.

Default owners:

- `AGENTS.md`
- `docs/design-principles.md`
- closely related canonical docs when the doctrine is topic-specific

Typical examples:

- dogfooding as a normal development mode
- preserving one primary owner per concern
- preferring repo-native state over chat residue

### `durable_understanding`

Use for repo-specific interpretive understanding that reduces rediscovery cost but is not itself a hard shared policy.

Default owner:

- Memory

Typical examples:

- subsystem-specific repo knowledge
- recurring interpretation hints
- anti-rediscovery notes that remain useful across sessions

### `active_directional_intent`

Use for bounded active direction that should steer current work but should not be mistaken for timeless repo doctrine.

Default owners:

- `.agentic-workspace/planning/state.toml` (`todo.active_items`)
- `.agentic-workspace/planning/execplans/`

Typical examples:

- the current promoted roadmap slice
- current lane-local constraints or follow-through
- bounded active execution intent

### `enforceable_workflow`

Use when prose is no longer the strongest home and the guidance should become verifiable through checks, validation commands, or workflow tooling.

Default owners:

- `scripts/check/`
- validation workflows
- config plus checks when both explanation and enforcement are needed

Typical examples:

- required validation lanes for a class of change
- drift checks that should fail or warn when durable policy is violated
- proof workflows that should be invoked consistently

### `temporary_local_guidance`

Use for useful but non-durable local guidance that should stay transient unless repetition or broader impact proves otherwise.

Default owner:

- current chat or local execution context only

Typical examples:

- one-pass local execution choreography
- tool-specific convenience notes
- guidance that stops mattering after the current bounded slice ends

## Promotion Test

Promote a chat-borne instruction when all of these are plausibly true:

- it would still matter after the current session or agent ends
- future work would pay reminder or rediscovery cost if it stayed only in chat
- one of the standing-intent classes clearly fits better than leaving it unowned

Keep it transient when any of these are true:

- it only affects the current local step
- it is tool- or model-specific convenience with no repo-level durability value
- the strongest owner surface is still unclear and the ambiguity would risk misclassification

## Owner Mapping Rule

- Prefer the strongest existing owner surface for the class.
- Do not default everything into Memory.
- Do not stretch config to hold broad doctrine or execution choreography.
- Do not leave active direction in doctrine once it becomes a bounded current slice.
- When workflow expectations should be verifiable, prefer checks or validation over prose-only preservation.

## Stronger-Home Guidance

- `repo_doctrine` may later promote into `config_policy` or `enforceable_workflow` when prose is too weak.
- `active_directional_intent` may harden into doctrine, policy, or checks only after it stops being merely lane-local.
- `durable_understanding` should shrink or move when a stable canonical doc or stronger enforcement now explains it better.

## Stronger-Home Decision Test

Promote standing intent into `config_policy` when:

- the guidance should be machine-readable and survive startup without rereading prose
- the repo needs a stable default or policy mode rather than explanation alone
- the concern changes repo-wide defaults more than one local workflow

Promote standing intent into `enforceable_workflow` when:

- drift should be detectable rather than merely remembered
- the repo needs repeatable validation, warnings, or failing checks for the concern
- a check, validation command, or workflow can verify the rule without turning the repo into a generic automation system

Keep the guidance primarily as doctrine when:

- it is still broad philosophy or boundary explanation rather than a stable toggle
- a stronger home would overspecify the doctrine too early
- human legibility still matters more than machine-readable enforcement for the concern

## First Promotion Examples

The first reportable examples in this repo are:

- `improvement_latitude` promoted into `.agentic-workspace/config.toml` as machine-readable standing policy
- `optimization_bias` promoted into `.agentic-workspace/config.toml` as machine-readable output policy
- planning-surface integrity promoted into `scripts/check/check_planning_surfaces.py`
- source/payload/root-install boundary protection promoted into `scripts/check/check_source_payload_operational_install.py`

These examples show the intended path:

- doctrine or repeated guidance becomes explicit
- the concern proves stable enough for config or checks
- the stronger home becomes authoritative
- the older prose may remain as explanation, but not as the only enforcement path

## Precedence Order

When standing-intent surfaces conflict, use this first compact precedence order:

1. explicit current human instruction
2. active directional intent for the current bounded lane
3. checked-in config policy
4. enforceable workflow or validation/check surfaces
5. standing repo doctrine
6. durable interpretive understanding such as Memory
7. superseded residue kept only for history or explanation

Interpret this compactly:

- current human instruction can always redirect the current work
- active lane-local direction may narrow broader doctrine for the current slice
- active lane-local direction should not silently override checked-in hard policy
- config and enforceable workflow outrank broader doctrine when the repo has chosen a machine-readable or verifiable rule
- Memory informs interpretation but should not overrule clearer doctrine or policy

## Supersession Rules

Use these first supersession rules:

- newer durable guidance in the same owner surface replaces older guidance for the same concern
- when the same concern moves into a stronger home such as config or checks, that stronger home becomes authoritative and older prose becomes explanatory or should shrink
- active directional intent is slice-scoped; it may temporarily narrow doctrine, but it does not rewrite repo-wide policy after the slice ends
- explicitly superseded or archived residue may remain for history, but it should stop governing current work

## First Effective View

Use `agentic-workspace report --target ./repo --format json` for the first compact effective standing-intent view.

That view should answer, without broad rereading:

- which standing-intent classes currently have durable repo-owned surfaces in force
- which surfaces own them
- what is authoritative policy versus doctrine versus interpretive understanding
- what active directional intent currently matters
- what precedence order should resolve conflicts among those surfaces

## Boundaries

- Do not treat every chat instruction as standing intent.
- Do not create a unified mega-surface for policy, doctrine, Memory, Planning, and checks.
- Do not treat the first slice as a full precedence or supersession engine.
- Do not hide source provenance when surfacing effective standing intent.

## Relationship To Other Docs

- Use [`.agentic-workspace/docs/reporting-contract.md`](.agentic-workspace/docs/reporting-contract.md) for the compact report surface that exposes the effective standing-intent view.
- Use [`.agentic-workspace/docs/knowledge-promotion-workflow.md`](.agentic-workspace/docs/knowledge-promotion-workflow.md) for the canonical workflow for moving chat-borne guidance into durable homes.
- Use [`execution-flow-contract.md`](execution-flow-contract.md) when the question is confirmed versus interpreted task intent for one slice rather than durable repo-wide guidance.
- Use [`docs/design-principles.md`](docs/design-principles.md) for standing doctrine already adopted by the repo.
