## REMOVED Requirements

### Requirement: REQUIREMENTS.md written at Phase 1 approval

**Reason**: Five of the file's six sections restated structured fields that already carry
the same content in full -- the dimension table (`parameters.py`, `parts[].dimensions`),
fit requirements (`interfaces[]` and the clearance-by-fit-type table), and printer/DFM
constraints (`printer`/`material`/`nozzle_mm` and `printer_profile.json`) -- which the
project's own rule against narrating structured fields forbids elsewhere. The sixth
section, the resolved intent and its open assumptions, is now carried by the approved
`intent` field, which unlike this file is required, schema-validated, and read by Phase 2
and Phase 3.

**Migration**: The approved reformulation Phase 1 writes to `BUILD_PLAN.json`'s `intent`
replaces the "Intent", "Topology", "Fit requirements", and "Open questions / assumptions"
sections (see the `approved-intent` spec). "Dimensions" is already covered by
`parameters.py`, written at the same checkpoint. "Printer & DFM constraints" is already
covered by the plan's own fields plus `printer_profile.json`. Existing projects that
carry a `REQUIREMENTS.md` on disk keep it as an inert artifact; nothing reads it and
nothing updates it.

### Requirement: Every section present regardless of content

**Reason**: The requirement governs the layout of a file that is no longer written.

**Migration**: None -- `intent` is prose, not a sectioned template.

### Requirement: Amended in place by Phase 2, never regenerated

**Reason**: The requirement governs a file that is no longer written. The equivalent
maintenance rule for `intent` -- rewritten only on an approved correction, carried forward
unchanged by a re-plan -- lives in the `approved-intent` and `planning-phase` specs.

**Migration**: Phase 2 no longer amends `REQUIREMENTS.md`; it carries the approved
`intent` forward unchanged.

### Requirement: Journal milestone on write

**Reason**: The `phase1/requirements_written` milestone records the write of a file that
no longer exists.

**Migration**: The `phase1/dimensions_approved` milestone already records the Phase 1 exit
checkpoint, which now covers the approved intent as well; no replacement line is added.
