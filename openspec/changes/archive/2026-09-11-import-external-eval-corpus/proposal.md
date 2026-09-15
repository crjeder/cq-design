## Why

`evals/cases/` today holds ~10 hand-authored canonical requests (the `eval-harness`
spec's "Canonical eval corpus" requirement). That is enough to catch gross
regressions but too thin to give confident signal on prompt, reference, or
model-routing changes -- the aggregate `mean_chamfer_mm`/pass-rate can shift by
noise alone with only ~10 samples. `documentation/related_projects.md` surveys two
projects that publish real text-request -> **CadQuery code** pairs (not a different
kernel needing conversion): "Text-to-CadQuery" (arXiv 2505.06507, ~170k pairs) and
`WKJBryan/cadquery-library` (2600+ hand-curated examples). Both run through
`run_cadquery_model.py` unmodified, so a sampled slice of either can become golden
`evals/cases/` entries at near-zero conversion cost -- see the rating writeup added
to `TODO.md` under "Benchmark corpora for evals/".

**Freeze note:** `TODO.md` records a V1.0 feature freeze (defects only) as of
2026-08-12. This proposal is new eval-tooling scope, not a defect fix, so it needs
an explicit freeze exception before any task below is implemented. This document is
the proposal only; nothing here is implemented yet.

## What Changes

- New script `evals/import_external_corpus.py`: samples a domain-filtered subset of
  an external text->CadQuery corpus and writes each sampled pair as a golden
  `evals/cases/<id>/` entry (`request.md`, the source script, `golden/*.stl`, a
  synthesized single-part `BUILD_PLAN.json`, and `case.json` with provenance
  fields), reusing `run_cadquery_model.py --deliver --formats stl` unmodified to
  produce the golden mesh. Reads from a local, manually-downloaded snapshot only --
  it does not fetch from the network itself, matching this skill's offline,
  subprocess-based design.
- Every source pair the importer writes gets an `"external"` tag (plus a
  per-source tag, e.g. `"text-to-cadquery"`) in its `case.json`, and
  `evals/run_evals.py` gains a `--tags` filter (comma-separated, OR-matched
  against each case's `tags`) so a run can target the canonical corpus, the
  external corpus, or both, without hand-listing case names. `--cases` is
  unaffected; the two filters combine (intersect) when both are given.
- Cases synthesize a minimal single-part `BUILD_PLAN.json` (one `parts` entry
  pointing at the copied source script, no `units`/`joints`/`kinematics`) rather
  than a hand-authored plan, since the source pairs never carried planning intent.
  The `eval-harness` spec's corpus requirement is clarified (not loosened) to
  allow this for imported cases while keeping every plan passing
  `plan_validate.py`.
- A source pair whose script fails to execute or whose result is non-watertight is
  skipped and logged, never written as a case -- a broken source pair cannot serve
  as a golden reference.
- Explicitly out of scope: fetching corpora over the network, converting
  non-CadQuery corpora (Text2CAD/DeepCAD's B-rep sketch-extrude format --
  tracked separately in `TODO.md`, blocked on a converter that doesn't exist),
  and running the importer as part of the normal skill pipeline or CI -- it is a
  manual, occasional maintenance tool like `evals/generate_goldens.py`.

## Capabilities

### New Capabilities
- `external-corpus-import`: sample, filter, execute, and provenance-tag pairs from
  a local snapshot of an external text->CadQuery corpus into `evals/cases/`.

### Modified Capabilities
- `eval-harness`: corpus requirement clarified to admit imported cases with a
  synthesized single-part plan; runner gains a `--tags` case-subsetting filter.

## Impact

- New: `evals/import_external_corpus.py`, `tests/test_import_external_corpus.py`
  (offline fixture snapshot, no network access in tests), an unspecified number of
  new case directories under `evals/cases/` (count set by whoever runs the
  importer, not fixed by this proposal).
- Modified: `evals/run_evals.py` (`--tags` filter, additive/backward compatible),
  `CLAUDE.md` (Core Scripts table + File Layout), `TODO.md` (mark the corresponding
  backlog items in progress once work starts).
- Reuses without modification: `src/run_cadquery_model.py` (`--deliver` STL
  export), `src/plan_validate.py` (validates the synthesized plan),
  `evals/model_prices.json` (unaffected -- imported cases carry no telemetry until
  actually run through `--generate`).
- **Blocking prerequisite, not yet resolved by this proposal:** the license of
  each source corpus (Text-to-CadQuery's arXiv/code release, and
  `WKJBryan/cadquery-library`) must be confirmed to permit redistributing derived
  golden meshes and copied source scripts inside this repository before the
  importer is run against it. Tasks below make this an explicit, blocking step
  rather than an assumption.
