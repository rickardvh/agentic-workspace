"""Generated runtime-backed Python command adapter.

Source: src/agentic_workspace/contracts/command_package_ir.json
Program: agentic-memory
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
              "tiny",
              "full"
            ],
            "default": "tiny",
            "flags": [
              "--profile"
            ],
            "help": "Output profile. Defaults to tiny; use full for action detail.",
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
              "tiny",
              "full"
            ],
            "default": "tiny",
            "flags": [
              "--profile"
            ],
            "help": "Output profile. Defaults to tiny; use full for action detail.",
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
              "tiny",
              "full"
            ],
            "default": "tiny",
            "flags": [
              "--profile"
            ],
            "help": "Output profile. Defaults to tiny; use full for report detail.",
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
    },
    {
      "adapter_id": "memory.route-report.cli",
      "command": {
        "manifest_ref": "package:memory:cli",
        "name": "route-report"
      },
      "conformance_refs": [
        "memory.route-report.process"
      ],
      "effect_hints": {
        "destructive": false,
        "idempotent": true,
        "read_only": true,
        "requires_preflight_gate": false,
        "writes_repo_state": false
      },
      "interface": {
        "help": "Show a compact aggregate routing snapshot derived from checked-in feedback cases and fixtures.",
        "name": "route-report",
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
            "help": "Output profile. Defaults to tiny; use full for fixture detail.",
            "name": "profile"
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
        "id": "memory.route-report.report",
        "path": "operations/memory.route-report.report.json"
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
          "memory.route_report.load",
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
      "adapter_id": "memory.promotion-report.cli",
      "command": {
        "manifest_ref": "package:memory:cli",
        "name": "promotion-report"
      },
      "conformance_refs": [
        "memory.promotion-report.process"
      ],
      "effect_hints": {
        "destructive": false,
        "idempotent": true,
        "read_only": true,
        "requires_preflight_gate": false,
        "writes_repo_state": false
      },
      "interface": {
        "help": "Suggest memory notes that should be promoted into canonical docs or considered for elimination through skills, scripts, tests, or refactors.",
        "name": "promotion-report",
        "options": [
          {
            "flags": [
              "--target"
            ],
            "help": "Target repository path. Defaults to the current directory.",
            "name": "target"
          },
          {
            "default": [],
            "flags": [
              "--notes"
            ],
            "help": "Explicit memory notes to inspect.",
            "name": "notes",
            "nargs": "*"
          },
          {
            "choices": [
              "all",
              "remediation"
            ],
            "default": "all",
            "flags": [
              "--mode"
            ],
            "help": "Report all candidates or only medium/high-confidence remediation candidates.",
            "name": "mode"
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
        "id": "memory.promotion-report.report",
        "path": "operations/memory.promotion-report.report.json"
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
          "memory.promotion_report.load",
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
      "adapter_id": "memory.list-files.cli",
      "command": {
        "manifest_ref": "package:memory:cli",
        "name": "list-files"
      },
      "conformance_refs": [
        "memory.list-files.process"
      ],
      "effect_hints": {
        "destructive": false,
        "idempotent": true,
        "read_only": true,
        "requires_preflight_gate": false,
        "writes_repo_state": false
      },
      "interface": {
        "help": "Preview packaged bootstrap files.",
        "name": "list-files",
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
        "id": "memory.list-files.report",
        "path": "operations/memory.list-files.report.json"
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
          "memory.bootstrap.files.list",
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
      "adapter_id": "memory.list-skills.cli",
      "command": {
        "manifest_ref": "package:memory:cli",
        "name": "list-skills"
      },
      "conformance_refs": [
        "memory.list-skills.process"
      ],
      "effect_hints": {
        "destructive": false,
        "idempotent": true,
        "read_only": true,
        "requires_preflight_gate": false,
        "writes_repo_state": false
      },
      "interface": {
        "help": "List bundled bootstrap-lifecycle skills.",
        "name": "list-skills",
        "options": [
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
        "id": "memory.list-skills.report",
        "path": "operations/memory.list-skills.report.json"
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
          "memory.bootstrap.skills.list",
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
  "program": "agentic-memory",
  "targets": [
    {
      "entrypoints": [
        "agentic-memory"
      ],
      "generated_root": "packages/memory/src/repo_memory_bootstrap/generated_cli_package",
      "generation_status": "runtime-backed-read-only-adapter",
      "kind": "python",
      "maturity_level_ref": "runtime-backed-read-only-adapter",
      "package_name": "agentic-memory",
      "test_environment": "python-dev"
    },
    {
      "entrypoints": [
        "agentic-memory"
      ],
      "generated_root": "generated/typescript/memory-cli",
      "generation_status": "runnable-read-only-adapter",
      "kind": "typescript",
      "maturity_level_ref": "runnable-read-only-adapter",
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
            "tiny",
            "full"
          ],
          "default": "tiny",
          "flags": [
            "--profile"
          ],
          "help": "Output profile. Defaults to tiny; use full for action detail.",
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
            "tiny",
            "full"
          ],
          "default": "tiny",
          "flags": [
            "--profile"
          ],
          "help": "Output profile. Defaults to tiny; use full for action detail.",
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
            "tiny",
            "full"
          ],
          "default": "tiny",
          "flags": [
            "--profile"
          ],
          "help": "Output profile. Defaults to tiny; use full for report detail.",
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
    "operation_id": "memory.report.report"
  },
  {
    "adapter_id": "memory.route-report.cli",
    "interface": {
      "help": "Show a compact aggregate routing snapshot derived from checked-in feedback cases and fixtures.",
      "name": "route-report",
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
          "help": "Output profile. Defaults to tiny; use full for fixture detail.",
          "name": "profile"
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
    "operation_id": "memory.route-report.report"
  },
  {
    "adapter_id": "memory.promotion-report.cli",
    "interface": {
      "help": "Suggest memory notes that should be promoted into canonical docs or considered for elimination through skills, scripts, tests, or refactors.",
      "name": "promotion-report",
      "options": [
        {
          "flags": [
            "--target"
          ],
          "help": "Target repository path. Defaults to the current directory.",
          "name": "target"
        },
        {
          "default": [],
          "flags": [
            "--notes"
          ],
          "help": "Explicit memory notes to inspect.",
          "name": "notes",
          "nargs": "*"
        },
        {
          "choices": [
            "all",
            "remediation"
          ],
          "default": "all",
          "flags": [
            "--mode"
          ],
          "help": "Report all candidates or only medium/high-confidence remediation candidates.",
          "name": "mode"
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
    "operation_id": "memory.promotion-report.report"
  },
  {
    "adapter_id": "memory.list-files.cli",
    "interface": {
      "help": "Preview packaged bootstrap files.",
      "name": "list-files",
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
    "operation_id": "memory.list-files.report"
  },
  {
    "adapter_id": "memory.list-skills.cli",
    "interface": {
      "help": "List bundled bootstrap-lifecycle skills.",
      "name": "list-skills",
      "options": [
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
    "operation_id": "memory.list-skills.report"
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
    parser = argparse.ArgumentParser(prog="agentic-memory", description="")
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
