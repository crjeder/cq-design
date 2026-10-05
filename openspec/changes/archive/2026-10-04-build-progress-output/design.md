## Context

`build.py` runs `resolve_orientations` (loop over parts, then unions) and then `export_model` (load each part, write keep-out STLs, write `model.3mf`, write per-union STLs, fuse and write per-plate STLs). Both loops are silent. `export_model` is also called by `quality_gate.py` and by `model_export.main`, whose stdout is JSON.

## Goals / Non-Goals

**Goals:**
- A person watching `build.py` sees steady `[k/N]` progress.
- Other `export_model` callers are unchanged.

**Non-Goals:**
- A progress bar, a percentage, TTY detection, `\r` redraw, or a progress library.
- Weighting phases by cost; each phase counts its own units.
- Progress output from `model_export.main` or `quality_gate.py`.

## Decisions

- **Stdout, flushed.** Progress is not an error, and `build.py`'s stdout is a human summary that nothing parses. `print(..., flush=True)` avoids block buffering when stdout is piped. The `build failed:` message stays on stderr. Alternative, stderr: rejected, it implies a problem and splits one report across two streams.
- **Per-phase counters, no percentage.** Phase costs differ by orders of magnitude, so one overall percentage would stall and jump. Alternative, weighted overall percentage: rejected, the weights would be invented.
- **Callback, not a logger or a return value.** `export_model(..., progress: Callable[[str], None] | None = None)`, keyword-only, called with the full line text. `None` means silent, so existing callers need no change. The callback owns the I/O; `export_model` stays free of `print`.
- **`export_model` builds the `[k/N]` text.** It already knows `N` for each of its loops (parts from the plan, unions after loading, plates after grouping). Union-STL and plate totals are known once the load loop finishes, before those loops run.
- **Orientation phase counts only unions that need computing.** A pre-pass in `resolve_orientations` marks unions whose accepted entry is missing or stale (`is_stale` is a hash compare, cheap). Reused entries print nothing. `N` is the size of that set; if it is zero the phase prints nothing.
- **3MF is one line, no counter.** `write_named_3mf` is a single call over all objects.

## Risks / Trade-offs

- [The orientation pre-pass duplicates the staleness check that the main loop does] -> compute it once into a set and reuse it in the loop, so the check is not repeated.
- [Part-load lines count parts, while the union STL lines count unions, so `N` differs between phases] -> the step label (`loading`, `stl`, `plate`) makes the unit explicit.
- [`build-format-option` adds a per-union loop to `export_model`] -> if it lands first, give that loop its own `[k/N] <fmt>` line; otherwise nothing to do.

## Open Questions

- None.
