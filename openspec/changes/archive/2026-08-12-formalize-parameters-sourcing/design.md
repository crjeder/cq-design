## Context

`skill/phase1_requirements.md` (Provenance write, at approval) and the
`dimension-validation-checkpoint` spec already prescribe: write `parameters.py` at the
project root the same turn the user approves the Phase 1 dimension table, before Phase 2
starts; append `- phase1/dimensions_approved: parameters.py written, <n> dimensions
recorded` to `build/journal.md`; Phase 2 (`skill/phase2_planning.md`) updates the same
file only if planning adds a new measurement. This is entirely procedural -- no script
reads, writes, or checks `parameters.py`. `src/quality_gate.py` already has one advisory
presence check of this shape: `_run_telemetry_stage` warns (never blocks) when
`build/attempts.jsonl` is missing/empty/unparseable, so the eval harness's metrics have
data. That stage's call site and result shape is the template for this change.

## Goals / Non-Goals

**Goals:**
- Close the concrete gap named in TODO.md: something checks the procedure was actually
  followed, instead of the file's existence being unverified prose convention.
- Keep the check advisory (`warning`), matching every other presence-only stage in the
  gate (telemetry, cosmetic-slope) -- `parameters.py` is provenance, not geometry; a
  missing file cannot make a part unprintable.

**Non-Goals:**
- Reconciling `parameters.py`'s raw sourced values against a part script's own
  `PARAMETERS` block (resolved/derived geometry, deliberately not the same numbers --
  e.g. a clearance-adjusted hole diameter derived from a sourced screw diameter). No
  concrete case has shown these drifting in a way that mattered; building a diff/reconcile
  tool for a hypothetical is the over-engineering `ponytail` and this project's own
  "no speculative features" rule both rule out.
- Extending `import_params.py` (which round-trips a part script's `PARAMETERS` block into
  `BUILD_PLAN.json`) to also read `parameters.py`. Different files, different purpose:
  `import_params.py` reconciles *resolved geometry* values against the plan;
  `parameters.py` records *raw real-world* values against nothing (it is explicitly "not
  imported by the build"). Conflating them would require a mapping between raw and
  resolved values that doesn't exist today and that the TODO item itself only floats as
  "optionally."
- A schema or structured format for `parameters.py`. It stays a human-readable Python
  module with comments; the check only asks "does it exist and have content," not "is
  every line well-formed" -- the existing prose format has worked across projects and
  imposing structure now is solving a problem nobody hit.

## Decisions

**Gate stage, not a schema/CLI tool.** The other half of "formalize" (make it a
prescribed deliverable) is already done in the phase docs and the
`dimension-validation-checkpoint` spec. The only thing actually missing is
verification, and `quality_gate.py` is where every other advisory provenance check
(telemetry) already lives, wired into the same `run_gate` flow and reported through the
same `{source, severity, type, message, hint}` contract Phase 4 delivery already reads.

**Trigger condition: journal milestone present, file absent -- not "always warn if
absent."** A design with zero real-world dimensions (the phase1 doc's explicit skip
case: "no real-world dimension lookups were performed") correctly has no
`parameters.py` and no `dimensions_approved` journal line. Warning unconditionally would
false-positive on every such project. Gating on the journal milestone line means the
check only fires when Phase 1 itself recorded that sourcing happened.

**Path derivation: project root = `os.path.dirname(plan_path)`.** `BUILD_PLAN.json`,
`parameters.py`, and `build/journal.md` are all conventionally co-located at the project
root (`skill/phase2_planning.md`: "at the project root alongside `BUILD_PLAN.json`");
`run_gate` already receives `plan_path`, so no new parameter is needed on the public
`run_gate(...)` signature -- mirrors how `_run_telemetry_stage`'s log path is resolved
from `script_path`'s directory today.

**Non-empty check, not content validation.** "Missing or empty" catches the two failure
modes that matter (procedure skipped entirely; file touched but never filled in). Parsing
the file's Python syntax or asserting comment-per-constant would need the AST-walking
machinery `import_params.py` already has for a different file, for a benefit (catching a
malformed but non-empty file) with no observed incidents to justify it.

## Risks / Trade-offs

[A project that manually deletes `parameters.py` after delivery but keeps `journal.md`
would false-positive on a re-run of the gate] -> acceptable: advisory-only, same
tolerance the telemetry stage already has for its own absent-log case, and re-running
the gate against a already-delivered project is not the intended flow.

[Journal milestone line text could drift if `skill/phase1_requirements.md`'s exact
wording changes] -> match on the stable prefix `phase1/dimensions_approved` (the part
`skill/resume.md` treats as the milestone key), not the full sentence, so the trailing
`<n> dimensions recorded` count staying free-form doesn't break detection.

## Open Questions

None -- scope is deliberately small; see Non-Goals for what was considered and cut.
