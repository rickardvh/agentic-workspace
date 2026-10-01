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

## Initial host-session limits and accepted assumption

Initial Codex selected use from a synthetic repository subdirectory did not reach
the canonical skill. The session reported environment policy blocking its
read-only cache read. Explicit access to the isolated profile and removing
inherited application session identity did not resolve it. Account-connected
remote plugin metadata was still visible, so these sessions cannot establish a
minimal tool profile either. No runtime command or repository mutation was
observed. A successful target-file trace was still required; recognition and a
zero session exit code are not handoff evidence. A final retry with the synthetic
fixture inside the task workspace produced the same policy rejection; changing
the fixture location did not establish handoff. No adapter workaround or hook
was introduced to bypass that rejection.

The user identified that the original installed skill path was 266 characters,
above the traditional Windows maximum path length. Two further selected-use
retries used an isolated profile with a 173-character installed skill path.
This task read that exact file successfully. The child CLI still rejected
PowerShell and `cmd` reads before process launch with `blocked by policy`.
The second retry also removed inherited application task-identity metadata,
while preserving the permission profile and approval settings, with the same
result. The original long path was a valid concern, but shortening it did not
resolve the remaining failure. The tool supplied no specific policy rule or
evidence that path length caused that rejection.

Inspection prompted by the user's permission question found a harness mismatch.
Both short-path rollouts recorded an effective managed `read-only` policy with
root read access, restricted network and approval `never`, despite the launch
argument `--sandbox workspace-write`. The isolated config explicitly selected
`read-only`; it also omitted the default host's `[windows] sandbox = "elevated"`
setting. The parent task had `danger-full-access`, so inherited permission
metadata did not establish identical effective permissions. Read-only access
should still permit the attempted read. `codex doctor` reported the isolated
restricted sandbox as healthy and supplied no specific launch-failure cause.
The effective-policy mismatch is a diagnostic lead, not a proven explanation.

Claude's local authentication status was `loggedIn: false`; the user has a free
Claude account without Claude Code access. Selected Claude handoff and downstream
use are accepted assumptions for this PR, following the user's explicit
instruction. Native validation, discovery and lifecycle were observed separately.
Authentication is not copied into the deliverable or recorded here.

## Windows harness investigation and observed Codex handoff

Direct native `codex sandbox -P :read-only` reads failed with Windows access
denied in the original temporary fixture but succeeded for the checkout's
`LICENSE`. Both the original `.git` fixture and a subsequent ordinary-root
fixture created with Python `tempfile.mkdtemp()` had protected directory ACLs
granting only owner, SYSTEM and Administrators. The normal checkout also grants
`CodexSandboxUsers` access. Fresh disposable fixtures created with ordinary
directory inheritance allowed the sandbox to read their input and installed
skill. The authentication copy retained the original authentication file's ACL;
no existing fixture or repository ACL was broadened.

Model-driven reads still rejected before launch until the isolated profile
explicitly selected `[windows] sandbox = "elevated"`. That change reached native
sandbox startup, which reported a missing or incompatible setup marker and
raised UAC. The bounded attempt ended with
`orchestrator_helper_launch_canceled: ShellExecuteExW failed to launch setup helper: 1223`.
Using the host's already provisioned sandbox then completed the same model-driven
read with exit zero. These checks identify two harness prerequisites; unrestricted
model command access was not needed and no rejection was bypassed.

Codex CLI 0.159.0 then installed the marketplace and entry through native commands
in that provisioned host profile. Both registrations were absent before the test.
Each model session explicitly set `sandbox_mode="read-only"`, retained approval
`never`, and used the configured model. Completed command traces, rather than
model claims or session exit codes alone, establish these results:

