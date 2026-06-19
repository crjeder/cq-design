# TODO

Tasks not tracked in an `openspec/changes/` change. Anything tied to a specific
change lives in that change's `tasks.md`, not here.

- [x] add kinematic analysis using PyBullet
- [x] add install script for skill
- [x] publish on github
- [x] check filament hinge understanding
- [ ] kinematic: explore adding one simple ground/seating plane (lid-hits-floor
      checks); surrounding-geometry questions stay out of scope (external simulation)
- [ ] kinematic: articulated chains (a moving union carries other unions through
      the sweep) -- deferred
- [ ] gate: plate clearance check -- co-plated unions must keep a gap > layer
      height everywhere or they fuse in the print
- [ ] joints: side-tagged `face_mount` docks so the planner derives union
      membership and the world joint axis automatically (interface naming: keep
      assembly/mating docks conceptually distinct from kinematic axes even though
      both live in the block `interfaces` array)
- [ ] `interface`needs a third type: `union` (extending `face_mount`, `hinge_axis`) where it is    
      fused to the body. `hinge_axis`is to narrow.

