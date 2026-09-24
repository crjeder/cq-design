## Why

`request_log` entries can be typed `level: "parameter"` with `targets` naming the
part(s) a correction is scoped to, but nothing checks that the correction actually
stayed inside that scope. The C5 knuckle pivot ping-pong (`TODO.md`, "C5 knuckle
pivot ping-pong") reproduced exactly this: a request to raise the cradle's own
`EAR_STANDOFF` also got copy-edited into the plate's independently-typed `PIVOT_Z`,
a separate part's literal, because nothing routed the shared value through
`joints`/`mate_chain.py` and nothing flagged the sibling-part edit after the fact.
`shared-literal-detection` (merged in `2026-09-11-absence-lints-and-coordinate-frame`)
catches the *structural* half of this -- a plan with unlinked shared interfaces or
hinge language and no `joints` entry -- but it runs on `BUILD_PLAN.json` alone and
says nothing about which files a given correction round actually touched. A plan
that already declares a `joints` link, or one whose shared literal isn't expressed
as a declared `interfaces[]` entry at all, gets no signal when a `parameter`-level
correction still leaks into a sibling part's script. The typed-entry label
(`documentation/intent_recognition.md` gap, `TODO.md`'s "Typed request_log entries")
exists specifically to make this routing rule checkable; today it is decoration.

## What Changes

- `request_log_search.py`'s `add` command gains a `--snapshot-scripts <dir>` flag:
  when the appended entry has `level: "parameter"`, it hashes every part script
  found in `<dir>` (via `freshness.script_hash`) and stores the result on the entry
  as a new optional `script_baseline` field (`{part_id: sha256}`).
- `quality_gate.py` gains a new check stage, `check_parameter_routing`: for the
  newest `request_log` entry carrying a `script_baseline`, it re-hashes the current
  build directory's part scripts and diffs against the baseline. Any part whose
  script changed, whose id is absent from the entry's `targets`, and that is not
  linked to a targeted part by a `joints` entry's `members`, is reported as a
  `routing_violation` finding naming the entry's text, the targeted part(s), and
  the unexpectedly-changed part.
- `routing_violation` findings are advisory by default (this codebase's default for
  a judgment call without eval evidence -- see `request-relative-acceptance`'s same
  eval-gate rule for promoting advisory findings to blocking).
- `skill/phase3_build.md`'s correction-handling rule is extended: appending a
  `parameter`-level `request_log` entry SHALL pass `--snapshot-scripts build/` so
  the baseline is captured before the builder acts on the correction.
- `src/build_plan_schema.json` gains the optional `script_baseline` field on
  `request_log` entries (additive, existing plans without it are unaffected).

## Capabilities

### New Capabilities
- `parameter-routing-check`: `request_log_search.py add --snapshot-scripts`, the
  script-hash baseline it stores, the `quality_gate.py` drift check that diffs
  against it, the joint-linkage exemption, and the advisory `routing_violation`
  finding it produces.

### Modified Capabilities
- `request-log`: `request_log` entries gain the optional `script_baseline` field
  (schema), and the existing "applied only within its targets" requirement is
  updated from orchestrator-discipline-only to mechanically checked.

## Impact

- `src/build_plan_schema.json` -- new optional `script_baseline` field on
  `request_log` entries
- `src/log.py` (owns `request_log_search.py`'s CLI) -- `add --snapshot-scripts`,
  script hashing via `freshness.script_hash`
- `src/quality_gate.py` -- new `check_parameter_routing` stage
- `skill/phase3_build.md` -- correction-handling rule states the snapshot flag
- `tests/test_log.py`, `tests/test_quality_gate.py` -- new coverage
- `TODO.md` -- "Intent as invariant" residual-gap note updated once this lands
