"""Generated runtime-backed Python command adapter.

Source: src/agentic_workspace/contracts/command_package_ir.json
Program: agentic-memory-bootstrap
Regenerate with: uv run python scripts/generate/generate_command_packages.py
"""

from __future__ import annotations

import argparse
import json
from collections.abc import Callable
from typing import Any

# DO NOT EDIT DIRECTLY.
# Command/interface changes belong in src/agentic_workspace/contracts/command_package_ir.json.
# Runtime behavior changes belong in hand-written operation/primitive implementation code.
# Regenerate with: uv run python scripts/generate/generate_command_packages.py
GENERATED_COMMAND_PACKAGE: dict[str, Any] = json.loads(
    r"""
{
  "commands": [
    {
      "adapter_id": "memory.status.cli",
      "command": {
        "manifest_ref": "package:memory:cli",
        "name": "status"
      },
      "conformance_refs": [
        "memory.status.process"
      ],
      "effect_hints": {
        "destructive": false,
        "idempotent": true,
        "read_only": true,
        "requires_preflight_gate": false,
        "writes_repo_state": false
      },
      "interface": {
        "help": "Report whether memory bootstrap files are present.",
        "name": "status",
        "options": [
          {
            "flags": [
              "--target"
            ],
            "help": "Target repository path. Defaults to the current directory.",
            "name": "target"
          },
          {
            "choices": [
              "text",
              "json"
            ],
            "default": "text",
            "flags": [
              "--format"
            ],
            "help": "Output format.",
            "name": "format"
          }
        ]
      },
      "operation_ref": {
        "id": "memory.status.report",
        "path": "operations/memory.status.report.json"
      },
      "projection_boundary": {
        "runtime_owned": [
          "memory bootstrap inspection",
          "module result assembly",
          "output emission"
        ],
        "target_specific": [
          "parser library",
          "package entrypoint wiring",
          "help text layout",
          "test container image"
        ],
        "universal": [
          "command identity",
          "operation reference",
          "runtime primitive reference",
          "effect hints",
          "conformance refs"
        ]
      },
      "runtime_binding": {
        "kind": "operation-primitive-sequence",
        "primitive_refs": [
          "memory.bootstrap.status.load",
          "output.emit"
        ]
      },
      "schemas": {
        "input": [],
        "output": []
      },
      "status": "generated"
    },
    {
      "adapter_id": "memory.doctor.cli",
      "command": {
        "manifest_ref": "package:memory:cli",
        "name": "doctor"
      },
      "conformance_refs": [
        "memory.doctor.process"
      ],
      "effect_hints": {
        "destructive": false,
        "idempotent": true,
        "read_only": true,
        "requires_preflight_gate": false,
        "writes_repo_state": false
      },
      "interface": {
        "help": "Read-only doctor report.",
        "name": "doctor",
        "options": [
          {
            "flags": [
              "--target"
            ],
            "help": "Target repository path. Defaults to the current directory.",
            "name": "target"
          },
          {
            "action": "store_true",
            "flags": [
              "--strict-doc-ownership"
            ],
            "help": "Enforce doc-ownership audits even when the repo manifest has not enabled them.",
            "name": "strict_doc_ownership"
          },
          {
            "choices": [
              "text",
              "json"
            ],
            "default": "text",
            "flags": [
              "--format"
            ],
            "help": "Output format.",
            "name": "format"
          }
        ]
      },
      "operation_ref": {
        "id": "memory.doctor.report",
        "path": "operations/memory.doctor.report.json"
      },
      "projection_boundary": {
        "runtime_owned": [
          "package-local primitive implementation",
          "payload assembly",
          "output emission"
        ],
        "target_specific": [
          "parser library",
          "package entrypoint wiring",
          "help text layout",
          "test container image"
        ],
        "universal": [
          "command identity",
          "operation reference",
          "runtime primitive reference",
          "effect hints",
          "conformance refs"
        ]
      },
      "runtime_binding": {
        "kind": "operation-primitive-sequence",
        "primitive_refs": [
          "memory.bootstrap.doctor.load",
          "output.emit"
        ]
      },
      "schemas": {
        "input": [],
        "output": []
      },
      "status": "generated"
    },
    {
      "adapter_id": "memory.report.cli",
      "command": {
        "manifest_ref": "package:memory:cli",
        "name": "report"
      },
      "conformance_refs": [
        "memory.report.process"
      ],
      "effect_hints": {
        "destructive": false,
        "idempotent": true,
        "read_only": true,
        "requires_preflight_gate": false,
        "writes_repo_state": false
      },
      "interface": {
        "help": "Read-only report report.",
        "name": "report",
        "options": [
          {
            "flags": [
              "--target"
            ],
            "help": "Target repository path. Defaults to the current directory.",
            "name": "target"
          },
          {
            "choices": [
              "text",
              "json"
            ],
            "default": "text",
            "flags": [
              "--format"
            ],
            "help": "Output format.",
            "name": "format"
          }
        ]
      },
      "operation_ref": {
        "id": "memory.report.report",
        "path": "operations/memory.report.report.json"
      },
      "projection_boundary": {
        "runtime_owned": [
          "package-local primitive implementation",
          "payload assembly",
          "output emission"
        ],
        "target_specific": [
          "parser library",
          "package entrypoint wiring",
          "help text layout",
          "test container image"
        ],
        "universal": [
          "command identity",
          "operation reference",
          "runtime primitive reference",
          "effect hints",
          "conformance refs"
        ]
      },
      "runtime_binding": {
        "kind": "operation-primitive-sequence",
        "primitive_refs": [
          "memory.report.load",
          "output.emit"
        ]
      },
      "schemas": {
        "input": [],
        "output": []
      },
      "status": "generated"
    }
  ],
  "id": "memory-bootstrap",
  "package_role": "memory-module-cli",
  "program": "agentic-memory-bootstrap",
  "targets": [
    {
      "entrypoints": [
        "agentic-memory-bootstrap"
      ],
      "generated_root": "packages/memory/src/repo_memory_bootstrap/generated_cli_package",
      "generation_status": "runtime-backed-read-only-adapter",
      "kind": "python",
      "maturity_level_ref": "runtime-backed-read-only-adapter",
      "package_name": "agentic-memory-bootstrap",
      "test_environment": "python-dev"
    },
    {
      "entrypoints": [
        "agentic-memory-bootstrap"
      ],
      "generated_root": "generated/typescript/memory-cli",
      "generation_status": "proof-fixture",
      "kind": "typescript",
      "maturity_level_ref": "metadata-proof-fixture",
      "package_name": "@agentic-workspace/memory-cli",
      "test_environment": "docker"
    }
  ]
}
"""
)

