# Turn useful lessons into lasting improvements

Use this reference when a saved lesson could be handled more reliably by a test,
tool, configuration rule or project document.

The goal is not to create another layer. Move the lesson to the place that can
apply it more reliably, verify the change there, then remove advice that has become
redundant.

| Saved lesson | Better long-term home | What must be true first |
| --- | --- | --- |
| Repeated mechanical mistake | Test, check, generator, command, configuration rule or code guard | The failure is understood and the new mechanism can prevent it |
| Useful repeated shortcut | Command, skill, runbook or helper | Several comparable uses show that the shortcut really helps |
| Human or domain rule | Project documentation, configuration, contract or architecture document | A current human/domain decision supports the rule |
| Repository-specific correction | Repository guidance or configuration | Evidence shows the rule belongs only to that repository |
| Interesting but unready improvement | GitHub issue or other improvement queue | More work is needed before changing product behaviour |
| Rationale that still prevents rediscovery | Memory | No stronger project mechanism replaces it yet |

A change is complete only when the target mechanism has actually been updated and
checked. Merely naming a better home for the lesson is not enough.

After the stronger mechanism works, reconsider the older saved lesson:

- **keep** it when it still adds information;
- **shorten** it when only some context remains useful;
- **replace it with a short pointer** when that genuinely saves lookup time;
- **delete it** when the new mechanism fully replaces it.

Do not keep duplicate instructions “just in case”. When there is no useful lesson
to apply, create no recommendation or extra record.
