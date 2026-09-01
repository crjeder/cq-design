## 1. License verification (blocking prerequisite)

- [ ] 1.1 Confirm the redistribution terms of the Text-to-CadQuery dataset/code
      release (arXiv 2505.06507) and of `WKJBryan/cadquery-library`; record each in
      a `SOURCE_LICENSES` table in `evals/import_external_corpus.py` keyed by
      `--source` value.
- [ ] 1.2 The importer SHALL hard-error (no cases written) if `--source` names a
      value not present in `SOURCE_LICENSES`, rather than proceeding with an
      unknown license.
- [ ] 1.3 Cross-reference against the standing `TODO.md` "sbom, add credit for
      projects where code came from" item so the recorded licenses feed that work
      instead of duplicating it later.

## 2. Domain filter and sampling

- [ ] 2.1 In `evals/import_external_corpus.py`, add a keyword allowlist (enclosure,
      bracket, box, plate, adapter, bore, mount, stand, hook, clip, holder, hinge,
      standoff, lid, panel -- refine against a sample of real pair descriptions
      during implementation) matched case-insensitively against each pair's text
      description; only matches are eligible for sampling.
- [ ] 2.2 Add deterministic sampling (`--sample-size`, `--seed`, default seed
      fixed) over the filtered set so re-running the importer with the same flags
      reproduces the same case set.
- [ ] 2.3 Unit test the filter and sampling determinism against a small offline
      fixture corpus (a handful of hand-written pairs covering on-domain,
      off-domain, and borderline descriptions).

## 3. Golden generation

- [ ] 3.1 For each sampled pair, invoke `run_cadquery_model.py --deliver --formats
      stl` (unmodified, subprocess) against the pair's source script; on failure or
      a non-watertight result, log and skip the pair -- do not write a case
      directory for it.
- [ ] 3.2 On success, copy the source script into the case directory and populate
      `golden/*.stl` from the delivered output.
- [ ] 3.3 Synthesize a minimal single-part `BUILD_PLAN.json` (one `parts` entry
      referencing the copied script, no `units`/`joints`/`kinematics`) and validate
      it via `plan_validate.py` before writing the case; treat a validation failure
      the same as an execution failure (log and skip).
- [ ] 3.4 Unit test golden generation against the fixture corpus from 2.3,
      including one deliberately-broken pair to exercise the skip path.

## 4. Case writing and provenance

- [ ] 4.1 Write `request.md` as the pair's verbatim source description.
- [ ] 4.2 Write `case.json` with `tolerance_mm` (wider default for imported cases,
      e.g. `2.0`), `expected_parts: 1`, `tags` (`["external", "<source>"]`),
      `source`, `source_id` (the pair's original identifier/index), and `license`
      (from the `SOURCE_LICENSES` table in 1.1).
- [ ] 4.3 Case directory naming: `<source-prefix>-<source_id>` (e.g.
      `ext-t2cq-00042`), distinct from hand-authored case names by construction.
- [ ] 4.4 CLI summary: report counts sampled / skipped (with reasons) / written.

## 5. `run_evals.py` `--tags` filter

- [ ] 5.1 Add a `--tags` argument (comma-separated) to `evals/run_evals.py`'s
      parser; a case is included when it has no `--tags` filter applied, or when
      its `case.json` `tags` array intersects the given set.
- [ ] 5.2 Combine with `--cases` by intersection when both are given (explicit case
      list first, then further filtered by `--tags`); default behavior (neither
      flag) is unchanged.
- [ ] 5.3 Unit test the filter against `test_run_evals.py`'s existing case-loading
      fixtures, including the case where a case has no `tags` key at all
      (hand-authored cases predate this field).

## 6. Wrap-up

- [ ] 6.1 Add `evals/import_external_corpus.py` to the CLAUDE.md Core Scripts table
      and File Layout section.
- [ ] 6.2 Run `ruff check --fix` and `ruff format` on the new/changed files.
- [ ] 6.3 Run the full test suite (`uv run pytest tests/`) and confirm no
      regressions.
- [ ] 6.4 Update `TODO.md`'s "Benchmark corpora for evals/" section: check off the
      Text-to-CadQuery / WKJBryan/cadquery-library rows once the importer lands,
      leaving the Text2CAD/DeepCAD rows open (still blocked on a converter).
