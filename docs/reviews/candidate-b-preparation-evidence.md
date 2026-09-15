# Candidate B preparation evidence

## Issue-form preparation (#3262)

The first Candidate B probe adapts the existing repository issue-body aid and
integrates it into `github-issue-creation`. This is implementation evidence, not
independent acceptance of #3262 or completion of #3276.

### Exact subject and bounded trace

Baseline: accepted master `dda514d2f1d4ecc91e81cb7fba99d1c8d19e06ce`.
The after trace uses this PR's helper and the checked-in
`github-issue-body/examples/direction-request.json`, with all required semantic
fields explicitly supplied. Each trace runs in a fresh Python process on Windows
with the repository environment. No GitHub mutation, model worker, network fetch,
runtime resolution, or detail fetch occurs.

| Observation | Before | After |
| --- | ---: | ---: |
| Helper machine calls | 1 | 1 |
| Preparation-local source reads (excluding imports/request load) | 1 form | 1 form + 1 helper |
| YAML parses / request schema validations | 1 / 1 | 1 / 1 |
| Preparation SHA-256 digests, no additional source refs | 0 | 3 |
| Request JSON bytes, compact serialization | 1373 | 1373 |
| Result JSON bytes, compact serialization | 1501 | 2221 |
| Body bytes | 1033 | 873 |
| Preparation elapsed | 4.12 ms | 4.78 ms |
| Fresh-process elapsed, including Python/imports | 158.36 ms | 161.37 ms |
| Trace retries / repairs | 0 / 0 | 0 / 0 |

Single observations are not a statistical performance claim. Imported dependency
reads are outside the source-read count. The smaller body removes invented
optional-field TODO sections; supplied substantive fields remain intact. The
larger packet carries identity, completeness, and authority boundaries.

The previous ordinary skill required a model-mediated form inspection followed
by formatting/default reconciliation. The new ordinary path is one preparation
call after shaping, without carrying the 4735-byte direction form into the model
for that complete-input case. This is **procedure-step accounting (2 to 1)**,
not measured model inference calls: no controlled model comparison was run.
Incomplete input still requires semantic work; its diagnostic packet deliberately
returns current form fields/options. No speedup or lower total agent cost is
claimed. No cache/reuse layer is justified by this trace.

Development validation initially exposed a Windows test text-decoding assumption
and unsupported mandatory bug-form checkboxes; both were corrected before the
passing run. The initial edit command also encountered an unavailable bare
`python`; the existing repository environment was used. These are actual repair
costs, distinct from the zero-repair final trace.

### Fidelity, availability and subtraction

- Existing owner tests cover current direction/bug/review forms, supplied
  parent/leaf/later-evidence completion text, explicit checkbox assertions,
  missing/ambiguous/placeholder input, current template changes, helper/source/input
  drift and unrelated-source controls. The CLI exercises unavailable inputs and
  returns no body for incomplete requests.
- Preparation reads current forms and local source references. URLs/IDs remain
  explicitly external-currentness-unobserved. `--previous` compares only declared
  local preparation inputs and always recomputes; neither a prior packet nor a
  current comparison grants creation authority.
- The single retained formatter accepts typed shaped input. Planning lane/archive/
  decomposition conversion, semantic completion defaults, dropdown guessing and
  placeholder synthesis are removed. Existing scalar CLI convenience converges
  on the same preparation function.
- Python, PyYAML and jsonschema remain repository-maintainer dependencies in the
  existing locked environment. No shipped runtime, dependency, or public AW
  command is added. Missing tools/dependencies use the skill's direct current-form
  Markdown fallback.
- #3263 should derive its material availability contract only after the companion
  #3261 probe. This local comparison is not a proposed generic dependency ABI.
- #2929 creation replay is not exercised here: this implementation had an existing
  bounded issue owner and required no legitimate new issue. Creating a fixture
  issue merely for evidence would add external noise. That bounded inapplicability
  applies to this leaf, not to all remaining Candidate B work.

### Proof disposition and stop boundary

The existing issue-body owner suite is consolidated around input/form fidelity,
failure boundaries and exact local dependencies. Obsolete default-generation and
Planning-conversion tests are removed. Closure examples test text preservation,
not duplicate issue-shaping decisions. The existing aid-manifest suite and strict
source/payload check cover integration; no new CI constituent or cross-adapter
matrix is added. This is repository-only Python/Markdown work, so Rust semantics
and generated public contracts are unchanged.

Stop after focused owner/integration checks and repository commit checks pass,
then obtain independent review. Tests do not establish external-write authority,
independent acceptance, broad-owner reconciliation, Candidate B publication, or
#3276 completion. Total comparative operating cost remains unknown.
