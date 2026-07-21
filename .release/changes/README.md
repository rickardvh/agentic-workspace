# Release Changesets

Product PRs that affect packaged behavior, generated outputs, release policy, or
shipped payloads must add one TOML changeset in this directory.

```toml
schema_version = "agentic-workspace/release-change/v1"
bump = "patch"
summary = "Describe the user-visible release note."
```

Use `major`, `minor`, or `patch` for `bump`. The release PR copies every summary
into `.release/releases/vMAJOR.MINOR.PATCH.md`, consumes all pending changesets,
and removes the TOML files after applying the highest requested bump to every
coordinated package manifest.
