-include .env.local

MAKEFLAGS += --no-print-directory

UV_CACHE_DIR ?= $(CURDIR)/.uv-cache-root
REVIEW_MAX_CYCLES ?= 3
export UV_CACHE_DIR
ifeq ($(VALIDATION_JOIN_TOKEN),join:$(VALIDATION_RUN_ID))
VALIDATION_RUN_PROVENANCE ?= transported-child
else
VALIDATION_RUN_ID := $(shell uv run --no-project python scripts/check/allocate_validation_run_id.py)
VALIDATION_JOIN_TOKEN := join:$(VALIDATION_RUN_ID)
VALIDATION_RUN_PROVENANCE := allocated-here
endif
export VALIDATION_RUN_ID
export VALIDATION_JOIN_TOKEN
export VALIDATION_RUN_PROVENANCE
# Serial execution is the safe local default. Callers that have measured
# capacity may explicitly opt in, for example: PYTEST_PARALLEL_ARGS='-n 4'.
PYTEST_PARALLEL_ARGS ?=
WORKSPACE_PYTEST_PARALLEL_ARGS ?= $(PYTEST_PARALLEL_ARGS)
WORKSPACE_PROOF_PYTEST_PARALLEL_ARGS ?= $(PYTEST_PARALLEL_ARGS)
PACKAGE_PYTEST_PARALLEL_ARGS ?= $(PYTEST_PARALLEL_ARGS)
MEMORY_PYTEST_PARALLEL_ARGS ?= $(PACKAGE_PYTEST_PARALLEL_ARGS)
PLANNING_PYTEST_PARALLEL_ARGS ?= $(PACKAGE_PYTEST_PARALLEL_ARGS)
VERIFICATION_PYTEST_PARALLEL_ARGS ?= $(PACKAGE_PYTEST_PARALLEL_ARGS)
COMPACT_RUN = uv run python scripts/check/run_compact_command.py
PACKED_ARTIFACT_DIR ?= $(CURDIR)/.agentic-workspace/local/packed-artifact-conformance
PACKED_ARTIFACT_RECEIPT ?= $(PACKED_ARTIFACT_DIR)/generated-command-conformance-local.json
PACKED_ARTIFACT_CONTEXT ?= local

WORKSPACE_TEST_CLI = \
	tests/test_native_advisory_config.py \
	tests/test_native_assignment_judgment.py \
	tests/test_native_assignment_policy.py \
	tests/test_native_claim_review.py \
	tests/test_native_config_admission.py \
	tests/test_native_configuration_write.py \
	tests/test_native_delegation_lifecycle.py \
	tests/test_native_execution_configurations.py \
	tests/test_native_former_routes.py \
	tests/test_native_frontier.py \
	tests/test_native_independent_owner.py \
	tests/test_native_instruction_verification.py \
	tests/test_native_instruction_write.py \
	tests/test_native_invoke_continuation.py \
	tests/test_native_maintainer_logging.py \
	tests/test_native_measurement.py \
	tests/test_native_memory_capture.py \
	tests/test_native_memory_declarations.py \
	tests/test_native_memory_disposition.py \
	tests/test_native_npm_routes.py \
	tests/test_native_operating_carriage.py \
	tests/test_native_planning_create.py \
	tests/test_native_planning_lifetime.py \
	tests/test_native_proof_procedure.py \
	tests/test_native_proof_scope.py \
	tests/test_native_public_cli.py \
	tests/test_native_readonly_handoff.py \
	tests/test_native_release_receipt.py \
	tests/test_native_release_topology.py \
	tests/test_native_repository_adoption.py \
	tests/test_native_repository_decisions.py \
	tests/test_native_resource_owner.py \
	tests/test_native_resources.py \
	tests/test_native_source_reconciliation.py \
	tests/test_native_startup_adapter.py \
	tests/test_native_system_intent.py \
	tests/test_native_transport.py \
	tests/test_native_verification_declarations.py \
	tests/test_native_workflow_artifact_profile.py

WORKSPACE_TEST_PROOF = \
	tests/test_native_domain_proof.py \
	tests/test_native_proof_producer.py \
	tests/test_native_verification_strategy.py

