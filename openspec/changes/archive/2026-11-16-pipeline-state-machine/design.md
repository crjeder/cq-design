## Context

`build/journal.md` already records milestones (`skill/resume.md`) and `freshness.py` already hashes part scripts, but nothing reads them to decide what may run next. The next step is whatever Claude infers from `SKILL.md`. `documentation/pipeline.md` fixes the target: decision A (a state machine in `src/pipeline.py`), the loops-back table, and `edit` as an explicit plan-less route. This change covers steps 0-10 and 15-16 of that table; slicing steps 11-14 do not exist yet.

Constraints: stdlib only, no CadQuery import (cheap to call at every step); Python 3.10-3.12; JSON contract plus a test per `CLAUDE.md` "Program vs. prompt"; existing journals must stay readable.

## Goals / Non-Goals

**Goals:**
- One source of truth for "where is this run": route, done steps, allowed next steps, blocked steps with the unmet precondition.
- Reject an invalid transition with a typed error before anything is written.
- Model the loops back (re-approved dimensions void the plan approval, a changed part script voids its acceptance) without timestamps.
- Model `edit` as a first-class route.
- Resume and the builder prompt read the same status output.

**Non-Goals:**
- Gating individual tool calls: hooks never see sub-agent calls (see memory note on hooks), so enforcement is at milestone boundaries, not per call.
- Making `quality_gate.py`, `build.py` etc. refuse to run themselves. They can adopt `pipeline.py can` later.
- Steps 11-14 (slicing, G-code), the telemetry hook reading the state, rung 1-3 skip logic beyond treating `rung_decision` as optional.
- A persisted state file.

## Decisions

