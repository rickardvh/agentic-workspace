# Select the instruction authoring need

```agentic-procedure
{
  "kind": "agentic-workspace/procedure/v1",
  "id": "instruction-authoring-need",
  "question": "Does the requested rule need scope and field shaping, or is its Markdown ready for publication and inspection?",
  "branches": [
    {"id": "format", "description": "Choose valid Markdown and the smallest intended applicability and consequences", "next": "references/format.md"},
    {"id": "publish", "description": "Preview, publish or revise one source, recover an interrupted write and inspect its effect", "next": "references/publish.md"}
  ]
}
```

Select from the accepted request and current sources. Selection supplies a method,
not publication authority or successful evidence.
