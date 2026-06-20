"""Generated executable command projection.

Source: src/agentic_workspace/contracts/command_package_ir.json
Program: agentic-workspace
Operation: memory.front-door
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
    command_value = getattr(args, 'memory_command', None)
    if not command_value:
        from agentic_workspace.workspace_runtime_primitives import _memory_help_payload as help_payload_function

        payload = help_payload_function(target=getattr(args, 'target', None))
        if getattr(args, 'format', None) == 'json':
            print(json.dumps(payload, indent=2))
        else:
            from agentic_workspace.workspace_runtime_primitives import _print_memory_help as help_text_function

            help_text_function(payload)
        return 0
    local_handlers = {}
    local_handler = local_handlers.get(str(command_value))
    if local_handler is not None:
        module_name, function_name = local_handler
        module = __import__(module_name, fromlist=[function_name])
        return getattr(module, function_name)(args)
    argv = ['agentic-memory'] if False else []
    argv.append(str(command_value))
    for commands, attr in [(['capture-note', 'create-note'], 'slug')]:
        if str(command_value) in commands:
            value = getattr(args, attr, None)
            if value is not None and value != '' and value != []:
                argv.append(str(value))
    for option, attr, fallback_attr, kind in [('--target', 'target', '', 'value'), ('--title', 'title', '', 'value'), ('--folder', 'folder', '', 'value'), ('--note-type', 'note_type', '', 'value'), ('--summary', 'summary', '', 'value'), ('--task', 'task', '', 'value'), ('--stage', 'stage', '', 'value'), ('--existing-note', 'existing_note', '', 'value'), ('--force-new-reason', 'force_new_reason', '', 'value'), ('--mode', 'mode', '', 'value'), ('--memory-role', 'memory_role', '', 'value'), ('--promotion-target', 'promotion_target', '', 'value'), ('--promotion-trigger', 'promotion_trigger', '', 'value'), ('--retention-after-promotion', 'retention_after_promotion', '', 'value'), ('--local-reason', 'local_reason', '', 'value'), ('--applies-to', 'applies_to', '', 'repeated_group'), ('--use-when', 'use_when', '', 'repeated_group'), ('--routes-from', 'routes_from', '', 'repeated_group'), ('--stale-when', 'stale_when', '', 'repeated_group'), ('--evidence', 'evidence', '', 'repeated_group'), ('--files', 'files', '', 'repeated_group'), ('--surface', 'surfaces', '', 'repeated_group'), ('--notes', 'notes', '', 'repeated_group'), ('--local', 'local', '', 'flag'), ('--dry-run', 'dry_run', '', 'flag'), ('--verbose', 'verbose', '', 'flag'), ('--format', 'format', '', 'value')]:
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
        module = __import__('repo_memory_bootstrap.cli', fromlist=['main'])
        module_main = getattr(module, 'main')
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            result = module_main(argv)
        output = buffer.getvalue()
        for old, new in [('agentic-memory ', 'agentic-workspace memory ')]:
            output = output.replace(old, new)
        print(output, end='')
        return int(result or 0)
    except ImportError:
        build_generated_parser().error('The memory module must be installed to use memory subcommands.')
        return 2


def invoke(_values: Mapping[str, Any]) -> object:
    raise RuntimeError('memory.front-door' + ' has no generated operation callable')
