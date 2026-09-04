# Maintainer toolbox disposition

The four current model-judgment procedures and the small active model-evaluation
runner live under `tools/`. They are not packaged, installed into host
repositories, or loaded by `start`/`invoke`.

Deleted pre-v1 tooling is dispositioned as follows:

- review, issue shaping/creation, and single-finding dogfooding procedures:
  **restore current maintainer value**;
- deterministic/direct/partial-client scenario execution and explicit provider
  availability for #2821-#2827: **restore minimal active research dependency**;
- generated helper scripts for issue bodies and broad report/reconcile/proof
  command choreography: **replace more simply** with current templates,
  `start`/`invoke`, and repository validation commands;
- agent manifests/routing catalogues, review pollers, external-consumer copies,
  historical episode/result archives, fixture forests, Docker sandboxes, the
  structured-executor prototype, old foundation/path/ownership skills, and stack
  management wrappers: **obsolete/delete**.

The evaluation runner always records deterministic observed status separately
from provider availability. Missing provider configuration is `unknown`, while
an explicitly configured adapter probe distinguishes `available`, `unavailable`,
and `unknown` with provenance. No environment bit is accepted as proof of access.

Live evaluation is an explicit maintainer action: pass both `--provider` and an
`--adapter-command`. The command receives one JSON object on stdin and returns
one JSON object on stdout. It first receives a `probe`; only an `available`
response permits live calls. Each live scenario then runs matched `direct` and
`assisted` conditions. The assisted request contains evidence produced through
the public `Workspace.start` and, when actionable, `Workspace.invoke` boundary,
including the returned next decision.

Reports retain bounded evidence for the effective provider input, tool calls,
retry and repair counts, elapsed time, correctness and authority outcomes, and
explicit unknowns. The adapter owns credentials and provider-specific request
semantics; neither enters the product package. The runner, scenarios, and
maintainer skills remain under `tools/`, and a wheel-build test proves they are
not installed. Running without a provider or adapter is deterministic and makes
no provider calls.
