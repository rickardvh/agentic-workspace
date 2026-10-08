# Repository instruction Markdown

This is the public format for creating or revising one AW instruction. The native
Markdown parser and public proposal remain the executable authority. A JSON
envelope schema does not validate the Markdown string it carries.

## Files and syntax

Use a direct `.md` file in either canonical instruction directory named in
[publication](publish.md). Discovery is not recursive and linked sources are not
admitted. Current discovery allows at most 64 sources and scans at most 256 total
directory entries. Publication requires nonempty UTF-8 content of at most 65,536
bytes; its source argument is at most 256 characters.

Without front matter, the entire Markdown body is global guidance. It does not
automatically become enforced policy. Optional front matter starts on the first
line with exactly `---` and ends with another line containing exactly `---`.
Only the eight fields below are supported, each at most once. Blank lines and
whole-line comments starting with `#` are accepted within front matter.

Each field takes an inline comma-separated list, or a block list:

```markdown
---
paths: [src/adapters/**]
governed_by:
  - docs/api-contract.md
---

Keep API adapters consistent with the existing API contract.
```

Inline entries may have surrounding single or double quotes. Block entries begin
with `-` and may be indented. This is constrained list syntax, not arbitrary YAML:
no scalar field values, nested objects, anchors, folded strings, inline comments
or escaping rules. Inline lists split at every comma, including quoted commas;
use block entries for a value containing commas. `[]` or an empty field supplies
no selectors or consequences. Do not use an empty scope to approximate a narrow
rule: absent or empty path/route lists mean unrestricted scope on that dimension.
Unknown or repeated fields and unterminated metadata are rejected. Preserve and
diagnose malformed sources rather than silently converting them into policy.

## Applicability and lifetime

`paths` lists repository-relative patterns for relevant changed paths or operation
targets. Entries in one list are alternatives. Matching uses fnmatch semantics:
`*` spans separators, `?` matches one character, and bracket classes such as
`[ab]`, `[a-z]` and `[!a]` are supported. `**` is not a separate recursive operator;
`src/adapters/**` is a useful prefix pattern. Matching follows host case
normalisation on Windows. Do not assume shell glob expansion or Git pathspecs.

`routes` lists exact semantic route identifiers, optionally ending in `/**` to
include that route and its descendants. An identifier has at least two slash-separated
segments. Each starts with a lowercase ASCII letter or digit and contains only
lowercase ASCII letters, digits or `-`. Select existing routes by current task meaning through public
semantic discovery/selection; do not fabricate them or infer selection from task
keywords. With both `paths` and `routes`, both conditions must hold. Missing or
stale selection can leave applicability unresolved; that is not a proven non-match.
Duplicate route selectors are rejected when applicability is resolved.
Do not add a route condition when path scope already expresses the intended rule.

Shared versus machine-local placement chooses lifetime independently of these
conditions. A local scoped rule can still apply to many paths; a shared rule can
be narrowly scoped. Neither placement grants additional authority.

## Context and consequences

| Field | Meaning and boundary |
| --- | --- |
| `read` | Deliver named repository resources as context for matching work. Reading alone creates no governance or proof obligation. |
| `governed_by` | Name governing files once and deliver their context. Verification requires current coverage of the instruction's consumer scope; source changes require reconsideration, not automatic consumer edits. |
| `reconcile` | Require a current Verification judgement of resulting work against named sources. Do not duplicate their policy or rewrite every consumer merely to record a judgement. |
| `use` | Prefer an existing skill resolved by its registered skill identifier or exact semantic route (optionally prefixed with `skill:`). An unresolved skill is a gap; preference is not execution, mandatory selection or permission. |
| `checks` | Require current evidence for the repository's real commands or declared requirements through Verification. Declaration is not execution or successful evidence. |
| `protect` | Restrict affected writes matching repository-relative patterns through current authority. It grants no writes elsewhere and does not promise a host-wide sandbox. |

`paths`, `read`, `governed_by`, `reconcile` and `protect` reject leading `/` or `~`,
backslashes, colons and any `..` path component. `governed_by` and `reconcile`
additionally require exact canonical relative file references: no glob characters
(`*`, `?`, `[` or `]`), empty or `.` components. Use existing readable files.
The parser's acceptance of a `read` entry is not proof that its resource resolves;
inspect returned context and diagnostics. Use exact file references for ordinary
context. `protect` uses the same pattern matching as `paths`.

For `checks`, inline or block strings name requirements; `requirement:<id>` refers
to a real repository Verification declaration. Only a block entry beginning with
`run:` declares a command, with a nonempty command following it:

```markdown
---
paths:
  - src/adapters/**
checks:
  - requirement:api_contract
  - run: python -m unittest discover -s tests
---

Verify adapters against the API contract before claiming completion.
```

This example assumes that requirement and command exist in the host. A command is
the rest of the `run:` line as written; do not wrap it in YAML quotes or expect a
multiline script. `[run: command]` is a string requirement, not a command object.
Do not invent requirements or import this example's test command into another host.

Fields compose: scoped context can accompany governance, checks or protection.
Keep only what the requested behaviour needs. `read` cannot stand in for
`governed_by`; `use` cannot stand in for evidence. Hard consequences require
current source admission and owner judgement. Inspect those separately from valid
syntax and applicability using [publication and inspection](publish.md).
