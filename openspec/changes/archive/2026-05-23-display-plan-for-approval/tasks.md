## 1. Update spec

- [x] 1.1 Archive the delta spec into `openspec/specs/planning-phase/spec.md` by replacing the "Plan is shown to user for review before loop starts" requirement block with the updated version from the change's delta spec

## 2. Update SKILL.md

- [x] 2.1 Replace the Phase 2 plan-display prose in `SKILL.md` with the human-readable summary format: show the written path, then emit a Markdown summary with Printer/Material, Parts, Interfaces, Assembly strategy, and Constraints sections -- no raw JSON in chat
- [x] 2.2 Add a note that the summary is shown before asking for approval, and that the user may edit `BUILD_PLAN.json` on disk before confirming

## 3. Verify

- [x] 3.1 Read the updated `SKILL.md` Phase 2 section and confirm it matches the spec scenarios: no JSON in chat, all required summary sections present, approval gate described, re-validation-from-disk described
- [x] 3.2 Read the updated `openspec/specs/planning-phase/spec.md` and confirm the modified requirement contains all seven scenarios from the delta spec
