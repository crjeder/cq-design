## 1. Sourcing prompt

- [x] 1.1 Write `prompts/sourcing.md`: no-user-channel framing (matching `research.md`'s
      contract), the collect-then-classify search workflow (one web search, then
      Thingiverse/Printables/MakerWorld/GitHub), and a seed corpus section fed by
      `{{SOURCING_CORPUS}}`
- [x] 1.2 Define the candidate return contract: Markdown table (or JSON, matching
      `research.md`'s style) with `source`, `platform`, `kind`, `license`, `notes` per
      candidate, plus a source list
- [x] 1.3 Delete `prompts/find_parts.md`

## 2. render_prompt.py wiring

- [x] 2.1 Add `render_sourcing(request: str) -> str` to `src/render_prompt.py`, filling
      `{{REQUEST_TEXT}}` and `{{SOURCING_CORPUS}}` (extracted from
      `documentation/Block_Sources.md` section 2 via new `sourcing_corpus()` helper) --
      no `{{SKILL_DIR}}` needed since the prompt has no shell command (spec amended
      during implementation)
- [x] 2.2 Add the `sourcing` subcommand to `render_prompt.py`'s CLI (`--request-file`,
      `--out` default `build/sourcing_prompt.txt`), matching the `research` subcommand's
      argument/print shape
- [x] 2.3 Add `tests/test_render_prompt.py` coverage for `render_sourcing()`: fills the
      corpus tables, fails on an unfilled placeholder (mirroring existing
      `render_research()` tests)

## 3. Phase 0 skill doc

- [x] 3.1 Replace `skill/phase0_sourcing.md`'s inline "Search workflow" section with
      dispatch instructions: write the request to a file, run
      `render_prompt.py sourcing`, spawn the sourcing agent with
      `Read <out> in full and follow it.`, receive the candidate list
- [x] 3.2 Keep the five-rung ladder, collect-then-classify rule, license section, and
      rung-3 user-confirmation step unchanged -- they now operate on the agent's
      candidate list instead of search results gathered inline
- [x] 3.3 Update the cross-reference in `skill/phase1_requirements.md` (currently "Phase 0
      search reuses Phase 1's workflow by reference") to point at the sourcing agent
      instead

## 4. Architecture doc

- [x] 4.1 Add a `Sourcing` row to `ARCHITECTURE.md`'s agent roster table (model: default,
      input: rendered `prompts/sourcing.md`, output: candidate list, why: page snapshots
      stay out of the main session -- same justification as Research)
- [x] 4.2 Add a `SOURCING` node to the mermaid diagram, feeding Phase 0's classification
      step the same way `RESEARCH` feeds `CK1`

## 5. Validation

- [x] 5.1 Run `uv run pytest tests/test_render_prompt.py tests/test_plan_validate.py` to
      confirm nothing regresses -- 141 passed
- [x] 5.2 Confirm `skill/phase0_sourcing.md` reads standalone (ladder, license rules,
      dispatch instructions all present) and `SKILL.md` stays under 10 KB -- doc reads
      standalone (fixed a stale "ladder below" cross-reference found during review);
      `SKILL.md` untouched by this change, still 10,648 bytes, a pre-existing over-limit
      noted as out of scope by the original phase0-sourcing-triage change
- [x] 5.3 Dry-run Phase 0 on one request answerable by a found model (e.g. a common phone
      stand) to confirm the sourcing agent returns a usable candidate list and the
      existing rung-3 user-confirmation flow still works unchanged -- live dry run via a
      general-purpose agent reading the rendered `build/sourcing_prompt.txt` returned a
      well-formed candidate table (Thingiverse + MakerWorld hits, correctly declining to
      cite two Printables candidates blocked by Cloudflare instead of inventing sources)
