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
# Serial execution is the safe local default.  Callers that have measured
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
	tests/test_bounded_external_issue_route.py \
	tests/test_dynamic_instruction_projection.py \
	tests/test_operating_projection_receipt.py \
	tests/test_workspace_cli.py \
	tests/test_workspace_cli_blackbox.py \
	tests/test_workspace_config_cli.py \
	tests/test_workspace_defaults_cli.py \
	tests/test_workspace_doctor_status_cli.py \
	tests/test_workspace_evaluation.py \
	tests/test_workspace_implement_cli.py \
	tests/test_workspace_intent_cli.py \
	tests/test_workspace_modules_cli.py \
	tests/test_operating_decision.py \
	tests/test_workspace_ownership_cli.py \
	tests/test_workspace_planning_help_cli.py \
	tests/test_workspace_projection_reuse.py \
	tests/test_workspace_runtime_projection.py \
	tests/test_workspace_skills_cli.py \
	tests/test_workspace_summary_cli.py

WORKSPACE_TEST_PROOF = \
	tests/test_assurance_authority.py \
	tests/test_generated_command_package_proof_runner.py \
	tests/test_output_profile_budgets.py \
	tests/test_proof_subject.py \
	tests/test_workspace_proof_cli.py \
	tests/test_workspace_proof_generated_packages_cli.py

WORKSPACE_TEST_SESSION_REVIEW = \
	tests/test_chatgpt_review_loop.py \
	tests/test_codex_session_identity_agent_aid.py \
	tests/test_github_check_inspection.py \
	tests/test_pr_comment_delta.py \
	tests/test_review_merge_gate.py \
	tests/test_review_stack_ops.py \
	tests/test_review_stack_transitions.py \
	tests/test_start_chatgpt_review_poller.py \
	tests/test_workspace_session_logging.py

WORKSPACE_TEST_CONTRACTS = \
	tests/test_agent_aids.py \
	tests/test_command_surface_bundle_check.py \
	tests/test_contract_catalogues.py \
	tests/test_contract_tooling_surfaces.py \
	tests/test_github_issue_body_agent_aid.py \
	tests/test_instruction_clause_ir.py \
	tests/test_intent_feedback.py \
	tests/test_module_contract.py \
	tests/test_no_absolute_paths.py \
	tests/test_package_artifact_duplicates.py \
	tests/test_prompt_semantic_markers.py \
	tests/test_review_scale_extracted_boundaries.py \
	tests/test_runtime_compatibility.py \
	tests/test_runtime_implementation_ownership.py \
	tests/test_shared_core.py \
	tests/test_schema_reference_docs.py \
	tests/test_security_supply_chain.py \
	tests/test_scoped_instructions.py \
	tests/test_structured_file_inventory.py \
	tests/test_trusted_execution.py \
	tests/test_validation_runtime_plan.py \
	tests/test_workspace_makefile_targets.py

WORKSPACE_TEST_GENERATED_RELEASE = \
	tests/test_branch_carried_package_state.py \
	tests/test_command_generation_integration.py \
	tests/test_command_generation_release_promotion.py \
	tests/test_coordinated_release.py \
	tests/test_generated_tool_conformance.py \
	tests/test_package_identity.py \
	tests/test_release_recovery_status.py \
	tests/test_release_workflows.py \
	tests/test_support_bearing_promotion.py \
	tests/test_workspace_packaging.py

