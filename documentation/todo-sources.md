# Parametric sources and block library -- details

Tasks: [TODO.md](../TODO.md#8-parametric-sources-and-block-library).

### Parameter Sets

e. g. Lego interface definition
unit is "one point" (w * l * h): 8 * 8 * (3 * 3,2) ; center point (r * h): 2,4 * 1.8 , ...
reference:
- https://brickipedia.fandom.com/wiki/LEGO_Brick?file=Brick-in-mm.svg
- https://www.bartneck.de/2019/04/21/lego-brick-dimensions-and-measurements/

### STEP fetch script

`src/fetch_step.py`: query the [step.parts API](https://github.com/earthtojake/step.parts/blob/main/DEVELOPMENT.md#api-notes) (`--query` / `--id`) and download the STEP to `build/refs/`, verified against the API `sha256`, reusing `fetch_stl.py` scheme/redirect/size limits; output `{success, errors, path, bytes, sha256}` + matched `standard`/`attributes`. Gap today: `fetch_stl.py` is STL-only, so a rung-2 STEP hit cannot be downloaded. Also: point `prompts/sourcing.md` at the script, add a `reference/scripts.md` entry, one mocked-response test. Low priority (STEP import is mainly the benchmark). Upstream's `step-parts` skill was retired, so only the API remains as a reference
