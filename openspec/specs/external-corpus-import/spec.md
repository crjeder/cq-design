# external-corpus-import Specification

## Purpose

Let a maintainer grow the eval corpus from an external text-to-CadQuery dataset without
any pipeline coupling: a manual, network-free tool that samples, filters by domain
keyword, executes each candidate script, and writes only the pairs that produce a
watertight result as ordinary `evals/cases/` cases, tagged and licensed for provenance.

## Requirements

### Requirement: The importer samples and filters pairs from a local corpus snapshot

Given a `--source` naming one supported external corpus and an `--input` path to a
local, manually-downloaded snapshot of it, the tool SHALL NOT perform any network
access itself. It SHALL filter candidate pairs by a keyword allowlist matched
against each pair's text description, and SHALL deterministically sample up to
`--sample-size` pairs from the filtered set using `--seed`.

#### Scenario: Network-free operation
- **WHEN** the importer is run against a local `--input` snapshot
- **THEN** it performs no HTTP, dataset-hub, or git-remote access during the run

#### Scenario: Off-domain pairs are excluded
- **WHEN** a pair's description matches none of the domain keywords
- **THEN** it is not eligible for sampling

#### Scenario: Sampling is reproducible
- **WHEN** the importer is run twice with the same `--source`, `--input`,
  `--sample-size`, and `--seed`
- **THEN** both runs select the same set of pairs

### Requirement: An unknown source's license blocks the run

The tool SHALL maintain a table mapping each supported `--source` value to a
recorded license. If the named `--source` has no recorded license, the tool SHALL
exit with an error and SHALL NOT write any case directories.

#### Scenario: Unrecorded license halts the import
- **WHEN** `--source` names a corpus with no entry in the license table
- **THEN** the tool exits with an error before sampling or writing any case, and
  no `evals/cases/` directory is created or modified

### Requirement: A sampled pair becomes a golden case only if its script executes and produces a watertight result

For each sampled pair, the tool SHALL execute the pair's source CadQuery script via
`run_cadquery_model.py --deliver --formats stl`, unmodified. A pair whose execution
fails or whose result is not watertight SHALL be logged and skipped; no case
directory SHALL be written for it.

#### Scenario: A working pair is written as a case
- **WHEN** a sampled pair's script executes successfully and its result is
  watertight
- **THEN** a case directory is written under `evals/cases/` containing the copied
  script, `golden/*.stl`, a synthesized `BUILD_PLAN.json`, `request.md`, and
  `case.json`

#### Scenario: A broken pair is skipped, not repaired
- **WHEN** a sampled pair's script raises an error or produces a non-watertight
  result
- **THEN** the tool logs the pair as skipped with the reason, and writes no case
  directory for it

### Requirement: Each written case carries a synthesized, schema-valid single-part plan

The tool SHALL synthesize a `BUILD_PLAN.json` for each written case containing
exactly one `parts` entry referencing the copied source script, with no `units`,
`joints`, or `kinematics` fields. The synthesized plan SHALL pass
`plan_validate.py` before the case is written; a validation failure SHALL be
treated the same as an execution failure (logged, skipped, no case written).

#### Scenario: Synthesized plan validates
- **WHEN** a case is written
- **THEN** its `BUILD_PLAN.json` passes `plan_validate.py` with no errors

### Requirement: Each written case records provenance and license

The tool SHALL write `case.json` for each case with, at minimum, `tolerance_mm`,
`expected_parts`, `tags` (including `"external"` and a per-source tag),
`source`, `source_id` (the pair's original identifier within its corpus), and
`license` (from the source's recorded license).

#### Scenario: Provenance fields are present
- **WHEN** a case is written by the importer
- **THEN** its `case.json` includes `source`, `source_id`, `license`, and a
  `tags` array containing `"external"`

### Requirement: The importer is a manual tool, not a pipeline stage

The importer SHALL NOT be invoked automatically by the skill's part loop, quality
gate, or CI. It SHALL be run explicitly by a maintainer, like
`evals/generate_goldens.py`.

#### Scenario: Normal skill operation never invokes the importer
- **WHEN** the skill runs its normal Sourcing Triage -> Planning -> Part Loop ->
  Model Export -> Quality Gate pipeline
- **THEN** `import_external_corpus.py` is not invoked at any stage
