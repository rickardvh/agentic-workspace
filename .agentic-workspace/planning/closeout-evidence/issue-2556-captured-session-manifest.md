# Issue #2556 captured-session manifest

This stable derived manifest describes the original dogfooding capture at `.agentic-workspace/local/logs/aw-session-20260814170232-7b3b8508/session.md`. The boundary is the first 164 entries classified as live-agent Agentic Workspace commands; the last included timestamp is `2026-08-15T10:53:00.856850+00:00`. Session-log analyzer entries are excluded. Grouping byte-identical command text at that boundary yields exactly 20 repeated shapes.

Issue #2556 is the authoritative aggregate snapshot: about 4.48 MiB of AW output, 13 duplicated output digests, 28 commands over 10 seconds, and 28 outputs over 50 KiB. Three identical `closeout_trust` calls totaled 708,406 ms (maximum 264,258 ms); one selected Planning summary took 208,532 ms; the largest selected proof response was 360,795 bytes.

## Repeated command shapes

The SHA-256 values are derived from the complete byte-identical command text in the local source. Together with count and class they provide stable identities without copying machine-local artifacts into checked-in evidence.

| Count | SHA-256 | Command class |
| ---: | --- | --- |
| 9 | `da61ecee430ab14c0ec27826ee94772cb5b191ebbd1e3f7e180205cf09c7f500` | summary |
| 7 | `c8316573206552940d6086a5dfa9a702bffc999f99726e68f3ffa12dc64026f3` | closeout_trust |
| 5 | `f38605be9575f488e5f712c01c2e56ffec8501bb42e15bfd274bee1e4e493e54` | summary_selected (continuation_view) |
| 4 | `ae5ef6c5920c8e180ae1f32026fd0543df52aeab802dcbb6fe2e302223a85092` | report runtime_mirror_consistency |
| 4 | `3f6a57fe2ecd7cb9ef943d5630de338d709b0dbc7f2b2554b96ee567e9f17e78` | report verification |
| 3 | `4c0aead1f2dd8194102d42e9be1e4df339903faf102269e29d11b5276f1b7540` | proof generated Python CLI |
| 3 | `7cc46e3f588657b2729658d9824d37b22370b71fbc62fc5a7d56921ccd8634af` | proof_selected evaluation route |
| 3 | `3964d694c4c83031793436ce17654e6da5bf3bda29b60a219e48516a635e08f5` | start cohesive open-issues task |
| 2 | `c6eb5156ff473a8f8786cea6c438a0f1dfc8b5631f78f5fc190a6061ed775423` | defaults root_cli_authority |
| 2 | `aa8e73919e22501fdb7cf5f0576928c36cf27d2b841247dda475dd1b63a1b615` | doctor planning |
| 2 | `9a8a585bb9ee4d8a809f021e57ed8e03734b14e33f7c48dacf850458a6c62df3` | evaluation status help |
| 2 | `6b3c1189d82cd4e3422a8a81e464b900af2cbff19327612ac73e8e6f47babe0d` | modules |
| 2 | `86a5baadbdf529d306193a86526a040734e25d6b1e595a0753270ba60aeb591b` | planning closeout dry run |
| 2 | `9268c5b78e5cc3a534e0d6e78c97a346981e410459b8b1c18b657beced00311b` | planning owner-select |
| 2 | `f0a5de040303bf1c68173b3a56f0f96c0a68dbd0fd86978c337e01f1b4d84dcc` | proof_selected startup/migration cohort |
| 2 | `88e14603dd8a7b4d2ee03ec5c6e68203569d05653ab9e1e249232f907d7c0fa9` | report improvement_intake |
| 2 | `d966bc974e15fcf8f661669960289731b678a3f67f78cb048656b85f99c5e802` | session-log status |
| 2 | `33086b657085021f0f018ca387d6ac302bb5ad897391de6379db7b9d6a0d7fb3` | start address-comments task |
| 2 | `69e6c28e9223e16203fff0fb9d4276204e72d5a6e38f3664d3401784cc8688ce` | start implement-open-issues task |
| 2 | `37f96893ba7ce19c829def3f853621cb0ab14c353c26497598e7c23bcba296d8` | start_selected implement-open-issues task |

## Representative replay mapping

| Replay fixture | Captured class mapping |
| --- | --- |
| start | Captured start/start_selected shapes `3964d694c4c83031`, `33086b657085021f`, `69e6c28e9223e162`, and `37f96893ba7ce19c` |
| summary_selected | Captured selected Planning-summary shape `f38605be9575f488` |
| implement | Captured implement class; 24 commands were task/path/selector variants, so no byte-identical implement shape repeated |
| proof | Captured proof/proof_selected shapes `4c0aead1f2dd8194`, `7cc46e3f588657b2`, and `f0a5de040303bf1c` |
| closeout_trust | Captured selected-report shape `c831657320655294` |

The replay deliberately represents the captured semantic command classes rather than claiming its final ten invocations were the original session. Cold/warm measurements remain in `issue-2556-projection-reuse.closeout.json`.
