## Context

`skill/phase3_build.md` Step 5 ("Log the attempt (always, before retrying or
advancing)") already prescribes exactly one `telemetry.py append` per attempt,
including correction rounds, and says skipping it loses the measurement baseline.
Verification of the TODO item's first half is therefore done: the prescription
exists and is unambiguous. What is missing is any consequence for ignoring it --
`build/attempts.jsonl` is written purely by convention, so the C5 Phone-Holder
session (7 correction rounds) delivered with no log and nothing noticed.

The gate (`src/quality_gate.py`) is the only place that already runs
once-outside-the-fix-loop model-level stages (kinematic, plate clearance,
keep-out, edge treatment, feature presence, cosmetic slope) and whose report
(`build/quality_gate.json`) Phase 4 reads when reporting delivery. It is the
existing hook; nothing new is needed to carry the signal.

## Goals / Non-Goals

**Goals:**
- Make an unwritten telemetry log visible at delivery instead of silent.
- Keep it advisory: geometry is unaffected, so it must never fail the gate.

**Non-Goals:**
- Auto-writing the telemetry record from the gate. The gate cannot know the
  attempt number, prompt size, or executing model -- only the part loop can.
- Per-part or per-attempt completeness auditing ("every part in the plan has at
  least one record", "attempt numbers are contiguous"). Presence is the signal
  the reported failure mode needs; completeness is a separate, larger check.
- Changing `src/telemetry.py`, the record schema, or the JSONL format.

## Decisions

**D1. Detection lives in the gate, not in a new script.** The gate already
aggregates model-level findings into the structure Phase 4 reports. A dedicated
`telemetry_check.py` would be a second file, a second CLI, and a second call site
in the skill for a check that is a file-existence test. Rejected.

**D2. Presence, not schema validation.** The check counts parseable JSON lines
and stops at the first one. `telemetry.py` already validates on write and refuses
to write partial lines, so re-validating records at read time re-implements a
guarantee the writer holds. A file with at least one parseable record proves the
loop ran the helper at least once, which is exactly the failure mode observed.

**D3. `warning`, never `error`.** A missing log says nothing about the model's
printability. Making it an error would fail delivery on a purely procedural
lapse and would tempt a session to write a placeholder record to get past the
gate -- worse than no data.

**D4. Path defaults to the part-script directory.** `run_gate` already derives
`parts_dir` from `script_path` for the freshness check; the telemetry log lives
in that same `build/` directory. Reusing that derivation means no new plumbing
and no assumption about the working directory. A `--attempts-log` override
covers layouts where the gate is invoked from elsewhere.

**D5. Emitted once per gate run.** The gate is invoked per part, so a multi-part
model produces one warning per part -- acceptable duplication for zero extra
machinery. Deduplicating would require model-level state the gate does not keep.

## Risks / Trade-offs

- **Repeated warning noise on multi-part models** (one per gate invocation) →
  the Phase 4 report collapses it to a single line naming the missing log; the
  duplication only shows in raw `quality_gate.json`.
- **Presence check passes on a log with one stale record from an earlier
  session** → accepted. Append-only logs are explicitly durable across sessions
  (`attempt-telemetry` spec), so distinguishing "this session's records" needs a
  session id the format does not carry. Out of scope; noted for a follow-up if
  the weaker signal proves insufficient.
- **A session could satisfy the check with a junk record** → mitigated by D3:
  since the finding never blocks, there is no incentive to game it.
