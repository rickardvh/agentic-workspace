#!/usr/bin/env node
// Generated runnable adapter.
// Source: src/agentic_workspace/contracts/command_package_ir.json
// Program: agentic-memory
// Regenerate with: uv run python scripts/generate/generate_command_packages.py
// DO NOT EDIT DIRECTLY.

import { spawnSync } from 'node:child_process';
import { writeSync } from 'node:fs';

const supportedCommands = new Set(["adopt", "bootstrap-cleanup", "capture-note", "create-note", "current", "doctor", "init", "install", "list-files", "list-skills", "migrate-layout", "promotion-report", "prompt", "report", "route", "route-report", "route-review", "search", "status", "sync-memory", "uninstall", "upgrade", "verify-payload"]);
const commandDefinitions = [
  {
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
    "name": "status"
  },
  {
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
    "name": "doctor"
  },
  {
    "interface": {
      "help": "Install bootstrap files into a repository.",
      "name": "install",
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
            "--dry-run"
          ],
          "help": "Show planned changes without writing files.",
          "name": "dry_run"
        },
        {
          "action": "store_true",
          "flags": [
            "--force"
          ],
          "help": "Overwrite managed files that already exist.",
          "name": "force"
        },
        {
          "flags": [
            "--project-name"
          ],
          "help": "Value used for the <PROJECT_NAME> placeholder.",
          "name": "project_name"
        },
        {
          "flags": [
            "--project-purpose"
          ],
          "help": "Value used for the <PROJECT_PURPOSE> placeholder.",
          "name": "project_purpose"
        },
        {
          "flags": [
            "--key-repo-docs"
          ],
          "help": "Value used for the <KEY_REPO_DOCS> placeholder.",
          "name": "key_repo_docs"
        },
        {
          "flags": [
            "--key-subsystems"
          ],
          "help": "Value used for the <KEY_SUBSYSTEMS> placeholder.",
          "name": "key_subsystems"
        },
        {
          "flags": [
            "--primary-build-command"
          ],
          "help": "Value used for the <PRIMARY_BUILD_COMMAND> placeholder.",
          "name": "primary_build_command"
        },
        {
          "flags": [
            "--primary-test-command"
          ],
          "help": "Value used for the <PRIMARY_TEST_COMMAND> placeholder.",
          "name": "primary_test_command"
        },
        {
          "flags": [
            "--other-key-commands"
          ],
          "help": "Value used for the <OTHER_KEY_COMMANDS> placeholder.",
          "name": "other_key_commands"
        },
        {
          "choices": [
            "default",
            "strict-doc-ownership"
          ],
          "default": "default",
          "flags": [
            "--policy-profile"
          ],
          "help": "Installer policy preset.",
          "name": "policy_profile"
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
    "name": "install"
  },
  {
    "interface": {
      "help": "Alias for install, intended for clean bootstrap cases.",
      "name": "init",
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
            "--dry-run"
          ],
          "help": "Show planned changes without writing files.",
          "name": "dry_run"
        },
        {
          "action": "store_true",
          "flags": [
            "--force"
          ],
          "help": "Overwrite managed files that already exist.",
          "name": "force"
        },
        {
          "flags": [
            "--project-name"
          ],
          "help": "Value used for the <PROJECT_NAME> placeholder.",
          "name": "project_name"
        },
        {
          "flags": [
            "--project-purpose"
          ],
          "help": "Value used for the <PROJECT_PURPOSE> placeholder.",
          "name": "project_purpose"
        },
        {
          "flags": [
            "--key-repo-docs"
          ],
          "help": "Value used for the <KEY_REPO_DOCS> placeholder.",
          "name": "key_repo_docs"
        },
        {
          "flags": [
            "--key-subsystems"
          ],
          "help": "Value used for the <KEY_SUBSYSTEMS> placeholder.",
          "name": "key_subsystems"
        },
        {
          "flags": [
            "--primary-build-command"
          ],
          "help": "Value used for the <PRIMARY_BUILD_COMMAND> placeholder.",
          "name": "primary_build_command"
        },
        {
          "flags": [
            "--primary-test-command"
          ],
          "help": "Value used for the <PRIMARY_TEST_COMMAND> placeholder.",
          "name": "primary_test_command"
        },
        {
          "flags": [
            "--other-key-commands"
          ],
          "help": "Value used for the <OTHER_KEY_COMMANDS> placeholder.",
          "name": "other_key_commands"
        },
        {
          "choices": [
            "default",
            "strict-doc-ownership"
          ],
          "default": "default",
          "flags": [
            "--policy-profile"
          ],
          "help": "Installer policy preset.",
          "name": "policy_profile"
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
    "name": "init"
  },
  {
    "interface": {
      "help": "Add bootstrap capability to an existing repository conservatively.",
      "name": "adopt",
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
            "--dry-run"
          ],
          "help": "Show planned changes without writing files.",
          "name": "dry_run"
        },
        {
          "action": "store_true",
          "flags": [
            "--apply-local-entrypoint"
          ],
          "help": "Patch AGENTS.md with the canonical workflow pointer block when needed.",
          "name": "apply_local_entrypoint"
        },
        {
          "flags": [
            "--project-name"
          ],
          "help": "Value used for the <PROJECT_NAME> placeholder.",
          "name": "project_name"
        },
        {
          "flags": [
            "--project-purpose"
          ],
          "help": "Value used for the <PROJECT_PURPOSE> placeholder.",
          "name": "project_purpose"
        },
        {
          "flags": [
            "--key-repo-docs"
          ],
          "help": "Value used for the <KEY_REPO_DOCS> placeholder.",
          "name": "key_repo_docs"
        },
        {
          "flags": [
            "--key-subsystems"
          ],
          "help": "Value used for the <KEY_SUBSYSTEMS> placeholder.",
          "name": "key_subsystems"
        },
        {
          "flags": [
            "--primary-build-command"
          ],
          "help": "Value used for the <PRIMARY_BUILD_COMMAND> placeholder.",
          "name": "primary_build_command"
        },
        {
          "flags": [
            "--primary-test-command"
          ],
          "help": "Value used for the <PRIMARY_TEST_COMMAND> placeholder.",
          "name": "primary_test_command"
        },
        {
          "flags": [
            "--other-key-commands"
          ],
          "help": "Value used for the <OTHER_KEY_COMMANDS> placeholder.",
          "name": "other_key_commands"
        },
        {
          "choices": [
            "default",
            "strict-doc-ownership"
          ],
          "default": "default",
          "flags": [
            "--policy-profile"
          ],
          "help": "Installer policy preset.",
          "name": "policy_profile"
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
    "name": "adopt"
  },
  {
    "interface": {
      "help": "Upgrade an existing bootstrap install.",
      "name": "upgrade",
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
            "--dry-run"
          ],
          "help": "Show planned changes without writing files.",
          "name": "dry_run"
        },
        {
          "action": "store_true",
          "flags": [
            "--force"
          ],
          "help": "Overwrite managed files that already exist.",
          "name": "force"
        },
        {
          "action": "store_true",
          "flags": [
            "--apply-local-entrypoint"
          ],
          "help": "Patch AGENTS.md with the canonical workflow pointer block when needed.",
          "name": "apply_local_entrypoint"
        },
        {
          "flags": [
            "--project-name"
          ],
          "help": "Value used for the <PROJECT_NAME> placeholder.",
          "name": "project_name"
        },
        {
          "flags": [
            "--project-purpose"
          ],
          "help": "Value used for the <PROJECT_PURPOSE> placeholder.",
          "name": "project_purpose"
        },
        {
          "flags": [
            "--key-repo-docs"
          ],
          "help": "Value used for the <KEY_REPO_DOCS> placeholder.",
          "name": "key_repo_docs"
        },
        {
          "flags": [
            "--key-subsystems"
          ],
          "help": "Value used for the <KEY_SUBSYSTEMS> placeholder.",
          "name": "key_subsystems"
        },
        {
          "flags": [
            "--primary-build-command"
          ],
          "help": "Value used for the <PRIMARY_BUILD_COMMAND> placeholder.",
          "name": "primary_build_command"
        },
        {
          "flags": [
            "--primary-test-command"
          ],
          "help": "Value used for the <PRIMARY_TEST_COMMAND> placeholder.",
          "name": "primary_test_command"
        },
        {
          "flags": [
            "--other-key-commands"
          ],
          "help": "Value used for the <OTHER_KEY_COMMANDS> placeholder.",
          "name": "other_key_commands"
        },
        {
          "choices": [
            "default",
            "strict-doc-ownership"
          ],
          "default": "default",
          "flags": [
            "--policy-profile"
          ],
          "help": "Installer policy preset.",
          "name": "policy_profile"
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
    "name": "upgrade"
  },
  {
    "interface": {
      "help": "Move bootstrap-managed files from the legacy memory layout into `.agentic-workspace/memory/` conservatively.",
      "name": "migrate-layout",
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
            "--dry-run"
          ],
          "help": "Show planned changes without writing files.",
          "name": "dry_run"
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
    "name": "migrate-layout"
  },
  {
    "interface": {
      "help": "Remove bootstrap-managed files conservatively.",
      "name": "uninstall",
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
            "--dry-run"
          ],
          "help": "Show planned changes without writing files.",
          "name": "dry_run"
        },
        {
          "flags": [
            "--project-name"
          ],
          "help": "Value used for the <PROJECT_NAME> placeholder.",
          "name": "project_name"
        },
        {
          "flags": [
            "--project-purpose"
          ],
          "help": "Value used for the <PROJECT_PURPOSE> placeholder.",
          "name": "project_purpose"
        },
        {
          "flags": [
            "--key-repo-docs"
          ],
          "help": "Value used for the <KEY_REPO_DOCS> placeholder.",
          "name": "key_repo_docs"
        },
        {
          "flags": [
            "--key-subsystems"
          ],
          "help": "Value used for the <KEY_SUBSYSTEMS> placeholder.",
          "name": "key_subsystems"
        },
        {
          "flags": [
            "--primary-build-command"
          ],
          "help": "Value used for the <PRIMARY_BUILD_COMMAND> placeholder.",
          "name": "primary_build_command"
        },
        {
          "flags": [
            "--primary-test-command"
          ],
          "help": "Value used for the <PRIMARY_TEST_COMMAND> placeholder.",
          "name": "primary_test_command"
        },
        {
          "flags": [
            "--other-key-commands"
          ],
          "help": "Value used for the <OTHER_KEY_COMMANDS> placeholder.",
          "name": "other_key_commands"
        },
        {
          "choices": [
            "default",
            "strict-doc-ownership"
          ],
          "default": "default",
          "flags": [
            "--policy-profile"
          ],
          "help": "Installer policy preset.",
          "name": "policy_profile"
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
    "name": "uninstall"
  },
  {
    "interface": {
      "help": "Remove the temporary bootstrap workspace.",
      "name": "bootstrap-cleanup",
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
    "name": "bootstrap-cleanup"
  },
  {
    "interface": {
      "arguments": [
        {
          "default": "",
          "help": "Optional note slug to create when a new note is recommended.",
          "name": "slug",
          "nargs": "?"
        }
      ],
      "help": "Recommend whether durable learning should update an existing Memory note or create a new one.",
      "name": "capture-note",
      "options": [
        {
          "default": "",
          "flags": [
            "--summary"
          ],
          "help": "Short summary of the learning to preserve.",
          "name": "summary"
        },
        {
          "default": [],
          "flags": [
            "--files"
          ],
          "help": "Changed files that should influence routing.",
          "name": "files",
          "nargs": "*"
        },
        {
          "default": [],
          "flags": [
            "--surface"
          ],
          "help": "Explicit routing surfaces.",
          "name": "surface",
          "nargs": "*"
        },
        {
          "default": "",
          "flags": [
            "--existing-note"
          ],
          "help": "Existing note path to force-review first.",
          "name": "existing_note"
        },
        {
          "default": "",
          "flags": [
            "--force-new-reason"
          ],
          "help": "Reason a new note is preferred even when related notes exist.",
          "name": "force_new_reason"
        },
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
    "name": "capture-note"
  },
  {
    "interface": {
      "arguments": [
        {
          "help": "Memory note slug to create.",
          "name": "slug"
        }
      ],
      "help": "Create a minimal Memory note and matching manifest entry.",
      "name": "create-note",
      "options": [
        {
          "flags": [
            "--title"
          ],
          "help": "Memory note title. Defaults to a title derived from the slug.",
          "name": "title"
        },
        {
          "default": "domains",
          "flags": [
            "--folder"
          ],
          "help": "Memory note folder under the repo memory root.",
          "name": "folder"
        },
        {
          "default": "domain",
          "flags": [
            "--note-type"
          ],
          "help": "Memory note type recorded in the manifest.",
          "name": "note_type"
        },
        {
          "default": "",
          "flags": [
            "--summary"
          ],
          "help": "Short note summary.",
          "name": "summary"
        },
        {
          "default": [],
          "flags": [
            "--applies-to"
          ],
          "help": "Repo paths or surfaces this note applies to.",
          "name": "applies_to",
          "nargs": "*"
        },
        {
          "default": [],
          "flags": [
            "--use-when"
          ],
          "help": "Routing hints for when to use this note.",
          "name": "use_when",
          "nargs": "*"
        },
        {
          "default": [],
          "flags": [
            "--routes-from"
          ],
          "help": "Surfaces or files that should route to this note.",
          "name": "routes_from",
          "nargs": "*"
        },
        {
          "default": [],
          "flags": [
            "--stale-when"
          ],
          "help": "Conditions that make this note stale.",
          "name": "stale_when",
          "nargs": "*"
        },
        {
          "default": [],
          "flags": [
            "--evidence"
          ],
          "help": "Evidence references supporting this note.",
          "name": "evidence",
          "nargs": "*"
        },
        {
          "default": "",
          "flags": [
            "--memory-role"
          ],
          "help": "Memory role metadata.",
          "name": "memory_role"
        },
        {
          "default": "",
          "flags": [
            "--promotion-target"
          ],
          "help": "Optional durable promotion target.",
          "name": "promotion_target"
        },
        {
          "default": "",
          "flags": [
            "--promotion-trigger"
          ],
          "help": "Optional promotion trigger.",
          "name": "promotion_trigger"
        },
        {
          "default": "",
          "flags": [
            "--retention-after-promotion"
          ],
          "help": "Retention policy after promotion.",
          "name": "retention_after_promotion"
        },
        {
          "action": "store_true",
          "flags": [
            "--dry-run"
          ],
          "help": "Show planned changes without writing files.",
          "name": "dry_run"
        },
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
    "name": "create-note"
  },
  {
    "interface": {
      "help": "Inspect or check legacy current-memory migration residue.",
      "name": "current",
      "options": [],
      "subcommand_dest": "current_command",
      "subcommands": [
        {
          "help": "Show legacy current-memory notes when present.",
          "name": "show",
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
        {
          "help": "Check legacy current-memory notes for migration pressure.",
          "name": "check",
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
        }
      ],
      "subcommands_required": true
    },
    "name": "current"
  },
  {
    "interface": {
      "help": "Print a canonical agent prompt for install, adopt, populate, upgrade, or uninstall.",
      "name": "prompt",
      "options": [],
      "subcommand_dest": "prompt_command",
      "subcommands": [
        {
          "help": "Print the canonical install prompt.",
          "name": "install",
          "options": [
            {
              "flags": [
                "--target"
              ],
              "help": "Target repository path. Defaults to ./repo in prompt text.",
              "name": "target"
            }
          ]
        },
        {
          "help": "Print the canonical adoption prompt.",
          "name": "adopt",
          "options": [
            {
              "flags": [
                "--target"
              ],
              "help": "Target repository path. Defaults to ./repo in prompt text.",
              "name": "target"
            }
          ]
        },
        {
          "help": "Print the canonical populate prompt.",
          "name": "populate",
          "options": [
            {
              "flags": [
                "--target"
              ],
              "help": "Target repository path. Defaults to ./repo in prompt text.",
              "name": "target"
            }
          ]
        },
        {
          "help": "Print the canonical upgrade prompt.",
          "name": "upgrade",
          "options": [
            {
              "flags": [
                "--target"
              ],
              "help": "Target repository path. Defaults to ./repo in prompt text.",
              "name": "target"
            }
          ]
        },
        {
          "help": "Print the canonical uninstall prompt.",
          "name": "uninstall",
          "options": [
            {
              "flags": [
                "--target"
              ],
              "help": "Target repository path. Defaults to ./repo in prompt text.",
              "name": "target"
            }
          ]
        }
      ],
      "subcommands_required": true
    },
    "name": "prompt"
  },
  {
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
    "name": "report"
  },
  {
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
            "text",
            "json"
          ],
          "default": "text",
          "flags": [
            "--format"
          ],
          "help": "Output format.",
          "name": "format"
        },
        {
          "action": "store_true",
          "flags": [
            "--verbose"
          ],
          "help": "Emit full routing detail instead of the compact default.",
          "name": "verbose"
        }
      ]
    },
    "name": "route-report"
  },
  {
    "interface": {
      "help": "Suggest the smallest relevant durable note set for touched files or surfaces so the agent can read less, not more.",
      "name": "route",
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
            "--files"
          ],
          "help": "Touched file paths to route from.",
          "name": "files",
          "nargs": "*"
        },
        {
          "default": [],
          "flags": [
            "--surface"
          ],
          "help": "Explicit routing surfaces.",
          "name": "surface",
          "nargs": "*"
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
      ],
      "usage_error_hints": [
        {
          "message": "Memory task tip: 'memory route' routes touched files or explicit surfaces. For task-shaped memory consultation, run 'agentic-workspace start --task \"<task>\" --select memory_consult --format json' or 'agentic-workspace report --section memory_consult --format json'.",
          "when_argv_contains": [
            "route"
          ],
          "when_message_contains": [
            "--task"
          ]
        }
      ]
    },
    "name": "route"
  },
  {
    "interface": {
      "help": "Suggest memory updates for changed work and surface compact upstream improvement candidates.",
      "name": "sync-memory",
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
            "--files"
          ],
          "help": "Changed file paths to inspect.",
          "name": "files",
          "nargs": "*"
        },
        {
          "default": [],
          "flags": [
            "--notes"
          ],
          "help": "Explicit memory notes to review.",
          "name": "notes",
          "nargs": "*"
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
    "name": "sync-memory"
  },
  {
    "interface": {
      "help": "Review checked-in routing feedback cases against the current routing result.",
      "name": "route-review",
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
    "name": "route-review"
  },
  {
    "interface": {
      "arguments": [
        {
          "help": "Keyword or pattern to search for.",
          "name": "query"
        }
      ],
      "help": "Search for keywords across all memory notes.",
      "name": "search",
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
    "name": "search"
  },
  {
    "interface": {
      "help": "Verify the packaged bootstrap payload contract.",
      "name": "verify-payload",
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
    "name": "verify-payload"
  },
  {
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
    "name": "promotion-report"
  },
  {
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
    "name": "list-files"
  },
  {
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
    "name": "list-skills"
  }
];
const commandByName = new Map(commandDefinitions.map((definition) => [definition.name, definition.interface]));
const argv = process.argv.slice(2);
const command = argv[0];

function optionFlags(option) {
  return Array.isArray(option.flags) ? option.flags : [];
}

function interfaceOptions(iface) {
  return Array.isArray(iface.options) ? iface.options : [];
}

function interfaceArguments(iface) {
  return Array.isArray(iface.arguments) ? iface.arguments : [];
}

function interfaceSubcommands(iface) {
  return Array.isArray(iface.subcommands) ? iface.subcommands : [];
}

function isHelpToken(token) {
  return token === '--help' || token === '-h';
}

function printRootHelp() {
  console.log(`Usage: agentic-memory <command> [options]`);
  console.log(`Supported generated commands: ${Array.from(supportedCommands).join(', ')}`);
  console.log('Weak-agent routing: allowed-mutation-with-review');
  console.log('TypeScript CLI boundary: generated parser/help/validation, then canonical Python runtime handoff.');
  console.log('Recovery: use a supported generated command or route back to the canonical Python CLI.');
}

function printInterfaceHelp(path, iface) {
  const argumentNames = interfaceArguments(iface).map((argument) => argument.nargs === '?' ? `[${argument.name}]` : `<${argument.name}>`);
  const hasSubcommands = interfaceSubcommands(iface).length > 0;
  const subcommandSuffix = hasSubcommands ? ' <subcommand>' : '';
  const argumentSuffix = argumentNames.length ? ` ${argumentNames.join(' ')}` : '';
  console.log(`Usage: ${path.join(' ')}${subcommandSuffix} [options]${argumentSuffix}`);
  if (iface.help) console.log(String(iface.help));
  const options = interfaceOptions(iface);
  if (options.length) {
    console.log('Options:');
    for (const option of options) {
      const choices = Array.isArray(option.choices) ? ` choices=${option.choices.join('|')}` : '';
      const required = option.required === true ? ' required' : '';
      console.log(`  ${optionFlags(option).join(', ')}${required}${choices}  ${option.help ?? ''}`);
    }
  }
  const subcommands = interfaceSubcommands(iface);
  if (subcommands.length) {
    console.log('Subcommands:');
    for (const subcommand of subcommands) {
      console.log(`  ${subcommand.name}  ${subcommand.help ?? ''}`);
    }
  }
}

function failValidation(message) {
  console.error(`TypeScript CLI validation failed: ${message}`);
  console.error('Recovery: run agentic-memory --help and choose a supported generated command or valid option.');
  process.exit(2);
}

function validateChoice(spec, value, label) {
  if (Array.isArray(spec.choices) && !spec.choices.includes(value)) {
    failValidation(`${label} must be one of: ${spec.choices.join(', ')}`);
  }
  if (spec.type === 'integer' && !/^-?\d+$/.test(value)) {
    failValidation(`${label} must be an integer`);
  }
}

function optionByFlag(iface, flag) {
  return interfaceOptions(iface).find((option) => optionFlags(option).includes(flag));
}

function consumeOption(iface, option, tokens, index, seenOptions) {
  const optionName = option.name ?? optionFlags(option)[0];
  if (optionName) seenOptions.add(optionName);
  if (option.action === 'store_true') return index + 1;
  if (option.nargs === '*') {
    let cursor = index + 1;
    while (cursor < tokens.length && !String(tokens[cursor]).startsWith('-')) {
      validateChoice(option, String(tokens[cursor]), optionFlags(option)[0]);
      cursor += 1;
    }
    return cursor;
  }
  if (index + 1 >= tokens.length || isHelpToken(tokens[index + 1])) {
    failValidation(`${optionFlags(option)[0]} requires a value`);
  }
  const value = String(tokens[index + 1]);
  validateChoice(option, value, optionFlags(option)[0]);
  return index + 2;
}

function validateInterface(iface, tokens, path) {
  const seenOptions = new Set();
  const positional = [];
  let index = 0;
  while (index < tokens.length) {
    const token = String(tokens[index]);
    if (isHelpToken(token)) {
      printInterfaceHelp(path, iface);
      process.exit(0);
    }
    if (token.startsWith('-')) {
      const option = optionByFlag(iface, token);
      if (!option) failValidation(`unknown option ${token} for ${path.join(' ')}`);
      index = consumeOption(iface, option, tokens, index, seenOptions);
      continue;
    }
    const subcommand = interfaceSubcommands(iface).find((candidate) => candidate.name === token);
    if (subcommand) {
      validateInterface(subcommand, tokens.slice(index + 1), [...path, token]);
      return;
    }
    positional.push(token);
    index += 1;
  }
  for (const option of interfaceOptions(iface)) {
    const optionName = option.name ?? optionFlags(option)[0];
    if (option.required === true && optionName && !seenOptions.has(optionName)) {
      failValidation(`missing required option ${optionFlags(option)[0]} for ${path.join(' ')}`);
    }
  }
  const positionalSpecs = interfaceArguments(iface);
  const requiredPositionals = positionalSpecs.filter((argument) => argument.nargs !== '?' && argument.default === undefined);
  if (positional.length < requiredPositionals.length) {
    failValidation(`missing required argument for ${path.join(' ')}`);
  }
  if (positional.length > positionalSpecs.length) {
    failValidation(`unexpected argument ${positional[positionalSpecs.length]} for ${path.join(' ')}`);
  }
  positional.forEach((value, position) => validateChoice(positionalSpecs[position] ?? {}, value, positionalSpecs[position]?.name ?? 'argument'));
  if (interfaceSubcommands(iface).length && iface.subcommands_required !== false && positional.length === 0) {
    failValidation(`missing subcommand for ${path.join(' ')}`);
  }
}

if (!command || command === '--help' || command === '-h') {
  printRootHelp();
  process.exit(0);
}

if (!supportedCommands.has(command)) {
  console.error(`Unsupported generated command: ${command}`);
  console.error('Recovery: run agentic-memory --help and choose one of the supported generated commands.');
  process.exit(2);
}

validateInterface(commandByName.get(command), argv.slice(1), [command]);

const runtimeCommand = process.env.AGENTIC_WORKSPACE_RUNTIME ?? "python -c \"import sys; from repo_memory_bootstrap.cli import main; raise SystemExit(main(sys.argv[1:]))\"";

function splitRuntimeCommand(commandLine) {
  const parts = [];
  let current = '';
  let quote = null;
  for (const char of commandLine.trim()) {
    if (quote) {
      if (char === quote) quote = null;
      else current += char;
    } else if (char === '"' || char === "'") {
      quote = char;
    } else if (/\s/.test(char)) {
      if (current) {
        parts.push(current);
        current = '';
      }
    } else {
      current += char;
    }
  }
  if (quote) throw new Error('runtime command has an unterminated quote');
  if (current) parts.push(current);
  if (parts.length === 0) throw new Error('runtime command is empty');
  return parts;
}

let result;
try {
  const [runtimeExecutable, ...runtimeArgs] = splitRuntimeCommand(runtimeCommand);
  result = spawnSync(runtimeExecutable, [...runtimeArgs, ...argv], { encoding: 'utf8', maxBuffer: 16 * 1024 * 1024 });
} catch (error) {
  console.error(`Adapter runtime handoff failed: ${error.message}`);
  console.error('Recovery: verify AGENTIC_WORKSPACE_RUNTIME or run the canonical Python CLI directly.');
  process.exit(1);
}
if (result.error) {
  console.error(`Adapter runtime handoff failed: ${result.error.message}`);
  console.error('Recovery: verify AGENTIC_WORKSPACE_RUNTIME or run the canonical Python CLI directly.');
  process.exit(1);
}
if (result.stdout) writeSync(1, result.stdout);
if (result.stderr) writeSync(2, result.stderr);
process.exit(result.status ?? 1);
