# External Intent Evidence Contract

This contract defines the optional external-planning evidence artifact consumed by planning intent-validation surfaces.

Use it when a repo has planning evidence outside the checked-in planning state and wants the product to reconcile that evidence without making any external system authoritative.

## Rule

- checked-in planning state remains primary
- external evidence is optional
- absence of external evidence must not break summary or report
- invalid external evidence should reduce trust visibly instead of silently failing

## Artifact Path

- `.agentic-workspace/planning/external-intent-evidence.json`

## Accepted Shape

```json
{
  "kind": "planning-external-intent-evidence/v1",
  "items": [
    {
      "system": "github",
      "id": "#251",
      "title": "Graceful partial compliance",
      "status": "open",
      "kind": "lane",
      "parent_id": "",
      "planning_residue_expected": "required"
    }
  ]
}
```

## Field Meaning

- `system`: optional external system label such as `github`, `jira`, or `manual`
- `id`: stable external work-item identifier
- `title`: compact human label
- `status`: `open` or `closed`
- `kind`: optional item class such as `lane`, `slice`, `review`, or `task`
- `parent_id`: optional higher-level external item
- `planning_residue_expected`: one of:
  - `required`: closed item should usually leave visible checked-in planning residue
  - `optional`: residue may exist but is not required for trust
  - `none`: do not treat missing checked-in residue as suspicious by itself

## Intended Use

The intent-validation surface may use this artifact to answer:

- which open external items are still not represented in active or candidate checked-in planning state
- which closed external items have lower-trust closeout because expected checked-in residue is missing
- whether the repo looks quiet only because larger intent fell out of visible planning state

## Non-Authority Rule

This artifact must not replace checked-in planning ownership.

It exists to provide additional evidence when:

- a repo also uses an issue tracker
- a human wants to reconcile quiet checked-in planning with external work state
- a local-only repo wants to record external planning observations manually

The product should still work normally when the artifact is absent.
