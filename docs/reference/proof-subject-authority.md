# Proof identity and admission

Rust owns proof dependency roles, subject construction, subject comparison,
receipt shape admission and assignment-proof binding. Python and TypeScript
transport those contracts; the native public Verification reader consumes the
same receipt admission. Building a subject or admitting a receipt's shape grants
no publication, producer, freshness, strategy or task-completion authority.

Python-issued subjects preserve their established compact JSON fingerprints and
observed Python runtime. Timestamp decoding remains a host codec: the Python
adapter retains its existing timezone-aware ISO decoder, while native receipt
reading accepts its supported ISO representation. An unsupported representation
remains unadmitted. A caller-supplied timestamp observation is available only at
the trusted producer transport, not native ordinary ingress.

The subject owner hashes confined declared semantic inputs. Proof publication
outputs remain diagnostic unless explicitly declared as claim inputs. Missing
files, escaped paths and incomplete identities cannot become reusable proof.
Same claims and matching valid fingerprints can reuse a subject; changed semantic
inputs stale it. An unrelated scope does not prove the current claim.

The existing Python proof reconciliation consumes bounded batches across the
native process boundary. Two commands and twenty candidate receipts require one
receipt-admission batch and one freshness batch, rather than a process for every
pair. Batches do not retain a cache between owner evaluations. A subsequent
source change is re-read and rejected.

Remaining native evidence work includes independently deriving the actual
execution runtime, selected strategy coverage and authenticated returned judgment.
Legacy Python runtime binding is preserved for compatibility; it is not copied
from a stored receipt and treated as a current native runtime observation. A new
native execution producer must bind the environment its command actually needs.
Native Verification continues to expose these unresolved requirements explicitly.

Original-owner fixtures, existing receipt publication/reconciliation regressions,
malformed identity negatives and independent language/JSON consumers protect this
boundary. These checks do not satisfy the separate expensive-proof reuse,
independent review, native dogfood or supported-provider lifecycle gates.
