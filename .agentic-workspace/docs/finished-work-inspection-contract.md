# Finished-Work Inspection Contract

This contract defines the compact finished-work inspection surface exposed through planning summary and report.

Use it when you need to verify whether previously closed planning lanes still look honestly landed without reconstructing the whole history from chat, issue prose, or bespoke checklist files.

## Rule

- archived checked-in execplan residue remains the primary closeout evidence
- optional reopening evidence may lower trust, but must not replace the archive as source of record
- the product must work normally when no external or supplementary planning system exists
- suspicious historical closeout should surface as a compact report signal, not only as a manual audit ritual

## Primary Surface

- `finished_work_inspection_contract` in `agentic-workspace summary --format json`
- `finished_work_inspection` in `agentic-planning-bootstrap report --format json`

## Optional Evidence Artifact

- `.agentic-workspace/planning/finished-work-evidence.json`

Accepted shape:

```json
{
  "kind": "planning-finished-work-evidence/v1",
  "items": [
    {
      "system": "manual",
      "id": "#260",
      "title": "Finished-work intent inspection",
      "status": "open",
      "kind": "lane",
      "reopens": ["#220", "#222", "#229"]
    }
  ]
}
```

## Field Meaning

- `system`: optional external or local source label such as `github`, `jira`, or `manual`
- `id`: stable identifier for the newer follow-on or reopening work item
- `title`: compact label for the newer work
- `status`: `open` or `closed`
- `kind`: optional class such as `lane`, `slice`, `review`, or `task`
- `reopens`: list of prior work-item refs that this newer item is evidence against
- `reason`: optional compact explanation for why the earlier closeout is now lower trust

## Classification Model

The finished-work inspection surface classifies archived closeouts as:

- `clearly_landed`: archived residue says the work closed and no reopening evidence points back at it
- `partial`: the archive itself says the bounded slice landed while larger intent or required continuation stayed open
- `likely_premature_closeout`: optional reopening evidence points back at a supposedly closed archived lane, so the original close decision should be treated as lower trust

## Intended Use

The surface should cheaply answer:

- which archived closeouts still look solid from their own residue
- which archived lanes were honest partial closeouts rather than true completion
- which previously closed lanes now have explicit evidence that they were closed too early
- what a reviewer or agent should inspect next before treating historical work as settled
