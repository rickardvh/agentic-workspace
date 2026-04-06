# Roadmap

Last reviewed: 2026-04-06

## Purpose

Inactive long-horizon candidate work.

## Active Handoff

- The full Agentic Workspace design principles are now a canonical repo doc rather than attachment-only guidance, so future roadmap promotion and product-shape changes should be tested against that file explicitly.
- External entry, naming, architecture, maturity framing, and maintainer-boundary docs are now in a credible product shape.
- The stable package contract freeze tranche landed across explicit contract shortlists, runtime doctor and verify-payload reporting, and root workspace passthrough proof.
- The first-party module contract tranche landed across explicit descriptor metadata for lifecycle arguments, install signals, workflow-overlap paths, generated-artifact classification, and centralized descriptor construction.
- The current promoted tranche is module registry and capability model so the workspace layer can enumerate first-party modules and lifecycle support from one internal model instead of scattered lists and command-specific assumptions.
- A broader modular-platform vision now frames that maturity work as part of a larger outcome: Agentic Workspace should become a modular agent-ready platform with first-party managed modules, registry-ready orchestration, intentional composition, and a future extension boundary that still preserves strict ownership.
- Shared-tooling extraction remains a later support candidate inside the same maturity program, but only if duplicated checks and renderers still create sustained maintenance drag after the lifecycle and adoption phases settle.
- Promote the next candidate only when the scope is bounded enough for a short execplan and a narrow validation story.

Future promoted work should continue to pass the design tests in `docs/design-principles.md`: lower startup friction, reduce rediscovery, preserve ownership boundaries, stay quiet in normal use, and remain portable beyond this monorepo.

## Next Candidate Queue

- Module registry and capability model: make module discovery, lifecycle hooks, ownership surfaces, and capabilities explicit and queryable. Promote when the first-party module contract is stable enough that registry work will not be immediately redesigned.
- Composition contract hardening: define how modules interact, compose presets, and share lifecycle reporting without blurring ownership. Promote when multi-module installs still feel incidental rather than clearly intentional after the root lifecycle work lands.
- Extension boundary design: define the public plugin or external-module contract only after first-party module assumptions have stabilized. Promote when first-party modules themselves are using a sufficiently explicit module contract that could be versioned for external use.
- Shared tooling extraction: evaluate a common checker core when the first stable monorepo release exposes repeated maintenance friction across duplicated scripts. Promote when duplicated checker and renderer maintenance remains a higher cost than any unresolved product-contract ambiguity.

## Platform Vision Goal

- Evolve Agentic Workspace from two strong packages plus a thin composition layer into a modular platform for making repositories agent-ready, with first-party managed modules, clean lifecycle orchestration, and a future path to third-party modules or plugins.

## Platform Vision Outcome

- A repository can be made agent-ready through installable modules.
- Memory and planning remain first-party managed modules.
- The root tool orchestrates lifecycle and composition.
- Module boundaries remain real.
- Future modules can slot in without redesigning the core.
- Third-party extensions become possible through a stable module contract.
- The workspace layer remains a coordinator, not the hidden owner of all domain logic.

## Full Maturity Goal

- Bring Agentic Memory and Agentic Planning from real, dogfooded products to boring, trustworthy, and broadly adoptable packages while preserving strict module boundaries and keeping `agentic-workspace` a thin composition layer.

## Full Maturity Success Criteria

- Installs and upgrades are predictable and conservative.
- Partial adoption works reliably outside the monorepo.
- Generated surfaces are trustworthy and cheap to validate.
- Package contracts are stable enough that future changes mostly refine rather than redefine them.
- Dogfooding continues to improve the products without overfitting them to this repo.

## Maturity Phases

### Phase 1 - Make the workspace lifecycle the real entrypoint

- Finalise the root `agentic-workspace` lifecycle UX around `init`, `status`, `doctor`, `upgrade`, and `uninstall`.
- Keep preset and module selection clean for `memory`, `planning`, and `full`.
- Standardise machine-readable lifecycle reports and repo-specific handoff prompts.
- Preserve direct package CLIs for maintainers and power users.
- Done when new users can bootstrap from the root CLI without subdirectory-specific commands, existing repos are handled conservatively, lifecycle outputs are consistent, and the workspace layer still delegates module logic.

### Phase 2 - Formalize the first-party module model

