## 1. Tag FDM Guidelines File

- [x] 1.1 Add `<!-- applies_to: always -->` to "Basic Dimension Rules" and "Wall Thickness" sections
- [x] 1.2 Add `<!-- applies_to: snap_hook_clip, snap_socket_receiver -->` to "Snap-fit" section
- [x] 1.3 Add `<!-- applies_to: screw_boss, pcb_standoff -->` to "Screw Mount Structure" section
- [x] 1.4 Add `<!-- applies_to: hollow_box, fillet_box -->` to "Fillets (Corner Rounding)" section
- [x] 1.5 Add `<!-- applies_to: always -->` to "Print Orientation Considerations" section
- [x] 1.6 Add `<!-- applies_to: port_cutout, cable_slot -->` to "Holes & Openings" section
- [x] 1.7 Verify: read back the file and confirm all sections have a tag

## 2. Add Helpers to orchestrate.py

- [x] 2.1 Add `_load_full_reference(path: str) -> str` that reads and returns the file contents
- [x] 2.2 Add `_load_reference_sections(path: str, block_names: list[str]) -> str` that parses `<!-- applies_to: ... -->` tags and returns matching sections plus `always` sections
- [x] 2.3 Write a quick manual test: call `_load_reference_sections` with `["snap_hook_clip"]` and confirm only snap-fit + always sections are returned

## 3. Update orchestrate.py Render Functions

- [x] 3.1 In `build()`, load CQ reference and raw FDM file content once before the part loop
- [x] 3.2 Update `_render_part_prompt` signature to accept `cq_ref: str` and `fdm_path: str`; add `{{CQ_REFERENCE}}` and `{{FDM_GUIDELINES}}` to its replacements dict (FDM filtered by part's `blocks_needed`)
- [x] 3.3 Update `_render_assembly_prompt` signature to accept `cq_ref: str`; add `{{CQ_REFERENCE}}` to its replacements dict
- [x] 3.4 Update all call sites of both render functions in `build()` to pass the new arguments

## 4. Update Prompt Templates

- [x] 4.1 In `prompts/part.md`: add `{{FDM_GUIDELINES}}` section (e.g., "## FDM Design Guidelines") and `{{CQ_REFERENCE}}` section (e.g., "## CadQuery Reference") near the bottom
- [x] 4.2 In `prompts/part.md`: remove the "Common Modeling Patterns" section (superseded by CQ reference)
- [x] 4.3 In `prompts/part.md`: remove the "Rules" section bullet items that duplicate FDM guideline content (keep coordinate vocabulary and block-import rules)
- [x] 4.4 In `prompts/assembly.md`: add `{{CQ_REFERENCE}}` placeholder section near the bottom
- [x] 4.5 In `prompts/planning.md`: add `{{FDM_GUIDELINES}}` placeholder section near the bottom

## 5. Update SKILL.md

- [x] 5.1 Add a note to the "Phase 1: Planning" section documenting that `{{FDM_GUIDELINES}}` must be substituted when rendering `planning.md`, using `_load_reference_sections` with the union of all `blocks_needed` across all parts (or all `always` sections if the plan is not yet known)

## 6. Update Tests

- [x] 6.1 In `test_orchestrate.py`: update any assertion that inspects rendered prompt content to expect `{{CQ_REFERENCE}}` and `{{FDM_GUIDELINES}}` to be expanded (not literal placeholder strings)
- [x] 6.2 Add a test for `_load_reference_sections` covering: matching block, non-matching block, `always` tag, missing tag (excluded)
- [x] 6.3 Run the full test suite and confirm all tests pass
