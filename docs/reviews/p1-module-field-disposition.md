# P1 module field disposition

Implementation under #3443. Ready for independent review; no issue closure or
acceptance is claimed. The current native owner API is the baseline, not the
historical Python module model advertised by the superseded authoring documents.

| Field/group | Disposition and implemented result |
| --- | --- |
| Native Registration identity/revision/api_version | KEEP_DOMAIN: linked implementation compatibility. |
| describe / resolve | KEEP_DOMAIN: lazy domain descriptor and deterministic observation, not agent phases. |
| capability domains/effects/requests/operations; source/config schemas | KEEP_DOMAIN: independent fact/effect/currentness meaning, strict admitted bounds. |
| Context and Resolution facts/blockers/requests/prepared result | KEEP_DOMAIN: current domain input/output; optional operation permits facts-only ownership. |
| Repository independent admissions | KEEP_DOMAIN: authorization and source/effect grants cannot migrate to optional skills. |
| Registry participation_model, including recommended_loop, module_can_contribute, task_posture_model, conflict/projection/dynamic-instruction recipes | REMOVE: deleted model and schema fields. No consumer requires a replacement; historical diagnostic defaults remain empty. |
| First-party modules[].participation loop_steps/declares/posture_triggers/dynamic_projection/authority_boundaries/conflict_provenance | REMOVE: deleted all three rows and schema. Actual native domain restrictions remain in each owner; optional selection/sequence is in M1-M5. |
| Historical startup_steps/workflow_surfaces/install signals | KEEP_DOMAIN, internal distribution only: source-maintenance lifecycle detection/preservation still consumes paths, not native module phases. |
| Historical module-capability/v2 / Python providers | DEMOTED compatibility fixtures: corrected public authoring references; not native registration. No new callbacks or aliases. |
| Package-owned skill entries and procedure resources | MOVE_TO_SKILL completed in M1-M5: ordinary passive sources, optional generic question/reference control, no privilege. |

The removed participation taxonomy was a second description of agent choreography.
No native field is removed just to improve a field count: the surviving strict
native owner contract already describes domain identity, current observations and
owned effects. Native module authors now have one accurate documented contract,
with no additional required field or core module-name registration.

Neutral read-only and operation-oriented fixture checks exercise the same native
assembly through all four transports. First-party authority evidence comes from
the Planning/Assignment, Memory and Verification controls in the lower stack;
this change does not alter those domain algorithms or admissions.