- Define the shared internal module contract for first-party modules.
- Introduce module metadata such as module ID, maturity, owned surfaces, managed surfaces, generated surfaces, lifecycle capabilities, doctor/status hooks, and dependency or conflict declarations.
- Refactor workspace orchestration to use module adapters rather than special-case memory or planning logic.
- Make preset resolution data-driven from module declarations.
- Done when memory and planning are orchestrated through the same module interface, the workspace layer no longer needs bespoke branching per module, and adding a new first-party module does not require redesigning the core lifecycle flow.

### Phase 3 - Harden module boundaries and ownership rules

- Turn current boundary policy into an explicit module-system contract.
- Define what the workspace layer owns: lifecycle orchestration, module registry or discovery, preset resolution, shared reporting, and compatibility enforcement.
- Define what modules own: installed surfaces, domain semantics, generated artifacts, and their own drift checks.
- Add guardrails so modules cannot silently rewrite unrelated module state, generated artifacts derive from canonical sources, and the workspace layer does not hide module-owned mutations.
- Done when module boundaries are documented as platform policy, orchestration and module semantics are clearly separate, and future module work is forced through the ownership test rather than added ad hoc.

### Phase 4 - Turn memory and planning into boring first-party modules

- Build fixture coverage for empty repos, docs-heavy repos, repos with existing `AGENTS.md`, planning-like docs, memory-like docs, and existing contributor or command docs.
- Validate clean install, conservative adopt, prompt quality, and doctor/status usefulness for each target.
- Tighten preserve-versus-manage rules so repo-owned, package-managed, and refreshable surfaces stay explicit.
- Freeze the Agentic Memory installed contract around the note tree, manifest role, routing entrypoint, freshness expectations, skill ownership boundary, and improvement-pressure behavior.
- Freeze the Agentic Planning contract around `ROADMAP.md`, `TODO.md`, `docs/execplans/`, archive behavior, generated routing docs, planning-surface validation expectations, and thresholds for TODO-only versus execplan-required work.
- Done when memory and planning are stable, boring first-party modules with predictable lifecycle behavior and trustworthy generated or managed surfaces.

### Phase 5 - Build the module registry and capability model

- Add a module registry model for first-party modules.
- Track module capabilities such as managed-surface installation, generated-doc rendering, checks, status output, lifecycle hooks, ownership surfaces, dependencies, and conflicts.
- Add workspace commands or report paths that can enumerate installed modules and surface their capabilities.
- Make `status` and `doctor` module-aware through registry data rather than hard-coded assumptions.
- Done when lifecycle reporting becomes module-driven, installed modules and capabilities can be enumerated cleanly, and new modules can plug into the registry without redesigning core commands.

### Phase 6 - Support composition as a first-class product feature

- Define preset composition rules, including what `full` means and how composition handles generated artifacts and lifecycle reporting.
- Define cross-module integration contracts for how planning can reference memory, how memory can route from planning context, and how future routing or checks modules may interact without stealing ownership.
- Improve composed lifecycle UX with clear reports, composed handoff prompts, and module-aware upgrade or uninstall behavior.
- Done when composed installs are as understandable as single-module installs, module interactions are explicit, and full-stack use does not blur source-of-truth ownership.

### Phase 7 - Introduce new first-party modules only through the contract

- Define acceptance criteria for a new first-party module: distinct ownership boundary, independently meaningful capability, selective adoptability, and lifecycle hooks that fit the module contract.
- Use those criteria to evaluate candidates such as routing or checks.
- Keep candidate capabilities internal until their boundary is stable and repeated reuse pressure is proven.
- Done when new module proposals are evaluated against a written threshold and ecosystem growth happens through a controlled module pipeline rather than convenience extraction.

### Phase 8 - Design the extension boundary

- Define a public extension surface for external modules, including manifest schema, lifecycle hook interface, capability declaration, and compatibility/version contract.
- Define plugin safety rules so extensions cannot silently redefine precedence, mutate unrelated module state, or bypass owned/generated-surface declarations.
- Decide the extension loading model, such as installed package entrypoints, repo-local declarations, or explicit plugin registration.
- Done when third-party extension is possible in principle without weakening core boundaries and the public extension contract is explicit and versionable.

### Phase 9 - Prove external ecosystem viability