WORKSPACE_TEST_INTEGRATION = \
	tests/test_adaptation.py \
	tests/test_agentic_workspace_launcher.py \
	tests/test_compact_command_runner.py \
	tests/test_composed_operation_scenarios.py \
	tests/test_completion_cost_json_corpus.py \
	tests/test_completion_cost_lane_evidence.py \
	tests/test_completion_cost_live_behavior_proof.py \
	tests/test_completion_cost_schema_analysis.py \
	tests/test_cross_drive_target_paths.py \
	tests/test_external_agent_evaluation_lane.py \
	tests/test_external_consumer_profile.py \
	tests/test_external_consumer_readiness.py \
	tests/test_external_integration_boundary.py \
	tests/test_external_operation_clients.py \
	tests/test_git_hooks.py \
	tests/test_lazy_discovery_measurements.py \
	tests/test_lifecycle_smoke.py \
	tests/test_long_horizon_episode.py \
	tests/test_maintainer_surfaces.py \
	tests/test_memory_effectiveness.py \
	tests/test_module_extension_scenario_matrix.py \
	tests/test_planning_delegation.py \
	tests/test_reconciliation.py \
	tests/test_repository_scanning.py \
	tests/test_repo_evolution_scenario.py \
	tests/test_repo_improvement_effectiveness.py \
	tests/test_source_payload_operational_install.py \
	tests/test_v1_contract.py

.PHONY: help sync-all sync-memory sync-planning sync-verification \
	setup install-hooks pre-commit \
	test test-nosync test-rust-core test-workspace test-workspace-cli test-workspace-proof test-workspace-session-review test-workspace-contracts test-workspace-contracts-measurement test-workspace-generated-release test-workspace-integration test-memory test-planning test-verification \
	lint lint-nosync lint-workspace lint-memory lint-planning lint-verification markdownlint markdownlint-memory \
	typecheck typecheck-nosync typecheck-workspace typecheck-memory typecheck-planning typecheck-verification \
	format format-nosync format-workspace format-memory format-planning format-verification \
	format-check format-check-nosync format-check-workspace format-check-memory format-check-planning format-check-verification \
	verify verify-nosync verify-workspace verify-memory verify-planning verify-verification composed-operation-scenarios \
	memory-freshness memory-freshness-strict recurring-friction-ledger planning-surfaces planning-surfaces-strict validation-runtime-plan validation-runtime-plan-measurement structured-file-inventory structured-file-inventory-changed runtime-implementation-ownership security-supply-chain package-artifact-duplicates agent-aids source-payload-operational-install source-payload-operational-install-strict maintainer-surfaces maintainer-surfaces-strict render-agent-docs render-schema-reference render-command-packages schema-reference-docs absolute-paths \
	generated-command-packages generated-command-packages-docker packed-artifact-conformance output-profile-budgets external-consumer-readiness \
	check check-nosync check-bounded-parallel check-memory check-memory-nosync check-planning check-planning-nosync check-verification check-verification-nosync check-all start-review-poller

