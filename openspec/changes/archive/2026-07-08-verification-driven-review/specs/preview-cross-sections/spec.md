## REMOVED Requirements

### Requirement: Cross-section views are appended to the multi-view tile
**Reason:** Sections are no longer part of the preview tile. The default tile is the
2x2 first-angle projection (`cq-preview-rendering`), and cross-sections are written as
separate files so the review can open and scrutinize each one against a specific
verification question. Replaced by "Cross-section views are written as separate files
through declared positions".

### Requirement: render_preview.py exposes --cross-sections flag
**Reason:** The flag's behavior changed from appending a section row to the tile to
writing separate section files through caller-supplied declared positions. Replaced by
"render_preview.py exposes --cross-sections producing separate files".

### Requirement: run_cadquery_model.py forwards --cross-sections
**Reason:** The wrapper now also forwards the declared feature/union section positions,
and the resulting section files land in `previews[1:]` after the tile. Replaced by
"run_cadquery_model.py forwards --cross-sections with declared positions".

## ADDED Requirements

### Requirement: Cross-section views are written as separate files through declared positions

When cross-section rendering is enabled, the renderer SHALL write each cross-section as
a **separate PNG file**, not append it to the multi-view tile. Each section SHALL be
cut through a declared feature or union position supplied by the caller (from
`BUILD_PLAN.json` interfaces/unions), so a section actually crosses the geometry a
review question is about. When no positions are supplied, the renderer SHALL fall back
to the three bounding-box-center cuts (Section X, Section Y, Section Z). The separate
section paths SHALL be returned in `previews[1:]` (the default tile stays
`previews[0]`).

#### Scenario: Section written through a declared junction

- **WHEN** the caller supplies a union-junction position and requests cross-sections
- **THEN** a separate section PNG cut through that position is written and its path
  appears in `previews[1:]`, and the default `previews[0]` tile is unchanged

#### Scenario: Fallback to center cuts

- **WHEN** cross-sections are requested with no declared positions
- **THEN** three separate section files are written for the bounding-box-center X, Y,
  and Z cuts

#### Scenario: Boolean cut failure degrades gracefully

- **WHEN** a cross-section Boolean cut raises an OCC exception
- **THEN** that section file is skipped with a warning to stderr and the remaining
  sections and the default tile are produced normally

### Requirement: render_preview.py exposes --cross-sections producing separate files

The `render_preview.py` CLI SHALL accept an optional `--cross-sections` flag that, when
present with `--views multi`, writes the section views as separate files (through
caller-supplied declared positions when provided, else the center cuts). It SHALL have
no effect when `--views iso` is used. The section cut positions SHALL be threadable from
the caller (e.g. a repeatable `--section-through`/`--extra-section` position list).

#### Scenario: --cross-sections flag writes separate section files

- **WHEN** `python src/render_preview.py --script model.py --output preview.png
  --cross-sections` is run
- **THEN** the script exits 0, `preview.png` is the 2x2 tile, and one section PNG per
  cut is written as a separate file

#### Scenario: --cross-sections ignored for iso view

- **WHEN** `python src/render_preview.py --script model.py --output preview.png --views
  iso --cross-sections` is run
- **THEN** the script exits 0 and produces a single isometric view (flag silently ignored)

### Requirement: run_cadquery_model.py forwards --cross-sections with declared positions

`run_cadquery_model.py` SHALL accept a `--cross-sections` flag and, when present with
`--preview`, forward it to `render_preview.py` along with the section positions derived
from the part's declared feature/union positions. The flag SHALL only be forwarded when
`--preview` is also set. The resulting section-file paths SHALL appear in the JSON
output's `previews` array after the default tile.

#### Scenario: Wrapper forwards flag and positions to renderer

- **WHEN** `run_cadquery_model.py model.py --preview --cross-sections` is invoked with
  declared feature positions available
- **THEN** `render_preview.py` receives `--cross-sections` and the section positions,
  and the JSON output's `previews` contains the default tile followed by one path per
  section file

#### Scenario: --cross-sections without --preview is a no-op

- **WHEN** `run_cadquery_model.py model.py --cross-sections` is invoked without `--preview`
- **THEN** no preview is rendered and the flag is ignored
