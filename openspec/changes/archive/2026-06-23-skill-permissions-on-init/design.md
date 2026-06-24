## Context

The skill drives its pipeline by issuing shell commands (`uv run --project "$SKILL_DIR"
python "$SKILL_DIR/src/<tool>.py" ...`, `uv sync`, `cp`/`Copy-Item`, `mkdir`/`New-Item`),
`WebSearch`/`WebFetch`, and Playwright browser MCP calls. Claude Code gates each tool call
against the merged `permissions.allow` lists in global and project-local settings. A fresh
working directory has none of the skill's command shapes allow-listed, so the user is
prompted repeatedly during a single run.

The command shapes are known and stable: they differ only in the interpolated `$SKILL_DIR`
absolute path and per-part arguments (script names, dimensions, file paths). They are
therefore expressible as a fixed set of wildcard allow patterns. Claude Code already supports
this style — the repo's own `.claude/settings.local.json` uses entries like `Bash(uv *)` and
`PowerShell(uv run pytest *)`.

Project-local settings live at `.claude/settings.local.json` in the working directory and are
git-ignored, which is the correct home for per-directory, machine-local permission grants.

## Goals / Non-Goals

**Goals:**
- Seed `.claude/settings.local.json` in the working directory with the permission patterns
  the skill's own commands need, on first use in that directory or on explicit init.
- Merge idempotently: create the file if absent, otherwise add only missing patterns to
  `permissions.allow` without reordering, removing, or duplicating existing entries.
- Cover both shells (Bash and PowerShell) since SKILL.md documents both.

**Non-Goals:**
- Touching the user's global settings or `$SKILL_DIR`.
- Granting permissions for commands the skill does not itself issue.
- Guaranteeing zero prompts for inherently unpredictable calls: arbitrary manufacturer
  `WebFetch` domains and browser MCP tools whose server name is environment-dependent. These
  remain best-effort (known maker domains are seeded; the rest still prompt).
- Auto-approving anything destructive — the list is read/scaffold/build commands only.

## Decisions

### 1. Detection of "first use" — use the permission block itself as the marker

No separate marker file. On entry the skill checks whether the working directory's
`.claude/settings.local.json` already contains the skill's sentinel pattern (the distinctive
`run_cadquery_model.py` allow entry). Absent → run init. Present → skip. Explicit init always
re-runs the merge so a newer skill version can add patterns. Rationale: avoids a second
on-disk artifact to keep in sync, and the block's presence is exactly the condition we care
about.

Alternative considered: a `.cq-design-init` stamp file. Rejected — redundant with the block
and can drift from the actual settings content.

### 2. Merge via a small helper script, list stored as data

Add `src/skill_permissions.json` (the canonical allow-pattern list, single source of truth)
and `src/init_permissions.py` (reads/creates `<cwd>/.claude/settings.local.json`, merges the
list into `permissions.allow` deduped and order-preserving, writes back with 2-space indent,
prints the patterns it added). Rationale: JSON merge with dedup is fiddly to do reliably by
hand and across platforms; a script is testable (`tests/test_init_permissions.py`) and keeps
the list editable without code changes.

Alternative considered: have Claude read/merge/write inline with the Read/Write tools (no
Bash prompt at all). Rejected as the primary path — not unit-testable and error-prone for
idempotent dedup — but it is the documented fallback if the helper cannot run.

### 3. Bootstrap prompt is accepted

Running `init_permissions.py` is itself a command that may prompt once on a truly fresh
directory. That single approval seeds everything else. Accepted trade-off; documented in
SKILL.md so the user knows the first prompt is the bootstrap.

### 4. Canonical pattern set

Stored in `src/skill_permissions.json`. Wildcards absorb the `$SKILL_DIR` path and per-part
args. Both Bash and PowerShell variants are included:

- Tool runners / validation:
  `Bash(uv run --project * python * run_cadquery_model.py *)`,
  `Bash(uv run --project * python * print_orientation.py *)`,
  `Bash(uv run --project * python * model_export.py *)`,
  `Bash(uv run --project * python * quality_gate.py *)`,
  `Bash(python * plan_validate.py *)`, `Bash(python * measure_stl.py *)`,
  plus the broader `Bash(uv run *)` and `Bash(uv sync*)` fallbacks, and `PowerShell(...)`
  twins of each.
- Self-contained build scaffold: `Bash(uv run python build/build.py*)`,
  `Bash(cp *)` / `PowerShell(Copy-Item *)`, `Bash(mkdir *)` /
  `PowerShell(New-Item -ItemType Directory *)`, `Bash(uv sync*)` / `PowerShell(uv sync*)`.
- STL download helper: `Bash(python -c *urllib*)` is intentionally NOT broadly allowed
  (arbitrary `python -c` is too wide); the download still prompts. (Open question below.)
- Dimension lookup: `WebSearch`, and `WebFetch(domain:...)` for the maker sources SKILL.md
  names (`www.thingiverse.com`, `api.thingiverse.com`, `www.printables.com`,
  `makerworld.com`, `www.gsmarena.com`). Arbitrary manufacturer domains still prompt.
- Browser MCP: best-effort entry for the Playwright server the skill documents. Because the
  MCP server segment is environment-dependent, this is documented as may-still-prompt rather
  than guaranteed.

The list is deliberately scoped to skill-issued shapes; it is tunable in one file from field
experience.

## Risks / Trade-offs

- [Over-broad patterns weaken the user's safety prompts] → Scope to skill command shapes;
  no destructive verbs; prefer the named-script patterns and keep the broad `uv run *`
  fallback as the documented, reviewable widest grant. The file is git-ignored and
  per-directory, limiting blast radius.
- [Clobbering a hand-edited settings.local.json] → Merge is additive and order-preserving;
  never rewrites or drops existing entries. Covered by a test that starts from a populated
  file.
- [MCP/arbitrary-domain calls still prompt] → Documented as a known gap; the bulk of prompts
  (the per-step `uv run`/`python` calls) are eliminated, which is the actual pain point.
- [Settings schema drift in Claude Code] → The helper only touches `permissions.allow`
  (create the nested object if missing) and leaves all other keys untouched.

## Open Questions

- Should the `python -c` STL-download one-liner get its own narrow pattern, or keep prompting?
  Leaning keep-prompting (arbitrary `-c` is hard to scope safely); revisit if it proves a
  frequent interruption.
- Whether to also offer a `--global` explicit-init mode that seeds the user's global settings
  for users who always work in fresh directories. Out of scope for this change.
