# Which AW components should I use?

Start with `agentic-workspace`. Enable Planning, Memory or Verification only when
that component solves a recurring problem in your repository.

AW itself can still be useful without any optional component: it can route the
agent to project instructions and skills, read current AW settings and support
controlled repository changes.

AW may be unnecessary when the repository is cheap to reread, tasks finish in one
sitting, and existing documentation and tests already preserve the important
rules.

For the product model, see [How AW fits into a project](package/overview.md). For
extension design, see [Modules](package/modules.md).

## Choose by the problem you actually have

- Use **Memory** when agents repeatedly rediscover useful repository facts,
  recurring traps, runbooks or subsystem orientation.
- Use **Planning** when unfinished work must survive interruption or handoff with
  its goal, constraints, progress and next step intact.
- Use **Verification** when the project benefits from reusable checking
  procedures, saved evidence or explicit known gaps.
- Use several when each independently saves enough future work to justify the
  extra state.
- Use AW without optional components when routing and repository guidance help but
  none of those three problems is significant.
- Use ordinary project documentation and tests alone when AW would cost more than
  it saves.

The current built-in components are examples, not a fixed list of every possible
future extension.

## Keep ordinary use simple

Installing a component should not make every task read its manual or follow a new
command sequence. The repository's startup skill remains the entry point, and AW
only shows component information when it matters to the current task.

Direct component commands and internal manifests are mainly for debugging,
maintenance or specialised integrations. Ordinary agents should follow the
specific action or reference returned for the task rather than reconstructing a
component workflow.

## Read next

- [Product overview](package/overview.md)
- [Modules and extensions](package/modules.md)
- [Integration boundaries](extension-boundary.md)
- [Your repository and AW files](package/installed-surfaces.md)
- [Memory](../packages/memory/README.md)
- [Planning](../packages/planning/README.md)
- [Verification](../packages/verification/README.md)
- [Architecture](architecture.md)
