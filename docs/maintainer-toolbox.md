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

The evaluation runner records deterministic observed status separately from
provider availability. It neither calls a provider nor treats missing access as
product failure; live provider execution remains an explicit maintainer action.
