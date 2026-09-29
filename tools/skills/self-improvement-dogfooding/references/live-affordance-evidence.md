# Current live affordance observation

Observed 29 September 2026. **Completed and satisfied after bounded finding
triage.** Both fresh sessions completed, all four required interaction classes
were observed, migration and authority checks passed, and managed scratch release
and removal committed. The independent cleanup/release invariant passed. No
observer failure or unresolved material interaction failure remains in this run.

The raw scorer result remains **failed / affordance-finding** and is unchanged.
The standing assessment includes the receipt-based dispositions below; it does not
silently turn the detector green or infer success from final files alone.

## Exact subject and execution

- Clean standalone candidate `81776086fd4b34ffec06c56ab7027a30b3b62ac7`, version
  1.5.1, target `x86_64-unknown-linux-gnu`.
- Inventory SHA-256: `c75e8fa0d0799d52c092a9115e6f16b9436801cc5837605edd47d81242a83288`.
- CLI/core SHA-256:
  `434559e96fa926a6c1d61ad145a497fd4ccb1daeb00353200a27109275947b5b` /
  `8d3ef8dfb3aa9b613c33cff2d703e59feca43c4513b900cbdfcbe2b7f24cfdbc`.
- Local Docker Sandboxes on Windows, Linux guest evidence; Codex CLI 0.149.1,
  `gpt-5.6-sol`, medium reasoning, subscription OAuth. Two sessions, each bounded
  by 900 seconds and 128 product calls; elapsed time 1235.407 seconds.
- Immutable template: `sha256:a68b972a59148c6359ade441387159033f6d196d48aef9dda06d2d4bb26eb41e`.
- Recipe/scorer/actor SHA-256:
  `454ee81cda399fd71244f9bd40e735bfa2f9bbde327f620a740f540761181233` /
  `29b67cf14993243f405ad4dc52fbb8cfe59c113b4c3f1285ee63eea2d31477da` /
  `0fa471e9be23c495e32ec2e249a71a36bada28ddd0f86fb9b1908b657b71a349`.
- Observer SHA-256: `d022868794efe2c97a7e043e4faaf910cd4d24e095cd0f7b2ead98e9d050b5d9`.

## Repair and observed completion

The previous sandbox-global 128-call limit mixed setup and both actor sessions.
The repaired observer assigns 128 calls to each controller-started session, with
separate bounded setup. Only the root controller can advance the session. The
three-session maximum, time limits, aggregate 40 MiB receipt cap, earlier receipts
and first failure remain enforced. No allowance was extended during this run.

There were four setup calls, 62 preparation calls and 54 resumed calls. Trusted
receipts show routed restrictions, a composed action and its committed effect,
and fresh reentry. Scratch release committed at event 97, scratch removal at
event 105, and final Planning update at event 115 (zero-based actor events).
The independent recipe accepted scratch retirement and preserved release data;
settings, README, policy, notes and installed-subject checks passed. Both actors
reported completion, consistent with the independent checks. Sandbox cleanup
removed the runtime; the clean candidate build worktree was archived.

The existing socket regression was extended; all 73 focused transport, scorer and
consumer-journey tests passed. A separate real Linux socket exercise with a
synthetic product effect completed cleanup at cumulative call 129, enforced the
128-call session limit, denied actor reset and retained the first failure. That
control proves the transport boundary; it is not live product evidence.

## Findings and bounded disposition

The unchanged detector retained two findings, triaged within #3709:

- Event 5, repeated unchanged rejection: events 4 and 5 supplied empty stdin
  (`e3b0c442…b855`) with `--input -`. Trusted stderr reports `invalid-json`, EOF at
  line 1 column 0. This is expected rejection of malformed actor input. Subsequent
  valid input progressed; no native crash or unresolved resource failure follows.
- Event 24, exact offered-action rejection: the actor submitted `planning.create`
  without its original task context. The owner rejected it before effect as stale
  for the current task identity. Event 27 carried the context and committed the
  same action hash, `3a784aae476f7dace9b43b0692aa36b328b7876e07429fafb2bdf22ac55a6dec`.
  This establishes expected currentness enforcement and successful supported
  recovery, rather than an unconstructible offered action.

These recovered input errors remain visible as findings. Their bounded
dispositions, full trusted coverage, committed cleanup and independent checks
support satisfied current evidence under #3710's procedure. No detector rule was
weakened and no additional provider attempt was made after this result. Independent
PR acceptance and parent #3708 closeout remain separate obligations.

Reported session token totals were 5,038,135 and 2,289,875. Cache accounting and
marginal monetary cost remain unknown; Linux evidence makes no Windows-native or
minimal-toolchain claim.

## Preserved evidence

The current raw result remains outside the repository: SHA-256
`4265e5059d907663f4a1973c4566146237d3070afea526a067245fb469019977`.
Earlier failed results remain unchanged: `b01ca5be97fc5f1101f7647b4a544cbe8d0a0941ece3528fe2083ff88bd38e1e`
and `4ab48d7b88b3f685cc39c746f27be64f737f46cc893bb5bd3b44aff8290ff223`;
the first setup failure remains `99c2cd28aa1b9f1ce0336f0ae6ab7de2c1ebc8953b9796cbad608e802c5cf532`.
Earlier diagnostic identities remain in preceding note revisions and local files.
