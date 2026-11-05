---
name: workspace-change-design
description: Choose a maintainable change when responsibility, dependencies, consumed behaviour or stored data are at stake.
---

# Choose a maintainable change

Use this method when a choice can materially affect who owns a behaviour, what
the project depends on, or what callers or stored data can rely on. Use it before
committing to the choice, even when it surfaces partway through a clear task.
Reuse what you already know when the relevant sources and assumptions still apply.

Start with the requested outcome and the behaviour that must hold. Minimise the
cost over time of failures and of understanding, changing, operating and
verifying the result. Treat applicable user, repository and host requirements as
constraints. Apply a different local method when its authority and scope cover
the choice. This guidance is readable directly and grants no permission, proof
or exception to workspace restrictions, including explicit disablement.

When adding, replacing, removing or materially updating a package or toolchain,
consult [dependency choices](references/dependencies.md) before committing.
Routine use of an established dependency can proceed with the current setup.

- **Find the existing responsibility.** Read the implementation, governing
  source and nearby callers relevant to the choice. Prefer changing the
  component that owns the behaviour over teaching each caller another version
  of it. A coherent fix can span several necessary files. Keep discovery and
  cleanup within the task.
- **Share a responsibility when its rules and lifecycle are shared.** Keep
  similar code separate when its meaning or reasons to change differ. Add a
  boundary for a current need such as isolating an external system, expressing
  a shared rule or supporting known variation. Prefer explicit data flow,
  readable names and visible failures. Consider runtime cost where it affects
  the outcome.
- **Finish the replacement within scope.** Move the behaviour and its users
  before removing the superseded path. Keep a bridge for an identifiable
  consumer or transition, and record its exit condition in existing guidance
  when someone will need it. Check consumers, retained evidence and user data
  before deletion. Local reference searches cover only the sources they can see.
- **Update the authoritative source.** Change the contract, documentation or
  generator that defines the changed behaviour. Regenerate affected outputs with
  the repository's method and keep intentionally distributed copies coherent.
  Extend existing guidance where it can hold the lasting information.
- **Preserve trust and recovery boundaries.** When handling untrusted input,
  secrets, permissions, external effects or stored data, find the applicable
  protections and recovery path before acting. Keep checks and credentials
  protected. Establish how external effects or data can actually be recovered
  before promising rollback.

Use [proof selection](../workspace-proof-selection/references/select.md) for the
changed failure risks. Stop when the requested behaviour is supported by
adequate evidence and the affected sources agree. Carry a consequential
unresolved fact or tradeoff in the existing task or PR when review or follow-up
depends on it. Ordinary reversible decisions need no separate record.
