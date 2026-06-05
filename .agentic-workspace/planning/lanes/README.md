# Planning Lane Records

Lane records are the middle Planning artifact between an epic decomposition and concrete slice execplans.

- Decompositions own high-level intent, soft requirements, and candidate lanes.
- Lane records own the concrete lane outcome, strategy, subsystem boundaries, slice sequence, proof aggregation, residual lane work, and contribution back to the parent epic.
- Execplans own one concrete implementation slice, including touched paths, validation commands, execution residue, and slice closeout.

Do not turn execplans into lane journals. A slice may reference a lane, and the lane may list the slice execplan, but lane strategy and lane-to-epic closeout evidence belong in the lane record.
