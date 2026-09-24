## Context

`BUILD_PLAN.json`'s `request_log` entries can carry `level` (`functional` |
`operation` | `parameter`) and `targets` (part ids / `part.feature` names), added
by the `2026-09-01-typed-request-log` change. Nothing reads `level`/`targets` to
enforce anything -- they are recorded metadata only. `request-relative-acceptance`
(same date) reads `targets` to *scope which request text a reviewer sees*, but a
review only judges the render, not which files the builder actually touched to
produce it.

`shared-literal-detection` (`2026-09-11-absence-lints-and-coordinate-frame`) is
the nearest existing guard against the same underlying failure mode -- a shared
literal (a pivot Z, a bore diameter) re-diverging between two independently-typed
part scripts. It runs in `plan.py validate`, purely on the `BUILD_PLAN.json` dict:
it flags a *structural* gap (two parts share a named/positional interface, or the
plan uses hinge/pivot language, with no `joints` entry linking them). It has two
blind spots this change closes: (1) a plan that already declares a correct
`joints` link can still have a *specific correction round* leak into a sibling's
script -- the structural check only runs once, at validate time, and says nothing
about what a given round actually edited; (2) a shared literal that isn't
expressed as a declared `interfaces[]` entry at all (the actual C5 case: `PIVOT_Z`
was a bare literal in both scripts, not modeled as a shared interface) gets no
signal from a plan-structure check no matter how many times it re-runs.

`quality_gate.py`'s `run_gate` already runs once per part, already loads the full
plan, and `freshness.py` already provides a stdlib-only script-hash primitive
(`script_hash`) used by the export-manifest staleness check. This change composes
those two existing pieces rather than adding a new whole-model script or a new
check module.

## Goals / Non-Goals

**Goals:**
- Detect, mechanically, when a `parameter`-level correction scoped to part(s) A
  results in a script change to an unrelated part B.
- Reuse the `intent_ts` reconciliation pattern (stamp at write time, diff-check at
  read time) and `freshness.script_hash` rather than inventing a new mechanism.
- Keep the finding advisory, consistent with this codebase's default for a
  judgment-call check with no eval evidence yet (`request-relative-acceptance`
  sets the same bar for its findings).
- Stay additive: plans and `request_log` entries with no `script_baseline` are
  unaffected, exactly like `level`/`targets` before them.

**Non-Goals:**
- Not a replacement for `shared-literal-detection`; the two are complementary
  (structural absence-of-joints vs. this-round's-actual-file-drift).
- Not promoting the finding to blocking. That needs eval evidence, same
  condition `request-relative-acceptance` already states for its own findings.
- Not auto-fixing the drift or auto-routing the value through `joints`/
  `mate_chain.py` -- this only surfaces that it happened.
- Not covering `functional`/`operation`-level entries. A `functional` correction
  (add/remove a part) or an `operation` correction (change how a feature is made)
  legitimately touches whatever files it needs to; only `parameter` entries carry
  the "design otherwise fixed" premise that makes an out-of-scope file change a
  signal rather than noise.

## Decisions

**Baseline capture point: `request_log_search.py add --snapshot-scripts <dir>`,
called by the orchestrator before acting on a `parameter`-level correction.**
Mirrors `--reconciled`'s existing opt-in-at-append-time shape. Alternative
considered: compute the baseline automatically inside `quality_gate.py` the first
time it sees a new `parameter` entry with no baseline yet. Rejected: the whole
point is a *before* snapshot; by the time `quality_gate.py` next runs, the
builder has already edited files, so an automatic baseline computed there would
capture the post-edit state and detect nothing.

**Where the check runs: inside `quality_gate.py`'s existing per-part `run_gate`,
not a new whole-model script.** `run_gate` already loads `plan` in full and knows
`script_path`'s directory (`build/`), where every part's `<id>.py` lives by
convention (`skill/phase3_build.md`'s existing `--script build/<part_id>.py`
calls). Alternative considered: a new whole-model script alongside
`plate_clearance_check.py`/`keep_out_check.py`. Rejected: those exist because
their checks need every part's *STL* simultaneously (geometry across unions);
this check only needs to hash small `.py` text files, which is cheap enough to
redo on every `run_gate` call without a separate whole-model pass or new CLI
entry point.

**Scope of the diff: hash every `<part_id>.py` present in the script's directory
on each `run_gate` call, not just the part currently being gated.** This catches
the violation on the very next gate call for *any* part, rather than waiting
until the drifted sibling itself happens to be re-gated (which, per
`skill/phase3_build.md`'s final-delivery pass, gates every part eventually, but
not necessarily right after the offending round). Cost is negligible: build
directories hold a handful of small scripts.

**Joint-linkage exemption: two parts are exempt from each other if any
`joints[].members` entry has one member's `part` matching each.** Reuses the
existing schema field with no new one; matches `shared-literal-detection`'s own
"a `joints` entry linking them silences the finding" rule, so the two checks
agree on what counts as "properly routed."

**Baseline selection: only the newest `request_log` entry carrying a
`script_baseline` is checked.** An older entry's baseline is superseded by the
newer one's (or by an entry with no baseline at all, e.g. a `clarification`,
which means "nothing pinned since then" and the check is skipped until the next
`parameter` entry with `--snapshot-scripts`). Matches `intent_ts`'s "only the
newest reconciliation matters" semantics.

## Risks / Trade-offs

- [Orchestrator forgets `--snapshot-scripts`] -> No baseline is recorded, so the
  check silently has nothing to compare -- same fail-open behavior as `intent_ts`
  before its own enforcement landed. Mitigated by stating the flag in
  `skill/phase3_build.md`'s correction-handling rule (prose, same enforcement
  ceiling as the `level`/`targets` labels themselves already have).
- [False positive: a legitimate derived-value change routed correctly through
  `joints`/`mate_chain.py` still touches a sibling's script] -> Exempted via the
  joint-linkage rule above. A plan that legitimately shares a value *without* a
  `joints` entry (the exact anti-pattern this change exists to catch) will still
  flag -- that is the intended behavior, not a false positive.
- [Directory convention assumption: sibling scripts live at
  `<script_path's dir>/<part_id>.py`] -> Matches every existing
  `skill/phase3_build.md` invocation (`--script build/<part_id>.py`). If a part
  script is genuinely absent from that directory (not yet built this round), it
  is simply skipped -- absence is not evidence of drift.
- [Advisory-only means the LLM can ignore the finding] -> Same ceiling every
  other advisory check in this pipeline has today; promotion requires eval
  evidence per the Non-Goals above.

## Migration Plan

Additive only: new optional schema field, new optional CLI flag, new check
function gated on that field's presence. No existing plan, entry, or test
changes behavior. No rollback beyond reverting the change.

## Open Questions

- Should `check_parameter_routing` also run as a standalone CLI (like
  `plan_validate.py validate`) for a human to invoke mid-build without a full
  gate pass? Deferred -- no caller needs this yet; add if `skill/phase3_build.md`'s
  correction-handling flow wants an earlier signal than the next `run_gate` call.
