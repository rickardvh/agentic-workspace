# Control Input Disposition

The public operating model is one resolved contract, not a collection of peer posture knobs. `compile_control_inputs` retains an input only when it is applicable now and maps to a supported material decision dimension: action, constraint, proof, claim, procedure, or capability selection.

| Existing input family | Semantic owner / authority | Disposition | Material contract effect |
| --- | --- | --- | --- |
| shared config and workflow obligations | repository / repo policy | retain when matched; otherwise omit | action, constraint, proof, claim, or required procedure |
| module selection | repository plus module compatibility owner | retain | capability selection |
| module posture fragments | module | remove as a global dimension; derive bounded contribution | action candidate, procedure, or capability selection only |
| local override and runtime capability | current machine/runtime | retain at weaker authority | narrows executable capability or local preference; never repo policy |
| target guidance and canonical instructions | source owner declared by context-authority registry | retain by reference when applicable | procedure or constraint |
| task facts and changed paths | current task/runtime observation | derive | relevance, action scope, and proof selection |
| proof/assurance requirements | repository or admitted evidence owner | retain | proof and bounded claim |
| artifact, initiative, delegation, clarification, and output posture | mixed | merge into their action/constraint/procedure effects; keep diagnostics behind selectors | only the resulting current constraint or action |
| optimization hints | advisory owner | demote unless evaluation proves a material effect | advisory action ordering only |
| review rubrics and report shape | repository or consumer | keep outside first-line decision unless required now | procedure/output constraint |
| diagnostic inventory and unmatched config | diagnostic source | omit from first-line contract | selector-backed explanation only |

Authority precedence does not silently merge classes. Repo-shared policy, local runtime facts, module-domain inputs, and task-derived facts retain provenance. Competing authoritative effects on the same dimension fail closed with the repository as resolution owner. Modules may add actions, procedures, and capability selection; they cannot create global proof, claim, or policy dimensions.

Migration is subtractive: consumers should read `operating_decision.control_inputs.effects`; broad task-posture and config packets remain diagnostic compatibility projections until their remaining consumers are migrated, and must not be treated as parallel permission or claim authorities.
