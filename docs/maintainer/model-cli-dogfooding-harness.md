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

The subscription actor uses `--driver agent --backend sandbox --model gpt-5.6-luna
--reasoning medium --billing subscription` with an immutable non-Docker Codex
template supplied through `--template`. Docker Sandboxes 0.45.1 supports the
mountless sandbox and disabled shared skills used here. Configure OpenAI OAuth
with `sbx secret set openai --oauth`. The controller creates a separate uid and
private provider home without an authentication file (the Sandbox proxy holds
subscription credentials), disables SSH socket access and sudo, excludes the template
MCP gateway, and denies repository/publishing network routes before model work.
It never mounts the maintainer checkout or home.

Each actor is limited to three sessions, each at most 900 seconds. A continuation
uses two sessions and a replacement sandbox with retained repository files only;
`.agentic-workspace/local/` custody, configuration effects, and host notes are
excluded and reconstructed on the replacement machine. Preflight rejects an
actor-home authentication file or inherited API credentials.
The optional token threshold stops on observed telemetry; it is not a hard
provider-side quota. Missing usage and monetary cost remain unknown. Subscription
OAuth does not establish support for metered API execution.

All seven families have a live path. Removal is checked before re-adoption;
maintenance must preserve disabled policy and restore the local boundary;
interruption checks the public stale-source rejection before fresh recovery.
Continuation checks that work really remains before transferring repository bytes
to a new sandbox. Upgrade and local-independence use an exact earlier public
subject as their declared starting recipe. A final task diff alone cannot prove
these transitions. Native actor execution and minimal-profile absence remain
unavailable in this backend. A Linux guest on Windows supplies Linux evidence.

Matched comparisons require equal task, underlying information, tools, permissions
and opportunities to improve ordinary repository guidance. Retain both assigned
arms, including aborts. The comparison helper supplies no economic superiority
claim or automatic policy admission.

The installed-consumer workflow freezes public current/previous inventories once,
then calls the same runner. Relevant candidate checks remain in platform-release;
publication attempts call the public workflow even when a registry job fails.
Daily selection rotates seven scenario families and four profiles across the six
declared targets, reserving at most three subscription sessions of 900 seconds.
macOS is explicitly skipped for the current acceptance scope. Native actor and
unavailable architecture assignments remain non-passing in the denominator.

Manual dispatch accepts exact public versions. Live dispatch requires master,
the protected `consumer-live` environment, a dedicated `consumer-sandbox` runner
with Python and authenticated Docker Sandboxes, and repository variable
`CONSUMER_LIVE_RUNNER_READY=true`. `CONSUMER_TEMPLATE` may name another immutable
Codex template digest. Provision these only after independent review; source
tests do not establish trusted hosted execution. No PR job receives provider state.

`consumer_schedule.py` supplies `freeze`, `run`, `summary` and `cleanup` operations.
Keep frozen subjects and initial result files together; diagnostic retries need
separate output directories. Summaries retain missing installations, provider
unavailability, skipped targets, exhausted budget, usage unknowns and evidence age.
The always-run cleanup step deletes only recorded disposable resource names.
Sanitized CI artifacts expire after seven days. Route actionable failures through
the existing dogfooding owner, searching existing issues before filing another;
the actor and reporting jobs have no issue-writing credentials.

The former command-mention suites, pinned AW fixtures, long-horizon executor and
reference state machine are retired. Dated records in the
[historical evaluation pack](../../src/tooling/model-cli-harness/external-agent-evaluation/README.md)
remain historical evidence. Their schema checks and summaries do not certify the
current product. Independent review and natural-use evidence retain their owners.