- Validate memory-only adoption, planning-only adoption, full-stack adoption, and at least one multi-module external repo using the root lifecycle.
- Capture adoption evidence about smooth composition, unclear boundaries, and lifecycle UX that still feels too monorepo-shaped.
- Refine the platform based on external use rather than internal elegance alone.
- Done when selective and composed adoption both work in practice and the platform model survives contact with repos that do not share this monorepo's habits.

### Phase 10 - Mature the platform as an ecosystem

- Publish a stable module-system charter.
- Publish compatibility policy for first-party modules and extension hooks.
- Keep root docs focused on how to adopt the platform, choose modules, and extend safely.
- Ensure lifecycle commands feel boring and predictable and dogfooding continues to improve the platform without overfitting it to one repo.
- Done when Agentic Workspace is clearly the umbrella product, first-party modules are mature and predictable, future modules have a real home, and the platform is extensible without becoming blurry.

### Cross-cutting maturity work

- Expand liveness validation for manifest-to-generated-doc consistency, startup-path consistency across maintainer surfaces, and rerender freshness after canonical changes.
- Mark generated surfaces prominently as generated and non-manual.
- Fail fast on safe drift and warn clearly where hard failure would be too aggressive.
- Keep one canonical source per generated surface.

- Publish compatibility promises for stable memory and planning surfaces once lifecycle, adoption, and module-contract behavior are no longer moving targets.
- Classify dogfooding friction as package defect, install/adopt issue, docs or routing issue, workspace orchestration issue, or monorepo-only friction.
- Route meaningful friction into roadmap, active plans, durable memory, or docs instead of chat residue.
- Prefer product fixes over monorepo-only workaround guidance when friction repeats.
- Keep the root README external-user-first and package naming/product naming stable.
- Sharpen package READMEs around fit, non-fit, solo use, and cross-package interplay.
- Done when generated surfaces are trustworthy, public docs stay compact, compatibility promises are believable, and repeated internal friction produces reusable product improvements instead of repo-local hacks.

## Release Gates

### Agentic Memory full-maturity gate

- Install, adopt, upgrade, and uninstall are boring and conservative.
- The memory contract is stable and documented.
- Selective adoption works in external repos.
- Improvement-pressure behavior has proven it reduces sprawl instead of only describing it.
- Future changes are mostly incremental refinements.

### Agentic Planning full-maturity gate

- The planning contract is stable and documented.
- Install and adopt work safely in messy repos.
- Planning-surface and generated-doc drift is tightly controlled.
- Task-size thresholds and archive behavior feel predictable.
- External adopters can use it without relying on monorepo habits.

### Platform ecosystem gate

- Agentic Workspace is clearly the umbrella product and default lifecycle entrypoint.
- First-party modules are mature, modular, and predictable.
- Module registry, capability reporting, and composition rules are explicit.
- New first-party modules enter only through the written module contract.
- The extension boundary is explicit enough that third-party modules are possible without weakening core ownership rules.
- External repos can adopt selective and composed module sets without relying on monorepo-specific habits.

## Sequencing Recommendation

1. Make the workspace lifecycle the default entrypoint.
2. Formalize the internal module contract.
3. Harden ownership boundaries as enforceable platform rules.
4. Stabilize memory and planning as boring first-party modules.
5. Add registry and capability-driven orchestration.
6. Make composition first-class.
7. Add new first-party modules only through the module contract.
8. Design the plugin boundary.
9. Prove the platform externally.
10. Publish the ecosystem as a stable modular platform.

## Compact Horizon View

### Near-term

- Make the root lifecycle around `init`, `status`, `doctor`, `upgrade`, and `uninstall` the default product entrypoint.
- Define the internal module contract and refactor memory/planning orchestration toward module adapters.
- Harden install/adopt behavior and ownership boundaries.

### Mid-term

- Stabilize memory and planning as mature first-party modules.
- Add module registry and capability reporting.
- Make multi-module composition first-class.
- Define acceptance criteria for future first-party modules.

### Later

- Design the public extension/plugin contract.
- Support safe third-party modules.
- Validate the platform in external repos using selective and composed adoption.
- Publish stable module-system compatibility and extension policy.

## Reopen Conditions

- Reopen roadmap planning when active queue completes or a new bounded candidate is ready to promote.

## Promotion Rules

- Promote candidate items only when active tranche dependencies are clear and bounded.
- Keep detailed execution in `docs/execplans/` once promoted.
- Prefer collaboration-safe installed-contract work over new top-level concepts when dogfooding shows concurrent-edit ambiguity or merge pressure.
