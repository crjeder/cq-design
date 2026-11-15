## Why

The print-orientation search scores every candidate with exact, full-mesh work. On the Silica-tray part (1.29M faces, 112 candidates, ~530 copied retention posts) one union takes ~54 s, and the cost grows with faces x candidates. The user previously skipped the search for that part as "too slow". Most of the exact work cannot change the winner: bridge detection only discounts a candidate's support cost, so a cheap normals-only bound already rules out almost every candidate.

## What Changes

- Add a normals-only (vectorized) pre-pass that computes, for every candidate, the raw support cost (an upper bound on the exact cost) and a lower bound (`BRIDGE_COST_FACTOR` x raw), plus strength, build height, visual and bed contact, without copying or transforming the mesh per candidate.
- Run the exact bridge-aware support evaluation only for candidates that can still win under the active `optimize_for` mode, in ascending lower-bound order, stopping once the next lower bound cannot beat the incumbent.
- Selection result is identical to the exhaustive search (same rotation, same reported scores for the chosen pose).
- Allow `orientation_for` to tessellate its throwaway STL at a coarser tolerance for scoring, controlled by an explicit parameter whose default keeps current fidelity until validated.
- Progress line per search (already added): candidate i/N, elapsed, ETA.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `print-orientation-optimization`: candidate scoring may skip exact evaluation of candidates provably unable to be selected, provided the selected orientation and its reported scores equal those of exhaustive scoring; the search reports progress.

## Impact

- `src/print_orientation.py` (`optimize_orientation` loop, new bound helpers), `src/mesh_io.py` (raw/bounded support cost helper), `src/print_finishing.py` (`orientation_for` tessellation parameter).
- `src/build_template.py` / generated `build.py` pass progress (done).
- Tests: `tests/test_print_orientation.py` gains an exhaustive-vs-pruned equivalence test over existing fixtures.
- No JSON contract change; `candidates` internals are not part of the output.
