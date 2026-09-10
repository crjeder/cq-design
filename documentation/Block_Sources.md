# Reusable CAD model libraries 
on GitHub, rated for use as `src/blocks/` in cq-design

| Repo | Stars | Last Push | Usability as blocks | Why |
|---|---:|---|---|---|
| [gumyr/cq_warehouse](https://github.com/gumyr/cq_warehouse) | 151 | 2024-01 | **High** | Already the project's `cq-warehouse` git dependency (`CLAUDE.md`, `pyproject.toml`). Threads, fasteners, gears, extended workplane ops — same CadQuery API, zero porting. Slower-moving than `bd_warehouse` (its build123d successor) but directly importable today. |
| `cq_gears` | | | **High** | Generates parametric spur, helical, and planetary gears directly as CadQuery objects. |
| `cqMore` | | | **High** | Adds fundamental API extensions and base geometric primitives. |
| `cqterrain` | | | **High** | A specialized part library for terrain and structural components. |
| [michaelgale/cq-gridfinity](https://github.com/michaelgale/cq-gridfinity) | 200 | 2025-04 | **Medium-High** | Pure CadQuery, actively maintained, narrow but well-defined domain (Gridfinity baseplates/boxes). Worth vendoring specific generators as a `blocks/gridfinity.py` module if a project needs it; too specialized to import wholesale. |
| [fa-mc/vibe-cading](https://github.com/fa-mc/vibe-cading) | 5 | 2026-06 | **Medium** | Explicitly built for CadQuery + LLM agents (typed-parameter Python classes for screws, gears, joints, bearings, heat-set inserts, hinges, standoffs) — closest philosophical match to this skill's `blocks/` pattern. Low stars/immature, so treat as a design reference and cherry-pick, not a hard dependency. |
| [medicationforall/cadqueryhelper](https://github.com/medicationforall/cadqueryhelper) | 25 | 2026-04 | **Medium** | Small CadQuery primitive/helper library, actively pushed. Fine for occasional shape-primitive borrowing; not comprehensive enough to be a core dependency. |
| [gumyr/bd_warehouse](https://github.com/gumyr/bd_warehouse) | 96 | 2026-07 | **Medium** | build123d, not CadQuery — different API/kernel wrapper, so no direct import. But it's the actively-maintained successor to `cq_warehouse` with the broadest fastener/thread/gear/pipe coverage; useful as an algorithm/parameter reference when `cq_warehouse` lacks a part, porting logic by hand. |
| [BelfrySCAD/BOSL2](https://github.com/BelfrySCAD/BOSL2) | 2252 | 2026-06 | **Medium** (reference only) | OpenSCAD, not Python — cannot be imported as a block. But it's the largest, most actively maintained parametric-shape library in the ecosystem (attachments, threading, gears, masks); useful for algorithm/formula reference when implementing a new `blocks/` module from scratch. |
| [BelfrySCAD/BOSL2](https://github.com/BelfrySCAD/BOSL2) | 2252 | 2026-06 | **High** | Attachments. Unless you make models containing just one object, the attachments features can revolutionize your modeling. They let you position components of a model relative to other components so you don't have to keep track of the positions and orientations of parts of the model. You can instead place something on the TOP of something else, perhaps aligned to the RIGHT. For a full introduction to attachments, consult the Attachments Tutorial. |
| PartCAD Repositories | | | **Medium** | An emerging package manager that unifies CadQuery, build123d, and OpenSCAD. Highly reusable if you want to orchestrate cross-framework parts, but adds an extra tooling abstraction layer. |
| [nophead/NopSCADlib](https://github.com/nophead/NopSCADlib) | 1602 | 2025-10 | **Low-Medium** (reference only) | OpenSCAD. Huge real-world mechanical/electronic parts catalogue (motors, extrusions, connectors) — good for cross-checking dimensions/tolerances, not for code reuse. |
| [openscad/MCAD](https://github.com/openscad/MCAD) | 681 | 2025-10 | **Low** (reference only) | OpenSCAD. Older, smaller, less actively maintained than BOSL2/NopSCADlib; some overlap value for basic mechanical primitives (bearings, gears, screws) as a naming/dimension reference. |
| [keeeal/bd-vslot](https://github.com/keeeal/bd-vslot) | 3 | 2026-01 | **Low** | build123d, single-purpose (V-slot rail hardware), 3 stars. Only relevant if a project specifically needs V-slot components; port by hand if so. |
| [JustinSDK/dotSCAD](https://github.com/JustinSDK/dotSCAD) | 929 | 2023-01 | **Low** | OpenSCAD, math/geometry-utility focused (not parts). Different language, stale since 2023 — reference value only for algorithmic tricks (e.g. curve generation). |
| [cqparts/cqparts](https://github.com/cqparts/cqparts) | 148 | 2020-03 | **Low** | CadQuery wrapper framework, unmaintained since 2020. Its assembly/wrapper abstraction also conflicts with this skill's direct-Workplane block pattern — would require adapting, not just importing. |
| [x0pherl/partomatic](https://github.com/x0pherl/partomatic) | 10 | 2026-05 | **Low** | build123d, generic parametric-config utility rather than a parts catalogue. Low relevance to sourcing actual geometry blocks. |
| [revarbat/BOSL](https://github.com/revarbat/BOSL) | 687 | 2023-02 | **Very Low** | OpenSCAD, superseded by BOSL2, stale. No reason to use over BOSL2. |
| [CadQuery/awesome-cadquery](https://github.com/CadQuery/awesome-cadquery) | 181 | 2026-06 | **N/A** (index) | Curated link list, not a library — useful as a discovery starting point (surfaced most of the above), not a source of code. |
| [phillipthelen/awesome-build123d](https://github.com/phillipthelen/awesome-build123d) | 89 | 2026-05 | **N/A** (index) | Same role for the build123d ecos
| TraceParts / GrabCAD Open STEP Archives | | | high | **Standard Hardware Components.** Consuming vendor-neutral ISO 10303 (STEP) files is natively supported by CadQuery's underlying OpenCascade kernel. You lose parametric variation at runtime, but you gain exact, un-triangulated math representations for mates, fillets, and CNC work. |
| FreeCAD Standard Parts Library (`Macro_PartsLibrary`) | | | high | **Fasteners & Bearings.** Because FreeCAD also uses the OpenCascade kernel, its internal geometries map 1:1 to CadQuery. Many FreeCAD catalog macros can either be exported directly to standard STEP or read via raw Python tables to reconstruct parts. |
| OpenCascade Community Catalogs | | | high | **Core Geometric Primitives.** Native OpenCascade `.brep` file catalogs are fully open and can be directly loaded into CadQuery without any translations using `cq.Shape.cast(OCC.Core.BRepTools...)`. |
| Misumi / McMaster-Carr Open Data | | | medium | **Industrial Hardware.** While hosted by commercial entities, their standardized STEP downloads are perfectly formatted. You can build a local cache folder and use a Python dictionary script to match part numbers to `importStep()` paths. |
| https://github.com/adafruit/Adafruit_CAD_Parts | | | | **Adafruit products** | 
| https://github.com/OpenVSP/OpenVSP | | | | modell aircraft geometry tool |
| https://github.com/eclecticc/ParametricCase | | | | PC Case |
| https://github.com/AndyLevesque/QuackWorks | | | | | 
| https://hackaday.io/project/27631-3d-printing-real-world-keys | | | | real-world keys |
| https://github.com/nvx/protec-3d-printing | | | Printable ABLOY PROTEC Keys |
| https://github.com/conorpp/3d-maze-generator | | | | 3d-maze-generator |
| https://github.com/vsergeev/3d-parametric-whoop | | | | Quadrocopter |
| https://github.com/onthelake/parametric_lego | | | | LEGO |
| https://github.com/matthova/hovalin | | | | Violin |









