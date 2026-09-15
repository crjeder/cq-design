## 1. Checklist reference

- [x] 1.1 Add a "Request conformance" question class to `reference/Visual Review Checklist.md`: generated from the scoped `request_log` text (the `initial` entry plus per-part entries), one yes/no question per placement/form claim in the wording, each answered against a cited view.
- [x] 1.2 In the same section, state the advisory-vs-blocking rule: a request-conformance "no" is an advisory finding unless the same discrepancy also fails a plan-derived question or universal invariant, in which case it is a blocking `visual_mismatch` citing the request text.
- [x] 1.3 Add the note that promoting request-conformance findings to blocking-by-default requires `evals/run_evals.py` evidence from under-specified cases.
- [x] 1.4 State that the request-conformance class is omitted when `BUILD_PLAN.json` has no `request_log`.

## 2. Entry scoping

- [x] 2.1 Confirm whether `python src/request_log_search.py BUILD_PLAN.json --query "<part id/name>"` is sufficient to select per-part entries. Confirmed sufficient: the existing per-name query pattern (phase3_build.md section-selection, step 2) already unions matches across multiple query terms; the scoping rule runs `--query` for the part id, `description`, and each interface name. No `--part` mode or new test needed.
- [x] 2.2 Document the scoping rule in `skill/phase3_build.md`: always feed the `initial` entry; add per-part entries via typed `targets` when present, else via the keyword match. (Added as "Scoping to a part" in the Request log section.)

## 3. Implementation audit (autonomous path)

- [x] 3.1 In `skill/phase3_build.md` Implementation audit step 1, add the scoped `request_log` text to the auditor agent's prompt contents; keep the explicit "does NOT receive the part script" rule.
- [x] 3.2 In step 2, add the request-conformance bar to the auditor's checklist application ("does the render satisfy the user's own words?").
- [x] 3.3 In steps 3-4, specify that a request-conformance mismatch with all checklist questions passing returns `verdict: pass` with an advisory entry in `findings` (request text + cited view), surfaced to the user, builder not resumed.
- [x] 3.4 In step 5, specify that a request-conformance mismatch that also fails a checklist question goes in `failed_questions` as `severity: blocking` with the request text cited, and resumes the builder as today.

## 4. Progressive visual self-review (inline path)

- [x] 4.1 In `skill/phase3_build.md` progressive Step 4, add the request-conformance question class to the inline question-driven review, generated from the scoped `request_log` text.
- [x] 4.2 Apply the same advisory-vs-blocking rule as the auditor path; advisory findings are displayed grouped separately and do not consume a retry.

## 5. Validation and evidence

- [x] 5.1 `openspec validate request-relative-acceptance --strict` passes.
- [x] 5.2 Dry-run the C5 phone-holder cradle request against the updated checklist wording. The `initial` request phrase "align the hole with the bore hole on the front plate when the leg lies flat on the front plate" is a folded-pose reference-frame claim; under the new class the reviewer asks "does the render show the hole aligned with the bore in the leg-flat pose?" answered against the isometric/section. The plan encoded independent pivot literals in the authoring frame, so the render contradicts the stated frame -> at minimum an advisory request-conformance finding is now raised where before no gate looked at the wording.
- [x] 5.3 Confirm an eval-corpus golden plan with no `request_log` runs the review unchanged. Verified: no plan under `evals/cases/` contains `request_log`, so the request-conformance class is omitted for the entire existing corpus and the plan-derived questions, invariants, and engineering rows are untouched.
- [x] 5.4 Note in the change that adding under-specified eval cases and any promotion to blocking is out of scope here (tracked separately). Added as an "Out of Scope" section in `proposal.md`.