**D1. State is derived on every call, never stored.** `status` computes from `build/journal.md` (decisions) and artifacts (`BUILD_PLAN.json` part ids, `build/<id>.py` hash). Alternative: a `build/state.json`. Rejected: a second record drifts from the journal and the artifacts, which is the defect class being fixed (stale milestones, PR #250).

**D2. Order-based validity.** A journal line counts only if, in the current attempt (after the last `phase0/restart`), each prerequisite milestone appears earlier than it, using the latest occurrence of each. Re-appending `dimensions_approved` after `plan_approved` leaves `plan_approved` earlier than its prerequisite chain, so it and everything downstream read as void. Alternative: file mtimes, as `documentation/pipeline.md` words it ("newer than its inputs"). Rejected: mtimes are noisy across checkouts and copies (the reason `freshness.py` hashes); journal order is exact and already append-only.

**D3. Milestone table in code.** A dict `MILESTONES` maps each milestone key (with `<id>` placeholder for per-part ones) to `{prereqs, routes, optional}`. The table is the single definition; `skill/resume.md`'s milestone table remains the human-facing description and a test asserts the keys match it.

| Milestone | Prerequisites |
|---|---|
| `phase0/rung_decision`, `phase0/sourcing_skipped`, `phase1/topology_confirmed` | none (optional) |
| `phase1/dimensions_approved` | none |
| `phase2/plan_written` | `dimensions_approved` |
| `phase2/plan_approved` | `plan_written` |
| `phase3/stub_approved:<id>`, `escalation:<id>` | `plan_approved` (optional) |
| `phase3/part_accepted:<id>` | `plan_approved` |
| `phase3/design_approved` | `part_accepted:<id>` for every part id in `BUILD_PLAN.json` |
| `phase3/orientation_chosen` | `design_approved` |
| `phase3/assembly_written` | `orientation_chosen` |
| `phase3/gate_result` | `assembly_written` |
| `phase4/delivered` | `gate_result` (rung 3: `rung_decision` only) |

**D4. Part staleness by hash.** `part_accepted:<id>` lines carry `sha=<script_hash>` in their text (from `freshness.script_hash`). `status` recomputes the hash of `build/<id>.py`; a mismatch marks the part `stale` (not accepted) and, via D2-style dependency, blocks `design_approved`. A line with no `sha=` (old journals) is `unknown`, treated as accepted with a warning, matching `freshness.is_stale`'s "unknown is not stale" rule.

**D5. Routes.** `design` (phases 0-4), `plan` (stops at `plan_approved`; allowed next is empty and the status says `complete`), `edit` (stateless). The route is given by the caller (`--route`), defaulting to `design` when `build/journal.md` exists and `edit` never being inferred. Each command file passes its own route, so `/cq-design:edit` cannot be mistaken for a half-run design. On `edit`, `status` returns the fixed step list (import, modify, verify, export) without reading any file, and `advance`/`can` for `print_orientation`, `quality_gate`, plan and journal milestones return `route_forbids`. A missing plan or `build/` is never an error on this route.

**D6. CLI contract (JSON on stdout, exit 0/1).**
- `pipeline.py status [--route R] [--dir D]` -> `{route, attempt_start, done: [...], void: [{milestone, reason}], stale_parts: [...], allowed_next: [...], blocked: [{step, missing}], complete}`.
- `pipeline.py can <milestone> ...` -> `{ok, missing}`; exit 1 when not ok.
- `pipeline.py advance <milestone> <text>` -> checks `can`, appends via `log.append_line`, returns the line; on refusal writes nothing and emits `errors: [{type, message, hint}]` with types `prerequisite_missing`, `route_forbids`, `unknown_milestone`, `part_stale`.
Same `errors` shape as `run_cadquery_model.py`.

**D7. Existing writers stay.** `plan.py validate` and `write_assembly.py` keep appending their own line (`build-journal` spec). `status` validates them like any other line, so a script-written milestone with unmet prerequisites is void rather than blocked at write time. Alternative: make those scripts call `can` first. Deferred: it touches two more scripts and their tests for little extra safety.

**D8. Prose changes are small.** `resume.md`'s procedure step 4 becomes "run `pipeline.py status`, resume at `allowed_next[0]`"; the user still confirms. User-decision appends in `skill/phase*.md` switch from `log.py journal append` to `pipeline.py advance`. `render_prompt.py` adds one line to the builder prompt: the part id, its allowed steps, and "do not run steps beyond these" (the sub-agent scope limit).

## Risks / Trade-offs

- [Journal line without prerequisites written by an old skill version] -> `status` marks it void with a reason; resume shows it and asks the user, never deletes it.
- [Milestone table drifts from `skill/phase*.md`] -> test cross-checks the table against `skill/resume.md`'s milestone table.
- [Enforcement is advisory for sub-agents: nothing stops a builder from running a script] -> accepted; the check happens where main records milestones, which is where wrong-order runs became visible. Revisit with per-script `can` calls.
- [Hash in the journal text is a convention, not a schema] -> parsed with one regex; absent means unknown, never a failure.
- [Rung-3 shortcut wrongly applied] -> only a `rung <n>` parsed from the line opens it; malformed lines are void (D9).

## Migration Plan

Additive. Existing journals work unchanged (no `sha=` means unknown). The skill prose and `render_prompt.py` change in the same release as `pipeline.py`; projects pick it up through `/cq-design:update`. Rollback: revert the prose edits; `pipeline.py` is inert unless called.

**D9. Sourcing has its own status.** `status` carries `sourcing`: `pending` (no sourcing line), `skipped` (`phase0/sourcing_skipped`, written when the user says design from scratch or main skips triage for a custom part, decision B), or `rung_<n>` parsed from the `rung <n>` that opens the `rung_decision` text. Sourcing never blocks Phase 1 (it is optional). Only rung 3 (found mesh delivered as-is: no plan, no part script, no gate) changes the path: `phase4/delivered` then needs `rung_decision` instead of `gate_result`, and phases 1-3 are reported `skipped`. Rungs 1, 2, 4 re-author through the normal pipeline and are reported, not shortcut. A `rung_decision` line whose text lacks `rung <n>` is void with a reason.

**D10. Plan then design.** The route is per invocation and the journal is shared, so a `plan`-route run that reached `plan_approved` continues on the `design` route without re-planning; `status --route design` then lists the part loop in `allowed_next`.
