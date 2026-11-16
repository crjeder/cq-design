# Pipeline

Target pipeline for cq-design, from the user's request to reviewed G-code. Drafted
2026-11-16. Steps marked **new** do not exist yet; everything else describes the
current skill (`SKILL.md`, `skill/phase*.md`, `ARCHITECTURE.md`).

Owners: **program** = deterministic script in `src/` (or an external CLI), **agent** =
LLM sub-agent, **main** = main session (owns every user checkpoint).

## Decisions

| Id | Question | Decision | Rejected |
|---|---|---|---|
| A | Who controls the order of the steps | State machine program (`src/pipeline.py`, **new**): owns the build state, reports the allowed next step, rejects invalid transitions; `edit` is an explicit plan-less route | Skill prose only (today) |
| B | When sourcing triage runs | LLM decides per request: run it for parts likely to exist (standard enclosures, mounts for known products), skip it for custom parts | Always; only on request |
| C | Slicer | estampo driving the OrcaSlicer CLI (pinned profiles and Docker image) | PrusaSlicer CLI, CuraEngine, no slicing |
| D | G-code danger check | GcodeGuard `scan` with a per-printer profile, blocking; pin a commit | gcode-lint, GcodeGuard + gcode-inspector, none |
| E | Print plates for multi-part models | estampo bin-packs plates; our 3MF keeps one named object per union | Slicer project-3MF plates, operator splits |
| F | Human G-code review | PrusaSlicer G-code Viewer (standalone app) next to the GcodeGuard findings | Own HTML page (gcode-preview), PrintView3D, none |
| G | Print time and filament weight | Slicer's own stats from the G-code header; the slicer-free bound only when slicing is skipped | klipper_estimator / gcode-estimator, slicer-free bound only |
| H | Where slicing runs | Inside the pipeline, before delivery; a blocking finding sends the run back | Separate command after delivery |

## Steps

| # | Step | Owner | In | Out | Status |
|---|---|---|---|---|---|
| 0 | Setup | program (`init_permissions.py`) | working directory | `.claude/settings.local.json`, `profile.json`, `skill_config.json`, `build/` | exists |
| 1 | Route the request: design / plan-only / edit; resume if `build/journal.md` exists | program (`pipeline.py`, decision A) + main | request, build state | route, next allowed step | **new** (today: LLM reads `SKILL.md`) |
| 2 | Sourcing triage, five-rung ladder | main decides whether to run (decision B); sourcing agent searches; main classifies | request | rung; rungs 1-3 skip steps 3-5 | exists, gating **new** |
| 3 | Requirements: topology Q&A, dimension research, acceptance statements; checkpoint 1 | main + research agent + oracle agent | request | dimension table, `parameters.py`, `acceptance.json` | exists |
| 4 | Planning; checkpoint 2 | planner agent + program (`plan.py validate`) | approved requirements | `BUILD_PLAN.json` | exists |
| 5 | Part loop: staged or one run, lint, validate, render, audit, escalation | builder agent + programs (`script_lint.py`, `run_cadquery_model.py`, `feature_presence_check.py`) + auditor agent | plan entry per part | passing `build/<id>.py`, previews, `attempts.jsonl` | exists |
| 6 | Design approval; checkpoint 3 | main | all renders | approved design | exists |
| 7 | Advisors: FEM stress, toolpath speed | program (`fem_check.py`, `toolpath_speed.py`) | approved parts | advisories | exists |
| 8 | Print orientation and print finishing | program (`print_orientation.py`, `print_finishing.py`); geometry edits go back to step 5 | approved parts | `orientations.json` | exists |
| 9 | Write assembly, whole-model checks, quality gate | program (`write_assembly.py`, kinematic / plate-clearance / keep-out checks, `quality_gate.py`) | parts + placement | `build/<union_id>.quality_gate.json` | exists |
| 10 | Export in print pose | program (`build.py`) | accepted model | `out/` STEP / STL / 3MF / estampo TOML; one 3MF object per union (decision E) | exists |
| 11 | Headless slicing | program (estampo + OrcaSlicer CLI, decision C); estampo bin-packs plates (decision E) | estampo TOML, 3MF, printer profile | G-code per plate | **new** |
| 12 | G-code danger check, blocking | program (GcodeGuard `scan`, decision D) | G-code, per-printer GcodeGuard profile (start/end macros allowlisted) | findings (SARIF); exit 2 = block | **new** |
| 13 | Human G-code review | main: user opens the G-code in the PrusaSlicer G-code Viewer next to the findings (decision F) | G-code, findings | approve / reject | **new** |
| 14 | Print time and filament weight | program: read OrcaSlicer's stats from the G-code header (decision G) | G-code | time, filament length and weight | **new** (today: slicer-free bound from `toolpath_speed.py`) |
| 15 | Deliver: report, `README.md`, `REGENERATE.md` | main | all of the above | report to the user | exists, report gains steps 11-14 |
| 16 | Post-delivery corrections | main, back to the step the change touches | user change request | new run of that step onward | exists |

## Loops back

| From | Trigger | Back to |
|---|---|---|
| 3 | user corrects the dimension table | 3 (research agent) |
| 4 | `plan.py validate` errors or plan edits | 4 (planner agent) |
| 5 | 3 failed attempts | main asks for a hint, resumes the same builder |
| 5 | auditor `visual_mismatch` | 5 (same builder) |
| 6 | change request | 5 |
| 8 | orientation needs a geometry edit | 5, then audit again |
| 12 | blocking GcodeGuard finding caused by geometry or pose | 8 (or 5 if geometry must change) |
| 12 | blocking finding caused by slicer settings or profile | 11 |
| 13 | user rejects the G-code | 11 (settings) or 8 / 5 (model) |
| any | change to the user's intent | 3 (intent is the invariant; see `ARCHITECTURE.md`) |

The state machine (decision A) enforces these transitions: a step runs only when its
predecessor's output exists and is newer than its inputs.

## Open points

- GcodeGuard is new with one maintainer: recheck it on real OrcaSlicer output for
  each target printer before making it blocking.
- `profile.json` has no bed dimensions yet; estampo plate packing and the GcodeGuard
  build-volume rules need them.
- Slicing skipped (no estampo / OrcaSlicer installed): steps 11-14 report `unverified`,
  never pass, and step 15 falls back to the slicer-free time bound.
