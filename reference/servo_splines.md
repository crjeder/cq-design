# Servo Spline Reference

Look up `servo_spline` parameters when the user names a servo (model, brand, or
spline code) but gives no numeric spline specs. Pick the row, then feed
`spline_external_diameter` (= OD) and `tooth_count` (= T) into `servo_spline(...)`.
The narrow tooth-profile dimensions vary little across servos; unless the datasheet
says otherwise, use the SG90/Futaba-25T profile defaults:
`tooth_depth=0.3, tooth_base_width=0.7, tooth_tip_width=0.1`.

| Spline code | Tooth count (T) | Outer diameter (OD, mm) | Common brands & models |
| --- | --- | --- | --- |
| A1 | 15 | 3.65 | Hitec sub-micro (HS-50, HS-55, HS-35HD) |
| B1 | 25 | 4.00 | Hitec mini/micro (HS-65HB, HS-56HB, HS-125MG) |
| D1 | 15 | 4.80 | Hitec feather (HS-81, HS-82MG, HS-85BB) |
| Micro 21T | 21 | 4.60-4.70 | TowerPro SG90 (TP), MG90S |
| Micro 21T (standard) | 21 | 4.80-4.90 | Generic 9g micro servos (SG90 clones) |
| Futaba mini (2F) | 21 | 4.90 | Futaba micro/nano (S3107, S3153, S117), Turnigy TG9e |
| C1 | 24 | 5.50 | Hitec standard heavy-duty (HS-311, HS-645MG, HS-755HB) |
| Futaba standard (3F) | 25 | 5.80-5.90 | Global standard: Futaba, Savox, Traxxas, Power HD, GoOSERVO, TowerPro (MG995/MG996R), Emax, Tamiya |
| H25T | 25 | 5.85 | Hitec brushless/premium (HS-83XX, HSB-93XX) - matches Futaba 25T horns |
| Giant scale (E1) | 15 | 7.90 | Hitec mega/giant scale (HS-5745MG, HS-5755MG) |

## Notes

- 25T is not universally interchangeable. Futaba 25T (3F), Hitec H25T, and generic
  25T servos share the tooth count but differ slightly in pitch profile and
  tolerance. When the exact brand is unknown, use OD 5.92 (the SG90-class 25T value
  already defaulted in the block) and tune `clearance` on a test print.
- OD is the tip-circle diameter = `spline_external_diameter`. FDM prints holes
  undersized, so the block's default `clearance=0.1` targets a firm press fit at
  nominal; raise for slip, lower/negative for tighter interference.
