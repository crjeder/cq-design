## 1. Feature frame

- [x] 1.1 Add `src/feature_frame.py`: window, host-wall exclusion, bbox, snapped normal, depth, CLI printing JSON
- [x] 1.2 Tests: hole-in-wall, boss-on-plate, slot, no-geometry fixtures
- [x] 1.3 Add file lines to `FILES.md` and a contract entry to `reference/scripts.md`

## 2. Whole-part section scoring

- [x] 2.1 Add slice scorer next to `src/section_select.py` (15 slices per axis, score, dedupe vs reserved, time cap)
- [x] 2.2 Integrate with `render_preview._auto_cuts` (bore cuts first, scorer fills)
- [x] 2.3 Tests: U-profile and enclosure fixtures select the expected cut

## 3. Feature views and sheet

- [x] 3.1 Add `--feature` flag to `render_preview.py`; feature camera along normal, bbox framing, iso fallback
- [x] 3.2 Draw marker in detail and section renders; section through feature axis only when depth >= 0.5 mm
- [x] 3.3 Add `preview.render_sheet` composing up to 4 captioned tiles in a 2 x 2 grid; write full-size tile files too
- [x] 3.4 Add `--sheet` flag and forward both flags through `run_cadquery_model.py`
- [x] 3.5 Tests: tile cap of 4, "(not shown)" legend, marker pixel at projected anchor

## 4. Relevance ranking and command

- [x] 4.1 Add ranking in `src/render_prompt.py` (prompt mention, correction/clarification/ask_user, other mention, size) reusing the request_log helper
- [x] 4.2 Switch interface cut axis in `section_cuts` to the feature frame, keeping the wall fallback
- [x] 4.3 Emit `--feature` / `--sheet` from `validate_args`; tests for ranking order and cap
- [x] 4.4 Update `prompts/builder.md` to open the sheet first and drill into tile files

## 5. Verification

- [x] 5.1 Re-run the storage-shelf and an enclosure example end to end; check the sheet shows marked features and informative sections
- [x] 5.2 Close the TODO.md "Preview proactive detail renders" entry