help:
	@echo "Available targets:"
	@echo "  help                 Show this help."
	@echo "  setup                Sync the dev environment and install local git hooks."
	@echo "  install-hooks        Install the repo-managed local git hooks for this clone."
	@echo "  pre-commit           Run format, lint, and typecheck in one collision-safe validation run."
	@echo "  sync-all             Sync merged root environment for all workspace packages."
	@echo "  sync-memory          Sync consolidated root dev environment for memory package checks."
	@echo "  sync-planning        Sync consolidated root dev environment for planning package checks."
	@echo "  sync-verification    Sync consolidated root dev environment for verification package checks."
	@echo "  test                 Run workspace and package test suites serially by default."
	@echo "  test-rust-core       Run the shared Rust operating-decision core tests."
	@echo "  test-nosync          Run tests after caller-provided dependency sync."
	@echo "                       Opt into pytest-xdist only with PYTEST_PARALLEL_ARGS='-n <count>'."
	@echo "  test-workspace       Run all focused workspace test targets serially."
	@echo "  test-workspace-cli   Run workspace CLI, config, summary, and projection tests."
	@echo "  test-workspace-proof Run proof-router and generated proof-package tests."
	@echo "  test-workspace-session-review  Run session logging and review-loop tests."
	@echo "  test-workspace-contracts  Run contract, schema, inventory, and guardrail tests."
	@echo "  test-workspace-generated-release  Run generated-command and release workflow tests."
	@echo "  test-workspace-integration  Run external, lifecycle, launcher, and cost tests."
	@echo "  lint                 Run non-mutating lint checks across workspace and packages."
	@echo "  lint-nosync          Run lint checks after caller-provided dependency sync."
	@echo "  markdownlint         Run Markdown lint checks for the memory package surfaces."
	@echo "  typecheck            Run ty type checks across workspace and packages."
	@echo "  typecheck-nosync     Run type checks after caller-provided dependency sync."
	@echo "  packed-artifact-conformance  Replay CI's exact npm-artifact semantic lane locally."
	@echo "  format               Apply Ruff formatting across workspace and packages."
	@echo "  format-check         Run formatting checks across workspace and packages."
	@echo "  format-check-nosync  Run formatting checks after caller-provided dependency sync."
	@echo "  verify               Verify workspace CLI wiring and both packaged payload contracts."
	@echo "  verify-nosync        Run verification checks after caller-provided dependency sync."
	@echo "  memory-freshness     Run the root memory freshness audit."
	@echo "  recurring-friction-ledger  Run the root recurring-friction ledger audit."
	@echo "  planning-surfaces    Run the root planning surface audit."
	@echo "  validation-runtime-plan  Check validation graph, evidence, CI/local parity, and duplicate-execution policy."
	@echo "  structured-file-inventory  Check tracked JSON/TOML/YAML/YML files against the inventory."
	@echo "  structured-file-inventory-changed  Check CHANGED_PATHS with full escalation on inventory authority changes."
	@echo "  runtime-implementation-ownership  Enforce one runtime owner and review-scale ratchets."
	@echo "  security-supply-chain  Verify immutable CI, scanners, trusted-shell admission, and release provenance."
	@echo "  package-artifact-duplicates  Check built package artifacts for duplicate archive members."
	@echo "  agent-aids           Check checked-in agent aid manifests and coverage."
	@echo "  source-payload-operational-install  Run source/payload/root-install boundary checks."
	@echo "  maintainer-surfaces  Run maintainer-surface freshness and liveness checks."
	@echo "  render-agent-docs    Regenerate root planning docs from the managed manifest."
	@echo "  render-schema-reference  Regenerate generated JSON Schema reference docs."
	@echo "  render-command-packages  Regenerate generated command package CLIs."
	@echo "  absolute-paths       Fail if tracked files contain absolute filesystem paths."
	@echo "  generated-command-packages  Run generated command package proof with compact output."
	@echo "  generated-command-packages-docker  Run generated command package Docker proof with compact output."
	@echo "  check                Run the full root validation lane."
	@echo "  check-nosync         Run the full root validation lane after caller-provided dependency sync."
	@echo "  check-bounded-parallel  Run full validation with explicit bounded pytest-xdist workers."
	@echo "  check-memory         Run package-local checks for packages/memory."
	@echo "  check-planning       Run package-local checks for packages/planning."
	@echo "  check-verification   Run package-local checks for packages/verification."
	@echo "  check-all            Run checks for imported packages."
	@echo "  start-review-poller  Start one detached global PR-review poller for this checkout."

sync-all:
	@$(COMPACT_RUN) --label "sync-all" -- uv sync --all-packages --all-groups

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
	@cargo test --workspace

test-workspace: test-workspace-cli test-workspace-proof test-workspace-session-review test-workspace-contracts test-workspace-generated-release test-workspace-integration

test-workspace-cli:
	@$(COMPACT_RUN) --label "workspace CLI tests" -- uv run pytest $(WORKSPACE_PYTEST_PARALLEL_ARGS) $(WORKSPACE_TEST_CLI)

test-workspace-proof:
	@$(COMPACT_RUN) --label "workspace proof tests" -- uv run pytest $(WORKSPACE_PROOF_PYTEST_PARALLEL_ARGS) $(WORKSPACE_TEST_PROOF)

test-workspace-session-review:
	@$(COMPACT_RUN) --label "workspace session and review tests" -- uv run pytest $(WORKSPACE_PYTEST_PARALLEL_ARGS) $(WORKSPACE_TEST_SESSION_REVIEW)

