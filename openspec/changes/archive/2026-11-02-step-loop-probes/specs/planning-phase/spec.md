## ADDED Requirements

### Requirement: Build plan carries every instance's parameters and edge treatments
Each object in a part's `blocks_needed` SHALL be able to carry `id` (snake_case,
unique within the part), `params` (name -> value) and `edges` (edge-set name -> size in
mm). For a part built as a step script, every block, template and primitive instance
the script selects SHALL have such an entry with `id` and `params`. `plan.py validate`
SHALL fail when an instance's `params` names a parameter its inventory entry does not
declare, omits a required one, or `edges` names an edge set the entry does not declare.

#### Scenario: Instance with complete params
- **WHEN** the plan declares `{"name": "screw_boss", "id": "boss", "params": {"d_screw":
  3.2, "d_outer": 8, "h": 6}}`
- **THEN** plan validation passes for that instance

#### Scenario: Unknown edge set
- **WHEN** a `box` instance declares `edges: {"rim": 1.0}` and `box` has no `rim` set
- **THEN** plan validation fails naming the instance, `rim`, and the entry's edge sets

#### Scenario: Missing required param
- **WHEN** a `cylinder` instance omits `h`
- **THEN** plan validation fails naming the instance and `h`
