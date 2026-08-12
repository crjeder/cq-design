## ADDED Requirements

### Requirement: The tool bisects a single numeric part-script parameter against a named kinematics entry

Given a part script path, a parameter name, a `BUILD_PLAN.json` path, a `joint_id`,
and two bound values (`--lo`, `--hi`), the tool SHALL locate the module-level
numeric assignment for the named parameter in the script (the same AST-based,
module-level `NAME = <numeric literal>` lookup `import_params.py` uses), and SHALL
bisect between the bounds using `run_kinematic_check`'s pass/fail result for the
named `joint_id` as the oracle at each candidate value.

#### Scenario: Parameter located via AST, matching import_params.py's convention
- **WHEN** a script declares `NOTCH_HEIGHT = 8.0` as a module-level assignment in
  its `PARAMETERS` block
- **THEN** the tool locates that assignment the same way `import_params.py`'s
  `parse_parameters` does, and rejects a parameter name that is not a module-level
  numeric-literal assignment

#### Scenario: A candidate value is evaluated by regenerating geometry and re-sweeping
- **WHEN** the tool tests a candidate value for `NOTCH_HEIGHT`
- **THEN** it rewrites the script's assignment line to that value, regenerates the
  searched part's STL, runs `run_kinematic_check` against the plan, and reads the
  result for the named `joint_id` only

---

### Requirement: The tool checks bound validity before bisecting

The tool SHALL evaluate `--lo` and `--hi` once each before bisecting. `--lo` SHALL
fail the named joint's sweep (collision or an incomplete achieved range) and `--hi`
SHALL pass it (full required range achieved, no finding for that `joint_id`). If
either bound does not satisfy this, the tool SHALL exit with an error identifying
which bound violated the assumption and SHALL NOT proceed to bisect.

#### Scenario: Both bounds satisfy the precondition
- **WHEN** `--lo 4` collides and `--hi 12` clears for the named joint
- **THEN** the tool proceeds to bisect between them

#### Scenario: The lower bound already clears
- **WHEN** `--lo 4` already reports no collision for the named joint
- **THEN** the tool exits with an error naming `--lo` as invalid and does not bisect

#### Scenario: The upper bound still collides
- **WHEN** `--hi 12` still reports a collision for the named joint
- **THEN** the tool exits with an error naming `--hi` as invalid and does not bisect

---

### Requirement: Bisection converges to a tolerance and reports a margined recommendation

The tool SHALL bisect until `hi - lo <= --tolerance-mm` (default `0.1`), maintaining
the invariant that `lo` fails and `hi` passes at every step. On convergence it SHALL
report the converged `hi` (the tightest passing value observed) and a recommended
value equal to `hi + --margin-mm` (default `0.2`).

#### Scenario: Bisection converges within tolerance
- **WHEN** bisecting `NOTCH_HEIGHT` between 4 and 12 with `--tolerance-mm 0.1`
- **THEN** the tool stops once the passing/failing bracket is 0.1mm or narrower and
  reports the converged passing value

#### Scenario: Recommended value includes the safety margin
- **WHEN** the converged passing value is 8.05mm and `--margin-mm` is 0.2
- **THEN** the reported recommended value is 8.25mm

---

### Requirement: Geometry is written back only when explicitly requested

The tool SHALL NOT modify the part script by default. When `--apply` is passed, it
SHALL rewrite the script's parameter assignment to the recommended (margined) value
using the same line-rewrite mechanism used for candidates, preserving the rest of
the line's formatting.

#### Scenario: Default run leaves the script unmodified
- **WHEN** the tool is run without `--apply`
- **THEN** the part script on disk is unchanged after the search completes, and the
  recommended value is reported only in the tool's output

#### Scenario: --apply writes the recommended value
- **WHEN** the tool is run with `--apply`
- **THEN** the script's parameter assignment line is rewritten to the recommended
  value, and any surrounding comment or alignment on that line is preserved

---

### Requirement: Scoped STL regeneration reuses the rest of the model's existing export

Between bisection steps, the tool SHALL regenerate only the STL of the part whose
script was edited, posed into the assembled frame the same way `model_export.py`
poses it (`placement`, or a `joints` mate-chain pose when present), and SHALL reuse
the other unions' STLs already present in `--stl-dir` unchanged. It SHALL NOT
re-run `model_export.py` for the whole model on every candidate.

#### Scenario: Only the searched part's STL changes between steps
- **WHEN** the tool tests a new candidate value
- **THEN** only the searched part's STL file in `--stl-dir` is rewritten; every
  other union's STL file is untouched

---

### Requirement: Non-monotonic search is out of scope and not silently masked

The tool SHALL NOT attempt to detect or correct for a non-monotonic relationship
between the searched parameter and clearance anywhere in the interior of the
`[lo, hi]` bracket. Its only monotonicity check is the bounds precondition above.

#### Scenario: Interior non-monotonicity is not detected
- **WHEN** a candidate strictly between `lo` and `hi` collides even though a nearer
  candidate to `lo` passed
- **THEN** the tool's bisection may report a value that does not actually clear at
  every pose; this is a documented limitation, not a defect the tool checks for
