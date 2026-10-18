## ADDED Requirements

### Requirement: Section-cut guidance matches the renderer's cut selection
The builder prompt (`prompts/builder.md`) and the script docs (`reference/scripts.md`, `FILES.md`) SHALL describe section-cut selection as `render_preview.py` implements it: when any `--extra-section` cut is supplied, those cuts are the only sections rendered and the bounding-box-center cuts are not added; otherwise `--cross-sections` renders the bounding-box-center cuts. They SHALL NOT claim that a `--auto-sections` flag exists or is passed in the validate command while `render_preview.py` does not accept it. Geometry-driven bore/boss cuts SHALL be described as obtained by running `section_select.py` by hand and passing its `extra_section_args` as `--extra-section` arguments.

#### Scenario: Builder prompt does not promise auto sections
- **WHEN** `prompts/builder.md` is rendered for any part
- **THEN** it contains no reference to `--auto-sections` and states that `--extra-section` cuts replace the default bounding-box cuts

#### Scenario: Builder prompt explains how to get bore cuts
- **WHEN** a builder needs a section through a bore or boss axis
- **THEN** the prompt directs it to run `section_select.py` on the part script and pass the returned `extra_section_args` to the validate command

#### Scenario: Script docs do not list a missing flag
- **WHEN** `reference/scripts.md` and `FILES.md` describe `section_select.py`
- **THEN** they describe it as a standalone CLI and do not state that `render_preview.py` or `run_cadquery_model.py` accepts `--auto-sections`
