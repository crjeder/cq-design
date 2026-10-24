# CADPrompt sample run (2026-10-19)

- Dataset: github.com/Kamel773/CAD_Code_Generation `CADPrompt/` at commit
  `33dcecd6087ff7b8a4454b1ba4d56504a6364399` (not vendored: the repo has no license).
- Part scripts: `evals/cadprompt/parts/p<id>.py`, written single-shot by Claude Opus 5.5 from
  each prompt's `Natural_Language_Descriptions_Prompt_with_specific_measurements.txt` only
  (the reference `Python_Code.py` was not read). This is the part loop through
  `run_cadquery_model.py --deliver`, not the full five-phase pipeline.
- Command: `uv run python -I evals/cadprompt_bench.py --dataset <CADPrompt> --out <run dir>`
- Scale: unit-cube normalized. With 2048 sampled points the Chamfer floor for an exact match
  is about 0.01-0.02 (see 00003558), so differences below that are sampling noise.

| id | tier | built | chamfer | iou |
|---|---|---|---|---|
| 00003558 | Simple | yes | 0.0208 | 1.000 |
| 00009823 | Simple | yes | 0.0109 | 0.512 |
| 00670106 | Simple | yes | 0.0174 | 0.995 |
| 00000633 | Moderate | yes | 0.0063 | 0.998 |
| 00004154 | Moderate | yes | 0.0158 | 0.998 |
| 00996329 | Moderate | yes | 0.0205 | 0.811 |
| 00001817 | Complex | yes | 0.0127 | 1.000 |
| 00520321 | Complex | yes | 0.0193 | 1.000 |
| 00037135 | Very Complex | yes | 0.0208 | 1.000 |
| 00039681 | Very Complex | yes | 0.0585 | 0.443 |
| **mean** | Simple | 3/3 | 0.0163 | 0.836 |
| **mean** | Moderate | 3/3 | 0.0142 | 0.936 |
| **mean** | Complex | 2/2 | 0.0160 | 1.000 |
| **mean** | Very Complex | 2/2 | 0.0397 | 0.722 |
| **mean** | all | 10/10 | 0.0203 | 0.876 |

Misses, from comparing extents with the ground truth:

- 00009823: the prompt's "side length 1.5" is the ground truth's across-corners width, so the
  hexagon came out twice as wide at the same thickness. After normalization it is half as
  thick, which halves the IoU while Chamfer stays low.
- 00996329: the ground-truth L has one 0.6667 leg and one 0.75 leg; the script used 0.75 for
  both.
- 00039681: the prompt gives no outer diameter. The script guessed 0.85; the ground truth is
  1.5.
- 00670106 and 00037135 only score well because of the 24-rotation ICP seeding. The ground
  truth cylinder lies along Y although the prompt says X. With the paper's identity-seeded
  ICP they scored IoU 0.230 and 0.285.
