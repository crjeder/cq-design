## ADDED Requirements

### Requirement: Render command treats its argument as one script path
The `/cq-design:render` command SHALL pass its argument to `run_cadquery_model.py` as a single quoted argument.

#### Scenario: Script path contains spaces
- **WHEN** the user runs `/cq-design:render "my parts/box.py"`
- **THEN** `run_cadquery_model.py` receives `my parts/box.py` as one argument
