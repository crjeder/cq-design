## MODIFIED Requirements

### Requirement: Planning prompt produces structured BUILD_PLAN
The system SHALL provide a `prompts/planning.md` prompt that, when invoked with a user's model description, produces a valid `BUILD_PLAN.json` file conforming to the defined schema.

The prompt SHALL include a coordinate vocabulary section defining:
- North = +Y, East = +X, South = -Y, West = -X, Up = +Z, Down = -Z
- The Down face (Z=0) is always the print bed face

The prompt SHALL instruct the LLM to populate `planning_notes` with overall design rationale before committing to any dimension values.

The prompt SHALL instruct the LLM to populate `part_notes` for any part whose `blocks_needed` is empty, explaining what will be written from scratch.

The prompt SHALL provide a fit-type clearance table and instruct the LLM to:
1. Extract stated clearance preference from the user's request if present
2. Ask the user interactively if the fit type is ambiguous
3. Default to the lower end of the relevant fit-type range otherwise

Fit-type clearance defaults:
- press_fit: 0.0 mm
- snap_fit: 0.15 mm
- sliding: 0.25 mm
- loose/cover: 0.5 mm

The prompt SHALL instruct the LLM to apply per-interface `clearance_mm` overrides when a specific interface requires a different clearance than the assembly default.

The prompt SHALL instruct the LLM to omit the `assembly` key entirely when `parts` contains exactly one entry.

#### Scenario: Single-part model
- **WHEN** user describes a simple enclosure for an Arduino Nano
- **THEN** planning prompt produces a `BUILD_PLAN.json` with one part entry, printer/material constraints, at least one interface entry for the USB port, and no `assembly` key

#### Scenario: Multi-part model
- **WHEN** user describes a hinged box with a snap-fit lid
- **THEN** planning prompt produces a `BUILD_PLAN.json` with at least two part entries and an `assembly` strategy entry

#### Scenario: Dimension research required
- **WHEN** the model involves a known real-world product (phone, PCB, connector)
- **THEN** the planning prompt instructs the LLM to perform web search for exact dimensions before populating the plan

#### Scenario: Dimension cannot be verified
- **WHEN** the LLM cannot find a verified dimension via web search
- **THEN** the LLM emits -1 for that dimension value, records the unknown in `planning_notes`, and asks the user for the correct value in the same conversational turn before finalizing the JSON

#### Scenario: Interface with non-default clearance
- **WHEN** a part has both a snap-fit join (0.15 mm) and a press-fit PCB standoff (0.0 mm)
- **THEN** the assembly-level `clearance_mm` is set to 0.15 and the press-fit interface carries a `clearance_mm: 0` override

#### Scenario: Coordinate vocabulary used for interface walls
- **WHEN** a USB-C port is on the front of an enclosure
- **THEN** the interface entry uses `"wall": "south"` (South = -Y = front-facing in default orientation)

#### Scenario: Planning notes populated
- **WHEN** the LLM chooses to split a model into two parts
- **THEN** `planning_notes` contains the reasoning for the split decision

#### Scenario: Part notes populated for scratch geometry
- **WHEN** a part's `blocks_needed` is empty
- **THEN** `part_notes` for that part describes what geometry will be written from scratch

---

### Requirement: BUILD_PLAN.json schema includes part decomposition, interfaces, and block selection
The `BUILD_PLAN.json` schema SHALL include the following top-level fields:

- `schema_version` (integer, required)
- `intent` (string, required)
- `printer` (string, required)
- `material` (string, required)
- `nozzle_mm` (number, required)
- `parts` (array of part objects, required, min 1)
- `assembly` (object, required only if `parts` length > 1)
- `constraints` (object, required)
- `planning_notes` (string, optional)

Each part object SHALL include:
- `id` (string, required, unique)
- `description` (string, required)
- `dimensions` (object with `w_mm`, `d_mm`, `h_mm`, required)
- `interfaces` (array, may be empty)
- `blocks_needed` (array of block names from inventory, may be empty)
- `part_notes` (string, optional)

Each interface object MAY include:
- `clearance_mm` (number, optional): overrides `assembly.clearance_mm` for this interface only

The `print_orientation` field is removed from the part object schema and is no longer required or accepted.

#### Scenario: Part with physical interface
- **WHEN** a part has a USB-C port cutout
- **THEN** its `interfaces` array contains an entry with `type: "port_cutout"`, `connector: "usb_c"`, `wall` (using coordinate vocabulary), and `size_mm`

#### Scenario: Part with no interfaces
- **WHEN** a part is a simple bracket with no connectors or mating surfaces
- **THEN** its `interfaces` array is empty and validation still passes

#### Scenario: Single-part plan has no assembly key
- **WHEN** `BUILD_PLAN.json` has exactly one entry in `parts`
- **THEN** the `assembly` key is absent and validation passes

#### Scenario: Plan with planning_notes
- **WHEN** `BUILD_PLAN.json` includes a `planning_notes` string
- **THEN** validation passes (field is optional and unvalidated)

#### Scenario: Plan with part_notes
- **WHEN** a part object includes a `part_notes` string
- **THEN** validation passes (field is optional and unvalidated)

## REMOVED Requirements

### Requirement: print_orientation is a required part field
**Reason:** The field was free text with no enumeration, was not consumed consistently by downstream prompts, and is made redundant by the Z=0 print-bed convention already enforced in `part.md` and by the coordinate vocabulary used for interface wall positions.
**Migration:** Remove `print_orientation` from all BUILD_PLAN.json files and test fixtures. Interface wall positions expressed with coordinate vocabulary (`"wall": "south"`) replace any orientation information the field carried.
