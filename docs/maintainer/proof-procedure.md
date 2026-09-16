# Callable proof procedure

The standard `workspace-proof-selection` skill now uses `proof-procedure` for
selected preparation and one exact check-to-receipt sequence. Its canonical
Markdown retains semantic guidance and removes envelope-copying choreography.
The shipped mirror and executable registry entry derive from that source.

`native_methods` is an internal command-to-function binding used by transport
and executable discovery. It contains the two actual consumers, resources and
proof, without routing by skill name or introducing a semantic registry. The
existing CLI declaration owns command metadata; the existing skill registry
owns optional method references. Both consumers share passive availability and
selected-material revalidation. Method selection is not a proof requirement for
direct native owner users.

Preparation uses the shared [current decision frontier](decision-frontier.md),
including post-effect continuation. It selects proof context before optional
owner detail is built; unrelated Configuration and Planning detail and untaken
manual report branches remain lazy. Execution can carry a unique missing required check established by Verification
without a model selection echo. Verification examines complete current routes and
profile knowledge, including alternatives omitted from bounded presentation; a sole
protocol candidate, unresolved applicability or a legitimate alternative yields.
The skill does not interpret manifests or decide sufficiency. Otherwise execution
accepts one exact selected-check request set or previously
returned native proof action. It never follows another owner's primary action,
answers applicability/sufficiency, runs an arbitrary batch, or authenticates a
reviewer. The selected command passes through native admission and custody;
Verification reobserves its receipt. Semantic scope and strategy assessments
remain exact caller carriage. An invocation without its assessment request set
can recover the effect but yields instead of reconstructing the missing request.

The proof publisher now reports that its owned receipt outputs introduce no new
semantic source paths. This permits the existing post-effect continuation to
run. Mutations of declared inputs still invalidate publication; arbitrary nested
command writes are not authenticated source edits. This declaration does not
claim a full filesystem diff or a command sandbox.

The result preserves the effect separately from current preparation. An invalid
post-effect source leaves the command committed and returns exact custody reentry
with `retry_effect=false`. Lost or uncertain results use native recovery, never
automatic new selection. Proof and independent review remain separate from the
method, even when strict closeout has no matching protocol.

## Bounded evidence and operating cost

Three native composition cases cover selected execution/admitted receipt/fresh
claim answer, strict closeout and missing/direct method, and confirmed execution
with failed continuation. Existing applicability and measurement journeys also
consume the composed path and compare retained results. The existing resource
composition cases and Rust two-consumer binding case protect shared behavior and
selective method currentness. This retains missing composition failure classes,
without a new matrix of adapters or a second proof test suite.

Before the frontier integration, the selected fixture reported 7,802 JSON bytes for preparation and 15,449 for the
execution/result boundary, using Python's default JSON serialization. Its full
direct debug answer was 107,641 bytes, but that is **not** the optimized direct
baseline: direct users also have compact/carried projections. These figures are
fixture observations, not a general context-reduction or performance claim.

A sole required check uses one caller interaction (`execute`) and four explicit
public owner calls, including the owner probe and exact selection. It still leaves
claim judgment and strict closeout visible. Regression cases cover optional and
unselected profile alternatives, semantic scope, a sole non-required candidate,
and receipt-backed requirements that must not run again.

The ordinary explicitly selected sequence uses two caller interactions (`prepare`, then
`execute`) and four explicit public owner calls in total. Native `invoke` also
performs its pre-effect admission and post-effect resolution; those costs remain.
A direct caller which uses continuation can perform the same four public calls;
the composition removes two model-mediated envelope transfers. The frontier
integration also removes optional construction, as measured separately in the
linked frontier evidence; mandatory native authority work remains.
Semantic scope/assessment carriage requires one additional current scope read
before receipt admission. No batching, hidden retry, persistent procedure state,
or new evidence store is added. Existing receipt/custody residue remains owned by
the proof operation.

Stop after native composition, shared resource, current Verification prerequisite
and contract/payload checks pass. Independent acceptance and source trust remain
external; successful local tests do not close aggregate #3277 or establish all
repository assurance requirements.
