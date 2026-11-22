## Context

The FDM-specific design is spread over three places: `prompts/planning.md` (fit clearances,
material allowances, printer constraints), `src/quality_gate.py` (min wall from
`plan["constraints"]`, thin regions, overhang/bridge, fins), and `build.py` /
`build_template.py` (print orientation via `orientations.json`). CADGenBench currently
fights this with prose in `evals/cadgenbench_run.py`'s `FIDELITY` prompt, which no script
enforces (see the program-vs-prompt rule in CLAUDE.md). The gate and `build.py` read the
plan, not the profile, so the switch must reach the plan.

## Goals / Non-Goals

**Goals:**
- One switch that turns off every FDM-specific geometry change, enforced by scripts.
- Default behavior byte-for-byte unchanged.
- The benchmark runner uses the switch instead of prose.

**Non-Goals:**
- Per-feature toggles (clearances only, orientation only). Add when a use case appears.
- Changing the delivered file set or formats.
- Removing the planner's drawing-faithfulness rules, which apply in both modes.

## Decisions

- **One enum field, not booleans.** `design_intent: "print" | "cad"` on profile and plan.
  Alternative: separate flags per rule. Rejected: the benchmark needs all of them off, and
  an enum leaves room for later intents without schema churn.
- **Lives in the profile, copied into the plan.** The profile is what users and the runner
  edit; the plan is what the gate and `build.py` already load. `plan.py` validation checks
  the copy. Alternative: a CLI flag on each script. Rejected: three scripts plus the
  planner prompt would each need it passed, and a missing flag silently reverts to print.
- **Gate skips stages by name, keeps geometry stages.** A single guard where the stage list
  is assembled, so a skipped stage emits nothing. Valid B-rep, watertight, bbox, feature and
  probe checks stay: they measure fidelity, not printability.
- **`build.py` uses identity rotation.** Same code path as an accepted `orientations.json`
  of `rotate: []`, so the three-poses contract holds (print pose equals build pose).
- **Prompt rules gated at render time.** `render_prompt.py` already substitutes
  `{{PRINTER_PROFILE}}`; the print-only sections move behind a conditional so the "print"
  output is unchanged and the "cad" output omits them.

## Risks / Trade-offs

- [A plan written in "cad" mode is not printable as delivered] -> intended; the field is
  explicit and recorded in the plan and `planning_notes`.
- [Planner ignores the omitted rules but still invents clearances] -> the prompt states
  nominal dimensions are used unmodified; the existing drawing probes catch deviations.
- [Profile/plan drift: profile says cad, stale plan says print] -> `render_prompt.py`
  planner output always rewrites the plan field; the gate reads only the plan.

## Open Questions

- Whether `cq-design:edit` (STEP edit fixtures) should honor the field too. Edit already
  keeps the input's coordinates; confirm at apply time that it never calls the print
  orientation or wall gate, and note it in the tasks if it does.
