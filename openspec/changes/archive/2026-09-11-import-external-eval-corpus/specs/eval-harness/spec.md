## MODIFIED Requirements

### Requirement: Canonical eval corpus
The repository SHALL contain an `evals/cases/` corpus of approximately 10
hand-authored canonical requests, each dimensioned against a request the skill
might realistically see. Each case directory SHALL contain the verbatim user
request (`request.md`), a golden `BUILD_PLAN.json` that passes
`plan_validate.py`, one or more golden meshes under `golden/` in the authored
frame, and a `case.json` with at minimum `tolerance_mm` and the expected part
count.

The corpus MAY additionally contain cases imported from an external
text-to-CadQuery corpus via `evals/import_external_corpus.py` (see the
`external-corpus-import` capability). An imported case's `BUILD_PLAN.json` MAY be
a synthesized single-part plan (one `parts` entry, no `units`/`joints`/
`kinematics`) rather than hand-authored, but SHALL still pass `plan_validate.py`
like any other case's plan. An imported case's `request.md` is the source
corpus's original pair description, not necessarily written in this skill's usual
conversational-request style. Imported cases are distinguished from hand-authored
ones by an `"external"` entry in `case.json`'s `tags` array, not by directory
location -- both live as flat siblings under `evals/cases/`.

#### Scenario: Case plans are valid
- **WHEN** `plan_validate.py` is run against any case's `BUILD_PLAN.json`,
  hand-authored or imported
- **THEN** validation passes with no errors

#### Scenario: Case is self-contained
- **WHEN** a case directory is inspected
- **THEN** it contains `request.md`, `BUILD_PLAN.json`, at least one golden
  mesh, and `case.json`

#### Scenario: An imported case's plan is a synthesized single-part plan
- **WHEN** a case's `case.json` `tags` array includes `"external"`
- **THEN** its `BUILD_PLAN.json` contains exactly one `parts` entry and no
  `units`, `joints`, or `kinematics` fields, and still passes `plan_validate.py`

## ADDED Requirements

### Requirement: Case subsetting by tag
The eval runner (`evals/run_evals.py`) SHALL support a `--tags` argument
(comma-separated). When given, a case SHALL be included only if its `case.json`
`tags` array intersects the given set; a case with no `tags` key SHALL be treated
as having an empty tag set. When `--tags` is omitted, case selection SHALL be
unaffected (all cases, or the `--cases` subset if given). When both `--cases` and
`--tags` are given, the effective case set SHALL be their intersection.

#### Scenario: Tag filter selects the external corpus only
- **WHEN** the runner is invoked with `--tags external`
- **THEN** only cases whose `case.json` `tags` array contains `"external"` are
  scored

#### Scenario: Tag filter selects the canonical corpus by exclusion
- **WHEN** the runner is invoked with `--tags canonical` and every hand-authored
  case's `case.json` includes a `"canonical"` tag
- **THEN** only hand-authored cases are scored

#### Scenario: No tag filter leaves existing behavior unchanged
- **WHEN** the runner is invoked without `--tags`
- **THEN** case selection behaves exactly as it did before this field existed

#### Scenario: Cases predating the tags field are excluded by any tag filter
- **WHEN** a case's `case.json` has no `tags` key and `--tags` is given
- **THEN** that case is excluded from the run (empty tag set does not intersect
  any non-empty filter)
