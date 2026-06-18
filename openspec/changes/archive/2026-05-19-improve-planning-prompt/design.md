## Context

The CAD skill pipeline has three prompt templates (`planning.md`, `part.md`, `assembly.md`) and a JSON schema (`build_plan_schema.json`) that must share a consistent vocabulary. Currently `print_orientation` is a free-text string in the schema with no enumeration; `part.md` receives it via `{{PRINT_ORIENTATION}}` but does its own thing ("use centered=(True,True,False) so bottom is at Z=0"), making the field effectively noise. Clearance guidance is a single 0.3–0.5 mm range regardless of fit type, which is mechanically incorrect for press-fit and snap-fit joins.

The planning step runs inside an interactive Claude Code skill session (not via `claude -p`). The LLM can ask the user questions in the conversation before writing JSON to disk; the JSON output and the conversational turn are separate channels.

## Goals / Non-Goals

**Goals:**
- Remove `print_orientation` cleanly from schema, validator, orchestrator, and both prompt templates
- Establish North/South/East/West/Up/Down coordinate vocabulary in both `planning.md` and `part.md`
- Add `planning_notes` (top-level) and `part_notes` (per-part) as optional JSON fields for LLM reasoning
- Replace the single clearance range with a fit-type table; add optional per-interface `clearance_mm` override
- Give the LLM a defined path when web search fails for dimensions (-1 placeholder + interactive ask)
- Suppress the `assembly` block for single-part models in the prompt

**Non-Goals:**
- Changing the orchestration loop (orchestrate.py) beyond removing the `{{PRINT_ORIENTATION}}` replacement line
- Adding new JSON Schema enforcement for `planning_notes`/`part_notes` (additionalProperties is already unrestricted)
- Changing `part.md` beyond removing `{{PRINT_ORIENTATION}}` and adding the coordinate vocabulary section
- Changing the assembly or quality-gate phases

## Decisions

### D1: Remove `print_orientation` entirely rather than redefine it

**Decision:** Delete the field from schema, validator, orchestrator, and prompt templates.

**Rationale:** The field is redundant. `part.md` already enforces Z=0 as the print bed via `centered=(True,True,False)`. The only practical information it carried ("which face is up") is now expressed through interface wall positions using the coordinate vocabulary. Keeping a redundant required field creates drift risk between what planning writes and what part.md expects.

**Alternative considered:** Keep the field as a coordinate-vocab string (e.g., `"down"` = print bed face). Rejected: adds no information that isn't already in the geometry + interface positions, and keeps a required field that implementers must maintain in tests and fixtures.

### D2: Coordinate vocabulary lives in both prompt templates as a shared glossary

**Decision:** Both `planning.md` and `part.md` include the same six-line table:

```
North = +Y   South = -Y
East  = +X   West  = -X
Up    = +Z   Down  = -Z   (Down face = print bed)
```

**Rationale:** The two prompts run in separate `claude -p` invocations and share no runtime state. The only shared contract is the BUILD_PLAN JSON and the vocabulary used to describe it. Embedding the same table in both prompts is the simplest way to guarantee consistent interpretation without a dynamic lookup.

**Alternative considered:** A shared vocabulary file included via `{{COORDINATE_VOCAB}}` injection. Rejected: adds an orchestrator template slot for a six-line table; not worth the indirection.

### D3: `planning_notes` and `part_notes` are unvalidated JSON fields

**Decision:** Add the fields to the schema as optional strings under `additionalProperties`-style relaxation; the validator does not enforce their presence or content.

**Rationale:** Their purpose is LLM reasoning scratchpad, not machine-readable contract. Strict validation would add maintenance overhead with no benefit. The fields are explicitly mentioned in the planning prompt so the LLM knows to populate them.

**Alternative considered:** Enforce `planning_notes` as required. Rejected: adds friction for programmatic plan construction (e.g., tests) and provides no correctness guarantee.

### D4: Per-interface `clearance_mm` override, not a per-interface fit_type enum

**Decision:** Add an optional `clearance_mm` number to each interface object. The planning prompt maps fit types to recommended values; the LLM writes the resolved number into the JSON.

**Rationale:** The downstream consumer (assembly.md) receives a number, not a fit-type label. Resolving fit-type to mm in the planning step keeps the assembly prompt simple. A fit_type enum would require assembly.md to carry the same lookup table.

**Alternative considered:** Add `fit_type` enum to interface schema and resolve in assembly.md. Rejected: spreads the clearance table across two prompts and requires schema changes to enumerate fit types.

### D5: Interactive dimension fallback via -1 placeholder and conversational ask

**Decision:** When a dimension cannot be verified, the LLM emits `-1` for that value and lists it in `planning_notes`. The planning prompt instructs the LLM to then ask the user in the same conversational turn before finalizing the JSON.

**Rationale:** Planning is an interactive skill step. The user is present. An explicit `-1` placeholder is machine-detectable (plan_validate.py could optionally warn on negative dimensions in a future pass) and forces the issue into `planning_notes` where it is visible. Silent guessing is worse than asking.

**Alternative considered:** Emit a `clarification_needed` top-level array in the JSON and have the orchestrator pause. Rejected: requires orchestrator changes and a new schema field for a problem that is simpler to resolve in conversation before the JSON is written.

## Risks / Trade-offs

- **Breaking schema change** → All existing BUILD_PLAN.json files and test fixtures that include `print_orientation` will fail validation after the schema change. Mitigation: update all test fixtures in the same PR; note the breaking change in the proposal.
- **Coordinate vocab coherence over time** → If `part.md` or `planning.md` are edited independently, the vocabulary tables could drift. Mitigation: the tables are short (6 lines each) and conspicuously placed; a code reviewer will notice divergence. A unit test that greps both files for the vocabulary terms would eliminate the risk entirely but is out of scope here.
- **LLM may still omit `part_notes`** → The field is optional and the LLM has no enforcement pressure to fill it. Mitigation: the planning prompt explicitly says "if `blocks_needed` is empty, you MUST populate `part_notes`" — making it a conditional requirement tied to a detectable condition.

## Migration Plan

1. Update schema, validator, orchestrator (one PR — all breaking changes together)
2. Update both prompt templates in the same PR
3. Update all test fixtures in the same PR
4. Run `python3 plan_validate.py` against any existing BUILD_PLAN.json files to confirm no regressions
5. No rollback complexity — this is a file-only change with no deployed service

## Open Questions

- Should `plan_validate.py` warn (not fail) when any dimension value is `-1`? Would make the placeholder convention machine-visible without a hard requirement. Out of scope for this change but worth a follow-up.
