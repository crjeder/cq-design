"""Assert the Material Constants table in reference/Engineering Design Rules.md agrees
with the machine-readable src/material_properties.json it is sourced from."""

import json
import os
import re

SKILL_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_PROPS_PATH = os.path.join(SKILL_ROOT, "src", "material_properties.json")
_DOC_PATH = os.path.join(SKILL_ROOT, "reference", "Engineering Design Rules.md")

_ROW_RE = re.compile(
    r"^\|\s*(?P<material>[^|]+?)\s*\|\s*(?P<strain>[\d.]+)\s*\|\s*(?P<flex>[\d.]+)\s*\|"
    r"\s*(?P<E>[\d.]+)\s*\|\s*(?P<nu>[\d.]+)\s*\|\s*(?P<inplane>[\d.]+)\s*\|"
    r"\s*(?P<z>[\d.]+)\s*\|\s*(?P<shear>[\d.]+)\s*\|"
)


def _parse_table_rows() -> dict[str, dict[str, float]]:
    rows: dict[str, dict[str, float]] = {}
    with open(_DOC_PATH, encoding="utf-8") as f:
        for line in f:
            m = _ROW_RE.match(line.strip())
            if not m:
                continue
            rows[m.group("material")] = {
                "allowable_strain_pct": float(m.group("strain")),
                "flexural_modulus_gpa": float(m.group("flex")),
                "E_mpa": float(m.group("E")),
                "nu": float(m.group("nu")),
                "s_inplane_mpa": float(m.group("inplane")),
                "s_z_mpa": float(m.group("z")),
                "s_shear_mpa": float(m.group("shear")),
            }
    return rows


def _load_properties() -> dict[str, dict]:
    with open(_PROPS_PATH, encoding="utf-8") as f:
        return json.load(f)


def test_table_rows_found():
    rows = _parse_table_rows()
    assert set(rows) == {"PLA", "PETG", "ABS", "TPU (95A)"}


def test_table_agrees_with_material_properties_json():
    rows = _parse_table_rows()
    props = _load_properties()["materials"]
    assert set(rows) == set(props)
    for material, doc_values in rows.items():
        json_values = props[material]
        for key, doc_value in doc_values.items():
            assert doc_value == json_values[key], (
                f"{material}.{key}: table says {doc_value}, "
                f"material_properties.json says {json_values[key]}"
            )


def test_default_safety_factor_stated_in_doc():
    props = _load_properties()
    with open(_DOC_PATH, encoding="utf-8") as f:
        text = f.read()
    assert str(props["default_safety_factor"]) in text