test-workspace-contracts:
	@$(COMPACT_RUN) --label "workspace contract tests" -- uv run pytest $(WORKSPACE_PYTEST_PARALLEL_ARGS) $(WORKSPACE_TEST_CONTRACTS)

test-workspace-contracts-measurement:
	@$(COMPACT_RUN) --label "workspace contract measurement tests" -- uv run pytest $(WORKSPACE_PYTEST_PARALLEL_ARGS) $(WORKSPACE_TEST_CONTRACTS) -k "not test_validation_runtime_plan_matches_makefile_ci_and_evidence"

test-workspace-generated-release:
	@$(COMPACT_RUN) --label "workspace generated and release tests" -- uv run pytest $(WORKSPACE_PYTEST_PARALLEL_ARGS) $(WORKSPACE_TEST_GENERATED_RELEASE)

test-workspace-integration:
	@$(COMPACT_RUN) --label "workspace integration tests" -- uv run pytest $(WORKSPACE_PYTEST_PARALLEL_ARGS) $(WORKSPACE_TEST_INTEGRATION)

test-memory:
	@$(COMPACT_RUN) --label "memory tests" --cwd packages/memory -- uv run pytest $(MEMORY_PYTEST_PARALLEL_ARGS)

test-planning:
	@$(COMPACT_RUN) --label "planning tests" --cwd packages/planning -- uv run pytest $(PLANNING_PYTEST_PARALLEL_ARGS)

test-verification:
	@$(COMPACT_RUN) --label "verification tests" --cwd packages/verification -- uv run pytest $(VERIFICATION_PYTEST_PARALLEL_ARGS)

test-nosync: test-workspace test-memory test-planning test-verification

test: sync-all test-nosync

lint-workspace:
	@$(COMPACT_RUN) --label "workspace lint" -- uv run ruff check src tests
	@$(COMPACT_RUN) --label "prompt semantic markers" -- uv run python scripts/check/check_prompt_semantic_markers.py
	@cargo fmt --all -- --check
	@cargo clippy --workspace --all-targets -- -D warnings

lint-memory:
	@$(COMPACT_RUN) --label "memory lint" --cwd packages/memory -- uv run ruff check .
	@$(COMPACT_RUN) --label "memory markdownlint" --cwd packages/memory -- uv run pymarkdown -d md013,md024 scan AGENTS.md README.md bootstrap skills

lint-planning:
	@$(COMPACT_RUN) --label "planning lint" --cwd packages/planning -- uv run ruff check .

lint-verification:
	@$(COMPACT_RUN) --label "verification lint" --cwd packages/verification -- uv run ruff check .

lint-nosync: lint-workspace lint-memory lint-planning lint-verification

lint: sync-all lint-nosync

markdownlint-memory:
	@$(COMPACT_RUN) --label "memory markdownlint" --cwd packages/memory -- uv run pymarkdown -d md013,md024 scan AGENTS.md README.md bootstrap skills

markdownlint: sync-all markdownlint-memory

typecheck-workspace:
	@$(COMPACT_RUN) --label "workspace typecheck" -- uv run ty check src

typecheck-memory:
	@$(COMPACT_RUN) --label "memory typecheck" --cwd packages/memory -- uv run ty check src

typecheck-planning:
	@$(COMPACT_RUN) --label "planning typecheck" --cwd packages/planning -- uv run ty check src

typecheck-verification:
	@$(COMPACT_RUN) --label "verification typecheck" --cwd packages/verification -- uv run ty check src

typecheck-nosync: typecheck-workspace typecheck-memory typecheck-planning typecheck-verification

typecheck: sync-all typecheck-nosync

format-workspace:
	@$(COMPACT_RUN) --label "workspace format" -- uv run ruff format src tests

format-memory:
	@$(COMPACT_RUN) --label "memory format" --cwd packages/memory -- uv run ruff format .

format-planning:
	@$(COMPACT_RUN) --label "planning format" --cwd packages/planning -- uv run ruff format .

