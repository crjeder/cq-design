## 1. Schema

- [x] 1.1 Add `name` to the `parts[].interfaces[]` item schema in
      `src/build_plan_schema.json`: `{"type": "string", "pattern": "^[a-z][a-z0-9_]*$",
      "description": "..."}`, optional (not added to the item's `required` list), placed
      alongside the other placement fields (design D1, D2)
- [x] 1.2 Extend `_hint_for_error` in `src/plan_validate.py` so a pattern violation on an
      interface `name` yields an actionable hint stating the normalization rule
      (lowercase, spaces and hyphens to underscores), not a bare regex

## 2. Uniqueness cross-check

- [x] 2.1 Add `_check_interface_names(plan)` to `src/plan_validate.py`, modeled on
      `_check_unions`: per part, collect declared `interfaces[].name` values, skip
      interfaces with no `name`, and append an error naming the part and the duplicated
      name on collision (design D3, D4, D5)
- [x] 2.2 Note the deliberate per-part (not model-wide) scope in the helper's docstring,
      contrasting it with `_check_unions`
- [x] 2.3 Wire `errors.extend(_check_interface_names(plan))` into `validate_plan`
      alongside the existing cross-check calls

## 3. Tests

- [x] 3.1 `tests/test_plan_validate.py`: a plan whose interface declares
      `name: "inner_lip"` validates clean
- [x] 3.2 `tests/test_plan_validate.py`: `name: "Inner Lip"` and `name: "inner-lip"` are
      each rejected with a schema error naming the field
- [x] 3.3 `tests/test_plan_validate.py`: two interfaces on one part named `mount_hole` are
      rejected with an error naming that part and the duplicated name
- [x] 3.4 `tests/test_plan_validate.py`: the same name on two different parts validates
      clean, and a part with three unnamed interfaces validates clean
- [x] 3.5 Run `uv run pytest tests/test_plan_validate.py tests/test_eval_corpus.py` and
      confirm all 11 golden plans still validate unchanged

## 4. Spec store reconciliation

- [x] 4.1 Confirm the `planning-phase` delta in
      `openspec/changes/add-interface-name-field/specs/planning-phase/spec.md` matches
      what landed in code, and run `openspec validate --change add-interface-name-field`

## 5. End-to-end verification

- [x] 5.1 Author a scratch plan with one part carrying two named+positioned interfaces,
      validate it, and render it via
      `run_cadquery_model.py --preview --callout ... --unlocated-name ...` as
      `skill/phase3_build.md` Step 3 would; eyeball the tile for correct badge placement
      and a legend matching the names verbatim (design: first real-plan exercise of the
      callout overlay) -- verified: scratch part with two named holes rendered badges 1/2
      on the correct features and legend "1 mount_hole_a  2 mount_hole_b"
- [x] 5.2 Update the `TODO.md` request-log-to-cross-section item: the `interfaces[].name`
      BLOCKER note is resolved, leaving the name-to-position join available
- [x] 5.3 Delete the stale workaround memory at
      `C:\Users\puck-\.claude\projects\D--Code-cq-design\memory\skill_gap_interfaces_name_field.md`
      (or mark it RESOLVED in the same style as the other resolved skill-gap memories) and
      update its `MEMORY.md` index line
