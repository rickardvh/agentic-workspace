# Lazy Discovery Measurement Audit

## Scope

- Run the first cheap lazy-discovery measurement framework against the current selector-enabled defaults, proof, and ownership surfaces in this repo.

## Method

- Command: `uv run python scripts/check/measure_lazy_discovery.py --target .`
- Proxy metrics:
  - UTF-8 bytes returned
  - character count returned
  - approximate tokens via `ceil(character_count / 4)`
- Comparison rule:
  - full machine-readable contract output for a question
  - selector-shaped narrow answer for the same question

## Results

| Question | Full bytes | Narrow bytes | Bytes saved | Reduction |
| --- | ---: | ---: | ---: | ---: |
| Choose the proof lane | 13891 | 4402 | 9489 | 68.3% |
| Read the current proof state | 4957 | 4398 | 559 | 11.3% |
| Resolve the owner of active execution state | 5243 | 655 | 4588 | 87.5% |
| **Total** | **24091** | **9455** | **14636** | **60.8%** |

Approximate token proxy:

| Question | Full approx tokens | Narrow approx tokens | Tokens saved | Reduction |
| --- | ---: | ---: | ---: | ---: |
| Choose the proof lane | 3473 | 1101 | 2372 | 68.3% |
| Read the current proof state | 1240 | 1100 | 140 | 11.3% |
| Resolve the owner of active execution state | 1311 | 164 | 1147 | 87.5% |
| **Total** | **6024** | **2365** | **3659** | **60.7%** |

## Takeaways

- The selector path now gives a materially cheaper one-answer route overall in this repo.
- Validation-lane choice and ownership lookup show the strongest gain because the full surfaces carry much broader contract context than the narrow question needs.
- Current proof-state lookup is only modestly smaller because most of that surface is already the current-state object; future compactness work should focus on state-specific subfields only if repeated use shows that remaining 11.3% matters.

## Decision

- The first compact-contract selector tranche is now justified by measured retrieval-size reduction rather than schema neatness alone.
- Future compactness work should use this audit pattern before claiming a lazy-discovery win.
