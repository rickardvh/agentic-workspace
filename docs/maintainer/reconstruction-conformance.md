# Reconstruction conformance followthrough

#2909 consumes the corrected owners under #2983; #3138 remains the promotion
ledger. Green PR checks do not establish that every inherited prototype test or
public operation has a current native disposition.

## Evidence boundaries

| Surface | Current evidence and limit |
| --- | --- |
| Native ordinary consumers | `test_native_public_cli.py`, the native owner suites and `test_shared_core.py` exercise the Rust authority through native, JSON, Python and TypeScript consumers. Each owner retains its own currentness and authority assertions. |
| Compact operating carriage | `test_native_operating_carriage.py` compares exact actions/claims and bounded answers across four consumers, rejects unknown/altered/forged/stale/work-rebound carriage, and measures a predetermined host-composed configuration journey. Existing owner tests explicitly request full detail. `test_native_invoke_continuation.py` compares full/compact/carried post-effect entry across four surfaces; Rust tests preserve committed outcomes on continuation failure and distinguish uncertainty from rejection. Reuse and worker-entry outcomes remain open; see `operating-carriage.md`. |
| Independently linked owner | `test_native_independent_owner.py` builds a separate Rust fixture. Its manifest is classified as a diagnostic fixture; linking supplies no repository admission. |
| Generated process contracts | `test_generated_tool_conformance.py` runs the migrated startup and four explicit retirement contracts through Python's native entry point. Remaining cases exercise historical generated adapters and cannot prove current native command support. |
| Extracted Python helpers | `test_review_scale_extracted_boundaries.py` retains publication, selected-owner, write-order and dry-run compatibility assertions. These are helper tests, not native owner acceptance. |
| Assignment override fixture | The former reassignment fixture is retired with its unavailable export. Native eligibility and request rejection remain covered; full attempt replacement remains with #2210/#2947. See `assignment-public-disposition.md`. |
| Session identity | The source checkout config selects the native binary. The retained Python launcher's identity bridge is historical implementation evidence; tests do not require a machine-local config file or claim the old launcher is current. |

The four retired process cases require their exact native unknown-command error
and retain filesystem restrictions. Empty stdout is permitted because rejection
is emitted on stderr. No failure is converted into a successful operation.

## Unresolved cumulative findings

The September 9 source-checkout audit started from `52e3c83da` with the fixture
corrections in this slice. It does **not** establish a passing `make check-nosync`:

- The CLI group reached 631 passes and two skips before five failures. Former
  Assignment dispatch/export setup still calls the unavailable command family;
  a context-currentness fixture still invokes the former evaluation command.
  Retained empty-return and unrelated-Planning invariants need explicit native
  consumer dispositions, not restored Python command authority.
- The session/review group reached 223 passes before five failures. Its old
  configured-launcher assertion is corrected here. Former `config`/`session-log`
  integration cases still require disposition against current native diagnostic
  capture and the separately retained analysis helpers (#2995/#2613).
- The contract group reached 439 passes before five failures. Inventory and mock
  signature defects are corrected here. The old Python implementation-size
  ratchets still report growth; this slice neither raises their limits nor
  represents that checker as proof of the single Rust authority.
- The validation runtime plan omits current compact labels and commands. Its
  measurements are bound to the historical graph. Updating that plan requires
  truthful current measurements or an explicit historical-evidence disposition;
  old result identities must not be rewritten as a successful current run.

These bounded runs used `--maxfail=5`; additional failures may remain after the
reported ones. They are diagnostic progress, not exhaustive candidate evidence.
Exact artifact admission, cross-owner aggregate journeys, repository-lifetime
benefit, and the other current #2909 completion requirements remain open.
