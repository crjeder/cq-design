# CAD source catalogue

Two separate catalogues, because they answer two different questions:

1. **[Blocks library candidates](#1-blocks-library-candidates)** — reusable *feature-level*
   geometry that could become part of `src/blocks/`. Rated by whether it should be vendored
   or depended on.
2. **[Phase 0 sourcing corpus](#2-phase-0-sourcing-corpus)** — finished models and hardware
   archives to search when a *specific request* might already exist upstream. Fed to the
   five-rung ladder in `skill/phase0_sourcing.md`. Nothing here is a block; a finished
   one-off model is not a block however good it is.

---

## 1. Blocks library candidates

**Rating scale** — answers one question: *should this become part of the blocks library?*

| Rating | Meaning |
|---|---|
| **High** | Vendor or depend on it now: parametric, CadQuery-compatible, feature-level, reusable across many parts. |
| **Medium** | Cherry-pick or port by hand — right shape, wrong language, wrong scope, or too immature to depend on. |
| **Low** | Dimension/algorithm reference at most. No code path into `blocks/`. |

| Repo | Stars | Last Push | Usability as blocks | Why |
|---|---:|---|---|---|
| [gumyr/cq_warehouse](https://github.com/gumyr/cq_warehouse) | 151 | 2024-01 | **High** | Already the project's `cq-warehouse` git dependency (`pyproject.toml`). Threads, fasteners, gears, extended workplane ops — same CadQuery API, zero porting. Slower-moving than `bd_warehouse` (its build123d successor) but directly importable today. |
| [meadiode/cq_gears](https://github.com/meadiode/cq_gears) | 160 | 2024-12 | **High** | Generates parametric spur, helical, and planetary gears directly as CadQuery objects. |
| [JustinSDK/cqMore](https://github.com/JustinSDK/cqMore) | 63 | 2022-06 | **High** | Adds fundamental API extensions and base geometric primitives. Unmaintained since 2022 — vendor the functions you need rather than depending on it. |
| [medicationforall/cqterrain](https://github.com/medicationforall/cqterrain) | 38 | 2026-09 | **High** | A specialized part library for terrain and structural components. |
| [mmalecki/cq-queryabolt](https://github.com/mmalecki/cq-queryabolt) | 8 | 2025-01 | **High** | A `WorkplaneMixin` giving `boltHole`, `cskBoltHole`, `cboreBoltHole`, `nutcatchParallel`, `nutcatchSidecut` from named fasteners ("M3"). Small, MIT, pure CadQuery, directly overlapping `blocks/fasteners.py` + `blocks/hardware.py`. Low stars but the code is tiny enough to read fully and vendor. |
| [michaelgale/cq-gridfinity](https://github.com/michaelgale/cq-gridfinity) | 200 | 2025-04 | **Medium-High** | Pure CadQuery, actively maintained, narrow but well-defined domain (Gridfinity baseplates/boxes). Worth vendoring specific generators into `blocks/gridfinity.py` if a project needs it; too specialized to import wholesale. |
| [sethfischer/cq-electronics](https://github.com/sethfischer/cq-electronics) | 20 | 2025-07 | **Medium-High** | Pure CadQuery, MIT, representational models of boards/components (RPi, SBCs, connectors). The parametric counterpart to the STEP archives below: importable **keep-out / mating bodies** for enclosure work, which is this skill's core case. |
| [szymswiat/cq-enclosure](https://github.com/szymswiat/cq-enclosure) | 3 | 2025-05 | **Medium-High** | Pure CadQuery, MIT, pip-installable. Generates a gasketed (IP66-style) box + lid + gasket with inside/outside screw bosses, countersunk wood/machine screw options and mounting tabs. The whole generator is a finished model, but the gasket groove and lid-screw boss patterns are exactly the sealed-enclosure features `blocks/` lacks — port those. Low stars, small enough to read fully. |
| [AndyLevesque/QuackWorks](https://github.com/AndyLevesque/QuackWorks) | 242 | 2026-08 | **Medium-High** (reference only) | OpenSCAD, so no import. But Underware / Multiconnect / openGrid are **mounting-interface standards** — exactly the block shape `gridfinity.py` already is. Port the mating profiles by hand into a `blocks/multiconnect.py` if demand appears. Note: CC BY-NC-SA (noncommercial) — read for dimensions, do not vendor code. |
| [fa-mc/vibe-cading](https://github.com/fa-mc/vibe-cading) | 5 | 2026-06 | **Medium** | Explicitly built for CadQuery + LLM agents (typed-parameter Python classes for screws, gears, joints, bearings, heat-set inserts, hinges, standoffs) — closest philosophical match to this skill's `blocks/` pattern. Low stars/immature, so treat as a design reference and cherry-pick, not a hard dependency. |
| [medicationforall/cadqueryhelper](https://github.com/medicationforall/cadqueryhelper) | 25 | 2026-04 | **Medium** | Small CadQuery primitive/helper library, actively pushed. Fine for occasional shape-primitive borrowing; not comprehensive enough to be a core dependency. |
| [tanius/cadquery-models](https://github.com/tanius/cadquery-models) | 20 | 2023-05 | **Medium** | A bucket of ~15 independent parametric designs (clips, mounts, spacers, knobs, rodclip), Unlicense/public domain. Not a library, but several designs are block-shaped — the best **cherry-pick source** in the long tail, and license-free to vendor. |
| [gumyr/bd_warehouse](https://github.com/gumyr/bd_warehouse) | 96 | 2026-07 | **Medium** (reference only) | build123d, not CadQuery — different API wrapper over the same kernel, so no direct import. But it's the actively-maintained successor to `cq_warehouse` with the broadest fastener/thread/gear/pipe coverage; useful as an algorithm/parameter reference when `cq_warehouse` lacks a part. |
| [BelfrySCAD/BOSL2](https://github.com/BelfrySCAD/BOSL2) | 2252 | 2026-06 | **Medium** (reference only) | OpenSCAD, so it can never be imported — but it is the largest, most actively maintained parametric-shape library in the ecosystem (threading, gears, masks), and the best formula reference when writing a new `blocks/` module from scratch. Its standout idea is **attachments**: positioning components relative to each other (put this on the TOP of that, aligned RIGHT) instead of tracking absolute poses. That concept is High-value and partially covered here by `placement.py` / `mate_chain.py` — worth mining for the parts that aren't. |
| [CadQuery/cadquery-contrib](https://github.com/CadQuery/cadquery-contrib) | 70 | 2026-01 | **Medium** (reference only) | Official grab-bag of CadQuery example scripts, tutorials and an MCP server — examples, not an importable library. Good corpus for `reference/` CadQuery patterns and for eval-case inspiration. |
| [partcad/partcad](https://github.com/partcad/partcad) | 493 | 2026-09 | **Medium** | An emerging package manager that unifies CadQuery, build123d, and OpenSCAD. Highly reusable for orchestrating cross-framework parts, but adds an extra tooling abstraction layer. |
| [nophead/NopSCADlib](https://github.com/nophead/NopSCADlib) | 1602 | 2025-10 | **Low-Medium** (reference only) | OpenSCAD. Huge real-world mechanical/electronic parts catalogue (motors, extrusions, connectors) — good for cross-checking dimensions/tolerances, not for code reuse. |
| [zignig/cqparts_bucket](https://github.com/zignig/cqparts_bucket) | 22 | 2020-03 | **Low-Medium** (reference only) | Broad mechanical catalogue (motors, bearings, pulleys, servos, gears, Arduino) — good **dimension reference**. Built on `cqparts`, unmaintained since 2020 and conflicting with this skill's direct-Workplane pattern, so no direct import. |
| [RinIgarashi/CadQuery_Abenics-generator](https://github.com/RinIgarashi/CadQuery_Abenics-generator) | 1 | 2025-09 | **Low-Medium** (reference only) | Generator for Abenics spherical (monopole) gears — genuinely parametric CadQuery, but a very exotic mechanism. Keep as an algorithm reference if a spherical-joint request ever appears. |
| [onthelake/parametric_lego](https://github.com/onthelake/parametric_lego) | 4 | 2017-09 | **Low-Medium** (reference only) | Stale since 2017, so treat the numbers as a starting point, not gospel. The LEGO stud/socket pair is a mating **interface standard** in the same class as Gridfinity, so the profile is block-shaped. Useful as a dimension/tolerance reference; trademark makes shipping a `blocks/lego.py` inadvisable. |
| [paulirotta/PELA-blocks](https://github.com/paulirotta/PELA-blocks) | 118 | 2020-09 | **Low-Medium** (reference only) | OpenSCAD, CC BY-SA, stale since 2020. LEGO Technic-compatible blocks, beams, pegs, axles plus electronics-enclosure and knob/socket panels. Same interface-standard class as `parametric_lego` but with the Technic pin/axle hole profiles and FDM calibration notes; better tolerance reference of the two. Same trademark caveat. |
| [infradom/parametric_din_rail_enclosure](https://github.com/infradom/parametric_din_rail_enclosure) | 4 | 2026-09 | **Low-Medium** (reference only) | CadQuery, actively pushed, but **no license** (all rights reserved) so nothing can be vendored. Dataclass-driven DIN-rail case for small ESP32 boards (board position, USB cutout, LED windows). The 35 mm DIN-rail (EN 60715) clip is an interface standard worth a `blocks/` profile if demand appears; take the dimensions from the standard, not this code. |
| [openscad/MCAD](https://github.com/openscad/MCAD) | 681 | 2025-10 | **Low** (reference only) | OpenSCAD. Older, smaller, less actively maintained than BOSL2/NopSCADlib; some overlap value for basic mechanical primitives (bearings, gears, screws) as a naming/dimension reference. |
| [JonnyHaystack/NoCap](https://github.com/JonnyHaystack/NoCap) | 19 | 2023-10 | **Low** (reference only) | Parametric MX keycap. The MX stem is an interface standard, so the stem dimensions belong in `reference/hardware_dims`; the cap surface itself is not block material. |
| [jmwright/cadquery-projects](https://github.com/jmwright/cadquery-projects) | 6 | 2025-12 | **Low** (reference only) | Personal project scripts from a CadQuery maintainer — idiomatic code worth reading for style, not structured as blocks. |
| [khaledelhady44/CadQuery-Cookbook](https://github.com/khaledelhady44/CadQuery-Cookbook) | 0 | 2025-02 | **Low** (reference only) | Example snippets collected explicitly as LLM-training data. Unvetted quality; occasional pattern value, no library. |
| [farnasirim/cq-centrifugal-fan](https://github.com/farnasirim/cq-centrifugal-fan) | 4 | 2024-02 | **Low** (reference only) | Single parametric centrifugal impeller. Useful only if a fan/blower request appears; impeller geometry is not a general block. |
| [keeeal/bd-vslot](https://github.com/keeeal/bd-vslot) | 3 | 2026-01 | **Low** | build123d, single-purpose (V-slot rail hardware). Only relevant if a project specifically needs V-slot components; port by hand if so. |
| [JustinSDK/dotSCAD](https://github.com/JustinSDK/dotSCAD) | 929 | 2023-01 | **Low** | OpenSCAD, math/geometry-utility focused (not parts). Different language, stale since 2023 — reference value only for algorithmic tricks (e.g. curve generation). |
| [cqparts/cqparts](https://github.com/cqparts/cqparts) | 148 | 2020-03 | **Low** | CadQuery wrapper framework, unmaintained since 2020. Its assembly/wrapper abstraction conflicts with this skill's direct-Workplane block pattern — would require adapting, not just importing. |
| [x0pherl/partomatic](https://github.com/x0pherl/partomatic) | 10 | 2026-05 | **Low** | build123d, generic parametric-config utility rather than a parts catalogue. Low relevance to sourcing actual geometry blocks. |
| [medicationforall/cqindustry](https://github.com/medicationforall/cqindustry) | 15 | 2026-07 | **Low** | Well-structured "blueprint class" library, but the domain is industrial tabletop terrain (towers, domes, greebles). The authoring pattern is more interesting than the geometry. |
| [nomad-vagabond/cq-uav](https://github.com/nomad-vagabond/cq-uav) | 19 | 2025-03 | **Low** | Airfoil/wing generative framework with material and aero analysis. Parametric and well-built, but out of domain for printed mechanical blocks. |
| [openvmp/openvmp-models](https://github.com/openvmp/openvmp-models) | 11 | 2026-09 | **Low** | CadQuery-scripted robot assemblies (Don1) plus a sourcing/BOM catalogue. Work in progress, assembly-level rather than feature-level. Mild reference value for the part-catalog + BOM pattern. |
| [revarbat/BOSL](https://github.com/revarbat/BOSL) | 687 | 2023-02 | **Very Low** | OpenSCAD, superseded by BOSL2, stale. No reason to use over BOSL2. |
| [OpenVSP/OpenVSP](https://github.com/OpenVSP/OpenVSP) | 839 | 2026-08 | **Very Low** | Standalone aircraft OML/analysis application, not a Python part library. Out of domain for FDM blocks. |
| [CadQuery/awesome-cadquery](https://github.com/CadQuery/awesome-cadquery) | 181 | 2026-06 | **N/A** (index) | Curated link list, not a library — useful as a discovery starting point (surfaced most of the above), not a source of code. |
| [phillipthelen/awesome-build123d](https://github.com/phillipthelen/awesome-build123d) | 89 | 2026-05 | **N/A** (index) | Same role for the build123d ecosystem. |

### Personal model collections

Unfactored buckets of one-off scripts. Listed once, together, because the verdict is identical
for all of them: **Low** — occasionally worth reading, never worth vendoring, nothing factored
for reuse.

[Wren6991/CQCAD](https://github.com/Wren6991/CQCAD) (6★, author disclaims quality, CC0) ·
[swolebro/caddyshack](https://github.com/swolebro/caddyshack) (7★, author explicitly refuses to
make it installable) · [uchan-nos/cadquery-models](https://github.com/uchan-nos/cadquery-models) (4★) ·
[helmecke/cadquery-models](https://github.com/helmecke/cadquery-models) (3★) ·
[bullestock/cadquery](https://github.com/bullestock/cadquery) (2★)

---

## 2. Phase 0 sourcing corpus

Search targets for `skill/phase0_sourcing.md`. **Rung** is the ladder rung a hit here would
normally land on: rung 1 = parametric source to adapt, rung 2 = STEP/BREP dumb solid to
import and measure against.

### Hardware & component archives (rung 2)

The highest-value half of this catalogue: these cover the skill's most common case — building
an enclosure or bracket around a part that already exists.

| Source | Rung | Notes |
|---|---|---|
| [adafruit/Adafruit_CAD_Parts](https://github.com/adafruit/Adafruit_CAD_Parts) (1.5k★, 2026-08) | 2 | STEP/STL/Fusion files for hundreds of Adafruit boards. The best ready-made **mating-reference cache** for "enclosure around a known PCB": `importStep()` the board, measure, cut. |
| TraceParts / GrabCAD open STEP archives | 2 | **Standard hardware components.** Vendor-neutral ISO 10303 (STEP) is natively supported by CadQuery's OpenCascade kernel. No runtime parametric variation, but exact un-triangulated geometry for mates and fillets. |
| FreeCAD Standard Parts Library (`Macro_PartsLibrary`) | 2 | **Fasteners & bearings.** FreeCAD also uses OpenCascade, so its geometry maps 1:1. Catalog macros export to STEP, or the raw Python dimension tables can be read to reconstruct parts parametrically. |
| OpenCascade community catalogs | 2 | **Core geometric primitives.** Native `.brep` catalogs load into CadQuery with no translation via `cq.Shape.cast(OCC.Core.BRepTools...)`. |
| Misumi / McMaster-Carr open data | 2 | **Industrial hardware.** Commercially hosted but cleanly formatted STEP downloads. Build a local cache folder and map part numbers to `importStep()` paths with a dictionary. |

### Finished models by domain (rung 1)

| Source | Domain | Notes |
|---|---|---|
| [eclecticc/ParametricCase](https://github.com/eclecticc/ParametricCase) | PC case | Finished parametric case (OpenSCAD). Adapt the parameters; nothing generalizes to `blocks/`. |
| [joshreve/dactyl-keyboard](https://github.com/joshreve/dactyl-keyboard) | Ergonomic keyboard | Large generative project, geometry heavily case-specific. |
| [LukasStu/Ferris-Sweep-Bling-MX-Case](https://github.com/LukasStu/Ferris-Sweep-Bling-MX-Case) | Keyboard case | One finished case for one specific PCB. |
| [neuman/gripster](https://github.com/neuman/gripster) (3★) | Thumb keyboard | Whole device (shell + PCB + firmware) generated from one parametric file. The single-source-of-truth pattern is the interesting part. |
| [hrvach/deskhop](https://github.com/hrvach/deskhop) | KVM switch | Hardware/firmware project; the CAD is one enclosure. |
| [vsergeev/3d-parametric-whoop](https://github.com/vsergeev/3d-parametric-whoop) | Quadcopter frame | One finished parametric frame. |
| [DrLex0/print3D-customizable-sieve](https://github.com/DrLex0/print3D-customizable-sieve) | Sieve / strainer | Finished customizable part. Mild reference value for perforation-pattern math in `connectors.vent_grid`. |
| [Buback/ParametricDeLavalModel](https://github.com/Buback/ParametricDeLavalModel) | De Laval nozzle | Single nozzle-profile model, aerospace-specific. |
| [matthova/hovalin](https://github.com/matthova/hovalin) | Violin | Freeform/organic. Out of scope for mesh→parametric reverse engineering (rung 4 explicitly excludes this). |
| [phrxmd/container](https://github.com/phrxmd/container) | Shipping containers | Decorative scale models. |
| [conorpp/3d-maze-generator](https://github.com/conorpp/3d-maze-generator) | Maze novelty | Generative novelty. |
| [jobtalle/Lindenmayer3D](https://github.com/jobtalle/Lindenmayer3D) | L-system art | Generative art, no mechanical features. |
| [medicationforall/cqspoolterrain](https://github.com/medicationforall/cqspoolterrain) | Tabletop terrain | Terrain built onto filament spools. |
| [medicationforall/cqladderterrainstreamlit](https://github.com/medicationforall/cqladderterrainstreamlit) | Tabletop terrain | Streamlit front-end around one generator. |
| [medicationforall/obeliskterrainapp](https://github.com/medicationforall/obeliskterrainapp) | Tabletop terrain | Streamlit app around one model. |
| [zbynekwinkler/cadquery-skylark](https://github.com/zbynekwinkler/cadquery-skylark) | Aircraft | Not relevant for 3D printing due to size. |
| [3D-printing real-world keys](https://hackaday.io/project/27631-3d-printing-real-world-keys) · [nvx/protec-3d-printing](https://github.com/nvx/protec-3d-printing) | Lock keys | Project write-ups rather than libraries, in a security-sensitive domain. Not recommended as a sourcing target. |

---

## Indexes, duplicates and dead links

| Entry | Status |
|---|---|
| [CadQuery/awesome-cadquery](https://github.com/CadQuery/awesome-cadquery) (181★) | **Index.** Curated link list — the discovery starting point that surfaced most of this file. |
| [phillipthelen/awesome-build123d](https://github.com/phillipthelen/awesome-build123d) (89★) | **Index.** Same role for the build123d ecosystem. |
| [lwidm/cq_gears](https://github.com/lwidm/cq_gears) | **Duplicate.** Fork of `meadiode/cq_gears` (rated High above). Use upstream. |
| [S-S-X](https://github.com/S-S-X) (YAPM) | **Bad link.** Points at a user profile, not a repository; no YAPM repo resolves under it. Needs a working URL before it can be rated. |
| [cadhub.xyz](https://github.com/Irev-Dev/cadhub) | **Abandoned.** |

## Next actions

- **Top vendoring candidates**: `cq-queryabolt` (fastener cutout mixin — overlaps
  `blocks/fasteners.py` directly) and `cq-electronics` (importable board keep-out bodies),
  with `tanius/cadquery-models` as the best license-free cherry-pick source.
- **Best non-code borrow**: BOSL2's attachment model, checked against what `placement.py` /
  `mate_chain.py` already do.
- Promote from section 2 to section 1 only on evidence — when the same shape gets sourced and
  converted repeatedly, not on speculation.