WORKSPACE_TEST_SESSION_REVIEW = \
	tests/test_chatgpt_review_loop.py \
	tests/test_codex_session_identity_agent_aid.py \
	tests/test_github_check_inspection.py \
	tests/test_pr_comment_delta.py \
	tests/test_review_preparation.py \
	tests/test_review_stack_ops.py \
	tests/test_start_chatgpt_review_poller.py

WORKSPACE_TEST_CONTRACTS = \
	tests/test_assurance_applicability.py \
	tests/test_external_consumer_readiness.py \
	tests/test_pr_semver_integration.py \
	tests/test_proof_publication.py \
	tests/test_proof_receipt_owner.py \
	tests/test_source_request_dependencies.py \
	tests/test_agent_aids.py \
	tests/test_cargo_release.py \
	tests/test_ci_exhaustive_admission.py \
	tests/test_configuration_procedure.py \
	tests/test_contract_catalogues.py \
	tests/test_github_issue_body_agent_aid.py \
	tests/test_github_workflow_skills.py \
	tests/test_language_facade.py \
	tests/test_no_absolute_paths.py \
	tests/test_package_artifact_duplicates.py \
	tests/test_platform_release.py \
	tests/test_preview_public_smoke.py \
	tests/test_reconstruction_disposition_map.py \
	tests/test_registry_release.py \
	tests/test_release_candidate.py \
	tests/test_schema_reference_docs.py \
	tests/test_security_supply_chain.py \
	tests/test_selected_procedure_preparation.py \
	tests/test_shared_core.py \
	tests/test_skills_first_interface.py \
	tests/test_structured_executor_contracts.py \
	tests/test_structured_executor_replay.py \
	tests/test_structured_executor_safety.py \
	tests/test_structured_file_inventory.py \
	tests/test_validation_runtime_plan.py \
	tests/test_workspace_makefile_targets.py

WORKSPACE_TEST_GENERATED_RELEASE = \
	tests/test_coordinated_release.py \
	tests/test_package_identity.py \
	tests/test_preview_release.py \
	tests/test_preview_release_workflow.py \
	tests/test_release_recovery_status.py \
	tests/test_release_workflows.py \
	tests/test_support_bearing_promotion.py \
	tests/test_workspace_packaging.py

WORKSPACE_TEST_INTEGRATION = \
	tests/test_agentic_workspace_launcher.py \
	tests/test_compact_command_runner.py \
	tests/test_completion_cost_json_corpus.py \
	tests/test_completion_cost_lane_evidence.py \
	tests/test_completion_cost_live_behavior_proof.py \
	tests/test_completion_cost_schema_analysis.py \
	tests/test_external_agent_evaluation_lane.py \
	tests/test_external_integration_boundary.py \
	tests/test_git_hooks.py \
	tests/test_long_horizon_episode.py \
	tests/test_v1_contract.py

.PHONY: help sync-all sync-memory sync-planning sync-verification \
	setup install-hooks pre-commit \
	test test-nosync test-rust-core test-workspace test-workspace-cli test-workspace-proof test-workspace-session-review test-workspace-contracts test-workspace-generated-release test-workspace-integration test-memory test-planning test-verification \
	lint lint-nosync lint-workspace markdownlint markdownlint-workspace markdownlint-memory \
	typecheck typecheck-nosync typecheck-workspace \
	format format-nosync format-workspace \
	format-check format-check-nosync format-check-workspace \
	verify verify-nosync verify-workspace verify-memory verify-planning verify-verification \
	memory-freshness memory-freshness-strict  structured-file-inventory structured-file-inventory-changed security-supply-chain package-artifact-duplicates agent-aids native-sources render-schema-reference schema-reference-docs absolute-paths \
	 packed-artifact-conformance \
	check check-nosync check-bounded-parallel check-memory check-memory-nosync check-planning check-planning-nosync check-verification check-verification-nosync check-all start-review-poller

help:
	@echo "setup: synchronize the development environment and install hooks"
	@echo "test: run native/public and maintainer tests"
	@echo "test-rust-core: build and test both native crates"
	@echo "test-memory / test-planning / test-verification: focused native owner tests"
	@echo "lint / typecheck / format-check: source validation"
	@echo "native-sources: product boundary and generated agent interface checks"
	@echo "packed-artifact-conformance: validate exact release artifacts"
	@echo "check: run the aggregate development checks"

