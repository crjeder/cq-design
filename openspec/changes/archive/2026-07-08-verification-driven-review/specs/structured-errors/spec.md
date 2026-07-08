## ADDED Requirements

### Requirement: Disconnected union bodies are reported as structured errors

The wrapper (`run_cadquery_model.py`) SHALL emit a blocking `disconnected_body` error
when a union body splits into more than one connected component. Each declared union
maps to one rigid printed body and is therefore expected to tessellate into a single
connected component. The emitted `errors` entry SHALL carry `type:
"disconnected_body"`, the offending `union` id, a
`component_count`, and a `message` listing each component's bounding box and volume,
plus a `hint` directing the author to union or bridge the pieces into one body. The
check SHALL run per union (a single-`Workplane` result is one union with id equal to
the part id; a `dict` result is checked once per union key) and SHALL exclude the
reserved keep-out key.

#### Scenario: Union splits into multiple bodies

- **WHEN** a part's `result` union tessellates into two non-touching solids
- **THEN** `errors` contains one entry with `type: "disconnected_body"`, the `union`
  id, `component_count: 2`, per-component bbox/volume in `message`, and a bridging
  hint; `success` is `false`

#### Scenario: Single connected body

- **WHEN** a union tessellates into exactly one connected component
- **THEN** no `disconnected_body` entry appears in `errors`

#### Scenario: Multi-union part checked per union

- **WHEN** a `dict` result declares two unions, each a single connected body
- **THEN** no `disconnected_body` entry appears, even though the part has two separate
  bodies, because each declared union is independently one component

#### Scenario: Keep-out zone excluded

- **WHEN** a `dict` result carries the reserved keep-out key alongside union bodies
- **THEN** the keep-out entry is not subjected to the connected-component check
