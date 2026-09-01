## 1. `verify_seated` helper

- [ ] 1.1 Add `verify_seated(support, boss, axis, label="", overlap=1.0)` to
      `src/cq_verify.py`, reusing `_AXIS_TOKENS`, `_solid`, and `_fail`; compute the
      bite depth as `support`'s bbox overreach past `boss`'s tangent face on `axis`
      and raise `_fail("boss_swallowed", label, ...)` when it exceeds `overlap`.
- [ ] 1.2 Add unit tests to `tests/test_cq_verify.py`: bite-past-tangent raises,
      correctly-seated-at-tangent passes, deliberate embed within `overlap` passes.

## 2. Wrapper typed-error mapping

- [ ] 2.1 Add `boss_swallowed` to `run_cadquery_model.py`'s marked-error ->
      typed-error mapping, alongside `unbacked_mate` and the other `cq-verify:*`
      types.
- [ ] 2.2 Add an end-to-end test to `tests/test_run_wrapper.py` (mirroring
      `test_unbacked_mate_end_to_end`): a script that calls `verify_seated` on a
      center-seated riser/knuckle produces a `boss_swallowed` entry in `errors`.

## 3. Authoring guidance

- [ ] 3.1 Add the pin-hinge routing rule (build a print-in-place revolute knuckle
      hinge via `blocks.joints.pin_hinge`; hand-rolled joins declare
      `verify_seated`) to `prompts/part.md`'s enumerated contract-rule list.
- [ ] 3.2 Mirror the same rule in `SKILL.md`'s generated-script rules.
- [ ] 3.3 Add the `boss_swallowed` risk point (flat support seated at a round
      feature's center) to the `cq_verify` guard-placement guidance already in
      `prompts/part.md` / `skill/phase3_build.md`.

## 4. Verification

- [ ] 4.1 Run `uv run pytest tests/test_cq_verify.py tests/test_run_wrapper.py`.
- [ ] 4.2 Re-check the C5 cradle knuckle example from `TODO.md` ("C5 hinge ear
      center-vs-edge") against `verify_seated` by hand (numbers only, no need to
      regenerate the part) to confirm it would have fired.
