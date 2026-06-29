## MODIFIED Requirements

### Requirement: Interface type vocabulary is a closed set
The system SHALL enforce that all interface `type` values in `inventory.json` belong to the
following closed set:

`face_mount`, `screw_hole`, `snap_hook`, `snap_socket`, `axis`, `pin`, `socket`, `slot`,
`port_cutout`, `sliding_interface`, `nut_trap`, `hinge_axis`, `ball`, `ball_socket`,
`finger`, `mortise`, `tenon`, `dowel`, `seam`, `union`

The vocabulary SHALL be enforced identically by the inventory JSON Schema `type` enum and the
inventory validator, so the two agree on the accepted set.

#### Scenario: Valid interface type
- **WHEN** an inventory entry declares `"type": "screw_hole"`
- **THEN** inventory loads without error

#### Scenario: nut_trap interface type accepted
- **WHEN** an inventory entry declares `"type": "nut_trap"`
- **THEN** inventory loads without error

#### Scenario: sliding_interface type accepted
- **WHEN** an inventory entry declares `"type": "sliding_interface"`
- **THEN** inventory loads without error

#### Scenario: seam interface type accepted
- **WHEN** an inventory entry declares `"type": "seam"`
- **THEN** inventory loads without error

#### Scenario: union interface type accepted
- **WHEN** an inventory entry declares `"type": "union"`
- **THEN** inventory loads without error

#### Scenario: Invalid interface type
- **WHEN** an inventory entry declares `"type": "glue_tab"` (not in vocabulary)
- **THEN** inventory validation raises an error naming the block and the invalid type

## ADDED Requirements

### Requirement: The `union` interface marks a fused-to-body connection
A `union` interface SHALL denote a face or region where the block is rigidly fused
(boolean-unioned) into its parent part's body, producing one printed rigid body with no
assembly seam and no relative motion. It is distinct from a mating dock (`face_mount`,
`snap_hook`/`snap_socket`, `dovetail`/`finger`/`mortise`/`tenon`, `pin`/`socket`, ...), which
joins this block to a separately printed part across a seam, and from a kinematic axis
(`axis`, `hinge_axis`, `ball`/`ball_socket`, ...), which defines a moving joint. A `union`
interface descriptor SHALL carry the same required fields as any other interface
(`type`, `orientation`, `origin`).

#### Scenario: Fused sub-feature uses union, not face_mount
- **WHEN** a block (e.g. a `screw_boss` welded onto an enclosure wall) is rigidly fused into
  its parent part's body rather than mating with a separate printed part
- **THEN** the connection is expressed as a `union` interface, not a `face_mount`

#### Scenario: Union interface has the standard descriptor shape
- **WHEN** a block declares `{"type": "union", "orientation": "+Z", "origin": [0, 0, 5]}`
- **THEN** it validates like any other interface, locating the fused region in block-local
  coordinates
