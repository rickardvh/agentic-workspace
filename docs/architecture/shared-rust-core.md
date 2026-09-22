# Rust, Python and TypeScript APIs

Use these APIs to call AW from your own application or agent host. All three
reach the same Rust implementation; choosing a client language does not restrict
the language of the repository being worked on.

For terminal use, read the [CLI guide](../package/commands.md). For deciding what
an agent integration needs to do, read [Integrate an agent or tool](../extension-boundary.md).

## Install in your application's environment

| Client | Dependency |
| --- | --- |
| Rust | `agentic-workspace-core`; the examples also use `serde_json` |
| Python | `agentic-workspace` |
| TypeScript / Node.js | `@agentic-workspace/workspace-cli` |

Select and pin a published version using [Getting started](../agentic-workspace-install.md).
A global CLI installation is separate from adding a dependency to your program.
The Python and npm packages include the native executable pair for their supported
platform; those installed clients do not need Cargo. A Rust application compiles
the core as a dependency. Missing or damaged native executables are an error, not
a reason to switch to another implementation.

## Query current context

Each example asks the same question about the Git repository in the current
working directory. Run it from that repository, or change `target`. The result
is JSON describing the current context and available next steps; the exact
content depends on the repository. A successful query does not authorise a write.

### Rust

Add `agentic-workspace-core` at your selected release version and `serde_json` to
your application's dependencies. Call the public `operating` module:

```rust
use agentic_workspace_core::operating;
use serde_json::json;

fn main() -> Result<(), Box<dyn std::error::Error>> {
    let result = operating::start(json!({
        "target": ".",
        "task": "Inspect this repository",
        "projection": "compact"
    }))?;
    println!("{}", serde_json::to_string_pretty(&result)?);
    Ok(())
}
```

`operating::start` and `operating::invoke` accept `serde_json::Value` and return
`Result<Value, CoreError>`. They provide the same context-query and action-execution
boundary used by the language clients. See the [public Rust implementation](../../src/core/src/operating.rs)
for the exact entry points.

### Python

Use the installed package's top-level exports, not internal source-checkout modules:

```python
import json
import sys
from agentic_workspace import DecisionContractError, start

try:
    result = start({
        "target": ".",
        "task": "Inspect this repository",
        "projection": "compact",
    })
except DecisionContractError as error:
    print(f"AW query failed: {error}", file=sys.stderr)
    raise SystemExit(1)

print(json.dumps(result, indent=2))
```

Functions accept mappings containing JSON-compatible values and return dictionaries.
`DecisionContractError` reports native lookup or request rejection. See the
[installed exports](../../src/cli/python/agentic_workspace/__init__.py) and their
[signatures](../../src/cli/python/agentic_workspace/_binding.py).

### TypeScript / Node.js

Use the package-root exports in an ES module. This example is also valid JavaScript:

```typescript
import { start } from "@agentic-workspace/workspace-cli";

try {
  const result = start({
    target: ".",
    task: "Inspect this repository",
    projection: "compact",
  });
  console.log(JSON.stringify(result, null, 2));
} catch (error) {
  console.error("AW query failed:", error);
  process.exitCode = 1;
}
```

These calls are synchronous and return JSON objects. The package includes
[TypeScript declarations](../../src/cli/typescript/operating.d.mts); they describe the
transport, while Rust validates requests. The same exports are available from
`@agentic-workspace/workspace-cli/operating`.

## Inputs and results

A work context contains `target`, a description in `task`, and optional `changed`
paths. Keep that context consistent when submitting a returned request or action.
Use `request` with `start`, and `invocation` with `invoke`.

The default `compact` projection keeps optional detail behind references. `full`
returns expanded information. `carried` includes an explicit context carrier for
continuation without rebuilding the envelope. The carrier is transport data, not
permission to repeat a previous operation.

| Python | TypeScript | Purpose |
| --- | --- | --- |
| `start(context)` | `start(context)` | Query context or submit a current request. |
| `invoke(context)` | `invoke(context)` | Execute an exact returned action. |
| `resources(context)` | `resources(context)` | Submit a resource request. |
| `select_reference(context, reference, answer=...)` | `selectReference(context, reference, answer?)` | Select returned detail or supply the bounded answer a question requests. |
| `answer_carried(carriage, reference, answer)` | `answerCarried(carriage, reference, answer)` | Answer using the returned carrier. |
| `invoke_carried(carriage, reference)` | `invokeCarried(carriage, reference)` | Execute the exact action selected from a carrier. |

For queries, detail selection and invocation, the Rust `operating` calls accept
the corresponding JSON inputs directly. Clients must use returned references and
actions rather than inventing their identity or effect-bearing fields. Optional
questions and actions are not an instruction to execute everything offered.

An invocation can report rejection or uncertainty in its result; absence of a
language exception is not proof that it applied. Read `effect_outcome` separately
from continuation. Preserve a confirmed effect if continuation fails. If the
effect is uncertain, use recovery rather than submitting it as a new operation.

For source development, build both binaries as described in the
[contributor guide](../maintainer/contributor-playbook.md). The full source tree
contains historical Python modules that are not installed public APIs; their
presence is not an alternative import contract.
