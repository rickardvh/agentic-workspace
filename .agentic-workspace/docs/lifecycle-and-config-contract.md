# Configuration and repository lifecycle

Repository policy lives in `.agentic-workspace/config.toml`; local overrides live in `.agentic-workspace/config.local.toml`. Current effective policy, source admission and bounded configuration changes belong to the native Configuration owner.

Use `agentic-workspace start --target <repo> --task "<task>" --format json` when exact current configuration or lifecycle information is needed. Follow current detail references and returned requests. Supply the requested judgment, then use `invoke` with the exact admitted action. Do not reconstruct a write from remembered fields.

Executable installation, repository adoption, optional domain setup and removal are distinct operations. Consult current installation guidance for the artifact and Configuration for repository effects. Adoption preserves existing instructions and does not imply that optional Planning, Memory or Verification state exists.

For recovery, inspect current owner gaps and the named sources. Preserve malformed, stale, modified or unowned material until its owner admits a repair. Do not restore removed lifecycle commands, invoke a package maintenance tool as a fallback public runtime, or edit interpreted state to bypass an unresolved source.
