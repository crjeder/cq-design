## MODIFIED Requirements

### Requirement: The authoring frame is the author's choice

`prompts/part.md` SHALL state that the author chooses the frame in which it builds the
part, and SHALL NOT prescribe an authoring frame or require the author to match a frame
assumed elsewhere in the plan. Guidance that recommends an authoring frame for a class of
part (for example, authoring a printable foundation with its physical bottom at Z=0)
SHALL be stated as a recommendation the author may follow or depart from, and never as a
precondition of the part's placement being correct.

This recommendation SHALL name the case it is meant to resolve: a part whose stated pose
intent places its physical bottom away from Z=0 in the assembled frame (a "floating"
part). For that case, `prompts/part.md` SHALL pair the Z=0-bottom authoring
recommendation with the existing `translate_mm` write-back mechanism (contract rule 6):
author with the physical bottom at script Z=0, then report the offset as
`placement.translate_mm` to land in the stated pose intent. This remains a
recommendation, not a new contract rule -- an author who authors a floating part in a
different frame and reports the matching transform is still not incorrect.

#### Scenario: Author departs from a recommended frame
- **WHEN** the author builds a part in a frame other than one the guidance recommends
- **THEN** the part is not incorrect on that account; the author reports the transform
  matching the frame it actually used

#### Scenario: Guidance does not pin the frame to the plan
- **WHEN** `prompts/part.md` discusses authoring frames
- **THEN** it does not instruct the author to adopt a frame the plan assumed, because the
  plan no longer assumes one

#### Scenario: Floating assembled frame names the paired pattern
- **WHEN** a part's stated pose intent places its physical bottom away from Z=0 in the
  assembled frame
- **THEN** `prompts/part.md` names this case and recommends authoring with the physical
  bottom at script Z=0, reporting the offset as `placement.translate_mm` (contract rule
  6) to reach the stated pose intent, rather than leaving the pairing implicit
