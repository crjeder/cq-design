"""CADPrompt scoring path -- synthetic meshes, no CadQuery, no dataset."""

import sys
from pathlib import Path

import numpy as np
import trimesh

sys.path.insert(0, str(Path(__file__).parent.parent / "evals"))

import cadprompt_bench  # noqa: E402  # pyright: ignore[reportMissingImports]


def _score(produced, golden, tmp_path):
    produced.export(tmp_path / "p.stl")
    golden.export(tmp_path / "g.stl")
    return cadprompt_bench.score_pair(tmp_path / "p.stl", tmp_path / "g.stl")


def test_scaled_rotated_shifted_copy_scores_as_identical(tmp_path):
    golden = trimesh.creation.box((3.0, 1.0, 0.5))
    produced = golden.copy()
    produced.apply_scale(7.0)
    produced.apply_transform(trimesh.transformations.rotation_matrix(np.pi / 2, [1, 0, 0]))
    produced.apply_translation((5, -2, 9))
    score = _score(produced, golden, tmp_path)
    assert score["iou"] > 0.98
    assert score["chamfer"] < 0.03


def test_different_shape_scores_worse(tmp_path):
    score = _score(trimesh.creation.cylinder(0.5, 1.0), trimesh.creation.box((1, 1, 1)), tmp_path)
    assert score["iou"] < 0.9
    assert score["chamfer"] > 0.03
