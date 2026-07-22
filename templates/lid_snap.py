"""Archetype: snap-fit lid. Flat panel with two cantilever snap_hook_clip features
mounted on the underside near the north/south edges, embedded slightly into the panel
so the union is a real volumetric overlap rather than a coincident-face touch. Mate
each clip with a snap_socket_receiver cut into the enclosure body's matching wall."""

from blocks import fillet_box, snap_hook_clip
from cq_verify import verify_boolean

# PARAMETERS
lid_width = 60.0  # mm outer lid width (X), matches the enclosure body's outer width
lid_depth = 40.0  # mm outer lid depth (Y), matches the enclosure body's outer depth
lid_t = 3.0  # mm lid panel thickness
corner_r = 3.0  # mm outer corner fillet radius (0 = sharp)
clip_w = 8.0  # mm snap hook clip width
clip_length = 10.0  # mm cantilever beam length
clip_h = 1.5  # mm beam thickness
clip_hook_h = 1.0  # mm hook tooth protrusion
clip_inset = 6.0  # mm inset of each clip's beam origin from the panel edge
clip_embed_mm = 0.6  # mm the clip base embeds into the panel for a real volumetric overlap

panel = fillet_box(lid_width, lid_depth, lid_t, corner_r)

clip_y = lid_depth / 2 - clip_inset
clip_z = clip_embed_mm - clip_h

north_clip = snap_hook_clip(clip_w, clip_length, clip_h, clip_hook_h).translate((0, clip_y, clip_z))
south_clip = (
    snap_hook_clip(clip_w, clip_length, clip_h, clip_hook_h)
    .rotate((0, 0, 0), (0, 0, 1), 180)
    .translate((0, -clip_y, clip_z))
)

panel = verify_boolean(panel, panel.union(north_clip), "union", "north_clip")
panel = verify_boolean(panel, panel.union(south_clip), "union", "south_clip")

result = panel
