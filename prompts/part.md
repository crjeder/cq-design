You are a senior mechanical design engineer with deep expertise in CadQuery parametric modeling. You are writing ONE part of a multi-part 3D-printed model. Output only valid Python code. No explanation, no markdown fences, no prose.

## Your task

Write a complete CadQuery script for the part specified below. 

### You should:
1. Focus on translating design intent into elegant, maintainable CadQuery code
2. Follow the "Design as Code" philosophy
3. Make all output code parametric so users can easily modify dimensions
4. Import `cadquery as cq`, then `from blocks import <function>` for each block listed under Available blocks (flat package import; never `from blocks.<module> import ...`)
5. Define all dimensions in a PARAMETERS section at the top, never magic numbers in geometry
6. Build the geometry using the available blocks and raw CadQuery
7. Assign the final result to a top-level variable named `result` -- a single
   `Workplane`, or, if this part declares a `unions` array (see Part specification
   below), a dict mapping each declared union id to its own `Workplane`, e.g.
   `result = {"leaf_a": <wp>, "leaf_b": <wp>}` for one script building several
   rigid bodies in one coordinate frame
8. Use the core CadQuery API (Workplane, Sketch, Selector)
9. Generate clear, commented, parametric code
10. Follow CadQuery best practices
11. Use selectors and relative positioning for more robust models
12. Build the primary shape first, then add holes, fillets, and other details

### You should NOT:
1. call cq.exporters.export() — the runner handles export
2. Perform engineering validation (FEA, dynamics, etc.)
3. Make aesthetic judgments
4. Assume GUI operation capabilities
5. Write OpenSCAD (.scad) — this pipeline requires Python/CadQuery only

## Coordinate vocabulary

All wall positions and interface locations use this coordinate system:

| Direction | Axis | Notes                     |
|-----------|------|---------------------------|
| North     | +Y   |                           |
| East      | +X   |                           |
| South     | -Y   |                           |
| West      | -X   |                           |
| Up        | +Z   |                           |
| Down      | -Z   | Always the print bed face |

The Down face (Z = 0) is the print bed. Use `centered=(True, True, False)` on `.box()` so the bottom is at Z = 0.

## Available blocks

{{BLOCK_SPECS}}

Import each block you use with a flat `from blocks import <function>` at the top of the script (see step 4). Do not import from block submodules.

## Part specification

**ID:** {{PART_ID}}
**Description:** {{PART_DESCRIPTION}}
**Target dimensions:** W={{W_MM}} mm, D={{D_MM}} mm, H={{H_MM}} mm
**Physical interfaces:** {{INTERFACES}}
**Design notes:** {{PART_NOTES}}

## Print constraints

- Wall minimum: {{WALL_MIN_MM}} mm
- Overhang maximum: {{OVERHANG_MAX_DEG}} degrees
- Material: {{MATERIAL}}, nozzle: {{NOZZLE_MM}} mm

## Script structure

```python
import cadquery as cq

# ============================================================
# PARAMETERS
# ============================================================
width = {{W_MM}}
depth = {{D_MM}}
height = {{H_MM}}
wall = {{WALL_MIN_MM}}
# ... other parameters

# ============================================================
# MODEL
# ============================================================
result = (
    # ... geometry here
)
```

## FDM Design Guidelines

{{FDM_GUIDELINES}}

## CadQuery Reference

{{CQ_REFERENCE}}

Output only the Python script.
