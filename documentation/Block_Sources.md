# Reusable CAD model libraries 
on GitHub, rated for use as `src/blocks/` in cq-design

**Rating scale** — answers one question: *should this become part of the blocks library?*
**High** = vendor or depend on it now (parametric, CadQuery-compatible, feature-level, reusable
across many parts). **Medium** = cherry-pick or port by hand. **Low/Very Low** = at most a
dimension/algorithm reference, or a Phase 0 sourcing candidate for one specific request —
a finished one-off model is not a block, however good it is.

| Repo | Stars | Last Push | Usability as blocks | Why |
|---|---:|---|---|---|
| [gumyr/cq_warehouse](https://github.com/gumyr/cq_warehouse) | 151 | 2024-01 | **High** | Already the project's `cq-warehouse` git dependency (`CLAUDE.md`, `pyproject.toml`). Threads, fasteners, gears, extended workplane ops — same CadQuery API, zero porting. Slower-moving than `bd_warehouse` (its build123d successor) but directly importable today. |
| [`cq_gears`](https://github.com/meadiode/cq_gears) | | | **High** | Generates parametric spur, helical, and planetary gears directly as CadQuery objects. |
| [`cqMore`](https://github.com/JustinSDK/cqMore) | | | **High** | Adds fundamental API extensions and base geometric primitives. |
| [`cqterrain`](https://github.com/medicationforall/cqterrain) | | | **High** | A specialized part library for terrain and structural components. |
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
| [phillipthelen/awesome-build123d](https://github.com/phillipthelen/awesome-build123d) | 89 | 2026-05 | **N/A** (index) | Same role for the build123d ecosystem — discovery index, not code.  |
| TraceParts / GrabCAD Open STEP Archives | | | high | **Standard Hardware Components.** Consuming vendor-neutral ISO 10303 (STEP) files is natively supported by CadQuery's underlying OpenCascade kernel. You lose parametric variation at runtime, but you gain exact, un-triangulated math representations for mates, fillets, and CNC work. |
| FreeCAD Standard Parts Library (`Macro_PartsLibrary`) | | | high | **Fasteners & Bearings.** Because FreeCAD also uses the OpenCascade kernel, its internal geometries map 1:1 to CadQuery. Many FreeCAD catalog macros can either be exported directly to standard STEP or read via raw Python tables to reconstruct parts. |
| OpenCascade Community Catalogs | | | high | **Core Geometric Primitives.** Native OpenCascade `.brep` file catalogs are fully open and can be directly loaded into CadQuery without any translations using `cq.Shape.cast(OCC.Core.BRepTools...)`. |
| Misumi / McMaster-Carr Open Data | | | medium | **Industrial Hardware.** While hosted by commercial entities, their standardized STEP downloads are perfectly formatted. You can build a local cache folder and use a Python dictionary script to match part numbers to `importStep()` paths. |
| [adafruit/Adafruit_CAD_Parts](https://github.com/adafruit/Adafruit_CAD_Parts) | 1500 | | **Medium** (reference only) | STEP/STL/Fusion files for hundreds of Adafruit boards — no parametric source, so not a block. But it is the best ready-made **rung-2 mating-reference cache** for the skill's most common case (an enclosure around a known PCB): `importStep()` the board, measure, cut. |
| [OpenVSP/OpenVSP](https://github.com/OpenVSP/OpenVSP) | | | **Very Low** | Standalone aircraft OML/analysis application, not a Python part library. Out of domain for FDM blocks. |
| [eclecticc/ParametricCase](https://github.com/eclecticc/ParametricCase) | | | **Low** | One finished parametric PC case (OpenSCAD). Phase 0 rung-1 candidate if someone asks for a PC case; nothing generalizable to `blocks/`. |
| [AndyLevesque/QuackWorks](https://github.com/AndyLevesque/QuackWorks) | 242 | active | **Medium-High** (reference only) | OpenSCAD, so no import. But Underware / Multiconnect / openGrid are **mounting-interface standards** — exactly the block shape `gridfinity.py` already is. Port the mating profiles by hand into a `blocks/multiconnect.py` if demand appears. Note: CC BY-NC-SA (noncommercial) — read for dimensions, do not vendor code. |
| [3D-printing real-world keys](https://hackaday.io/project/27631-3d-printing-real-world-keys) | | | **Very Low** | One-off project write-up, not a library; also a security-sensitive domain. Skip. |
| [nvx/protec-3d-printing](https://github.com/nvx/protec-3d-printing) | | | **Very Low** | Same as above — single lock-key model, no reusable geometry. |
| [conorpp/3d-maze-generator](https://github.com/conorpp/3d-maze-generator) | | | **Very Low** | Generative novelty model. No reusable feature primitives. |
| [vsergeev/3d-parametric-whoop](https://github.com/vsergeev/3d-parametric-whoop) | | | **Very Low** | One finished parametric quadcopter frame. Phase 0 candidate only. |
| [onthelake/parametric_lego](https://github.com/onthelake/parametric_lego) | | | **Medium** (reference only) | The LEGO stud/socket pair is a mating **interface standard** in the same class as Gridfinity, so the profile is block-shaped. Useful as a dimension/tolerance reference; trademark makes shipping a `blocks/lego.py` inadvisable. |
| [matthova/hovalin](https://github.com/matthova/hovalin) | | | **Very Low** | Single freeform/organic model (violin). Nothing parametric to reuse. |
| [DrLex0/print3D-customizable-sieve](https://github.com/DrLex0/print3D-customizable-sieve) | | | **Low** | Finished customizable part. Mild reference value for perforation-pattern math in `connectors.vent_grid`; not worth a block of its own. |
| [jobtalle/Lindenmayer3D](https://github.com/jobtalle/Lindenmayer3D) | | | **Very Low** | L-system generative art. No mechanical primitives. |
| [Buback/ParametricDeLavalModel](https://github.com/Buback/ParametricDeLavalModel) | | | **Very Low** | Single nozzle-profile model, aerospace-specific. |
| [JonnyHaystack/NoCap](https://github.com/JonnyHaystack/NoCap) | | | **Low** (reference only) | Parametric MX keycap. The MX stem is an interface standard, so the stem dimensions are worth noting in `reference/hardware_dims`; the cap surface itself is not block material. |
| [LukasStu/Ferris-Sweep-Bling-MX-Case](https://github.com/LukasStu/Ferris-Sweep-Bling-MX-Case) | | | **Very Low** | One finished case for one specific PCB. |
| [phrxmd/container](https://github.com/phrxmd/container) | | | **Very Low** | Scale-model shipping containers. Decorative, not functional geometry. |
| [CadQuery/cadquery-contrib](https://github.com/CadQuery/cadquery-contrib) | | | **Medium** (reference only) | Official grab-bag of CadQuery example scripts, tutorials and an MCP server — examples, not an importable library. Good corpus for `reference/` CadQuery patterns and for eval-case inspiration. |
| [joshreve/dactyl-keyboard](https://github.com/joshreve/dactyl-keyboard) | | | **Low** | Large generative keyboard project; its geometry is heavily case-specific. Phase 0 candidate at best. |
| [medicationforall/cqspoolterrain](https://github.com/medicationforall/cqspoolterrain) | | | **Low** | Tabletop terrain built onto filament spools. Narrow theme, no general primitives. |
| [S-S-X](https://github.com/S-S-X) (YAPM) | | | **N/A** (bad link) | The URL points at a user profile, not a repository — no YAPM repo resolves under it. Needs a working link before it can be rated. |
| [neuman/gripster](https://github.com/neuman/gripster) | 3 | | **Very Low** | Single-device project (thumb keyboard) generated from one script. Interesting pattern, no reusable blocks. |
| [hrvach/deskhop](https://github.com/hrvach/deskhop) | | | **Very Low** | A KVM hardware/firmware project; the CAD is one enclosure. Not a geometry library. |
| [medicationforall/cqladderterrainstreamlit](https://github.com/medicationforall/cqladderterrainstreamlit) | | | **Low** | Streamlit front-end around one terrain generator. App wrapper, not blocks. |
| [lwidm/cq_gears](https://github.com/lwidm/cq_gears) | | | **N/A** (duplicate) | Fork of `meadiode/cq_gears`, already rated **High** above. Use the upstream. |
| [RinIgarashi/CadQuery_Abenics-generator](https://github.com/RinIgarashi/CadQuery_Abenics-generator) | | | **Low-Medium** (reference only) | Generator for Abenics spherical (monopole) gears — genuinely parametric CadQuery, but a very exotic mechanism. Keep as an algorithm reference if a spherical-joint request ever appears. |
| [tanius/cadquery-models](https://github.com/tanius/cadquery-models) | 20 | | **Medium** | A bucket of ~15 independent parametric designs (clips, mounts, spacers, knobs, rodclip), Unlicense/public domain. Not a library, but several designs are block-shaped — the best **cherry-pick source** in the long tail, and license-free to vendor. |
| [zbynekwinkler/cadquery-skylark](https://github.com/zbynekwinkler/cadquery-skylark) | | | **Very Low** | Not relevant for 3D printing due to size (as noted). |
| [sethfischer/cq-electronics](https://github.com/sethfischer/cq-electronics) | 20 | | **Medium-High** | Pure CadQuery, MIT, representational models of boards/components (RPi, SBCs, connectors). The parametric counterpart to the Adafruit STEP archive: importable **keep-out / mating bodies** for enclosure work, which is this skill's core case. Strongest vendoring candidate in the unrated set after `cq-queryabolt`. |
| [mmalecki/cq-queryabolt](https://github.com/mmalecki/cq-queryabolt) | 8 | | **High** | A `WorkplaneMixin` giving `boltHole`, `cskBoltHole`, `cboreBoltHole`, `nutcatchParallel`, `nutcatchSidecut` from named fasteners ("M3"). Small, MIT, pure CadQuery, and directly overlapping `blocks/fasteners.py` + `blocks/hardware.py`. Low stars but the code is tiny enough to read fully and vendor. |
| [nomad-vagabond/cq-uav](https://github.com/nomad-vagabond/cq-uav) | 19 | | **Low** | Airfoil/wing generative framework with material and aero analysis. Parametric and well-built, but out of domain for printed mechanical blocks. |
| [khaledelhady44/CadQuery-Cookbook](https://github.com/khaledelhady44/CadQuery-Cookbook) | 0 | | **Low** (reference only) | Example snippets collected explicitly as LLM-training data. Unvetted quality; occasional pattern value, no library. |
| [Wren6991/CQCAD](https://github.com/Wren6991/CQCAD) | 6 | | **Low** | Self-described "random selection of parts", author disclaims quality. CC0 so free to borrow, but nothing is factored for reuse. |
| [jmwright/cadquery-projects](https://github.com/jmwright/cadquery-projects) | | | **Low** (reference only) | Personal project scripts from a CadQuery maintainer — idiomatic code worth reading for style, not structured as blocks. |
| [zignig/cqparts_bucket](https://github.com/zignig/cqparts_bucket) | 22 | | **Low-Medium** (reference only) | Broad mechanical catalogue (motors, bearings, pulleys, servos, gears, Arduino) — good **dimension reference**. Built on `cqparts`, which is unmaintained since 2020 and conflicts with this skill's direct-Workplane pattern, so no direct import. |
| [medicationforall/cqindustry](https://github.com/medicationforall/cqindustry) | 15 | | **Low** | Well-structured "blueprint class" library, but the domain is industrial tabletop terrain (towers, domes, greebles). The authoring pattern is more interesting than the geometry. |
| [uchan-nos/cadquery-models](https://github.com/uchan-nos/cadquery-models) | | | **Low** | Personal model collection, no factored primitives. |
| [swolebro/caddyshack](https://github.com/swolebro/caddyshack) | 7 | | **Low** | Author explicitly refuses to make it installable ("I don't want to give anyone the idea that they should be using it"). Mixed FreeCAD/CadQuery jigs — read-only curiosity. |
| [helmecke/cadquery-models](https://github.com/helmecke/cadquery-models) | | | **Low** | Personal model collection. |
| [medicationforall/obeliskterrainapp](https://github.com/medicationforall/obeliskterrainapp) | | | **Low** | Streamlit app around one terrain model. |
| [openvmp/openvmp-models](https://github.com/openvmp/openvmp-models) | 11 | | **Low** | CadQuery-scripted robot assemblies (Don1) plus a sourcing/BOM catalogue. Work in progress, assembly-level rather than feature-level. Mild reference value for the part-catalog + BOM pattern. |
| [bullestock/cadquery](https://github.com/bullestock/cadquery) | | | **Low** | Personal model collection. |
| [farnasirim/cq-centrifugal-fan](https://github.com/farnasirim/cq-centrifugal-fan) | | | **Low** (reference only) | Single parametric centrifugal impeller. Useful only if a fan/blower request appears; impeller geometry is not a general block. |
| [cadhub.xyz](https://github.com/Irev-Dev/cadhub) | | | **N/A** | Abandoned (as noted). |

## Notes

- **BOSL2 appears twice with conflicting ratings** (Medium reference-only vs. High for
  attachments). Both are defensible for different reasons but the rows should be merged:
  BOSL2 is OpenSCAD, so it can never be imported — the attachments *concept* is High-value
  (a placement/mating abstraction this skill partly covers with `placement.py` /
  `mate_chain.py`), the code is reference-only.
- **Top vendoring candidates from the previously-unrated set**:
  `cq-queryabolt` (fastener cutout mixin, High) and `cq-electronics` (importable board
  keep-out bodies, Medium-High), with `tanius/cadquery-models` as the best license-free
  cherry-pick source.
- Anything rated Low/Very Low here is not wasted — those are inputs for the **Phase 0
  sourcing ladder** (`skill/phase0_sourcing.md`), which handles one-off finished models.
  Consider splitting this file into a "blocks candidates" table and a "Phase 0 search
  corpus" list.
