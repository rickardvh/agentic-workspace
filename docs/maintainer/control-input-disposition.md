# Control Input Disposition

The public operating model is one resolved contract, not a collection of peer posture knobs. `compile_control_inputs` retains an input only when it is applicable now and maps to a supported material decision dimension: action, constraint, proof, claim, procedure, or capability selection.

| Current source | Semantic owner / authority | Disposition | Material contract effect |
| --- | --- | --- | --- |
| `.agentic-workspace/instructions/*.md` | repository instruction owner | preferred generic authoring surface; compile when global or path-matched | guidance, canonical context, procedure route, completion check, or write restriction |
| `.agentic-workspace/config.toml [workspace]` | repository / runtime contract | retain only real CLI/runtime/installation choices | runtime capability and target selection; not ordinary guidance |
| `.agentic-workspace/config.local.toml` | current machine/runtime | retain at weaker authority | narrows executable capability or local preference; cannot create repo policy |
| module selection and module-owned config/state | repository plus module compatibility owner | retain capability selection and domain facts; keep module-local controls behind the module | capability selection, relevant action, or procedure only |
| module posture fragments | module | remove as a global dimension; derive bounded contribution | action candidate, procedure, or capability selection only |
| `AGENTS.md` and host adapters | repository adapter owner | keep as thin bootstrap; migrate ordinary scoped guidance | route to startup and the canonical instruction owner |
| target guidance and canonical repo docs | source owner declared by context-authority registry | retain by reference when applicable; route from `read` instead of copying | procedure, context, or constraint |
| task facts and changed paths | current task/runtime observation | derive | relevance, action scope, and proof selection |
| Verification/proof/assurance declarations | specialised repository or admitted evidence owner | retain domain semantics; compile cross-cutting checks and claim restrictions through the clause IR | proof and bounded claim |
| skill metadata and routing | skill/capability owner | retain procedure; resolve short `use` names against admitted identities | procedure preference without authority widening |
| artefact, initiative, delegation, clarification, and output posture | mixed | merge into their action/constraint/procedure effects; keep diagnostics behind selectors | only the resulting current constraint or action |
| optimisation hints | advisory owner | demote unless evaluation proves a material effect | advisory action ordering only |
| review rubrics and report shape | repository or consumer | keep outside first-line decision unless required now | procedure/output constraint |
| diagnostic inventory and unmatched config | diagnostic source | omit from first-line contract | selector-backed explanation only |

Authority precedence does not silently merge classes. Repo-shared policy, local runtime facts, module-domain inputs, and task-derived facts retain provenance. Competing authoritative effects on the same dimension fail closed with the repository as resolution owner. Modules may add actions, procedures, and capability selection; they cannot create global proof, claim, or policy dimensions.

Ordinary guidance belongs in scoped Markdown, skills keep reusable procedure,
configuration keeps Workspace and local execution choices, and specialised
formats retain domain semantics. Consumers use the compiled operating decision;
diagnostic projections grant no permission or claim authority.

## Repository bootstrap migration

The repository's `AGENTS.md` contains only the canonical mandatory startup fence.
The former surrounding rules retain the following owners (#3660):

| Former paragraph | Current owner and disposition |
| --- | --- |
| Adapter authority marker | Removed; `.agentic-workspace/OWNERSHIP.toml` identifies the bootstrap surface. No duplicate marker is needed. |
| Native source preparation | Startup ordinary-use reference leads to `workspace-setup-jumpstart/references/boundaries.md` before native use; `docs/maintainer/native-repository-path.md` retains the repository build details. Both native binaries remain required. |
| Generated surfaces and applicable validation | Scoped `workspace-operating.md` requires regeneration and applicable proof for structured contract changes; Verification owns proof. |
| Bounded proof before commit and truthful milestone | Scoped `workspace-operating.md`; Planning owns milestone publication. |
| Validation, issue completion, intent and operating cost | Scoped `workspace-operating.md` and existing `workspace-dogfooding.md` requirements; Verification owns claim judgment and the responsible source owns friction repair. |
| Source reconciliation and unresolved admissions | Scoped `workspace-operating.md`; System Intent and source owners retain reconciliation. Existing unresolved protection remains unchanged. |
| Independent PR review and continuing implementation | `github-pr-review.md` owns custody and review eligibility. Operating guidance points implementation actors there; the review route supplies it to review actors. No implementation actor may direct a reviewer. |
| Optional advisory shaping critic | `tools/skills/github-issue-shaping/SKILL.md`; bounded advice remains distinct from independent review or acceptance. |

Instruction changes use native instruction publication. Skills and referenced
documents hold procedure; neither an instruction publication receipt nor a
passing check establishes independent review or issue completion.
