## ADDED Requirements

### Requirement: Run report flags unmanaged edits
The `step_worker.py run` report SHALL include `unmanaged_edit` as defined by `script-ops`
for both warm and fallback runs, and its value SHALL also appear in the saved step report
the builder passes to the audit.

#### Scenario: Unmanaged edit in a warm run
- **WHEN** the builder edits `build/<part>.py` as text after its last `script_ops.py`
  command and runs the step worker
- **THEN** the report has `unmanaged_edit: true` and the steps run as usual
