# Emboss & Deboss Text Reference

Text-specific CadQuery gotchas: split out of `CadQuery Pattern Reference.md` so the
main reference stays general-purpose. Appended to the builder's CadQuery reference **only
for a part that involves text/emboss** (`src/render_prompt.py`) -- treat this as a
continuation of that file when present, not a separate optional doc.

## Table of Contents

1. Text Deboss: `combine='cut'` Silent Failure
2. Embossed Text Overflow and Clipping
3. Measuring Text Bounding Boxes

## Text Deboss: combine='cut' Silent Failure

`combine='cut'` in `.text()` often silently fails, producing unchanged geometry. This appears related to workplane context contamination and OCCT boolean sensitivity on coplanar surfaces.

**Canonical deboss pattern — always works:**
```python
# Create text on a FRESH workplane at absolute coordinates
text_solid = (
    cq.Workplane("XY")
    .transformed(offset=(0, text_y, top_z), rotate=(0, 0, 90))
    .text(label, font_size, -depth, font="Arial")
)
# Explicitly cut from body
body = body.cut(text_solid)
```

**Detection:** Compare face count or file size before/after. If unchanged, the cut failed silently. Assert it at build time with `cq_verify.verify_boolean`: `body = verify_boolean(body, body.cut(text_solid), "cut", "label_text")` -- a no-op then fails as a typed `silent_boolean` error naming the feature, instead of vanishing.

**Overflow guard:** the clip pattern below removes protrusions; `cq_verify.verify_feature_bounds(before, after, "label_text")` additionally flags text that pokes past the body so you know clipping was needed.

## Embossed Text Overflow and Clipping

`combine='a'` (additive text) creates geometry outside the body boundary. Characters that extend past the body outline become floating protrusions.

**Clip pattern:**
```python
# After adding embossed text
clip = body_profile(cq.Workplane("XY")).extrude(thickness + emboss_height)
result = result.intersect(clip)
```

## Measuring Text Bounding Boxes

CadQuery has no API for font metrics. Measure empirically:

```python
def measure_text_bbox(text, font_size=10.0, font="Arial"):
    solid = cq.Workplane("XY").text(text, font_size, 1.0, combine=False)
    bb = solid.val().BoundingBox()
    return bb.xlen / font_size, bb.ylen / font_size  # width_ratio, height_ratio
```

Cache ratios for known labels. Multiply ratio by desired font_size to get actual dimensions.
