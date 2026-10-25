## ADDED Requirements

### Requirement: Geometry-driven auto sections fill remaining cut slots

`render_preview.py` SHALL accept `--auto-sections`. When set, it SHALL behave as if `--cross-sections` were also set. It SHALL call `section_select.select_sections` on the whole model, passing the `--extra-section` cuts as `reserved`, and SHALL append the selected cuts after the `--extra-section` cuts until there are at most 3 cuts in total. When there are no extra-section cuts and the selector returns none, the renderer SHALL fall back to the three bounding-box-center cuts. If the selector raises, the renderer SHALL print a warning to stderr and continue as if nothing had been selected. `run_cadquery_model.py --preview --auto-sections` SHALL forward the flag, and the builder's rendered validate command SHALL include it.

#### Scenario: Auto cut through an off-center bore

- **WHEN** a box with a through-hole at x=10 is rendered with `--auto-sections` and no `--extra-section`
- **THEN** a section file `*_section_x_10mm.png` is written and no bbox-center section files are written

#### Scenario: Extra sections reserve slots

- **WHEN** `--extra-section y=0` is given together with `--auto-sections`
- **THEN** the cuts are the y=0 cut first, followed by at most 2 selector cuts

#### Scenario: Plain box falls back to center cuts

- **WHEN** a part with no bores is rendered with `--auto-sections`
- **THEN** the three bounding-box-center section files are written

#### Scenario: Selector error only warns

- **WHEN** `select_sections` raises
- **THEN** a `WARNING` naming `--auto-sections` is printed to stderr and the preview still succeeds with the fallback cuts

#### Scenario: Wrapper forwards the flag

- **WHEN** `run_cadquery_model.py --preview --auto-sections` runs on a part with an off-center bore
- **THEN** `previews` includes the auto-selected section file
