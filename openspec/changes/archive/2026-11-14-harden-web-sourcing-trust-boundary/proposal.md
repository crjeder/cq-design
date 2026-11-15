## Why

The sourcing and research agents read untrusted web content (model descriptions, comments,
spec pages, downloaded STLs, linked scripts) while holding Bash, Write and Edit, and they hand
free-form Markdown back to the privileged main session. A prompt injection in a Thingiverse
comment can therefore run shell commands, and injected text in a `Notes` cell reaches the
session that owns the user channel and every tool. Rung 1 goes further: a found CadQuery script
is "reused directly", which executes third-party Python with the user's privileges. Natural
language cannot be sanitized reliably, so the fix is structural: shrink what the readers can
do, type what they can return, and never execute web code without the user's consent.

## What Changes

- **Agent tool trim.** `agents/sourcing.md` drops Bash, Write, Edit, Glob and Grep (keeps
  Read for its prompt file, WebSearch, WebFetch). `agents/research.md` drops Write, Edit, Glob
  and Grep (keeps Read, WebSearch, WebFetch, and Bash for `fetch_stl.py` and
  `measure_stl.py` only).
- **Typed return contract.** Both agents return one fenced JSON block instead of a Markdown
  table. The main session saves it and runs a new validator script
  (`src/web_result.py`), which checks types, enums, URL shape and lengths, strips control
  characters, and renders the display table. The main session acts only on the validator's
  output. **BREAKING** for anything parsing the old Markdown table (only the skill prose does).
- **Notes are display-only.** Free-text fields (`notes`, source descriptions) are shown to
  the user and SHALL NOT be copied into `BUILD_PLAN.json`, `known_context.md`, planner or
  builder prompts, or generated scripts.
- **Controlled STL download.** A new `src/fetch_stl.py` replaces the inline
  `urllib.urlretrieve` call: http(s) only, size cap, STL parse check, fixed output directory
  `build/refs/`, filename derived by the script. No domain allowlist.
- **Rung 1 code execution needs consent.** A found CadQuery script (and a mechanically
  converted build123d script) is flagged as third-party code; the main session SHALL ask the
  user for permission before it is run. On decline, the part is re-authored through the normal
  part loop, the same way OpenSCAD sources are handled.
- **Source strings are safe to embed.** The validator rejects source values containing
  newlines or non-URL text, so `# researched: <source>` comments cannot break out into code.
- Prompts get one line marking page text as data, not instructions (backstop only).

## Capabilities

### New Capabilities
- `web-result-validation`: typed JSON return contract for the sourcing and research agents,
  the `web_result.py` validator, and the display-only rule for free-text fields.
- `reference-download`: `fetch_stl.py`, the single sanctioned way to download a reference
  mesh from the web.

### Modified Capabilities
- `agent-definitions`: sourcing and research tool lists shrink to the minimum their task needs.
- `subagent-orchestration`: sourcing and research agents return validated JSON; the main
  session acts only on validator output.
- `sourcing-triage`: rung 1 CadQuery reuse and build123d conversion require explicit user
  permission before third-party code runs; decline falls back to re-authoring.

## Impact

- `agents/sourcing.md`, `agents/research.md` (and the project copies `init_permissions.py`
  installs).
- `prompts/sourcing.md`, `prompts/research.md` return contracts and the STL download step.
- `skill/phase0_sourcing.md` (rung 1 consent, validator step), `skill/phase1_requirements.md`
  (validator step, display-only notes).
- New `src/web_result.py`, `src/fetch_stl.py`, their tests, entries in `FILES.md` and
  `reference/scripts.md`, and Bash allow-patterns in `src/skill_permissions.json`.
- Existing tests that assert agent tool lists (`agent-definitions`) need updating.
