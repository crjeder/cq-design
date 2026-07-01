## REMOVED Requirements

### Requirement: Hinge leaf carries interleaving knuckles on a pin axis
**Reason**: The lone-half `hinge_leaf` factory (one leaf per call, authored by two
independent calls) is the matched-pair anti-pattern -- nothing binds the two halves to a
single parametric source, so they can drift apart until they no longer mate. It is
superseded by `pin_hinge`, which carries both matched leaves.
**Migration**: For a print-in-place hinge, use `pin_hinge`, which returns both leaves as
the named member unions `leaf_a`/`leaf_b`. A separate-parts hinge (two independently
printed leaves) is withdrawn until the cross-part kinematic tree can distribute
`pin_hinge`'s two members onto two parts.

### Requirement: Pin variant bores a pin hole; print-in-place leaves a gap
**Reason**: Part of the removed `hinge_leaf` factory; `pin_hinge` covers the print-in-place
bored-knuckle hinge.
**Migration**: Use `pin_hinge` (filament-pin print-in-place hinge).

### Requirement: Hinge inventory entry states the required print orientation
**Reason**: Part of the removed `hinge_leaf` inventory entry.
**Migration**: The `pin_hinge` inventory `use` string states the required print
orientation for the print-in-place hinge.
