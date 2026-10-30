# Resolve a testing design question

Use the relevant section when the [compact selection method](select.md) leaves
a concrete design question. These examples specialise that method; they do not
require every technique, a new library or a separate design document.

## Model intended behaviour

For material new behaviour, choose a small test model while shaping the change:
a few justified examples, a decision table, state transitions or a property may
suffice. Choose depth from consequence, plausible exposure, reach, reversibility
and uncertainty. A one-line authority check may need more evidence than a large
mechanical refactoring; uncertainty about a shared dependency can justify
investigation without predicting the exact hidden defect.

| Question | Useful starting point |
| --- | --- |
| Which inputs behave differently? | Representative valid and invalid classes; split a class when its members behave differently. |
| Where does behaviour change? | Boundary values and values just either side, with relevant units and representations. |
| Which rules interact? | Decision tables or constrained combinations, including forbidden outcomes. |
| What depends on history? | Valid and invalid transitions, operation sequences, retries and interruption points. |
| What should hold across many inputs? | Properties or relationships between runs, with generators reaching the relevant categories. |
| Which configurations interact? | Risk-appropriate interaction coverage; pairwise coverage does not establish higher-order correctness. |
| Does the real interface work? | A focused storage, transport, packaging or deployment check with the actual boundary or a justified faithful substitute. |
| Does prose or presentation work for its reader? | Direct inspection or a bounded reader/user exercise; automate stable objective contracts, not subjective quality by word matching. |

Examples and generated cases complement each other. More generated samples do
not establish more independently justified risks. Keep failures interpretable.
Characterisation can help a risky legacy refactoring, but observed output is not
automatically correct or a permanent compatibility promise. Change expectations
when intended requirements change; a pure refactoring normally preserves them.

## Establish correctness and fidelity

An oracle is the basis for deciding whether an outcome is correct. Use an
explicit requirement, independently calculated example, trusted reference or
justified invariant. Computing expected and actual values with the same new
helper can preserve the same mistake on both sides. A round trip can similarly
miss matching encoder/decoder errors; use known examples or interoperability
evidence where that matters.

Choose a stable behavioural boundary with useful failure localisation. It may be
a pure function, component API, local database or full user journey. Private
units are not automatically best because they are cheap, nor end-to-end tests
because they are realistic. A mock returning success does not prove that a
transaction commits or an authority check holds. Control time, latency and
failures with substitutes where useful, while checking relevant fidelity. Keep
additional adapter or environment evidence when it observes risks the shared
semantic tests cannot establish.

For important new or repaired coverage, check sensitivity to the relevant wrong
behaviour when proportionate: a pre-fix run, small injected fault or focused
mutation can help. This does not mandate a mutation framework, score or
reconstruction of every old version.

## Diagnose an escape and retain useful protection

| What the prior evidence missed | Repair to consider |
| --- | --- |
| A relevant test existed but was not run | Repair execution selection, prerequisites or delivery; do not duplicate it. |
| A category or boundary was absent | Extend its coherent family or add a clear independent case. |
| An assertion accepted an incorrect result | Strengthen the expected result or invariant. |
| A fake concealed real dependency behaviour | Repair fidelity or add the missing real-boundary check. |
| A sequence or interaction was absent | Extend state/interaction coverage; preserve a minimal reproducer where useful. |
| The requirement changed or was ambiguous | Resolve the intended behaviour and update coverage accordingly. |

Investigate nearby risks in the same abstraction when useful. An old passing
suite establishes neither completeness nor negligent design; assumptions and
requirements matter. An urgent fix can disclose an unresolved diagnostic gap
without waiting for an exhaustive audit. Never weaken expectations or accept a
new snapshot merely to make the patch green.

Parameterise cases sharing a contract and assertion structure, with independent
case reporting. A dedicated case is often clearer when setup, cause or expected
outcome differs; avoid branching expected-value logic or shared mutable setup
that hides failures. One class may need several representatives. A rare
fuzz-discovered counterexample can deserve a permanent small seed after improving
the generator: the possibility of regeneration is not reliable protection.
Temporary experiments can disappear once durable protection is sufficient or
repeatability has no worthwhile future use.

## Select execution without hiding uncertainty

Price selection and execution together. Running a small fast suite can be
cheaper than spending minutes filtering one-second tests. Broad shared-code,
dependency, build, configuration or platform changes can warrant broader checks.
Incomplete impact maps, including dynamic maps that miss new paths or
environmental dependencies, cannot prove omitted tests irrelevant. Omitting a
test from this run does not justify deleting it.

Recurring execution follows repository authority. Expensive integration, fuzz,
platform or performance checks need an appropriate event or cadence; high
consequence checks may need to gate changes. Do not invent schedules or move
required checks to nightly runs. Reuse evidence only when its actual inputs,
environment and scope still apply, not just because command text is unchanged.

Use bounded discovery for novelty, uncertainty, consequential boundaries or
repeated escapes. A large fixed passing suite does not establish a complete
model. Keep ordinary tests isolated, reproducible and resource-bounded; control
clocks, randomness and external state, retaining useful failure seeds or context.
A flaky result may reveal a product race. Retries cannot erase it; quarantine
must expose lost protection and a responsible recovery path.

## Consolidate without losing protection

Before merging or deleting, identify surviving assertions, input distinctions,
sequences, environmental fidelity and diagnostic value. Similar names, shared
covered lines and long histories of passing do not establish substitutability.
Compare a replacement with the old reproducer or a representative fault when
useful. Independent oracles or environments can justify apparent overlap.

Use coverage to find unexplored code and mutation to challenge assertions, not as
universal success targets; preserve explicit required metrics. Measure runtime
or recurring failure/maintenance cost before making material economic claims.
Prefer simpler setup, cheaper faithful boundaries and reliable tests over hiding
cost behind more workers or looser timeouts. Parallelism can reduce latency
without removing compute or maintenance. No global suite cleanup is implied.

## Research and limits

This is engineering guidance, not a claim that a technique or suite shape is
universally optimal. Read research only for a question that needs it:

- [QuickCheck, Claessen and Hughes (2000)](https://research.chalmers.se/en/publication/237427)
  introduces executable properties and custom generators, including pitfalls.
- [NIST SP 800-142 (2010)](https://csrc.nist.gov/pubs/sp/800/142/final)
  explains combinatorial testing with practical trade-offs and limits.
- [Software Engineering at Google, chapter 13](https://abseil.io/resources/swe-book/html/ch13.html)
  discusses the applicability and fidelity of test doubles; its organisational
  suite proportions are not portable requirements.
- [Rothermel et al. (1999)](https://digitalcommons.unl.edu/csetechreports/82/)
  found that suite reduction could substantially compromise fault detection in
  their experiments. Apparent redundancy alone is insufficient.

The [consolidated design and bibliography](https://github.com/rickardvh/agentic-workspace/issues/3930)
also covers input selection, oracle problems, mutation, coverage, regression
selection and flaky-test diagnosis. Those studies keep their original contexts;
they supply no universal quotas, ratios or guarantees.
