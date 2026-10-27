## Context

CADGenBench edit fixtures ship `input.step`, `renders/` of it, and `edit_description.txt`;
the scored output is one STEP that the harness fuses and moves into canonical pose
(`evals/cadgenbench_run.py` `write_candidate`). Today the harness's edit prompt asks the
full skill to "import it with importStep and apply this edit", which drags the run through
sourcing, requirements, planning, print orientation and the quality gate, and delivers in
print pose. Every tool an edit needs already exists: `cq.importers` for the input,
`run_cadquery_model.py` for run/validate/preview/`--deliver --formats ... --output-dir`,
and `diff_models.py` for an exact A-vs-B volume diff in a shared frame.

## Goals / Non-Goals

**Goals:**
- One command that turns (solid file, change text) into an edited STEP in the input frame.
- A checkable "did the edit actually happen, in the right direction" signal before delivery.
- The benchmark harness drives edit fixtures through that command.

**Non-Goals:**
- Feature recognition / reparametrizing the imported solid (it stays a dumb solid, as in
  Phase 0 rung 2).
- Printability work: orientation, quality gate, DFM thresholds, `build.py`, `REGENERATE.md`.
- Editing meshes (STL/3MF) or cq-design's own part scripts (those are edited directly and
  rebuilt with `/cq-design:build`).
- Multi-step edit sessions or undo; each invocation is one edit from the given file.

## Decisions

- **Prompt-only command, no new `src/` script.** The deterministic parts (import, run,
  export, diff) are existing tools with JSON contracts; the remaining work (turning the
  description into CadQuery ops, judging whether a diff matches the intent) is judgment.
  Alternative considered: an `edit_step.py` wrapper that runs both scripts, meshes and
  diffs in one call. Rejected for now: it would be three existing calls glued together.
  Add it if the command text's call sequence proves error-prone in benchmark runs.
- **Input meshed via a two-line `build/edit_input.py`** (`result = cq.importers.importStep(path)`)
  rather than teaching `diff_models.py`/`mesh_io` to read STEP. Keeps `diff_models.py`'s
  STL contract unchanged and reuses `run_cadquery_model.py`'s tessellation, so A and B are
  meshed identically.
- **Diff thresholds are judgment, `identical` is the only hard rule.** `diff_models.py`
  gives `only_a_volume` / `only_b_volume` / `bbox_delta` but not where the change is;
  whether those match "add a 5 mm hole" is read by the session together with the diff PNG.
  A hard spatial rule (changed volume inside a declared box) would need the description
  parsed into a region, which is the judgment itself.
- **No print pose, no plan.** Edit fidelity is defined in the input frame; the benchmark
  canonicalizes pose itself. Skipping phases 0-2 is what makes the command cheap enough
  for a benchmark budget.
- **Iteration cap of 5**, matching the order of magnitude of the part loop's attempt
  budget; on exhaustion nothing is delivered so the harness scores an empty folder rather
  than a wrong solid that passes sanity.
- **Harness prompt invokes the command.** `build_prompt`'s edit branch becomes
  `/cq-design:edit input.step <description>` plus `UNATTENDED` and `FIDELITY` without its
  `build/build.py` sentence (moved into the generation branch). `delivered_steps` already
  reads `out/` first, so `out/input_edited.step` is picked up unchanged.

## Risks / Trade-offs

- [Headless `claude -p` may not expand a plugin slash command in the prompt] -> Verify
  with one edit fixture (`--fixtures <id>`) before a full run; fallback is a prompt that
  says "Run the cq-design edit command (`commands/edit.md`) on input.step with: ...".
- [Face/edge edits (change a fillet radius, move a hole) are awkward as booleans on a dumb
  solid] -> The command allows face/edge operations on the imported body (fill-and-recut
  for holes); edits that truly need the original feature tree will fail the diff check and
  stop after 5 iterations instead of delivering garbage.
- [`UNATTENDED` mentions `planning_notes`, which the edit path has no file for] -> The
  command records assumptions in its report; the stray mention is harmless.
- [Tessellation noise makes `identical` false for a no-op edit] -> Both sides go through
  the same exporter at the same settings, and `--tol` defaults to 1e-6 of total volume;
  a no-op import/re-export diffs as identical (covered by a test).

## Open Questions

- Should edit results also be offered as STL for printing? Not needed for the benchmark;
  the user can run `run_cadquery_model.py build/<stem>_edited.py --deliver --formats stl`.
