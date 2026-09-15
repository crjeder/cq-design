# Sub-agent pipeline architecture

Target architecture for splitting the cq-design pipeline into sub-agents.
Purpose: clean state per role, less main-session context pressure, per-role
model routing (strong model for planning, cheaper model for part authoring).

Two forces determine every agent boundary:

1. **User interaction** - sub-agents cannot talk to the user. Every checkpoint
   (dimension table, plan approval, design approval, build-stage checkpoints,
   hint requests) MUST live in the main session.
2. **Context weight** - web page snapshots and preview PNGs are the heavy
   payloads. They belong inside the agent that consumes them, so they never
   accumulate in the main session.

```mermaid
---
config:
  layout: dagre
---
flowchart TB
    subgraph MAIN["MAIN SESSION - orchestrator. Owns every user checkpoint. Holds only: plan, verdicts, tables, final preview paths."]
        REQ["Phase 1: requirements Q&A,<br>topology clarification"]
        CK1{"Dimension table<br>approved?"}
        CK2{"BUILD_PLAN.json<br>approved?"}
        ROUTE{"Per part:<br>staged or one run?"}
        PROG["Stage checkpoint:<br>user reviews the stage renders"]
        HINT["Attempts exhausted:<br>ask user - hint / accept / skip"]
        CK3{"Design approval:<br>user reviews all renders"}
        FINISH["Deterministic finish - programs, no LLM:<br>print orientation, model export +<br>whole-model checks (kinematic, plate<br>clearance, keep-out), quality gate, deliver"]
    end

    RESEARCH["RESEARCH AGENT<br>web search, spec pages, community models,<br>measure_stl reverse-engineering.<br>Returns the validation table only -<br>page snapshots die here."]
    PLANNER["PLANNER AGENT - strong model (Fable/Opus)<br>rendered prompts/planning.md in,<br>BUILD_PLAN.json out.<br>Topology errors cost a full rebuild,<br>so this is where model strength pays."]
    PV["plan_validate.py<br>(program)"]
    BUILDER["PART BUILDER AGENT x N - cheaper model (Sonnet),<br>parallelizable. One agent per part.<br>Internal loop, max 3 attempts:<br>write - lint - validate - render - self-check.<br>Draft and refine are ONE agent: retries keep<br>memory of what already failed.<br>Images and retry noise die here."]
    DET["script_lint.py,<br>run_cadquery_model.py<br>(programs)"]
    AUDITOR["IMPLEMENTATION AUDITOR AGENT<br>fresh context - never sees the scripts.<br>Judges plan entry vs rendered views,<br>answers the visual checklist citing views.<br>Deterministic backstop: feature_presence_check.py"]

    REQ --> RESEARCH --> CK1
    CK1 -- "corrections" --> RESEARCH
    CK1 -- "approved" --> PLANNER --> PV
    PV -- "schema / inventory errors" --> PLANNER
    PV -- "valid" --> CK2
    CK2 -- "edits" --> PLANNER
    CK2 -- "approved" --> ROUTE
    ROUTE -- "stages from review_policy<br>or user override" --> BUILDER
    BUILDER -- "stage_ready" --> PROG
    PROG -- "approve / change / finish:<br>RESUME the same agent" --> BUILDER
    BUILDER <--> DET
    BUILDER -- "blocked after 3 attempts" --> HINT
    HINT -- "hint: RESUME the same agent,<br>attempt context intact" --> BUILDER
    BUILDER -- "part passed" --> AUDITOR
    AUDITOR -- "visual_mismatch: named question<br>+ cited view" --> BUILDER
    AUDITOR -- "all questions pass" --> CK3
    CK3 -- "change request" --> BUILDER
    CK3 -- "approved" --> FINISH
    FINISH -- "orientation demands a<br>geometry edit" --> BUILDER

    style REQ fill:#FFE0B2,stroke:#FF6D00
    style CK1 stroke:#f87171,fill:#fef2f2
    style CK2 stroke:#f87171,fill:#fef2f2
    style CK3 stroke:#f87171,fill:#fef2f2
    style ROUTE stroke:#f87171,fill:#fef2f2
    style HINT fill:#FFE0B2,stroke:#FF6D00
    style PROG fill:#FFE0B2,stroke:#FF6D00
    style RESEARCH stroke:#818cf8,fill:#eef2ff
    style PLANNER stroke:#818cf8,fill:#eef2ff
    style BUILDER stroke:#818cf8,fill:#eef2ff
    style AUDITOR stroke:#818cf8,fill:#eef2ff
    style PV stroke:#AA00FF,fill:#E1BEE7
    style DET stroke:#AA00FF,fill:#E1BEE7
    style FINISH stroke:#AA00FF,fill:#E1BEE7
```

