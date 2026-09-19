## Exact tools without protocol copying

Use the public Rust-backed contract as a tool, not as prose to memorize.

For generic current resolution, a configured invocation may use `start --target . --task "<task>" --format json`. Known changed paths can be supplied with repeated `--changed` arguments. Compact output may include exact requests/actions/references and same-work carriage; optional detail remains lazy.

When a bounded owner request is returned, supply only the requested human/agent judgment or material and return the exact request through the supported public input. When an effect-bearing action is returned, execute that exact action through `invoke`; do not reconstruct it from schema-valid parts.

For a non-trivial structured request, keep the request as data rather than
embedding its semantic payload in shell text. Preserve the exact AW-returned
request and fill only the fields/material the owner asks for. Write the completed
request as UTF-8 JSON with a file-writing tool, then submit it with a short command:
`agentic-workspace start --target . --task "<same task>" --input <request.json>`
(using the configured invocation and the same changed-path context). The shell
command carries ordinary arguments and the file path, not nested text, JSON
serialization or quoting logic. Continue from the returned result/action; file
input uses the same native owner validation and grants no additional authority.

When a temporary request file is useful and AW-managed scratch is appropriate,
use one bounded task container and remove it when no longer needed through the
[task resource lifecycle](../../workspace-resources/SKILL.md). Small/simple answers
need no file ceremony; `--input -` also accepts JSON on stdin. There is no byte-count
threshold: avoid turning structured material into a large shell script. This
procedure does not guarantee that a host will accept every invocation.

After an invocation, distinguish the effect outcome from continuation. Never retry a possibly committed effect merely because continuation failed. Use a current continuation when available; otherwise use exact re-entry/recovery or freshly resolve current state. Currentness is revalidated by the owner, not guaranteed by remembered model context.

Detailed schemas and packet fields belong to generated contracts/reference surfaces. Load them only when a client or debugging task actually needs them.
