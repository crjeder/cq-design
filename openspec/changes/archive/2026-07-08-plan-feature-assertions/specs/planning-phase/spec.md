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
each part's `placement`.

Each part object SHALL include:
- `id` (string, required, unique)
- `description` (string, required)
- `dimensions` (object with `w_mm`, `d_mm`, `h_mm`, required)
- `interfaces` (array, may be empty)
- `blocks_needed` (array of block names from inventory, may be empty)
- `print_orientation` (string, required)

Each `interfaces[]` entry SHALL require `type` (string) and MAY carry structured,
machine-readable placement fields (all optional): `wall` (one of the six face names),
`position_mm` (`[x, y, z]`, the feature's intended center in the part's authored frame),
and a size field (`diameter_mm` for round features, or `size_mm` as `[w, h]` for
rectangular). These fields SHALL be defined in the schema (not free-form
`additionalProperties`), so a declared placement is machine-readable; they remain optional
so an interface may declare only its `type`, and an empty `interfaces` array still
validates.

#### Scenario: Part with physical interface
- **WHEN** a part has a USB-C port cutout
- **THEN** its `interfaces` array contains an entry with `type: "port_cutout"`, `connector: "usb_c"`, `wall`, and `position_mm`

#### Scenario: Interface with structured placement is machine-readable
- **WHEN** an interface entry declares `position_mm` and a size field
- **THEN** the schema validates them as structured fields (an array of numbers for `position_mm`, a number or `[w, h]` for the size), rejecting a malformed placement

#### Scenario: Interface with only a type still validates
- **WHEN** an interface entry declares `type` but no `wall`, `position_mm`, or size
- **THEN** validation passes (the placement fields are optional)

#### Scenario: Part with no interfaces
- **WHEN** a part is a simple bracket with no connectors or mating surfaces
- **THEN** its `interfaces` array is empty and validation still passes

#### Scenario: Multi-part plan needs no assembly object
- **WHEN** a plan contains two or more parts
- **THEN** validation passes without an `assembly` field, and the schema rejects an `assembly` property if one is supplied
