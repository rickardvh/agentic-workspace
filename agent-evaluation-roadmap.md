# Roadmap: Agent-Driven Dogfooding, Model-Zoo Evaluation, and Self-Improvement Loops

## Goal

Use agents themselves as a major development driver for Agentic Workspace by combining:

- real self-dogfooding
- human-free benchmark runs
- structured agent feedback
- repeated-failure clustering
- bounded human-guided prioritization

The aim is to make the product better for many different agents, especially smaller and cheaper ones, without letting benchmark theater or autonomous product drift replace judgment.

## Guiding rule

- Dogfood first.
- Benchmark narrowly and repeatedly.
- Prefer evidence from weaker/cheaper agents when the failure is about ambiguity, discovery cost, proof choice, handoff, or restart.
- Let agents generate signal, not final product strategy.
- Convert repeated friction into bounded contract improvements.

This matches the current product direction: checked-in continuity, delegated judgment, query-first discovery, mixed-agent posture, and machine-readable proof/ownership/reporting surfaces.

## Success criteria

- The repo can be evaluated without human-in-the-loop benchmark execution.
- Different agents can produce comparable operational feedback and benchmark results.
- Repeated failures cluster into a small number of actionable product deficiencies.
- Cheaper/smaller agents improve over time on:
  - startup
  - ownership lookup
  - proof selection
  - handoff
  - restart
  - plan curation
- Roadmap work is increasingly driven by measured friction rather than idea momentum.

---

## Stage 1: Formalize dogfooding as a first-class product signal

### Objective

Make real use of the product on itself the primary development input, not just an implicit practice.

### Deliverables

- A checked-in dogfooding note that defines:
  - what counts as ordinary-use dogfooding
  - what counts as strong-planner / cheap-implementer dogfooding
  - what should be captured as friction
  - what should be ignored as one-off model weakness
- A compact failure taxonomy for dogfooding, such as:
  - startup/routing confusion
  - proof ambiguity
  - ownership ambiguity
  - plan curation drift
  - restart reread cost
  - handoff insufficiency
  - mixed-agent posture confusion
- A rule for when dogfooding friction becomes:
  - local cleanup
  - review finding
  - roadmap candidate

### Exit criteria

- Dogfooding feedback is captured in a consistent shape.
- The repo can distinguish repeated product friction from isolated annoyance.

---

## Stage 2: Build the model-zoo benchmark lane

### Objective

Run narrow operational benchmarks across many agents and model tiers.

### Scope

Benchmark the product on the questions it claims to make cheaper:

- startup path
- ownership lookup
- proof-lane selection
- delegated-judgment escalation
- handoff and restart
- planning inspection
- bounded jumpstart follow-through

### Deliverables

- A benchmark runner that can execute the same scenario across:
  - strong frontier models
  - smaller/cheaper models
  - local/open models
  - agents with strong internal delegation
  - agents without it
- A model registry for benchmark runs with metadata such as:
  - family
  - strength tier
  - cost tier
  - context-window class
  - internal-delegation capability
- A run manifest format that records:
  - fixture
  - prompt
  - role
  - agent/model
  - outputs
  - score summary

### Exit criteria

- The same benchmark family can run across multiple agents without human participation.
- Results are comparable even if not perfectly deterministic.

---

## Stage 3: Add human-role and judge-role agents as standard benchmark roles

### Objective

Make evaluation scalable by removing real humans from benchmark loops.

### Deliverables

- A structured human-policy spec for benchmark scenarios:
  - requested outcome
  - priorities
  - hard constraints
  - prohibitions
  - escalation response rules
- A worker-agent contract for what the benchmarked agent may do
- A judge-agent rubric covering:
  - correctness
  - proof choice
  - ownership choice
  - escalation correctness
  - retrieval efficiency
  - handoff continuity
  - scope discipline
- Structured result output for all three roles

### Exit criteria

- Benchmarks run without real human intervention.
- Human-role and judge-role behavior is stable enough to compare runs.

---

## Stage 4: Turn agent feedback collection into a standard review channel

### Objective

Collect practical “how useful is this product to me?” feedback from many different agents, not just benchmark scores.

### Deliverables

- A standard feedback prompt template for agents
- A normalized feedback output shape capturing:
  - overall verdict
  - strongest benefits
  - main friction points
  - discovery cost
  - handoff/restart quality
  - proof/trust quality
  - agent-agnostic fit
  - concrete improvements
- A lightweight clustering pass that groups feedback into repeated friction classes
- A rule for weighting feedback from:
  - strong models
  - cheap models
  - internal-delegation agents
  - no-delegation agents

### Prioritization rule

Prefer cheap/small-agent feedback when the failure is about:

- ambiguity
- discovery cost
- restart cost
- proof selection
- handoff
- plan curation

### Exit criteria

- The repo can compare agent feedback across multiple agent families in one common frame.
- Repeated themes emerge without manual synthesis each time.

---

## Stage 5: Weight weaker and cheaper agents deliberately

### Objective

Use the most informative failure signals, not just the most impressive agents.

### Rationale

A strong model can often compensate for product weakness.
A weaker model exposes:

- ambiguity
- hidden assumptions
- over-reading
- missing handoff state
- weak proof routing

### Deliverables

- A weighting rule for benchmark and feedback interpretation:
  - strong-model failures are high severity
  - weak-model ambiguity failures are also high severity
  - weak-model pure capability failures are lower relevance unless they map to product claims