| Control | Observed result |
| --- | --- |
| Selected bridge from A subdirectory, no fence | Installed cache skill read, Git root A resolved, canonical skill and its relative reference read, `ENTRY-A1`, then sample summarized. |
| Different repository B, same installed bridge | B's canonical reference supplied `ENTRY-B1`. |
| Refresh A alone | A supplied `ENTRY-A2`; a fresh B session still supplied `ENTRY-B1`. |
| Linked-worktree subdirectory | Linked `.git` file resolved its own root and `ENTRY-A1`, while main A already had `ENTRY-A2`. An initial harness attempt used an absent empty subdirectory; it was created before the successful retry. |
| Absent AW | Checked local context, summarized the sample quietly; no install, setup or runtime probe. |
| Broken entry | Reported the target's missing canonical skill path without claiming successful entry or attempting repair. |
| Coexisting fence and selected bridge | Both entries were used; one canonical skill read supplied `ENTRY-F1`. |
| Ordinary prompt, plugin installed, no fence | `Summarize sample.txt. Keep the task read-only.` read only the sample. Neither bridge nor canonical entry was activated. |
| Native plugin and marketplace removal, fence fallback | Fresh session read canonical skill and relative reference via repository instructions, supplied `ENTRY-F1`, and summarized the sample without reading the removed bridge. |

All six synthetic Git working trees remained clean after the controlled A refresh
was committed. Native removal restored the host configuration semantically,
including unrelated settings. No model session wrote repository files or invoked
an AW runtime. The installed skill SHA-256 at the end of bridge controls was
`9f3c337797d489d12af751557ae0f93ce656bd9c11447d1a8e438b0beab7203b`.

This established selected Codex handoff and shared bridge controls on the
provisioned host. At that point the isolated-profile use observation remained
outstanding, so the PR stayed draft without a closing reference. The following
bounded exercise resolves that remaining observation. Claude authenticated
behaviour remains the user's accepted assumption. Ordinary non-activation remains
a disclosed limit of the passive adapter, not a reason to add activation hooks.

## Completed isolated Codex use and removal

