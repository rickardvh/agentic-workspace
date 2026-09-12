# Route registry sources

The Rust route catalogue reads `tools/skills/REGISTRY.json` and
`.agentic-workspace/skills/REGISTRY.json` when present. It never recursively
searches the managed tree. A present canonical registry can admit custom or
independent registries through `registry_sources`, an array of exact
repository-relative file paths:

```json
{"schema_version":"skill-registry.v1","registry_sources":["custom/skills/REGISTRY.json"],"skills":[]}
```

Explicitly referenced sources are required. Missing, invalid, incompatible,
non-file or linked/reparse sources fail closed. Paths cannot escape the target;
each path has at most 64 components, each read is bounded to 256 KiB, and the
source set has at most 256 files. References may compose; duplicates and cycles
are read once. These declarations admit vocabulary only, never applicability,
effects or completion. Skill procedure paths remain relative to their registry.

The discovery result reports the selected `sources`. Its revision derives from
their exact paths and normalized contents, including declarations of further
sources. Changing or withdrawing a real source changes dependent route
currentness. Unrelated local instructions, scratch, nested repositories and
links outside selected paths do not participate. No scan ledger or index is
persisted. All public projections consume this same Rust catalogue.
