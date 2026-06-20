"""Generated executable command projection.

Source: src/agentic_workspace/contracts/command_package_ir.json
Program: agentic-workspace
Operation: planning.front-door
Regenerate with: uv run python scripts/generate/generate_command_packages.py
"""

from __future__ import annotations

import argparse

from typing import Any
from collections.abc import Mapping

# DO NOT EDIT DIRECTLY.
# Command behavior changes belong in src/agentic_workspace/contracts/command_package_ir.json and the referenced operation contract.
# Regenerate with: uv run python scripts/generate/generate_command_packages.py

import contextlib
import io
import json
from ..cli import build_generated_parser


def run(args: argparse.Namespace) -> int:
    command_value = getattr(args, 'planning_command', None)
    if not command_value:
        from agentic_workspace.workspace_runtime_primitives import _planning_help_payload as help_payload_function

        payload = help_payload_function(target=getattr(args, 'target', None))
        if getattr(args, 'format', None) == 'json':
            print(json.dumps(payload, indent=2))
        else:
            from agentic_workspace.workspace_runtime_primitives import _print_planning_help as help_text_function

            help_text_function(payload)
        return 0
    local_handlers = {'decision-scaffold': ('agentic_workspace.workspace_runtime_primitives', '_run_planning_decision_adapter'), 'decision-promote': ('agentic_workspace.workspace_runtime_primitives', '_run_planning_decision_adapter')}
    local_handler = local_handlers.get(str(command_value))
    if local_handler is not None:
        module_name, function_name = local_handler
        module = __import__(module_name, fromlist=[function_name])
        return getattr(module, function_name)(args)
    argv = ['agentic-planning'] if False else []
    argv.append(str(command_value))
    for commands, attr in [(['promote-to-plan'], 'item_id'), (['lane-promote', 'lane-activate', 'lane-close', 'lane-archive'], 'lane'), (['archive-plan', 'closeout'], 'plan'), (['close-item'], 'item'), (['create-review'], 'slug')]:
        if str(command_value) in commands:
            value = getattr(args, attr, None)
            if value is not None and value != '' and value != []:
                argv.append(str(value))
    for option, attr, fallback_attr, kind in [('--id', 'id', '', 'value'), ('--title', 'title', '', 'value'), ('--source', 'source', '', 'value'), ('--artifact', 'artifact', '', 'value'), ('--target', 'target', '', 'value'), ('--plan-slug', 'plan_slug', '', 'value'), ('--scope', 'scope', '', 'value'), ('--classification', 'classification', '', 'value'), ('--route', 'route', '', 'value'), ('--current-slice', 'current_slice', '', 'value'), ('--proof', 'proof', '', 'value'), ('--residual-work', 'residual_work', '', 'value'), ('--parent-contribution', 'parent_contribution', '', 'value'), ('--parent-close-permission', 'parent_close_permission', '', 'value'), ('--next-owner', 'next_owner', '', 'value'), ('--skipped-reason', 'skipped_reason', '', 'value'), ('--expected-savings', 'expected_savings', '', 'value'), ('--actual-friction', 'actual_friction', '', 'value'), ('--proof-result', 'proof_result', '', 'value'), ('--quality-concern', 'quality_concern', '', 'value'), ('--decomposition-adjustment', 'decomposition_adjustment', '', 'value'), ('--reason', 'reason', '', 'value'), ('--issue', 'issue', '', 'value'), ('--parent-lane-closeout', 'parent_lane_closeout', '', 'value'), ('--closure-decision', 'closure_decision', '', 'value'), ('--intent-satisfied', 'intent_satisfied', '', 'value'), ('--unsolved-intent', 'unsolved_intent', '', 'value'), ('--intent-evidence', 'intent_evidence', '', 'value'), ('--closure-reason', 'closure_reason', '', 'value'), ('--closure-evidence', 'closure_evidence', '', 'value'), ('--reopen-trigger', 'reopen_trigger', '', 'value'), ('--discard-summary', 'discard_summary', '', 'value'), ('--continuation-summary', 'continuation_summary', '', 'value'), ('--claim-level', 'claim_level', '', 'value'), ('--intent-status', 'intent_status', '', 'value'), ('--residue', 'residue', '', 'value'), ('--proof-from', 'proof_from', '', 'value'), ('--residue-owner', 'residue_owner', '', 'value'), ('--what-happened', 'what_happened', '', 'value'), ('--scope-touched', 'scope_touched', '', 'value'), ('--changed-surfaces', 'changed_surfaces', '', 'value'), ('--review-summary', 'review_summary', '', 'value'), ('--outcome-summary', 'outcome_summary', '', 'value'), ('--expect-planning-revision', 'expect_planning_revision', '', 'value'), ('--activate', 'activate', '', 'flag'), ('--queue', 'queue', '', 'flag'), ('--switch-active', 'switch_active', '', 'flag'), ('--prep-only', 'prep_only', '', 'flag'), ('--overwrite', 'overwrite', '', 'flag'), ('--remove-source', 'remove_source', '', 'flag'), ('--dry-run', 'dry_run', '', 'flag'), ('--render-markdown', 'render_markdown', '', 'flag'), ('--apply-cleanup', 'apply_cleanup', '', 'flag'), ('--prepare-closeout', 'prepare_closeout', '', 'flag'), ('--retain-archive', 'retain_archive', '', 'flag'), ('--discard-archive', 'discard_archive', '', 'flag'), ('--verbose', 'verbose', '', 'flag'), ('--path', 'paths', 'path', 'repeated'), ('--format', 'format', '', 'value')]:
        value = getattr(args, attr, None)
        if (value is None or value == [] or value == '') and fallback_attr:
            value = getattr(args, fallback_attr, None)
        if kind == 'flag':
            if bool(value):
                argv.append(option)
        elif kind == 'repeated':
            if isinstance(value, str):
                value = [value]
            for item in value or []:
                argv.extend([option, str(item)])
        elif kind == 'repeated_group':
            if isinstance(value, str):
                value = [value]
            if value:
                argv.append(option)
                argv.extend(str(item) for item in value)
        elif value is not None and value != '' and value != []:
            argv.extend([option, str(value)])
    try:
        module = __import__('repo_planning_bootstrap.cli', fromlist=['main'])
        module_main = getattr(module, 'main')
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            result = module_main(argv)
        output = buffer.getvalue()
        for old, new in [('agentic-planning reconcile ', 'agentic-workspace reconcile '), ('agentic-planning summary ', 'agentic-workspace summary '), ('agentic-planning doctor ', 'agentic-workspace doctor '), ('agentic-planning ', 'agentic-workspace planning '), ('agentic-memory ', 'agentic-workspace memory ')]:
            output = output.replace(old, new)
        print(output, end='')
        return int(result or 0)
    except ImportError:
        build_generated_parser().error('The planning module must be installed to use planning subcommands.')
        return 2


def invoke(_values: Mapping[str, Any]) -> object:
    raise RuntimeError('planning.front-door' + ' has no generated operation callable')
