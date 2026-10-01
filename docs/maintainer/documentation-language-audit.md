# Documentation language audit for #3739

This file records the finite documentation review performed for #3739. It is
review evidence, not a terminology registry or a permanent wording policy.

The audit uses the documentation scope declared by
`.agentic-workspace/instructions/documentation.md`. The rule applied throughout
the current corpus is simple: explain the concrete file, action, setting or
consequence first; retain an exact technical identifier only when the reader
actually needs that identifier.

## Result

- Total Markdown files in the declared scope: **351**
- Rewritten or removed in this PR: **37**
- Current narrative/maintainer pages reviewed with no edit needed: **69**
- Exact/generated references reviewed as technical lookup material: **127**
- Historical/evidence material preserved as historical text: **118**

Known internal shorthand such as `support-bearing`, `admission`,
`projection`, `custody`, `currentness`, `operating contract`,
`affordance`, `claim boundary`, `carriage` and similar noun chains was used
as discovery input, not as a banned-word list. Rewrites were made when the prose
required the reader to understand the implementation term before understanding
the practical meaning.

Exact API/configuration field names remain literal. Historical records were not
rewritten merely to modernise vocabulary because that would change the record of
what was reviewed or observed at the time.

## Rewritten current documentation

- `README.md`
- `docs/agent-os-capabilities.md`
- `docs/agentic-workspace-install.md`
- `docs/architecture.md`
- `docs/architecture/learning-effectiveness.md`
- `docs/architecture/learning-promotion.md`
- `docs/architecture/shared-rust-core.md`
- `docs/assurance-authority-contract.md`
- `docs/collaboration-safety.md`
- `docs/continuation-readiness-projections.md`
- `docs/customization.md`
- `docs/design-principles.md`
- `docs/documentation-style-guide.md`
- `docs/ecosystem-roadmap.md`
- `docs/everyday-use.md`
- `docs/evidence-and-support.md`
- `docs/extension-boundary.md`
- `docs/host-repo-learning.md`
- `docs/integration-contract.md`
- `docs/jumpstart-contract.md`
- `docs/maintainer/contributor-playbook.md`
- `docs/maintainer/documentation-language-audit.md`
- `docs/maintainer/index.md`
- `docs/maintainer/maintainer-commands.md`
- `docs/maintainer/testing-strategy.md`
- `docs/maturity-model.md`
- `docs/module-capability-contract.md`
- `docs/package/installed-surfaces.md`
- `docs/package/lifecycle.md`
- `docs/package/overview.md`
- `docs/package/scoped-instructions.md`
- `docs/package/skill-authoring.md`
- `docs/routine-work-context.md`
- `docs/security/threat-model.md`
- `docs/troubleshooting.md`
- `docs/verification.md`
- `docs/which-package.md`

## Reviewed current documentation with no change

These pages were included in the audit. No edit was made where the prose was
already locally intelligible or where the remaining technical term was introduced
with a concrete meaning.

