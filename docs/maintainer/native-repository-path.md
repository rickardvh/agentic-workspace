# Native repository maintenance

The source repository's configured ordinary AW invocation is
`./target/debug/agentic-workspace`. Before first use and after changing Rust or
bundled contract/payload sources, run `cargo build --locked --workspace --bins`.
This builds both the CLI and its colocated shared core; building only the CLI
adapter can leave the core absent or stale. Windows resolves the `.exe` suffix.
The executable calls the shared Rust core. Python and TypeScript remain
bindings. Repository generators and checks may use Python, but are not an
alternate authority for ordinary product operations.

The Python distribution's optional command entry point launches its paired native
executable. The source runner resolves this checkout's native artifacts directly,
without choosing an editable Python distribution or refreshing a generated CLI.
Missing native artifacts fail closed. Older `init`, `summary`, `implement` and
other former-host commands are not a compatibility fallback; use the current
native request/action contract. Maintainer generators remain separate tooling.

Start with the invocation in `AGENTS.md`, the current task and `--format json`.
Include each known path with a separate `--changed`. Read the decision packet:
source-read requests deliver current instructions, bounded answer requests carry
the owner's authority/currentness fields, and `primary_action` is the exact
invocation the native owner has prepared. Submit requests to `start --input`
and actions to `invoke --input`, preserving target, task and changed paths.
Resolve again after an effect. A blocked or missing action is not permission to
switch to the former host.

The former Planning bridge preserves established selection and material:

- A recognized former source is readable context, not native mutation custody.
- An occupied legacy selector requires the exact owner-produced, revision-bound
  transfer request and an explicit human answer. Transfer preserves the selector's
  selection and the plan bytes. It grants neither proof nor completion.
- Following acquisition, native updates preserve owner identity and relationships.
  Reconcile the changed source before reusing its current subject or proof.
- Tracked update provenance uses repository-relative references. Local immutable
  attempts and results remain bound to their producing checkout. A copied plan
  preserves its observed material but must acquire current native custody in the
  new checkout. Never copy local receipts to manufacture that authority.
- Pending writes retain their original invocation and postimage format across
  software changes; recovery does not silently rewrite the uncertain effect.

Native payload admission compares installed bytes with the artifact's bundled
payload and checks the configured release/capability requirement. A provenance
label cannot hide drift. Required-before-work and required-before-claim keep
their distinct force, as do advisory compatibility and closeout obligations.

This path has real former-owner transfer/update/recovery evidence and independent
native, JSON, Python and TypeScript tests. It does not establish all native owner
outcomes or release/platform admission. Configuration mutation, consequential
delegation, positive lifecycle-derived target evidence and remaining owners stay
with #2613/#2767, #2947/#2817/#2818/#2210, #2209 and the #2983 frontier. #2909
aggregates conformance; #2990 admits one exact release-equivalent candidate.

For a current read-only assignment with a configured automatic process transport,
the native handoff returns a `delegation/dispatch/v1` request. Submit that exact
request bundle and invoke its returned action. Execution sends the sealed packet
on stdin, bounds process lifetime/output and returns the complete re-entry
request. A returned observation establishes no proof, Planning progress or
completion. Invalid, stopped, incomplete and stale returns remain excluded.
Repeating the exact current action reuses its terminal result; interrupted
terminal publication recovers without launching the worker again. An interrupted
worker without retained terminal evidence remains uncertain and cannot relaunch
under the same action. This process route does not claim native provider
continuation, shared-worktree mutation or complete lifecycle admission.
The returned re-entry bundle includes `delegation/read-result/v1`: the execution
owner checks its exact committed result and revalidates the original action
before exposing execution provenance. A caller-edited observation cannot acquire
that provenance. Transport provenance still grants no task acceptance or target
quality. The existing context-cost contract records process-input bytes and
elapsed time; provider framing, tokens, internal retries and downstream burden
remain unknown when the adapter cannot observe them.

Assignment offers a bounded use/repair/reject judgment for that current execution.
Planning may retain the admitted summary through its existing writer into the
selected owner's continuation frontier. Fresh re-entry is still required; proof
execution carries the exact Planning continuation. One current retained result
and selected-command check may supply contextual evidence for the matching
eligible configuration. Source drift or native Planning supersession de-adopts
that signal; it grants no target eligibility, task-success or completion authority.
