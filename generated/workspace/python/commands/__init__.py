"""Generated command module registry.

Source: src/agentic_workspace/contracts/command_package_ir.json
Program: agentic-workspace
Regenerate with: uv run python scripts/generate/generate_command_packages.py
"""

from __future__ import annotations

# DO NOT EDIT DIRECTLY.
# Command module changes belong in src/agentic_workspace/contracts/command_package_ir.json.
# Regenerate with: uv run python scripts/generate/generate_command_packages.py

from . import agent_guidance_delete as _command_agent_guidance_delete
from . import agent_guidance_edit as _command_agent_guidance_edit
from . import agent_guidance_merge as _command_agent_guidance_merge
from . import agent_guidance_promote as _command_agent_guidance_promote
from . import agent_guidance_retire as _command_agent_guidance_retire
from . import agent_guidance_revalidate as _command_agent_guidance_revalidate
from . import agent_guidance_split as _command_agent_guidance_split
from . import agent_guidance_supersede as _command_agent_guidance_supersede
from . import agent_guidance_suppress as _command_agent_guidance_suppress
from . import agent_guidance_weaken as _command_agent_guidance_weaken
from . import assignment_admit as _command_assignment_admit
from . import assignment_cleanup as _command_assignment_cleanup
from . import assignment_close as _command_assignment_close
from . import assignment_dispatch as _command_assignment_dispatch
from . import assignment_export as _command_assignment_export
from . import assignment_import as _command_assignment_import
from . import assignment_integrate as _command_assignment_integrate
from . import assignment_override as _command_assignment_override
from . import assignment_reassign as _command_assignment_reassign
from . import assignment_reject as _command_assignment_reject
from . import assignment_repair as _command_assignment_repair
from . import assignment_status as _command_assignment_status
from . import autopilot_run as _command_autopilot_run
from . import checkpoint_write as _command_checkpoint_write
from . import config_policy_apply as _command_config_policy_apply
from . import config_report as _command_config_report
from . import correction_event_correct_dispute as _command_correction_event_correct_dispute
from . import correction_event_identity_init as _command_correction_event_identity_init
from . import correction_event_prune_compact as _command_correction_event_prune_compact
from . import correction_event_query as _command_correction_event_query
from . import correction_event_submit as _command_correction_event_submit
from . import correction_event_withdraw_supersede as _command_correction_event_withdraw_supersede
from . import defaults_report as _command_defaults_report
from . import delegation_outcome_append as _command_delegation_outcome_append
from . import doctor_report as _command_doctor_report
from . import evaluation_authority_refresh as _command_evaluation_authority_refresh
from . import evaluation_delivery_status as _command_evaluation_delivery_status
from . import evaluation_external_adapter_receipt as _command_evaluation_external_adapter_receipt
from . import evaluation_external_delivery as _command_evaluation_external_delivery
from . import evaluation_external_host_result_import as _command_evaluation_external_host_result_import
from . import evaluation_external_request as _command_evaluation_external_request
from . import evaluation_local_delivery as _command_evaluation_local_delivery
from . import evaluation_observe as _command_evaluation_observe
from . import evaluation_prune as _command_evaluation_prune
from . import evaluation_register as _command_evaluation_register
from . import evaluation_report_preview as _command_evaluation_report_preview
from . import evaluation_retry as _command_evaluation_retry
from . import evaluation_status as _command_evaluation_status
from . import evaluation_transition as _command_evaluation_transition
from . import external_evidence_query as _command_external_evidence_query
from . import external_evidence_submit as _command_external_evidence_submit
from . import external_intent_refresh_github as _command_external_intent_refresh_github
from . import final_response_admit as _command_final_response_admit
from . import implement_context as _command_implement_context
from . import init_lifecycle as _command_init_lifecycle
from . import install_lifecycle as _command_install_lifecycle
from . import instructions_check as _command_instructions_check
from . import instructions_create as _command_instructions_create
from . import instructions_explain as _command_instructions_explain
from . import instructions_list as _command_instructions_list
from . import instructions_migrate as _command_instructions_migrate
from . import instructions_route_select as _command_instructions_route_select
from . import instructions_routes as _command_instructions_routes
from . import memory_front_door as _command_memory_front_door
from . import modules_report as _command_modules_report
from . import ownership_report as _command_ownership_report
from . import planning_front_door as _command_planning_front_door
from . import preflight_report as _command_preflight_report
from . import prompt_init as _command_prompt_init
from . import prompt_uninstall as _command_prompt_uninstall
from . import prompt_upgrade as _command_prompt_upgrade
from . import proof_report as _command_proof_report
from . import reconcile_report as _command_reconcile_report
from . import report_combined as _command_report_combined
from . import session_log_manage as _command_session_log_manage
from . import setup_guidance as _command_setup_guidance
from . import skills_report as _command_skills_report
from . import start_context as _command_start_context
from . import status_report as _command_status_report
from . import summary_report as _command_summary_report
from . import system_intent_sync as _command_system_intent_sync
from . import uninstall_lifecycle as _command_uninstall_lifecycle
from . import upgrade_lifecycle as _command_upgrade_lifecycle
from . import work_thread_carry_inspect as _command_work_thread_carry_inspect
from . import work_thread_carry_prune as _command_work_thread_carry_prune
from . import work_thread_carry_select as _command_work_thread_carry_select
from . import work_thread_prune as _command_work_thread_prune
from . import work_thread_select as _command_work_thread_select


