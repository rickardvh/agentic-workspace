## Development source preparation or reassessment

Use this detail only for a development source checkout, or when Configuration
returns `source-reassessment-required`. Ordinary installed setup uses the shipped
artifact; these maintainer steps are not another consumer lifecycle.

Build the native pair with `cargo build --locked --workspace --bins` before first
native use and after Rust or bundled contract/payload changes. Build both binaries
together. Reuse the pair while its relevant source remains current; a new context
alone needs no rebuild. If a required build is outside authorized scope, state the
specific runtime gap and use the read-only fallback.

Edit owning canonical sources and regenerate declared payload copies through the
repository's existing generator. Source maintenance is separate from a target
repository effect; a newer artifact grants no overwrite authority.

For a returned source reassessment gap, answer the bounded current setup question
with its grounded reason. Configuration prepares and reobserves the source witness
internally before publication. Keep unknown formats and newer installed material
preserved. After assessment commits, use its exact `reconcile-payload` proposal
when provenance renewal remains required; the assessment itself does not renew it.
