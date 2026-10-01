# Set up AW in an existing repository

Use this guide after installing AW in a repository that already has code,
documentation and working conventions. The goal is to connect AW to what the
repository already knows, not to analyse or import the whole project.

## Start from the current AW result

Run the normal `start` path and follow the specific request or action it returns.
The [native CLI catalogue](/docs/reference/cli-catalogue.md) lists the executable
commands.

A repository that has completed setup records a `configuration_readiness` value
in `.agentic-workspace/adoption-receipt.json`. That exact field name is part of
the stored format. AW uses it to tell whether repository configuration needs
attention.

A missing field in an older receipt does not by itself mean the repository is
broken. When AW detects a real mismatch, it should identify the affected setup
action rather than blocking unrelated read-only work.

## Inspect before writing

Use `setup` to inspect the repository before changing shared configuration. It
may point to existing project instructions, settings or useful follow-up work, but
it does not authorise bulk imports or automatic Planning/Memory writes.

Follow the specific Configuration request returned for the change. Each proposed
edit is checked against the source files it was based on before it is applied.

Shared AW settings belong in `.agentic-workspace/config.toml`. Machine-specific
settings belong in `.agentic-workspace/config.local.toml`. Verification
definitions belong in Verification's manifest, and reusable procedures belong in
skills or scoped instructions.

Setup has no separate questionnaire or hidden wizard state. After applying one
setup change, ask AW for the current result again if the next action depends on
what changed.

## Save only information that will help later work

Do not import repository material merely because it exists.

Useful candidates include:

- stable project constraints or restart instructions that agents repeatedly need;
- recurring traps or expensive-to-rediscover facts for Memory;
- genuinely unfinished work for Planning;
- reusable checking guidance for Verification;
- missing human documentation that should be fixed in the project itself.

README files, issue backlogs, generated references and design documents should
normally remain where they are. Link to them rather than copying them into AW
unless having a separate saved fact clearly reduces future rediscovery.

Low-confidence, one-off or generic observations should remain temporary.

## Verify setup work

Before saying setup follow-through is complete, be able to explain:

- which setup command or returned action was used;
- which existing project sources were inspected;
- what was saved, changed, deferred or deliberately ignored;
- where any durable information was written;
- which check supports the changed files.

Do not create placeholder rules or saved records merely to make setup look
complete.
