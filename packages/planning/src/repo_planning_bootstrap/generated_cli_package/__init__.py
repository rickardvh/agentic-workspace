"""Generated runtime-backed Python command adapter.

Source: src/agentic_workspace/contracts/command_package_ir.json
Program: agentic-planning
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
      "adapter_id": "planning.status.cli",
      "command": {
        "manifest_ref": "package:planning:cli",
        "name": "status"
      },
      "conformance_refs": [
        "planning.status.process"
      ],
      "effect_hints": {
        "destructive": false,
        "idempotent": true,
        "read_only": true,
        "requires_preflight_gate": false,
        "writes_repo_state": false
      },
      "interface": {
        "help": "Report whether planning bootstrap files are present.",
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
            "action": "store_true",
            "flags": [
              "--verbose"
            ],
            "help": "Emit broad diagnostic output for debugging or audit detail.",
            "name": "verbose"
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
        "id": "planning.status.report",
        "path": "operations/planning.status.report.json"
      },
      "projection_boundary": {
        "runtime_owned": [
          "planning bootstrap inspection",
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
          "planning.bootstrap.status.load",
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
      "adapter_id": "planning.doctor.cli",
      "command": {
        "manifest_ref": "package:planning:cli",
        "name": "doctor"
      },
      "conformance_refs": [
        "planning.doctor.process"
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
              "--verbose"
            ],
            "help": "Emit broad diagnostic output for debugging or audit detail.",
            "name": "verbose"
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
        "id": "planning.doctor.report",
        "path": "operations/planning.doctor.report.json"
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
          "planning.bootstrap.doctor.load",
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
      "adapter_id": "planning.summary.cli",
      "command": {
        "manifest_ref": "package:planning:cli",
        "name": "summary"
      },
      "conformance_refs": [
        "planning.summary.process"
      ],
      "effect_hints": {
        "destructive": false,
        "idempotent": true,
        "read_only": true,
        "requires_preflight_gate": false,
        "writes_repo_state": false
      },
      "interface": {
        "help": "Read-only summary report.",
        "name": "summary",
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
              "tiny",
              "compact",
              "full"
            ],
            "default": "tiny",
            "flags": [
              "--profile"
            ],
            "help": "Summary profile. Defaults to tiny; use compact or full for more detail.",
            "name": "profile"
          },
          {
            "flags": [
              "--task"
            ],
            "help": "Optional task text used to return a task-scoped compact summary.",
            "name": "task"
          },
          {
            "default": [],
            "flags": [
              "--changed"
            ],
            "help": "Optional changed paths used to scope compact summary output.",
            "name": "changed",
            "nargs": "*"
          },
          {
            "action": "store_true",
            "flags": [
              "--verbose"
            ],
            "help": "Emit broad diagnostic output for debugging or audit detail.",
            "name": "verbose"
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
        "id": "planning.summary.report",
        "path": "operations/planning.summary.report.json"
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
          "planning.summary.load",
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
      "adapter_id": "planning.report.cli",
      "command": {
        "manifest_ref": "package:planning:cli",
        "name": "report"
      },
      "conformance_refs": [
        "planning.report.process"
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
              "tiny",
              "full"
            ],
            "default": "tiny",
            "flags": [
              "--profile"
            ],
            "help": "Output profile. Defaults to tiny; use full for audit detail.",
            "name": "profile"
          },
          {
            "action": "store_true",
            "flags": [
              "--verbose"
            ],
            "help": "Emit broad diagnostic output for debugging or audit detail.",
            "name": "verbose"
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
        "id": "planning.report.report",
        "path": "operations/planning.report.report.json"
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
          "planning.report.load",
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
      "adapter_id": "planning.reconcile.cli",
      "command": {
        "manifest_ref": "package:planning:cli",
        "name": "reconcile"
      },
      "conformance_refs": [
        "planning.reconcile.process"
      ],
      "effect_hints": {
        "destructive": false,
        "idempotent": true,
        "read_only": true,
        "requires_preflight_gate": false,
        "writes_repo_state": false
      },
      "interface": {
        "help": "Read-only reconcile report.",
        "name": "reconcile",
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
        "id": "planning.reconcile.report",
        "path": "operations/planning.reconcile.report.json"
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
          "planning.reconcile.load",
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
  "id": "planning-bootstrap",
  "package_role": "planning-module-cli",
  "program": "agentic-planning",
  "targets": [
    {
      "entrypoints": [
        "agentic-planning"
      ],
      "generated_root": "packages/planning/src/repo_planning_bootstrap/generated_cli_package",
      "generation_status": "runtime-backed-read-only-adapter",
      "kind": "python",
      "maturity_level_ref": "runtime-backed-read-only-adapter",
      "package_name": "agentic-planning",
      "test_environment": "python-dev"
    },
    {
      "entrypoints": [
        "agentic-planning"
      ],
      "generated_root": "generated/typescript/planning-cli",
      "generation_status": "runnable-read-only-adapter",
      "kind": "typescript",
      "maturity_level_ref": "runnable-read-only-adapter",
      "package_name": "@agentic-workspace/planning-cli",
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
    "adapter_id": "planning.status.cli",
    "interface": {
      "help": "Report whether planning bootstrap files are present.",
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
          "action": "store_true",
          "flags": [
            "--verbose"
          ],
          "help": "Emit broad diagnostic output for debugging or audit detail.",
          "name": "verbose"
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
    "operation_id": "planning.status.report"
  },
  {
    "adapter_id": "planning.doctor.cli",
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
            "--verbose"
          ],
          "help": "Emit broad diagnostic output for debugging or audit detail.",
          "name": "verbose"
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
    "operation_id": "planning.doctor.report"
  },
  {
    "adapter_id": "planning.summary.cli",
    "interface": {
      "help": "Read-only summary report.",
      "name": "summary",
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
            "tiny",
            "compact",
            "full"
          ],
          "default": "tiny",
          "flags": [
            "--profile"
          ],
          "help": "Summary profile. Defaults to tiny; use compact or full for more detail.",
          "name": "profile"
        },
        {
          "flags": [
            "--task"
          ],
          "help": "Optional task text used to return a task-scoped compact summary.",
          "name": "task"
        },
        {
          "default": [],
          "flags": [
            "--changed"
          ],
          "help": "Optional changed paths used to scope compact summary output.",
          "name": "changed",
          "nargs": "*"
        },
        {
          "action": "store_true",
          "flags": [
            "--verbose"
          ],
          "help": "Emit broad diagnostic output for debugging or audit detail.",
          "name": "verbose"
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
    "operation_id": "planning.summary.report"
  },
  {
    "adapter_id": "planning.report.cli",
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
            "tiny",
            "full"
          ],
          "default": "tiny",
          "flags": [
            "--profile"
          ],
          "help": "Output profile. Defaults to tiny; use full for audit detail.",
          "name": "profile"
        },
        {
          "action": "store_true",
          "flags": [
            "--verbose"
          ],
          "help": "Emit broad diagnostic output for debugging or audit detail.",
          "name": "verbose"
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
    "operation_id": "planning.report.report"
  },
  {
    "adapter_id": "planning.reconcile.cli",
    "interface": {
      "help": "Read-only reconcile report.",
      "name": "reconcile",
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
    "operation_id": "planning.reconcile.report"
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
    parser = argparse.ArgumentParser(prog="agentic-planning", description="")
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
