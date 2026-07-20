"""Generated command module registry.

Source: src/agentic_workspace/contracts/command_package_ir.json
Program: agentic-workspace
Regenerate with: uv run python scripts/generate/generate_command_packages.py
"""

from __future__ import annotations

# DO NOT EDIT DIRECTLY.
# Command module changes belong in src/agentic_workspace/contracts/command_package_ir.json.
# Regenerate with: uv run python scripts/generate/generate_command_packages.py

from . import autopilot_run as _command_autopilot_run
from . import checkpoint_write as _command_checkpoint_write
from . import config_report as _command_config_report
from . import defaults_report as _command_defaults_report
from . import delegation_outcome_append as _command_delegation_outcome_append
from . import doctor_report as _command_doctor_report
from . import evaluation_observe as _command_evaluation_observe
from . import evaluation_register as _command_evaluation_register
from . import evaluation_status as _command_evaluation_status
from . import evaluation_transition as _command_evaluation_transition
from . import external_intent_refresh_github as _command_external_intent_refresh_github
from . import final_response_admit as _command_final_response_admit
from . import implement_context as _command_implement_context
from . import init_lifecycle as _command_init_lifecycle
from . import install_lifecycle as _command_install_lifecycle
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
    'autopilot.run': _command_autopilot_run.run,
    'checkpoint.write': _command_checkpoint_write.run,
    'config.report': _command_config_report.run,
    'defaults.report': _command_defaults_report.run,
    'delegation-outcome.append': _command_delegation_outcome_append.run,
    'doctor.report': _command_doctor_report.run,
    'evaluation.observe': _command_evaluation_observe.run,
    'evaluation.register': _command_evaluation_register.run,
    'evaluation.status': _command_evaluation_status.run,
    'evaluation.transition': _command_evaluation_transition.run,
    'external-intent.refresh-github': _command_external_intent_refresh_github.run,
    'final-response.admit': _command_final_response_admit.run,
    'implement.context': _command_implement_context.run,
    'init.lifecycle': _command_init_lifecycle.run,
    'install.lifecycle': _command_install_lifecycle.run,
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
