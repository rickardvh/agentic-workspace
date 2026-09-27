## Use a returned request or action

Use this reference when AW asks for a decision, returns an operation to invoke,
or identifies managed state that must change through its responsible component.
The returned **request** asks for input; the returned **action** describes an
operation that can have effects. Keep their exact identity fields. Supply only
the requested judgment or material, then inspect the result before proceeding.

AW's **carriage** is the disposable JSON that keeps those exact objects and prior
answers between calls. It is useful transport, not a saved plan or permission.

## Choose the input method before constructing the request

For a simple choice or small answer, use the returned reference directly. No
scratch file is needed. For a substantial structured update, keep the returned
request and prior answers as data. Use a file-writing tool to put UTF-8 JSON in
one task scratch file, then submit that file with `start --input`. Do not embed
the document, its nested JSON or its construction in a shell command. The shell
should carry the invocation and file path. The examples below show how to retain
the exact work context and answers.

When the file is a complete context object, put `projection` and the task context
inside that object; do not also pass conflicting context flags. The separate
`--reference` and `--answer` examples below use a returned carriage envelope.

If the host rejects an invocation before execution, report the observed rejection
and keep its cause unknown unless evidence identifies it. Use the supported input
method within existing permissions. If an effect may have happened, follow the
recovery instructions below before trying again.

A trusted correction about a recurring execution method requires source
disposition, even when it arrives during this exchange. Apply it now, supply the
finding through [current material](ordinary.md#current-material-and-needs), and
use the [correction procedure](../../workspace-instruction-correction/SKILL.md).
Compare the responsible source: apply sufficient existing guidance, make an
authorised bounded repair, or explain why no saved change is needed. A chat
promise does not establish that disposition.

## Carry the exact request and prior answers

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
