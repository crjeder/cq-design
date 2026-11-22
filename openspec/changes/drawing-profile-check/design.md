## Context

A part's `BUILD_PLAN.json` entry can carry authored `probes[]` (`solid_at`, `empty_at`,
`ray`, `bbox`, build pose, `label` required). Today they are checked only by `Part.result()`
in a step script; a plain part script never evaluates them ("legacy part scripts do not
evaluate them"), and the gate evaluates a probe only when an oracle `probe` statement binds
it. Planning rule 17 asks for probes on unprobed request dimensions, but says nothing about
section views, wall sides or flange directions, which is where the CADGenBench shape failures
come from (#396: 135 is a 2 mm sheet-metal bracket with correct bbox and b1, IoU 0.19).

`probes.evaluate(probe, shape)` already checks one probe on a BRep, and
`quality_gate._run_oracle_stage` already loads the part's build-pose body as a compound of
its unions.

## Goals / Non-Goals

**Goals:**
- Every authored probe is checked on the finished part, whatever kind of script built it.
- Drawings with thin walls or bends produce probes that pin wall side and flange direction.
- CADGenBench work directories survive the run for diagnosis.

**Non-Goals:**
- Rendering silhouettes or sections and comparing images or outlines with the drawing.
- Extracting dimensions from the drawing by script (the planner reads it).
- New probe kinds.
- Fixing fixture 136 itself (needs the kept work dir to diagnose first).

## Decisions

1. **Probes, not silhouette rendering.** The issue suggests rendering each view's silhouette
   or section and comparing it with the drawing's extents and profile points. The plan has no
   machine-readable outline to compare an image against, and the failing quantities (which
   side of a 2 mm dimension the wall lies on, which way a flange goes) are point facts: a
   `solid_at` just inside the dimensioned face plus an `empty_at` just past it decides wall
   side exactly on the BRep, with no tessellation or pixel tolerance. Overall view extents are
   the `bbox` probe. Alternative: a new `section` probe kind (2D extents of a plane cut).
   Rejected for now: brackets already cover the cited failures; add it if a fixture shows a
   profile error no point bracket can express.

2. **New gate stage `plan_probes`, next to the oracle stage, build pose.** Loads the body the
   same way as `_run_oracle_stage` (extract that loader into one helper used by both),
   builds `Probe(**entry)` for each `probes[]` entry, evaluates with `probes.evaluate`. The
   body is loaded only when the part has probes to check. Issue shape:
   `{source: "geometry", severity: "error", type: "probe_unmet", label, kind, expected,
   observed, message, hint}`; the hint says to compare against the section view the label
   cites and check which side of the dimension the material lies.

3. **Skip probes an oracle statement binds.** A label listed in any `acceptance_bindings[]`
   `probes` for the part is already checked by the oracle stage, which carries its own round
   counting and `ask_user` escalation; reporting it twice would double-count one defect.

4. **Run for step scripts too.** `Part.result()` already fails a step script on a bad probe,
   so the stage is normally silent there; skipping it would need script-kind detection for no
   gain.

5. **Prompt rule placement: planning rule 17 gets a thin-wall / sheet-metal paragraph.** It is
   judgment (reading section views), so it stays prose; the gate stage is what enforces it.
   The rule also requires `planning_notes` to state, per thickness dimension, the face it
   references and the bend radius side, so the builder sees the decision and a reviewer can
   trace it.

6. **Runner: delete `_work/<id>/.venv` after each fixture, keep the rest.** The venv is the
   bulk of the directory and is regenerable; scripts, `BUILD_PLAN.json`, `build/journal.md`,
   `build/attempts.jsonl` and `cost.json` are small and are what diagnosis needs. Done in
   `generate()` after `run_fixture`, also on timeout or error. Alternative: copy selected
   files elsewhere. Rejected: an allowlist would miss whatever the next failure needs.

## Risks / Trade-offs

- [A probe point placed within OCC classifier noise of a face flips IN/OUT] -> Rule 17 already
  keeps points 0.1 mm off surfaces; the new rule puts bracket points at half the wall
  thickness from the face, never closer than 0.1 mm.
- [The planner reads the drawing wrong and writes a wrong probe, so the gate enforces the
  wrong form] -> The rule makes the wall side an explicit, labelled decision in
  `planning_notes`; a wrong read was already happening silently, now it is visible.
- [Loading the body adds gate time for parts with probes] -> One extra script run per probed
  part, shared with the oracle stage when both need it.
- [`.venv` delete fails on Windows because a process holds a file] ->
  `shutil.rmtree(..., ignore_errors=True)`; a leftover venv costs disk, not correctness.
