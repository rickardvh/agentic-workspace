# Installing Agentic Workspace

Use this when a human links an agent to this repository and asks it to install Agentic Workspace in another host repo.

The repository link is documentation and package source. Do not clone this repository into a temporary folder just to copy files into the host repo.

## Target

The target repo is the repository where the user wants Agentic Workspace installed.

Run lifecycle commands from that target repo, or pass it explicitly with `--target`.

## Preferred Path

Use an installed `agentic-workspace` CLI from the target repo's environment when available.

For a support-bearing public install, choose a versioned GitHub release and download its
`distribution-install-readiness.json`. The receipt contains the canonical copyable
`uv tool install` command for the exact `agentic-workspace` wheel URL and SHA-256 digest.
Run that command unchanged; it resolves the three coordinated module wheels from the
same release with hashes embedded in root-wheel metadata. Registry resolution and
mutable branch URLs are not supported installation channels.

The same release includes `redistributable-package-readiness.json`, which proves that
the coordinated wheels, sdists, and npm tarballs carry the owner-approved MIT and
project metadata. The npm tarballs are exact GitHub release assets; the
`@agentic-workspace/*-cli` names are intentionally unpublished and must not be used in
an `npm install` registry command.

```bash
agentic-workspace defaults --section module_selection --format json
agentic-workspace init --target . --modules memory
```

Ordinary bootstrap writes only necessary checked-in surfaces: repo-owned config/startup, a compact adoption receipt, and the smallest selected module state anchors. Generic package docs, templates, schemas, bundled skills, payload provenance, and upgrade-source provenance stay package-owned and are read from the installed package, dev dependency, editable install, or source checkout at runtime. Use `--mirror-payload` only when the host repo explicitly wants the full bundled payload checked in.

Choose the smallest module set that fits:

- `memory`: durable repo knowledge and anti-rediscovery context.
- `planning`: active work continuity, proof expectations, and handoff state.
- `verification`: reusable evidence protocols, proof-route hints, and known gaps.
- `planning,memory`: both Planning and Memory, only when both are explicitly desired.

## If The CLI Is Missing

Install `agentic-workspace` with the exact command in the selected release's
`distribution-install-readiness.json`, then rerun the same lifecycle command.

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

If ordinary bootstrap needs a finishing brief, it is written under `.agentic-workspace/local/scratch/` and should not be checked in. Payload mirror mode may still write `.agentic-workspace/bootstrap-handoff.md` or `.agentic-workspace/bootstrap-handoff.json`; treat those as bounded finishing briefs before normal repo work resumes.
