# Preview and visual review -- details

Tasks: [TODO.md](../TODO.md#6-preview-and-visual-review).

### Preview ideas

Drawing feature edges on preview renders (lower value, worth a look)
varen: its renderer draws the model’s real edges without the extra diagonal lines that come from the mesh triangles.
cq-design today: I found no edge overlay in preview.py, render_preview.py or zbuffer.py. Drawn edges would make visual review easier, especially for chamfers and shallow steps.

Phase 3: mandatory visual self-review after any geometry change; builder picks extra views that show the edited feature (`section_select.py` is a start)

Preview: face labels / stable references drawn on the preview PNG so a user can point at a feature (cheap version of their viewer selection-to-prompt loop; the full viewer is out of scope)
