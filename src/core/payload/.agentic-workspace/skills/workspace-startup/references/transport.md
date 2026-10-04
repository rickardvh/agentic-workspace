## Client transport and stored carriage

Use this detail when an integration can retain native machine data outside the
model-visible result. AW carriage preserves exact requests and earlier answers;
it grants no permission and does not retain task meaning. Plain compact callers
use returned reentry/reference/answer directly through the
[ordinary owner interaction](owners.md).

For a carried client, show the entire `view`, including peer restrictions, source
material and claim limits. Printing carriage before filtering saves no context.
Keep the machine carriage in one bounded task file. Use the configured executable,
actual task, known changed paths and an existing scratch path:

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

After judging a question, submit its exact reference and the bounded semantic
answer without copying owner identity fields:

```powershell
$raw = & $aw start --input $carrier --reference $reference --answer $answer --projection carried
if ($LASTEXITCODE -ne 0) { throw 'Answer failed; resolve current state' }
$r = $raw | ConvertFrom-Json -ErrorAction Stop
$r.carriage | ConvertTo-Json -Depth 100 -Compress |
    Set-Content -LiteralPath $carrier -Encoding utf8 -ErrorAction Stop
$r.view | ConvertTo-Json -Depth 100 -Compress
```

For an admitted effect, use `invoke --input $carrier --reference $reference`
with the returned action reference. Store the complete result before interpreting
continuation. Parsing or storage failure never permits replaying a possibly
committed effect. Reobserve or recover through its exact owner.

A bare request input with task/changed flags is suitable only when no earlier
answers are needed. After an answered step, retain current reentry or carriage.
A complete context file owns its projection and work fields; omitted flags do
not replace that context. Stable `owner:request:...` identities discover current
requests; submit answers using the exact returned reference.

Stale, corrupt or lost carriage recovers through current sources. Never repair
its identity fields by hand. Omit `delivery_refs` after the corresponding source
text is lost, even if the carrier file survives. Reacquire required text and
preserve useful meaning with Planning, not a transport file. A host rejection
before execution establishes only the observed rejection; once execution may
have started, preserve effect uncertainty and follow recovery.