GENERATED_COMMAND_HANDLERS = {
    'agent-guidance.delete': _command_agent_guidance_delete.run,
    'agent-guidance.edit': _command_agent_guidance_edit.run,
    'agent-guidance.merge': _command_agent_guidance_merge.run,
    'agent-guidance.promote': _command_agent_guidance_promote.run,
    'agent-guidance.retire': _command_agent_guidance_retire.run,
    'agent-guidance.revalidate': _command_agent_guidance_revalidate.run,
    'agent-guidance.split': _command_agent_guidance_split.run,
    'agent-guidance.supersede': _command_agent_guidance_supersede.run,
    'agent-guidance.suppress': _command_agent_guidance_suppress.run,
    'agent-guidance.weaken': _command_agent_guidance_weaken.run,
    'assignment.admit': _command_assignment_admit.run,
    'assignment.cleanup': _command_assignment_cleanup.run,
    'assignment.close': _command_assignment_close.run,
    'assignment.dispatch': _command_assignment_dispatch.run,
    'assignment.export': _command_assignment_export.run,
    'assignment.import': _command_assignment_import.run,
    'assignment.integrate': _command_assignment_integrate.run,
    'assignment.override': _command_assignment_override.run,
    'assignment.reassign': _command_assignment_reassign.run,
    'assignment.reject': _command_assignment_reject.run,
    'assignment.repair': _command_assignment_repair.run,
    'assignment.status': _command_assignment_status.run,
    'autopilot.run': _command_autopilot_run.run,
    'checkpoint.write': _command_checkpoint_write.run,
    'config.policy-apply': _command_config_policy_apply.run,
    'config.report': _command_config_report.run,
    'correction-event.correct-dispute': _command_correction_event_correct_dispute.run,
    'correction-event.identity-init': _command_correction_event_identity_init.run,
    'correction-event.prune-compact': _command_correction_event_prune_compact.run,
    'correction-event.query': _command_correction_event_query.run,
    'correction-event.submit': _command_correction_event_submit.run,
    'correction-event.withdraw-supersede': _command_correction_event_withdraw_supersede.run,
    'defaults.report': _command_defaults_report.run,
    'delegation-outcome.append': _command_delegation_outcome_append.run,
    'doctor.report': _command_doctor_report.run,
    'evaluation.authority-refresh': _command_evaluation_authority_refresh.run,
    'evaluation.delivery-status': _command_evaluation_delivery_status.run,
    'evaluation.external-adapter-receipt': _command_evaluation_external_adapter_receipt.run,
    'evaluation.external-delivery': _command_evaluation_external_delivery.run,
    'evaluation.external-host-result-import': _command_evaluation_external_host_result_import.run,
    'evaluation.external-request': _command_evaluation_external_request.run,
    'evaluation.local-delivery': _command_evaluation_local_delivery.run,
    'evaluation.observe': _command_evaluation_observe.run,
    'evaluation.prune': _command_evaluation_prune.run,
    'evaluation.register': _command_evaluation_register.run,
    'evaluation.report-preview': _command_evaluation_report_preview.run,
    'evaluation.retry': _command_evaluation_retry.run,
    'evaluation.status': _command_evaluation_status.run,
    'evaluation.transition': _command_evaluation_transition.run,
    'external-evidence.query': _command_external_evidence_query.run,
    'external-evidence.submit': _command_external_evidence_submit.run,
    'external-intent.refresh-github': _command_external_intent_refresh_github.run,
    'final-response.admit': _command_final_response_admit.run,
    'implement.context': _command_implement_context.run,
    'init.lifecycle': _command_init_lifecycle.run,
    'install.lifecycle': _command_install_lifecycle.run,
    'instructions.check': _command_instructions_check.run,
    'instructions.create': _command_instructions_create.run,
    'instructions.explain': _command_instructions_explain.run,
    'instructions.list': _command_instructions_list.run,
    'instructions.migrate': _command_instructions_migrate.run,
    'instructions.route-select': _command_instructions_route_select.run,
    'instructions.routes': _command_instructions_routes.run,
    'memory.front-door': _command_memory_front_door.run,
    'modules.report': _command_modules_report.run,
    'ownership.report': _command_ownership_report.run,
    'planning.front-door': _command_planning_front_door.run,
    'preflight.report': _command_preflight_report.run,
    'prompt.init': _command_prompt_init.run,
    'prompt.uninstall': _command_prompt_uninstall.run,
    'prompt.upgrade': _command_prompt_upgrade.run,
    'proof.report': _command_proof_report.run,
    'reconcile.report': _command_reconcile_report.run,
    'report.combined': _command_report_combined.run,
    'session-log.manage': _command_session_log_manage.run,
    'setup.guidance': _command_setup_guidance.run,
    'skills.report': _command_skills_report.run,
    'start.context': _command_start_context.run,
    'status.report': _command_status_report.run,
    'summary.report': _command_summary_report.run,
    'system-intent.sync': _command_system_intent_sync.run,
    'uninstall.lifecycle': _command_uninstall_lifecycle.run,
    'upgrade.lifecycle': _command_upgrade_lifecycle.run,
    'work-thread.carry-inspect': _command_work_thread_carry_inspect.run,
    'work-thread.carry-prune': _command_work_thread_carry_prune.run,
    'work-thread.carry-select': _command_work_thread_carry_select.run,
    'work-thread.prune': _command_work_thread_prune.run,
    'work-thread.select': _command_work_thread_select.run,
}