format-verification:
	@$(COMPACT_RUN) --label "verification format" --cwd packages/verification -- uv run ruff format .

format-nosync: format-workspace format-memory format-planning format-verification

format: sync-all format-nosync

format-check-workspace:
	@$(COMPACT_RUN) --label "workspace format-check" -- uv run ruff format --check src tests

format-check-memory:
	@$(COMPACT_RUN) --label "memory format-check" --cwd packages/memory -- uv run ruff format --check .

format-check-planning:
	@$(COMPACT_RUN) --label "planning format-check" --cwd packages/planning -- uv run ruff format --check .

format-check-verification:
	@$(COMPACT_RUN) --label "verification format-check" --cwd packages/verification -- uv run ruff format --check .

format-check-nosync: format-check-workspace format-check-memory format-check-planning format-check-verification

format-check: sync-all format-check-nosync

verify-workspace:
	@$(COMPACT_RUN) --label "workspace verify" -- uv run agentic-workspace modules --format json

verify-memory:
	@$(COMPACT_RUN) --label "memory verify-payload" --cwd packages/memory -- uv run agentic-memory verify-payload --target .

verify-planning:
	@$(COMPACT_RUN) --label "planning verify-payload" --cwd packages/planning -- uv run agentic-planning verify-payload

verify-verification:
	@$(COMPACT_RUN) --label "verification report" --cwd packages/verification -- uv run agentic-verification report --target . --format json

verify-nosync: verify-workspace verify-memory verify-planning verify-verification

verify: sync-all verify-nosync

memory-freshness:
	@$(COMPACT_RUN) --label "memory doctor" -- uv run agentic-workspace doctor --target . --format json

memory-freshness-strict:
	@$(COMPACT_RUN) --label "memory report" -- uv run agentic-workspace report --target . --format json

recurring-friction-ledger:
	@$(COMPACT_RUN) --label "recurring friction ledger" -- uv run agentic-workspace report --target . --format json

planning-surfaces:
	@$(COMPACT_RUN) --label "planning surfaces" -- uv run python scripts/check/check_planning_surfaces.py

planning-surfaces-strict:
	@$(COMPACT_RUN) --label "planning surfaces strict" -- uv run python scripts/check/check_planning_surfaces.py --strict

validation-runtime-plan:
	@$(COMPACT_RUN) --label "validation runtime plan" -- uv run python scripts/check/check_validation_runtime_plan.py

validation-runtime-plan-measurement:
	@$(COMPACT_RUN) --label "validation runtime plan measurement" -- uv run python scripts/check/check_validation_runtime_plan.py --measurement-phase

structured-file-inventory:
	@$(COMPACT_RUN) --label "structured file inventory" -- uv run python scripts/check/check_structured_file_inventory.py

structured-file-inventory-changed:
	@$(COMPACT_RUN) --label "structured file inventory changed" -- uv run python scripts/check/check_structured_file_inventory.py --changed $(CHANGED_PATHS)

runtime-implementation-ownership:
	@uv run python scripts/check/check_runtime_implementation_ownership.py

security-supply-chain:
	@uv run python scripts/check/check_security_supply_chain.py --format json

package-artifact-duplicates:
	@$(COMPACT_RUN) --label "package artifact duplicates" -- uv run python scripts/check/check_package_artifact_duplicates.py

agent-aids:
	@$(COMPACT_RUN) --label "agent aid manifests" -- uv run python scripts/check/check_agent_aids.py

source-payload-operational-install:
	@$(COMPACT_RUN) --label "source-payload boundary" -- uv run python scripts/check/check_source_payload_operational_install.py

source-payload-operational-install-strict:
	@$(COMPACT_RUN) --label "source-payload boundary strict" -- uv run python scripts/check/check_source_payload_operational_install.py --strict

maintainer-surfaces: render-agent-docs schema-reference-docs planning-surfaces source-payload-operational-install verify-memory verify-planning
	@$(COMPACT_RUN) --label "maintainer surfaces" -- uv run python scripts/check/check_maintainer_surfaces.py

