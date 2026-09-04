# Generated two-language contract

`contracts/semantic-ir.json` is the implementation-independent authority for
public kinds, decision composition, contribution dimensions, operation result
semantics, canonical serialization/identity, compatible required capabilities,
supported operation identities, and the explicit target primitive
boundary.

Run `python scripts/generate_contracts.py` after changing that authority. It
produces:

- the Python semantic projection and packaged IR in `src/agentic_workspace/`;
- the JavaScript runtime, TypeScript declarations, package manifest, and IR in
  `typescript/`.

`scripts/check_generated_contracts.py` fails when a projection is stale. Shared
conformance vectors execute both projections and the JSON CLI boundary. A normal
semantic change starts in the IR/generator and must not be patched independently
into either generated target.

Canonical values use NFC strings, Unicode-code-point key order, ASCII-escaped
UTF-8 JSON, safe integers, and SHA-256. Unknown additive fields are ignored by
normalization; an unknown required capability fails closed with an exact upgrade
route. Both targets expose the same capability-first module admission,
contribution, bounded-decision, operation, and result semantics. Effectful
TypeScript dispatch requires a host durable-commit coordinator; Python supplies
the equivalent filesystem/process primitive in `Workspace.invoke`.

The Python-only primitives are CLI bootstrap, filesystem persistence, entry
point discovery, process execution, JSON Schema validation, and host handler
dispatch/persistence callbacks. The TypeScript-only primitives are ES module
bootstrap and host-supplied module registration, persistence/process bindings,
schema validation, and handler dispatch. These primitives may implement their
platform boundary but may not acquire domain-specific operation meaning.

External adapters consume these package/JSON boundaries. They are not registered
with AW, and AW does not own their credentials, provider lifecycle, or telemetry.
An external source owner contributes the same normalized capability contract and
admits observations through its own typed operation.
