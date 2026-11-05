# Evolve a contract

Use this reference with the [change-design method](../SKILL.md) when changing
consumed behaviour or retained data. A private change that ships atomically can
stay on the common method when it has no affected consumer or retained state.

- **Find what consumers rely on.** Read the governing contract, support policy
  and relevant callers, generated clients, scripts or saved records. An API,
  CLI result, event, configuration file or stored record can carry a contract.
  Separate components that ship together from independently updated readers
  and writers. Usage shows possible impact. The actual support promise and
  task authority determine what must be preserved or may change.
- **Check the dimensions that can change.** Consider source and build
  compatibility, binary compatibility where relevant, wire formats, behaviour
  and persisted data. A strict reader may reject an extra field, and an
  exhaustive client may fail on a new enum value. A record can still parse
  while a default, unit, order, error, null or side effect changes its meaning.
  Use the actual format and consumers to decide which risks matter.
- **Choose preservation or an authorised transition.** Preserve supported
  behaviour where required. If support is unclear, use the available evidence,
  prefer a bounded compatible choice where practical and state any uncertainty
  that matters. Local search cannot establish that external consumers are
  absent. Seek an owner decision if a consequential break needs authority.
  Make an authorised break explicit, update consumers in scope and follow the
  repository's release and support process. Necessary security tightening can
  change behaviour. Describe the impact and use the applicable authority.
- **Account for coexistence and recovery.** If versions overlap, work through
  the relevant old and new readers and writers, rollout order, retries and
  partial failures. Check representative old records and what conversion
  could lose. Stage an additive transition when it helps independently
  deployed components coexist. Use the actual data recovery or forward repair
  path. A code revert can restore the old implementation while leaving new
  writes that it cannot read.
- **Keep the transition and its sources coherent.** Keep an alias, adapter
  or dual read for a specific consumer or transition. Record when it can
  be removed in existing guidance if someone will need that decision.
  Update the authoritative contract, regenerate affected outputs and update
  migration or release guidance when required. When removal is authorised,
  retire superseded behaviour and its guidance together.

Use [proof selection](../../workspace-proof-selection/references/select.md)
to check the relevant consumer or transition with representative old inputs,
records or independently specified expectations. New producer tests alone
cannot establish old-client behaviour. Report the observed compatibility and
transition evidence separately from release readiness or deployment.