- `.release/changes/README.md`
- `docs/documentation-status.md`
- `docs/host-repo-dogfooding-report-template.md`
- `docs/index.md`
- `docs/maintainer/benchmarking-contract.md`
- `docs/maintainer/chatgpt-review-continuation.md`
- `docs/maintainer/configuration-contraction.md`
- `docs/maintainer/consequential-delegation.md`
- `docs/maintainer/context-memory-curation.md`
- `docs/maintainer/contract-test-replacement-plan.md`
- `docs/maintainer/dogfooding-feedback.md`
- `docs/maintainer/external-shaping-and-fresh-sessions.md`
- `docs/maintainer/independent-native-owners.md`
- `docs/maintainer/installed-contract-design-checklist.md`
- `docs/maintainer/memory-consequences.md`
- `docs/maintainer/memory-lifetime-boundary.md`
- `docs/maintainer/merge-order-independent-package-state.md`
- `docs/maintainer/model-cli-dogfooding-harness.md`
- `docs/maintainer/module-extension-effort-ledger.md`
- `docs/maintainer/native-execution-configurations.md`
- `docs/maintainer/native-npm-artifact.md`
- `docs/maintainer/native-planning-creation.md`
- `docs/maintainer/native-proof-execution.md`
- `docs/maintainer/native-release-topology.md`
- `docs/maintainer/native-repository-path.md`
- `docs/maintainer/native-startup-adapter.md`
- `docs/maintainer/native-system-intent.md`
- `docs/maintainer/native-verification-admission.md`
- `docs/maintainer/native-verification-strategy.md`
- `docs/maintainer/native-workflow-artifact-profile.md`
- `docs/maintainer/operating-carriage.md`
- `docs/maintainer/operational-affordance-design.md`
- `docs/maintainer/planning-lifetime-boundary.md`
- `docs/maintainer/proof-procedure.md`
- `docs/maintainer/proof-publication-custody.md`
- `docs/maintainer/repository-layout.md`
- `docs/maintainer/repository-read-profile.md`
- `docs/maintainer/retained-knowledge-and-owner-changes.md`
- `docs/maintainer/reusable-source-assessments.md`
- `docs/maintainer/route-registry-sources.md`
- `docs/maintainer/rust-toolchain.md`
- `docs/maintainer/scheduled-tasks/README.md`
- `docs/maintainer/scheduled-tasks/aw-public-watch.md`
- `docs/maintainer/selected-proof-execution.md`
- `docs/maintainer/source-payload-operational-install.md`
- `docs/maintainer/standing-obligations.md`
- `docs/maintainer/testing-reference.md`
- `docs/maintainer/typescript-planning-activation-custody.md`
- `docs/native-patch-delivery.md`
- `docs/package/cli-boundary-tests.md`
- `docs/package/commands.md`
- `docs/package/contracts.md`
- `docs/package/generated-behavior-test-inventory.md`
- `docs/package/knowledge-gates.md`
- `docs/package/knowledge-routing.md`
- `docs/package/modules.md`
- `docs/package/output-profiles.md`
- `docs/planning-cli-naming.md`
- `docs/planning-live-state-collaboration-design.md`
- `docs/priority3-validation.md`
- `docs/priority4-validation.md`
- `docs/priority5-validation.md`
- `docs/reconciliation-contract.md`
- `docs/release-and-versioning.md`
- `docs/repo-source-obligation-contract.md`
- `docs/setup-findings-contract.md`
- `src/tooling/github/README.md`
- `src/tooling/model-cli-harness/external-agent-evaluation/README.md`
- `tools/skills/README.md`

## Exact/generated reference material

These pages primarily document exact schemas, fields, commands or generated
contracts. Identifiers remain unchanged. The audit treats their exact spelling as
technical reference rather than ordinary explanatory prose; human-facing guides
must explain those identifiers without making readers infer their meaning.

