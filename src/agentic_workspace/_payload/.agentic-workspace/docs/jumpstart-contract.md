# Jumpstart Contract

Jumpstart is the bounded post-bootstrap phase for a newly installed or adopted Agentic Workspace in a lived-in repo. It orients the agent toward useful durable workspace surfaces without turning init into broad repo analysis.

## Entry

Start with compact routing:

```bash
agentic-workspace start --target . --task "<task>" --format json
agentic-workspace setup --target . --format json
```

A fresh necessary-surfaces bootstrap records a versioned `configuration_readiness` identity in `.agentic-workspace/adoption-receipt.json`. Ordinary startup uses that durable receipt, not setup-shaped task wording, to route one exact `reconcile-repository-configuration` action to `workspace-setup-jumpstart` and the configured `setup` command. A current identity stays quiet. Missing readiness metadata in a legacy receipt is not, by itself, evidence that setup is incomplete; an explicit stale identity blocks only configured-workflow claims and effects while leaving unrelated read-only inspection available.

Use `setup` as a pre-write and pre-seed discovery report. It may point at candidate surfaces, promotion rules, and follow-up routes, but it does not authorize bulk imports or automatic planning/memory writes by itself.

## Configuration concerns

The setup report projects current work as `configuration_concerns`: each concern names its identity, owner, status, materiality/dependency, evidence strength and authority, inference, apply route or human decision, and detail selector. Resolve `satisfied` and `not-applicable` silently. Route `inference-ready` work to its existing owner without asking the user, then rerun setup. Ask only a current `human-decision-required` question, using outcome and consequence language, and route the answer immediately to its owner. A `bounded-route-required` concern stops setup and moves broad analysis to bounded Planning or human authority.

Strong inference sources are explicit repo config, durable intent documents, declared test commands, CI workflows, and ownership maps. Generic filenames, keywords, directory names, scratch artifacts, and policy copied from the Agentic Workspace source repository are not independent authority. Capability needs may be translated from a recurring repository outcome to the owning module route without asking the user to choose module names.

Setup has no fixed questionnaire and keeps no independent wizard state. A repository may need zero questions; after every owner action or human answer, ordinary setup is resolved again from current authority.

## Promote

Promote only information that has a durable owner and would reduce future rediscovery:

- stable operating boundaries, invariants, traps, restart rules, or proof expectations to Memory;
- bounded active follow-up to Planning;
- evidence-backed friction or workflow improvement to improvement intake;
- package or host-repo documentation gaps to docs only when the missing guidance is reusable.

Keep low-confidence, generic, one-off, or broad narrative findings transient.

## Mature Repo Seed Bias

For mature repos, prefer compact contract-like surfaces over broad prose mirrors. Good first Memory candidates are surfaces that encode repeatable decisions, restart boundaries, task-shape guidance, proof expectations, or other durable operating knowledge.

Do not bulk-import README files, issue backlogs, generated references, or design prose simply because they exist. Link to canonical docs instead of copying them when the document is already discoverable and not expensive to reconstruct.

## Proof

Before claiming setup follow-through, show:

- the setup command used;
- the candidate surfaces inspected;
- each promoted, dismissed, or deferred finding;
- where durable residue was written, if any;
- the validation command selected for changed paths.
