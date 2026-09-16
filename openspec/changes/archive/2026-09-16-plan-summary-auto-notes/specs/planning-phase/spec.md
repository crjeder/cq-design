## MODIFIED Requirements

### Requirement: Plan names reuse the user's own nouns

When the user has named a part or feature in their request or during the
conversation, `prompts/planning.md` SHALL instruct the planner to use that word as the
corresponding part `id` or `interfaces[].name`, normalized only mechanically
(lowercased, spaces and hyphens to underscores) -- never replaced by a synonym. The
planner SHALL coin names only for parts and features the user never named. Every coined
name SHALL be introduced to the user before the build loop starts via `plan_summary.py`'s
**Names I chose** section (see `plan-summary-checkpoint` spec), which detects a coined
name automatically by checking each part id and interface name against `request_log`
rather than requiring the reviewing session to spot it by reading `planning_notes`. When
normalization produces a collision with an existing id, the planner SHALL disambiguate
with a suffix and surface the rename in the summary.

#### Scenario: User noun becomes the plan name

- **WHEN** the user's request says "a mug with a handle"
- **THEN** the plan's interface or part representing that feature is named `handle`,
  not a planner-chosen synonym such as `grip` or `side_loop`

#### Scenario: Coined names are introduced at the checkpoint

- **WHEN** the plan contains a part the user never named
- **THEN** `plan_summary.py`'s **Names I chose** section lists that part's id before the
  user is asked to approve the plan

#### Scenario: Colliding user nouns are disambiguated visibly

- **WHEN** the user names two distinct features with the same word
- **THEN** the plan disambiguates them with suffixes and the plan summary states the
  mapping (in `planning_notes`, surfaced at the checkpoint), rather than silently
  renaming one
