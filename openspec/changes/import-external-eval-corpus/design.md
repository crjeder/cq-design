## Context

`evals/cases/` (the `eval-harness` capability) is hand-authored and small by
design -- each case is dimensioned against a real request the skill might see.
That is right for regression-testing the pipeline's *planning* behavior, but it
means the corpus can't grow without someone hand-writing a new request and a
golden `BUILD_PLAN.json`. Two surveyed projects (`documentation/related_projects.md`,
rated in `TODO.md`'s "Benchmark corpora for evals/" section) publish real
text-request -> CadQuery-code pairs that need no kernel conversion. This change
adds a one-shot importer that turns a sampled, filtered slice of either into
golden `evals/cases/` entries, without changing how `run_evals.py` scores a case.

## Goals / Non-Goals

**Goals:**
- Grow the corpus's sample size for `chamfer_mm`/pass-rate aggregates without
  hand-authoring, using pairs that are already valid CadQuery.
- Keep every imported case indistinguishable from a hand-authored one to
  `run_evals.py`: same directory shape, same `plan_validate.py`-passing plan, same
  scoring path. No change to how a case is *scored*, only to how one is *written*.
- Make provenance and licensing per case explicit and machine-checkable
  (`case.json`'s `source`/`source_id`/`license` fields), feeding the standing
  `TODO.md` "sbom, add credit for projects where code came from" item.
- Let a run target canonical-only, external-only, or both, via a small additive
  `--tags` filter on the existing runner.

**Non-Goals:**
- Network access from within the importer or the eval pipeline. The maintainer
  downloads a corpus snapshot out of band (a JSONL export or a repo checkout) and
  points `--input` at the local copy. This keeps the skill's offline,
  subprocess-based execution model intact and avoids baking a dataset-hub
  dependency into `src`/`evals`.
- Converting non-CadQuery corpora (Text2CAD/DeepCAD's B-rep sketch-extrude JSON).
  Tracked separately in `TODO.md`; blocked on a converter that doesn't exist yet
  and is out of scope here.
- Automatic re-import / corpus refresh on a schedule or in CI. Like
  `generate_goldens.py`, this is a manual tool a maintainer runs when they want to
  (re)populate the external slice, given the dataset sizes involved (170k pairs
  for Text-to-CadQuery) make an unbounded or automatic run expensive.
- Curating individual cases by hand after import. The domain filter and sampling
  are the only selection mechanism; a maintainer who wants a specific pair can add
  it as an ordinary hand-authored case instead.

## Decisions

### Cases are flat siblings under `evals/cases/`, distinguished by tag, not a subdirectory
`run_evals.py`'s `all_cases` listing is `CASES_DIR.iterdir()`, non-recursive.
Nesting imported cases under `evals/cases/external/` would make that single
directory look like one unscoreable case. Keeping them flat (prefixed, e.g.
`ext-t2cq-00042/`) needs no runner change beyond the new `--tags` filter, and
`--tags external` (or a per-source tag) gives the same "run only the imported
slice" ability a subdirectory would have, without touching the corpus-listing
code path at all.

### The importer never fetches over the network
Consistent with this skill's design (no MCP, no runtime network dependency in the
gate pipeline) and avoids embedding a specific dataset-hub client or auth flow
into `evals/`. The cost is a manual step per corpus refresh; acceptable since this
is an occasional maintenance action, not something the pipeline or CI runs.

### A synthesized single-part plan, not a loosened schema
The alternative -- relaxing `plan_validate.py` or the `eval-harness` spec's
"golden `BUILD_PLAN.json`" requirement to allow a caseless/plan-less case -- would
create a second code path in `run_evals.py` for cases without a plan. Instead the
importer always writes a real, schema-valid single-part plan (one `parts` entry,
the copied script, no `units`/`joints`/`kinematics`). This is strictly less work
than adding a plan-optional branch to the scorer, and keeps `plan_validate.py`'s
existing guarantee ("every case's plan passes validation") true without carving
out an exception.

### Broken source pairs are skipped, not force-fixed
The importer is not a code-repair tool. A pair whose script errors or produces a
non-watertight mesh through the *existing, unmodified* `run_cadquery_model.py`
is logged and skipped -- it cannot be a golden reference for anything, and
"fixing" someone else's corpus entry would make the golden mesh no longer
represent that corpus's actual output.

### License verification is a blocking, explicit task
Neither source's redistribution terms are confirmed as of this proposal. Rather
than assume permissive terms, task 1 below makes verifying and recording the
license (per source, in the importer's own `SOURCE_LICENSES` table) a
precondition the importer refuses to run without -- an unset/unknown license for
a `--source` value is a hard error, not a warning.

## Risks / Trade-offs

- **Corpus imbalance:** if one source's filtered/sampled pairs dominate case
  count, aggregate metrics could shift to reflect that source's authoring style
  rather than this skill's actual request distribution. Mitigated by a
  `--sample-size` cap per source (small relative to the ~10 canonical cases,
  e.g. tens not hundreds) rather than importing everything that matches the
  domain filter.
- **Domain filter is a keyword allowlist, not semantic.** It will admit some
  off-domain pairs and reject some on-domain ones described unusually. Accepted
  as good-enough for a regression corpus; a maintainer can always hand-curate
  after the fact by deleting a written case directory.
- **Tolerance for imported cases is looser than hand-authored ones** (proposed
  default wider `tolerance_mm`, e.g. 2.0mm vs. hand-authored cases' typically
  tighter values) since imported requests were never dimensioned against real
  hardware the way this skill's own canonical cases are. This is a deliberate,
  visible choice recorded per case in `case.json`, not silently baked into the
  scorer.
