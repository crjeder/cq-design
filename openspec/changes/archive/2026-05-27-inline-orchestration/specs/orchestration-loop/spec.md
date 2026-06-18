## REMOVED Requirements

### Requirement: Orchestrator reads BUILD_PLAN and drives one focused LLM call per part
**Reason**: The orchestrator script is deleted. Claude executes the part loop inline as SKILL.md instructions, calling run_cadquery_model.py directly via Bash rather than invoking a Python orchestrator which in turn calls claude -p subprocesses.
**Migration**: SKILL.md phase 3 replaces all behavior previously encoded in orchestrate.py. No migration path needed for end users; the skill interface (/cq-design) is unchanged.

---

### Requirement: Orchestrator validates geometry against plan after each part
**Reason**: Geometry validation remains in run_cadquery_model.py (unchanged). Dimension mismatch detection and correction is now handled by Claude inline when it parses the wrapper JSON result, rather than by orchestrate.py logic.
**Migration**: None required. The validation behavior is preserved; only who acts on the result changes.

---

### Requirement: Retry limit is enforced per part
**Reason**: The retry loop moves into SKILL.md prose instructions. Claude tracks attempt count and stops at 3 retries, then asks the user conversationally rather than blocking on terminal input().
**Migration**: None required for users. The retry limit (3) is unchanged.

---

### Requirement: Assembly phase receives verified actual dimensions, not plan estimates
**Reason**: Assembly phase is now handled inline by Claude, which has the wrapper JSON results from each part in its context. Claude reads actual bounding box values directly from those results when generating the assembly script.
**Migration**: None required. The behavior is preserved.

---

### Requirement: Orchestrator build log is written to the caller's cwd
**Reason**: orchestrate.py and its BuildLog class are deleted. Inline execution produces a conversational summary. Writing a structured build_log.json is deferred as optional.
**Migration**: Users who relied on build_log.json for scripted post-processing should note this is no longer automatically written. This is a known regression; see design.md open questions.
