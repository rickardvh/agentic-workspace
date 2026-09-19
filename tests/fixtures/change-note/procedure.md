# Change visibility

Compare the observed patch with the stated intent. A change to a public result,
input, error or interaction is user-visible. A refactor preserving those is
internal. If evidence is insufficient, return unknown and request the missing
information instead of guessing.

```agentic-procedure
{"kind":"agentic-workspace/procedure/v1","id":"visibility","question":"Does the observed change alter behavior visible to a user?","branches":[{"id":"visible","description":"Public behavior changes","next":"user-note.md"},{"id":"internal","description":"Behavior is preserved","next":"internal-note.md"}]}
```

Manual alternatives: [user-visible](user-note.md), [internal](internal-note.md).
