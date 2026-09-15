## ADDED Requirements

### Requirement: Phase-file prose does not restate itself
A `skill/phase*.md` file SHALL NOT state the same substantive rule more than
once within its own body. Where a later section needs the reader to recall a
rule already stated earlier in the same file, it SHALL reference the earlier
statement by section name rather than repeating the rule's content. This is
distinct from the existing requirements against restating a
guaranteed-in-context read or a code-enforced contract: those cover content
whose source of truth lives outside the phase file; this one covers a phase
file duplicating its own text.

#### Scenario: A rule stated in one section is needed again in a later section
- **WHEN** a phase file's later section (e.g. an approval or exit-checkpoint
  step) depends on a constraint already stated in full earlier in the same
  file (e.g. in an "Ask vs. assume" or eligibility section)
- **THEN** the later section names the earlier section instead of restating
  the constraint's full wording

#### Scenario: Two adjacent sentences make the same point
- **WHEN** a section's opening states a rule and the very next sentence
  restates the same rule in different words with no new information
- **THEN** the section keeps a single statement of the rule
