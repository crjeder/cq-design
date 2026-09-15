## 1. Trim skill/phase3_build.md

- [x] 1.1 In the "Post-delivery corrections" section (currently lines 267-283), replace
      the inline incident narrative ("before this section existed, doing so was a
      judgment call this file never actually asked for..." through "...left for the user
      to trigger later") with a link to `TODO.md#silica-tray-re-export-coincidence`.
- [x] 1.2 Confirm the rule itself survives verbatim in substance: a post-delivery
      geometry correction re-runs print-orientation, model export, and quality gate for
      the affected union(s) (unaffected unions keep their accepted
      `build/orientations.json` entry) before Phase 4's delivery report repeats.
- [x] 1.3 Keep the mention of the `source_script_hash` self-correction note if it adds
      information the rule depends on; otherwise fold it into the same trimmed
      paragraph or the linked TODO entry, whichever avoids duplication.

## 2. Verify

- [x] 2.1 Read the trimmed section back and confirm it reads as a complete, actionable
      rule without needing to open `TODO.md` to know what to do.
- [x] 2.2 Confirm `TODO.md#silica-tray-re-export-coincidence` still contains the full
      backstory the trimmed section used to carry inline.
