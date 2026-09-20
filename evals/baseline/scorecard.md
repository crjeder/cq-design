# Eval scorecard

Cost is billed when `cost src` is `recorded`, otherwise estimated (tokens ~ prompt_chars / 4, input rate only).

| case | first-shot | attempts-to-pass | chamfer (mm) | cost/part (USD) | cost src |
|---|---|---|---|---|---|
| adapter-ring | 0.00 | 2.00 | 0.000 | 4.8392 | recorded |
| boss-plate | 1.00 | 1.00 | 0.031 | 6.3367 | recorded |
| east-side-mount | 0.00 | 2.00 | 2.674 | 1.2760 | recorded |
| enclosure-body | 1.00 | 1.00 | 0.013 | 0.5675 | recorded |
| hinged-latch | 1.00 | 1.00 | 0.037 | 1.5589 | recorded |
| l-bracket | 1.00 | 1.00 | 12.709 | 1.9930 | recorded |
| lid-thickness-correction | 1.00 | 1.00 | no artifacts | 0.3341 | recorded |
| phone-stand | 1.00 | 1.00 | 8.552 | 1.7859 | recorded |
| sliding-lid | 1.00 | 1.00 | 1.057 | 1.8734 | recorded |
| snap-lid | 1.00 | 1.00 | 1.037 | 2.1790 | recorded |
| two-part-box | 0.50 | 1.50 | 0.434 | 1.5804 | recorded |
| u-clip | 1.00 | 1.00 | 4.213 | 2.1245 | recorded |
| wall-hook | 0.00 | 4.00 | 6.636 | 3.2909 | recorded |

**Aggregate** (13 cases): first-shot 0.73, attempts-to-pass 1.42, chamfer 3.116 mm (12 cases), cost/part 2.2876 USD
