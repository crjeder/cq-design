## Why

Rung-3 vetting step 2 (`skill/phase0_sourcing.md:83-84`) tells the orchestrator to "run the
quality gate's mesh-level stages" on a downloaded STL but gives no command. The only gate
entry point, `quality_gate.py`, requires `--script` and `--plan` (`src/quality_gate.py:1264-1265`),
and a rung-3 mesh has neither. The orchestrator is left improvising or running `--help`,
which `SKILL.md:18` forbids ("Every invocation is documented at the step that uses it --
never run `--help`").

## What Changes

- Replace rung-3 vetting step 2 in `skill/phase0_sourcing.md` with the tools that run on a
  bare mesh:
  - **Watertightness**: read `is_watertight` from the `measure_stl.py` JSON already produced
    in step 1 (no second command).
  - **Overhang**: `print_orientation.py <stl> --overhang-max-deg <n> --optimize-for min_support`,
    with `<n>` from `profile.json` `constraints.overhang_max_deg`; read `support_score` and
    `rotate` from its JSON.
- Define the pass/fail outcome concretely: `is_watertight: false` fails rung 3 (same
  severity as the gate's `non_watertight` error); a nonzero `support_score` is a finding
  shown to the user at the step-3 confirmation (same severity as the gate's overhang
  warning), not an automatic downgrade.
- Update the `sourcing-triage` spec wording that names "the quality gate's mesh-level stages"
  so it names the bare-mesh checks instead.

No script changes.

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `sourcing-triage`: rung-3 vetting requirement names the bare-mesh commands
  (`measure_stl.py` `is_watertight`, `print_orientation.py` support cost) instead of the
  quality gate, and states that an overhang needing support is surfaced to the user rather
  than failing rung 3.

## Impact

- `skill/phase0_sourcing.md` (rung 3 vetting steps 2 and the failure bullet).
- `openspec/specs/sourcing-triage/spec.md` (via delta at archive).
- No code, CLI, or JSON contract changes. `quality_gate.py` is untouched.