- A benchmark report split by:
  - strong planner agents
  - cheap implementer agents
  - internal-delegation agents
  - non-delegating agents

### Exit criteria

- The evaluation loop prioritizes the failures most relevant to the product’s stated goals:
  - lower token cost
  - lower rereading
  - better handoff
  - less human micromanagement

---

## Stage 6: Connect evaluation output directly to bounded improvement lanes

### Objective

Prevent the evaluation system from becoming an isolated dashboard.

### Deliverables

- A bridge from benchmark/feedback failure classes into:
  - review findings
  - TODO candidates
  - roadmap candidates
  - contract cleanups
- A repeated-failure rule, for example:
  - one strong-model failure may justify action
  - one review artifact plus one weak-model repeated failure may justify action
  - repeated weak-model ambiguity failures across two agent families justify action
- A compact triage view showing:
  - repeated failure class
  - affected surfaces
  - likely remediation target
  - suggested bounded next slice

### Exit criteria

- Benchmark and feedback outputs naturally produce bounded product work.
- The system improves from repeated signal rather than from one-off anecdotes.

---

## Stage 7: Expand from frozen fixtures to real bounded repo work

### Objective

Move from purely synthetic evaluation toward realistic product stress.

### Sequence

Start with:

- frozen fixture repos
- narrow operational questions
- bounded restart/handoff scenarios

Then move to:

- cloned real repos
- mature-repo adoption/jumpstart
- small real issues
- bounded implementation tasks
- strong-planner / cheap-implementer relay work

### Deliverables

- A small curated set of real external repos for evaluation
- Selection criteria for real tasks:
  - bounded
  - inspectable
  - not legally or ethically problematic
  - not too noisy to score
- A rubric for what counts as useful external proof versus too much scenario noise

### Exit criteria

- The product has evidence beyond its own monorepo.
- Real-repo evaluation stays bounded and actionable.

---

## Stage 8: Add planning- and handoff-specific stress tests

### Objective

Focus on the areas where the product’s unique value should be strongest.

### Benchmark families

- active planning inspection without prose-first rereading
- proof-lane choice from compact selectors
- ownership lookup by path/concern
- interrupted-task restart
- planner-to-implementer handoff
- bootstrap-to-jumpstart continuation
- cheap-agent residue capture

### Deliverables

- Scenario families specifically targeting:
  - planning_record usefulness
  - report-first inspection
  - handoff artifact sufficiency
  - proof-route sufficiency
  - mixed-agent posture usefulness

### Exit criteria

- The repo can tell whether new compact/query-first/planning-state surfaces are actually reducing mistakes and rereads.

---

## Stage 9: Keep humans in the decision loop, not the execution loop

### Objective

Use agents heavily without giving away product judgment too early.

### Deliverables

- A short policy note stating:
  - agents may generate evidence, critique, candidate improvements, and comparative signals
  - agents do not autonomously decide roadmap direction
  - humans remain responsible for:
    - priority
    - product boundaries
    - concept count discipline
    - when to accept or reject repeated agent requests
- A review checkpoint for any improvement candidate generated mainly by benchmarks/feedback

### Exit criteria

- The loop is agent-driven in signal generation, but human-guided in product judgment.

---

## Stage 10: Make the loop continuous and cheap

### Objective

Turn the whole system into an ongoing self-improvement flywheel.

### Deliverables

- Scheduled or routine reruns of:
  - frozen benchmark suites
  - selected model-zoo feedback prompts
  - a small dogfooding audit
- Compact trend reports on:
  - repeated failure classes
  - agent-family improvement
  - read-cost changes
  - proof-selection improvement
  - handoff/restart success
- A regression rule that flags when:
  - concept count rises but measured operating cost does not fall
  - weaker agents get worse on routing/proof/handoff
  - humans are pulled back into repeated steering

### Exit criteria

- The repo has a sustainable self-improvement loop.
- Evaluation remains cheaper than the confusion and regressions it prevents.

---

## Recommended sequencing

### First tranche

1. Formalize dogfooding capture
2. Build the model-zoo benchmark lane
3. Add human-role and judge-role agents
4. Add structured feedback collection

### Second tranche

5. Add weighting for weaker/cheaper agents
2. Connect feedback and benchmark output to bounded improvements
3. Add planning/handoff stress tests

### Third tranche

8. Expand to real external repos and real bounded issues
2. Formalize human decision checkpoints
3. Make the loop continuous and cheap

---

## Immediate next actions

- Define the dogfooding failure taxonomy
- Freeze the first multi-agent benchmark families
- Create the structured human-policy spec
- Create the structured judge rubric
- Build the standardized agent-feedback prompt and output shape
- Run the first benchmark/feedback sweep across a small model zoo
- Cluster the first repeated failure classes and route one or two into bounded fixes

---

## Guardrails

- Do not let benchmarks drift into generic coding prestige tests.
- Do not confuse model weakness with product weakness unless the failure maps to product claims.
- Do not let agent suggestions become roadmap truth without human review.
- Do not optimize for strong models at the expense of weak-model clarity.
- Do not broaden real-repo evaluation before frozen fixtures and narrow scenarios are stable.
- Do not let the evaluation system grow larger than the product problems it is meant to solve.

## North star

A wide range of agents — especially smaller and cheaper ones — should be able to use Agentic Workspace to start, continue, hand off, prove, and finish work with less rereading, less ambiguity, and less human micromanagement over time.
