"""pipeline.py state machine -- fast, no CadQuery."""

import json
import re
from pathlib import Path

import pipeline

SKILL = Path(__file__).resolve().parent.parent


def project(tmp_path, lines=(), parts=("lid", "base"), scripts=()):
    (tmp_path / "build").mkdir(exist_ok=True)
    (tmp_path / "build" / "journal.md").write_text(
        "".join(f"- {ln}\n" for ln in lines), encoding="utf-8"
    )
    if parts:
        plan = {"parts": [{"id": p} for p in parts]}
        (tmp_path / "BUILD_PLAN.json").write_text(json.dumps(plan), encoding="utf-8")
    for s in scripts:
        (tmp_path / "build" / f"{s}.py").write_text("result = 1\n", encoding="utf-8")
    return tmp_path


def st(root, route="design"):
    return pipeline.status(root, route)


DIMS = "phase1/dimensions_approved: ok"
WRITTEN = "phase2/plan_written: ok"
APPROVED = "phase2/plan_approved: ok"


def test_fresh_dir(tmp_path):
    s = st(tmp_path)
    assert s["done"] == []
    assert "phase0/rung_decision" in s["allowed_next"]
    assert "phase1/dimensions_approved" in s["allowed_next"]


def test_restart_voids_earlier_lines(tmp_path):
    root = project(tmp_path, [DIMS, "phase0/restart: again"])
    assert "phase1/dimensions_approved" not in st(root)["done"]


def test_status_writes_nothing(tmp_path):
    st(tmp_path)
    assert list(tmp_path.iterdir()) == []


def test_reapproved_dimensions_void_plan(tmp_path):
    root = project(tmp_path, [DIMS, WRITTEN, APPROVED, DIMS])
    s = st(root)
    assert {v["milestone"] for v in s["void"]} == {"phase2/plan_written", "phase2/plan_approved"}
    assert "phase2/plan_written" in s["allowed_next"]


def test_design_approval_needs_every_part(tmp_path):
    root = project(tmp_path, [DIMS, WRITTEN, APPROVED, "phase3/part_accepted:lid: ok"])
    s = st(root)
    assert "phase3/part_accepted:base" in s["allowed_next"]
    errs = pipeline.can(root, "phase3/design_approved", "design")
    assert errs[0]["type"] == "prerequisite_missing"
    assert "part_accepted:base" in errs[0]["message"]


def test_script_written_line_out_of_order_is_void(tmp_path):
    root = project(tmp_path, [WRITTEN])
    assert st(root)["void"][0]["milestone"] == "phase2/plan_written"


def test_stale_part(tmp_path):
    root = project(tmp_path, [DIMS, WRITTEN, APPROVED], scripts=["lid"])
    old = pipeline.script_hash(str(root / "build" / "lid.py"))
    (root / "build" / "journal.md").write_text(
        (root / "build" / "journal.md").read_text() + f"- phase3/part_accepted:lid: ok sha={old}\n",
        encoding="utf-8",
    )
    assert st(root)["stale_parts"] == []
    (root / "build" / "lid.py").write_text("result = 2\n", encoding="utf-8")
    s = st(root)
    assert s["stale_parts"] == ["lid"]
    assert "phase3/part_accepted:lid" in s["allowed_next"]
    assert "phase3/part_accepted:lid" not in s["done"]


def test_legacy_part_line_warns_not_stale(tmp_path):
    root = project(tmp_path, [DIMS, WRITTEN, APPROVED, "phase3/part_accepted:lid: ok"])
    s = st(root)
    assert s["stale_parts"] == []
    assert "phase3/part_accepted:lid" in s["done"]
    assert s["warnings"]


def test_design_approved_blocked_by_stale_part(tmp_path):
    root = project(tmp_path, [DIMS, WRITTEN, APPROVED], scripts=["lid", "base"])
    h = {p: pipeline.script_hash(str(root / "build" / f"{p}.py")) for p in ("lid", "base")}
    lines = [DIMS, WRITTEN, APPROVED] + [f"phase3/part_accepted:{p}: ok sha={h[p]}" for p in h]
    project(tmp_path, lines, scripts=["lid", "base"])
    (root / "build" / "base.py").write_text("result = 3\n", encoding="utf-8")
    assert pipeline.can(root, "phase3/design_approved", "design")[0]["type"] == "part_stale"


