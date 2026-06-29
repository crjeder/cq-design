## ADDED Requirements

### Requirement: Thin-region detection is robust to mesh triangle density

The geometry-level thin-region detector SHALL report a contiguous thin wall regardless of how
finely the part is tessellated. Subsampling the local-thickness ray-cast for performance SHALL
NOT cause a thin wall to go unreported on meshes whose face count exceeds the sample cap: a
thin wall reported on a coarse mesh SHALL still be reported when the same wall is remeshed to
more faces than the cap. The detector SHALL preserve the ray-cast performance bound (the
number of thickness rays stays bounded by the sample cap; the per-face thickness pass SHALL
NOT scale with the square of the full face count), and each reported region SHALL keep its
existing fields (thickness, thin direction, XY/Z orientation, location, nearest feature,
brittle flag), computed from measured faces.

#### Scenario: Thin wall on a mesh above the sample cap is still reported
- **WHEN** a part with a thin wall (thin direction in the XY plane) is tessellated to more
  faces than the ray-cast sample cap
- **THEN** the detector still reports that wall as a thin-in-XY region with its measured
  thickness, rather than returning no thin regions

#### Scenario: Result is stable across tessellation density
- **WHEN** the same thin-walled part is measured at a coarse tessellation (at or below the
  cap) and at a fine tessellation (above the cap)
- **THEN** both measurements report the thin wall as a region with comparable thickness, so
  the finding does not depend on triangle count

#### Scenario: Uniformly thick dense mesh reports nothing
- **WHEN** a part whose every region is at or above the thickness threshold is tessellated to
  more faces than the cap
- **THEN** the detector reports no thin regions (the density-robust grouping does not
  manufacture spurious regions from unsampled faces)