- `docs/reference/agent-aid-manifest.md`
- `docs/reference/agent-feedback.md`
- `docs/reference/assignment-context-cost.md`
- `docs/reference/assignment-lifecycle-input.md`
- `docs/reference/assignment-lifecycle-result.md`
- `docs/reference/assignment-transport-metrics.md`
- `docs/reference/assignment-worker-context.md`
- `docs/reference/assurance-applicability.md`
- `docs/reference/assurance-application.md`
- `docs/reference/authority-markers.md`
- `docs/reference/cli-catalogue.md`
- `docs/reference/command-adapter-generation.md`
- `docs/reference/command-package-ir.md`
- `docs/reference/compact-contract-answer.md`
- `docs/reference/config-report-input.md`
- `docs/reference/config-report-result.md`
- `docs/reference/conformance.md`
- `docs/reference/context-authority-declaration.md`
- `docs/reference/context-authority-owner-result.md`
- `docs/reference/context-authority-registry.md`
- `docs/reference/context-gap.md`
- `docs/reference/context-templates.md`
- `docs/reference/contract-inventory.md`
- `docs/reference/correction-event-input.md`
- `docs/reference/correction-event-result.md`
- `docs/reference/decision-point-carry-inspect-result.md`
- `docs/reference/decision-point-carry-prune-result.md`
- `docs/reference/decision-point-carry-select-result.md`
- `docs/reference/delegation-outcome-append-input.md`
- `docs/reference/delegation-outcome-append-result.md`
- `docs/reference/delegation-outcomes.md`
- `docs/reference/effect-attempt.md`
- `docs/reference/evaluation-authority-refresh-input.md`
- `docs/reference/evaluation-authority-refresh-result.md`
- `docs/reference/evaluation-closure-authority.md`
- `docs/reference/evaluation-definition.md`
- `docs/reference/evaluation-domain-authority.md`
- `docs/reference/evaluation-issue-disposition.md`
- `docs/reference/evaluation-observation-input.md`
- `docs/reference/evaluation-observation.md`
- `docs/reference/evaluation-observe-result.md`
- `docs/reference/evaluation-report-delivery-input.md`
- `docs/reference/evaluation-report-delivery-result.md`
- `docs/reference/evaluation-summary.md`
- `docs/reference/evidence-authority.md`
- `docs/reference/executable-affordance.md`
- `docs/reference/external-evidence-candidate.md`
- `docs/reference/external-evidence-host-result.md`
- `docs/reference/external-evidence-operation-input.md`
- `docs/reference/external-evidence-operation-result.md`
- `docs/reference/final-response-admission-result.md`
- `docs/reference/generated-behavior-stratification.md`
- `docs/reference/generated-command-check-inventory.md`
- `docs/reference/guidance-lifecycle-input.md`
- `docs/reference/guidance-lifecycle-result.md`
- `docs/reference/implementer-context.md`
- `docs/reference/improvement-latitude-policy.md`
- `docs/reference/improvement-signal-contract.md`
- `docs/reference/index.md`
- `docs/reference/installed-surface-catalogue.md`
- `docs/reference/instruction-applicability.md`
- `docs/reference/instruction-clause-program.md`
- `docs/reference/local-chat-checkpoint-write-result.md`
- `docs/reference/local-chat-checkpoint.md`
- `docs/reference/local-chat-checkpoints.md`
- `docs/reference/local-work-thread-prune-result.md`
- `docs/reference/local-work-thread-select-result.md`
- `docs/reference/local-work-thread.md`
- `docs/reference/module-capability.md`
- `docs/reference/native-cli.md`
- `docs/reference/native-delegation-transport.md`
- `docs/reference/operating-decision.md`
- `docs/reference/operation-failure.md`
- `docs/reference/operation-invocation.md`
- `docs/reference/operation-primitives.md`
- `docs/reference/operation.md`
- `docs/reference/operational-affordance-roles.md`
- `docs/reference/optimization-bias-policy.md`
- `docs/reference/ownership-ledger.md`
- `docs/reference/payload-verification-policy.md`
- `docs/reference/planning-integration-proposal.md`
- `docs/reference/planning-integration-receipt.md`
- `docs/reference/planning-issue-relation.md`
- `docs/reference/planning-owner-selection-receipt.md`
- `docs/reference/planning-reconciliation.md`
- `docs/reference/preflight-policy.md`
- `docs/reference/proof-route-cost-replay.md`
- `docs/reference/proof-route-hints.md`
- `docs/reference/proof-routes-manifest.md`
- `docs/reference/proof-selection-rules.md`
- `docs/reference/proof-subject-authority.md`
- `docs/reference/python-contract-consumption.md`
- `docs/reference/python-extraction-map.md`
- `docs/reference/python-runtime-boundary.md`
- `docs/reference/python-runtime-projection-inventory.md`
- `docs/reference/repo-friction-policy.md`
- `docs/reference/repo-improvement-effectiveness.md`
- `docs/reference/repo-improvement-execution.md`
- `docs/reference/report-contract-manifest.md`
- `docs/reference/repository-assurance-decision.md`
- `docs/reference/resolved-evidence-producer.md`
- `docs/reference/review-authentication.md`
- `docs/reference/runtime-compatibility.md`
- `docs/reference/runtime-semantic-exceptions.md`
- `docs/reference/scoped-instruction-operation-input.md`
- `docs/reference/scoped-instruction-operation-result.md`
- `docs/reference/selector-contracts-manifest.md`
- `docs/reference/semantic-task-routes.md`
- `docs/reference/separation-of-duty.md`
- `docs/reference/session-log-event.md`
- `docs/reference/session-logging.md`
- `docs/reference/setup-findings-policy.md`
- `docs/reference/setup-findings.md`
- `docs/reference/skill-spec.md`
- `docs/reference/source-decision-input.md`
- `docs/reference/startup-context.md`
- `docs/reference/structured-file-inventory.md`
- `docs/reference/subsystem-intent.md`
- `docs/reference/target-support.md`
- `docs/reference/verification-requirements.md`
- `docs/reference/view-spec.md`
- `docs/reference/workflow-artifact-profiles.md`
- `docs/reference/workspace-config.md`
- `docs/reference/workspace-local-override.md`
- `docs/reference/workspace-report.md`
- `docs/reference/workspace-runtime-primitive-families.md`
- `docs/reference/workspace-surfaces-manifest.md`