_GENERATED_ADAPTER_COMMANDS: list[dict[str, Any]] = json.loads(
    r"""
[
  {
    "adapter_id": "memory.status.cli",
    "interface": {
      "help": "Report whether memory bootstrap files are present.",
      "name": "status",
      "options": [
        {
          "flags": [
            "--target"
          ],
          "help": "Target repository path. Defaults to the current directory.",
          "name": "target"
        },
        {
          "choices": [
            "text",
            "json"
          ],
          "default": "text",
          "flags": [
            "--format"
          ],
          "help": "Output format.",
          "name": "format"
        }
      ]
    },
    "operation_id": "memory.status.report"
  },
  {
    "adapter_id": "memory.doctor.cli",
    "interface": {
      "help": "Read-only doctor report.",
      "name": "doctor",
      "options": [
        {
          "flags": [
            "--target"
          ],
          "help": "Target repository path. Defaults to the current directory.",
          "name": "target"
        },
        {
          "action": "store_true",
          "flags": [
            "--strict-doc-ownership"
          ],
          "help": "Enforce doc-ownership audits even when the repo manifest has not enabled them.",
          "name": "strict_doc_ownership"
        },
        {
          "choices": [
            "text",
            "json"
          ],
          "default": "text",
          "flags": [
            "--format"
          ],
          "help": "Output format.",
          "name": "format"
        }
      ]
    },
    "operation_id": "memory.doctor.report"
  },
  {
    "adapter_id": "memory.report.cli",
    "interface": {
      "help": "Read-only report report.",
      "name": "report",
      "options": [
        {
          "flags": [
            "--target"
          ],
          "help": "Target repository path. Defaults to the current directory.",
          "name": "target"
        },
        {
          "choices": [
            "text",
            "json"
          ],
          "default": "text",
          "flags": [
            "--format"
          ],
          "help": "Output format.",
          "name": "format"
        }
      ]
    },
    "operation_id": "memory.report.report"
  }
]
"""
)
_GENERATED_COMMANDS_BY_NAME: dict[str, dict[str, Any]] = {
    str(command["interface"]["name"]): command for command in _GENERATED_ADAPTER_COMMANDS
}

RuntimeHandler = Callable[[str, argparse.Namespace], int]


def generated_command_names() -> tuple[str, ...]:
    return tuple(sorted(_GENERATED_COMMANDS_BY_NAME))


def supports_generated_command(argv: list[str] | tuple[str, ...]) -> bool:
    return bool(argv) and str(argv[0]) in _GENERATED_COMMANDS_BY_NAME


def _option_type(option_spec: dict[str, Any]) -> Any:
    if option_spec.get("type") == "integer":
        return int
    return None


def _add_option(parser: argparse.ArgumentParser, option_spec: dict[str, Any]) -> None:
    kwargs: dict[str, Any] = {}
    action = option_spec.get("action")
    if isinstance(action, str):
        kwargs["action"] = action
    if "choices" in option_spec:
        kwargs["choices"] = tuple(option_spec["choices"])
    if "default" in option_spec:
        kwargs["default"] = option_spec["default"]
    if "nargs" in option_spec:
        kwargs["nargs"] = option_spec["nargs"]
    option_type = _option_type(option_spec)
    if option_type is not None:
        kwargs["type"] = option_type
    if option_spec.get("required") is True:
        kwargs["required"] = True
    help_text = option_spec.get("help")
    if isinstance(help_text, str):
        kwargs["help"] = help_text
    parser.add_argument(*option_spec["flags"], **kwargs)


def build_generated_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="agentic-memory-bootstrap", description="")
    subparsers = parser.add_subparsers(dest="command", required=True)
    for command in _GENERATED_ADAPTER_COMMANDS:
        interface = command["interface"]
        command_parser = subparsers.add_parser(
            str(interface["name"]),
            help=str(interface["help"]),
            description=str(interface["help"]),
        )
        command_parser.set_defaults(_generated_operation_id=command["operation_id"])
        for option in interface.get("options", []):
            _add_option(command_parser, option)
    return parser


def run_generated_command(argv: list[str] | tuple[str, ...], runtime_handler: RuntimeHandler) -> int:
    parser = build_generated_parser()
    args = parser.parse_args(list(argv))
    operation_id = str(getattr(args, "_generated_operation_id"))
    return runtime_handler(operation_id, args)