sync-all:
	@$(COMPACT_RUN) --label "sync-all" -- uv sync --locked --all-groups

install-hooks:
	uv run python scripts/install_git_hooks.py

setup: sync-all install-hooks

pre-commit:
	@uv run python scripts/git_hooks/pre_commit.py

start-review-poller:
	@$(COMPACT_RUN) --label "review poller" -- uv run python tools/start_chatgpt_review_poller.py --target . --max-cycles $(REVIEW_MAX_CYCLES)

sync-memory:
	@$(COMPACT_RUN) --label "sync-memory" -- uv sync --all-packages --group dev

sync-planning:
	@$(COMPACT_RUN) --label "sync-planning" -- uv sync --all-packages --group dev

sync-verification:
	@$(COMPACT_RUN) --label "sync-verification" -- uv sync --all-packages --group dev

.NOTPARALLEL: test-workspace

test-rust-core:
	@cargo build --locked --workspace --bins
	@cargo test --locked --workspace

test-workspace: test-workspace-cli test-workspace-proof test-workspace-session-review

# Retained schema/generation/release model suites are explicit source maintenance.
test-source-maintenance: test-workspace-contracts test-workspace-generated-release test-workspace-integration

test-workspace-cli:
	@$(COMPACT_RUN) --label "workspace CLI tests" -- uv run pytest $(WORKSPACE_PYTEST_PARALLEL_ARGS) $(WORKSPACE_TEST_CLI)

test-workspace-proof:
	@$(COMPACT_RUN) --label "workspace proof tests" -- uv run pytest $(WORKSPACE_PROOF_PYTEST_PARALLEL_ARGS) $(WORKSPACE_TEST_PROOF)

test-workspace-session-review:
	@$(COMPACT_RUN) --label "workspace session and review tests" -- uv run pytest $(WORKSPACE_PYTEST_PARALLEL_ARGS) $(WORKSPACE_TEST_SESSION_REVIEW)

test-workspace-contracts:
	@$(COMPACT_RUN) --label "workspace contract tests" -- uv run pytest $(WORKSPACE_PYTEST_PARALLEL_ARGS) $(WORKSPACE_TEST_CONTRACTS)

test-workspace-generated-release:
	@$(COMPACT_RUN) --label "workspace generated and release tests" -- uv run pytest $(WORKSPACE_PYTEST_PARALLEL_ARGS) $(WORKSPACE_TEST_GENERATED_RELEASE)

test-workspace-integration:
	@$(COMPACT_RUN) --label "workspace integration tests" -- uv run pytest $(WORKSPACE_PYTEST_PARALLEL_ARGS) $(WORKSPACE_TEST_INTEGRATION)

test-memory:
	@uv run pytest tests/test_native_memory_capture.py tests/test_native_memory_disposition.py tests/test_native_memory_declarations.py -q

test-planning:
	@uv run pytest tests/test_native_planning_create.py tests/test_native_planning_lifetime.py -q

test-verification:
	@uv run pytest tests/test_native_proof_producer.py tests/test_native_verification_strategy.py tests/test_native_domain_proof.py -q

test-nosync: test-workspace test-source-maintenance

test: sync-all test-nosync

lint-workspace: markdownlint-workspace
	@$(COMPACT_RUN) --label "workspace lint" -- uv run ruff check src tests
	@cargo fmt --all -- --check
	@cargo clippy --locked --workspace --all-targets -- -D warnings




lint-nosync: lint-workspace

lint: sync-all lint-nosync

markdownlint-memory:

markdownlint-workspace:
	@$(COMPACT_RUN) --label "workspace markdownlint" -- uv run python scripts/check/check_workspace_markdown.py

markdownlint: sync-all markdownlint-workspace markdownlint-memory

typecheck-workspace:
	@$(COMPACT_RUN) --label "workspace typecheck" -- uv run ty check src




typecheck-nosync: typecheck-workspace

typecheck: sync-all typecheck-nosync

format-workspace:
	@$(COMPACT_RUN) --label "workspace format" -- uv run ruff format src tests




format-nosync: format-workspace

format: sync-all format-nosync

format-check-workspace:
	@$(COMPACT_RUN) --label "workspace format-check" -- uv run ruff format --check src tests




format-check-nosync: format-check-workspace

