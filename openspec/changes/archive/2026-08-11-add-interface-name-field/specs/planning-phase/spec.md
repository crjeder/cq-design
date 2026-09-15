## MODIFIED Requirements

### Requirement: BUILD_PLAN.json schema includes part decomposition, interfaces, and block selection
The `BUILD_PLAN.json` schema SHALL include the following top-level fields:

- `schema_version` (integer, required)
- `intent` (string, required)
- `printer` (string, required)
- `material` (string, required)
- `nozzle_mm` (number, required)
- `parts` (array of part objects, required, min 1)
- `constraints` (object, required)

The schema SHALL NOT define an `assembly` object, and SHALL NOT make any field
conditionally required on the number of parts. Multi-part assembly is expressed through
each part's `placement`, which the part author supplies during the build phase (see
`assembled-pose-handback`); the planner expresses the same relationship as each part's
`pose_intent`.

Each part object SHALL include:
- `id` (string, required, unique)
- `description` (string, required)
- `dimensions` (object with `w_mm`, `d_mm`, `h_mm`, required)
- `interfaces` (array, may be empty)
- `blocks_needed` (array of block names from inventory, may be empty)
- `print_orientation` (string, required)
- `pose_intent` (string, optional): the part's goal pose in the shared assembled frame,
  stated as intent rather than as a rotation sequence

Each `interfaces[]` entry SHALL require `type` (string) and MAY carry structured,
machine-readable placement fields (all optional): `name` (the agreed vocabulary word for
the feature), `wall` (one of the six face names), `position_mm` (`[x, y, z]`, the
feature's intended center in the part's authored frame), and a size field
(`diameter_mm` for round features, or `size_mm` as `[w, h]` for rectangular). These
fields SHALL be defined in the schema (not free-form `additionalProperties`), so a
declared placement is machine-readable; they remain optional so an interface may declare
only its `type`, and an empty `interfaces` array still validates.

The `name` field SHALL be constrained to the same normalized snake_case form as a part
`id` (`^[a-z][a-z0-9_]*$`), so that the mechanical normalization promised by the
user-noun naming rule is enforced by the schema rather than left to the planner.

#### Scenario: Part with physical interface
- **WHEN** a part has a USB-C port cutout
- **THEN** its `interfaces` array contains an entry with `type: "port_cutout"`, `connector: "usb_c"`, `wall`, and `position_mm`

#### Scenario: Interface with structured placement is machine-readable
- **WHEN** an interface entry declares `position_mm` and a size field
- **THEN** the schema validates them as structured fields (an array of numbers for `position_mm`, a number or `[w, h]` for the size), rejecting a malformed placement

#### Scenario: Named interface validates
- **WHEN** an interface entry declares `name: "inner_lip"` alongside its `type`
- **THEN** validation passes and the name is available to downstream consumers as a structured field

#### Scenario: Non-normalized interface name is rejected
- **WHEN** an interface entry declares `name: "Inner Lip"` or `name: "inner-lip"`
- **THEN** validation fails with a schema error naming the offending field, rather than silently accepting an unnormalized vocabulary word

#### Scenario: Interface with only a type still validates
- **WHEN** an interface entry declares `type` but no `name`, `wall`, `position_mm`, or size
- **THEN** validation passes (the placement fields are optional)

#### Scenario: Part with no interfaces
- **WHEN** a part is a simple bracket with no connectors or mating surfaces
- **THEN** its `interfaces` array is empty and validation still passes

#### Scenario: Multi-part plan needs no assembly object
- **WHEN** a plan contains two or more parts
- **THEN** validation passes without an `assembly` field, and the schema rejects an `assembly` property if one is supplied

#### Scenario: Part declares its pose as intent
- **WHEN** a planner positions a part away from the assembled-frame origin
- **THEN** the part carries a `pose_intent` string and no planner-written `placement`

## ADDED Requirements

### Requirement: Interface names are unique within a part
`plan_validate.py` SHALL reject a plan in which two `interfaces[]` entries of the same
part declare the same `name`, mirroring the existing union-id uniqueness cross-check.
The error SHALL name the part and the duplicated name. Because callout badges are
numbered by supply order and the legend echoes names verbatim, a duplicate name within
one part would produce two indistinguishable legend lines and an ambiguous conversational
reference. Names SHALL be permitted to repeat across different parts, where the part id
disambiguates them.

#### Scenario: Duplicate name within one part is rejected
- **WHEN** a part declares two interfaces both named `mount_hole`
- **THEN** validation fails with an error naming that part and the duplicated name

#### Scenario: Same name on two different parts is accepted
- **WHEN** two different parts each declare an interface named `mount_hole`
- **THEN** validation passes

#### Scenario: Unnamed interfaces do not collide
- **WHEN** a part declares three interfaces, none of which carries a `name`
- **THEN** validation passes (the uniqueness check considers only declared names)
