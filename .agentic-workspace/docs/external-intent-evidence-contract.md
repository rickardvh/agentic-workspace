# External Intent Evidence Contract

This contract defines the optional provider-neutral external-owner observation payload consumed by Planning admission, reconciliation, and route surfaces. The legacy external-intent item fields remain a compatibility input to this one contract; they are not a parallel authority.

Use it when a repo has planning evidence outside the checked-in planning state and wants the product to reconcile that evidence without making any external system authoritative.

## Rule

- checked-in planning state remains primary
- external evidence is optional and reconstructable
- absence of external evidence must not break summary or report
- invalid external evidence should reduce trust visibly instead of silently failing
- ordinary provider refreshes should write ignored local cache, not checked-in history mirrors
- every observation is an immutable snapshot identified by `observation_id`, `external_revision`, `observed_at`, provenance, and an exact `refresh_route`
- Planning derives admission and relevance; adapters cannot select, mutate, prove, satisfy, promote, or close a Planning owner
- unmatched backlog stays in the bounded external-intent cache/query path and is absent from ordinary Planning pressure

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
      "source_repository": "owner/repo",
      "observation_id": "github:issue:251:2026-04-27T12:00:00Z",
      "owner": {
        "id": "#251",
        "kind": "issue",
        "locator": "https://example.invalid/owner/repo/issues/251"
      },
      "status_class": "current",
      "external_revision": "2026-04-27T12:00:00Z",
      "observed_at": "2026-04-27T12:00:00Z",
      "freshness": {
        "status": "current",
        "observed_at": "2026-04-27T12:00:00Z",
        "expires_at": "2026-04-28T12:00:00Z",
        "max_age_seconds": 86400
      },
      "blockers": [],
      "evidence_refs": ["https://example.invalid/owner/repo/issues/251"],
      "provenance": {
        "provider_class": "github",
        "resolver_id": "github-gh-cli",
        "source_ref": "https://example.invalid/owner/repo/issues/251",
        "refresh_id": "2026-04-27T12:00:00Z"
      },
      "refresh_route": "agentic-workspace external-intent refresh-github --issue #251 --storage cache",
      "availability": "available",
      "provider_detail": {}
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

Planning normalizes legacy items into the observation fields above and adds:

- `planning_relationship`: `explicit`, `evidence-backed`, `ambiguous`, or `unrelated`; it never defaults to the only selected owner
- `admission.state`: `current`, `externally-blocked`, `externally-completed-awaiting-admission`, `contradicted`, `stale`, `unavailable`, `ambiguous`, or `unrelated`
- `admission.reason_code`: a stable explanation suitable for #2281 reconciliation and #2277 routing

`provider_detail` is opaque and adapter-owned. Planning admission, route, and reconciliation logic must not inspect it.

## Projection and promotion

Ordinary startup, summary, and selected-owner queries project only observations with a fresh explicit or evidence-backed relationship to a selected/live owner. Full unmatched evidence remains available through explicit bounded external-intent queries. A 1,000-item unrelated snapshot must not create durable candidates, owners, or ordinary route pressure.

Promotion is a separate explicit decision. `external-intent refresh-github --apply-planning-candidates` requires one or more `--issue` selections; a broad refresh cannot bulk-create Planning work. Repeated refresh replaces the cache snapshot instead of retaining a second `previous_items` authority, and candidate promotion remains idempotent by stable external reference.

Evidence references supplied by an adapter are observation evidence only. External completion becomes `externally-completed-awaiting-admission`; it does not satisfy Planning intent, AW proof, lane closure, or parent closure.

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