format-check: sync-all format-check-nosync

# Native ingress and all four public transports supersede the retired Python CLI suite.
verify-workspace:
	@$(COMPACT_RUN) --label "workspace native command admission" -- uv run pytest tests/test_native_public_cli.py -q

verify-memory:
	@uv run pytest tests/test_native_memory_declarations.py -q

verify-planning:
	@uv run pytest tests/test_native_planning_lifetime.py -q

verify-verification:
	@uv run pytest tests/test_native_verification_declarations.py -q

verify-nosync: verify-workspace native-sources

verify: sync-all verify-nosync

memory-freshness:
	@$(COMPACT_RUN) --label "memory freshness" -- uv run python scripts/check/check_memory_freshness.py

memory-freshness-strict:
	@$(COMPACT_RUN) --label "memory freshness strict" -- uv run python scripts/check/check_memory_freshness.py --strict



structured-file-inventory:
	@$(COMPACT_RUN) --label "structured file inventory" -- uv run python scripts/check/check_structured_file_inventory.py

structured-file-inventory-changed:
	@$(COMPACT_RUN) --label "structured file inventory changed" -- uv run python scripts/check/check_structured_file_inventory.py --changed $(CHANGED_PATHS)


security-supply-chain:
	@uv run python scripts/check/check_security_supply_chain.py --format json

package-artifact-duplicates:
	@$(COMPACT_RUN) --label "package artifact duplicates" -- uv run python scripts/check/check_package_artifact_duplicates.py

agent-aids:
	@$(COMPACT_RUN) --label "agent aid manifests" -- uv run python scripts/check/check_agent_aids.py






render-schema-reference:
	@$(COMPACT_RUN) --label "render schema reference" -- uv run python scripts/generate/generate_schema_reference.py
	@$(COMPACT_RUN) --label "render contract catalogues" -- uv run python scripts/generate/generate_contract_catalogues.py


schema-reference-docs:
	@$(COMPACT_RUN) --label "schema reference docs" -- uv run python scripts/generate/generate_schema_reference.py --check --check-annotations
	@$(COMPACT_RUN) --label "contract catalogues" -- uv run python scripts/generate/generate_contract_catalogues.py --check

absolute-paths:
	@$(COMPACT_RUN) --label "absolute paths" -- uv run python scripts/check/check_no_absolute_paths.py




packed-artifact-conformance:
	@uv run python scripts/check/check_native_release_topology.py --artifact-dir "$(PACKED_ARTIFACT_DIR)" --receipt-out "$(PACKED_ARTIFACT_RECEIPT)" --execution-context "$(PACKED_ARTIFACT_CONTEXT)"

check-memory-nosync: test-memory verify-memory memory-freshness-strict

check-memory: sync-all check-memory-nosync

check-planning-nosync: test-planning memory-freshness

check-planning: sync-all check-planning-nosync

check-verification-nosync: test-verification verify-verification

check-verification: sync-all check-verification-nosync

check-nosync: native-sources test-rust-core test-nosync lint-nosync typecheck-nosync format-check-nosync verify-nosync memory-freshness-strict structured-file-inventory security-supply-chain package-artifact-duplicates agent-aids absolute-paths

check: sync-all check-nosync

check-bounded-parallel:
	@$(MAKE) sync-all
	@$(MAKE) test-workspace-cli WORKSPACE_PYTEST_PARALLEL_ARGS='-n 16'
	@$(MAKE) -j 4 test-workspace-proof test-workspace-session-review test-workspace-contracts test-workspace-generated-release test-workspace-integration test-memory test-planning test-verification lint-nosync typecheck-nosync format-check-nosync verify-nosync memory-freshness-strict structured-file-inventory package-artifact-duplicates agent-aids absolute-paths WORKSPACE_PYTEST_PARALLEL_ARGS='-n 16' WORKSPACE_PROOF_PYTEST_PARALLEL_ARGS='-n 8' MEMORY_PYTEST_PARALLEL_ARGS='-n 8' PLANNING_PYTEST_PARALLEL_ARGS='' VERIFICATION_PYTEST_PARALLEL_ARGS='-n 8'

check-all: check-nosync

native-sources:
	@uv run python scripts/check/check_native_sources.py
	@uv run python scripts/generate/generate_agent_interface.py --check
