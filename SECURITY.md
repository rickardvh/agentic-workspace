# Security policy

## Supported versions

Security fixes are made on the current default branch and the latest coordinated release. Older releases may receive guidance, but are not promised patches.

## Reporting a vulnerability

Use [GitHub private vulnerability reporting](https://github.com/rickardvh/agentic-workspace/security/advisories/new). Do not open a public issue for an undisclosed vulnerability or include credentials, repository secrets, or exploit data in Planning, Memory, logs, or pull requests.

Include the affected version/commit, platform, trust assumptions, reproduction, and impact. Maintainers will acknowledge a report as soon as practical, coordinate validation and remediation privately, and publish an advisory when users can act safely.

## Security boundary

Agentic Workspace is a mutation-capable workflow tool, not a sandbox. A host repository and its checked configuration, proof commands, hooks, generators, and explicit executor commands must be trusted before execution. Dry-run means the selected AW lifecycle operation does not apply its declared repository mutation; it does not make imported code or configured commands safe.

The normative boundary and supply-chain controls are documented in [docs/security/threat-model.md](docs/security/threat-model.md).
