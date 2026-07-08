## 1. Author the anti-patterns companion

- [x] 1.1 Create `reference/CadQuery Anti-Patterns.md` with a header explaining it is the
      negative-space companion to `CadQuery Pattern Reference.md`, organized by durability
      tier, and three tier sections
- [x] 1.2 Tier 1 (Kernel-level / OCCT): `BREP_API command not done` causes (fillet radius vs
      shortest edge / overlapping fillets, self-intersecting profile, self-intersecting
      sweep, shell thickness vs local curvature), boolean-in-a-loop (batch into one compound,
      subtract once), unclosed wires, and the feature-ops-vs-booleans principle WITH the
      anchor rule (feature ops for bosses/holes/edges; booleans for combining separate solids
      and for cavities/enclosures where `.shell()` is fragile)
- [x] 1.3 Tier 2 (Stateful-context, "deleted under an algebra-mode API"): origin drift /
      `ProjectedOrigin`, losing solid context after a selector (`.end()`), `.val()` vs
      `.vals()`, `.each()` misuse, `.translate()` on a Workplane, index-selector fragility
      (with the note that the principle is broader but the tag fix is fluent-specific),
      hardcoded global coords. Cross-reference the main reference's "Workplane Context
      Stacking" and "Fresh Workplane Pattern" sections here instead of restating them
- [x] 1.4 Tier 3 (CadQuery API mechanics): `.extrude(combine=False)`, `.cutBlind()` normal
      direction / `workplane(invert=True)`, fluent-vs-func one-line "don't mix" note
- [x] 1.5 Confirm NO Free Function API (`cadquery.func`) content is present

## 2. Update the main pattern reference

- [x] 2.1 In `reference/CadQuery Pattern Reference.md` Sketch API section, add the
      `.placeSketch()` reusable-profile recipe
- [x] 2.2 In the Machining Operations section, add `.extrude(..., combine=False)` for a
      separate solid, and `.cutBlind()` with `.workplane(invert=True)` for cutting into the
      solid along the inverted normal
- [x] 2.3 Reconcile contradiction 1: in Common Gotcha #10 (boolean-cut over `.shell()`), add
      a back-reference to the boolean-usage anchor rule so the two do not read as opposed
- [x] 2.4 Reconcile contradiction 2: in Transform Operations, note `.translate()` applies to
      an extracted Shape / finished result, not as a mid-chain positioning primitive
- [x] 2.5 Reconcile contradiction 3: confirm the Fresh Workplane Pattern section reads
      consistently with "don't hardcode globals" (it uses a workplane frame); adjust wording
      only if it implies raw global placement
- [x] 2.6 Add an entry for the anti-patterns companion to the Table of Contents (and note it
      is a separate injected file, like `emboss_text.md`)

## 3. Wire the injection (SKILL.md)

- [x] 3.1 In SKILL.md "Setup" reference list (line ~389), add
      `reference/CadQuery Anti-Patterns.md` as always-loaded, appended after the pattern
      reference and before the conditional `emboss_text.md`
- [x] 3.2 In the `{{CQ_REFERENCE}}` placeholder row (line ~430), update the value to:
      pattern reference + anti-patterns companion (always), then `emboss_text.md` only for
      text/emboss parts
- [x] 3.3 In the "Quick reference: key files" table (line ~1075), add a row for
      `reference/CadQuery Anti-Patterns.md`

## 4. Close out tracking

- [x] 4.1 Mark the `README.md` line 176 upgrade-material row and `TODO.md` line 138 checkbox
      as done (or update them to reflect the func-API-excluded scope)
- [x] 4.2 Verify no test asserts the exact `{{CQ_REFERENCE}}` content (injection is
      Claude-inline, not a rendering function); if any reference-file-listing test exists,
      add the companion to its expected set
