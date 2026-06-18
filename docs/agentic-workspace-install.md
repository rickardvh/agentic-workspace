# Installing Agentic Workspace

Use this when a human links an agent to this repository and asks it to install Agentic Workspace in another host repo.

The repository link is documentation and package source. Do not clone this repository into a temporary folder just to copy files into the host repo.

## Target

The target repo is the repository where the user wants Agentic Workspace installed.

Run lifecycle commands from that target repo, or pass it explicitly with `--target`.

## Preferred Path

Use an installed `agentic-workspace` CLI from the target repo's environment when available.

```bash
agentic-workspace defaults --section module_selection --format json
agentic-workspace init --target . --modules memory
```

Choose the smallest module set that fits:

- `memory`: durable repo knowledge and anti-rediscovery context.
- `planning`: active work continuity, proof expectations, and handoff state.
- `verification`: reusable evidence protocols, proof-route hints, and known gaps.
- `planning,memory`: both Planning and Memory, only when both are explicitly desired.

## If The CLI Is Missing

Install `agentic-workspace` into the target repo or its tool environment, then rerun the same lifecycle command.

Prefer the target repo's dependency/tooling convention. For example, a repo may use a dev dependency, a project tool environment, or a user-local tool install.

Use `uvx` or `pipx run` only as an explicit temporary/debug fallback. They are not the default host-repo install path because follow-on work expects repeated stable CLI calls.

## Rules

- Do not clone `https://github.com/rickardvh/agentic-workspace` into a temporary folder as the bootstrap strategy.
- Do not hand-copy package files into the host repo.
- Do not use package-specific CLIs unless the root `agentic-workspace` lifecycle path is unavailable or the user asked for package-local debugging.
- After install, use the target repo's configured agent instructions file, normally `AGENTS.md`, for ordinary work.

## Follow-Up

After installation, run:

```bash
agentic-workspace config --target . --format json
agentic-workspace doctor --target . --format json
```

If bootstrap writes `.agentic-workspace/bootstrap-handoff.md` or `.agentic-workspace/bootstrap-handoff.json`, treat that as the bounded finishing brief before normal repo work resumes.
