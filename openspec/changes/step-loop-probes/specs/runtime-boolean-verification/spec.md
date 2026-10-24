## REMOVED Requirements

### Requirement: Scratch parts require a staged construction plan
**Reason**: Part scripts are now a step list over blocks, templates and primitives (see
`step-script`); there is no raw-CadQuery scratch path. Every step is checked by the step
worker against the probe registry, which supersedes hand-placed `verify_stage` stages.
**Migration**: Build scratch geometry from primitive steps (`box`, `cylinder`, `prism`,
`revolve`, ...). Existing scripts with `verify_stage` keep running on the cold path;
convert them to the step form when the builder next edits them.
