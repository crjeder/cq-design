## Context

`quality_gate.py::run_gate` aggregates findings from ~10 stage functions (wrapper DFM,
geometry/overhang, 3MF manifold, telemetry, parameters presence/unresolved, plan
validation, kinematics, plate clearance, keep-out, edge treatment, feature presence,
hinge-guard, cosmetic-slope, Gridfinity) into one `issues` list, each item built either
by a raw dict literal (a handful of spots in `quality_gate.py` itself) or via
`units.make_issue(source, severity, type_, message, hint, **extra)`. `skill/phase3_build.md`'s
Quality gate section then hand-lists, per `type`, what the orchestrator should do:
resume the builder with a fix, re-run the export, ask the user a question, or just show
it alongside the print recipe. That list has to be kept in sync by hand every time a
check module adds a new finding type, and it lives in a doc the orchestrator reads,
not in the data the gate emits.

## Goals / Non-Goals

**Goals:**
- Every finding in `quality_gate.json`'s `issues` carries an `action` the orchestrator
  can switch on directly, with no type-specific knowledge needed for the common case.
- Adding a new finding type to an existing or future check module costs nothing extra
  at the call site — `action` is derived, not authored per `make_issue` call.
- The four actions cover every case the current prose in `phase3_build.md` describes:
  `fix` (resume the builder), `re_export` (stale STL, no script change needed),
  `ask_user` (the pipeline can't pick a remedy — geometry vs. plan, or a value judgment
  like "is this stop intentional"), `warn_only` (surface, never act).

**Non-Goals:**
- Not changing `make_issue`'s signature or touching any of the 6 check-module call
  sites (`kinematic_check.py`, `plate_clearance_check.py`, `keep_out_check.py`,
  `edge_treatment_check.py`, `feature_presence_check.py`, `gridfinity_check.py`) — the
  classification is centralized in `quality_gate.py`, not distributed.
- Not changing the `--fix` cold-context path (`_call_claude`/`_render_fix_prompt`);
  `action` is for the caller's own fix loop (Phase 3's part loop), which already runs
  the gate without `--fix`.
- Not changing `MAX_FIX_ROUNDS` bounding or the pass/fail (`errors` non-empty) computation.

## Decisions

**Classify centrally in `run_gate`, from `(type, severity)`, not per call site.**
Every finding already carries `type` and `severity` by the time `run_gate` assembles
`all_issues`. A single pass — `for issue in all_issues: issue["action"] = classify(issue)`
— covers every stage uniformly, including the raw-dict issues in `quality_gate.py` that
don't go through `make_issue`. Alternative considered: add an `action` (or per-type
default) parameter to `make_issue` and pass it at all ~35 call sites. Rejected — it
would need touching every check module for a value fully determined by data already
present (`type`, `severity`), and every future check module would have to remember to
pass it.

**Default from `severity`, override by `type` for the handful that disagree.**
`error -> fix`, `warning -> warn_only`, `info -> warn_only`. Three types override the
default because a single mechanical fix isn't the right response:
- `stale_artifact` (error) -> `re_export`: the script is fine, only the exported STL is
  out of date (`keep_out_check.py`, `plate_clearance_check.py`, `kinematic_check.py` all
  emit this the same way) — re-running the export and the gate resolves it with no
  builder involvement.
- `motion_collision`, `range_exceeds_limit` (error) -> `ask_user`: the current prose
  already describes two divergent remedies each ("relieve that geometry, or fix the
  plan's `kinematics` entry"; "change the range or the joint") — the gate has no way to
  know which one is right, so it must not auto-fix.
- `contact_limited_stop` (warning) -> `ask_user`: the current prose already asks the
  user whether the natural stop is the intended rest position — this is a warning that
  still needs a question asked, not silent display.

Alternative considered: a full per-`type` lookup table (one entry per finding type,
~35 entries). Rejected as needless duplication of what `severity` already encodes for
all but three types — the override table stays at 4 entries and reads as the exception
list it is, matching ponytail's "three similar lines beats a premature abstraction" the
other way: here the *abstraction* (severity default) is the lazy option, and the
explicit list is only as big as the real exceptions.

**Where the mapping lives.** A module-level dict in `quality_gate.py`:
```python
_ACTION_OVERRIDE = {
    "stale_artifact": "re_export",
    "motion_collision": "ask_user",
    "range_exceeds_limit": "ask_user",
    "contact_limited_stop": "ask_user",
}
_DEFAULT_ACTION = {"error": "fix", "warning": "warn_only", "info": "warn_only"}

def _classify_action(issue: dict) -> str:
    return _ACTION_OVERRIDE.get(issue["type"], _DEFAULT_ACTION[issue["severity"]])
```
Applied once, right before `run_gate` computes `errors`/`passed` at the end.

**`phase3_build.md` replacement text.** The per-type bullet list under "Quality gate"
is replaced by one rule: read each finding's `action` — `fix` resumes the part's
builder with `fix: <type>: <message> (hint: <hint>)`, re-audits if geometry changed,
re-exports, re-runs the gate (bounded at 2 rounds/part, same as today); `re_export`
re-runs Model export then the gate, no builder involved; `ask_user` surfaces the
finding's `message`/`hint` and asks before doing anything; `warn_only` is shown with
the print recipe and never triggers a round. `stale_artifact`, `motion_collision`,
`range_exceeds_limit`, and `contact_limited_stop` are no longer named in the doc at
all — the action they map to is authoritative.

## Risks / Trade-offs

- [A future check module emits a new `type` under `severity: error` that actually needs
  `ask_user` or `re_export`, but nobody adds it to `_ACTION_OVERRIDE`, so it silently
  gets `fix`] -> Mitigation: `fix` (resume the builder, re-audit, re-export, re-gate) is
  a safe-by-default over-reaction for a wrongly-defaulted error finding — worst case is
  a wasted builder round, not a silent miss, and the existing 2-round-then-escalate
  bound still applies.
- [`build/quality_gate.json` consumers outside this repo (if any) assume the current
  key set] -> Mitigation: called out as **BREAKING** in the proposal; this is a
  report-shape addition (new key), not a removal, so existing readers that don't
  validate against an exact key set are unaffected.

## Migration Plan

Single-PR change, no phased rollout: `_classify_action` ships alongside the
`phase3_build.md` doc update in the same commit, since the doc's old list would
otherwise silently drift from the code the moment either changes. No data migration —
`quality_gate.json` is regenerated fresh on every gate run.

## Open Questions

None — the four actions and the three overrides are fully determined by the existing
`phase3_build.md` prose being replaced; nothing here is a design choice pending
feedback.
