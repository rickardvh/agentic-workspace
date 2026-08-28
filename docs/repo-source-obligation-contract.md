# Repo-source obligations

A repo-source obligation is a derived setup concern. It says that effective Agentic Workspace configuration or an explicitly enabled capability depends on semantic information owned by the host repository. It is not a registry and does not copy source content into AW.

Each obligation identifies the semantic need, source class and owner, exact configured and acceptable candidates, status, materiality, affected claims, and one minimum continuation. Supported source states are `satisfied`, `candidate-existing`, `missing`, `ambiguous`, `stale-or-incompatible`, and `insufficient-authority`.

## Configuration inventory

| Applicable configuration | Repo-owned source class | Owner | Materiality and consequence |
| --- | --- | --- | --- |
| Explicit `system_intent.sources` / `preferred_source` | durable product or project intent | `system-intent.sync` | action-required for intent-alignment and full-intent claims |
| Repository-owned `assurance.classification_source` | assurance classifier rules | assurance configuration owner | action-required only for classification-dependent work |
| Configured `assurance.invariant_registry` | invariant definitions | assurance configuration owner | action-required for higher-assurance completion |
| Configured `assurance.risk_registry` | repository risk definitions | assurance configuration owner | action-required for risk-dependent higher-assurance work |
| Assurance requirement, domain proof lane, or closeout `authority_refs` | cited policy, proof/runbook, or closeout authority | assurance configuration owner | action-required only when that requirement, lane, or posture applies |
| Enabled module `capabilities.setup_concerns[].source_obligation` | module-declared semantic source class | declared module owner | declared `recommended` or `action-required`; no module-name branch in Workspace |

Obligations are emitted only when these configurations or capabilities are applicable. Product defaults, broad filename searches, scratch/local files, and paths outside the host repository cannot independently satisfy them. One exact configured repository file is authoritative when the configuration already binds it. Multiple plausible configured files require a human/domain choice unless a preferred source is explicit.

Missing required sources prevent the setup completion receipt from becoming `current`, but deferral remains local and proportional: unrelated work continues, while matching claims or operations route back to setup. Missing recommended sources remain follow-up pressure only.

AW may offer a shell with headings and ownership metadata for a missing source. It must not populate substantive intent, risk, invariant, compliance, release, or proof policy without repo evidence or human authority. Later removal, movement, or staleness of a previously satisfied source re-enters the existing repository-currentness reconciliation path rather than creating source history.
