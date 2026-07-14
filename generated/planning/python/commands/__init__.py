"""Generated command module registry.

Source: src/agentic_workspace/contracts/command_package_ir.json
Program: agentic-planning
Regenerate with: uv run python scripts/generate/generate_command_packages.py
"""

from __future__ import annotations

# DO NOT EDIT DIRECTLY.
# Command module changes belong in src/agentic_workspace/contracts/command_package_ir.json.
# Regenerate with: uv run python scripts/generate/generate_command_packages.py

from . import planning_adopt_lifecycle as _command_planning_adopt_lifecycle
from . import planning_archive_plan_lifecycle as _command_planning_archive_plan_lifecycle
from . import planning_close_item_lifecycle as _command_planning_close_item_lifecycle
from . import planning_closeout_lifecycle as _command_planning_closeout_lifecycle
from . import planning_create_review_lifecycle as _command_planning_create_review_lifecycle
from . import planning_decomposition_create_lifecycle as _command_planning_decomposition_create_lifecycle
from . import planning_delegation_decision_lifecycle as _command_planning_delegation_decision_lifecycle
from . import planning_doctor_report as _command_planning_doctor_report
from . import planning_handoff_report as _command_planning_handoff_report
from . import planning_init_lifecycle as _command_planning_init_lifecycle
from . import planning_install_lifecycle as _command_planning_install_lifecycle
from . import planning_intake_artifact_lifecycle as _command_planning_intake_artifact_lifecycle
from . import planning_lane_activate_lifecycle as _command_planning_lane_activate_lifecycle
from . import planning_lane_archive_lifecycle as _command_planning_lane_archive_lifecycle
from . import planning_lane_close_lifecycle as _command_planning_lane_close_lifecycle
from . import planning_lane_create_lifecycle as _command_planning_lane_create_lifecycle
from . import planning_lane_promote_lifecycle as _command_planning_lane_promote_lifecycle
from . import planning_list_files_report as _command_planning_list_files_report
from . import planning_new_plan_lifecycle as _command_planning_new_plan_lifecycle
from . import planning_owner_select_lifecycle as _command_planning_owner_select_lifecycle
from . import planning_promote_to_plan_lifecycle as _command_planning_promote_to_plan_lifecycle
from . import planning_prompt_render as _command_planning_prompt_render
from . import planning_reconcile_report as _command_planning_reconcile_report
from . import planning_report_report as _command_planning_report_report
from . import planning_status_report as _command_planning_status_report
from . import planning_summary_report as _command_planning_summary_report
from . import planning_uninstall_lifecycle as _command_planning_uninstall_lifecycle
from . import planning_upgrade_lifecycle as _command_planning_upgrade_lifecycle
from . import planning_verify_payload_report as _command_planning_verify_payload_report


GENERATED_COMMAND_HANDLERS = {
    'planning.adopt.lifecycle': _command_planning_adopt_lifecycle.run,
    'planning.archive-plan.lifecycle': _command_planning_archive_plan_lifecycle.run,
    'planning.close-item.lifecycle': _command_planning_close_item_lifecycle.run,
    'planning.closeout.lifecycle': _command_planning_closeout_lifecycle.run,
    'planning.create-review.lifecycle': _command_planning_create_review_lifecycle.run,
    'planning.decomposition-create.lifecycle': _command_planning_decomposition_create_lifecycle.run,
    'planning.delegation-decision.lifecycle': _command_planning_delegation_decision_lifecycle.run,
    'planning.doctor.report': _command_planning_doctor_report.run,
    'planning.handoff.report': _command_planning_handoff_report.run,
    'planning.init.lifecycle': _command_planning_init_lifecycle.run,
    'planning.install.lifecycle': _command_planning_install_lifecycle.run,
    'planning.intake-artifact.lifecycle': _command_planning_intake_artifact_lifecycle.run,
    'planning.lane-activate.lifecycle': _command_planning_lane_activate_lifecycle.run,
    'planning.lane-archive.lifecycle': _command_planning_lane_archive_lifecycle.run,
    'planning.lane-close.lifecycle': _command_planning_lane_close_lifecycle.run,
    'planning.lane-create.lifecycle': _command_planning_lane_create_lifecycle.run,
    'planning.lane-promote.lifecycle': _command_planning_lane_promote_lifecycle.run,
    'planning.list-files.report': _command_planning_list_files_report.run,
    'planning.new-plan.lifecycle': _command_planning_new_plan_lifecycle.run,
    'planning.owner-select.lifecycle': _command_planning_owner_select_lifecycle.run,
    'planning.promote-to-plan.lifecycle': _command_planning_promote_to_plan_lifecycle.run,
    'planning.prompt.render': _command_planning_prompt_render.run,
    'planning.reconcile.report': _command_planning_reconcile_report.run,
    'planning.report.report': _command_planning_report_report.run,
    'planning.status.report': _command_planning_status_report.run,
    'planning.summary.report': _command_planning_summary_report.run,
    'planning.uninstall.lifecycle': _command_planning_uninstall_lifecycle.run,
    'planning.upgrade.lifecycle': _command_planning_upgrade_lifecycle.run,
    'planning.verify-payload.report': _command_planning_verify_payload_report.run,
}