def test_advance_refused_writes_nothing(tmp_path):
    root = project(tmp_path, [DIMS])
    before = (root / "build" / "journal.md").read_text()
    line, errs = pipeline.advance(root, "phase3/orientation_chosen", "x", "design")
    assert line is None and errs[0]["type"] == "prerequisite_missing"
    assert (root / "build" / "journal.md").read_text() == before


def test_advance_valid_appends(tmp_path):
    root = project(tmp_path, [DIMS, WRITTEN])
    line, errs = pipeline.advance(root, "phase2/plan_approved", "user approved", "design")
    assert errs == [] and line == "- phase2/plan_approved: user approved"
    assert (root / "build" / "journal.md").read_text().endswith(line + "\n")


def test_advance_part_accepted_stamps_hash(tmp_path):
    root = project(tmp_path, [DIMS, WRITTEN, APPROVED], scripts=["lid"])
    line, _ = pipeline.advance(root, "phase3/part_accepted:lid", "audit passed", "design")
    assert line is not None
    assert "sha=" + pipeline.script_hash(str(root / "build" / "lid.py")) in line


def test_unknown_milestone(tmp_path):
    for key in ("phase9/foo", "phase3/part_accepted", "phase2/plan_written:x"):
        assert pipeline.can(tmp_path, key, "design")[0]["type"] == "unknown_milestone"


def test_edit_route_needs_nothing(tmp_path):
    s = st(tmp_path, "edit")
    assert s["allowed_next"] == pipeline.EDIT_STEPS
    assert pipeline.can(tmp_path, "phase3/gate_result", "edit")[0]["type"] == "route_forbids"
    assert list(tmp_path.iterdir()) == []


def test_plan_route_ends_at_approval_and_continues_as_design(tmp_path):
    root = project(tmp_path, [DIMS, WRITTEN, APPROVED])
    plan = st(root, "plan")
    assert plan["complete"] and plan["allowed_next"] == []
    design = st(root, "design")
    assert not design["complete"]
    assert "phase3/part_accepted:lid" in design["allowed_next"]
    assert pipeline.can(root, "phase3/part_accepted:lid", "plan")[0]["type"] == "route_forbids"


def test_sourcing_status(tmp_path):
    assert st(tmp_path)["sourcing"] == "pending"
    root = project(tmp_path, ["phase0/sourcing_skipped: from scratch"], parts=())
    s = st(root)
    assert s["sourcing"] == "skipped" and "phase1/dimensions_approved" in s["allowed_next"]
    root = project(tmp_path, ["phase0/rung_decision: rung 5, source none, license n/a"], parts=())
    s = st(root)
    assert s["sourcing"] == "rung_5" and "phase1/dimensions_approved" in s["allowed_next"]


def test_rung3_delivers_as_is(tmp_path):
    root = project(tmp_path, ["phase0/rung_decision: rung 3, source u, license ok"], parts=())
    s = st(root)
    assert s["sourcing"] == "rung_3"
    assert s["skipped_phases"] == ["phase1", "phase2", "phase3"]
    assert s["allowed_next"] == ["phase4/delivered"]
    _, errs = pipeline.advance(root, "phase4/delivered", "done", "design")
    assert errs == []
    assert st(root)["complete"]


def test_malformed_rung_line_is_void(tmp_path):
    root = project(tmp_path, ["phase0/rung_decision: found something"], parts=())
    s = st(root)
    assert s["sourcing"] == "pending"
    assert s["void"][0]["milestone"] == "phase0/rung_decision"


def test_cli_exit_codes(tmp_path, capsys):
    root = project(tmp_path, [DIMS])
    assert pipeline.main(["status", "--dir", str(root)]) == 0
    assert pipeline.main(["can", "phase4/delivered", "--dir", str(root)]) == 1
    assert pipeline.main(["advance", "phase2/plan_written", "ok", "--dir", str(root)]) == 0
    capsys.readouterr()


def test_milestone_table_matches_resume_doc():
    doc = (SKILL / "skill" / "resume.md").read_text(encoding="utf-8")
    keys = set(re.findall(r"^\| \d \| `(\w+)(?::<part_id>)?` \|", doc, re.M))
    ours = {k.split("/")[1] for k in pipeline.MILESTONES}
    assert ours | {"restart"} == keys
