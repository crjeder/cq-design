# Eval corpus ask-rule trigger count (task 1.2 / 5.4)

Per case, which of the three ask rules in `prompts/planning.md` (rule 1: unverifiable
dimension, rule 4: unclear fit type, rule 10: undeterminable load) the request text would
trigger. All ten requests state every dimension directly (no real-world product lookup),
so rule 1 never triggers on this corpus.

| Case | Rule 1 (dimension) | Rule 4 (fit type) | Rule 10 (load) |
|---|---|---|---|
| adapter-ring | no | n/a (no mating interface) | no (fit type not applicable; but load is a plausible ask - compression, adapter ring under axial clamp - "reasonable default" territory under the carve-out) |
| boss-plate | no | n/a (screw bosses, fastener-defined) | no (flat plate, compression-eligible under rule 10) |
| enclosure-body | no | n/a (open top, lid fit stated in the paired case) | no (structural but geometry implies compression/shell) |
| l-bracket | no | n/a (no mating fit stated) | no (bending load direction inferable from "join two panels at 90 degrees") |
| phone-stand | no | n/a | no (compression, explicit "wedge... inclined back face") |
| sliding-lid | no | **stated** ("sliding lid... locates inside the box rim") - not ambiguous | no |
| snap-lid | no | **stated** ("snap-on lid... snap prongs... engage the box walls") - not ambiguous | no |
| two-part-box | no | implied lip fit, not named - closest to a rule-4 candidate, but "inner locating lip" reads as sliding/loose by convention, not an open ambiguity | no |
| u-clip | no | n/a (single-part clip, no assembly fit) | no (tension/spring load, explicit "grips a 17mm panel") |
| wall-hook | no | n/a | no (structural, explicit reach/retaining-lip geometry implies load direction) |

**Baseline (before this change):** 0/10 cases trigger a genuine rule 1/4 ask. The
planner's prior behavior on ambiguous secondary choices (part/interface naming,
clearance value for the stated fit, plate grouping - none of which any case makes
genuinely unclear) is what the carve-out targets: without it, a strictly deliberate
planner could still ask about these non-blocking choices. None of the ten requests name
a real product, state an ambiguous fit, or leave load undeterminable, so this corpus
cannot exercise rule 1/4/10 differently before vs. after the change - the carve-out's
effect has to be judged by absence of *new* minor-choice questions in the post-run
transcripts (task 5.4), not by a change in this table.

**After (task 5.4):** re-run and confirm the eval transcripts show no new questions
about part naming, clearance-table defaults, or plate grouping on this corpus (should
already be zero, since `--generate` runs are non-interactive and any planner question
would surface as a stalled/failed case rather than a transcript line).