## Historical and exact-text evidence

These files are retained as evidence of prior decisions, experiments, migrations,
reviews or release work. Rewriting their period terminology would make the record
less faithful. Current guides may not rely on these files as the only explanation
of a present-day concept.

- `docs/decisions/README.md`
- `docs/decisions/identity-lifetimes.md`
- `docs/decisions/outcome-terminality.md`
- `docs/decisions/shared-semantic-authority.md`
- `docs/maintainer/activation-inventory.md`
- `docs/maintainer/agent-facing-audit.md`
- `docs/maintainer/agent-facing-core-audit.md`
- `docs/maintainer/agent-facing-maintainer-audit.md`
- `docs/maintainer/agent-facing-module-audit.md`
- `docs/maintainer/assignment-public-disposition.md`
- `docs/maintainer/aw-contract-test-replacement-inventory.md`
- `docs/maintainer/c53-conformance.md`
- `docs/maintainer/c54-conformance-input.md`
- `docs/maintainer/configuration-procedure-3266.md`
- `docs/maintainer/control-input-disposition.md`
- `docs/maintainer/decision-frontier.md`
- `docs/maintainer/execution-continuity-frontier.md`
- `docs/maintainer/final-reconstruction-frontier.md`
- `docs/maintainer/first-stable-safety-disposition.md`
- `docs/maintainer/generated-command-check-inventory.md`
- `docs/maintainer/host-evaluation-3267.md`
- `docs/maintainer/human-decision-audit.md`
- `docs/maintainer/instruction-clause-migration-map.md`
- `docs/maintainer/instruction-topology-migration.md`
- `docs/maintainer/lazy-discovery-measurements.md`
- `docs/maintainer/legacy-target-evidence-admission.md`
- `docs/maintainer/local-installed-state-action-shape-audit.md`
- `docs/maintainer/native-decision-archive-dogfood.md`
- `docs/maintainer/native-domain-proof-candidates.md`
- `docs/maintainer/native-planning-migration-dogfood.md`
- `docs/maintainer/ordinary-caution-action-shape-audit.md`
- `docs/maintainer/owner-transport-exercise.md`
- `docs/maintainer/planning-continuation-action-shape-audit.md`
- `docs/maintainer/proportional-proof-audit.md`
- `docs/maintainer/public-documentation-closure-2026-08-20.md`
- `docs/maintainer/rc4-release-preparation.md`
- `docs/maintainer/reconstruction-conformance.md`
- `docs/maintainer/release-validation.md`
- `docs/maintainer/repo-evidence-requirements.md`
- `docs/maintainer/repo-evolution-dogfood-2026-08-22.md`
- `docs/maintainer/scoped-instruction-migration-evidence.md`
- `docs/maintainer/skill-entry-evidence.md`
- `docs/maintainer/skill-exposure-3325.md`
- `docs/maintainer/skills-first-interface-conformance.md`
- `docs/maintainer/standing-obligation-exercise.md`
- `docs/maintainer/summary-status-preflight-action-shape-audit.md`
- `docs/maintainer/test-knowledge-inventory.md`
- `docs/maintainer/test-strategy-reconstruction-audit.md`
- `docs/reviews/adapter-orchestration-correction-evaluation-closure-2026-08-14.md`
- `docs/reviews/assumption-migration-routing-2026-06-22.md`
- `docs/reviews/assurance-operating-cost-review-2026-04-30.md`
- `docs/reviews/aw-chatgpt-review-continuation-dogfood-2026-07-14.md`
- `docs/reviews/aw-clear-planning-gate-compression-2026-06-23.md`
- `docs/reviews/aw-completion-cost-session-log-analysis-2026-06-23.md`
- `docs/reviews/aw-fresh-session-digest-dogfood-2026-06-23.md`
- `docs/reviews/aw-induced-completion-cost-inventory-2026-06-22.md`
- `docs/reviews/aw-local-chat-checkpoint-resume-dogfood-2026-06-26.md`
- `docs/reviews/aw-long-thread-dogfooding-report-2026-06-28.md`
- `docs/reviews/aw-ordinary-output-budget-guards-2026-06-23.md`
- `docs/reviews/aw-proof-failure-summary-dogfood-2026-06-23.md`
- `docs/reviews/aw-proof-retry-ladder-dogfood-2026-06-23.md`
- `docs/reviews/bootstrap-payload-full-scan-2026-04-29.md`
- `docs/reviews/candidate-b-preparation-evidence.md`
- `docs/reviews/candidate-b-publication.md`
- `docs/reviews/candidate-c-integrated-acceptance.md`
- `docs/reviews/cli-authority-audit-2026-04-26.md`
- `docs/reviews/codex-session-identity-canonical-invocation-2805.md`
- `docs/reviews/compact-intent-3380-2026-09-16.md`
- `docs/reviews/config-effect-review-2026-05-05.md`
- `docs/reviews/config-enforcement-wiring-review-2026-04-29.md`
- `docs/reviews/configured-orchestration-ordinary-action-closure-2026-08-24.md`
- `docs/reviews/decision-reuse-audit-2026-09-03.md`
- `docs/reviews/delegation-lane-cost-audit.md`
- `docs/reviews/delegation-residual-sweep-2026-09-07.md`
- `docs/reviews/documentation-hierarchy-cleanup-review-2026-05-01.md`
- `docs/reviews/dynamic-instruction-lane-closure-2026-08-17.md`
- `docs/reviews/first-contact-guide-contraction-2026-09-22.md`
- `docs/reviews/future-decision-context-closure-2026-08-23.md`
- `docs/reviews/generated-cli-adapter-high-assurance-report-2026-05-01.md`
- `docs/reviews/generated-cli-authority-audit-2026-05-01.md`
- `docs/reviews/generated-cli-package-strategy-2026-04-27.md`
- `docs/reviews/generated-cli-progressive-maturity-2026-05-01.md`
- `docs/reviews/generic-cg-control-operations-plan-2026-06-21.md`
- `docs/reviews/host-feasibility-3383-2026-09-16.md`
- `docs/reviews/memory-verification-runtime-boundary-disposition-2026-06-27.md`
- `docs/reviews/multi-language-cli-generation-gap-audit-2026-04-27.md`
- `docs/reviews/open-issues-closure-2026-08-27.md`
- `docs/reviews/operating-context-lane-closure-2026-08-14.md`
- `docs/reviews/operating-decision-parent-closeout-2026-08-28.md`
- `docs/reviews/operator-facing-closeout-reporting-review-2026-06-01.md`
- `docs/reviews/outside-2821-compatibility-closure-2026-09-02.md`
- `docs/reviews/p1-module-field-disposition.md`
- `docs/reviews/p1-public-surface-disposition.md`
- `docs/reviews/package-owned-assumptions-audit-2026-06-22.md`
- `docs/reviews/planning-record-proof-route-replay-2026-08-31.md`
- `docs/reviews/planning-runtime-boundary-disposition-2026-06-27.md`
- `docs/reviews/post-generation-cli-lifecycle-boundary-review-2026-04-26.md`
- `docs/reviews/powerskill-p1-design-3409.md`
- `docs/reviews/powerskill-p1-integration.md`
- `docs/reviews/powerskill-planning-umbrella-disposition.md`
- `docs/reviews/query-shaped-planning-reads-closeout-2026-08-28.md`
- `docs/reviews/remaining-assumption-authority-migrations-2026-06-22.md`
- `docs/reviews/reopened-product-closure-2026-08-21.md`
- `docs/reviews/repo-directed-improvement-lane-2648.md`
- `docs/reviews/repository-health-audit-2026-08-08.md`
- `docs/reviews/runtime-boundary-decomposition-audit-2026-06-20.md`
- `docs/reviews/selected-proof-execution-replay-2026-08-31.md`
- `docs/reviews/selector-first-output-policy-2026-06-28.md`
- `docs/reviews/self-configuration-integration-review-2026-08-28.md`
- `docs/reviews/shell-adapter-feasibility-2026-04-27.md`
- `docs/reviews/shipped-package-payload-audit-2026-04-28.md`
- `docs/reviews/shipped-payload-surface-inventory-2026-04-29.md`
- `docs/reviews/support-bearing-release-closeout-v0.40.1.md`
- `docs/reviews/system-intent-embodiment-review-2026-04-26.md`
- `docs/reviews/system-intent-future-work-review-2026-04-26.md`
- `docs/reviews/visible-product-surface-inventory-2026-04-26.md`
- `docs/reviews/workspace-lifecycle-provider-boundary-disposition-2026-06-27.md`
- `docs/reviews/workspace-report-context-runtime-disposition-2026-06-21.md`
