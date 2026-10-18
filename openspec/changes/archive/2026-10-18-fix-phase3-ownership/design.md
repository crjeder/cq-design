## Context

The part builder is a sub-agent that owns one script and returns a JSON contract; it never sees acceptance (audit pass, user approval), which happens in the orchestrating session. `skill/phase3_build.md` already runs the FEM and toolpath-speed advisors after acceptance, with correct `build/` paths and the `--deliver --formats step` step the FEM solve needs. `prompts/part.md` carries a second, stale copy of both.

Multi-union parts (`result` is a `dict[str, Workplane]`) export one file per union id from both the shim and `exporters.export_loaded`; `write_assembly.py` writes `stl/<uid>.stl`. The Phase 3 commands were written for the single-union case, where union id == part id.

## Goals / Non-Goals

**Goals:**
- One owner (the orchestrator) for each post-acceptance advisor.
- Per-union Phase 3 commands that resolve to files that exist for multi-union parts.

**Non-Goals:**
- Changing any `src/` tool, CLI flag, or output naming.
- Making `quality_gate.py` pose each union with its own orientation in one call (it applies one `--orientation` to every union STL the wrapper produced). Calling it once per union with that union's orientation is what this change documents; a per-union `rotate` inside the gate is a separate change.
- Per-union FEM. `fem_check.py` is keyed by `--part`, and a multi-union part's `--deliver --formats step` also writes `<union_id>.step`; FEM on multi-union parts is left as it is.

## Decisions

- **Delete from `part.md`, keep in `phase3_build.md`.** The orchestrator copy already has correct paths and the STEP export step. The alternative (teach the builder to deliver STEP and run the advisors) would widen the builder's file ownership and still not give it an acceptance signal.
- **Keep one line in `part.md`.** The builder still writes `engineering_rationale`, and on a resume after a FEM `"ok"` result it needs to know the cited FEM numbers replace the closed-form check rather than adding a beam formula back.
- **`<union_id>` placeholder plus one definitional sentence.** Rather than branching commands for single- vs multi-union parts, every per-union command uses `<union_id>` and one sentence states that a part without `unions` has union id == part id. Script paths stay `build/<part_id>.py`, since a script is per part.
- **`orientations.json` keyed by union id.** `quality_gate.py` already reads it as union-keyed and `phase3_build.md` already notes multi-union orientation is union-keyed; for single-union parts the key is unchanged.

## Risks / Trade-offs

- [The builder loses the FEM/toolpath interpretation guidance] -> The orchestrator copy carries the full reading guide and passes any fix back via `fix:` on resume.
- [A reader takes `<union_id>` to mean declared `unions` only] -> The definitional sentence covers the single-union case explicitly.
