## 1. Engineering rationale hooks in the part prompt

- [ ] 1.1 Add the ENGINEERING RATIONALE section requirement to `prompts/part.md`: block placement (between PARAMETERS and MODEL), the three required lines for load-bearing parts (load path, worst-case stress location, computed check referencing parameter names vs. a stated allowable), and the one-line form for non-load-bearing parts
- [ ] 1.2 Document the plan-driven trigger list in `prompts/part.md` (declared `load`, or `blocks_needed`/`archetype` in the load-bearing set: snap hooks, clips, hooks, brackets, screw bosses, pcb standoffs, living hinge, dovetail joints)
- [ ] 1.3 Update the script-structure example in `prompts/part.md` to show the rationale section, and confirm the "output only the Python script" contract still holds in both render modes
- [ ] 1.4 Note in `skill/phase3_build.md` that retry/correction prompts preserve the rationale obligation (re-evaluate the check when a cited parameter changes)

## 2. Engineering Design Rules reference

- [ ] 2.1 Write `reference/Engineering Design Rules.md`: material constants table tagged `always` (allowable strain, flexural modulus for PLA/PETG/ABS/TPU), snap-fit strain formula + coefficients, rib/boss/gusset ratio limits, insert/clearance deltas not already in `hardware_dims.md`; every section carries an `<!-- applies_to: ... -->` tag; target under ~4 KB, tables and formulas only
- [ ] 2.2 Add the new reference to the Phase 3 Step 1 substitution table in `skill/phase3_build.md`: inline renders cite selected section names, cold contexts get selected bodies; selection = `blocks_needed` intersection + `always` + load-relevant sections when the part declares a `load`
- [ ] 2.3 Add the file to the Phase 3 setup read list so inline citation is valid (per the reference-injection in-context rule)

## 3. Numbers-demanding review rows

- [ ] 3.1 Add an "Engineering rows" table to `reference/Visual Review Checklist.md`, generated from the same load-bearing trigger: each row asks for a value and threshold (rib/wall <= 0.6, snap-arm strain vs. allowable, boss ratios), answered by citing PARAMETERS / rationale block / wrapper `geometry` JSON
- [ ] 3.2 State the row-class distinction in the checklist: visual rows cite views, numeric rows cite the parameter or geometry value; a re-derived value that contradicts the rationale or exceeds its threshold is a blocking finding

## 4. Verification and A/B

- [ ] 4.1 Sanity-run one load-bearing eval case (e.g. a snap-lid case) end-to-end and confirm the generated script carries a rationale block whose numbers reference its own parameters
- [ ] 4.2 A/B on the eval corpus: score first-shot rate, attempts-to-pass, and cost per accepted part with hooks on vs. the pre-change prompt (`evals/run_evals.py` scorecards); record the outcome in the change folder
- [ ] 4.3 Update `IMPROVEMENT_PLAN.md` item 5 status based on the A/B result
