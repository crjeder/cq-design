## Context

Several pipeline stages consume artifacts derived from a part script (`build/<part_id>.py`)
and none of them can tell whether the script changed since the artifact was produced:

- `build_template.resolve_orientations` reuses `build/orientations.json` whenever it exists,
  with no comparison against the part script.
- `kinematic_check.py`, `plate_clearance_check.py`, `keep_out_check.py` resolve assembled-pose
  STLs by path (`units.stl_path`) and check only `os.path.exists`.

The C5 Phone-Holder retrospective caught the orientation case live (`TODO.md`, "orientation
cache staleness"): a cached `build_height_mm` from round 4 silently disagreed with a
round-6 geometry edit, and nothing in the pipeline could have said so. See `proposal.md` for
the full incident writeup.

## Goals / Non-Goals

**Goals:**
- A stdlib-only provenance stamp (`src/freshness.py`) computed from a part script's contents.
- `print_orientation.py` and `model_export.py` record that stamp when they produce an
  artifact.
- `build_template.resolve_orientations` and the three whole-model check stages
  (`kinematic_check`, `plate_clearance_check`, `keep_out_check`) verify the stamp and react:
  recompute (orientations) or emit a blocking `stale_artifact` finding (checks).
- Absent provenance data (no manifest, unstamped orientation entry) degrades to today's
  behavior — reuse / `check_skipped` — never a hard failure.

**Non-Goals:**
- Hashing the block library or the bundled `lib/` tooling. A block edit can change geometry
  without touching the part script, but that is a much wider blast radius and a separate
  decision.
- Auto-re-running the export from inside a check stage. The stages stay read-only; they
  report and let the pipeline (or the user) act.
- Geometry-bbox comparison as the staleness key. Cheap, but misses any edit that preserves
  the bounding box — precisely the phone-holder pivot-move case.

## Decisions

### The stamp: SHA-256 of the part script's bytes

`src/freshness.py`:

```python
def script_hash(script_path: str) -> str: ...        # sha256 hex digest of file bytes
def is_stale(stamped_hash: str | None, script_path: str) -> bool: ...
    # None (no stamp) -> False ("unknown", not a mismatch)
    # otherwise -> stamped_hash != script_hash(script_path)
```

**Why the script, not the STL or the mtime.** The part script is what `model_export` and
`print_orientation` actually consume — hashing it is a one-line, dependency-free operation on
data every caller already has a path to. mtime is explicitly rejected: it is noisy across
checkouts, copies, and editors (a `git checkout` or `cp -p` can leave a stale mtime on
unchanged content, or a fresh mtime on unchanged content — the direction that matters here).
Hashing the exported STL instead would make the stamp circular (compare the artifact to
itself) rather than to its source.

### Two provenance carriers, one shared primitive

The proposal identifies two independent consumers with different shapes, so they get two
different carrier formats built on the same `freshness.py` primitive rather than a single
schema forced onto both:

1. **Orientation result (`build/orientations.json`)** — one JSON object per union, already
   free-form (`print_orientation.py`'s output dict). Gains one key: `source_script_hash`.
   `print_orientation.py` sets it when invoked with the new optional `--source-script`
   argument; omitted, the result carries no such key (unstamped).
2. **Export manifest (`stl/export_manifest.json`)** — new sidecar file written by
   `model_export.export_model`, since STL files themselves carry no metadata field to stamp.
   Shape:

   ```json
   {
     "exported_at": "2026-07-27T12:00:00+00:00",
     "unions": {
       "<union_id>": {"part_id": "<part_id>", "source_script_hash": "<sha256 hex>"}
     },
     "keep_out_zones": {
       "<part_id>::<zone_name>": {"part_id": "<part_id>", "source_script_hash": "<sha256 hex>"}
     }
   }
   ```

   `keep_out_zones` uses the same `"<part_id>::<zone_name>"` key `export_model` already
   returns in its `keep_out_stls` dict, so a zone's own freshness is checkable by the same
   mechanism as a union's — the zone is exported from the same script as its declaring part's
   real unions, so it can go stale exactly the same way.

`freshness.py` exposes both write and read sides so no consumer hand-rolls the JSON shape:

```python
MANIFEST_FILENAME = "export_manifest.json"
def write_manifest(stl_dir: str, union_scripts: dict[str, tuple[str, str]],
                    keep_out_scripts: dict[str, tuple[str, str]]) -> str: ...
    # value tuples are (part_id, script_path); returns the written path
def read_manifest(stl_dir: str) -> dict | None: ...  # None if the file is absent
```

### Where the check stages get a script path from

`kinematic_check.py`, `plate_clearance_check.py`, `keep_out_check.py` currently take only
`(plan, stl_dir)` — no directory of part scripts to re-hash. Each gains an optional
`parts_dir: str | None` parameter (and CLI `--parts-dir`). When `parts_dir` is `None`, or the
manifest is absent, the stage degrades to a `check_skipped` warning for the freshness check
specifically (distinct from the existing "STL not found" `check_skipped`) — it does not
withhold the rest of the stage's checks.

`quality_gate.run_gate` already derives `stl_dir` from `os.path.dirname(os.path.abspath(script_path))`
when not given explicitly; the same directory is where every part script lives (`build/`), so
`run_gate` passes `parts_dir=os.path.dirname(os.path.abspath(script_path))` to the three
whole-model stages with no new gate-level flag needed. Direct CLI use of the three check
scripts (tests, ad-hoc debugging) opts in via `--parts-dir`.

`iter_unions(plan)` already yields `(part, uid, plate)`, so each stage resolves a union's
owning part id from the plan itself — no separate id-to-part lookup needed.

### Staleness short-circuits validation of that union, not the whole stage

Consistent with how a missing STL already causes that check to skip validating the affected
entry (`continue`) rather than aborting the stage, a `stale_artifact` finding for a union
excludes that union from the geometry comparison that would otherwise run against it —
reporting stale geometry as a collision result would be validating (and possibly passing)
superseded geometry, which is the exact failure mode this change closes.

### `resolve_orientations`: recompute on mismatch, stamp the result either way

```python
for uid in union_ids:
    entry = accepted.get(uid)
    if entry is not None and not is_stale(entry.get("source_script_hash"), script):
        chosen = entry
    else:
        chosen = _orientation_for(...)          # existing recompute path
        chosen["source_script_hash"] = script_hash(script)
        if entry is not None:
            recomputed.append(uid)              # stale entry -> note in build summary
    ...
```

An entry with no `source_script_hash` (pre-change project, hand-edited file) is treated as
`entry is not None and not is_stale(None, script)` → `is_stale` returns `False` for `None` →
reused unconditionally, matching current behavior exactly. `_print_summary` gains a trailing
note listing which union ids were recomputed and why ("orientations.json stale for these
unions — part script changed since the orientation was accepted").

### `optimize_orientation()` itself stays hash-agnostic

The stamp is attached by the caller (CLI `main()` in `print_orientation.py`, or
`build_template._orientation_for`), not inside `optimize_orientation()`. The function's job is
scoring a mesh; it has no script path to hash (its input is already a loaded mesh) and adding
one would mean threading a path through a pure-geometry function for one caller's bookkeeping.

## Risks / Trade-offs

- **Hash cost.** A part script is a few KB of Python; hashing it is microseconds. No
  measurable cost even across dozens of parts.
- **A block-library edit still isn't caught** (explicitly out of scope). Documented in the
  proposal and here so it isn't mistaken for an oversight; a future change can extend the
  manifest to also stamp `blocks/` if this proves to matter in practice.
- **Two carrier formats instead of one.** Slightly more surface than a single schema, but
  forcing the orientation-result shape (free-form, already public in `orientations.json`) and
  the manifest shape (new, multi-union, needs an `exported_at`) into one format would either
  bloat the orientation result with fields only the manifest needs, or require
  `print_orientation.py` to know about plates/zones it has no reason to know about.
- **`parts_dir` threading.** Three call sites gain a new optional parameter. Mitigated by
  defaulting it from data `run_gate` already has, so the common path (through the gate) needs
  no new flag.

## Migration Plan

No data migration: this is additive (new optional fields, new sidecar file). A project
exported before this change has no manifest and no stamped orientation entries; every
consumer's degradation path (`check_skipped` warning / unconditional reuse) reproduces
today's behavior exactly, so existing deliverables keep building without modification.
