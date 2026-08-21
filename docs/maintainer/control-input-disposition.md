# Control Input Disposition

The public operating model is one resolved contract, not a collection of peer posture knobs. `compile_control_inputs` retains an input only when it is applicable now and maps to a supported material decision dimension: action, constraint, proof, claim, procedure, or capability selection.

| Current source | Semantic owner / authority | Disposition | Material contract effect |
| --- | --- | --- | --- |
| `.agentic-workspace/instructions/*.md` | repository instruction owner | preferred generic authoring surface; compile when global or path-matched | guidance, canonical context, procedure route, completion check, or write restriction |
| `.agentic-workspace/config.toml [workspace]` | repository / runtime contract | retain only real CLI/runtime/installation choices | runtime capability and target selection; not ordinary guidance |
| `.agentic-workspace/config.toml [workflow_obligations]` | repository / compatibility sugar | migrate generic guidance and checks to scoped Markdown; retain only specialized stage semantics until its consumer is removed | bounded requirement or procedure through the clause IR |
| `.agentic-workspace/config.local.toml` | current machine/runtime | retain at weaker authority | narrows executable capability or local preference; cannot create repo policy |
| module selection and module-owned config/state | repository plus module compatibility owner | retain capability selection and domain facts; keep module-local controls behind the module | capability selection, relevant action, or procedure only |
| module posture fragments | module | remove as a global dimension; derive bounded contribution | action candidate, procedure, or capability selection only |
| `AGENTS.md` and host adapters | repository adapter owner | keep as thin bootstrap; migrate ordinary scoped guidance | route to startup and the canonical instruction owner |
| target guidance and canonical repo docs | source owner declared by context-authority registry | retain by reference when applicable; route from `read` instead of copying | procedure, context, or constraint |
| task facts and changed paths | current task/runtime observation | derive | relevance, action scope, and proof selection |
| Verification/proof/assurance declarations | specialized repository or admitted evidence owner | retain domain semantics; compile cross-cutting checks and claim restrictions through the clause IR | proof and bounded claim |
| skill metadata and routing | skill/capability owner | retain procedure; resolve short `use` names against admitted identities | procedure preference without authority widening |
| artifact, initiative, delegation, clarification, and output posture | mixed | merge into their action/constraint/procedure effects; keep diagnostics behind selectors | only the resulting current constraint or action |
| optimization hints | advisory owner | demote unless evaluation proves a material effect | advisory action ordering only |
| review rubrics and report shape | repository or consumer | keep outside first-line decision unless required now | procedure/output constraint |
| diagnostic inventory and unmatched config | diagnostic source | omit from first-line contract | selector-backed explanation only |

Authority precedence does not silently merge classes. Repo-shared policy, local runtime facts, module-domain inputs, and task-derived facts retain provenance. Competing authoritative effects on the same dimension fail closed with the repository as resolution owner. Modules may add actions, procedures, and capability selection; they cannot create global proof, claim, or policy dimensions.

Migration is subtractive: ordinary guidance moves to scoped Markdown, skills keep
reusable procedure, config keeps Workspace/capability/runtime choices, and
specialized formats keep only useful domain semantics. Consumers read the
compiled operating decision; broad task-posture, workflow-obligation, and config
packets remain diagnostic compatibility projections only while their remaining
consumers are migrated. They are not parallel permission or claim authorities.
