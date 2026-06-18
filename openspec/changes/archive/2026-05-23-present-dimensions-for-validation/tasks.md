## 1. Update SKILL.md Phase 1

- [x] 1.1 Add instruction to Phase 1 to announce each dimension lookup before starting it (product name + source URL)
- [x] 1.2 Add instruction to Phase 1 to report the found value and source after each lookup completes

## 2. Add Dimension-Validation Checkpoint to SKILL.md

- [x] 2.1 Add a new "Dimension validation checkpoint" section between Phase 1 and Phase 2 in SKILL.md
- [x] 2.2 Specify the table format (Item / Value mm / Source / Status columns) and the four status values
- [x] 2.3 Add the hard-pause instruction: "Do not generate BUILD_PLAN.json until the user approves or corrects the table"
- [x] 2.4 Add instruction: if user corrects a value, use the corrected value in the plan

## 3. Update SKILL.md Phase 2

- [x] 3.1 Add a note to Phase 2 that it starts only after the dimension checkpoint is approved
- [x] 3.2 Add a note that user-corrected values take precedence over looked-up values when populating BUILD_PLAN.json
