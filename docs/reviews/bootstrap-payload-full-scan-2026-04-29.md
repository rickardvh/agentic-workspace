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

The unclear boundary is not executable code. It is procedural agent guidance shipped as target-repo checked-in files, especially temporary bootstrap workspace skills that the CLI could potentially provide or materialise only during lifecycle operations.

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
- skill prompts are treated as checked-in payload, even though they behave like procedural execution affordances rather than durable repo knowledge.

If the intended product shape is "smallest checked-in target repo by default, with CLI-owned behavior and optional affordances generated/materialised on demand", then memory should be compressed further and planning optional surfaces should be revisited.

## Recommended Follow-Up

1. Add a memory payload classification record matching `packages/planning/payload-surface-classification.json`.
2. Split memory default payload into a smallest durable install plus optional lifecycle/skill materialisation.
3. Decide whether bundled skills are package resources, generated local integration, or checked-in target-repo payload. Avoid treating them as ordinary durable repo surfaces by default.
4. Decide whether planning optional/deep docs should remain shipped in the artifact, move into package source query output, or become a separate optional resource bundle.
5. Extend the source/payload checker with a non-failing payload-shape section that reports structural, machine, template, schema, prose, skill, optional, and temporary-lifecycle counts. This would make future scans cheap without making current architecture fail before the policy is settled.
