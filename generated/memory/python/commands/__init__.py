"""Generated command module registry.

Source: src/agentic_workspace/contracts/command_package_ir.json
Program: agentic-memory
Regenerate with: uv run python scripts/generate/generate_command_packages.py
"""

from __future__ import annotations

# DO NOT EDIT DIRECTLY.
# Command module changes belong in src/agentic_workspace/contracts/command_package_ir.json.
# Regenerate with: uv run python scripts/generate/generate_command_packages.py

from . import memory_adopt_lifecycle as _command_memory_adopt_lifecycle
from . import memory_bootstrap_cleanup_apply as _command_memory_bootstrap_cleanup_apply
from . import memory_capture_note_report as _command_memory_capture_note_report
from . import memory_create_note_apply as _command_memory_create_note_apply
from . import memory_current_report as _command_memory_current_report
from . import memory_doctor_report as _command_memory_doctor_report
from . import memory_init_lifecycle as _command_memory_init_lifecycle
from . import memory_install_lifecycle as _command_memory_install_lifecycle
from . import memory_list_files_report as _command_memory_list_files_report
from . import memory_list_skills_report as _command_memory_list_skills_report
from . import memory_migrate_layout_lifecycle as _command_memory_migrate_layout_lifecycle
from . import memory_promotion_report_report as _command_memory_promotion_report_report
from . import memory_prompt_render as _command_memory_prompt_render
from . import memory_report_report as _command_memory_report_report
from . import memory_route_report_report as _command_memory_route_report_report
from . import memory_route_review_report as _command_memory_route_review_report
from . import memory_route_report as _command_memory_route_report
from . import memory_search_report as _command_memory_search_report
from . import memory_status_report as _command_memory_status_report
from . import memory_sync_memory_report as _command_memory_sync_memory_report
from . import memory_uninstall_lifecycle as _command_memory_uninstall_lifecycle
from . import memory_upgrade_lifecycle as _command_memory_upgrade_lifecycle
from . import memory_verify_payload_report as _command_memory_verify_payload_report


GENERATED_COMMAND_HANDLERS = {
    'memory.adopt.lifecycle': _command_memory_adopt_lifecycle.run,
    'memory.bootstrap-cleanup.apply': _command_memory_bootstrap_cleanup_apply.run,
    'memory.capture-note.report': _command_memory_capture_note_report.run,
    'memory.create-note.apply': _command_memory_create_note_apply.run,
    'memory.current.report': _command_memory_current_report.run,
    'memory.doctor.report': _command_memory_doctor_report.run,
    'memory.init.lifecycle': _command_memory_init_lifecycle.run,
    'memory.install.lifecycle': _command_memory_install_lifecycle.run,
    'memory.list-files.report': _command_memory_list_files_report.run,
    'memory.list-skills.report': _command_memory_list_skills_report.run,
    'memory.migrate-layout.lifecycle': _command_memory_migrate_layout_lifecycle.run,
    'memory.promotion-report.report': _command_memory_promotion_report_report.run,
    'memory.prompt.render': _command_memory_prompt_render.run,
    'memory.report.report': _command_memory_report_report.run,
    'memory.route-report.report': _command_memory_route_report_report.run,
    'memory.route-review.report': _command_memory_route_review_report.run,
    'memory.route.report': _command_memory_route_report.run,
    'memory.search.report': _command_memory_search_report.run,
    'memory.status.report': _command_memory_status_report.run,
    'memory.sync-memory.report': _command_memory_sync_memory_report.run,
    'memory.uninstall.lifecycle': _command_memory_uninstall_lifecycle.run,
    'memory.upgrade.lifecycle': _command_memory_upgrade_lifecycle.run,
    'memory.verify-payload.report': _command_memory_verify_payload_report.run,
}
