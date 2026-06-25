# Design: dedupe-3mf-object-names

## Decision 1: Disambiguate by suffixing the part id

The part `id` is required and unique per plan (the schema requires it, and the kinematic and
placement code already key on it as a unique handle). So suffixing a colliding object's name
with its part id yields a name that is unique without inventing a counter or mutating
unrelated objects. This is also what the operator wants: the id is the stable handle they
see everywhere else (STL filenames `<id>.stl`, plate tags), so `"Hinge leaf (left_leaf)"`
ties the 3MF object back to the rest of the deliverables.

Format: `f"{base} ({pid})"`. The parenthesized id reads as a disambiguator and keeps the
human-readable description first.

## Decision 2: Only suffix actual collisions

Compute every part's base name first (`_object_name(description, id)`), then count how many
parts share each base name. Suffix only the names that occur more than once. A model whose
descriptions are already distinct produces byte-for-byte the same names as today, so this
change does not churn existing output or break any operator's muscle memory for the common
case.

## Decision 3: Uniqueness is closed under the suffix

Because part ids are unique, the suffixed names `"{base} ({id})"` are unique among the
colliding group. The only way a suffixed name could still collide is if some *other* part's
base name were literally the string `"{base} ({id})"` -- a description deliberately crafted
to mimic the disambiguator. This is not a real authoring case and not worth a second pass;
the dedup operates on the base-name collision set, which is the documented bug. (If a future
need arises, a final "append an integer until unique" pass can be layered on without changing
the spec, which only promises uniqueness.)

## Decision 4: Where it runs

The pass sits in `export_model` between computing the per-part object tuples and calling
`write_named_3mf` (`model_export.py:94-103`). It is pure string work over the parts list --
no geometry, no new imports. `_object_name` keeps its single responsibility (sanitize one
description); the new helper owns cross-part uniqueness.

Sketch:

```python
base_names = [_object_name(p.get("description", ""), p["id"]) for p in parts]
counts = Counter(base_names)
names = [
    f"{base} ({p['id']})" if counts[base] > 1 else base
    for base, p in zip(base_names, parts)
]
```

`names[i]` then feeds the `objects` tuple in place of the inline `_object_name(...)` call.
