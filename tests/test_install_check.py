import json

import install_check as ic


def _plugin(cfg, install_path, commit="aaa", create=True):
    if create:
        install_path.mkdir(parents=True)
    reg = cfg / "plugins"
    reg.mkdir(parents=True, exist_ok=True)
    (reg / "installed_plugins.json").write_text(
        json.dumps(
            {
                "version": 2,
                "plugins": {
                    "cq-design@mkt": [{"installPath": str(install_path), "gitCommitSha": commit}]
                },
            }
        ),
        encoding="utf-8",
    )


def _standalone(skills, commit="aaa"):
    d = skills / "cq-design"
    d.mkdir(parents=True)
    (d / "SKILL.md").write_text("x", encoding="utf-8")
    (d / ".version.json").write_text(json.dumps({"commit": commit}), encoding="utf-8")


def test_both_installed(tmp_path):
    cfg, skills = tmp_path / "cfg", tmp_path / "skills"
    _plugin(cfg, tmp_path / "cache" / "p")
    _standalone(skills)
    r = ic.check(cfg, skills)
    assert r["duplicate"] and r["commits_differ"] is False
    assert str(tmp_path / "cache" / "p") in r["hint"]


def test_commits_differ(tmp_path):
    cfg, skills = tmp_path / "cfg", tmp_path / "skills"
    _plugin(cfg, tmp_path / "p", commit="aaa")
    _standalone(skills, commit="bbb")
    assert ic.check(cfg, skills)["commits_differ"] is True


def test_plugin_only(tmp_path):
    _plugin(tmp_path / "cfg", tmp_path / "p")
    r = ic.check(tmp_path / "cfg", tmp_path / "skills")
    assert not r["duplicate"] and r["standalone"] is None and r["hint"] == ""


def test_standalone_only(tmp_path):
    _standalone(tmp_path / "skills")
    r = ic.check(tmp_path / "cfg", tmp_path / "skills")
    assert not r["duplicate"] and r["plugin"] is None


def test_corrupt_registry(tmp_path):
    cfg = tmp_path / "cfg"
    (cfg / "plugins").mkdir(parents=True)
    (cfg / "plugins" / "installed_plugins.json").write_text("{nope", encoding="utf-8")
    assert ic.check(cfg, tmp_path / "skills")["plugin"] is None


def test_stale_install_path_ignored(tmp_path):
    cfg, skills = tmp_path / "cfg", tmp_path / "skills"
    _plugin(cfg, tmp_path / "gone", create=False)
    _standalone(skills)
    assert not ic.check(cfg, skills)["duplicate"]
