# Generated Surface Trust

Generated material derives from a named current source and never adds authority.
The native host footprint is declared in `src/core/contracts/workspace_surfaces.json`.
Its materialization and preservation rules are enforced by Configuration.

`src/tooling/generate/generate_agent_interface.py` derives the core payload and
ownership read profile from their declared sources. Native builds reject payload
bytes that disagree with the portable input. Use `--check` to inspect freshness.
Repository-local owner state is not a disposable generated mirror.

`src/tooling/generate/generate_contract_catalogues.py` and
`src/tooling/generate/generate_schema_reference.py` produce reference documentation.
Edit their source contracts and regenerate when those declarations change.

The former generated command packages, standalone module installers and root
routing documents are removed. Native public commands and returned owner requests
are the current execution boundary; historical generated output supplies no
fallback authority or current proof.
