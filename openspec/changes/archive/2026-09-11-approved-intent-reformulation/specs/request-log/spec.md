## MODIFIED Requirements

### Requirement: Planning populates the initial request verbatim
The planning phase SHALL populate `request_log` when emitting a new plan: the
user's original request as the `initial` entry, plus one entry per clarification
gathered during requirements/planning, all verbatim. The `initial` entry SHALL keep
the user's unresolved opening wording even after Phase 1 resolves it -- the resolved
reading lives in `intent` (see the `approved-intent` spec), never in place of the
verbatim entry.

#### Scenario: Fresh plan from a clarified request
- **WHEN** the planner emits `BUILD_PLAN.json` after asking two clarifying
  questions
- **THEN** the plan's `request_log` holds the original request as `initial` and
  the two answers as `clarification` entries, in order, verbatim

#### Scenario: Vague opening is not rewritten by the reformulation
- **WHEN** Phase 1 reformulates "a stand for my laptop" into a fully resolved
  description the user approves
- **THEN** `request_log[0].text` still reads "a stand for my laptop" and the resolved
  description is written to `intent`

---

### Requirement: A sketch referenced by a request_log entry is copied into the project and re-read on iteration
When the user attaches an image (a sketch, a photo, or an annotated screenshot) to
their opening request, a clarification, or a correction, the orchestrator SHALL copy
that image into a `sketches/` directory at the project root under a stable, descriptive
name before appending the `request_log` entry, and SHALL record the copied file's
repo-relative path in that entry's `images` field. This applies to the `initial` entry
written in Phase 1 exactly as it applies to a mid-build correction. When iterating on
the feature a `request_log` entry's `images` annotate -- during a correction round or
Escalation -- the orchestrator SHALL re-read the referenced sketch file(s) before
re-authoring the part, the same discipline `skill/phase3_build.md` already prescribes
for preview renders ("read the render before re-rendering").

#### Scenario: An attached sketch is copied and logged
- **WHEN** the user gives a correction accompanied by an annotated image during the
  Design approval checkpoint
- **THEN** the image is copied into `sketches/`, and the appended `correction` entry's
  `images` field names that copied path

#### Scenario: An image attached to the opening request is captured
- **WHEN** the user's first message attaches a photo of the object to be fitted
- **THEN** the photo is copied into `sketches/` and the `initial` entry's `images` field
  names that copied path

#### Scenario: A referenced sketch is re-read before the next attempt
- **WHEN** the orchestrator re-authors a part in response to a correction whose
  `request_log` entry carries `images`
- **THEN** it reads the referenced sketch file(s) before writing the next attempt,
  not only the entry's `text`
