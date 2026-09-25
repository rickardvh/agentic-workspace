## Exact tools without protocol copying

Use the public Rust-backed contract as a tool, not as prose to memorize.

For generic current resolution, a configured invocation may use `start --target . --task "<task>" --format json`. Known changed paths can be supplied with repeated `--changed` arguments. Compact output may include exact requests/actions/references and same-work carriage; optional detail remains lazy.

When a bounded owner request is returned, supply only the requested human/agent judgment or material and return the exact request through the supported public input. When an effect-bearing action is returned, execute that exact action through `invoke`; do not reconstruct it from schema-valid parts.

For a non-trivial structured request, keep the request as data rather than
embedding its semantic payload in shell text. Preserve the exact AW-returned
request and fill only the fields/material the owner asks for. Write the completed
request as UTF-8 JSON with a file-writing tool, then submit it with a short command:
`agentic-workspace start --target . --task "<same task>" --input <request.json>`
(using the configured invocation and the same changed-path context). This bare
request form is sufficient only when no earlier work-bound answers are needed.
Task and changed-path flags identify scope; they do not carry prior answers.
For a multi-step exchange, keep the returned carriage and use its exact reference
with the bounded answer as shown below. Do not switch back to bare task flags
after answering a question: that fresh resolution can ask the question again or
withhold the next request. Keep the updated carriage after every answered step.
Resolve a stable `owner:request:...` identity using the same carriage. Its returned
`reference` accepts an `--answer` object containing the requested argument fields
(for example `{"material": {...}}`); native validation still governs the proposal.
Use that exact reference, not the stable identity itself, when submitting an
answer. Request identity and revision fields are never part of the answer.
The shell command carries ordinary arguments and the file path, not nested text, JSON
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

Use carried mode only when the caller can retain its machine data outside the
model-visible tool result. Show the entire `view`, including peer consequences,
source material and claim limits. Printing the carrier before filtering it saves
no model context. Plain compact callers can submit a returned reference with the
same explicit work context and only the new bounded answer; no file is required.

This PowerShell example uses the configured executable, actual task and changed
paths, and a `carrier.json` path inside an existing bounded task scratch container.
The shell holds the transport; only the final expression reaches the model:

```powershell
$scope = @('--target', '.', '--task', $task)
foreach ($path in $changed) { $scope += @('--changed', $path) }
$raw = & $aw start @scope --projection carried
if ($LASTEXITCODE -ne 0) { throw 'Startup failed' }
$r = $raw | ConvertFrom-Json -ErrorAction Stop
$r.carriage | ConvertTo-Json -Depth 100 -Compress |
    Set-Content -LiteralPath $carrier -Encoding utf8 -ErrorAction Stop
$r.view | ConvertTo-Json -Depth 100 -Compress
```

After judging a returned question, supply its exact `$reference` and the new
bounded `$answer` (a JSON value), without copying immutable owner fields:

```powershell
$raw = & $aw start --input $carrier --reference $reference --answer $answer --projection carried
if ($LASTEXITCODE -ne 0) { throw 'Answer failed; resolve current state' }
$r = $raw | ConvertFrom-Json -ErrorAction Stop
$r.carriage | ConvertTo-Json -Depth 100 -Compress |
    Set-Content -LiteralPath $carrier -Encoding utf8 -ErrorAction Stop
$r.view | ConvertTo-Json -Depth 100 -Compress
```

For an authorised effect, use `invoke --input $carrier --reference $reference`
with the returned action reference. Preserve the complete effect result, including
`value` and its owner-specific next requests, before handling its continuation.
Filtering for guessed top-level fields can discard a required next operation.
A parsing/storage failure after invocation is not permission
to replay the effect. Reobserve or use exact owner recovery. Consume a current
continuation; do not call start again solely for ceremony.

Changed task/target/scope requires fresh resolution, never editing an issued
envelope. Lost, stale or corrupt carriage also recovers through fresh current
sources or exact effect recovery. Keep only useful current transport files and
remove them through the resource lifecycle; carriage is not retained task meaning.

Source `delivery_refs` are separate presentation state. Submit them only while
their sufficient current text remains available to this consumer. After context
loss omit affected suppression refs even if the carrier file survives; reacquire
required text. A carrier grants neither availability nor proof or permission.
