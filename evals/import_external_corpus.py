"""Import a filtered, sampled slice of an external text->CadQuery corpus into
`evals/cases/`.

Manual, occasional maintenance tool, like `evals/generate_goldens.py` -- never
invoked by the skill pipeline, quality gate, or CI. Reads a local,
manually-downloaded corpus snapshot only; never fetches over the network itself.

Input format: a JSONL file at --input, one pair per line:
    {"id": "<source-local id>", "description": "<text request>", "code": "<CadQuery script text>"}

Usage:
    uv run python evals/import_external_corpus.py --source text-to-cadquery \\
        --input /path/to/snapshot.jsonl --sample-size 20

Each written case directory is `evals/cases/<prefix>-<slug>/`:
    request.md        verbatim pair description
    <part_id>.py       copied source script (part_id == case dir name, underscored)
    BUILD_PLAN.json    synthesized single-part plan (dimensions from the delivered mesh)
    case.json          tolerance_mm, expected_parts, tags, source, source_id, license
    golden/<part_id>.stl

A pair whose script fails to execute, whose result is not watertight, or whose
synthesized plan fails `plan_validate.py` is logged and skipped -- no case
directory is written for it.
"""

from __future__ import annotations

import argparse
import json
import random
import re
import shutil
import subprocess
import sys
from pathlib import Path

EVALS_DIR = Path(__file__).parent
CASES_DIR = EVALS_DIR / "cases"
SRC_DIR = EVALS_DIR.parent / "src"
RUNNER = SRC_DIR / "run_cadquery_model.py"

sys.path.insert(0, str(SRC_DIR))
from plan import validate_plan  # noqa: E402

# Redistribution terms per --source, keyed by source name. An unrecorded --source
# hard-errors before any sampling or writing (neither line is a guess: both upstream
# repos were checked directly and report no LICENSE file / license: null via the
# GitHub API; terms below are the repo owner's own confirmation, recorded 2026-09-11).
SOURCE_LICENSES = {
    "text-to-cadquery": (
        "Unrestricted (owner-confirmed 2026-09-11; no upstream LICENSE file -- "
        "github.com/Text-to-CadQuery/Text-to-CadQuery, arXiv 2505.06507)"
    ),
    "cadquery-library": (
        "Unrestricted (owner-confirmed 2026-09-11; no upstream LICENSE file -- "
        "github.com/WKJBryan/cadquery-library)"
    ),
}

# Case directory prefix per source, e.g. ext-t2cq-00042.
SOURCE_PREFIX = {
    "text-to-cadquery": "ext-t2cq",
    "cadquery-library": "ext-cql",
}

DOMAIN_KEYWORDS = [
    "enclosure", "bracket", "box", "plate", "adapter", "bore", "mount", "stand",
    "hook", "clip", "holder", "hinge", "standoff", "lid", "panel",
]  # fmt: skip

DEFAULT_SAMPLE_SIZE = 20
DEFAULT_SEED = 20260911
DEFAULT_TOLERANCE_MM = 2.0


def load_pairs(input_path: Path) -> list[dict]:
    pairs = []
    for line in Path(input_path).read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            pairs.append(json.loads(line))
    return pairs


def is_on_domain(description: str) -> bool:
    text = description.lower()
    return any(kw in text for kw in DOMAIN_KEYWORDS)


def sample_pairs(pairs: list[dict], sample_size: int, seed: int) -> list[dict]:
    """Deterministically sample up to `sample_size` on-domain pairs."""
    filtered = [p for p in pairs if is_on_domain(p["description"])]
    filtered.sort(key=lambda p: str(p["id"]))
    if len(filtered) <= sample_size:
        return filtered
    return random.Random(seed).sample(filtered, sample_size)


def _slug(source_id: object) -> str:
    return re.sub(r"[^A-Za-z0-9]+", "-", str(source_id)).strip("-").lower()


def case_name_for(prefix: str, source_id: object) -> str:
    return f"{prefix}-{_slug(source_id)}"


