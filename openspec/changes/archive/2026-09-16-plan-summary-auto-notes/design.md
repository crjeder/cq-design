## Context

`plan_summary.py` is a pure function (`summarize(plan, plan_path) -> str`) over an
already-schema-validated `BUILD_PLAN.json`. It has no CadQuery dependency and no I/O
beyond the path label, and its only caller is the Phase 2 checkpoint step in
`skill/phase2_planning.md`. `planning_notes` is one free-text string (not an array);
`prompts/planning.md` rule 4a is the only place that defines the `OPEN:` convention, and
it does not pin a line format beyond "starts with `OPEN:`" -- the planner prompt itself
shows no bullet marker, but nothing forbids the LLM prefixing one, so the parser has to
tolerate `- OPEN: ...` / `* OPEN: ...` / bare `OPEN: ...`.

## Goals / Non-Goals

**Goals:**
- Move the two mechanical extractions (open questions, coined names) out of session-side
  reading of `planning_notes` and into `plan_summary.py`, so the checkpoint's Markdown is
  the single source both the user and the session read.
- Keep the function pure and dependency-free (stdlib only, matching every other
  fast/no-CadQuery test file).

**Non-Goals:**
- Not touching **Design proposals** -- that category requires judging whether a
  `planning_notes` sentence is a proposal versus a stated fact, which stays inline LLM
  work.
- Not changing `BUILD_PLAN.json`'s schema or `planning_notes`'s type (still a single
  string, not a structured list) -- reformatting it as structured data is a bigger change
  than this proposal's scope and would touch every prompt that writes it.
- Not deduplicating or ranking flagged names -- one line per part/interface is enough for
  a human checkpoint.

## Decisions

**Open questions -- line-based `OPEN:` scan.** Split `planning_notes` on `\n`, strip
whitespace and a leading bullet marker (`-`, `*`, or `+` plus following space) from each
line, keep lines whose remainder starts with `OPEN:` (case-sensitive -- the prompt always
emits the literal token, so a case-insensitive match risks catching prose that merely
mentions "open"). Render as a Markdown bullet list under **Open questions**; omit the
section when the list is empty. This mirrors the existing informal rule in
`skill/phase2_planning.md` exactly, just executed by the script instead of by the reading
session.

Alternative considered: regex over the whole string with `re.MULTILINE`. Rejected --
splitlines + strip is the same result with less to explain, and the existing codebase
(`_load`, `_blocks` in this same file) already favors small stdlib loops over regex.

**Names I chose -- word-boundary substring check against `request_log[].text`.** For each
part `id` and each non-empty `interfaces[].name`, build the set of words
(`re.findall(r"[a-z0-9]+", text.lower())`) across every `request_log[].text`, and flag the
candidate when its own lowercased word-tokens are not a subset of that set. A name with an
underscore (e.g. `hole_2`) is split the same way, so `hole_2` matches if the user's text
contains "hole" (disambiguation suffixes like `_2` are expected not to appear verbatim,
per the phase2 doc's own `hole_2` example). Render as a Markdown bullet list under **Names
I chose**; omit the section when `request_log` is absent/empty (nothing to check against
-- silently omitting avoids flagging every name against no evidence) or when every
candidate matches.

Alternative considered: exact whole-name substring match (`name.lower() in full_text`).
Rejected -- `hole_2` or a hyphenated id would never literally appear in prose even when
every component word does, producing false positives on the exact case the phase2 doc
calls out as expected (suffix disambiguation).

**Placement in `plan_summary.py`, not a new module.** Both are small, single-purpose
functions reading fields `summarize()` already has in scope; a separate module would be
an unused-elsewhere abstraction for two ~10-line helpers.

## Risks / Trade-offs

- [Tokenizing loses some legitimate matches, e.g. planner writes `usb_c` but user said
  "USB-C port"] -> tokenizer splits on non-alphanumeric on both sides (`usb`, `c` vs.
  `usb`, `c`, `port`), so this actually matches; residual false positives (synonyms,
  paraphrase) are expected and acceptable -- the section is a nudge for the user to skim,
  not a hard gate, exactly like today's manual version.
- [`OPEN:` scan is case-sensitive and a planner drifts to lower-case `open:`] -> the
  planner prompt (`prompts/planning.md`) is the single source that emits this token and
  already pins it to the literal uppercase form; if this ever drifts, fix the prompt, not
  loosen the parser and risk false positives on prose.

## Open Questions

None -- scope is fully bounded by the two extractions named in the proposal.
