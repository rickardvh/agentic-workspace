# Installed entry evidence

This local record, dated 2026-09-30, separates observed checks from accepted
assumptions for issue #3729. The user explicitly directed finishing the work and
creating a PR while assuming Claude works. This supersedes the original
authenticated Claude session gate for this delivery; it does not turn that
assumption into observed host behaviour. The implementation and artifact checks
are complete. The host-session limitations below remain disclosed for review.

## Established boundaries

- One maintained bridge generates the npm skill and shared plugin skill byte for
  byte. Native plugin paths resolve inside the extracted marketplace. Portable
  and Claude manifests contain one skill and no other executable components.
- The actual dev-profile native npm staging and `npm pack` include the skill.
  The package has no self-referencing `skills` field or installer lifecycle hook.
- `skills-npm` 4.0.0 installed the packed declared source under npm 11.11.0 and
  pnpm 10.30.3 on Node 25.8.0. Neither operation created `AGENTS.md` or an AW
  enclave. Removing the dependency and declaration and resynchronising removed
  its exposure while preserving an unrelated skill. Clearing only the source
  declaration retained the installed package's cached skill; the user guide
  reflects this lifecycle boundary.
- Codex CLI 0.159.0 installed the local extracted marketplace through native
  `plugin marketplace add` and `plugin add`. Its selected task identified the
  installed bridge by name and cache path. This establishes discovery only.
- Claude Code 2.1.285 validated and installed the same marketplace with an
  isolated user profile. Plugin details reported one entry skill, zero agents,
  zero hooks, zero MCP servers and zero LSP servers. This establishes discovery
  only.
- Focused artifact tests validate generated parity, manifests, referenced paths,
  coordinated release archive identity/inventory and digest tamper rejection.
- Both isolated native profiles completed disable, enable, same-version update
  and removal. Codex's config disable was visible in native plugin listing;
  Claude's native commands succeeded. Hashes of all six synthetic working trees
  were unchanged. This proves local lifecycle preservation, not Git marketplace
  version movement or downstream use after removal.

## Host-session limits and accepted assumption

Real Codex selected use from a synthetic repository subdirectory did not reach
the canonical skill. The session reported environment policy blocking its
read-only cache read. Explicit access to the isolated profile and removing
inherited application session identity did not resolve it. Account-connected
remote plugin metadata was still visible, so these sessions cannot establish a
minimal tool profile either. No runtime command or repository mutation was
observed. A successful target-file trace is still required; recognition and a
zero session exit code are not handoff evidence. A final retry with the synthetic
fixture inside the task workspace produced the same policy rejection; changing
the fixture location did not establish handoff. No adapter workaround or hook
was introduced to bypass that rejection.

Claude's local authentication status was `loggedIn: false`; the user has a free
Claude account without Claude Code access. Selected Claude handoff and downstream
use are accepted assumptions for this PR, following the user's explicit
instruction. Native validation, discovery and lifecycle were observed separately.
Authentication is not copied into the deliverable or recorded here.

The two-repository revision/refresh, linked-worktree, absent/broken entry,
coexisting-entry, ordinary-task activation observation and post-removal fallback
controls could not be observed in the blocked Codex sessions. Synthetic fixture
construction is not behavioural
proof. These controls must use the installed bridge independently of the fence
where selected handoff is claimed. Native lifecycle operations are established
above; a real task through the generic fence after removal remains outstanding.

## Interventions and retained work

An extended-length Windows path caused an initial npm prefix failure. A retry
without an explicit prefix resolved to the existing home package rather than the
temporary tool directory. Thirty new packages and their shims were added with
`--no-save --ignore-scripts`; the existing declaration was unchanged. Corrected
installation uses an ordinary absolute path, an explicit prefix and a private
temporary package. Receipt- and creation-time-bounded removal of the accidental
additions was rejected by automatic approval review as blocked by policy. A short
single-path removal received the same rejection, so command length does not
explain it. The user removed `skills-npm`; 29 receipt-listed package directories
remain. Their cleanup remains unresolved; do not infer that the host was restored.

The temporary Claude optional native package required its own `install.cjs`
activation after installation with scripts disabled. No such hook was added to
AW. The first reused session harness omitted final text from its result, so raw
JSONL traces were captured before interpreting behaviour. The task's scratch was
initially retained while prerequisites were pending. After the user's submission
instruction, this finite record preserved the useful conclusions and limitations;
native `scratch-release` and `scratch-remove` both committed. Disposable staging,
raw traces, isolated profiles and the temporary authentication copy were removed
with that exact task container. No default host profile was changed. Do not claim
that unobserved handoff or automatic activation was established by these checks.

Formats were checked against the [OpenAI plugin format](https://developers.openai.com/plugins/build/plugins),
[Claude plugin lifecycle](https://code.claude.com/docs/en/plugins) and
[skills-npm source convention](https://github.com/antfu/skills-npm/blob/main/SPEC.md).
This finite record supplies no guarantee of automatic activation or enforcement.
