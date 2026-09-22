# Everyday use

Once AW is [installed and added to your repository](agentic-workspace-install.md), give your agent ordinary tasks. The repository's `AGENTS.md` entry points to the AW skill, which explains when to read saved context or use a tool. You do not need to run a command sequence around every edit.

## Make a normal change

State the result you need and any constraints the agent cannot infer from the repository.

> Add pagination to the users API. Preserve existing response fields and show which compatibility checks passed.

In a repository with API guidance configured, the agent can find that guidance and the relevant checks. It still chooses the implementation and uses its normal development tools. AW does not discover an unwritten requirement by itself; establish missing project rules through [configuration](customization.md).

For a typo, a direct edit and proportionate checking may be enough. Plans, retained lessons and delegation are optional aids, not evidence that the agent used AW properly.

<a id="continue-work-or-receive-a-worker-result"></a>

## Stop and continue later

Before ending a session with unfinished work, ask:

> Preserve the intended outcome, accepted progress, important decisions, unresolved questions and next step so another session can continue this task.

Planning can keep that continuation with the repository. Check that it describes the remaining work, not just a history of completed actions. Commit shared records together with the work they describe; machine-local execution evidence is not automatically portable.

In the next session:

> Find the saved pagination task, check whether its assumptions still hold, and continue from the next unfinished step.

A fresh agent should identify the relevant task rather than assume the last saved plan is today's assignment. If it cannot establish whether an interrupted action took effect, it should investigate or recover that action before repeating it.

<a id="a-scoped-repository-rule"></a>
<a id="configuration-without-protocol-copying"></a>

## Correct the agent

Make the lifetime of your correction explicit:

> For this change, keep the existing error wording.

> For future work anywhere in this repository, read the API contract before changing a public response.

> Only on this machine, use this executable location.

The first request can remain task-local. The others belong in shared or local instructions/configuration. Ask where the correction was saved and inspect the resulting change. A promise in chat is not persistence. [Configure your project](customization.md) shows the supported destinations.

## Delegate a bounded task

Describe a result that can be checked independently:

> Ask another agent to inspect the pagination patch for compatibility problems. Give it the API contract and patch, request findings with evidence, and do not let it modify the repository.

Delegation depends on the available host and configured transport. A manual handoff is a valid alternative when automatic execution is unavailable. The receiving agent needs the scope, relevant sources and expected return, not necessarily the entire parent conversation.

When it returns, the responsible agent still checks the result and integrates any changes. Receiving a patch or review-like report does not by itself establish independent approval.

## Check the result

Ask what was checked, against which revision, and what remains unverified. Verification can retain reusable checking procedures and evidence; your repository must supply its actual proof requirements.

A previous passing result may be reusable when its relevant dependencies are unchanged. It is not fresh evidence for different code merely because it has the same test name. Human review and explicitly required checks cannot be replaced by a favourable summary.

<a id="preserve-a-useful-lesson-or-decision"></a>
<a id="improve-a-method-within-current-authority"></a>

## Keep something useful from the work

Retain information when it is likely to change a future decision:

> Save the cause of this non-obvious failure and the conditions under which the workaround applies.

Memory can preserve that as advice. A binding project decision belongs in the project's decision records or policy; a repeatable method belongs in a skill. Correct the source of a deterministic defect rather than leaving a permanent warning about it elsewhere.

It is also reasonable to retain nothing: code, tests and the PR may already explain the result adequately.

<a id="read-with-repository-access-only"></a>

## Work with a repository-only reviewer

A reviewer without executable AW can read the same main skill and follow the relevant references in `.agentic-workspace/READING.json`. It can inspect recorded intent, progress and lessons. It cannot establish current machine state, available credentials or newly passing tests from those files.

For saved files, see [Your repository and data](package/installed-surfaces.md).
For failures, see [Troubleshooting](troubleshooting.md). Direct CLI operation is
an [integration and debugging reference](reference/native-cli.md).
