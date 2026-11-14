## Context

Phase 0 (sourcing) and Phase 1 (research) run in sub-agents that read untrusted web content.
ARCHITECTURE.md already quarantines page snapshots in those agents, but three gaps remain:

```
  UNTRUSTED              QUARANTINE                         PRIVILEGED
  web pages   --->  sourcing / research agent   --->   main session
  STL files         tools: Bash, Write, Edit,          (user channel, all tools)
  GitHub .py        WebSearch, WebFetch                      |
                          | free-form Markdown               v
                          +----------------------->  planner -> builder -> Python runs
```

1. The quarantine agents hold side-effect tools (Bash, Write, Edit) while reading attacker text.
2. The return channel is free-form Markdown; `Notes` and source descriptions carry page text
   into the main session and onward into prompts and `# researched: <source>` script comments.
3. Rung 1 executes a found CadQuery script directly.

Prompt injection cannot be filtered out of natural language, so the design bounds capability
and output instead of trying to clean input.

## Goals / Non-Goals

**Goals:**
- Minimal tools for each web-reading agent.
- The main session consumes only typed, validated fields from those agents.
- Free text from the web is shown to the user and goes nowhere else.
- No third-party code runs without explicit user consent.
- One sanctioned, bounded path for downloading a reference STL.

**Non-Goals:**
- Detecting or classifying injection attempts in text (unreliable; out of scope).
- A domain allowlist for downloads or WebFetch beyond the existing permission seed.
- Sandboxing CadQuery execution (rung 1 relies on consent for now).
- Hardening the planner, builder or auditor (they do not read web content).

## Decisions

### D1. Typed JSON return, validated by a script

Each agent ends with one fenced ```json block. Shapes:

- sourcing: `{"candidates": [{"url", "platform", "kind", "license", "reusable", "rung", "notes"}]}`
- research: `{"rows": [{"item", "value", "unit", "source_urls", "status", "notes"}]}`

The main session writes the block verbatim to `build/sourcing_result.json` or
`build/research_result.json` and runs
`src/web_result.py validate --kind sourcing|research <file>`. The script:

- enforces enums (`platform`, `kind`, `reusable`, `rung`, `unit`, `status`) and types
  (`value` is a number; `-1` only with `missing`);
- requires every URL to parse as `http(s)://host/...` with no whitespace or control
  characters, length <= 500;
- caps `item` at 120 and `notes` at 300 characters, strips control characters and
  collapses newlines in display fields;
- emits `{"success", "errors", "data", "display_markdown"}` where `data` excludes `notes`
  and `display_markdown` is the table for the user.

The main session acts on `data` only and shows `display_markdown` to the user. On
`success: false` it resumes the same agent once with the `errors`, then treats the agent as
having returned nothing.

*Alternatives:* keep Markdown and let the main session parse it (an LLM parser is the
attack surface); let the agent write the JSON file itself (needs Write; keeps the tool we are
removing); JSON Schema only (cannot express the URL and control-character rules cleanly, and
a script is the house pattern: deterministic checks go in `src/`).

### D2. Notes are display-only

`notes` exists for the user. Skill prose SHALL NOT copy it into `BUILD_PLAN.json`,
`build/known_context.md`, rendered planner/builder prompts, or script comments. Script
comments cite `source_urls[0]` from validated `data`, which D1 guarantees has no newline.

*Alternative:* sanitize notes and pass them on. Rejected: any text that reaches an LLM prompt
is instruction-capable no matter how it is cleaned.

### D3. Tool trim

| Agent | Keeps | Drops | Why kept |
|-------|-------|-------|----------|
| sourcing | Read, WebSearch, WebFetch | Bash, Write, Edit, Glob, Grep | Read: its prompt file |
| research | Read, Bash, WebSearch, WebFetch | Write, Edit, Glob, Grep | Bash: `fetch_stl.py`, `measure_stl.py` |

The research prompt names the two scripts as the only Bash commands to run. Permission
allow-patterns cover exactly those two invocations, so any other Bash call prompts the user.

*Alternative:* main session does download + measure and re-dispatches research. Rejected:
two round trips and the agent loses context for interpreting measurements.

### D4. `fetch_stl.py`

`uv run ... src/fetch_stl.py --url <url>` downloads to `build/refs/<sha256-prefix>.stl`. It
accepts only `http`/`https`, follows at most 3 redirects, aborts above 50 MB, and loads the
result with `mesh_io.load_mesh`; on parse failure it deletes the file. Output JSON:
`{"success", "errors", "path", "bytes", "sha256"}`. The caller cannot choose the output path.
No domain allowlist (user decision).

### D5. Rung 1 consent gate

When the main session takes `rung: 1` for a CadQuery or build123d candidate, it SHALL present
the URL, license and the statement "this runs third-party Python on your machine" and ask the
user to choose: run it (reuse/convert) or re-author it. Re-author follows the existing
OpenSCAD path (read parameters and topology, author through the part loop). The decision is
recorded in `planning_notes` with the provenance entry. OpenSCAD and FreeCAD already
re-author and need no gate. This is a prose rule in `skill/phase0_sourcing.md` because the
choice belongs to the user.

## Risks / Trade-offs

- [Research Bash is still general-purpose; a user approving an unexpected Bash prompt
  re-opens the hole] -> allow-patterns cover only the two scripts, so anything else is a
  visible prompt; the prompt text says to run nothing else.
- [Read lets an injected agent read local secrets and leak them through a WebSearch query or
  WebFetch URL] -> accepted residual risk for now; the prompt-file Read is required by the
  render pattern. A later change can pass sourcing/research prompts inline and drop Read.
- [JSON-only output raises agent formatting failures] -> one resume with validator errors,
  then empty result; existing behavior for "nothing found" already handles that.
- [Users click through the rung 1 consent] -> it is still strictly better than silent
  execution; sandboxing is a possible follow-up.
- [Dropping notes from the planner loses useful fit hints] -> the user sees them at the
  checkpoint and can restate anything relevant in their own words, which is then trusted.

## Migration Plan

Single release. `init_permissions.py` already overwrites stale project agent copies, so
`/cq-design:update` or the next init picks up the new tool lists. Rollback is reverting the
agent files, prompts and skill prose; the new scripts are unused once reverted.

## Open Questions

- Resolved (2026-11-14): agent `tools` does NOT accept scoped entries like `Bash(uv run ...)`
  (code.claude.com/docs/en/sub-agents: `tools` lists whole tools; a `disallowedTools`
  specifier still removes the whole tool). Scoping Bash to the two scripts relies on the
  settings allow-list (anything else prompts the user). Hard enforcement would need a
  `PreToolUse` hook in settings.json (hooks in plugin-agent frontmatter are ignored); out
  of scope here, possible follow-up.
