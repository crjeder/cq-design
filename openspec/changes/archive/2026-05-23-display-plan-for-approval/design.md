## Context

Phase 2 of the cq-design skill currently shows the raw `BUILD_PLAN.json` as a fenced JSON code block, then asks the user to approve or edit. Reviewers must mentally parse JSON structure, field names, and nesting to understand what the plan actually says -- making the approval step cosmetic rather than meaningful.

The change is confined to:
- `SKILL.md` Phase 2 description (the authoritative behavior spec for the skill)
- `openspec/specs/planning-phase/spec.md` requirement "Plan is shown to user for review"

No orchestrator code, no schema changes, no new dependencies.

## Goals / Non-Goals

**Goals:**
- Replace the raw JSON display with a structured human-readable summary
- Keep the approval gate (wait for user confirmation or edit before proceeding)
- Keep the disk write and re-validation-from-disk behavior unchanged

**Non-Goals:**
- Changing what goes into `BUILD_PLAN.json`
- Changing validation logic or schema
- Generating a separate "summary file" alongside `BUILD_PLAN.json`

## Decisions

### Decision: Markdown summary table, not prose

Show the plan as a set of compact Markdown sections (not free prose) so the structure is still scannable.

Proposed layout:
```
**Plan summary** -- Written to: `BUILD_PLAN.json`

**Printer / Material**
| Printer | Material | Nozzle |
| P1S     | PLA      | 0.4 mm |

**Parts**
| # | ID         | Description        | W x D x H (mm)    | Blocks           |
|---|------------|--------------------|--------------------|------------------|
| 1 | body       | main enclosure     | 80 x 50 x 30       | hollow_box       |
| 2 | lid        | snap-fit lid       | 80 x 50 x 3        | snap_hook_clip   |

**Interfaces** (one row per interface across all parts)
| Part | Type         | Connector | Wall | Position (mm)   |
|------|--------------|-----------|------|-----------------|
| body | port_cutout  | usb_c     | west | [40, 0, 15]     |

**Assembly strategy** (multi-part only)
<one-line assembly description from plan>

**Constraints**
| Wall min | Overhang max | Dim tolerance |
| 1.2 mm   | 45 deg       | 0.2 mm        |
```

Alternative considered: show raw JSON alongside the table. Rejected -- the table already contains all the information a user needs to approve; showing JSON too would be noise.

### Decision: Raw JSON is never displayed in chat

The file path and a note that the full JSON is on disk are sufficient. Users who want to inspect it can open the file.

## Risks / Trade-offs

- [Risk] Summary table omits fields the user cares about (e.g. `print_orientation`) → Mitigation: add `print_orientation` column to the Parts table; extend with additional rows if the spec adds new fields
- [Risk] Summary diverges from on-disk JSON if skill-side rendering has a bug → Mitigation: the disk write + validation step runs before display, so the JSON is authoritative regardless of how the summary looks

## Open Questions

None.
