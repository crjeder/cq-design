# Import, export and materials -- details

Tasks: [TODO.md](../TODO.md#10-import-export-and-materials).

### Export print-plate structure

Separate unions into print-plates. Today all unions compile to one "world"
result and `write_assembly` already writes each as a separately named 3MF
`<object>` with `plate` metadata. Core 3MF has no native print-plate concept
(objects + `<build><item>` only); true multi-plate assignment is a
slicer-specific extension (Bambu/Prusa project-3MF). Decide: emit the slicer
plate structure, or leave plate split to the operator.

### Reverse-engineer mesh

Reverse engineer 3D mesh / point cloud into primitives
(-> differential geometry comparison); "import" mesh files (.stl). See also
https://github.com/Stone-Age-Sculptor/StoneAgeLib/blob/main/images/DemonstrationTexture.png
for the related textures capability.

### Multi color material support (Claude-To-Print)

OzAILabs/Claude-To-Print, rated **High** -- concretizes the standing bare
`Multi color / material support` item above. A close analog skill (Claude
Code + build123d, same staged design-brief -> parametric-script ->
deterministic-export -> mesh-QA -> visual-feedback pipeline). Concrete
mechanism: multi-color/multi-material 3MF export via `lib3mf`, splitting a
part into named color regions and exporting a pre-colored 3MF for
AMS-style multi-filament printers. `threemf_multi.py` currently tracks
named unions/plates but not per-region color -- closed per-union by change `multi-material-planning` (a color boundary inside one solid remains out of scope).

### Multi-material and slicer parameters

Engineering of multi-material interfaces and properties -- boundaries are treated as non-sticky (no adhesion assumed, touching is silent); still open: multi-material FEM, per-union density within one part
- [x] calculate and export slicer parameters such as: wall loops, infill, support, brim (auto brim in orca is terrible) -- layer height and infill already exported via `--formats estampo`; walls/support/brim remain
