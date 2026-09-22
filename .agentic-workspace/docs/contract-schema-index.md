# Contract Schema Index

Native public contracts and shared schemas live under `src/core/contracts/`.
Planning, Memory and Verification schemas live with their native owners under
`src/core/src/modules/`. The Rust owners consume these declarations directly.
Python and Node facades forward the public envelopes; they do not interpret them.

Maintainer-only contracts live under `src/tooling/contracts/`. They describe
source validation, generation and repository workflow, not another installed
runtime. The structured-file inventory classifies retained structured sources.

Use `make native-sources`, `make structured-file-inventory`, and the applicable
native owner tests to validate a changed boundary. Generate reference output with
`make render-schema-reference`; edit its canonical schema rather than the output.
The retired generated-operation catalogues and Python host are not current APIs.
