# System Intent

Agentic Workspace exists to let an agent answer three questions from current,
owned repository state: what is true, what may happen next, and what can be
claimed afterward.

The v1 invariant is:

```text
relevant source owners -> one operating decision -> one typed operation
-> typed result -> source-owner reconciliation -> next operating decision
```

Views may select detail but never change decision identity, action, status, or
claim authority. Direct work remains direct. Durable state exists only for a
domain owner with durable value. Unknown repository content is never treated as
package-owned or removed by convenience.
