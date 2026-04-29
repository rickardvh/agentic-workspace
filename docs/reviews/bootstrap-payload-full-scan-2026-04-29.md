# Bootstrap Payload Full Scan

Date: 2026-04-29

## Scope

Scanned the package bootstrap payload sources and built package artifacts for:

- `packages/memory/bootstrap/`
- `packages/planning/bootstrap/`
- `packages/memory/skills/`
- `packages/planning/skills/`
- built memory wheel and sdist
- built planning wheel and sdist

Commands used:

- `uv run agentic-workspace start --format json`
- `uv run python scripts/check/check_source_payload_operational_install.py --format json --strict`
- `uv build packages/memory --wheel --sdist -o .agentic-workspace/local/scratch/payload-scan`
- `uv build packages/planning --wheel --sdist -o .agentic-workspace/local/scratch/payload-scan`
- raw filesystem classification of bootstrap and skill source trees
- built artifact classification of `_payload`, `bootstrap`, `_skills`, and `skills` entries

Skills are in scope because they are intentionally shipped declarative agent guidance. Their presence is not a finding. The hard boundary is executable code or runtime-specific assumptions in checked-in payload files.

## Hard Boundary Result

No hard payload violations were found.

- No executable-code files were present in memory or planning bootstrap payloads.
- No extensionless shebang files were present in memory or planning bootstrap payloads.
- No `scripts/`, `tools/`, or `optional/` helper directories were present in bootstrap payloads.
- No legacy `packages/memory/memory/` tree was present.
- No active planning state such as `state.toml` was present in planning bootstrap payload.
- No repo-specific memory runbook/note payloads were present in memory bootstrap artifacts.

The strict source/payload/root-install checker reported zero warnings.

## Built Artifact Counts

Normalized shipped payload or skill entries:

| Artifact | Count | Composition | Executable files | Helper dirs |
| --- | ---: | --- | ---: | ---: |
| memory wheel | 42 | 14 machine-data, 16 prose-doc, 9 structural-doc, 3 template | 0 | 0 |
| memory sdist | 42 | 14 machine-data, 16 prose-doc, 9 structural-doc, 3 template | 0 | 0 |
| planning wheel | 42 | 6 machine-data, 27 prose-doc, 4 schema, 5 structural-doc | 0 | 0 |
| planning sdist | 42 | 6 machine-data, 27 prose-doc, 4 schema, 5 structural-doc | 0 | 0 |

## Source Tree Observations

### Memory

The memory bootstrap source contains 34 files:

- structural entry/readme surfaces
- repo memory directory README files
- memory note templates
- memory manifest and upgrade metadata
- memory workflow and skill routing docs
- managed memory skills under `.agentic-workspace/memory/skills/`
- temporary install/adopt bootstrap skills under `.agentic-workspace/memory/bootstrap/skills/`

The package also ships `packages/memory/skills/` into `_skills`, adding bootstrap lifecycle skills outside the checked-in target payload.

This is acceptable product shape as long as those skills remain declarative and language-agnostic. A shipped skill may tell an agent what workflow to follow or which package CLI command to use; it must not assume that the host repository can execute Python, shell, Node, PowerShell, or any other language-specific helper from the checked-in payload.

### Planning

The planning bootstrap source contains 33 files:

- `AGENTS.template.md`
- core planning contract docs
- optional/deep contract docs
- planning manifest and upgrade metadata
- execplan and review templates
- planning schemas
- review/intake guidance files

Default install copies the required payload only. The package artifact still ships optional/deep planning docs and bundled planning skills so they can be installed with `--include-optional`.

The unclear boundary is package-shipped optional prose. This may be acceptable for optional install support, but it means the package still distributes a larger checked-in surface than the smallest default target repo needs.

## Architecture Assessment

The current architecture is clean with respect to executable code: executable behavior is in package source and CLI entry points, not bootstrap payloads.

The remaining architecture question is whether "shipped payload" should mean:

1. anything the package artifact carries for possible installation, or
2. only the smallest default checked-in target-repo install.

Today the implementation mixes both:

- planning has a smaller default install, but still ships optional/deep surfaces in the artifact;
- memory installs all managed memory skills and the temporary bootstrap workspace by default;
- skills are treated as checked-in declarative workflow affordances, which is valid when they stay language-agnostic and route execution back through package CLIs or host-provided commands.

If the intended product shape is "smallest checked-in target repo by default, with CLI-owned executable behavior and declarative skills as optional or managed affordances", then memory default payload size and planning optional surfaces should be revisited without treating skills themselves as residue.

## Recommended Follow-Up

1. Add a memory payload classification record matching `packages/planning/payload-surface-classification.json`.
2. Split memory default payload into the smallest durable install plus clearly managed declarative skills where they provide leverage.
3. Add checks or review guidance that shipped skills stay runtime-agnostic: they may route to package CLIs or host-declared commands, but must not ship or require language-specific helper code in target repos.
4. Decide whether planning optional/deep docs should remain shipped in the artifact, move into package source query output, or become a separate optional resource bundle.
5. Extend the source/payload checker with a non-failing payload-shape section that reports structural, machine, template, schema, prose, skill, optional, and temporary-lifecycle counts. This would make future scans cheap without making current architecture fail before the policy is settled.