maintainer-surfaces-strict: render-agent-docs schema-reference-docs planning-surfaces-strict source-payload-operational-install-strict verify-memory verify-planning
	@$(COMPACT_RUN) --label "maintainer surfaces strict" -- uv run python scripts/check/check_maintainer_surfaces.py --strict

render-agent-docs:
	@$(COMPACT_RUN) --label "render agent docs" -- uv run python scripts/render_agent_docs.py

render-schema-reference:
	@$(COMPACT_RUN) --label "render schema reference" -- uv run python scripts/generate/generate_schema_reference.py
	@$(COMPACT_RUN) --label "render contract catalogues" -- uv run python scripts/generate/generate_contract_catalogues.py

render-command-packages:
	@$(COMPACT_RUN) --label "render command packages" -- uv run python scripts/generate/generate_command_packages.py

schema-reference-docs:
	@$(COMPACT_RUN) --label "schema reference docs" -- uv run python scripts/generate/generate_schema_reference.py --check --check-annotations
	@$(COMPACT_RUN) --label "contract catalogues" -- uv run python scripts/generate/generate_contract_catalogues.py --check

absolute-paths:
	@$(COMPACT_RUN) --label "absolute paths" -- uv run python scripts/check/check_no_absolute_paths.py

composed-operation-scenarios:
	@$(COMPACT_RUN) --label "composed operation scenarios" -- uv run python scripts/check/check_composed_operation_scenarios.py

generated-command-packages:
	@uv run python scripts/check/run_generated_command_package_proof.py --all

generated-command-packages-docker:
	@uv run python scripts/check/run_generated_command_package_proof.py

packed-artifact-conformance:
	@uv run python scripts/check/run_generated_command_package_proof.py --packed-conformance --artifact-dir "$(PACKED_ARTIFACT_DIR)" --receipt-out "$(PACKED_ARTIFACT_RECEIPT)" --execution-context "$(PACKED_ARTIFACT_CONTEXT)"

check-memory-nosync: test-memory lint-memory typecheck-memory verify-memory memory-freshness-strict recurring-friction-ledger

check-memory: sync-all check-memory-nosync

check-planning-nosync: test-planning lint-planning typecheck-planning maintainer-surfaces memory-freshness

check-planning: sync-all check-planning-nosync

check-verification-nosync: test-verification lint-verification typecheck-verification verify-verification
	@$(COMPACT_RUN) --label "generated command packages" -- uv run python scripts/check/check_generated_command_packages.py

check-verification: sync-all check-verification-nosync

check-nosync: test-rust-core test-nosync lint-nosync typecheck-nosync format-check-nosync verify-nosync memory-freshness-strict maintainer-surfaces validation-runtime-plan structured-file-inventory runtime-implementation-ownership security-supply-chain package-artifact-duplicates agent-aids absolute-paths composed-operation-scenarios

check: sync-all check-nosync

check-bounded-parallel:
	@$(MAKE) sync-all
	@$(MAKE) test-workspace-cli WORKSPACE_PYTEST_PARALLEL_ARGS='-n 16'
	@$(MAKE) -j 4 test-workspace-proof test-workspace-session-review test-workspace-contracts-measurement test-workspace-generated-release test-workspace-integration test-memory test-planning test-verification lint-nosync typecheck-nosync format-check-nosync verify-nosync memory-freshness-strict maintainer-surfaces validation-runtime-plan-measurement structured-file-inventory package-artifact-duplicates agent-aids absolute-paths composed-operation-scenarios WORKSPACE_PYTEST_PARALLEL_ARGS='-n 16' WORKSPACE_PROOF_PYTEST_PARALLEL_ARGS='-n 8' MEMORY_PYTEST_PARALLEL_ARGS='-n 8' PLANNING_PYTEST_PARALLEL_ARGS='' VERIFICATION_PYTEST_PARALLEL_ARGS='-n 8'

check-all: check-memory check-planning check-verification
