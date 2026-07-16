## 1. Audit and carve

- [x] 1.1 Confirm the section-to-destination table from design.md against current
  SKILL.md headers; decide the Prerequisites question (default: move to
  `skill/setup.md` with a core pointer)
- [x] 1.2 Create `skill/phase1_requirements.md`, `skill/phase2_planning.md`,
  `skill/phase3_build.md`, `skill/phase4_deliver.md` with the phase sections moved
  verbatim (Phase 3 also absorbs Block library detail and Kinematic validation)
- [x] 1.3 Create `reference/hardware_dims.md` from the Hardware dimension reference
  section

## 2. Rewrite the core

- [x] 2.1 Reduce each SKILL.md phase section to summary + MUST-read pointer
  (SKILL_DIR-relative path); keep contracts (JSON contract, error table, DFM
  values, coordinate system, script rules, quick reference) in place
- [x] 2.2 Add the hardware_dims.md block-gated read rule where fastener blocks are
  introduced
- [x] 2.3 Verify core SKILL.md is under 10 KB (`wc -c`)

## 3. Consistency pass

- [x] 3.1 Grep openspec/specs and CLAUDE.md for SKILL.md section citations; update
  any that now point into skill/ files
- [x] 3.2 Update CLAUDE.md file layout with `skill/` and `reference/hardware_dims.md`
- [x] 3.3 Content-preservation check: every line removed from SKILL.md phase
  sections exists in exactly one new file (diff of sorted content)
- [x] 3.4 Dry-run each entry point (`/render`, `/deliver`, full request) against the
  new core text: confirm each names the files it must read and no procedure is
  reachable only from memory
