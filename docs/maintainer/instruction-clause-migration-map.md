# Instruction clause migration map

This map distinguishes source-specific authoring from the shared internal control semantics. The instruction IR is not a public DSL or a second workflow owner.

| Existing mechanism | Shared effect | Disposition |
| --- | --- | --- |
| Scoped instruction activation | `surface` | Compile applicability and the source-owned instruction reference; retain scoped files as authoring sources. |
| Skill recommendation and activation ranking | `prefer` | Compile advisory ranking; retain SkillSpec capability and procedure ownership. Fixed phase/module gates become removal candidates. |
| Assurance requirements and proof lanes | `require` | Compile only the cross-cutting satisfier/target edge; retain classification and evidence admission with their domain owners. |
| Action and claim ceilings | `restrict` | Compile bounded targets; retain operation, ownership, proof, and human authority as the permission owners. |
| Target and correction guidance | `surface`, `prefer`, or owner-derived fact | Retain rich domain judgment at the guidance owner; compile only bounded cross-cutting consequences. |
| Module relevance | fact plus `surface`/`prefer` | Capabilities remain module-owned; remove fixed first-party slot assumptions as compatibility consumers migrate. |
| Task posture and workflow obligations | source authoring sugar or removal | Compile material requirements/restrictions; background labels that have no decision effect. |

Compatibility projections remain readable while consumers migrate, but conformance tests require their effects to match the compiled projection. The existing operating decision remains the only cross-cutting action/blocker compiler.

The first derived compatibility path is `blocked_claim_classes`: applicable `restrict` effects against `claim:*` targets now produce that existing field. This removes the need for a second claim-ceiling interpretation in new instruction sources while preserving the current consumer contract.
