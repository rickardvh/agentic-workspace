# Source, payload and discovery boundaries

The Rust core owns current deterministic domain semantics and effects. Python, TypeScript, JSON and native CLI entry points project that authority. Maintainer tooling does not add public CLI commands.

Keep four layers distinct:

| Layer | Authority |
| --- | --- |
| Source and contracts | Native behavior and its public declarations; package source owns maintenance tools. |
| Bootstrap payload and package skills | Reusable templates and procedure supplied to consumers. |
| Root operational install | Repository policy and domain state under their declared owners. |
| Generated copies | Derived outputs refreshed from their source, never an independent authority. |

Edit the declared source of distributed content, regenerate its copies, and validate source/payload agreement. Do not overwrite repository-owned state to refresh product guidance. Use current Configuration owner requests for adoption or removal, with their exact custody and preservation rules.

Source-checkout maintainers inspect the boundary with `make native-sources` and the native artifact checks under `src/tooling/check/`. The canonical binding roots are `src/cli/python/` and `src/cli/typescript/`; no generated command-package implementation is required.

Discover specialized skills only when relevant to the task. Extract a new capability only when it has clear ownership, stable seams, independent utility and demonstrated maintenance value. Keep advisory findings transient until a current owner accepts actionable work or durable knowledge.