Legend: indigo = LLM sub-agent, purple = deterministic program, red diamond =
gate, orange = main-session user interaction.

## Agent roster

| Agent | Model | Input | Output | Why it is an agent |
|---|---|---|---|---|
| Research | default | rendered `prompts/research.md` | dimension validation table + sources, `parameters.py` values | page snapshots are huge; main gets a table |
| Planner | `skill_config.json`'s `models.planner` (default strong, e.g. Opus) | rendered `prompts/planning.md` | `BUILD_PLAN.json` | topology reasoning is the highest-leverage LLM step; a wrong topology is a full rebuild |
| Part builder (x N) | `skill_config.json`'s `models.part_author` (default mid-tier, e.g. Sonnet; `"inline"` skips the spawn) | `build/<id>_prompt.txt` = `prompts/builder.md` + `prompts/part.md`, rendered by `src/render_prompt.py` | passing `build/<id>.py`, bbox, preview paths, `attempts.jsonl` rows | contains the render images and retry noise; clean state between parts |
| Implementation auditor | default (vision) | `prompts/audit.md` rendered by `src/render_prompt.py`: plan entry, scoped request text, preview/section PNGs, PARAMETERS values for load-bearing parts, NOT the geometry code | per-question pass/fail with cited views | kills self-review bias - the author never grades its own homework |

Remarks:
- Research: lookup targets need to be researched and improved
- Research: output is a correct and user validated, complete, consistent and coflict free user intent.
- Planner, Builder: invariant is the user intent. any change to the intent starts over the outer loop (at research)
- Auditor: compare agaist intent

## Design rules

- **Draft and refine are one agent.** A separate refiner re-pays the whole
  reference-token cost each round while losing the one thing that makes retries
  cheap: memory of what attempt N already tried. The 3-attempt loop with typed
  error hints stays inside a single builder agent.
- **Two audits, two owners.** "3D-printing failure points" is deterministic
  (`script_lint.py`, `run_cadquery_model.py`, `quality_gate.py`) - programs,
  never agents. "Is the plan implemented" is the fresh-context LLM audit - the
  single strongest quality argument for the split.
- **Escalation resumes, never respawns.** A builder that exhausts its attempts
  returns `blocked` + error summary; main asks the user; the SAME agent is
  resumed with the hint, so attempt context is preserved exactly when it is
  valuable.
- **Checkpoints resume, too.** A staged part's builder returns `stage_ready`
  after each stage; main shows the renders to the user and resumes the same
  agent with the feedback. Every part therefore gets a builder and an audit, and
  main never loads the references or the images.
- **Orientation is not terminal.** The print-orientation loop can demand
  geometry edits (chamfer an overhang, add a foot); that re-enters the builder
  and re-runs validation + audit for the touched part.
- **No `.claude/agents/` files needed.** `src/render_prompt.py` writes each
  agent's prompt to a file; main spawns the agent with "read this file and
  follow it" and a per-call model override. Portable with the skill.

## Known tensions (measured, not assumed)

- **Cold-start cost vs. context relief.** Each builder re-reads the CadQuery
  Pattern Reference + Anti-Patterns + FDM guidelines. Inline pays that once;
  agents pay it N times - but inline pays image accumulation, which grows
  superlinearly with part count. `evals/run_evals.py` (cost per accepted part,
  first-shot rate, attempts-to-pass) is the acceptance test. No adoption on
  vibes.
- **Cross-part carryover is lost.** Inline, fixing `workplane_drift` on part 1
  makes part 3's author smarter. Mitigation: mine this session's
  `build/attempts.jsonl` error patterns into a one-line "known pitfalls" note
  injected into subsequent builder prompts.
- **Interface consistency across parts.** Two isolated builders authoring a
  mating pair can drift where one inline author would not. The plan's
  `interfaces` entries are the contract; kinematic, plate-clearance, and
  feature-presence checks are the deterministic net. Watch this in the first
  eval runs.
- **Parallel builders** need collision-free telemetry appends and per-part
  preview paths (mostly already true; verify before enabling parallelism).

## Sequencing

Agent instructions live in `prompts/research.md`, `prompts/planning.md`,
`prompts/builder.md` + `prompts/part.md`, and `prompts/audit.md`; the
`skill/phase*.md` files hold only main-session orchestration.

Model routing finally gives the telemetry `model` field real values (the part
telemetry hook records the executor's actual model per attempt), so the eval harness can prove whether the
routing pays for itself.

