# External Intent Evidence Contract

This contract defines the optional external-planning evidence payload consumed by planning intent-validation surfaces.

Use it when a repo has planning evidence outside the checked-in planning state and wants the product to reconcile that evidence without making any external system authoritative.

## Rule

- checked-in planning state remains primary
- external evidence is optional and reconstructable
- absence of external evidence must not break summary or report
- invalid external evidence should reduce trust visibly instead of silently failing
- ordinary provider refreshes should write ignored local cache, not checked-in history mirrors

## Artifact Path

- `.agentic-workspace/local/cache/external-intent-evidence.json` for ordinary ignored cache
- `.agentic-workspace/planning/external-intent-evidence.json` only as a legacy/manual compatibility input

## Accepted Shape

```json
{
  "kind": "planning-external-intent-evidence/v1",
  "refreshed_at": "2026-04-27T12:00:00+00:00",
  "refresh_metadata": {
    "adapter": "github-gh-cli",
    "repository": "owner/repo",
    "item_count": 1,
    "open_count": 1,
    "closed_count": 0,
    "state": "open"
  },
  "items": [
    {
      "system": "github",
      "id": "#251",
      "title": "Graceful partial compliance",
      "status": "open",
      "kind": "lane",
      "parent_id": "",
      "planning_residue_expected": "required",
      "url": "https://example.invalid/owner/repo/issues/251",
      "source_repository": "owner/repo"
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
- `refreshed_at`: optional timestamp for the evidence refresh run
- `refresh_metadata`: optional compact adapter metadata; consumers may surface it to show whether evidence may be stale
- provider adapters should keep ordinary refreshes small; for example, a GitHub adapter defaults to open issues and requires explicit `--state all` for closed-history audits
- `url`, `source_repository`, `labels`, and timestamp fields: optional provider details retained as evidence, not authority

## Intended Use

The intent-validation surface may use this artifact to answer:

- which open external items are still not represented in active or candidate checked-in planning state
- which closed external items have lower-trust closeout because expected checked-in residue is missing
- whether the repo looks quiet only because larger intent fell out of visible planning state

Use `external_work_reconciliation` in `agentic-workspace summary --format json` or `agentic-workspace report --target ./repo --section external_work_reconciliation --format json` as the first compact answer. It groups evidence freshness, current external work state, closeout reconciliation, and landed-open checks before provider-specific detail. Explicit report/reconcile paths may reconstruct the ignored cache from an optional provider adapter when one is available; missing adapters fall back to absent evidence instead of blocking offline planning.

## Non-Authority Rule

This artifact must not replace checked-in planning ownership.

It exists to provide additional evidence when:

- a repo also uses an issue tracker
- a human wants to reconcile quiet checked-in planning with external work state
- a local-only repo wants to record external planning observations manually

The product should still work normally when the artifact is absent.