def run_pair(pair: dict, part_id: str, case_dir: Path) -> tuple[dict | None, str | None]:
    """Execute the pair's script via `run_cadquery_model.py --deliver`.

    Returns `(wrapper_result, None)` on a watertight success, or `(None, reason)`
    if execution failed or the result is not watertight. Cleans up any partial
    `case_dir` on failure.
    """
    case_dir.mkdir(parents=True, exist_ok=True)
    script_path = case_dir / f"{part_id}.py"
    script_path.write_text(pair["code"], encoding="utf-8")

    proc = subprocess.run(
        [
            sys.executable,
            str(RUNNER),
            str(script_path),
            "--deliver",
            "--formats",
            "stl",
            "--output-dir",
            str(case_dir / "golden"),
        ],
        capture_output=True,
        text=True,
    )
    try:
        result = json.loads(proc.stdout)
    except json.JSONDecodeError:
        shutil.rmtree(case_dir, ignore_errors=True)
        return None, "unparseable run_cadquery_model.py output"

    if not result.get("success"):
        shutil.rmtree(case_dir, ignore_errors=True)
        return None, "execution failed"
    if not result.get("watertight"):
        shutil.rmtree(case_dir, ignore_errors=True)
        return None, "not watertight"
    return result, None


def write_case(
    source: str, pair: dict, case_dir: Path, part_id: str, wrapper_result: dict
) -> str | None:
    """Write BUILD_PLAN.json, request.md, and case.json for a successfully-run pair.

    Returns None on success, or a skip reason (and removes `case_dir`) if the
    synthesized plan fails `plan_validate.py`.
    """
    bbox = wrapper_result["geometry"]["bbox"]
    intent = (
        f"Imported from the external {source} corpus (source id {pair['id']}), not a "
        f"user-approved reformulation. Original pair description: {pair['description']}"
    )
    plan = {
        "schema_version": 1,
        "printer": "Bambu P1S",
        "material": "PLA",
        "nozzle_mm": 0.4,
        "intent": intent,
        "parts": [
            {
                "id": part_id,
                "description": pair["description"][:200],
                "dimensions": {"w_mm": bbox["x_mm"], "d_mm": bbox["y_mm"], "h_mm": bbox["z_mm"]},
                "interfaces": [],
                "blocks_needed": [],
            }
        ],
        "constraints": {
            "wall_min_mm": 1.2,
            "overhang_max_deg": 50,
            "dimension_tolerance_mm": 0.5,
        },
    }
    plan_path = case_dir / "BUILD_PLAN.json"
    plan_path.write_text(json.dumps(plan, indent=2) + "\n", encoding="utf-8")

    errors = validate_plan(str(plan_path))
    if errors:
        shutil.rmtree(case_dir, ignore_errors=True)
        return f"plan validation failed: {errors}"

    (case_dir / "request.md").write_text(pair["description"].strip() + "\n", encoding="utf-8")
    case_json = {
        "tolerance_mm": DEFAULT_TOLERANCE_MM,
        "expected_parts": 1,
        "tags": ["external", source],
        "source": source,
        "source_id": pair["id"],
        "license": SOURCE_LICENSES[source],
    }
    (case_dir / "case.json").write_text(json.dumps(case_json, indent=2) + "\n", encoding="utf-8")
    return None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True, help="corpus identifier, e.g. text-to-cadquery")
    parser.add_argument("--input", required=True, type=Path, help="local JSONL corpus snapshot")
    parser.add_argument("--sample-size", type=int, default=DEFAULT_SAMPLE_SIZE)
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    args = parser.parse_args(argv)
    source: str = args.source

    if source not in SOURCE_LICENSES:
        print(
            f"unknown --source {source!r}: no recorded license "
            f"(known sources: {sorted(SOURCE_LICENSES)})",
            file=sys.stderr,
        )
        return 1

    pairs = load_pairs(args.input)
    sampled = sample_pairs(pairs, args.sample_size, args.seed)
    prefix: str = SOURCE_PREFIX.get(source, source)

    written = 0
    skipped: list[tuple[str, str]] = []
    for pair in sampled:
        case_name = case_name_for(prefix, pair["id"])
        part_id = case_name.replace("-", "_")
        case_dir = CASES_DIR / case_name

        result, run_reason = run_pair(pair, part_id, case_dir)
        if result is None:
            skipped.append((str(pair["id"]), run_reason or "unknown failure"))
            print(f"  skip {pair['id']}: {run_reason}", file=sys.stderr)
            continue

        write_reason = write_case(source, pair, case_dir, part_id, result)
        if write_reason is not None:
            skipped.append((str(pair["id"]), write_reason))
            print(f"  skip {pair['id']}: {write_reason}", file=sys.stderr)
            continue
        written += 1
        print(f"  wrote {case_name}")

    print(f"sampled {len(sampled)}, written {written}, skipped {len(skipped)}")
    for pair_id, reason in skipped:
        print(f"  {pair_id}: {reason}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