The isolated profile's native `configRequirements/read` returned
`requirements: null`. No managed elevated-only restriction was configured.
After the elevated setup failure, this profile used the documented
`[windows] sandbox = "unelevated"` fallback. The
[Windows sandbox documentation](https://learn.chatgpt.com/docs/windows/windows-sandbox)
describes its restricted-token and ACL boundaries and its weaker network isolation
than the elevated implementation. This exercise establishes behaviour under that
supported fallback; it does not establish successful elevated provisioning.
Read-only permissions and approval `never` remained unchanged. Inherited security
metadata was preserved; no policy-bypass flag or adapter change was introduced.

Codex CLI 0.159.0 natively installed the entry into the isolated profile's cache.
The installed skill SHA-256 was again
`9f3c337797d489d12af751557ae0f93ce656bd9c11447d1a8e438b0beab7203b`.
Three fresh sessions using the configured model completed with exit zero. Their
saved turn metadata confirms `sandbox_policy.type = "read-only"` and approval
`never`; their completed command traces establish the following observations:

| Isolated-profile control | Observed result |
| --- | --- |
| Selected entry from A subdirectory, no fence | Five successful commands read the installed cache skill, resolved A's Git root, read its canonical skill and relative `ENTRY-A2` reference, and read the sample. Exactly one bridge and one canonical read. |
| Ordinary task with plugin installed, no fence | One successful sample read; zero bridge or canonical reads. Automatic activation remains unproven and was not forced. |
| Native plugin and marketplace removal, fresh fence fallback | Three successful reads supplied the canonical skill, relative `ENTRY-F1` reference and sample; zero bridge reads. The generic repository entry remains usable after removal. |

All six fixture working trees remained clean. Native removal left no AW entry
registration in the isolated profile; the temporary authentication copy was
removed and its absence verified. The default host profile was not modified in
this exercise. Earlier isolated install/load/disable/enable/update observations
and the shared target/currentness controls above are reused rather than repeating
the host matrix. The required isolated Codex use observation is now supported;
ordinary current CI and externally initiated independent recheck remain separate.

## Git update correction after independent review

The original source manifests pinned Claude's Git cache to `0.0.0-dev.0`.
The checked-in Claude manifest and marketplace entry now omit their version.
Coordinated release staging still stamps both with the explicit release version;
the portable Codex manifest retains its required distribution identity.

Claude Code 2.1.285 installed a native Git marketplace at fixture commit
`e081fd7598ab5426eb9be95284ef3743e923fbd2`, then refreshed the marketplace and
updated the plugin after the bridge bytes changed at
`b33d875a1a423d435db97531969f40c9deb13f24`. Its installed cache identity advanced
from `e081fd7598ab` to `b33d875a1a42`, and the installed skill bytes equalled
revision B. Native uninstall and marketplace removal succeeded. No authenticated
model session was required for this cache check.

The fixture used a Git-source HTTPS URL with subprocess-only Git `insteadOf`
transport to a local bare remote. This exercised native cloning, fetching and
Git cache identity, rather than local-directory marketplace behaviour. The CLI
rejected a direct `file:` marketplace URL. A profile under the scratch path then
hit Windows Git path limits; the successful fixture used a shorter isolated
profile inside its temporary Git fixture. No user's Git configuration or default
Claude profile was changed. Source/release projection tests now guard both the
absent Git version overrides and explicit archive versions.

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

The subsequent short-path check also removed its native plugin and temporary
authentication copy, and native scratch removal committed. Automatic approval
review rejected recursive removal of its temporary Git fixture directory with
the generic reason `blocked by policy`. That disposable fixture remains under
`.git/ep-bzv601k8`; its authentication file is confirmed absent. No specific
rejection rule was supplied.

The permission investigation also removed both new isolated plugins and their
authentication copies. Recursive cleanup of `entry-probe-1g_tf9x3/` and
`entry-check-aea64171/` was rejected by automatic approval review with only
`blocked by policy`; both directories remain. Their authentication files are
confirmed absent, and the failed elevated setup's `.sandbox-secrets` directory
is empty. The provisioned host's test plugin and marketplace were removed through
native lifecycle commands, and its configuration equals the pre-test semantic
snapshot. The evidence above preserves the finite trace conclusions; native
scratch removal for this investigation also committed.

Formats were checked against the [OpenAI plugin format](https://developers.openai.com/plugins/build/plugins),
[Claude plugin lifecycle](https://code.claude.com/docs/en/plugins) and
[skills-npm source convention](https://github.com/antfu/skills-npm/blob/main/SPEC.md).
This finite record supplies no guarantee of automatic activation or enforcement.

## Repository scope exercise for #3737

On 1 October 2026, Codex CLI 0.159.0 and Claude Code 2.1.285 used isolated
profiles and three temporary Git repositories: X and Y adopted AW; Z did not.
Configuration published only repository catalogues and enablement. The ordinary
user profiles were unchanged. These observations distinguish host discovery,
cached bytes, enablement and explicit selected use.

Codex's app-server `plugin/list` with explicit `cwds` and local marketplaces
reported each repository's distinct selector as installed and enabled. Its
`skills/list` returned the entry from that selector's host cache. Z returned no
AW marketplace or entry skill. The CLI's `plugin list` omitted repository
context, so it was unsuitable evidence for this boundary. The isolated user
configuration had trusted repository declarations and no plugin enablement.

A selected `$agentic-workspace-entry:agentic-workspace-entry` task started in
X's subdirectory, read the cached bridge, resolved X's Git root, read X's
canonical startup skill and its relative witness, then read X's sample. The
reported markers were `REPOSITORY-X-R1` and `X-SAMPLE`. The recorded model was
`gpt-6.1-sol`, with read-only policy, approvals disabled and the Windows
unelevated sandbox. This supplies selected handoff evidence, not automatic
activation or stronger sandbox provisioning evidence.

Claude local marketplace registration and project installation returned
`scope: project`, `enabled: true` and `projectEnabled: true` in X. Y's entry was
inactive there. A fresh collaborator profile initially listed no installed
plugins, and installation failed before local registration. Registration and
project installation succeeded without changing X's shared enablement. Switching
Y through Configuration removal to explicit local exposure left no shared
settings file; local settings were Git-ignored and native listing returned
`scope: local`, `enabled: true`. Z reported every installed AW entry disabled.
The isolated user profile had no user-level enablement settings. Claude itself
retained machine-local catalogue paths and downloaded bytes in its host cache.

X's bridge and canonical witness then advanced to R2 while Y stayed at R1.
Claude's returned marketplace-update and project-plugin-update commands produced
cached X bridge bytes equal to R2 and left Y's cache unchanged. Codex catalogue
refresh initially retained the old bytes when the manifest version was unchanged.
Changing X's version refreshed its cache without changing Y. A development
version with the bridge digest (`0.0.0-dev.0+3d1a41693f9eadee`) was also accepted
and cached correctly. The source generator now assigns development bridges a
content identity; explicit release staging retains its release version.

Removing X's Configuration-owned exposures made Codex's repository marketplace
list empty and Claude's cached entry disabled. A subsequent Codex task using
only the generic `AGENTS.md` pointer followed canonical startup and reported
`REPOSITORY-X-R2` and `X-SAMPLE`. Host-owned inactive caches remained. The
unchanged bridge's linked-worktree resolution evidence from #3729 above is
reused; no new bridge procedure was introduced.

The new deterministic fixtures cover all three scopes, unrelated settings,
matching unowned collisions, changed owned fields, local-ignore requirements and
refusal to expose tracked local settings,
interrupted publication, two independent repositories and exposure-before-bundle
removal. The retained released Configuration assessment initially blocked
source provenance reconciliation. A bounded native reassessment now checks the
development declaration, exact installed package bytes and prior record before
offering a current semantic assessment. Unknown records and newer installed
packages remain protected. The owner committed this checkout's reassessment and
its separate exact provenance reconciliation. Deterministic coverage exercises
both repository and machine-local assessment scopes, stale observations and
preservation guards.

### Review repair: repository Claude marketplace declarations

The initial Claude observation above used manual local marketplace registration.
The reviewed implementation now owns both `extraKnownMarketplaces` and
`enabledPlugins` in the selected project/local settings file, with directory
source `./.agentic-workspace/plugins`. This replaces the manual registration step
in the ordinary repository path; no scoped marketplace command is returned.

On 2026-10-01, isolated profiles and new adopted repositories exercised Claude
Code 2.1.285 for the initial project startup and 2.1.286 for the fresh collaborator
and local checks. Interactive startup accepted each disposable repository's trust
dialog and registered its relative directory declaration without `marketplace
add`. No model prompt was submitted; a synthetic API-key fixture allowed startup
without copying account credentials. These observations establish settings and
plugin lifecycle, not model-selected use or remote policy readiness.

The fresh collaborator initially listed no installed plugins. After trusted
startup, marketplace listing resolved the shared relative declaration to that
collaborator's checkout, while installed-plugin listing remained empty. Explicit
`plugin install <selector> --scope project` then reported project scope, enabled
and projectEnabled. The original profile also reported project enablement. Local
startup read the declaration from ignored `.claude/settings.local.json`; explicit
`--scope local` installation was enabled only in that repository, with no shared
settings file. The profile's other repository entry was disabled there, and both
profiles reported every AW entry disabled in the unrelated repository. Neither
profile had user-level AW marketplace declarations or enablement.

Shared and local settings retained the relative source after host installation.
Authenticated Configuration removal deleted both owned settings fragments and
native listing reported disabled entries in the removed repositories; host cache
bytes remained. Deterministic coverage additionally preserves unrelated
marketplace declarations and rejects matching unowned or edited owned declarations
in both scopes. Full API introspection has a bounded, named plugin-schema
allowance; optional discovery and effect revision appear only in selected setup
or an actual proposal, preserving the existing ordinary-response budgets.
