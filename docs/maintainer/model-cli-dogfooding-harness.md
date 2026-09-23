# Observe installed consumer behaviour

Use the maintainer harness to test whether an installed AW consumer finishes an
ordinary repository task. Select an exact candidate artifact directory or a
published stable version. The shared environment helper verifies actual installed
identity and records its target, tools and isolation boundary.

Run `src/tooling/release/consumer_environment.py --help` for environment probes and
`src/tooling/model-cli-harness/run_model_cli_harness.py --help` for outcome checks.
Use a run-owned directory under `.agentic-workspace/local/scratch/` and a new result
filename for each attempt. Never replace a failed public installation with a
checkout build. Preserve the first failure when making a diagnostic retry.

For a native Windows standalone first-contact run, for example:

```sh
python src/tooling/model-cli-harness/run_model_cli_harness.py run --public-version 1.3.2 --family first-contact --backend native --profile standalone --target x86_64-pc-windows-msvc --scratch <owned-scratch> --result <new-result.json>
```

Use the seven family names from `consumer_journeys.py`. `local-independence` and
`upgrade` also require `--previous-public-version` naming a different published
stable. A missing version fails; reserved tags are not upgrade fixtures. Existing
release consumers call the same complete first-contact case. Other families reuse
named native owner tests for detailed semantics and add installed composition
checks. A failed released product remains a failed observation, even when its fix
has landed in source.

The scorer reads bounded inert exports after the actor stops. It checks task
artifacts, allowed changes, preserved policy and claim honesty separately. It does
not execute actor-modified tests or reward command mentions. Offline exports have
no execution or installation witness, so an offline score cannot establish a
completed consumer journey. Missing token and cost observations remain unknown.

Native deterministic preparation records private state and PATH isolation. It does
not establish physical tool absence or an actor sandbox. Docker profiles contain
environment dependencies, never AW or a prepared repository. Provider tooling must
remain outside a minimal consumer or its additional tools must be disclosed.

Matched comparisons require equal task, underlying information, tools, permissions
and opportunities to improve ordinary repository guidance. Retain both assigned
arms, including aborts. The comparison helper supplies no economic superiority
claim or automatic policy admission.

The former command-mention suites, pinned AW fixtures, long-horizon executor and
reference state machine are retired. Dated records in the
[historical evaluation pack](../../src/tooling/model-cli-harness/external-agent-evaluation/README.md)
remain historical evidence. Their schema checks and summaries do not certify the
current product. Independent review and natural-use evidence retain their owners.
