"""journal.py append helper + CLI -- fast, no CadQuery."""

import journal


def test_append_creates_file(tmp_path):
    path = tmp_path / "journal.md"
    journal.append_line(path, "phase0/rung_decision", "rung 5, source none, license n/a")
    assert (
        path.read_text(encoding="utf-8")
        == "- phase0/rung_decision: rung 5, source none, license n/a\n"
    )


def test_append_does_not_disturb_existing_lines(tmp_path):
    path = tmp_path / "journal.md"
    journal.append_line(path, "phase1/topology_confirmed", "single-piece bracket")
    journal.append_line(
        path, "phase1/dimensions_approved", "parameters.py written, 6 dimensions recorded"
    )
    assert path.read_text(encoding="utf-8").splitlines() == [
        "- phase1/topology_confirmed: single-piece bracket",
        "- phase1/dimensions_approved: parameters.py written, 6 dimensions recorded",
    ]


def test_repeated_milestone_key_appends_new_line(tmp_path):
    path = tmp_path / "journal.md"
    journal.append_line(path, "phase3/part_accepted:lid", "audit passed")
    journal.append_line(path, "phase3/part_accepted:lid", "rebuilt after correction, audit passed")
    lines = path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 2
    assert lines[0] == "- phase3/part_accepted:lid: audit passed"
    assert lines[1] == "- phase3/part_accepted:lid: rebuilt after correction, audit passed"


def test_cli_append(tmp_path):
    path = tmp_path / "journal.md"
    rc = journal.main(
        ["append", str(path), "phase4/delivered", "README.md + REGENERATE.md written"]
    )
    assert rc == 0
    assert (
        path.read_text(encoding="utf-8")
        == "- phase4/delivered: README.md + REGENERATE.md written\n"
    )


def test_cli_unwritable_path_exits_nonzero(tmp_path, capsys):
    # Parent directory does not exist and is not created -- matches journal.md's
    # contract that build/ already exists by the time any milestone is written.
    missing = tmp_path / "does-not-exist" / "journal.md"
    rc = journal.main(["append", str(missing), "phase0/rung_decision", "rung 5"])
    assert rc == 1
    assert "journal" in capsys.readouterr().err
