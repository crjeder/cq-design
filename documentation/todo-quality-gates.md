# Quality gates and conformance checks -- details

Tasks: [TODO.md](../TODO.md#3-quality-gates-and-conformance-checks).

### Plan conformance gate


`BUILD_PLAN.json` already is a declared design-intent spec, which build123d-mcp's
`verify_spec` has to ask for separately. Turn each part's planned dimensions and
features into measured pass / fail / unverified checks in `quality_gate.py`
(extending `feature_presence_check.py`), so the visual auditor is a backstop
rather than the main evidence. Second half, from their `design_audit`: rebuild
each part with every plan parameter nudged +-10% and report which ones break
the build or the gate (brittle vs coupled vs robust). Tri-state reporting per the
text-to-cad gate item above.

### Hole checks and hole advisories

change rules into advisories: make holes drop shaped --> hole found. consider drop shape like [DfAM Check](https://github.com/earthtojake/text-to-cad/blob/main/skills/dfam-check/SKILL.md)

Hole checks against the solid geometry, never passing an ambiguous match
Varen: it measures the cylindrical faces on the final solid (diameter, axis, span). A hole’s position is where the cylinder axis meets the host surface, not the cylinder’s own reported centre. A planned hole is checked only when exactly one cylinder matches it. The outcomes are MATCHED, AMBIGUOUS, NOT_FOUND and UNAVAILABLE, and AMBIGUOUS never passes.
cq-design today: feature_presence_check.py:24 says plainly that holes made with .hole/.cboreHole are “out of first scope”. measure_stl.py finds cylinders from the mesh only.
Fix: measuring the CadQuery solid’s cylindrical faces directly would cover those holes, and the “a single match or no pass” rule is the part to copy. Varen found the need the hard way: its gears shipped with floating teeth and a “through hole” that cut nothing, because the checks only looked at whether the mesh was well formed.

### Gate ideas from the text-to-cad survey

Survey 2026-10-16, from its README, `skills/cad`, `dfam-check`, `dfm` and `AGENTS.md`
only (scripts and limit tables not read -- check the source before adopting). In
suggested implementation order; 1-4 are small changes in `quality_gate.py` /
`mesh_io.py` / skill text.

Gates: tri-state result (pass / fail / unverified). A check that could not run must never read as a pass. Their DfAM tool sets `partial: true`, lists the affected sections, exits 2. Audit how `quality_gate.py` reports a skipped or failed analysis

`thin_regions`: report `min_mm` and `p05_mm`, violation = `p05` below the limit (robust to single-triangle noise; cf. `sliver_fin`)

Gate / `measure_stl.py`: unit-scale sanity flag (`units_suspect` from the bbox diagonal) so overhang/support 0.0 on a mis-scaled mesh is not reported as clean

Gate findings: facts vs verdicts. Measuring tools report numbers only; each finding cites the limit's source (`profile.json` / plan constraint / default) and the JSON path of the measurement

`script_lint.py`: reproducibility rules for part scripts -- every file read is an input, no reading own outputs, no dependence on time, randomness, env vars or the working directory

DFM numbers in `reference/`: record rule provenance (source, version/access date, units, material). Unverifiable rule is reported as missing, never replaced by a silent default

### Scoped repair patches and attempt history

Source: MLYengineering/Text2CAD, rated Medium-High.

- Why: `quality_gate._render_fix_prompt` asks `claude -p` to output the whole script
  and `run_gate` overwrites `script_path` with it (`MAX_FIX_ROUNDS = 2`). Nothing
  limits unrelated rewrites, and round 2 does not know round 1's fix failed.
- Do: (a) in `run_gate`, keep the pre-fix text, compute `difflib.unified_diff` after
  `_extract_python`; if more than `FIX_MAX_CHANGED_FRACTION` (start 0.3) of lines
  changed, restore the original and report a `fix_rejected` info issue. (b) keep a
  `history` list across rounds (issue `type`s, and the changed hunks capped at 40
  lines); `_render_fix_prompt(script_path, issues, history)` adds a "Previous fix
  attempts that did not resolve these issues" block, and an instruction to change
  only the failing construct. (c) also append the part's earlier `error_types` from
  `attempts.jsonl` (`log._read_records` + `fold_attempts`).
- Test: `tests/test_quality_gate.py` with `_call_claude` monkeypatched: a full rewrite
  is rejected and the file restored; round-2 prompt contains round-1 history; a small
  patch is accepted.
- Done when: a deliberately over-eager fake fixer cannot change more than the cap.

### Differential geometry vs the previous attempt

Source: vericontext/cadgate, rated Medium-High.

- Why: `quality_gate.py` judges each attempt alone, so a regression between
  attempts (volume halves, bbox shifts, wall thins) is invisible.
- Do: after each successful wrapper run store `build/baseline/<part_id>.json` =
  `{volume_mm3, bbox_mm, min_wall_mm (if --wall-min), face_count}` from the
  wrapper's `geometry` block. New gate stage `_run_regression_stage` compares the
  current run to it and emits `geometry_regression` warnings above thresholds
  (volume +-25%, bbox axis +-20%) unless the latest `request_log` entry targets
  that part with `level` `functional` or `operation` (an intended change). Update
  the baseline on gate pass. `--no-baseline` flag to skip. Advisory, never blocks.
- Test: `tests/test_quality_gate.py`: unchanged part passes; halved volume warns;
  warning suppressed when a targeted correction exists.
- Done when: editing a part to remove a large feature produces one warning naming
  the old and new volume.

### Per-project design-rule file

Source: cad-khana / FreeCAD-AI, rated Medium-High.

- Why: DFM limits live in `plan.constraints` and `profile.json`; there is no way to
  say "all edges >= 0.8 mm fillet, min wall 1.2 mm for this project" and have the
  gate fail on it with the rule's own text.
- Do: optional `design_rules.json` at the project root, a list of
  `{id, check: "min_wall" | "min_fillet" | "min_clearance" | "max_overhang", value,
  scope: "all" | [part ids], severity}`. `init_permissions.py` does not seed it.
  New `quality_gate._run_design_rules_stage` maps each rule onto data the gate
  already computes (`thin_regions` for wall, `edge_treatment_check` for fillet,
  `plate_clearance_check`/`keep_out_check` for clearance, `_analyze_stl` for
  overhang) and re-labels the finding with the rule `id`. Add a JSON Schema
  `src/design_rules_schema.json` validated by `plan.py validate`-style call. No new
  geometry code.
- Test: `tests/test_quality_gate.py`: a rule tighter than the plan default fails a
  fixture part; a missing file adds no issue.
- Done when: a project rule of 1.2 mm min wall blocks a 1.0 mm wall with a message
  naming the rule id.
